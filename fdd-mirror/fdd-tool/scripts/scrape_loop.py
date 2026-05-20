"""Continuous WI portal scrape loop. No AI calls, no cost beyond compute.

Reads candidate brand names from one or more files (--candidates), searches each on
the WI portal, and downloads any that have a currently-Registered filing. Persists
a "tried" cache so re-runs skip already-checked names. Stops scraping when too many
PDFs are unprocessed (backlog cap) — no point piling up faster than extract_loop
can keep up.

Run in its own PowerShell:
    uv run python scripts/scrape_loop.py [--candidates names.txt] [--max-pending 20]

Companion: scripts/extract_loop.py runs in another PowerShell and processes the PDFs.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from src.scrapers.wisconsin import WisconsinScraper, latest_active

PDF_DIR = Path("data/wi_scrape")
OUTPUT_DIR = Path("output")
SEARCH_CACHE = Path("output/_search_cache.json")  # persistent: brand -> {status,...}
RATE_LIMIT_SEC = 2.5
DEFAULT_MAX_PENDING = 15
DEFAULT_POLL_INTERVAL_SEC = 60  # when backlogged, how often to recheck


def load_search_cache() -> dict:
    if SEARCH_CACHE.exists():
        try:
            return json.loads(SEARCH_CACHE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_search_cache(c: dict) -> None:
    SEARCH_CACHE.parent.mkdir(parents=True, exist_ok=True)
    SEARCH_CACHE.write_text(json.dumps(c, indent=2), encoding="utf-8")


def existing_db_brands() -> set[str]:
    import sqlite3
    db_path = Path("data/db.sqlite")
    if not db_path.exists():
        return set()
    names: set[str] = set()
    with sqlite3.connect(db_path) as conn:
        for row in conn.execute("SELECT brand_name, legal_name FROM franchisors"):
            if row[0]: names.add(row[0].strip().lower())
            if row[1]: names.add(row[1].strip().lower())
    return names


def count_pending_extraction() -> int:
    """Number of PDFs in data/wi_scrape/ that don't yet have output/{stem}/metadata.json."""
    if not PDF_DIR.exists():
        return 0
    return sum(1 for p in PDF_DIR.glob("*.pdf")
               if not (OUTPUT_DIR / p.stem / "metadata.json").exists())


def load_candidates(paths: list[str]) -> list[str]:
    """Load candidate names from one or more text/json files."""
    names: list[str] = []
    seen: set[str] = set()
    for src in paths:
        p = Path(src)
        if not p.exists():
            print(f"[warn] candidates file not found: {src}"); continue
        text = p.read_text(encoding="utf-8")
        try:
            data = json.loads(text)
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = list(data.keys())
            else:
                continue
        except json.JSONDecodeError:
            items = [ln.strip() for ln in text.split("\n") if ln.strip()]
        for n in items:
            n = str(n).strip()
            low = n.lower()
            if not n or low in seen: continue
            seen.add(low); names.append(n)
    return names


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", nargs="+",
                        default=["scripts/candidates.txt"],
                        help="One or more files with candidate brand names")
    parser.add_argument("--max-pending", type=int, default=DEFAULT_MAX_PENDING,
                        help="Stop scraping when this many PDFs await extraction")
    parser.add_argument("--poll-when-backlogged", type=int, default=DEFAULT_POLL_INTERVAL_SEC,
                        help="Seconds to wait before re-checking if backlog drops")
    args = parser.parse_args()

    candidates = load_candidates(args.candidates)
    cache = load_search_cache()
    in_db = existing_db_brands()

    print(f"=== scrape_loop starting ===")
    print(f"  candidates: {len(candidates)} from {args.candidates}")
    print(f"  cache: {len(cache)} previously searched")
    print(f"  DB brands: {len(in_db)}")
    print(f"  max pending extractions: {args.max_pending}")
    print(f"  rate: 1 req per {RATE_LIMIT_SEC}s\n")

    # Filter candidates: not in DB, not previously searched (no matter the outcome)
    pending: list[str] = []
    for c in candidates:
        low = c.strip().lower()
        if low in in_db: continue
        if low in {k.lower() for k in cache}: continue
        pending.append(c)
    print(f"untried: {len(pending)}\n")
    if not pending:
        print("nothing to do — all candidates already searched")
        return

    with WisconsinScraper(headless=True, rate_limit_sec=RATE_LIMIT_SEC) as scraper:
        for i, brand in enumerate(pending, start=1):
            # Backlog check — wait if extract_loop is too far behind
            while count_pending_extraction() >= args.max_pending:
                print(f"[backlog] {count_pending_extraction()} PDFs awaiting extraction; "
                      f"waiting {args.poll_when_backlogged}s for extract_loop to catch up")
                time.sleep(args.poll_when_backlogged)

            try:
                filings = scraper.search(brand)
                active = latest_active(filings)
                entry = {
                    "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "n_filings_seen": len(filings),
                }
                if not active:
                    entry["status"] = "no_registered_filing"
                    cache[brand] = entry
                    save_search_cache(cache)
                    print(f"[{i:5d}/{len(pending)}] {brand}: no Registered ({len(filings)} total)")
                    continue

                # Download with SHA-256 dedup against existing PDFs
                dl = scraper.download(active, PDF_DIR, dedup_against=PDF_DIR)
                entry.update({
                    "status": "downloaded" if not dl.was_duplicate else "duplicate_sha",
                    "portal_id": active.portal_id,
                    "legal_name": active.legal_name,
                    "trade_name": active.trade_name,
                    "effective_date": active.effective_date,
                    "sha256": dl.sha256,
                    "pdf_path": str(dl.path),
                    "was_duplicate": dl.was_duplicate,
                })
                cache[brand] = entry
                save_search_cache(cache)
                tag = "DUP" if dl.was_duplicate else "OK"
                print(f"[{i:5d}/{len(pending)}] {brand}: {tag} id={active.portal_id} "
                      f"({dl.size_bytes/1024/1024:.1f} MB)")

            except Exception as e:
                cache[brand] = {
                    "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "error",
                    "error": repr(e)[:300],
                }
                save_search_cache(cache)
                print(f"[{i:5d}/{len(pending)}] {brand}: ERROR {repr(e)[:120]}")

    print(f"\n[done] scrape pass complete")


if __name__ == "__main__":
    main()
