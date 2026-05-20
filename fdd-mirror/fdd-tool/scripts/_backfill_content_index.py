"""One-time backfill: scan all already-extracted PDFs in data/wi_scrape/ and
populate output/_content_to_stem.json so the next run of extract_loop.py can
skip duplicates we'd otherwise re-extract.

Safe to re-run. Only adds keys; never removes."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))
from _pdf_dedup import extract_content_key

PDF_DIR = Path("data/wi_scrape")
OUTPUT_DIR = Path("output")
CONTENT_TO_STEM = OUTPUT_DIR / "_content_to_stem.json"


def main() -> None:
    if not PDF_DIR.exists():
        print(f"no PDF dir at {PDF_DIR}")
        return
    existing = {}
    if CONTENT_TO_STEM.exists():
        try:
            existing = json.loads(CONTENT_TO_STEM.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    added = 0
    skipped = 0
    parsed_ok = 0
    parsed_partial = 0
    parsed_miss = 0

    for pdf in sorted(PDF_DIR.glob("*.pdf")):
        meta = OUTPUT_DIR / pdf.stem / "metadata.json"
        if not meta.exists():
            continue  # only index already-extracted PDFs
        ck = extract_content_key(pdf)
        if not ck:
            parsed_miss += 1
            continue
        if ck.get("effective_date"):
            parsed_ok += 1
        else:
            parsed_partial += 1
        for key_field in ("full_key", "year_key"):
            k = ck.get(key_field)
            if not k:
                continue
            if k in existing:
                skipped += 1
            else:
                existing[k] = pdf.stem
                added += 1

    CONTENT_TO_STEM.parent.mkdir(parents=True, exist_ok=True)
    CONTENT_TO_STEM.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    print(f"content dedup index: {len(existing)} entries ({added} added, {skipped} unchanged)")
    print(f"PDF extraction quality: {parsed_ok} high-confidence, {parsed_partial} year-only, {parsed_miss} miss")


if __name__ == "__main__":
    main()
