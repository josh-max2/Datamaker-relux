"""Long-running batch: scrape + extract + ingest the NEXT 200 untried WI franchisors.

Cumulative across runs. Each invocation:
  1. Tries to pull fresh list from WI activeFilings (1,879 names); falls back to hardcoded.
  2. Skips brands already tried (any prior run, any status except 'error' for retry).
  3. Takes the next 200 untried brands.
  4. For each: scrape -> SHA-256 dedup -> extract -> manifest update.
  5. Final step: re-ingest to SQLite + regenerate static site.

Manifest at output/_batch_progress.json — cumulative. Safe to interrupt and resume.

Usage:
    cd fdd-tool
    uv run python scripts/batch_200.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from src.scrapers.wisconsin import WisconsinScraper, latest_active

PER_RUN_TARGET = 1000            # successful new extractions per invocation
SCRAPE_DEST = Path("data/wi_scrape")
MANIFEST = Path("output/_batch_progress.json")
UV_PATH = "C:/Users/joshs/AppData/Roaming/Python/Python312/Scripts/uv.exe"
RATE_LIMIT_SEC = 2.5
ACTIVE_FILINGS_URL = "https://apps.dfi.wi.gov/apps/franchiseefiling/activeFilings.aspx"

# Hand-curated fallback pool used if WI active-filings page is in maintenance.
# Mix of home-services (from prior WI list fetch) and well-known national brands.
FALLBACK_POOL = [
    # Home services
    "1-800 WATER DAMAGE", "1-800-Packouts", "101 Mobility", "AAAC Support Services",
    "ABM Franchising", "AdvantaClean", "Aire Serv", "Aire-Master", "Alair Enterprises",
    "AMRAMP", "Archadeck", "Assisting Hands", "Aussie Pet Mobile", "Benjamin Franklin",
    "BlueFrog Plumbing", "CarePatrol", "CARSTAR", "Certa Pro", "Chem-Dry", "ChiroWay",
    "Christian Brothers Automotive", "City Wide", "CMIT Solutions", "ComForCare",
    "Conserva Irrigation", "CORE Group Restoration", "Coverall", "Critter Control",
    "Culligan", "Dryer Vent Wizard", "DUCTZ", "Dumpster Dudez", "Dryvebox",
    "Enviro-Master", "Executive Home Care", "Fish Window Cleaning", "Five Star Bath",
    "Five Star Painting", "Floorcoverings International", "Garage Experts",
    "Garage Living", "Glass Doctor", "Gotcha Covered", "GrassRoots Turf", "Griswold",
    "Grout Doctor", "HomeAides", "HomeCare Advocacy", "HomeSmart", "HomeVestors",
    "Homewatch CareGivers", "HomeWell", "HOODZ", "House Doctors", "HouseMaster",
    "Howard Hanna", "HPB Blinds", "JDog Franchises", "Junkluggers", "Keller Williams",
    "Keyrenter", "Kitchen Guard", "Koala Insulation", "Lawn Pride", "Lawn Squad",
    "Lightspeed Restoration", "Living Assistance", "Maid Right", "MaidPro", "MAACO",
    "Martinizing", "Mastercare", "Mosquito Hunters", "Mosquito Joe", "Mosquito Shield",
    "Mosquito Squad", "Mr. Appliance", "Mr. Electric", "National Property Inspections",
    "NHance", "PAUL DAVIS", "PACKOUTZ", "Painter Bros", "PatchMaster", "PILLAR TO POST",
    "Pro-Lift Doors", "ProColor Collision", "PURAIR", "Rainbow International",
    "Real Property Management", "Realty Executives", "Realty ONE Group", "Red Roof",
    "Restoration 1", "Restore Franchising", "Right at Home", "RooterMan", "Roto-Rooter",
    "Rytech", "Safer Home Services", "Scenthound", "Screenmobile",
    "Senior Care Authority", "Seniors Helping Seniors", "ServiceMaster", "Shack Shine",
    "ShelfGenie", "Sir Grout", "Spring Green Lawn Care", "Stanley Steemer",
    "Storm Guard", "Superior Fence", "Surface Experts", "Surface Specialists",
    "The Cleaning Authority", "The Grounds Guys", "The Grout Medic",
    "The HomeTeam Inspection", "The Vital Stretch", "The Woodhouse SPAS",
    "Touching Hearts", "True North Restoration", "Truly Nolen", "USA Insulation",
    "Vanguard Cleaning", "Window Gang", "Window Genie", "WINDOW WORLD",
    "World Inspection Network", "Zerorez", "Ziebart", "Zoom Drain",
    # Food / QSR
    "McDonald's", "Subway", "Burger King", "Wendy's", "Taco Bell", "Pizza Hut",
    "Domino's", "Papa John's", "KFC", "Chick-fil-A", "Five Guys", "Jersey Mike's",
    "Jimmy John's", "Firehouse Subs", "Arby's", "Sonic", "Popeyes", "Bojangles",
    "Wingstop", "Buffalo Wild Wings", "Applebee's", "Chili's", "Outback", "IHOP",
    "Denny's", "Cracker Barrel", "Texas Roadhouse", "Auntie Anne's", "Cinnabon",
    "Edible Arrangements", "Carvel", "Cold Stone", "Baskin Robbins", "Dairy Queen",
    "Marco's Pizza", "Hungry Howie's", "Papa Murphy's", "Little Caesars", "Pizza Inn",
    "Cici's", "Tropical Smoothie", "Smoothie King", "Robeks", "Jamba", "Dunkin",
    "Caribou Coffee", "Scooter's Coffee", "PJ's Coffee", "Krispy Kreme", "Shipley",
    "Saxbys", "MOD Pizza", "Famous Dave's", "Fuddruckers", "Steak n Shake",
    "Boston Market", "El Pollo Loco", "Captain D's", "Long John Silver's",
    "Schlotzsky's", "Quiznos", "Tim Hortons", "Coffee Beanery", "Honey Dew Donuts",
    "Honey Baked Ham", "Round Table Pizza", "Mountain Mike's", "Newk's", "Charleys",
    "Just Salad", "Salata", "Capriotti's", "Erbert and Gerbert's", "Cousins Subs",
    "Penn Station", "MOOYAH", "Smashburger", "Habit Burger", "Lee's Famous Recipe",
    "Donatos",
    # Hospitality
    "Best Western", "Choice Hotels", "Holiday Hospitality", "Days Inns", "Marriott",
    "Hilton", "Wyndham", "Motel 6", "Sonesta", "Extended Stay", "Country Inn",
    # Auto
    "Jiffy Lube", "Midas", "Valvoline", "Meineke", "AAMCO", "Take 5 Oil Change",
    "Maaco", "Tuffy", "Big O Tires", "Firestone Complete",
    # Fitness
    "Anytime Fitness", "Planet Fitness", "Crunch Fitness", "9Round", "Orange Theory",
    "Pure Barre", "F45", "CycleBar", "StretchLab", "Massage Envy",
    "The Joint Chiropractic", "Snap Fitness", "Title Boxing", "Club Pilates",
    "YogaSix", "Row House", "AKT", "Camp Bow Wow", "Dogtopia", "Petland",
    # Education / kids
    "Kumon", "Mathnasium", "Sylvan Learning", "Goddard School", "Primrose",
    "Kiddie Academy", "Code Wiz", "Code Ninjas", "Snapology", "Tutor Doctor",
    "Eye Level",
    # Senior care
    "Home Instead", "BrightStar Care", "Visiting Angels", "Comfort Keepers",
    "Senior Helpers",
    # Retail / specialty
    "The UPS Store", "Postnet", "Mail Boxes", "Great Clips", "Supercuts",
    "Sport Clips", "Cost Cutters", "Fantastic Sams", "Hair Cuttery", "Sola Salon",
    "Phenix Salon", "Wireless Zone", "Cellairis", "Once Upon A Child", "Plato's Closet",
    # Professional
    "Express Employment", "Spherion", "Labor Finders", "Snelling", "PrideStaff",
    "AtWork",
    # Real estate
    "RE/MAX", "Coldwell Banker", "Berkshire Hathaway", "Century 21", "Better Homes",
    "ERA", "Sotheby's International", "Compass",
    # Convenience
    "Travelodge", "Knights Inn", "7-Eleven", "Circle K",
]


def fetch_wi_pool_dynamic() -> list[str] | None:
    """Try the WI activeFilings page. Returns full list or None if maintenance."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"))
            page = ctx.new_page()
            page.goto(ACTIVE_FILINGS_URL, wait_until="networkidle", timeout=30000)
            body = page.inner_text("body")
            browser.close()
        if "not available" in body.lower() and len(body) < 500:
            return None  # maintenance page
        lines = [ln.strip() for ln in body.split("\n") if ln.strip()]
        skip_phrases = {"wisconsin.gov", "state of wisconsin", "department of",
                        "franchise e-filing", "franchise active",
                        "search results", "result count", "all rights", "contact us",
                        "expiration date", "legal name", "name", "trade name",
                        "pick a task", "view status", "dfi home page", "?"}
        names, seen = [], set()
        for ln in lines:
            low = ln.lower()
            if any(p in low for p in skip_phrases) or len(ln) < 3 or len(ln) > 100:
                continue
            if "/" in ln and len(ln) < 12:
                continue
            if ln in seen: continue
            seen.add(ln); names.append(ln)
        return names if len(names) > 100 else None
    except Exception as e:
        print(f"[fetch_wi_pool_dynamic] failed: {e}")
        return None


