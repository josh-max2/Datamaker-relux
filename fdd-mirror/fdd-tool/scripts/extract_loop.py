"""Continuous extract loop using `claude -p` subprocess (Max plan tokens, not API).

Watches data/wi_scrape/ for PDFs that don't yet have a corresponding output/{stem}/
metadata.json. For each such PDF, spawns a fresh `claude -p` session with explicit
instructions to extract Items 5/6/7/19/20 + metadata and write 6 JSON files. The
spawned Claude session does the LLM work using Read + Write tools — no API calls.

Run in its own PowerShell:
    uv run python scripts/extract_loop.py

Companion: scripts/scrape_loop.py runs in another PowerShell and feeds the data/ dir.

Cost model:
  - Per invocation: ~15k tokens overhead (CLAUDE.md/memory) + ~50k tokens for extraction work
  - Uses Max plan subscription tokens, NOT API credits
  - Max plan window: ~500k-1M tokens per 5-hour window (varies)
  - Realistic throughput: 7-15 brands per window, then waits for window to refresh
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PDF_DIR = Path("data/wi_scrape")
OUTPUT_DIR = Path("output")
INSTRUCTIONS_FILE = Path("scripts/_extract_instructions.md").resolve()
MANIFEST = Path("output/_extract_loop.json")
SHA_TO_STEM = Path("output/_sha_to_stem.json")           # dedup index: sha256 -> stem
CONTENT_TO_STEM = Path("output/_content_to_stem.json")    # content dedup: {full_key|year_key} -> stem
CLAUDE_BIN = r"C:\Users\joshs\.local\bin\claude.exe"
UV_BIN = "C:/Users/joshs/AppData/Roaming/Python/Python312/Scripts/uv.exe"
PER_INVOCATION_TIMEOUT_SEC = 600
POLL_INTERVAL_SEC = 30
INGEST_EVERY_N = 5


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_likely_fdd(pdf_path: Path) -> tuple[bool, str]:
    """Pre-flight check: does the PDF actually look like an FDD?
    Costs ~10ms and zero LLM tokens. Catches malformed downloads, error pages
    saved as PDF, wrong-document scrapes, etc. before we pay for extraction.

    Returns (is_fdd, reason). If is_fdd is False, the reason is logged in the manifest.
    Conservative: if we can't tell, return True so the LLM gets a chance.
    """
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        if len(reader.pages) < 5:
            return False, f"only {len(reader.pages)} pages — real FDDs are 100+"
        # Scan first 3 pages for the FDD header (varies in case + spacing)
        text = ""
        for i in range(min(3, len(reader.pages))):
            try:
                text += (reader.pages[i].extract_text() or "")
            except Exception:
                pass
        text_upper = text.upper()
        if "FRANCHISE DISCLOSURE DOCUMENT" not in text_upper:
            # Could also accept "FRANCHISE OFFERING CIRCULAR" (pre-2008 term, very rare now)
            if "FRANCHISE OFFERING CIRCULAR" not in text_upper:
                return False, "no FDD header in first 3 pages"
        # Tiny PDFs that have the header but no substance are also bad
        size_mb = pdf_path.stat().st_size / 1024 / 1024
        if size_mb < 0.3:
            return False, f"only {size_mb:.2f} MB — real FDDs are 1-30 MB"
        return True, "ok"
    except Exception as e:
        # Don't block on parse errors — let the LLM try
        return True, f"preflight failed: {e!r}"


def validate_extraction(stem: str) -> tuple[bool, str]:
    """Post-extraction sanity check. Catches broken extractions that
    technically wrote metadata.json but produced unusable output."""
    out_dir = OUTPUT_DIR / stem
    needed = [
        "metadata.json",
        "item5_initial_fee.json",
        "item6_ongoing_fees.json",
        "item7_investment.json",
        "item19_fpr.json",
        "item20_outlets.json",
    ]
    for fname in needed:
        p = out_dir / fname
        if not p.exists():
            return False, f"missing {fname}"
        # Allow JSON parse errors — ingest_outputs.py has a lenient parser fallback
        # But if the file is empty or tiny, that's a real failure
        size = p.stat().st_size
        if size < 5:
            return False, f"{fname} is empty (size={size})"
    # Metadata must have core fields
    try:
        meta = json.loads((out_dir / "metadata.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return False, f"metadata.json invalid JSON: {e}"
    if not (meta.get("legal_name") or meta.get("brand_name")):
        return False, "metadata.json missing legal_name and brand_name"
    return True, "ok"


def load_sha_index() -> dict[str, str]:
    if SHA_TO_STEM.exists():
        try:
            return json.loads(SHA_TO_STEM.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_sha_index(idx: dict[str, str]) -> None:
    SHA_TO_STEM.write_text(json.dumps(idx, indent=2), encoding="utf-8")


def load_content_index() -> dict[str, str]:
    if CONTENT_TO_STEM.exists():
        try:
            return json.loads(CONTENT_TO_STEM.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_content_index(idx: dict[str, str]) -> None:
    CONTENT_TO_STEM.write_text(json.dumps(idx, indent=2), encoding="utf-8")


def copy_existing_extraction(src_stem: str, dst_stem: str) -> bool:
    """When a SHA match is found, copy the existing extraction outputs to the new stem dir.
    Returns True on success."""
    src_dir = OUTPUT_DIR / src_stem
    dst_dir = OUTPUT_DIR / dst_stem
    if not src_dir.is_dir():
        return False
    if dst_dir.exists():
        return True  # already populated somehow
    try:
        shutil.copytree(src_dir, dst_dir)
        # Mark as dedup-copied so we can audit later
        marker = dst_dir / "_dedup_source.json"
        marker.write_text(json.dumps({
            "copied_from": src_stem,
            "copied_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "reason": "sha256_match",
        }, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        print(f"  [dedup-copy] failed: {e}")
        return False


def load_manifest() -> dict:
    if MANIFEST.exists():
        try:
            return json.loads(MANIFEST.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"started_at": time.strftime("%Y-%m-%d %H:%M:%S"), "extractions": {}}
    return {"started_at": time.strftime("%Y-%m-%d %H:%M:%S"), "extractions": {}}


def save_manifest(m: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(m, indent=2), encoding="utf-8")


def needs_extraction(pdf: Path) -> bool:
    """A PDF needs extraction if output/{stem}/metadata.json doesn't exist yet."""
    meta = OUTPUT_DIR / pdf.stem / "metadata.json"
    return not meta.exists()


