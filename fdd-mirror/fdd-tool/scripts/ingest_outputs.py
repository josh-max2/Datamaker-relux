"""Scan output/{pdf_stem}/ subdirectories and load all extractions into SQLite.

Discovers FDDs by walking output/. For each, looks up the source PDF in data/ to get
SHA-256, file size, page count. Also tries to find a Phase 1 manifest entry for
WI scrape source_url + portal_id metadata.

Idempotent: re-running re-ingests with replace_* semantics, so JSONs can be edited
and re-ingested without duplicates.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import pypdf

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from src import db


ROOT = Path(".")
OUTPUT_DIR = ROOT / "output"
DATA_DIR = ROOT / "data"
PILOT_MANIFEST = OUTPUT_DIR / "_pilot_wi_home_services.json"


def find_pdf_for_stem(stem: str) -> Path | None:
    """Look in data/ subdirs for a matching PDF."""
    candidates = [
        DATA_DIR / f"{stem}.pdf",
        DATA_DIR / "wi_scrape" / f"{stem}.pdf",
        DATA_DIR / "preflight" / f"{stem}.pdf",
    ]
    for c in candidates:
        if c.exists():
            return c
    # Fallback: any PDF matching stem
    for c in DATA_DIR.rglob(f"{stem}.pdf"):
        return c
    return None


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"    !! couldn't load {path.name}: {e}")
        return None
    # If the file was saved with a parse error wrapper, recover via lenient parser
    if "_parse_error" in data and "_raw" in data:
        from src.claude_client import _parse_json_lenient
        raw = data["_raw"]
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```", 2)[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip().rstrip("`").strip()
        salvaged = _parse_json_lenient(cleaned, raw)
        if salvaged.get("_salvaged") or "_parse_error" not in salvaged:
            print(f"    -> salvaged {path.name} via lenient parser")
            return salvaged
    return data


def derive_filing_state_from_path(pdf_path: Path) -> str:
    parts = {p.lower() for p in pdf_path.parts}
    if "wi_scrape" in parts:
        return "WI"
    # MN preflight + Service Experts / ReBath
    if "preflight" in parts:
        return "MN"
    if "mn" in pdf_path.stem.lower():
        return "MN"
    # Crumbl / Servpro fixtures
    if "yale" in pdf_path.stem.lower():
        return "WI"  # Crumbl Yale FDD is filed in WI (per spec mention)
    return "UNKNOWN"


def derive_industry(legal_name: str, brand_name: str | None) -> str | None:
    """Industry classifier based on name keywords. Rules are ordered —
    more specific patterns come first to avoid being shadowed by generic ones."""
    text = f"{legal_name} {brand_name or ''}".lower()
    rules = [
        # === Food / QSR (now includes prestige brands by name) ===
        (r"crumbl|cookie|bakery|donut|pizza|burger|smoothie|sandwich|food|ramen|restaurant|cafe|coffee|tea|salad|sushi|deli|grill|chicken|taco|bbq|barbecue|ice cream|frozen yogurt|subway|mcdonald|dunkin|wendy|kfc|domino|jersey mike|pizza hut|taco bell|burger king|sonic|arby|chick-?fil-?a", "food-quick-service"),

        # === Fitness / wellness (Planet Fitness, Anytime Fitness, Orangetheory, etc.) ===
        (r"\bfitness\b|gym\b|crossfit|yoga|pilates|orangetheory|anytime fitness|planet fitness|f45|barre|cycle\b|spin\s|massage envy|massage|wellness|chiropract", "fitness-wellness"),

        # === Education / tutoring (Kumon, Mathnasium, Sylvan, Code Ninjas) ===
        (r"kumon|mathnasium|sylvan|huntington learning|code ninjas|tutor|learning center|montessori|primrose|goddard school", "education"),

        # === Tax / financial services (H&R Block, Liberty Tax, Jackson Hewitt) ===
        (r"h&r block|h\.r\.\s?block|liberty tax|jackson hewitt|\btax\b service|tax preparation|cpa|accountant", "tax-financial"),

        # === Hotel / hospitality (Holiday Inn, Hampton, Wyndham, etc.) ===
        (r"hotel|inn\b|motel|hospitality|holiday inn|hampton|wyndham|marriott|hilton|hometowne studios|red roof|days inn|suites\b", "hospitality"),

        # === Retail / convenience (UPS Store, 7-Eleven, Snap-on tools) ===
        (r"ups store|7-?eleven|circle k|snap-?on|matco|mac tools|\btools\b|retail|convenience", "retail-services"),

        # === Property management (Keyrenter, Real Property Mgmt) ===
        (r"property management|property mgmt|\bkeyrenter\b|real property|rental management", "property-management"),

        # === Dry cleaning / laundry (Martinizing) ===
        (r"martinizing|laundry|dry cleaner|dry cleaning", "dry-cleaning"),

        # === Air quality / pest mitigation (Modern PURAIR) ===
        (r"purair|air quality|duct cleaning|indoor air", "home-services-cleaning"),

        # === Real estate (before "homes" generic) ===
        (r"real estate|realty|broker|coldwell|keller williams|remax|re/max|sotheby|properties\b|homesmart|homevestors", "real-estate"),

        # === Automotive ===
        (r"\bauto\b|automotive|collision|carstar|maaco|car wash|oil change|tire|brake|christian brothers", "automotive-services"),

        # === Salon / beauty ===
        (r"salon|hair\s|hairstyl|cut\s|barber|cost cutters|fantastic sams|supercuts|great clips|nail|manicure|spa\b", "salon-beauty"),

        # === Pet services ===
        (r"\bpet\b|aussie pet|dog\s|cat\s|grooming|veterinar|kennel|critter|wildlife", "pet-services"),

        # === Staffing / employment ===
        (r"staffing|employment|workforce|recruit|express services|labor finder|spherion", "staffing-employment"),

        # === IT / tech services ===
        (r"cmit|it solutions|computer|tech\s|technology|cybersec|managed it|geek squad|i\.?t\. ?services", "tech-services"),

        # === Mobility / accessibility ===
        (r"mobility|accessibility|stair lift|stairlift|wheelchair|ramp|amramp|101 mobility", "mobility-accessibility"),

        # === Plumbing ===
        (r"rooter|plumb|drain|water heater|septic|sewer|benjamin franklin", "home-services-plumbing"),

        # === HVAC + duct/vent ===
        (r"hvac|heat\b|air condition|furnace|cooling|service experts|ductz|aire serv|aire-?master|enviro-?master", "home-services-hvac"),

        # === Restoration (before "water" generic, before "cleaning") ===
        (r"restor|water damage|mold|fire damage|servpro|paul davis|1-?800-?water", "home-services-restoration"),

        # === Cleaning (bins, maids, janitor, dryer-vent, plus name-specific) ===
        (r"clean|maid|janitor|jansan|bin blast|dryer vent|carpet|chem-?dry|window gang|stanley steemer|anago|coverall|jan-?pro|servicemaster|city wide|fish window", "home-services-cleaning"),

        # === Roofing / gutters ===
        (r"roof|gutter|chimney|bumble roofing", "home-services-roofing"),

        # === Painting ===
        (r"paint|color|finish|certa\s?pro|five star paint|certapainter", "home-services-painting"),

        # === Handyman / repair (incl. drywall patching) ===
        (r"handy|repair|home services|patch boy|patchmaster|mr\.? fix|fixerupper|glass doctor", "home-services-handyman"),

        # === Moving / junk removal / hauling / waste ===
        (r"junk|\bmove\b|moving|haul|truck|packout|bin king|college hunks|jdog|dumpster|dryve\s?box", "home-services-moving"),

        # === Outdoor / pest / lawn / irrigation ===
        (r"lawn|landscap|grounds|grass|turf|mosquito|pest|insect|fence|tree|irrig|pool|spa|outdoor|arc[hk]a?dec|conserva|grassroots", "home-services-outdoor"),

        # === Senior care / home care / chiropractic ===
        (r"\bcare\b|senior|home aide|comfort|griswold|right at home|caregiver|homewatch|homewell|assist|chiropract|chiroway|homewatchcare|comforcare|carepatrol|assisting hands|griswold home|home care|executive care", "home-services-senior-care"),

        # === Remodeling (bathtub, kitchen, closets, windows, insulation, flooring) ===
        (r"bath|kitchen|closet|insulation|window\b|re-?bath|bath fitter|garage\b|shutter|blind|tile|countertop|gotcha covered|floorcovering|floor coverings", "home-services-remodeling"),

        # === Industrial / B2B supplies (catch-all niche) ===
        (r"winzer|industrial supply|fastener|distributor", "b2b-supplies"),

        # === Custom home builder / construction ===
        (r"alair|custom home|home builder|construction|contractor", "home-services-remodeling"),

        # === Kitchen exhaust / commercial cleaning (HOODZ) ===
        (r"hoodz|kitchen exhaust|exhaust cleaning|commercial kitchen|hood cleaning", "home-services-cleaning"),

        # === Home inspection (HouseMaster, etc.) ===
        (r"housemaster|home inspect|inspection|inspector", "home-services-inspection"),

        # === HVAC commercial maintenance (Linc Service / ABM) ===
        (r"linc service|\babm\b|facility maintenance|building maintenance", "home-services-hvac"),

        # === Generic home services catch-all (House Doctors, Mastercare) ===
        (r"house doctor|mastercare|home doctor", "home-services-handyman"),
    ]
    for pat, cat in rules:
        if re.search(pat, text):
            return cat
    return None


def ingest_one(conn, stem: str, pilot_entry: dict | None) -> bool:
    """Ingest one output/{stem}/ dir. Returns True on success."""
    out_dir = OUTPUT_DIR / stem
    if not out_dir.is_dir():
        return False

    meta = load_json(out_dir / "metadata.json") or {}
    item5 = load_json(out_dir / "item5_initial_fee.json") or {}
    item6 = load_json(out_dir / "item6_ongoing_fees.json") or {}
    item7 = load_json(out_dir / "item7_investment.json") or {}
    item19 = load_json(out_dir / "item19_fpr.json") or {}
    item20 = load_json(out_dir / "item20_outlets.json") or {}

    # PDF lookup
    pdf_path = find_pdf_for_stem(stem)
    if not pdf_path:
        print(f"  !! no PDF found for {stem} — skipping")
        return False

    sha = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    try:
        page_count = len(pypdf.PdfReader(str(pdf_path)).pages)
    except Exception:
        page_count = None

    legal_name = meta.get("legal_name") or pilot_entry and pilot_entry.get("phase_a", {}).get("legal_name") or stem
    brand_name = meta.get("brand_name") or (pilot_entry and pilot_entry.get("phase_a", {}).get("trade_name")) or legal_name
    slug = db.slugify(brand_name or legal_name)

    franchisor_id = db.upsert_franchisor(
        conn,
        pdf_sha256=sha,  # primary dedup key — prevents duplicate franchisor rows
        legal_name=legal_name,
        brand_name=brand_name,
        state_of_inc=meta.get("state_of_inc"),
        website=meta.get("website"),
        industry=derive_industry(legal_name, brand_name),
        slug=slug,
    )

    filing_state = derive_filing_state_from_path(pdf_path)
    source_url = (pilot_entry or {}).get("phase_a", {}).get("source_url") or f"file://{pdf_path.resolve()}"
    issuance = meta.get("issuance_date")  # ISO string like "2026-04-02" or None

    fdd_id = db.upsert_fdd(
        conn,
        franchisor_id=franchisor_id,
        filing_year=meta.get("filing_year") or 0,
        filing_state=filing_state,
        effective_date=issuance,
        source_url=source_url,
        local_path=str(pdf_path),
        pdf_sha256=sha,
        page_count=page_count,
        # Even if the model said "has_item19=True", if the JSON was salvaged
        # we can't actually USE the data. Set the flag based on whether we
        # actually have ingestable records — keeps consistent with the audit
        # gate's has_item19_consistency check.
        has_item19=bool(item19.get("records") and not item19.get("_salvaged")),
        has_item20=bool(item20.get("yearly_summary") or item20.get("state_year_status")),
    )

    # Refuse to ingest item19 records if the JSON was salvaged from a truncated
    # response — those records may be incomplete (missing fields nulled out by
    # the lenient parser) or count-wrong. Force a re-extract instead of
    # silently polluting the DB.
    if item19.get("_salvaged"):
        rec_count = item19.get("_recovered_record_count")
        print(f"  ⚠ item19 was SALVAGED from a truncated response "
              f"({rec_count if rec_count is not None else 'unknown'} recovered records). "
              f"Skipping item19 ingest to avoid bad data. Re-run extract for this FDD.")
        n = 0
    elif item19.get("records"):
        n = db.replace_item19_records(conn, fdd_id, item19["records"])
    else:
        n = 0
    yearly = item20.get("yearly_summary", [])
    state_year = item20.get("state_year_status", [])
    m = db.replace_item20_locations(conn, fdd_id, yearly, state_year)
    db.replace_fees(conn, fdd_id, item5, item6, item7)
    conn.commit()
    print(f"  ok: {brand_name or legal_name}  (slug={slug}, fdd_id={fdd_id}, "
          f"{n} item19 records, {m} item20 rows)")
    return True


def main():
    print("=== Initializing DB ===")
    db.init_db()
    print(f"  -> {db.DB_PATH}")

    # Load pilot manifest if present (gives us source_url + portal_id for WI scraped brands)
    pilot_by_stem: dict[str, dict] = {}
    if PILOT_MANIFEST.exists():
        pilot = json.loads(PILOT_MANIFEST.read_text(encoding="utf-8"))
        for brand, entry in pilot.items():
            pdf_path = entry.get("phase_a", {}).get("pdf_path")
            if pdf_path:
                stem = Path(pdf_path).stem
                pilot_by_stem[stem] = entry

    # Walk output/ dirs (skip files like _pilot_*.json)
    print("\n=== Ingesting extractions ===")
    ok = 0
    failed = 0
    for d in sorted(OUTPUT_DIR.iterdir()):
        if not d.is_dir():
            continue
        with db.get_conn() as conn:
            if ingest_one(conn, d.name, pilot_by_stem.get(d.name)):
                ok += 1
            else:
                failed += 1

    # Summary
    print(f"\n=== Summary ===")
    print(f"  Ingested: {ok}  failed: {failed}")
    with db.get_conn() as conn:
        for table in ("franchisors", "fdds", "item19_records", "item20_locations", "fees_and_investment"):
            n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table}: {n} rows")


if __name__ == "__main__":
    main()