def enumerate_via_search(seeds: list[str], scraper) -> list[str]:
    """Fallback enumerator: run broad searches on the WI portal and aggregate unique
    legal/trade names. Each search returns up to ~hundreds of results.

    seeds: list of query strings like "LLC", "Inc", "Franchise", etc.
    """
    import re
    names_seen: set[str] = set()
    names: list[str] = []
    skip_words = {"DBA", "DOING BUSINESS AS"}
    for q in seeds:
        try:
            print(f"  enumerating '{q}'...")
            filings = scraper.search(q)
            print(f"    -> {len(filings)} results")
            for f in filings:
                for raw in (f.legal_name, f.trade_name):
                    if not raw: continue
                    # Clean: strip suffixes that don't affect search, take first plausible token
                    cleaned = raw.strip()
                    if cleaned.upper() in skip_words: continue
                    # Use trade name as preferred (more search-friendly), else legal name
                    key = cleaned.lower()
                    if key in names_seen: continue
                    if len(cleaned) < 3 or len(cleaned) > 100: continue
                    names_seen.add(key)
                    names.append(cleaned)
        except Exception as e:
            print(f"    !! '{q}' failed: {e}")
            continue
    return names


def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {"first_run_at": time.strftime("%Y-%m-%d %H:%M:%S"), "brands": {}, "runs": []}


