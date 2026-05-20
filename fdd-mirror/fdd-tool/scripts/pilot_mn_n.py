"""Pull N distinct franchisors from MN CARDS by recency.

Generalized version of pilot_mn_5.py:
  - Recency-first: sorted by (added_on, received_date) desc
  - Append-not-replace: a MN filing newer than what we have in the DB is
    treated as a brand UPDATE — its sha256 lands as a new fdds row sharing
    the same franchisor_id, and the brand page auto-flips via MAX(d.id).
  - Skip a filing IF (a) we already have a same-or-newer filing for the
    brand, OR (b) we already have the exact PDF (sha256 match — checked
    at download time).

Usage:
    python scripts/pilot_mn_n.py 100              # top 100 brands, year=2026
    python scripts/pilot_mn_n.py 50 --year 2025   # top 50 from 2025 Clean FDDs
"""
from __future__ import annotations
import argparse
import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.scrapers.minnesota import MinnesotaScraper
from src.dedup import normalize_brand_name
from src.db import DB_PATH


def existing_brand_latest_year(conn) -> dict[str, int]:
    rows = conn.execute("""
        SELECT fr.brand_name_key, MAX(d.filing_year) AS latest_year
        FROM franchisors fr
        JOIN fdds d ON d.franchisor_id = fr.id
        WHERE fr.brand_name_key IS NOT NULL AND d.filing_year IS NOT NULL
        GROUP BY fr.brand_name_key
    """).fetchall()
    return {r[0]: int(r[1]) for r in rows if r[1]}


def existing_shas(conn) -> set[str]:
    return {r[0] for r in conn.execute("SELECT pdf_sha256 FROM fdds").fetchall()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int, help="Number of distinct brands to pick")
    ap.add_argument("--year", type=int, default=2026,
                    help="MN filing year to search (default 2026)")
    ap.add_argument("--document-type", default="Clean FDD",
                    help="MN documentType filter (default 'Clean FDD')")
    ap.add_argument("--out", default=None,
                    help="Manifest output path (default output/_pilot_mn_<n>.json)")
    args = ap.parse_args()

    conn = sqlite3.connect(DB_PATH)
    brand_latest_year = existing_brand_latest_year(conn)
    known_shas = existing_shas(conn)
    print(f"Existing in DB: {len(brand_latest_year)} franchisors, {len(known_shas)} FDD SHAs")

    print(f"\nFetching MN CARDS {args.year} {args.document_type}s...")
    with MinnesotaScraper() as s:
        filings = s.search(year=args.year, document_type=args.document_type)
    print(f"  Returned {len(filings)} filings.")
    if len(filings) >= 500:
        print(f"  ⚠ Hit MN's 500-result page cap. Some {args.year} filings may not be visible.")

    filings.sort(
        key=lambda f: (f.added_on_iso or "0000-00-00", f.received_date_iso or "0000-00-00"),
        reverse=True,
    )

    selected = []
    seen_keys = set()
    n_skipped_newer = 0
    n_skipped_dupe = 0
    n_updates = 0
    n_new = 0
    for f in filings:
        key = normalize_brand_name(f.franchise_name or f.franchisor)
        if not key:
            continue
        if key in seen_keys:
            n_skipped_dupe += 1
            continue
        existing_year = brand_latest_year.get(key)
        if existing_year is not None and existing_year >= f.year:
            n_skipped_newer += 1
            continue
        seen_keys.add(key)
        selected.append(f)
        if existing_year is not None:
            n_updates += 1
        else:
            n_new += 1
        if len(selected) >= args.n:
            break

    print(f"\nSelection summary:")
    print(f"  Picked       : {len(selected)} (of requested {args.n})")
    print(f"    NEW brands : {n_new}")
    print(f"    UPDATES    : {n_updates} (newer filing for brands already in DB)")
    print(f"  Skipped      : {n_skipped_newer} have-newer-or-equal, {n_skipped_dupe} within-batch dupes")

    if not selected:
        print("\nNothing new to scrape. Exiting.")
        return 0

    print(f"\nFirst 10 picks:")
    for i, f in enumerate(selected[:10], 1):
        key = normalize_brand_name(f.franchise_name or f.franchisor)
        existing_year = brand_latest_year.get(key)
        kind = (f"UPD {existing_year}→{f.year}" if existing_year else "NEW         ")
        print(f"  {i:>3}. [{kind}] {f.franchisor[:50]:<52} (added {f.added_on})")
    if len(selected) > 10:
        print(f"  ... and {len(selected) - 10} more")

    # Download
    print(f"\nDownloading {len(selected)} PDFs...")
    dest = Path("data/mn_scrape")
    manifest = []
    n_failed = 0
    with MinnesotaScraper() as s:
        for i, f in enumerate(selected, 1):
            t0 = datetime.now()
            try:
                result = s.download(f, dest=dest, existing_shas=known_shas)
                dt = (datetime.now() - t0).total_seconds()
                key = normalize_brand_name(f.franchise_name or f.franchisor)
                existing_year = brand_latest_year.get(key)
                marker = "DUP" if result.was_duplicate else ("UPD" if existing_year else "NEW")
                print(f"  [{marker}] {i:>3}/{len(selected)}. {f.franchisor[:38]:<40}  "
                      f"{result.size_bytes/1024/1024:.1f}MB  ({dt:.1f}s)")
                manifest.append({
                    "franchisor": f.franchisor,
                    "franchise_name": f.franchise_name,
                    "document_id": f.document_id,
                    "guid": f.guid,
                    "source_url": f.download_url,
                    "received_date": f.received_date_iso,
                    "added_on": f.added_on_iso,
                    "filing_year": f.year,
                    "filing_state": "MN",
                    "pdf_path": str(result.path),
                    "pdf_sha256": result.sha256,
                    "size_bytes": result.size_bytes,
                    "was_duplicate": result.was_duplicate,
                    "is_update": existing_year is not None,
                    "previous_year": existing_year,
                    "downloaded_at": datetime.now().isoformat(),
                })
            except Exception as e:
                n_failed += 1
                print(f"  [FAIL] {i:>3}/{len(selected)}. {f.franchisor[:40]}: {type(e).__name__}: {e}")

    out_path = Path(args.out) if args.out else Path(f"output/_pilot_mn_{args.n}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"\nDownload summary:")
    print(f"  Successful   : {len(manifest)}")
    print(f"  Failed       : {n_failed}")
    print(f"  Manifest     : {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
