"""Download MN PDFs from a pre-curated candidates JSON.

Used after _survey_mn_recognizable.py has produced a candidates list. The
candidates JSON already encodes guid + download_url + filing metadata, so we
can reconstruct MinnesotaFiling objects without re-scraping.

Usage:
    python scripts/download_from_candidates.py output/_mn_recognized_candidates.json \
        --out output/_pilot_mn_186.json
"""
from __future__ import annotations
import argparse, json, sqlite3, sys
from datetime import datetime
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.scrapers.minnesota import MinnesotaScraper, MinnesotaFiling
from src.dedup import normalize_brand_name
from src.db import DB_PATH


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("candidates", help="Path to candidates JSON (output of survey)")
    ap.add_argument("--out", default="output/_pilot_mn_batch.json",
                    help="Manifest output path")
    ap.add_argument("--limit", type=int, default=None,
                    help="Limit to first N candidates (for testing)")
    ap.add_argument("--rate-limit", type=float, default=1.5,
                    help="Seconds between requests (default 1.5; bump to 4+ for retry batches)")
    ap.add_argument("--append", action="store_true",
                    help="Append to manifest instead of overwriting (used for retry batches)")
    args = ap.parse_args()

    candidates = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
    if args.limit:
        candidates = candidates[:args.limit]
    print(f"Loaded {len(candidates)} candidates from {args.candidates}")

    conn = sqlite3.connect(DB_PATH)
    known_shas = {r[0] for r in conn.execute("SELECT pdf_sha256 FROM fdds").fetchall()}
    print(f"Existing SHAs in DB: {len(known_shas)}")

    # MN download URL embeds the guid with curly braces but the property
    # already encodes them — reconstruct download_url cleanly via guid.
    # The candidates JSON has the raw guid and the encoded download_url; we
    # store both in MinnesotaFiling.
    dest = Path("data/mn_scrape")
    manifest = []
    if args.append:
        out_existing = Path(args.out)
        if out_existing.exists():
            manifest = json.loads(out_existing.read_text(encoding="utf-8"))
            print(f"Appending: starting with {len(manifest)} existing entries")
    n_failed = 0
    n_dup = 0
    with MinnesotaScraper(rate_limit_sec=args.rate_limit) as s:
        for i, c in enumerate(candidates, 1):
            # Rebuild dates back into MM/DD/YYYY for the Filing
            try:
                rec_iso = c.get("received_date") or ""
                rec_mdy = (datetime.strptime(rec_iso, "%Y-%m-%d").strftime("%m/%d/%Y")
                           if rec_iso else "")
                add_iso = c.get("added_on") or ""
                add_mdy = (datetime.strptime(add_iso, "%Y-%m-%d").strftime("%m/%d/%Y")
                           if add_iso else "")
            except ValueError:
                rec_mdy = ""
                add_mdy = ""
            filing = MinnesotaFiling(
                document_id=c["document_id"],
                franchisor=c["franchisor"],
                franchise_name=c.get("franchise_name") or "",
                document_type="Clean FDD",
                year=int(c["year"]),
                file_number="",
                received_date=rec_mdy,
                added_on=add_mdy,
                download_url=c["download_url"],
                guid=c["guid"],
            )
            t0 = datetime.now()
            try:
                result = s.download(filing, dest=dest, existing_shas=known_shas)
                dt = (datetime.now() - t0).total_seconds()
                marker = "DUP" if result.was_duplicate else "NEW"
                if result.was_duplicate:
                    n_dup += 1
                print(f"  [{marker}] {i:>3}/{len(candidates)}. "
                      f"{filing.franchisor[:38]:<40}  "
                      f"{result.size_bytes/1024/1024:.1f}MB  ({dt:.1f}s)")
                manifest.append({
                    "franchisor": filing.franchisor,
                    "franchise_name": filing.franchise_name,
                    "document_id": filing.document_id,
                    "guid": filing.guid,
                    "source_url": filing.download_url,
                    "received_date": filing.received_date,
                    "added_on": filing.added_on,
                    "filing_year": filing.year,
                    "filing_state": "MN",
                    "pdf_path": str(result.path),
                    "pdf_sha256": result.sha256,
                    "size_bytes": result.size_bytes,
                    "was_duplicate": result.was_duplicate,
                    "is_update": False,
                    "previous_year": None,
                    "downloaded_at": datetime.now().isoformat(),
                })
            except Exception as e:
                n_failed += 1
                print(f"  [FAIL] {i:>3}/{len(candidates)}. "
                      f"{filing.franchisor[:40]}: {type(e).__name__}: {e}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print()
    print(f"Download summary:")
    print(f"  Successful   : {len(manifest)}")
    print(f"  Duplicates   : {n_dup}  (already in DB by sha; will skip extract)")
    print(f"  Failed       : {n_failed}")
    print(f"  Manifest     : {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