def save_manifest(m: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(m, indent=2), encoding="utf-8")


def existing_brand_names() -> set[str]:
    """Lowercased set of brand_names and legal_names already in DB."""
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


def extract_pdf(pdf_path: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [UV_PATH, "run", "python", "-m", "src.extract", str(pdf_path)],
        capture_output=True, text=True, timeout=900,
    )
    return proc.returncode, proc.stdout[-500:]


def reingest_all() -> bool:
    proc = subprocess.run(
        [UV_PATH, "run", "python", "scripts/ingest_outputs.py"],
        capture_output=True, text=True, timeout=600,
    )
    return proc.returncode == 0


def regenerate_site() -> bool:
    proc = subprocess.run(
        [UV_PATH, "run", "python", "-m", "src.site_gen"],
        capture_output=True, text=True, timeout=300,
    )
    return proc.returncode == 0


def main() -> None:
    run_idx = 0
    manifest = load_manifest()
    if manifest.get("runs"):
        run_idx = len(manifest["runs"])
    run_record = {
        "run_number": run_idx + 1,
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "target": PER_RUN_TARGET,
    }
    print(f"=== Run #{run_record['run_number']} (target {PER_RUN_TARGET} new brands) ===\n")

    # Pool selection — try active filings first, then enumerate via search, then fallback
    dynamic = fetch_wi_pool_dynamic()
    pool: list[str] = []
    pool_sources: list[str] = []
    if dynamic:
        pool.extend(dynamic)
        pool_sources.append(f"wi_active_filings({len(dynamic)})")
        print(f"[pool] dynamic from WI activeFilings: {len(dynamic)} names")
    else:
        print(f"[pool] WI activeFilings unavailable; will enumerate via search at run start")
        # We need a scraper context to enumerate. Build the scraper EARLY for this.
        # Broad enumeration seeds. The WI portal caps results per query (~100-150),
        # so we use many diverse seeds to mosaic coverage. ~50 seeds, ~2 min total
        # at 2.5s/req throttle. Expected unique yield: 800-1500 names.
        ENUMERATE_SEEDS = [
            # Corporate suffixes
            "LLC", "Inc", "Corp", "Limited", "Holdings", "Company",
            # Franchise-jargon
            "Franchise", "Franchising", "SPV", "International", "Worldwide",
            "Group", "Brands", "Systems", "Services", "Solutions", "Concepts",
            "USA", "America", "Global",
            # Food / QSR
            "Pizza", "Burger", "Sub", "Sandwich", "Chicken", "Donut", "Coffee",
            "Tea", "Smoothie", "Bakery", "Grill", "Bar", "Cafe", "Restaurant",
            "Cream", "Yogurt", "Ice", "Cookies", "Snack",
            # Services
            "Auto", "Repair", "Clean", "Maid", "Plumbing", "HVAC", "Electric",
            "Roof", "Paint", "Lawn", "Pest", "Pool", "Window", "Fence", "Floor",
            "Carpet", "Move", "Junk", "Haul",
            # Health/Fitness/Beauty
            "Fitness", "Gym", "Yoga", "Pilates", "Massage", "Hair", "Salon",
            "Spa", "Nails", "Wellness", "Care", "Senior", "Dental", "Vision",
            # Other
            "Hotel", "Motel", "Inn", "Suites", "Resort",
            "Education", "Tutor", "School", "Academy", "Kids", "Learning",
            "Real Estate", "Realty", "Property", "Insurance",
            "Tax", "Print", "Sign", "Mailbox", "Cellular",
            "Tools", "Equipment", "Rental", "Express",
        ]
        with WisconsinScraper(headless=True, rate_limit_sec=RATE_LIMIT_SEC) as enum_scraper:
            enumerated = enumerate_via_search(ENUMERATE_SEEDS, enum_scraper)
        print(f"[pool] enumerated via search: {len(enumerated)} unique names")
        if enumerated:
            pool.extend(enumerated)
            pool_sources.append(f"search_enumeration({len(enumerated)})")
        # Always include the hand-curated list as a safety net
        pool.extend(FALLBACK_POOL)
        pool_sources.append(f"fallback({len(FALLBACK_POOL)})")
    # De-dup the pool itself (case-insensitive)
    seen_pool: set[str] = set()
    unique_pool: list[str] = []
    for n in pool:
        k = n.strip().lower()
        if k in seen_pool: continue
        seen_pool.add(k); unique_pool.append(n)
    pool = unique_pool
    run_record["pool_sources"] = pool_sources
    run_record["pool_size"] = len(pool)
    print(f"[pool] final pool: {len(pool)} unique names from {', '.join(pool_sources)}")

    # Filter: not in DB, not previously tried (successfully or as no_active_filing)
    existing = existing_brand_names()
    tried_names = {b.lower() for b, e in manifest["brands"].items()
                   if e.get("status") in ("ok", "no_active_filing", "duplicate", "extract_error")}
    print(f"[filter] in DB: {len(existing)}, previously-tried: {len(tried_names)}")
    pending: list[str] = []
    seen_lower: set[str] = set()
    for c in pool:
        norm = c.strip().lower()
        if norm in existing or norm in tried_names or norm in seen_lower:
            continue
        seen_lower.add(norm)
        pending.append(c)
    print(f"[filter] untried candidates: {len(pending)}")
    if not pending:
        print(f"[done] no untried candidates remain — pool exhausted")
        return

    run_record["candidates_for_run"] = len(pending)
    success_count = 0

    with WisconsinScraper(headless=True, rate_limit_sec=RATE_LIMIT_SEC) as scraper:
        for i, brand in enumerate(pending, start=1):
            if success_count >= PER_RUN_TARGET:
                print(f"\n[done] hit run target of {PER_RUN_TARGET}")
                break
            t0 = time.time()
            entry: dict = {"brand": brand, "run": run_record["run_number"],
                           "started_at": time.strftime("%Y-%m-%d %H:%M:%S")}
            try:
                filings = scraper.search(brand)
                active = latest_active(filings)
                if not active:
                    entry["status"] = "no_active_filing"
                    entry["n_filings_seen"] = len(filings)
                    manifest["brands"][brand] = entry
                    save_manifest(manifest)
                    print(f"[{i:3d}] {brand}: no Registered filing ({len(filings)} total)")
                    continue

                dl = scraper.download(active, SCRAPE_DEST, dedup_against=SCRAPE_DEST)
                entry.update({
                    "portal_id": active.portal_id,
                    "legal_name": active.legal_name,
                    "trade_name": active.trade_name,
                    "effective_date": active.effective_date,
                    "sha256": dl.sha256,
                    "pdf_path": str(dl.path),
                    "was_duplicate": dl.was_duplicate,
                    "source_url": dl.source_url,
                })
                if dl.was_duplicate:
                    entry["status"] = "duplicate"
                    manifest["brands"][brand] = entry
                    save_manifest(manifest)
                    print(f"[{i:3d}] {brand}: DUPLICATE sha match")
                    continue

                rc, tail = extract_pdf(dl.path)
                entry["extract_returncode"] = rc
                entry["extract_tail"] = tail
                if rc != 0:
                    entry["status"] = "extract_error"
                    manifest["brands"][brand] = entry
                    save_manifest(manifest)
                    print(f"[{i:3d}] {brand}: EXTRACT FAILED rc={rc}")
                    continue

                for line in tail.splitlines():
                    if "Total cost:" in line:
                        entry["extract_cost_usd"] = line.split("$")[-1].strip()
                        break

                entry["status"] = "ok"
                entry["elapsed_sec"] = round(time.time() - t0, 1)
                manifest["brands"][brand] = entry
                save_manifest(manifest)
                success_count += 1
                print(f"[{i:3d}] {brand}: OK  id={active.portal_id}  "
                      f"cost={entry.get('extract_cost_usd','?')}  "
                      f"elapsed={entry['elapsed_sec']}s  ({success_count}/{PER_RUN_TARGET})")
            except Exception as e:
                entry["status"] = "error"
                entry["error"] = repr(e)[:300]
                manifest["brands"][brand] = entry
                save_manifest(manifest)
                print(f"[{i:3d}] {brand}: ERROR {repr(e)[:120]}")

    # Finalize: ingest + regenerate
    print(f"\n[finalize] re-ingesting all extractions...")
    reingest_all()
    print(f"[finalize] regenerating site...")
    regenerate_site()

    run_record["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    run_record["successes"] = success_count
    manifest["runs"].append(run_record)
    save_manifest(manifest)

    total_success = sum(1 for e in manifest["brands"].values() if e.get("status") == "ok")
    print(f"\n[done] run #{run_record['run_number']}: {success_count} new this run, "
          f"{total_success} cumulative")
    print(f"[done] manifest: {MANIFEST}")


if __name__ == "__main__":
    main()