def discover_pending() -> list[Path]:
    if not PDF_DIR.exists():
        return []
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    return [p for p in pdfs if needs_extraction(p)]


def precompute_pdf_facts(pdf_path: Path) -> dict:
    """Pre-compute everything we can deterministically before invoking claude.
    Reduces tokens per extraction by ~5-8k. Costs ~200ms in Python.

    Returns a dict with:
      - sections: {cover, item5, item6, item7, item19, item20} -> (start, end) | None
      - item19_no_fpr: bool — True if Item 19 section contains the standard no-FPR phrase
      - body_start: int
      - page_count: int
      - known_metadata: dict — legal_name, effective_date (from _pdf_dedup if available)
    """
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from src import pdf_utils
        pages = pdf_utils.extract_pages(pdf_path)
        body = pdf_utils.find_fdd_body_start(pages)
        cover = pdf_utils.find_cover_page(pages)
        sections = {
            "cover": cover,
            "item5": pdf_utils.find_section(pages, 5, body),
            "item6": pdf_utils.find_section(pages, 6, body),
            "item7": pdf_utils.find_section(pages, 7, body),
            "item19": pdf_utils.find_section(pages, 19, body),
            "item20": pdf_utils.find_section(pages, 20, body),
        }
        # Pre-scan Item 19 for the no-FPR phrase so claude can skip it entirely
        item19_no_fpr = False
        if sections["item19"]:
            i19_text = pdf_utils.section_text(pages, sections["item19"][0], sections["item19"][1])
            i19_lower = i19_text.lower()
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
        # Known metadata from pdf_dedup (avoids claude re-extracting)
        known_metadata = {}
        try:
            from scripts._pdf_dedup import extract_content_key
            ck = extract_content_key(pdf_path)
            if ck:
                known_metadata = {
                    "legal_name": ck.get("legal_name"),
                    "effective_date": ck.get("effective_date"),
                }
        except Exception:
            pass
        return {
            "sections": sections,
            "item19_no_fpr": item19_no_fpr,
            "body_start": body,
            "page_count": len(pages),
            "known_metadata": known_metadata,
        }
    except Exception as e:
        # If pre-compute fails, return empty so claude falls back to doing it itself
        return {"_precompute_error": repr(e)}


