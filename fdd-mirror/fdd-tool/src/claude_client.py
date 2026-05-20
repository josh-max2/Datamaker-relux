"""Thin wrapper around the Anthropic SDK with prompt caching, JSON parsing, and retries."""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass

import anthropic
from dotenv import load_dotenv


def _parse_json_lenient(cleaned: str, raw: str) -> dict:
    """Parse JSON from a Claude response. Tries strict, then a repair pass, then
    array-element recovery, then surfaces raw.

    Repair pass handles common failure modes:
      - Unescaped double quotes inside string values (most common Claude failure)
      - Trailing commas before } or ]
      - Newlines inside string values (replace with \\n)

    Array-element recovery: when the document looks like {"records": [...]} but
    parsing fails (typically because the response was truncated mid-record), try
    to extract complete record objects from the array. Better than the old
    "flatten everything to a single dict" salvage which lost all but one record.
    """
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Repair attempt 1: remove trailing commas before } or ]
    repaired = re.sub(r",(\s*[}\]])", r"\1", cleaned)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass
    # Repair attempt 2: escape literal newlines inside string values
    # (Claude sometimes returns multi-line strings without \\n escaping)
    repaired2 = re.sub(
        r'"((?:[^"\\]|\\.)*?)"',
        lambda m: '"' + m.group(1).replace("\n", "\\n").replace("\r", "\\r") + '"',
        repaired,
        flags=re.DOTALL,
    )
    try:
        return json.loads(repaired2)
    except json.JSONDecodeError:
        pass
    # Repair attempt 3: escape UNESCAPED internal quotes within string values.
    # Common Claude failure on raw_excerpt-type fields where the source FDD
    # contains quoted legal terms — model writes them with literal " instead
    # of \". Use a state-machine that distinguishes a closing-quote (followed
    # by , } ] : or end-of-input) from an internal quote (followed by content).
    repaired3 = _escape_internal_quotes(repaired2)
    try:
        return json.loads(repaired3)
    except json.JSONDecodeError as e:
        # Array-element recovery: scan for `"records": [` and extract complete
        # `{...}` objects from the array up to the truncation point. Preserves
        # most of the data even when the response was cut off mid-record.
        recovered_records = _recover_array_elements(cleaned, key="records")
        if recovered_records is None:
            # Also try other common array keys (item20 uses yearly_summary +
            # state_year_status; future items may use others)
            for key in ("yearly_summary", "state_year_status", "data"):
                recovered_records = _recover_array_elements(cleaned, key=key)
                if recovered_records:
                    break

        # Final fallback: also extract top-level scalar fields (has_item19,
        # confidence, notes) via regex so the salvage dict still has some context.
        salvage: dict = {
            "_parse_error": str(e),
            "_raw": raw,                # FULL raw (was raw[:5000] — debug-hostile)
            "_salvaged": True,
        }
        if recovered_records is not None:
            salvage["records"] = recovered_records
            salvage["_recovered_record_count"] = len(recovered_records)

        # Pick up top-level scalars (anything BEFORE the first `[` is likely top-level)
        # so we still capture has_item19 / confidence / notes from the document head.
        first_bracket = cleaned.find("[")
        scan_region = cleaned[:first_bracket] if first_bracket > 0 else cleaned
        for m in re.finditer(r'"(\w+)"\s*:\s*("([^"\\]|\\.)*"|null|true|false|-?\d+(?:\.\d+)?)', scan_region):
            key, val = m.group(1), m.group(2)
            if key in salvage:
                continue
            try:
                salvage[key] = json.loads(val)
            except json.JSONDecodeError:
                continue
        return salvage


