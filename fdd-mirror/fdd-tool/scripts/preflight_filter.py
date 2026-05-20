"""Cheap reconnaissance pass: searches each candidate brand on the WI portal and
records whether it has a currently-Registered filing. No downloads, no extracts.

Outputs:
  output/_candidates_verified.json  — only brands with an active Registered filing,
                                       with portal_id + URL ready for batch_200.py to consume.
  output/_candidates_rejected.json  — names that returned no Registered filing (for audit).

Cost: $0 (no Claude calls). Time: ~2.5s/brand at the throttle rate.

Usage:
    uv run python scripts/preflight_filter.py [--source FILE | --use-fallback-pool]

The output JSON is consumed by an updated batch_200.py that reads from the verified
list instead of doing search-then-download per brand.
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

VERIFIED = Path("output/_candidates_verified.json")
REJECTED = Path("output/_candidates_rejected.json")
RATE_LIMIT_SEC = 2.5


def load_existing_verified() -> dict:
    """Already-verified brands (so re-runs don't re-search)."""
    if VERIFIED.exists():
        try:
            return json.loads(VERIFIED.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def load_existing_rejected() -> dict:
    if REJECTED.exists():
        try:
            return json.loads(REJECTED.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def existing_db_brands() -> set[str]:
    """Lowercase names already in our DB so we don't re-verify them."""
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", help="Path to JSON or newline-delimited TXT of brand names")
    parser.add_argument("--use-fallback-pool", action="store_true",
                        help="Use the hand-curated fallback pool from batch_200.py")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max number of brands to verify this run (0 = no limit)")
    args = parser.parse_args()

    # Load candidate names
    if args.use_fallback_pool or not args.source:
        from scripts.batch_200 import FALLBACK_POOL
        candidates = FALLBACK_POOL
        source_label = "fallback_pool"
    else:
        src = Path(args.source)
        text = src.read_text(encoding="utf-8")
        try:
            data = json.loads(text)
            if isinstance(data, list):
                candidates = [str(x) for x in data]
            elif isinstance(data, dict):
                candidates = list(data.keys())
            else:
                raise ValueError("unexpected JSON shape")
        except json.JSONDecodeError:
            candidates = [ln.strip() for ln in text.split("\n") if ln.strip()]
        source_label = str(src)

    verified = load_existing_verified()
    rejected = load_existing_rejected()
    in_db = existing_db_brands()

    print(f"=== Preflight filter ===")
    print(f"source: {source_label} ({len(candidates)} candidates)")
    print(f"existing verified: {len(verified)}")
    print(f"existing rejected: {len(rejected)}")
    print(f"in DB already: {len(in_db)}")

    # Build pending list: not in DB, not already verified, not already rejected
    pending: list[str] = []
    seen: set[str] = set()
    for c in candidates:
        norm = c.strip()
        low = norm.lower()
        if low in in_db or low in {k.lower() for k in verified} or low in {k.lower() for k in rejected}:
            continue
        if low in seen: continue
        seen.add(low); pending.append(norm)

    print(f"pending: {len(pending)}\n")
    if not pending:
        print("nothing to do — all candidates already classified")
        return

    if args.limit > 0:
        pending = pending[:args.limit]
        print(f"limiting this run to first {args.limit} pending\n")

    n_new_verified = 0
    n_new_rejected = 0

    with WisconsinScraper(headless=True, rate_limit_sec=RATE_LIMIT_SEC) as scraper:
        for i, brand in enumerate(pending, start=1):
            try:
                filings = scraper.search(brand)
                active = latest_active(filings)
                if active:
                    verified[brand] = {
                        "portal_id": active.portal_id,
                        "legal_name": active.legal_name,
                        "trade_name": active.trade_name,
                        "effective_date": active.effective_date,
                        "expiration_date": active.expiration_date,
                        "details_url": active.details_url,
                        "n_filings_seen": len(filings),
                        "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    n_new_verified += 1
                    print(f"[{i:4d}/{len(pending)}] {brand}: VERIFIED id={active.portal_id} ({active.trade_name})")
                    save(VERIFIED, verified)
                else:
                    rejected[brand] = {
                        "n_filings_seen": len(filings),
                        "reason": "no_registered_filing" if filings else "no_results",
                        "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    n_new_rejected += 1
                    print(f"[{i:4d}/{len(pending)}] {brand}: rejected ({len(filings)} total filings, none Registered)")
                    save(REJECTED, rejected)
            except Exception as e:
                print(f"[{i:4d}/{len(pending)}] {brand}: ERROR {e}")

    print(f"\n=== Done ===")
    print(f"This run: +{n_new_verified} verified, +{n_new_rejected} rejected")
    print(f"Cumulative verified: {len(verified)}")
    print(f"Cumulative rejected: {len(rejected)}")
    print(f"\nNext step: run batch_200.py — it will consume {VERIFIED} for fast targeted extraction.")


if __name__ == "__main__":
    main()
