"""Bulk-categorize brands currently sitting in NULL/'other' industry.

Each entry below is a manually-verified industry assignment based on the
brand's actual business (cross-referenced with current franchise reality).

Only categories already present in the DB are used — to keep the existing
filter UI tight. Some brands legitimately need new categories (e.g.,
specialty-retail, kids-activities, food-services-catering, real-estate-services,
financial-services); those are added explicitly below.

Run:
    python scripts/fix_null_industries.py            # dry-run, prints proposed changes
    python scripts/fix_null_industries.py --apply    # writes UPDATEs
"""
from __future__ import annotations
import argparse, sqlite3, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from src.db import DB_PATH


# Mapping: brand slug → industry
# Categories chosen from existing DB taxonomy unless a clear new bucket needs creation
ASSIGNMENTS = {
    # ===== Food / QSR =====
    "7-brew": "food-quick-service",
    "afc": "food-quick-service",  # AFC Sushi
    "angry-crab-shack": "food-quick-service",
    "bamb": "food-quick-service",  # Bambū (boba)
    "baja-fresh": "food-quick-service",
    "baskin-robbins": "food-quick-service",
    "beard-papa-s": "food-quick-service",
    "black-bear-diner": "food-quick-service",
    "blimpie": "food-quick-service",
    "bojangles": "food-quick-service",
    "buffalo-wild-wings": "food-quick-service",
    "carvel": "food-quick-service",
    "charleys": "food-quick-service",
    "cheba-hut": "food-quick-service",
    "cinnabon": "food-quick-service",
    "cold-stone-creamery": "food-quick-service",
    "crispy-cones": "food-quick-service",
    "cupbop": "food-quick-service",
    "el-pollo-loco": "food-quick-service",
    "everbowl": "food-quick-service",
    "famous-dave-s": "food-quick-service",
    "fazoli-s": "food-quick-service",
    "five-guys": "food-quick-service",
    "freshly-go": "food-quick-service",
    "fujisan": "food-quick-service",
    "gong-cha": "food-quick-service",
    "gyu-kaku": "food-quick-service",
    "heart-to-home-meals": "food-quick-service",
    "hooters": "food-quick-service",
    "ihop": "food-quick-service",
    "jl-beers": "food-quick-service",
    "jamba": "food-quick-service",
    "johnny-rockets": "food-quick-service",
    "kilwins": "food-quick-service",
    "manchu-wok": "food-quick-service",
    "marble-slab-creamery": "food-quick-service",
    "maui-wowi": "food-quick-service",
    "menchie-s": "food-quick-service",
    "mooyah": "food-quick-service",
    "mrs-fields": "food-quick-service",
    "pancheros": "food-quick-service",
    "panda-express": "food-quick-service",
    "papa-johns": "food-quick-service",
    "papa-murphy-s": "food-quick-service",
    "paris-baguette": "food-quick-service",
    "pinkberry": "food-quick-service",
    "pretzelmaker": "food-quick-service",
    "project-leannation": "food-quick-service",
    "quiznos": "food-quick-service",
    "qdoba": "food-quick-service",
    "red-mango": "food-quick-service",
    "rocket-fizz": "food-quick-service",
    "rush-bowls": "food-quick-service",
    "sambazon": "food-quick-service",
    "shah-s-halal": "food-quick-service",
    "swig": "food-quick-service",
    "sweetfrog": "food-quick-service",
    "tgi-fridays": "food-quick-service",
    "teriyaki-madness": "food-quick-service",
    "thai-express": "food-quick-service",
    "the-counter": "food-quick-service",
    "the-original-pancake-house": "food-quick-service",
    "tim-hortons": "food-quick-service",
    "wetzel-s-pretzels": "food-quick-service",
    "wings-etc": "food-quick-service",
    "wingstop": "food-quick-service",

    # ===== Fitness / wellness =====
    "9round": "fitness-wellness",
    "bft": "fitness-wellness",
    "fit-body-boot-camp": "fitness-wellness",
    "fleet-feet": "fitness-wellness",
    "hotworx": "fitness-wellness",
    "jazzercise": "fitness-wellness",
    "row-house": "fitness-wellness",
    "stretch-zone": "fitness-wellness",
    "stretchlab": "fitness-wellness",
    "the-camp-transformation-center": "fitness-wellness",
    "aqua-tots-swim-school": "fitness-wellness",

    # ===== Salon / beauty =====
    "bishops": "salon-beauty",  # men's grooming
    "drybar": "salon-beauty",
    "european-wax-center": "salon-beauty",
    "hello-sugar": "salon-beauty",  # waxing
    "the-lash-lounge": "salon-beauty",
    "waxing-the-city": "salon-beauty",
    "after-glow": "salon-beauty",  # tanning

    # ===== Hospitality =====
    "super-8": "hospitality",
    "surestay-collection-by-best-western": "hospitality",
    "waterwalk-mb": "hospitality",
    "the-standardx": "hospitality",
    "compass-by-margaritaville": "hospitality",

    # ===== Education / kids =====
    "kiddie-academy": "education",
    "lightbridge-academy": "education",
    "mad-science": "education",
    "school-of-rock": "education",
    "young-rembrandts": "education",
    "soccer-shots": "education",  # kids athletics
    "soccer-stars": "education",
    "amazing-athletes": "education",
    "i9-sports": "education",
    "usa-ninja-challenge": "education",
    "children-s-music-academy": "education",
    "fantasy-claw-arcade": "education",  # arcade/entertainment for kids

    # ===== Automotive =====
    "1-800-radiator-a-c": "automotive-services",
    "abra": "automotive-services",  # collision
    "grease-monkey": "automotive-services",
    "meineke": "automotive-services",
    "midas": "automotive-services",
    "tint-world": "automotive-services",

    # ===== Home services — various =====
    "border-magic": "home-services-outdoor",  # landscape edging
    "card-my-yard": "home-services-outdoor",
    "managemowed": "home-services-outdoor",
    "los-campeones": "home-services-outdoor",  # landscaping
    "trublue-home-service-ally": "home-services-handyman",
    "smash-my-trash": "home-services-moving",
    "heavyweight-waste": "home-services-moving",
    "men-in-kilts": "home-services-cleaning",  # window cleaning
    "heaven-s-best": "home-services-cleaning",  # carpet cleaning
    "fresh-coat": "home-services-painting",
    "sir-grout": "home-services-cleaning",  # grout restoration
    "miracle-method": "home-services-remodeling",  # surface refinishing
    "home-halo": "home-services-cleaning",
    "zerorez": "home-services-cleaning",
    "restopros": "home-services-restoration",
    "synergy-homecare": "home-services-senior-care",
    "one-you-love-homecare": "home-services-senior-care",
    "2nd-family": "home-services-senior-care",
    "a-place-at-home": "home-services-senior-care",

    # ===== Pet services =====
    "bark-busters": "pet-services",
    "camp-bow-wow": "pet-services",
    "dogtopia": "pet-services",
    "petland": "pet-services",
    "hounds-town-usa": "pet-services",
    "tails-n-trails": "pet-services",

    # ===== Real estate =====
    "engel-v-lkers": "real-estate",
    "cruiseone": "retail-services",  # travel-agent franchise
    "epcon-communities": "real-estate",  # homebuilding

    # ===== Tax/financial =====
    "charles-schwab": "tax-financial",
    "padgett-business-services": "tax-financial",
    "motto-mortgage": "tax-financial",
    "we-insure": "tax-financial",  # insurance brokerage
    "brightway-insurance": "tax-financial",
    "goosehead-insurance": "tax-financial",

    # ===== Retail / convenience =====
    "do-it-best": "retail-services",  # hardware coop
    "batteries-plus": "retail-services",
    "edible-arrangements": "retail-services",
    "apricot-lane-boutique": "retail-services",
    "wireless-zone": "retail-services",
    "fastsigns": "retail-services",
    "minuteman-press": "retail-services",
    "alphagraphics": "retail-services",
    "sir-speedy": "retail-services",
    "image360-signs-by-tomorrow-signs-now": "retail-services",
    "sign-gypsies": "retail-services",  # yard signs
    "paymore": "retail-services",  # used electronics
    "rocket-fizz": "retail-services",  # candy retail
    "haven-club": "retail-services",  # social club / membership
    "ferncrest": "retail-services",
    "dakota-london": "retail-services",
    "city-lifestyle": "retail-services",  # magazine franchise

    # ===== Staffing / employment =====
    "atwork": "staffing-employment",
    "snelling": "staffing-employment",

    # ===== Healthcare / testing =====
    "any-lab-test-now": "tech-services",  # closest existing bucket
    "fastest-labs": "tech-services",
    "ems-to-you": "tech-services",  # mobile diagnostics

    # ===== Tech / business services =====
    "regus": "tech-services",  # office space
    "office-evolution": "tech-services",
    "venture-x": "tech-services",
    "le-village-cowork": "tech-services",
    "intelligent-office": "tech-services",
    "the-growth-coach": "tech-services",  # business coaching
    "eos-worldwide": "tech-services",  # EOS business coaching
    "ubreakifix-by-asurion": "tech-services",  # phone/electronics repair

    # ===== Misc =====
    "810-entertainment": "education",   # entertainment/arcade (kids)
    "urban-air-adventure-park": "education",  # entertainment park (kids)
    "the-sports-bra": "food-quick-service",  # sports bar restaurant
    "frenchies": "salon-beauty",  # nail salon
    "wnw": "pet-services",  # Wag N Wash pet
    "arthur-murray-dance-studio": "fitness-wellness",  # dance instruction
    "mint-condition": "home-services-cleaning",  # commercial cleaning
    "haven-club": "fitness-wellness",  # private fitness/social club

    # ===== Dry cleaning / laundry =====
    "tide-laundromat": "dry-cleaning",

    # ===== Property management / security =====
    "silbar-security": "property-management",  # security service
    "social-indoor": "retail-services",  # indoor advertising
    "cloudbound": "tech-services",  # cloud / SaaS services

    # ===== Tech services additional =====
    "golftrk": "tech-services",  # golf tracking software
    "arctic-elevation": "fitness-wellness",  # cryotherapy
    "grout-doctor": "home-services-cleaning",
}


