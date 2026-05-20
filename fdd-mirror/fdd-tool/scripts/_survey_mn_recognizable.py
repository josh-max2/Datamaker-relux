"""Pull MN 2025 + 2026 Clean FDDs and identify recognizable brands.

Strategy:
  1. Fetch both years' Clean FDDs (~1000 filings before dedup)
  2. Combine + within-brand dedup keeping the most recent filing per brand
  3. Apply DB filter (skip brands we already have same-or-newer for)
  4. Match against a curated list of recognizable US franchise brand names
  5. Output: candidates.json with all recognized brands, sorted by recency

The curated list is hand-built from major US franchise systems known by
the general public — QSR/food, services, fitness, hospitality, automotive,
retail, etc. It uses normalize_brand_name() keys so 'McDonalds USA, LLC'
matches 'mcdonalds' regardless of legal-entity suffix.
"""
from __future__ import annotations
import json, sqlite3, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.scrapers.minnesota import MinnesotaScraper
from src.dedup import normalize_brand_name
from src.db import DB_PATH

# Curated list of recognizable US franchise brands. Normalize keys.
# Source: training knowledge of major franchise systems (Franchise 500, top
# 200 by outlet count). Each entry is the canonical brand name; the matcher
# normalizes to compare. ~250 brands.
RECOGNIZED_BRANDS = [
    # ===== Food / QSR =====
    "McDonalds", "Burger King", "Wendys", "Subway", "Dominos Pizza", "Pizza Hut",
    "Papa Johns", "Little Caesars", "Hungry Howies", "Marcos Pizza", "Round Table Pizza",
    "KFC", "Taco Bell", "Chick-fil-A", "Popeyes", "Bojangles", "Arbys", "Sonic", "A&W",
    "Carls Jr", "Hardees", "Whataburger", "Five Guys", "Wingstop", "Buffalo Wild Wings",
    "Wing Zone", "Wings Over", "Pollo Tropical", "El Pollo Loco", "Del Taco", "Taco Johns",
    "Moes Southwest Grill", "Qdoba", "Chipotle", "Baja Fresh", "Cafe Rio", "Pancheros",
    "Jersey Mikes", "Jimmy Johns", "Firehouse Subs", "Quiznos", "Penn Station", "Schlotzkys",
    "Charleys", "Tropical Smoothie Cafe", "Smoothie King", "Jamba Juice", "Robeks",
    "Auntie Annes", "Cinnabon", "Krispy Kreme", "Dunkin", "Tim Hortons", "Starbucks",
    "Caribou Coffee", "Scooters Coffee", "7 Brew", "Dutch Bros", "Biggby Coffee",
    "Crumbl", "Insomnia Cookies", "Great American Cookies", "Mrs Fields", "Maggie Moos",
    "Baskin Robbins", "Dairy Queen", "Cold Stone Creamery", "Carvel", "Yogurtland",
    "Menchies", "Tutti Frutti", "Pinkberry", "16 Handles", "Kilwins", "Rita's Italian Ice",
    "IHOP", "Dennys", "Applebees", "Olive Garden", "TGI Fridays", "Friendlys",
    "Cracker Barrel", "Waffle House", "Bob Evans", "Perkins", "Village Inn",
    "Outback Steakhouse", "Texas Roadhouse", "LongHorn Steakhouse", "Ruths Chris",
    "Cheesecake Factory", "Hooters", "Twin Peaks", "Famous Daves",
    "Anytime Fitness", "Planet Fitness", "Snap Fitness", "Orangetheory Fitness",
    "F45 Training", "9Round", "Title Boxing Club", "Crunch Fitness", "Golds Gym",
    "Worlds Gym", "Curves", "Jazzercise", "Pure Barre", "CycleBar", "StretchLab",
    "Club Pilates", "AKT", "Row House", "Camp Bow Wow", "Stretch Zone",
    # ===== Real Estate =====
    "RE/MAX", "Coldwell Banker", "Century 21", "Keller Williams", "Better Homes and Gardens",
    "Berkshire Hathaway HomeServices", "Howard Hanna", "ERA", "Weichert", "Realty Executives",
    "Sothebys International", "Engel & Volkers", "Compass", "EXIT Realty",
    "Property Management Inc", "All County Property Management", "Real Property Management",
    "Renters Warehouse", "HomeVestors", "We Buy Ugly Houses", "Express Homebuyers",
    # ===== Home Services =====
    "Servpro", "PuroClean", "Restoration 1", "Steamatic", "1-800-WATER-DAMAGE",
    "Roto-Rooter", "Mr Rooter", "Rooter-Man", "Benjamin Franklin Plumbing", "Mr Electric",
    "Mr Handyman", "Ace Handyman Services", "House Doctors", "Handyman Connection",
    "Molly Maid", "Merry Maids", "The Maids", "MaidPro", "Maid Right", "MaidBrigade",
    "Two Maids", "Heaven's Best", "Chem-Dry", "Stanley Steemer", "Oxi Fresh",
    "Coverall", "Anago", "Vanguard Cleaning Systems", "Jan-Pro", "City Wide",
    "1-800-GOT-JUNK", "Junk King", "College HUNKS Hauling Junk", "JDog Junk Removal",
    "Two Men and a Truck", "Bellhops", "PODS",
    "Bath Fitter", "Re-Bath", "ReBath", "Five Star Bath Solutions", "Granite Transformations",
    "Kitchen Tune-Up", "Closet Factory", "California Closets", "Tailored Living",
    "Closets by Design", "Budget Blinds", "3 Day Blinds", "Bumble Bee Blinds",
    "Mosquito Joe", "Mosquito Squad", "Mosquito Authority", "Mosquito Shield",
    "TruGreen", "Lawn Doctor", "Spring-Green", "Weed Man", "U.S. Lawns", "Lawn Squad",
    "Massage Envy", "Hand & Stone", "Massage Heights", "Elements Massage",
    "Great Clips", "Supercuts", "SportClips", "Fantastic Sams", "Cost Cutters",
    "Hair Cuttery", "Drybar", "Floyds 99", "European Wax Center", "Waxing the City",
    "Sola Salon Studios", "Cookie Cutters",
    "Maaco", "AAMCO", "Midas", "Meineke", "Jiffy Lube", "Valvoline Instant Oil Change",
    "Big O Tires", "Tuffy Tire & Auto", "Christian Brothers Automotive", "Honest-1 Auto Care",
    "Pep Boys", "Express Oil Change", "Take 5 Oil Change",
    # ===== Hospitality (hotel franchise systems) =====
    "Hilton", "Marriott", "Holiday Inn", "Days Inn", "Best Western", "Comfort Inn",
    "Hampton Inn", "Hyatt", "IHG", "Wyndham", "Choice Hotels", "La Quinta",
    "Super 8", "Motel 6", "Red Roof Inn", "HomeTowne Studios",
    # ===== Retail / Convenience =====
    "7-Eleven", "Circle K", "Cumberland Farms", "Wawa",
    "UPS Store", "FedEx Office", "Mail Boxes Etc", "Goin Postal", "Postal Annex",
    "Edible Arrangements", "Wireless Zone",
    "Aaron's", "Rent-A-Center", "Buddy's Home Furnishings",
    # ===== Tutoring / Education =====
    "Kumon", "Sylvan Learning", "Mathnasium", "Huntington Learning", "Tutor Doctor",
    "Eye Level Learning", "Best Brains", "Code Wiz", "Mad Science",
    "Goddard School", "Primrose Schools", "Kiddie Academy", "Childrens Lighthouse",
    "Lightbridge Academy", "Bright Horizons", "Kindercare", "La Petite Academy",
    "Code Ninjas", "i9 Sports", "Soccer Shots", "British Soccer", "JumpBunch",
    # ===== Financial / Business Services =====
    "H&R Block", "Jackson Hewitt", "Liberty Tax", "ATAX", "Daniel Ahart",
    "Express Employment", "Spherion", "Spring Personnel", "Snelling",
    "Snap-on Tools", "Matco Tools", "Mac Tools", "Cornwell Tools",
    # ===== Pets =====
    "Petland", "Camp Bow Wow", "Dogtopia", "K9 Resorts", "Bark Busters", "Hounds Town",
    "Pet Supplies Plus", "Aussie Pet Mobile", "PETSMART",
    # ===== Specialty / Other =====
    "FastSigns", "Signs Now", "Speedpro Imaging", "Minuteman Press",
    "AlphaGraphics", "Tutor Time", "Mr. Transmission",
    "1-800-PACK-RAT", "1-800-PACKOUTS", "PODS", "U-Haul",
    "Junkluggers", "Dumpster Dudez",
    # ===== Added round 2 (mined from unrecognized output) =====
    "CruiseOne", "Brusters Real Ice Cream", "Bruster's",
    "Speed Queen Laundry", "Red Mango", "Visiting Angels", "Tint World",
    "California Pizza Kitchen", "CPK", "Cupbop", "Mighty Dog Roofing",
    "Lees Sandwiches", "Cheba Hut", "Window World", "Right at Home",
    "Batteries Plus", "Urban Air", "Urban Air Adventure Park", "Studio 6",
    "PJs Coffee", "Chicken Salad Chick", "Griswold Home Care",
    "Wings Etc", "Any Lab Test Now", "Bambu", "Smoothie Factory",
    "Synergy Home Care", "Everbowl", "Bishops", "Bostons Pizza",
    "Beard Papas", "Rakkan Ramen", "Zips Dry Cleaners",
    "Pizza Ranch", "Panda Express", "Peets Coffee",
    "More Space Place", "Closet & Storage Concepts",
    "Original Pancake House", "Oasis Senior Advisors", "Frenchies",
    "Champps Kitchen", "Mooyah", "Rusty Taco", "Sharetea",
    "Soccer Stars", "Super Soccer Stars", "Amazing Athletes",
    "Hello Garage", "Hello Sugar", "BrightStar Care", "Lash Lounge",
    "School of Rock", "TruBlue", "Angry Crab Shack",
    "Plumbing Paramedics", "Pestmaster", "Sir Grout",
    "Fit Body Boot Camp", "Camp Transformation Center", "Bio-One",
    "Planet Smoothie", "Toppers Pizza", "Miracle Method",
    "Men in Kilts", "WaveMax Laundry", "Grease Monkey",
    "Padgett Business Services", "Speedee Oil Change", "Wayback Burgers",
    "Card My Yard", "Paris Baguette", "World Gym", "Great Steak",
    "Maui Wowi", "Samurai Sams", "Thai Express", "SweetFrog",
    "Wetzels Pretzels", "Blimpie", "Taco Time", "Vs Barbershop",
    "Teriyaki Madness", "Rocket Fizz", "Papa Murphys", "Charles Schwab",
    "Zerorez", "Ziggis Coffee", "Black Bear Diner", "uBreakiFix",
    "HOTWORX", "Ding Tea", "Hot Dog on a Stick", "A Place at Home",
    "Pretzelmaker", "Fatburger", "Fazolis", "Marble Slab Creamery",
    "Johnny Rockets", "Bloomin Blinds", "Gong cha", "Yoga Six",
    "Arthur Murray", "Aqua-Tots", "Roosters Mens Grooming", "SmartStyle",
    "Godfathers Pizza", "AFC American Family Care", "Regus",
    "U-Save Car Rental", "Young Rembrandts", "Bento Sushi",
    "Fleet Feet", "Do It Best", "We Insure", "Motto Mortgage",
    "MassageLuxe", "EOS Worldwide", "Apricot Lane Boutique",
    "Manchu Wok", "Office Evolution", "Venture X", "Sir Speedy",
    "PayMore", "Wag N Wash", "Topgolf", "Wild Birds Unlimited",
    "Mr Mister", "Mr Mister Roofing", "Glass Doctor",
    "GYU-KAKU", "PIZZA INN", "Pizza Inn", "Wayback",
    "Fantastic Sams", "Sport Clips", "Massage Heights",
    "Goosehead Insurance", "Brightway Insurance",
    "Christian Brothers", "Honest 1", "Take 5",
]

