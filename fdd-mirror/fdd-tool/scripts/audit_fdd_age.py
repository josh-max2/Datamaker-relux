"""FDD age audit — Tier 1.3 of Phase 4 strategy.

For each brand, identify:
  - filing_year used for the brand's currently-shown FDD
  - age in years vs 2026-05-19
  - whether MN/WI has a newer filing we missed

Output:
  - output/_fdd_age_audit.md (human-readable report)
  - output/_fdd_age_audit.csv (machine-readable for further processing)
  - prints summary by bucket: <12mo / 12-18mo / 18-24mo / >24mo
"""
from __future__ import annotations
import csv, sqlite3, sys
from datetime import datetime
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from src.db import DB_PATH

TODAY = datetime(2026, 5, 19)
CURRENT_YEAR = TODAY.year


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # For each franchisor, get the latest fdd (MAX d.id) — that's what site_gen picks
    rows = conn.execute("""
        SELECT fr.slug, fr.brand_name, fr.industry,
               d.id AS fdd_id, d.filing_year, d.filing_state, d.effective_date,
               (SELECT COUNT(*) FROM item19_records WHERE fdd_id=d.id) AS n19,
               (SELECT COUNT(*) FROM item20_locations WHERE fdd_id=d.id) AS n20
        FROM franchisors fr
        JOIN fdds d ON d.id = (SELECT MAX(d2.id) FROM fdds d2 WHERE d2.franchisor_id = fr.id)
        ORDER BY d.filing_year ASC NULLS FIRST, fr.brand_name
    """).fetchall()

    buckets = {"current": [], "1yr": [], "2yr": [], "3yr": [], "older": [], "unknown": []}
    for r in rows:
        fy = r["filing_year"] or 0
        age = CURRENT_YEAR - fy if fy > 0 else 999
        entry = {
            "slug": r["slug"], "brand": r["brand_name"], "industry": r["industry"],
            "filing_year": fy, "filing_state": r["filing_state"], "age_years": age,
            "n19": r["n19"], "n20": r["n20"],
        }
        if fy == 0:
            buckets["unknown"].append(entry)
        elif age == 0:
            buckets["current"].append(entry)
        elif age == 1:
            buckets["1yr"].append(entry)
        elif age == 2:
            buckets["2yr"].append(entry)
        elif age == 3:
            buckets["3yr"].append(entry)
        else:
            buckets["older"].append(entry)

    # Print summary
    total = sum(len(v) for v in buckets.values())
    print(f"FDD AGE AUDIT — {total} brands  (today: {TODAY.date()})")
    print(f"  Current year ({CURRENT_YEAR}):     {len(buckets['current'])} brands")
    print(f"  1 year old ({CURRENT_YEAR-1}):     {len(buckets['1yr'])} brands")
    print(f"  2 years old ({CURRENT_YEAR-2}):    {len(buckets['2yr'])} brands")
    print(f"  3 years old ({CURRENT_YEAR-3}):    {len(buckets['3yr'])} brands")
    print(f"  Older (4+ years):    {len(buckets['older'])} brands ⚠")
    print(f"  Unknown year:        {len(buckets['unknown'])} brands ⚠")
    print()
    print(f"Brands needing refresh consideration:")
    for tag, name in [("2yr", "2 years"), ("3yr", "3 years"), ("older", "4+ years"), ("unknown", "no year")]:
        if buckets[tag]:
            print(f"\n  [{name} old]")
            for e in buckets[tag]:
                print(f"    yr={e['filing_year']:<6} {e['slug']:<35} {e['brand'][:35]}  ({e['industry'] or '—'})")

    # Write markdown report
    out_md = Path("output/_fdd_age_audit.md")
    md = ["# FDD age audit\n",
          f"_Generated {TODAY.date()} — Tier 1.3 of Phase 4 strategy_\n",
          "## Summary\n",
          f"- Total brands: **{total}**",
          f"- Current year ({CURRENT_YEAR}): **{len(buckets['current'])}**",
          f"- 1 year old: **{len(buckets['1yr'])}**",
          f"- 2 years old: **{len(buckets['2yr'])}**",
          f"- 3 years old: **{len(buckets['3yr'])}** ⚠ refresh recommended",
          f"- 4+ years old: **{len(buckets['older'])}** ⚠⚠ urgent refresh",
          f"- Unknown year: **{len(buckets['unknown'])}** ⚠ data quality issue\n"]

    for tag, name in [("3yr", f"3 years old ({CURRENT_YEAR-3})"),
                       ("older", f"4+ years old (≤{CURRENT_YEAR-4})"),
                       ("unknown", "Unknown filing year")]:
        if buckets[tag]:
            md.append(f"\n## {name}\n")
            md.append("| Brand | Year | State | Industry | Item 19 records | Item 20 rows |")
            md.append("|---|---|---|---|---|---|")
            for e in buckets[tag]:
                yr = e['filing_year'] if e['filing_year'] else "—"
                md.append(f"| [{e['brand']}](/brands/{e['slug']}/) | {yr} | {e['filing_state'] or '—'} | {e['industry'] or '—'} | {e['n19']} | {e['n20']} |")
    out_md.write_text("\n".join(md), encoding="utf-8")
    print(f"\nMarkdown report -> {out_md}")

    # Write CSV
    out_csv = Path("output/_fdd_age_audit.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["slug", "brand", "industry", "filing_year", "filing_state", "age_years", "n19", "n20"])
        for tag in ("current", "1yr", "2yr", "3yr", "older", "unknown"):
            for e in buckets[tag]:
                w.writerow([e["slug"], e["brand"], e["industry"] or "", e["filing_year"],
                            e["filing_state"] or "", e["age_years"], e["n19"], e["n20"]])
    print(f"CSV -> {out_csv}")


if __name__ == "__main__":
    main()
