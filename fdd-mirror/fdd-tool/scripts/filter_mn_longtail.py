"""Filter the MN 'unrecognized' pile down to real-franchise candidates.

Pattern: legal-entity-name contains franchise-indicator suffixes
('Franchising', 'Franchisor', 'Franchise Holdings', 'Franchise Systems',
'Franchise SPV', 'Franchise LLC', 'Franchise Inc', etc).

Dedup against DB brand_name_keys (no rehash of brands we already have).

Output: candidates JSON formatted like the existing recognized_candidates so
download_from_candidates.py can pick it up directly.
"""
from __future__ import annotations
import json, re, sqlite3, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from src.scrapers.minnesota import MinnesotaScraper
from src.dedup import normalize_brand_name
from src.db import DB_PATH

# Franchise-indicator patterns in legal name
FRANCHISE_INDICATORS = re.compile(
    r"\b("
    r"Franchising|Franchisor|Franchise Holdings|Franchise Systems|Franchise SPV|"
    r"Franchise LLC|Franchise Inc|Franchise Corp|Franchising LLC|"
    r"Franchise Brands|Franchise Group|Franchise Company|"
    r"Franchise Concepts|Franchise USA|Franchise International|"
    r"FRANCHISE NETWORK|FRANCHISE Holding|FRANCHISE Operations|"
    r"FRANCHISES Inc|FRANCHISES LLC"
    r")\b",
    re.IGNORECASE,
)

# Hard-skip patterns: obvious one-off LLCs / not franchise entities
HARD_SKIP = re.compile(
    r"\b(?:Capital LLC|Holdings LLC$|Investments?|Ventures? LLC$|Properties LLC|"
    r"Real Estate LLC|Insurance Agency|Consulting LLC$|Marketing LLC$)\b",
    re.IGNORECASE,
)


def db_brand_keys() -> set[str]:
    conn = sqlite3.connect(DB_PATH)
    return {r[0] for r in conn.execute(
        "SELECT brand_name_key FROM franchisors WHERE brand_name_key IS NOT NULL"
    ).fetchall()}


def main():
    out_path = Path("output/_mn_longtail_candidates.json")

    # Fetch current MN year 2026 + 2025 filings — give us full metadata + guids
    print("Fetching MN 2026 + 2025 Clean FDDs...")
    with MinnesotaScraper() as s:
        f26 = s.search(year=2026, document_type="Clean FDD")
        f25 = s.search(year=2025, document_type="Clean FDD")
    print(f"  2026: {len(f26)}  2025: {len(f25)}")
    all_filings = f26 + f25

    # Within-brand dedup keyed on normalize(franchise_name|franchisor) — most recent wins
    by_brand: dict[str, object] = {}
    for f in all_filings:
        key = normalize_brand_name(f.franchise_name or f.franchisor)
        if not key:
            continue
        existing = by_brand.get(key)
        if existing is None:
            by_brand[key] = f
        else:
            new_sort = (f.added_on_iso or "", f.received_date_iso or "")
            old_sort = (existing.added_on_iso or "", existing.received_date_iso or "")
            if new_sort > old_sort:
                by_brand[key] = f
    print(f"Distinct brands across 2025+2026: {len(by_brand)}")

    # DB keys for dedup
    db_keys = db_brand_keys()
    print(f"DB brand_name_keys: {len(db_keys)}")

    # Filter: franchise-indicator in legal name; NOT already in DB (incl fuzzy)
    candidates = []
    n_skip_indb = 0
    n_skip_noindicator = 0
    n_skip_hardskip = 0
    for key, f in by_brand.items():
        legal = (f.franchisor or "")
        # Hard-skip first
        if HARD_SKIP.search(legal):
            n_skip_hardskip += 1
            continue
        # Need franchise indicator
        if not FRANCHISE_INDICATORS.search(legal):
            n_skip_noindicator += 1
            continue
        # DB dedup — direct key OR substring overlap
        fr_key = normalize_brand_name(legal)
        fn_key = normalize_brand_name(f.franchise_name or "")
        lookups = {k for k in (key, fr_key, fn_key) if k}
        if any(k in db_keys for k in lookups):
            n_skip_indb += 1
            continue
        # Fuzzy: any DB key is substring of one of these (or vv) and ≥5 chars
        fuzzy_hit = False
        for db_k in db_keys:
            if len(db_k) < 5:
                continue
            for lk in lookups:
                if len(lk) < 5:
                    continue
                if db_k == lk or db_k in lk or lk in db_k:
                    fuzzy_hit = True
                    break
            if fuzzy_hit:
                break
        if fuzzy_hit:
            n_skip_indb += 1
            continue
        candidates.append({
            "key": key,
            "franchisor": f.franchisor,
            "franchise_name": f.franchise_name,
            "year": f.year,
            "added_on": f.added_on_iso,
            "received_date": f.received_date_iso,
            "guid": f.guid,
            "document_id": f.document_id,
            "download_url": f.download_url,
        })

    print(f"\nFilter outcomes:")
    print(f"  Skipped (already in DB):        {n_skip_indb}")
    print(f"  Skipped (no franchise indicator): {n_skip_noindicator}")
    print(f"  Skipped (hard-skip pattern):    {n_skip_hardskip}")
    print(f"  CANDIDATES (pass all filters):  {len(candidates)}")

    # Sort by recency
    candidates.sort(key=lambda c: (c.get("added_on") or "", c.get("received_date") or ""), reverse=True)

    out_path.write_text(json.dumps(candidates, indent=2), encoding="utf-8")
    print(f"\nSaved -> {out_path}")

    # Quick preview
    print(f"\nFirst 30 candidates (most recent):")
    for i, c in enumerate(candidates[:30], 1):
        fn = (c.get("franchise_name") or "")[:30]
        fr = c["franchisor"][:45]
        print(f"  {i:>3}. [{c['added_on']}] {fr:<47} {fn}")


if __name__ == "__main__":
    main()