# Read prompts.py ONCE at module load — schemas don't change across invocations.
# Inlining them into the prompt eliminates a ~2000-token Read inside each claude session.
_PROMPTS_PY_CONTENT = None
def get_inlined_schemas() -> str:
    global _PROMPTS_PY_CONTENT
    if _PROMPTS_PY_CONTENT is None:
        prompts_path = Path(__file__).resolve().parents[1] / "src" / "prompts.py"
        _PROMPTS_PY_CONTENT = prompts_path.read_text(encoding="utf-8")
    return _PROMPTS_PY_CONTENT


def build_prompt(pdf_path: Path, facts: dict) -> str:
    """One-shot prompt with EVERYTHING claude needs already pre-computed:
      - PDF path
      - Section page ranges (no need to run Bash)
      - Item 19 no-FPR detection (skip section if True)
      - Schemas (inlined, no need to Read prompts.py)
      - Known metadata (legal_name, effective_date)
    """
    instructions = INSTRUCTIONS_FILE.read_text(encoding="utf-8")
    instructions = instructions.replace("PDF_PATH_HERE", str(pdf_path).replace("\\", "/"))
    instructions = instructions.replace("{PDF_STEM}", pdf_path.stem)
    instructions = instructions.replace("{STEM}", pdf_path.stem)

    schemas = get_inlined_schemas()
    facts_json = json.dumps(facts, default=str, indent=2)

    prompt = (
        f"Process the FDD at `{pdf_path}` using the instructions below. "
        f"When done, write to disk only — don't run ingest or site regeneration "
        f"(orchestrator handles those). Print EXTRACTION_DONE when finished.\n\n"
        f"## Pre-computed facts (use these — do NOT re-derive)\n\n"
        f"```json\n{facts_json}\n```\n\n"
        f"Skip the Bash command in the instructions — section boundaries are above.\n"
        f"Skip the 'Read src/prompts.py' step — schemas are inlined below.\n"
        f"If `item19_no_fpr` is true, write the no-FPR JSON for item19_fpr.json "
        f"and do not read the Item 19 pages at all.\n\n"
        f"## Schemas (from src/prompts.py)\n\n"
        f"```python\n{schemas}\n```\n\n"
        f"## Original instructions\n\n"
        + instructions
    )
    return prompt


