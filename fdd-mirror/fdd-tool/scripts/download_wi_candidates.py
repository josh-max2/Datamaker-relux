"""Download PDFs from WI portal for candidates produced by survey_wi_missing.py.

Saves a manifest in the same format as MN downloader so extract_parallel.py /
max_plan_extract_loop.py can pick it up.

Resume-safe: skips entries already downloaded (by portal_id or sha256).
"""
from __future__ import annotations
import argparse, json, sqlite3, sys
from datetime import datetime
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from src.scrapers.wisconsin import WisconsinScraper, FilingRow
from src.db import DB_PATH


def existing_shas() -> set[str]:
    conn = sqlite3.connect(DB_PATH)
    return {r[0] for r in conn.execute("SELECT pdf_sha256 FROM fdds").fetchall()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("candidates", help="Path to WI candidates JSON (output of survey)")
    ap.add_argument("--out", default="output/_pilot_wi_max_plan.json",
                    help="Manifest output path")
    ap.add_argument("--limit", type=int, default=None,
                    help="Limit to first N candidates")
    args = ap.parse_args()

    candidates = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
    # Filter to ones with portal_id (i.e., actually found in WI)
    candidates = [c for c in candidates if c.get("portal_id")]
    if args.limit:
        candidates = candidates[:args.limit]
    print(f"WI candidates with portal_id: {len(candidates)}")

    known_shas = existing_shas()
    print(f"Existing SHAs in DB: {len(known_shas)}")

    dest = Path("data/wi_scrape")
    manifest = []
    # Resume: load existing manifest entries if present
    existing_portal_ids = set()
    if Path(args.out).exists():
        manifest = json.loads(Path(args.out).read_text(encoding="utf-8"))
        existing_portal_ids = {m.get("portal_id") for m in manifest}
        print(f"Resuming: {len(manifest)} entries already in manifest")

    n_failed = 0
    n_dup = 0
    n_new = 0
    with WisconsinScraper() as scraper:
        for i, c in enumerate(candidates, 1):
            if c["portal_id"] in existing_portal_ids:
                continue
            filing = FilingRow(
                portal_id=c["portal_id"],
                legal_name=c["legal_name"],
                trade_name=c["trade_name"],
                effective_date=c["effective_date"],
                expiration_date="",
                status=c.get("status", "Registered"),
                details_url=c["details_url"],
            )
            t0 = datetime.now()
            try:
                result = scraper.download(filing, dest=dest, dedup_against=dest)
                dt = (datetime.now() - t0).total_seconds()
                if result.was_duplicate:
                    n_dup += 1
                    marker = "DUP"
                elif result.sha256 in known_shas:
                    marker = "DUP-DB"
                    n_dup += 1
                else:
                    n_new += 1
                    marker = "NEW"
                print(f"  [{marker}] {i:>3}/{len(candidates)}. {c['display'][:35]:<37}  "
                      f"{result.size_bytes/1024/1024:.1f}MB  ({dt:.1f}s)")
                manifest.append({
                    "franchisor": filing.legal_name,
                    "franchise_name": filing.trade_name,
                    "portal_id": filing.portal_id,
                    "source_url": filing.details_url,
                    "effective_date": filing.effective_date,
                    "filing_state": "WI",
                    "pdf_path": str(result.path),
                    "pdf_sha256": result.sha256,
                    "size_bytes": result.size_bytes,
                    "was_duplicate": result.was_duplicate or result.sha256 in known_shas,
                    "downloaded_at": datetime.now().isoformat(),
                })
                # Save after each download for resume safety
                Path(args.out).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            except Exception as e:
                n_failed += 1
                print(f"  [FAIL] {i:>3}/{len(candidates)}. {c['display'][:35]}: {type(e).__name__}: {str(e)[:80]}")

    print()
    print(f"Download summary:")
    print(f"  New downloads: {n_new}")
    print(f"  Duplicates:    {n_dup}")
    print(f"  Failed:        {n_failed}")
    print(f"  Manifest:      {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