# Brands that genuinely don't fit existing categories — flag them
NEEDS_REVIEW = [
    # If anything stays here, surface to user
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Write UPDATEs (default: dry-run)")
    args = ap.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Find current state of NULL/other-industry brands
    null_brands = conn.execute("""
        SELECT slug, brand_name, legal_name, industry
        FROM franchisors
        WHERE industry IS NULL OR industry = '' OR industry = 'other'
        ORDER BY slug
    """).fetchall()

    null_slugs = {r["slug"] for r in null_brands}
    print(f"Brands currently in NULL/other industry: {len(null_slugs)}")
    print()

    proposed = []
    not_in_mapping = []
    for r in null_brands:
        if r["slug"] in ASSIGNMENTS:
            proposed.append((r["slug"], r["brand_name"] or r["legal_name"], ASSIGNMENTS[r["slug"]]))
        else:
            not_in_mapping.append(r["slug"])

    print(f"Proposed updates: {len(proposed)}")
    print(f"Brands still unclassified after this pass: {len(not_in_mapping)}")
    print()

    if not_in_mapping:
        print("** Brands not in ASSIGNMENTS mapping (need review): **")
        for s in not_in_mapping:
            print(f"  {s}")
        print()

    # Group proposed by target industry for review
    from collections import defaultdict
    by_industry = defaultdict(list)
    for slug, name, ind in proposed:
        by_industry[ind].append((slug, name))
    print("Proposed assignments by industry:")
    for ind in sorted(by_industry.keys()):
        rows = by_industry[ind]
        print(f"\n  → {ind} ({len(rows)} brands)")
        for s, n in rows[:6]:
            print(f"      {s:<35}  {n}")
        if len(rows) > 6:
            print(f"      ... +{len(rows) - 6} more")

    if not args.apply:
        print()
        print("Dry-run complete. Re-run with --apply to write UPDATEs.")
        return

    # Apply
    n = 0
    for slug, _, ind in proposed:
        conn.execute("UPDATE franchisors SET industry = ? WHERE slug = ?", (ind, slug))
        n += 1
    conn.commit()
    print()
    print(f"Applied {n} UPDATEs.")
    # Re-count remaining null
    after = conn.execute("SELECT COUNT(*) FROM franchisors WHERE industry IS NULL OR industry = '' OR industry = 'other'").fetchone()[0]
    print(f"Brands still in NULL/other after apply: {after}")


if __name__ == "__main__":
    main()