# Brands that look recognized via substring matching but actually aren't
# franchise-retail. Filter them out after matching.
FALSE_POSITIVE_KEYS = {
    "compass",  # COMPASS GROUP USA / CANTEEN — institutional food service, not retail franchise
}

# Build the recognition set with normalized keys.
# Filter out very short keys to avoid false-positive substring matches
# (e.g. "era" would match "operator", "ihop" matches a chunk of many words).
# Anything under 5 chars only matches via exact equality.
_ALL_KEYS = {normalize_brand_name(b) for b in RECOGNIZED_BRANDS if b}
RECOGNIZED_KEYS_SUBSTRING = {k for k in _ALL_KEYS if len(k) >= 5}
RECOGNIZED_KEYS_EXACT = {k for k in _ALL_KEYS if len(k) < 5}
print(f"Recognition list: {len(RECOGNIZED_BRANDS)} brand names → "
      f"{len(RECOGNIZED_KEYS_SUBSTRING)} substring + {len(RECOGNIZED_KEYS_EXACT)} exact-only\n")


def find_brand_match(franchise_name: str, franchisor: str) -> str | None:
    """Return the matched recognition key, or None.

    Matches recognized brand keys against both the franchise_name (trade name)
    and the franchisor (legal entity) — many filings have the brand in the
    legal entity ("MIDAS INTERNATIONAL, LLC" contains "midas") while the
    franchise_name is a long marketing string.

    Short keys (<5 chars) use prefix-only match (e.g. "kfc" matches
    "kfctraditional" but not random middles) to keep false positives down.
    Longer keys use substring anywhere.
    """
    candidates = (normalize_brand_name(franchise_name), normalize_brand_name(franchisor))
    for cand in candidates:
        if not cand:
            continue
        # Exact match wins
        if cand in _ALL_KEYS:
            return cand
        # Substring match for longer brand keys
        for key in RECOGNIZED_KEYS_SUBSTRING:
            if key in cand:
                return key
        # Prefix-only match for short keys (3-4 chars) to avoid false positives
        for key in RECOGNIZED_KEYS_EXACT:
            if cand.startswith(key):
                return key
    return None