def invoke_claude(pdf_path: Path, facts: dict) -> tuple[bool, str, int, dict]:
    """Run a fresh `claude -p` session for one PDF.

    Returns (success, stdout_tail, elapsed_sec, usage_stats).
    usage_stats is a dict with input_tokens, output_tokens, cache_creation/read tokens.

    Critical: we scrub ANTHROPIC_API_KEY from the env so the spawned claude MUST use
    OAuth/keychain auth (the user's Max-plan login). This prevents accidental API spend.
    """
    import os
    prompt = build_prompt(pdf_path, facts)
    t0 = time.time()
    project_root = Path.cwd().resolve()
    cmd = [
        CLAUDE_BIN,
        "-p",
        "--model", "haiku",                          # Haiku for v1 fallback — 3-5x cheaper than Sonnet
        "--output-format", "json",                   # structured response incl. usage stats
        "--allowedTools", "Read", "Write",            # Bash dropped — sections pre-computed
        "--add-dir", str(project_root),
        "--exclude-dynamic-system-prompt-sections",  # better prompt-cache reuse
        "--effort", "low",                            # minimize thinking tokens
        prompt,
    ]
    # Scrub API key from env — force OAuth/Max-plan auth
    clean_env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=PER_INVOCATION_TIMEOUT_SEC,
            cwd=str(project_root),
            env=clean_env,
        )
        elapsed = int(time.time() - t0)
        out_tail = (proc.stdout + proc.stderr)[-3000:]

        # Parse the JSON result envelope (--output-format=json)
        usage = {}
        result_text = ""
        rate_limited = False
        try:
            envelope = json.loads(proc.stdout)
            result_text = envelope.get("result", "")
            usage = envelope.get("usage", {}) or {}
            # Some implementations put cost/usage at the top level too
            for k in ("total_cost_usd", "duration_ms", "num_turns"):
                if k in envelope:
                    usage[k] = envelope[k]
            if envelope.get("subtype") and "rate_limit" in str(envelope.get("subtype")).lower():
                rate_limited = True
        except json.JSONDecodeError:
            # Fall back to plain-text mode parsing
            result_text = proc.stdout

        # Detect rate-limit messages (Max-plan window exhausted)
        haystack = (out_tail + result_text).lower()
        if any(p in haystack for p in (
            "rate limit", "rate_limit", "usage_limit_exceeded", "5-hour",
            "5 hour", "exhausted", "approaching the limit", "quota",
        )):
            rate_limited = True

        success = (
            proc.returncode == 0
            and "EXTRACTION_DONE" in result_text
            and (OUTPUT_DIR / pdf_path.stem / "metadata.json").exists()
        )
        usage["rate_limited"] = rate_limited
        return success, out_tail, elapsed, usage
    except subprocess.TimeoutExpired:
        return False, f"TIMEOUT after {PER_INVOCATION_TIMEOUT_SEC}s", PER_INVOCATION_TIMEOUT_SEC, {}


def reingest_and_regen() -> None:
    """Re-ingest all extractions and regenerate the site. Called periodically."""
    try:
        subprocess.run([UV_BIN, "run", "python", "scripts/ingest_outputs.py"],
                       capture_output=True, text=True, timeout=300)
        subprocess.run([UV_BIN, "run", "python", "-m", "src.site_gen"],
                       capture_output=True, text=True, timeout=180)
        print(f"  [orchestrator] re-ingested + regenerated site")
    except Exception as e:
        print(f"  [orchestrator] re-ingest/regen error: {e}")


