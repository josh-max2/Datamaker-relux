"""Pilot: pull 5 distinct UNSEEN franchisors from MN CARDS by recency.

Steps:
  1. Search 2026 Clean FDDs.
  2. Sort by 'Added on' descending (most recent CARDS upload first).
  3. Filter out franchisors we already have in the DB
     (cross-state dedup via brand_name_key).
  4. Pick the top 5 distinct franchisors.
  5. Download their PDFs into data/mn_scrape/.
  6. Write a pilot manifest output/_pilot_mn_5.json for the extract step.

This is a recency-first walk. Re-running will pick up newer filings without
duplicating work (existing SHA-256s are checked at download time).
"""
from __future__ import annotations
import json, sqlite3, sys
from pathlib import Path
from datetime import datetime
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.scrapers.minnesota import MinnesotaScraper
from src.dedup import normalize_brand_name
from src.db import DB_PATH


def existing_brand_latest_year(conn) -> dict[str, int]:
    """For each known brand_name_key, the latest filing_year we have on file.

    The picker uses this to skip MN filings older-or-equal to what we already
    have, while ALLOWING through newer filings — so a 2026 Crumbl filing on MN
    can update our 2023 Crumbl record (adds a new fdd row sharing the same
    franchisor_id; the upsert layer handles the join).
    """
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
    conn = sqlite3.connect(DB_PATH)
    brand_latest_year = existing_brand_latest_year(conn)
    known_shas = existing_shas(conn)
    print(f"Existing in DB: {len(brand_latest_year)} franchisors, {len(known_shas)} FDD SHAs")

    print("\nFetching MN CARDS recent Clean FDDs (year=2026)...")
    with MinnesotaScraper() as s:
        filings = s.search(year=2026, document_type="Clean FDD")
    print(f"  Returned {len(filings)} filings.")

    # Sort by (added_on, received_date) desc — recency-first.
    # Including received_date as tiebreaker is important when many filings
    # share the same `Added on` date (typical: ~20 filings per day on MN).
    filings.sort(
        key=lambda f: (f.added_on_iso or "0000-00-00", f.received_date_iso or "0000-00-00"),
        reverse=True,
    )

    # Smart skip logic. Skip a filing IF:
    #   1. We have the exact PDF (sha256 match — can't compare without downloading,
    #      so we defer that check to download-time via existing_shas).
    #   2. We already have a same-year-or-newer filing for that brand
    #      (e.g. we have Crumbl 2024 and MN has Crumbl 2023 — skip).
    # ALLOW through filings that are NEWER than what we have for a known brand —
    # those get appended as new fdd rows (NOT replacements) and the brand page
    # auto-flips to the new data via MAX(d.id) in site_gen.
    selected = []
    seen_keys = set()
    skipped_have_newer = 0
    skipped_dupe_in_pick = 0
    for f in filings:
        key = normalize_brand_name(f.franchise_name or f.franchisor)
        if not key:
            continue
        # Within-batch dedup: when MN has e.g. Crumbl 2026 + Crumbl 2025 amendment,
        # take only the most-recently-added (first occurrence after recency sort).
        if key in seen_keys:
            skipped_dupe_in_pick += 1
            continue
        # Cross-DB dedup: skip if we already have a same-or-newer filing year.
        existing_year = brand_latest_year.get(key)
        if existing_year is not None and existing_year >= f.year:
            skipped_have_newer += 1
            continue
        seen_keys.add(key)
        selected.append(f)
        if len(selected) >= 5:
            break

    print(f"  Skipped {skipped_have_newer} already-have-same-or-newer, "
          f"{skipped_dupe_in_pick} within-pick duplicates.")
    print(f"  Picked {len(selected)} brands (mix of net-new + brand-update):\n")
    for i, f in enumerate(selected, 1):
        key = normalize_brand_name(f.franchise_name or f.franchisor)
        existing_year = brand_latest_year.get(key)
        kind = (f"UPDATE (had {existing_year}, MN has {f.year})"
                if existing_year is not None else "NEW")
        print(f"  {i}. [{kind}] {f.franchisor[:45]:<47} (filed {f.received_date}, added {f.added_on})")
        print(f"     doc_id={f.document_id}  guid={f.guid}")

    if not selected:
        print("\nNo new brands to scrape. Exiting.")
        return 0

    # Download each
    print("\nDownloading PDFs...")
    dest = Path("data/mn_scrape")
    manifest = []
    with MinnesotaScraper() as s:
        for i, f in enumerate(selected, 1):
            t0 = datetime.now()
            try:
                result = s.download(f, dest=dest, existing_shas=known_shas)
                dt = (datetime.now() - t0).total_seconds()
                key = normalize_brand_name(f.franchise_name or f.franchisor)
                existing_year = brand_latest_year.get(key)
                marker = "DUP" if result.was_duplicate else ("UPD" if existing_year else "NEW")
                print(f"  [{marker}] {i}. {f.franchisor[:40]}  "
                      f"{result.size_bytes/1024/1024:.1f}MB  sha={result.sha256[:12]}…  ({dt:.1f}s)")
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
                    # Indicates whether this filing UPDATES a brand we already had
                    # (existing_year=N, MN has M > N) or creates a NEW brand.
                    "is_update": existing_year is not None,
                    "previous_year": existing_year,
                    "downloaded_at": datetime.now().isoformat(),
                })
            except Exception as e:
                print(f"  [FAIL] {i}. {f.franchisor[:40]}: {type(e).__name__}: {e}")

    Path("output").mkdir(exist_ok=True)
    manifest_path = Path("output/_pilot_mn_5.json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest -> {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