def db_has_same_or_newer(brand_latest: dict[str, int], candidate_key: str,
                         franchise_name: str, franchisor: str, year: int) -> int | None:
    """Return the DB's filing_year if we already have this brand at >= year.

    Uses three lookup strategies to bridge the normalization gap between the
    recognition list keys ('griswoldhomecare') and the DB's stored
    brand_name_keys ('griswold'):
      1. Direct match on the canonical candidate key
      2. Match on normalize_brand_name(franchise_name) and (franchisor)
      3. Fuzzy substring — any DB key that is a substring of one of the
         normalized lookups (or vice versa), provided len ≥ 4 chars (avoids
         tiny substrings producing accidental matches)
    """
    norm_fn = normalize_brand_name(franchise_name)
    norm_fr = normalize_brand_name(franchisor)
    lookups = {candidate_key, norm_fn, norm_fr} - {""}
    # Direct match
    for k in lookups:
        if k in brand_latest:
            return brand_latest[k]
    # Fuzzy substring — DB key inside our lookup or vice versa
    for db_k, db_year in brand_latest.items():
        if len(db_k) < 4:
            continue
        for lk in lookups:
            if len(lk) < 4:
                continue
            if db_k == lk or db_k in lk or lk in db_k:
                return db_year
    return None


def existing_brand_latest_year(conn):
    rows = conn.execute("""
        SELECT fr.brand_name_key, MAX(d.filing_year) AS latest_year
        FROM franchisors fr JOIN fdds d ON d.franchisor_id = fr.id
        WHERE fr.brand_name_key IS NOT NULL AND d.filing_year IS NOT NULL
        GROUP BY fr.brand_name_key
    """).fetchall()
    return {r[0]: int(r[1]) for r in rows if r[1]}