def main() -> None:
    print(f"=== extract_loop starting ===")
    print(f"  PDF dir: {PDF_DIR.resolve()}")
    print(f"  Output:  {OUTPUT_DIR.resolve()}")
    print(f"  Claude:  {CLAUDE_BIN}")
    print(f"  Timeout: {PER_INVOCATION_TIMEOUT_SEC}s per invocation")
    print(f"  Re-ingest every {INGEST_EVERY_N} successful extractions")
    print(f"  Stop with Ctrl-C; safe to resume — work-in-progress is per-file\n")

    manifest = load_manifest()
    sha_index = load_sha_index()
    content_index = load_content_index()
    success_count_since_ingest = 0
    total_success = sum(1 for e in manifest["extractions"].values() if e.get("ok"))
    total_failed = sum(1 for e in manifest["extractions"].values() if not e.get("ok"))
    total_deduped = sum(1 for e in manifest["extractions"].values() if e.get("dedup_copied_from"))

    while True:
        pending = discover_pending()
        if not pending:
            print(f"[idle] no pending PDFs (ok={total_success} failed={total_failed} deduped={total_deduped}); "
                  f"sleeping {POLL_INTERVAL_SEC}s")
            time.sleep(POLL_INTERVAL_SEC)
            continue

        pdf = pending[0]

        # ----- Free dedup check #1: SHA-256 (catches byte-identical PDFs) -----
        sha = file_sha256(pdf)
        if sha in sha_index and sha_index[sha] != pdf.stem:
            src = sha_index[sha]
            if copy_existing_extraction(src, pdf.stem):
                total_deduped += 1
                manifest["extractions"][pdf.stem] = {
                    "last_attempt_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "ok": True,
                    "dedup_copied_from": src,
                    "dedup_method": "sha256",
                    "sha256": sha,
                    "elapsed_sec": 0,
                    "cost_avoided": True,
                }
                save_manifest(manifest)
                print(f"[{time.strftime('%H:%M:%S')}] {pdf.name}: DEDUP-SHA — copied from {src}")
                continue

        # ----- Free dedup check #2: content key (legal_name + effective_date) -----
        # Catches multi-state filings of the same FDD where the bytes differ but
        # the underlying franchisor + filing date are identical. Costs ~10ms.
        content_key = None
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from _pdf_dedup import extract_content_key as _eck
            content_key = _eck(pdf)
        except Exception as e:
            print(f"  [content-dedup] extraction failed (proceeding with full extract): {e!r}")

        if content_key:
            # Try full key (slug + exact date) first, then year fallback
            for key_field in ("full_key", "year_key"):
                key = content_key.get(key_field)
                if not key:
                    continue
                if key in content_index and content_index[key] != pdf.stem:
                    src = content_index[key]
                    if copy_existing_extraction(src, pdf.stem):
                        total_deduped += 1
                        manifest["extractions"][pdf.stem] = {
                            "last_attempt_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "ok": True,
                            "dedup_copied_from": src,
                            "dedup_method": f"content_{key_field}",
                            "content_key": key,
                            "legal_name": content_key.get("legal_name"),
                            "effective_date": content_key.get("effective_date"),
                            "sha256": sha,
                            "elapsed_sec": 0,
                            "cost_avoided": True,
                        }
                        save_manifest(manifest)
                        print(f"[{time.strftime('%H:%M:%S')}] {pdf.name}: DEDUP-CONTENT ({key_field}) "
                              f"— matched {src} via {content_key.get('legal_name')} / "
                              f"{content_key.get('effective_date') or content_key.get('year')}")
                        break
            else:
                # No match found in either key — fall through to LLM extraction
                pass
            # Re-check whether we just deduped (set entry in manifest)
            if manifest["extractions"].get(pdf.stem, {}).get("dedup_copied_from"):
                continue
        # Skip if previously failed in a way that wouldn't recover
        prev = manifest["extractions"].get(pdf.stem)
        if prev and prev.get("attempt_count", 0) >= 3 and not prev.get("ok"):
            print(f"[skip-perm] {pdf.name}: failed 3+ times, skipping")
            # Mark with a sentinel so we don't loop over it
            (OUTPUT_DIR / pdf.stem).mkdir(parents=True, exist_ok=True)
            (OUTPUT_DIR / pdf.stem / "metadata.json").write_text(
                json.dumps({"_extraction_skipped": True, "_reason": "max_attempts_exceeded"}, indent=2),
                encoding="utf-8")
            continue

        # ----- Pre-flight #3: PDF must look like an actual FDD -----
        # Catches malformed downloads, error pages, wrong-doc scrapes BEFORE we pay
        # for a claude invocation. ~10ms cost, can save $0.30-0.50 per skip.
        is_fdd, fdd_reason = is_likely_fdd(pdf)
        if not is_fdd:
            print(f"[skip-bad-pdf] {pdf.name}: {fdd_reason}")
            (OUTPUT_DIR / pdf.stem).mkdir(parents=True, exist_ok=True)
            (OUTPUT_DIR / pdf.stem / "metadata.json").write_text(
                json.dumps({"_extraction_skipped": True, "_reason": f"not_an_fdd: {fdd_reason}"}, indent=2),
                encoding="utf-8")
            manifest["extractions"][pdf.stem] = {
                "last_attempt_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "ok": False,
                "preflight_failed": True,
                "preflight_reason": fdd_reason,
                "elapsed_sec": 0,
                "cost_avoided": True,
            }
            save_manifest(manifest)
            continue

        print(f"[{time.strftime('%H:%M:%S')}] processing {pdf.name}...")
        # === v2 PATH: single-prompt text-only on Haiku (~$0.14/FDD avg) ===
        # Try v2 first; fall back to v1 (multi-turn vision) if v2 returns
        # empty sections (pdf_utils section detection failed).
        try:
            from extract_v2 import extract_one as v2_extract
            v2_entry = v2_extract(pdf, model="haiku")
            v2_usage = v2_entry.get("usage", {}) or {}
            v2_ok = v2_entry.get("ok", False)
            v2_cost = v2_usage.get("total_cost_usd", 0)
            v2_elapsed = v2_entry.get("elapsed_sec", 0)
            # Quality check: did v2 actually pull the data, or did it return
            # honest-but-empty results due to image-only tables or section detection misses?
            # Fallback triggers when ANY of:
            #   - Item 5, 7, or 20 returned _section_not_found
            #   - Item 19 has has_item19=true but records=[] with confidence < 0.6
            #     (table-as-image case — Haiku saw FPR exists but couldn't read the values)
            from pathlib import Path as _P
            v2_useful = False
            if v2_ok:
                stem_out = _P(f"output/{pdf.stem}")
                quality_issues = []
                # Critical sections must not be missing
                for fname, key in (
                    ("item5_initial_fee.json", "Item 5"),
                    ("item7_investment.json", "Item 7"),
                    ("item20_outlets.json", "Item 20"),
                ):
                    fpath = stem_out / fname
                    if fpath.exists():
                        try:
                            data = json.loads(fpath.read_text(encoding="utf-8"))
                            if data.get("_section_not_found"):
                                quality_issues.append(f"{key} not found")
                        except Exception:
                            quality_issues.append(f"{key} unparseable")
                # Item 19: if has_item19=true but no records + low confidence, tables were images
                i19_path = stem_out / "item19_fpr.json"
                if i19_path.exists():
                    try:
                        i19 = json.loads(i19_path.read_text(encoding="utf-8"))
                        if (i19.get("has_item19") is True
                                and not i19.get("records")
                                and (i19.get("confidence") or 0) < 0.6):
                            quality_issues.append("Item 19 tables are image-only (text extraction lost data)")
                    except Exception:
                        pass
                v2_useful = not quality_issues
                if quality_issues:
                    print(f"  -> v2 quality issues: {'; '.join(quality_issues)}; falling back to v1")
            if v2_ok and v2_useful:
                # v2 success — record + continue
                print(f"  -> OK v2 (haiku, {v2_elapsed}s, ${v2_cost:.4f})")
                manifest["extractions"][pdf.stem] = {
                    "last_attempt_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "ok": True,
                    "extractor": "v2",
                    "model": "haiku",
                    "usage": v2_usage,
                    "elapsed_sec": v2_elapsed,
                    "attempt_count": (manifest["extractions"].get(pdf.stem, {}).get("attempt_count", 0) + 1),
                }
                save_manifest(manifest)
                total_success += 1
                success_count_since_ingest += 1
                if content_key:
                    for key_field in ("full_key", "year_key"):
                        k = content_key.get(key_field)
                        if k and k not in content_index:
                            content_index[k] = pdf.stem
                    save_content_index(content_index)
                sha_index[sha] = pdf.stem
                save_sha_index(sha_index)
                if success_count_since_ingest >= INGEST_EVERY_N:
                    reingest_and_regen()
                    success_count_since_ingest = 0
                continue
            else:
                print(f"  -> v2 inconclusive (ok={v2_ok}, useful={v2_useful}); falling back to v1")
        except Exception as e:
            print(f"  -> v2 errored ({e!r}); falling back to v1")

        # === v1 fallback: multi-turn vision via claude -p ===
        # Pre-compute everything we can — section boundaries, no-FPR detection,
        # known metadata — to reduce tokens claude needs to spend.
        facts = precompute_pdf_facts(pdf)
        if facts.get("item19_no_fpr"):
            print(f"  [precompute] Item 19 is no-FPR; claude will skip those pages")
        if "_precompute_error" in facts:
            print(f"  [precompute] WARN: {facts['_precompute_error']!r}")
        success, out_tail, elapsed, usage = invoke_claude(pdf, facts)
        entry = manifest["extractions"].get(pdf.stem, {})
        entry["last_attempt_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        entry["elapsed_sec"] = elapsed
        entry["last_output_tail"] = out_tail
        # Capture per-invocation usage stats (input/output/cache tokens, cost)
        if usage:
            entry["usage"] = {k: v for k, v in usage.items() if k != "rate_limited"}

        # Rate-limit handling: DON'T increment attempt_count when the Max-plan
        # window is exhausted (we'll retry when the window refreshes)
        if usage.get("rate_limited") and not success:
            entry["rate_limited_count"] = entry.get("rate_limited_count", 0) + 1
            entry["ok"] = False
            manifest["extractions"][pdf.stem] = entry
            save_manifest(manifest)
            print(f"  -> RATE LIMITED ({elapsed}s); sleeping 5 min then retrying same PDF")
            time.sleep(300)
            continue

        # Real attempt — increment counter
        entry["attempt_count"] = entry.get("attempt_count", 0) + 1

        # Post-validation: even if claude returned EXTRACTION_DONE, sanity-check the outputs
        if success:
            is_valid, validation_reason = validate_extraction(pdf.stem)
            if not is_valid:
                print(f"  -> VALIDATION FAILED: {validation_reason}")
                success = False
                entry["validation_failed"] = True
                entry["validation_reason"] = validation_reason
        entry["ok"] = success
        manifest["extractions"][pdf.stem] = entry
        save_manifest(manifest)

        if success:
            total_success += 1
            success_count_since_ingest += 1
            # Add to SHA index
            sha_index[sha] = pdf.stem
            save_sha_index(sha_index)
            entry["sha256"] = sha
            # Add to content-dedup index so future multi-state copies skip extraction
            if content_key:
                for key_field in ("full_key", "year_key"):
                    k = content_key.get(key_field)
                    if k and k not in content_index:
                        content_index[k] = pdf.stem
                entry["legal_name"] = content_key.get("legal_name")
                entry["effective_date"] = content_key.get("effective_date")
                entry["content_key"] = content_key.get("full_key") or content_key.get("year_key")
                save_content_index(content_index)
            save_manifest(manifest)
            # Build a token/cost summary string from usage stats
            usage_str = ""
            if usage:
                in_t = usage.get("input_tokens", 0)
                out_t = usage.get("output_tokens", 0)
                cache_r = usage.get("cache_read_input_tokens", 0)
                cost = usage.get("total_cost_usd")
                usage_str = f", tokens=in{in_t:,}+out{out_t:,}"
                if cache_r:
                    usage_str += f"+cache_r{cache_r:,}"
                if cost is not None:
                    usage_str += f", $={cost:.4f}"
            print(f"  -> OK ({elapsed}s, total ok={total_success}{usage_str})")
            if success_count_since_ingest >= INGEST_EVERY_N:
                reingest_and_regen()
                success_count_since_ingest = 0
        else:
            total_failed += 1
            print(f"  -> FAILED ({elapsed}s) — tail: {out_tail[-300:].strip()}")


if __name__ == "__main__":
    main()
