"""Single-prompt text-only extractor (v2) — target <$0.25/FDD.

Architectural shift from extract_loop.py:
- No tool use (no Read, no Write tool calls). Cumulative cache-read tax eliminated.
- Pre-extract all section TEXT in Python via pdf_utils.
- Inline schemas + section text in ONE prompt.
- Call claude -p with --model haiku (3x cheaper than Sonnet).
- Parse JSON response → write 6 files in Python.

Trade-off: text-only loses some visual table fidelity. Acceptable for most fields;
quality measured against v1 outputs on a sample.

Usage:
    uv run python scripts/extract_v2.py PDF_PATH
    uv run python scripts/extract_v2.py PDF_PATH --model sonnet  # fallback if Haiku fails
    uv run python scripts/extract_v2.py --batch  # process all pending PDFs

Outputs are written to output/{stem}/ same as the v1 loop.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from src import pdf_utils
sys.path.insert(0, "scripts")
from _pdf_dedup import extract_content_key

PDF_DIR = Path("data/wi_scrape")
OUTPUT_DIR = Path("output")
PROMPTS_PY = Path("src/prompts.py")
MANIFEST = OUTPUT_DIR / "_extract_v2.json"
CLAUDE_BIN = r"C:\Users\joshs\.local\bin\claude.exe"
PER_INVOCATION_TIMEOUT_SEC = 600


def build_sections(pdf_path: Path) -> dict:
    """Pre-extract all section text + metadata. Pure Python, ~200ms."""
    pages = pdf_utils.extract_pages(pdf_path)
    body = pdf_utils.find_fdd_body_start(pages)
    cover = pdf_utils.find_cover_page(pages)
    section_ranges = {
        "item5": pdf_utils.find_section(pages, 5, body),
        "item6": pdf_utils.find_section(pages, 6, body),
        "item7": pdf_utils.find_section(pages, 7, body),
        "item19": pdf_utils.find_section(pages, 19, body),
        "item20": pdf_utils.find_section(pages, 20, body),
    }
    # Cover page text (for metadata)
    cover_text = pdf_utils.section_text(pages, cover, min(cover + 2, len(pages)))
    section_texts = {
        "cover": cover_text,
        "item5": pdf_utils.section_text(pages, *section_ranges["item5"]) if section_ranges["item5"] else "",
        "item6": pdf_utils.section_text(pages, *section_ranges["item6"]) if section_ranges["item6"] else "",
        "item7": pdf_utils.section_text(pages, *section_ranges["item7"]) if section_ranges["item7"] else "",
        "item19": pdf_utils.section_text(pages, *section_ranges["item19"]) if section_ranges["item19"] else "",
        "item20": pdf_utils.section_text(pages, *section_ranges["item20"]) if section_ranges["item20"] else "",
    }
    # Pre-scan Item 19 for the no-FPR phrase
    item19_no_fpr = False
    i19_lower = section_texts["item19"].lower()
    for phrase in (
        "we do not make any representation",
        "we do not make any financial performance representation",
        "no representations of historical or projected",
        "we are not making any representation",
        "we do not furnish or authorize",
    ):
        if phrase in i19_lower:
            item19_no_fpr = True
            break
    # Pull legal_name + effective_date from cover via _pdf_dedup
    known_meta = {}
    ck = extract_content_key(pdf_path)
    if ck:
        known_meta = {
            "legal_name": ck.get("legal_name"),
            "effective_date": ck.get("effective_date"),
        }
    return {
        "section_ranges": section_ranges,
        "section_texts": section_texts,
        "item19_no_fpr": item19_no_fpr,
        "known_meta": known_meta,
        "page_count": len(pages),
    }


def build_prompt(stem: str, info: dict) -> str:
    """Build a single self-contained prompt. No tool use needed."""
    schemas = PROMPTS_PY.read_text(encoding="utf-8")
    texts = info["section_texts"]
    known = info["known_meta"]
    no_fpr = info["item19_no_fpr"]

    # Truncate sections to control input cost — 25k chars (~6k tokens) per section is plenty
    MAX_CHARS = 25_000
    item19_block = ""
    if no_fpr:
        item19_block = (
            "## Item 19 (FPR) — PRE-DETECTED: NO FPR\n\n"
            "The section explicitly states the franchisor does not make financial "
            "performance representations. Output `{\"has_item19\": false, \"records\": [], "
            "\"confidence\": 0.95, \"notes\": \"explicit no-FPR\"}` for item19.\n\n"
        )
    else:
        item19_block = (
            f"## Item 19 (Financial Performance Representations)\n\n"
            f"{texts['item19'][:MAX_CHARS]}\n\n"
        )

    return (
        "Extract structured data from this US Franchise Disclosure Document. "
        "Output ONE JSON object — no prose, no markdown fences.\n\n"
        f"# Schemas\n\n```python\n{schemas}\n```\n\n"
        f"# Known facts (use directly; do NOT re-extract)\n\n"
        f"```json\n{json.dumps(known)}\n```\n\n"
        f"# Section text (verbatim from FDD)\n\n"
        f"## Cover\n{texts['cover'][:6_000]}\n\n"
        f"## Item 5\n{texts['item5'][:MAX_CHARS]}\n\n"
        f"## Item 6\n{texts['item6'][:MAX_CHARS]}\n\n"
        f"## Item 7\n{texts['item7'][:MAX_CHARS]}\n\n"
        f"{item19_block}"
        f"## Item 20\n{texts['item20'][:MAX_CHARS]}\n\n"
        "# Output\n\n"
        "ONE JSON object with keys: metadata, item5, item6, item7, item19, item20.\n"
        "Each follows the matching *_PROMPT schema.\n"
        "Item 19 no-FPR case: {\"has_item19\": false, \"records\": [], \"confidence\": 0.95, \"notes\": \"explicit no-FPR\"}.\n"
        "Missing section: {\"_section_not_found\": true}.\n\n"
        "## COMPACT OUTPUT — token budget rules\n"
        "- OMIT fields you'd set to null. Don't write `\"field_name\": null`.\n"
        "- OMIT `raw_excerpt` unless directly relevant (>50% of fields are clearly stated).\n"
        "- OMIT `notes` and `raw_text` when value is unambiguous.\n"
        "- For Item 19 records, omit any quartile/distribution fields the FDD doesn't report.\n"
        "- Use minified JSON if possible (no extra whitespace). The post-parser handles both.\n"
        "- Skip prose entirely — JSON ONLY."
    )


def call_claude(prompt: str, model: str = "haiku") -> tuple[bool, str, dict, int]:
    """Single-shot call to claude -p. Returns (ok, result_text, usage, elapsed_sec).
    Prompt is piped via stdin to avoid Windows command-line length limits (~32k chars)."""
    t0 = time.time()
    cmd = [
        CLAUDE_BIN,
        "-p",
        "--model", model,
        "--output-format", "json",
        "--input-format", "text",
        # No --allowedTools because we're not using tools at all
        "--exclude-dynamic-system-prompt-sections",
        "--effort", "low",
    ]
    clean_env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              input=prompt, encoding="utf-8",
                              timeout=PER_INVOCATION_TIMEOUT_SEC, env=clean_env)
        elapsed = int(time.time() - t0)
        envelope = {}
        result_text = ""
        usage = {}
        try:
            envelope = json.loads(proc.stdout)
            result_text = envelope.get("result", "")
            usage = envelope.get("usage", {}) or {}
            for k in ("total_cost_usd", "duration_ms", "num_turns"):
                if k in envelope:
                    usage[k] = envelope[k]
        except json.JSONDecodeError:
            result_text = proc.stdout
        ok = proc.returncode == 0 and bool(result_text.strip())
        return ok, result_text, usage, elapsed
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT", {}, PER_INVOCATION_TIMEOUT_SEC


def parse_and_write(stem: str, raw: str) -> tuple[bool, str]:
    """Parse the JSON response, write 6 output files. Returns (ok, reason)."""
    # Strip any markdown fences if claude ignored instructions
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # remove leading and trailing fences
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    try:
        bundle = json.loads(cleaned)
    except json.JSONDecodeError as e:
        # Try to find the largest valid JSON object in the response
        start = cleaned.find("{")
        if start < 0:
            return False, f"no JSON object found: {e}"
        try:
            bundle = json.loads(cleaned[start:])
        except json.JSONDecodeError:
            return False, f"JSON parse failed: {e}"

    out_dir = OUTPUT_DIR / stem
    out_dir.mkdir(parents=True, exist_ok=True)

    keymap = {
        "metadata": "metadata.json",
        "item5": "item5_initial_fee.json",
        "item6": "item6_ongoing_fees.json",
        "item7": "item7_investment.json",
        "item19": "item19_fpr.json",
        "item20": "item20_outlets.json",
    }
    for key, fname in keymap.items():
        data = bundle.get(key, {"_section_not_found": True})
        (out_dir / fname).write_text(json.dumps(data, indent=2), encoding="utf-8")

    # Validate metadata
    meta = bundle.get("metadata", {})
    if not (meta.get("legal_name") or meta.get("brand_name")):
        return False, "metadata missing legal_name and brand_name"
    return True, "ok"


def load_manifest() -> dict:
    if MANIFEST.exists():
        try:
            return json.loads(MANIFEST.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"extractions": {}}


def save_manifest(m: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(m, indent=2), encoding="utf-8")


def extract_one(pdf: Path, model: str = "haiku") -> dict:
    """Extract one PDF. Returns the manifest entry."""
    info = build_sections(pdf)
    prompt = build_prompt(pdf.stem, info)
    prompt_chars = len(prompt)
    ok, result, usage, elapsed = call_claude(prompt, model=model)

    entry = {
        "last_attempt_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_sec": elapsed,
        "model": model,
        "prompt_chars": prompt_chars,
        "page_count": info["page_count"],
        "item19_no_fpr": info["item19_no_fpr"],
    }
    if usage:
        entry["usage"] = usage

    if not ok:
        entry["ok"] = False
        entry["error"] = result[-500:] if result else "unknown"
        return entry

    parse_ok, reason = parse_and_write(pdf.stem, result)
    entry["ok"] = parse_ok
    entry["parse_reason"] = reason
    return entry


def main():
    p = argparse.ArgumentParser()
    p.add_argument("pdf", nargs="?", help="PDF path (single mode)")
    p.add_argument("--batch", action="store_true", help="Process all pending PDFs")
    p.add_argument("--model", default="haiku", help="claude model alias (haiku, sonnet, opus)")
    p.add_argument("--limit", type=int, default=10, help="Max PDFs in batch mode")
    args = p.parse_args()

    manifest = load_manifest()

    if args.batch:
        # Discover pending: PDFs without output/{stem}/metadata.json
        pending = []
        for pdf in sorted(PDF_DIR.glob("*.pdf")):
            meta = OUTPUT_DIR / pdf.stem / "metadata.json"
            if not meta.exists():
                pending.append(pdf)
            elif pdf.stem in manifest["extractions"] and manifest["extractions"][pdf.stem].get("ok"):
                continue  # already done by v2
        pending = pending[:args.limit]
        print(f"Processing {len(pending)} PDFs with model={args.model}\n")
        total_cost = 0.0
        ok_count = 0
        fail_count = 0
        for i, pdf in enumerate(pending, 1):
            print(f"[{i}/{len(pending)}] {pdf.name}")
            entry = extract_one(pdf, model=args.model)
            manifest["extractions"][pdf.stem] = entry
            save_manifest(manifest)
            usage = entry.get("usage") or {}
            cost = usage.get("total_cost_usd")
            cost_str = f"${cost:.4f}" if cost is not None else "n/a"
            if entry["ok"]:
                ok_count += 1
                total_cost += cost or 0
                print(f"  -> OK ({entry['elapsed_sec']}s, {cost_str})")
            else:
                fail_count += 1
                err = entry.get("parse_reason") or entry.get("error", "?")
                print(f"  -> FAILED ({entry['elapsed_sec']}s): {err[:120]}")
        print()
        if ok_count > 0:
            avg = total_cost / ok_count
            print(f"SUMMARY: {ok_count} ok, {fail_count} failed, total ${total_cost:.4f}, avg ${avg:.4f}/FDD")
    elif args.pdf:
        pdf = Path(args.pdf)
        if not pdf.exists():
            print(f"PDF not found: {pdf}"); sys.exit(1)
        print(f"Processing {pdf.name} with model={args.model}")
        entry = extract_one(pdf, model=args.model)
        manifest["extractions"][pdf.stem] = entry
        save_manifest(manifest)
        usage = entry.get("usage") or {}
        cost = usage.get("total_cost_usd")
        print(json.dumps(entry, indent=2))
        if entry["ok"]:
            print(f"\nOK in {entry['elapsed_sec']}s, cost ${cost:.4f}" if cost else f"\nOK in {entry['elapsed_sec']}s")
    else:
        p.print_help(); sys.exit(1)


if __name__ == "__main__":
    main()
