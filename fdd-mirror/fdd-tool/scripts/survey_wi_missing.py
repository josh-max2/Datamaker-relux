"""Search WI portal for recognizable franchise brands NOT yet in our DB.

Strategy:
  1. Load recognition list from _survey_mn_recognizable.py (RECOGNIZED_BRANDS)
  2. Diff against DB brand_name_keys → produce target list of missing brands
  3. For each target, search WI portal (Playwright)
  4. Filter to Registered status; pick latest active filing
  5. Verify the WI filing's brand_name_key matches our target (not just a partial collision)
  6. Output a candidates JSON (downstream: download_from_wi_candidates.py)

Run-resumable: writes candidates incrementally, so credit/network interrupts don't lose work.
"""
from __future__ import annotations
import json, re, sqlite3, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from src.scrapers.wisconsin import WisconsinScraper, latest_active
from src.dedup import normalize_brand_name
from src.db import DB_PATH


def load_recognition_list() -> list[str]:
    text = (Path("scripts") / "_survey_mn_recognizable.py").read_text(encoding="utf-8")
    m = re.search(r"RECOGNIZED_BRANDS = \[(.+?)\]", text, re.DOTALL)
    return re.findall(r'"([^"]+)"', m.group(1))


def db_brand_keys() -> set[str]:
    conn = sqlite3.connect(DB_PATH)
    return {r[0] for r in conn.execute(
        "SELECT brand_name_key FROM franchisors WHERE brand_name_key IS NOT NULL"
    ).fetchall()}


def find_missing_targets() -> list[tuple[str, str]]:
    """Return [(display_name, normalized_key)] for brands we want but lack."""
    brands = load_recognition_list()
    db_keys = db_brand_keys()
    seen_keys = set()
    targets = []
    for b in brands:
        k = normalize_brand_name(b)
        if not k or len(k) < 4 or k in seen_keys:
            continue
        seen_keys.add(k)
        if k in db_keys:
            continue
        # Fuzzy substring (avoid double-adding e.g. "midas" if "midasshop" exists)
        if any((k in dk and len(k) >= 5) or (dk in k and len(dk) >= 5) for dk in db_keys):
            continue
        targets.append((b, k))
    return targets


def main():
    out_path = Path("output/_wi_candidates.json")
    targets = find_missing_targets()
    print(f"Targets (recognizable brands missing from DB): {len(targets)}")

    # Resume support: if out_path exists, skip already-searched targets
    existing = {}
    if out_path.exists():
        existing = {e["key"]: e for e in json.loads(out_path.read_text(encoding="utf-8"))}
        print(f"Resuming: {len(existing)} targets already searched")

    candidates = list(existing.values())
    n_found = sum(1 for c in candidates if c.get("portal_id"))
    n_skipped_done = 0
    n_no_match = 0
    n_new_found = 0

    with WisconsinScraper() as scraper:
        for i, (display, key) in enumerate(targets, 1):
            if key in existing:
                n_skipped_done += 1
                continue
            try:
                results = scraper.search(display)
            except Exception as e:
                print(f"  [{i:>3}/{len(targets)}] {display:<32}  SEARCH ERROR: {type(e).__name__}: {str(e)[:80]}")
                # Save what we have so far
                continue

            # Filter to brand match — the WI search is loose (substring)
            # Require the normalized trade_name OR legal_name to match our target key
            matches = []
            for r in results:
                t_key = normalize_brand_name(r.trade_name or "")
                l_key = normalize_brand_name(r.legal_name or "")
                if (key in t_key and len(key) >= 5) or (key in l_key and len(key) >= 5) or t_key == key or l_key == key:
                    matches.append(r)

            active = latest_active(matches)
            if not active:
                n_no_match += 1
                candidates.append({"key": key, "display": display, "portal_id": None})
                print(f"  [{i:>3}/{len(targets)}] {display:<32}  no Registered match ({len(matches)} total)")
            else:
                n_new_found += 1
                candidates.append({
                    "key": key, "display": display,
                    "portal_id": active.portal_id,
                    "legal_name": active.legal_name,
                    "trade_name": active.trade_name,
                    "effective_date": active.effective_date,
                    "status": active.status,
                    "details_url": active.details_url,
                })
                print(f"  [{i:>3}/{len(targets)}] {display:<32}  FOUND id={active.portal_id} {active.legal_name[:40]}")

            # Save after EVERY search so interrupt doesn't lose progress
            out_path.write_text(json.dumps(candidates, indent=2), encoding="utf-8")

    print()
    print(f"Survey complete:")
    print(f"  Already-searched (resumed): {n_skipped_done}")
    print(f"  Newly found (Registered):   {n_new_found}")
    print(f"  No match / no active:       {n_no_match}")
    print(f"  Total found-with-portal_id: {sum(1 for c in candidates if c.get('portal_id'))}")
    print(f"  Saved -> {out_path}")


if __name__ == "__main__":
    main()