def main():
    conn = sqlite3.connect(DB_PATH)
    brand_latest = existing_brand_latest_year(conn)

    all_filings = []
    for year in (2026, 2025, 2024):
        print(f"Fetching MN {year} Clean FDDs...")
        with MinnesotaScraper() as s:
            f = s.search(year=year, document_type="Clean FDD")
        print(f"  {len(f)} filings.")
        all_filings.extend(f)
    print(f"\nTotal raw filings: {len(all_filings)}")

    # Per filing, try to match against recognition list (substring on either
    # franchise_name or franchisor). When matched, the key is the canonical
    # recognition key (e.g. multiple Choice Hotels brand-program filings all
    # collapse to "choicehotels"). When unmatched, key is the franchise_name
    # normalized (kept for later inspection but won't pass the filter).
    typed = []
    for f in all_filings:
        match_key = find_brand_match(f.franchise_name or "", f.franchisor or "")
        fallback_key = normalize_brand_name(f.franchise_name or f.franchisor)
        typed.append((match_key or fallback_key, match_key is not None, f))

    # Within-brand dedup keyed on canonical match (so all Choice Hotels child
    # brand filings collapse to one). Keep the most-recently-added.
    by_brand: dict[str, tuple[bool, object]] = {}
    for key, is_recognized, f in typed:
        if not key:
            continue
        existing = by_brand.get(key)
        if existing is None:
            by_brand[key] = (is_recognized, f)
        else:
            _, existing_f = existing
            new_sort = (f.added_on_iso or "", f.received_date_iso or "")
            old_sort = (existing_f.added_on_iso or "", existing_f.received_date_iso or "")
            if new_sort > old_sort:
                by_brand[key] = (is_recognized, f)

    print(f"After within-brand dedup (by canonical key): {len(by_brand)} distinct brands\n")

    # Apply DB filter (skip same-or-newer) + recognition filter
    recognized = []
    skipped_have_newer = 0
    skipped_not_recognized = 0
    skipped_false_positive = 0
    for key, (is_recognized, f) in by_brand.items():
        # Skip if not on recognition list
        if not is_recognized:
            skipped_not_recognized += 1
            continue
        # Skip explicit false-positive keys
        if key in FALSE_POSITIVE_KEYS:
            skipped_false_positive += 1
            continue
        # Cross-check DB via fuzzy lookup (DB stores brand-only keys like
        # 'griswold' while our recognition key is 'griswoldhomecare')
        existing_year = db_has_same_or_newer(
            brand_latest, key, f.franchise_name or "", f.franchisor or "", f.year)
        if existing_year is not None and existing_year >= f.year:
            skipped_have_newer += 1
            continue
        recognized.append((key, f, existing_year))

    # Sort recognized by recency
    recognized.sort(
        key=lambda kfx: (kfx[1].added_on_iso or "0000-00-00",
                          kfx[1].received_date_iso or "0000-00-00"),
        reverse=True,
    )

    print(f"Filter results:")
    print(f"  Skipped (have same-or-newer in DB) : {skipped_have_newer}")
    print(f"  Skipped (not on recognition list)  : {skipped_not_recognized}")
    print(f"  Skipped (manual false-positive)    : {skipped_false_positive}")
    print(f"  RECOGNIZED + new/update            : {len(recognized)}")

    # Also dump the unrecognized franchise_names so we can spot brands missed
    # in the recognition list (sorted by recency for quick eyeball review).
    unrecognized_sorted = sorted(
        [f for key, (is_rec, f) in by_brand.items() if not is_rec
         and not (brand_latest.get(key) is not None and brand_latest[key] >= f.year)],
        key=lambda f: (f.added_on_iso or "", f.received_date_iso or ""),
        reverse=True,
    )
    Path("output/_mn_unrecognized_brands.txt").write_text(
        "\n".join(f"{f.franchise_name:<40} | {f.franchisor[:50]:<52} | {f.added_on}"
                  for f in unrecognized_sorted),
        encoding="utf-8",
    )
    print(f"  (unrecognized list -> output/_mn_unrecognized_brands.txt for review)")

    n_update = sum(1 for _, _, ey in recognized if ey is not None)
    n_new = len(recognized) - n_update
    print(f"     of which NEW                    : {n_new}")
    print(f"     of which UPDATE existing brand  : {n_update}\n")

    print("Recognizable candidates (top 30):")
    for i, (key, f, existing_year) in enumerate(recognized[:30], 1):
        tag = f"UPD {existing_year}→{f.year}" if existing_year else "NEW         "
        print(f"  {i:>3}. [{tag}] {f.franchisor[:50]:<52} added={f.added_on}  rec={f.received_date}")
    if len(recognized) > 30:
        print(f"  ... and {len(recognized) - 30} more recognized brands")

    # Write the full list for the user to review
    out = Path("output/_mn_recognized_candidates.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps([
        {
            "rank": i,
            "key": key,
            "franchisor": f.franchisor,
            "franchise_name": f.franchise_name,
            "year": f.year,
            "added_on": f.added_on_iso,
            "received_date": f.received_date_iso,
            "previous_year": existing_year,
            "is_update": existing_year is not None,
            "guid": f.guid,
            "document_id": f.document_id,
            "download_url": f.download_url,
        } for i, (key, f, existing_year) in enumerate(recognized, 1)
    ], indent=2), encoding="utf-8")
    print(f"\nFull list -> {out}")


if __name__ == "__main__":
    main()