def _escape_internal_quotes(s: str) -> str:
    """State-machine repair: walk the input, escape any `"` that appears INSIDE
    a string but isn't followed by a JSON delimiter (`,` `}` `]` `:` or EOF).

    Handles the common model failure where verbatim FDD prose quoted with
    double quotes (e.g. "Initial Franchise Fee") ends up unescaped inside a
    JSON string value — making strict parse fail with "Expecting ',' delimiter".

    The look-ahead is conservative: we only call a `"` a closer when the next
    non-whitespace character is a JSON structural token. Anything else is
    treated as content and escaped.
    """
    out: list[str] = []
    i = 0
    n = len(s)
    in_string = False
    while i < n:
        ch = s[i]
        if not in_string:
            if ch == '"':
                in_string = True
            out.append(ch)
            i += 1
            continue
        # Inside a string
        if ch == "\\":
            # preserve escape sequence
            out.append(ch)
            if i + 1 < n:
                out.append(s[i + 1])
                i += 2
            else:
                i += 1
            continue
        if ch == '"':
            # Look ahead to decide: closer or internal?
            j = i + 1
            while j < n and s[j] in " \t\n\r":
                j += 1
            if j >= n or s[j] in ",}]:":
                # Closing quote
                in_string = False
                out.append(ch)
            else:
                # Internal unescaped quote — escape it
                out.append('\\"')
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _recover_array_elements(cleaned: str, key: str) -> list[dict] | None:
    """Find `"key": [` in cleaned, then walk forward extracting complete `{...}`
    objects until we either reach `]` (normal end) or run out of text
    (truncation). Returns list of dicts that JSON-parsed successfully.

    Used by the lenient parser to salvage records from a truncated array.
    """
    pattern = re.compile(r'"' + re.escape(key) + r'"\s*:\s*\[')
    m = pattern.search(cleaned)
    if not m:
        return None
    pos = m.end()  # right after the '['
    end_of_input = len(cleaned)
    records: list[dict] = []
    while pos < end_of_input:
        # Skip whitespace / commas
        while pos < end_of_input and cleaned[pos] in " \t\n\r,":
            pos += 1
        if pos >= end_of_input:
            break
        # End of array
        if cleaned[pos] == "]":
            break
        if cleaned[pos] != "{":
            # Unexpected character; stop here rather than churning
            break
        # Walk until matching '}' considering nested braces and strings
        depth = 0
        start = pos
        in_string = False
        escape = False
        while pos < end_of_input:
            ch = cleaned[pos]
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif in_string:
                if ch == '"':
                    in_string = False
            else:
                if ch == '"':
                    in_string = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        # complete object
                        obj_str = cleaned[start:pos + 1]
                        try:
                            records.append(json.loads(obj_str))
                        except json.JSONDecodeError:
                            # Try one repair pass (newlines / trailing commas)
                            r1 = re.sub(r",(\s*[}\]])", r"\1", obj_str)
                            r2 = re.sub(
                                r'"((?:[^"\\]|\\.)*?)"',
                                lambda mm: '"' + mm.group(1).replace("\n", "\\n").replace("\r", "\\r") + '"',
                                r1, flags=re.DOTALL,
                            )
                            try:
                                records.append(json.loads(r2))
                            except json.JSONDecodeError:
                                pass
                        pos += 1
                        break
            pos += 1
        else:
            # Hit end-of-input mid-object (truncation point) — stop cleanly
            break
    return records

load_dotenv()

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 8192
MAX_TOKENS_LARGE = 32000  # for items with long tabular output (e.g., Item 20 state-by-state)


@dataclass
class ExtractionResult:
    data: dict
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    cost_usd: float
    raw_text: str


def _cost(input_t: int, cached_t: int, output_t: int) -> float:
    # Sonnet 4.6 pricing as of 2026-05 (USD per million tokens). Update if MODEL changes.
    # See: https://www.anthropic.com/pricing
    p_in, p_cache_write, p_cache_read, p_out = 3.0, 3.75, 0.30, 15.0
    return (
        (input_t - cached_t) * p_in / 1_000_000
        + cached_t * p_cache_read / 1_000_000
        + output_t * p_out / 1_000_000
    )


def extract(
    system_prompt: str,
    user_prompt: str,
    images_b64: list[str] | None = None,
    *,
    cache_system: bool = True,
    max_tokens: int = MAX_TOKENS,
) -> ExtractionResult:
    """Run one extraction. Returns parsed JSON + token/cost stats."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    system = (
        [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}]
        if cache_system
        else [{"type": "text", "text": system_prompt}]
    )

    content: list[dict] = []
    if images_b64:
        for img in images_b64:
            content.append(
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/png", "data": img},
                }
            )
    content.append({"type": "text", "text": user_prompt})

    last_err = None
    resp = None
    use_stream = max_tokens > 8192
    for attempt in range(3):
        try:
            if use_stream:
                with client.messages.stream(
                    model=MODEL,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": content}],
                ) as stream:
                    for _ in stream.text_stream:
                        pass
                    resp = stream.get_final_message()
            else:
                resp = client.messages.create(
                    model=MODEL,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": content}],
                )
            break
        except (anthropic.APIError, anthropic.APIStatusError) as e:
            last_err = e
            time.sleep(2 ** attempt)
    if resp is None:
        raise last_err  # type: ignore[misc]

    raw = "".join(block.text for block in resp.content if hasattr(block, "text"))

    # The model is instructed to return raw JSON. Strip fences just in case.
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip().rstrip("`").strip()
    elif not (cleaned.startswith("{") or cleaned.startswith("[")):
        # Model occasionally produces prose preamble before the JSON
        # (e.g. "I can see the document contains... \n{...}"). The cleaner
        # used to fail-through this case → parse error at char 0 → salvage.
        # Find the first JSON-shaped block and parse from there.
        # We pick the EARLIEST { or [ and trust the trailing-content stripper
        # at parse-time to handle any garbage after.
        first_brace = cleaned.find("{")
        first_bracket = cleaned.find("[")
        candidates = [p for p in (first_brace, first_bracket) if p >= 0]
        if candidates:
            cleaned = cleaned[min(candidates):]
            # Strip trailing fence if model added one after the JSON
            cleaned = cleaned.rstrip().rstrip("`").rstrip()

    data = _parse_json_lenient(cleaned, raw)

    usage = resp.usage
    in_t = getattr(usage, "input_tokens", 0)
    out_t = getattr(usage, "output_tokens", 0)
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
    # Total input billed = uncached + cache_write_at_125% + cache_read_at_10%
    total_in_for_cost = in_t + cache_write  # cache_write is reported separately from input_tokens
    cost = _cost(total_in_for_cost, cache_read, out_t) + cache_write * 0.75 / 1_000_000

    return ExtractionResult(
        data=data,
        input_tokens=in_t + cache_write,
        cached_input_tokens=cache_read,
        output_tokens=out_t,
        cost_usd=cost,
        raw_text=raw,
    )
