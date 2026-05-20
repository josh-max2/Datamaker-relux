"""Flag any brand pages where charts/data look broken AND compute a per-brand
quality score (0-20).

Score components (each is 0-N points):
  - has_fees           (3) — initial fee disclosed
  - has_royalty        (2) — royalty %
  - has_investment     (3) — total investment range
  - has_item19         (3) — Item 19 records present + chartable
  - has_item20_states  (3) — per-state outlet rows (≥3 US states)
  - has_industry       (2) — industry classified (not NULL)
  - no_parse_errors    (2) — no _parse_error sentinels in source JSONs
  - no_quality_flag    (2) — db.replace_fees did not reject any field

Flags surfaced separately:
  - Breakeven > 20y on low end, > 30y on high end (suspicious)
  - Item 19 chart duplicate labels
  - has_item19=true but no chart rendered for 3+ chartable records
  - NULL industry
  - fees quality_flag (range violations from db.replace_fees)
"""
from __future__ import annotations
import json
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from src import db, site_gen


def _has_parse_errors(slug: str, conn) -> bool:
    """Check the source JSON files for any _parse_error sentinels."""
    legal = conn.execute("SELECT local_path FROM fdds f JOIN franchisors fr ON f.franchisor_id=fr.id WHERE fr.slug=? LIMIT 1", (slug,)).fetchone()
    if not legal: return False
    pdf_path = Path(legal[0])
    out_dir = Path("output") / pdf_path.stem
    if not out_dir.exists(): return False
    for f in ("metadata.json", "item5_initial_fee.json", "item6_ongoing_fees.json",
              "item7_investment.json", "item19_fpr.json", "item20_outlets.json"):
        p = out_dir / f
        if not p.exists(): continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            if "_parse_error" in d or "_read_error" in d:
                return True
        except Exception:
            return True
    return False


def quality_score(brand_detail: dict, parse_errs: bool, quality_flag: str | None) -> tuple[int, dict]:
    """Return (score 0-20, component breakdown)."""
    fees = brand_detail.get("fees") or {}
    item19 = brand_detail.get("item19_records") or []
    top_states = brand_detail.get("top_states") or []
    industry = (brand_detail.get("brand") or {}).get("industry")
    fdd = brand_detail.get("latest_fdd") or {}

    components = {
        "fees":         3 if (fees.get("initial_franchise_fee_low") or fees.get("initial_franchise_fee_high")) else 0,
        "royalty":      2 if fees.get("royalty_pct") else 0,
        "investment":   3 if (fees.get("total_investment_low") and fees.get("total_investment_high")) else 0,
        "item19":       3 if (fdd.get("has_item19") and len(item19) >= 2) else (1 if fdd.get("has_item19") else 0),
        "item20_states":3 if len(top_states) >= 5 else (1 if len(top_states) >= 1 else 0),
        "industry":     2 if industry else 0,
        "no_parse":     2 if not parse_errs else 0,
        "no_qual_flag": 2 if not quality_flag else 0,
    }
    return sum(components.values()), components


def main():
    conn = sqlite3.connect(str(db.DB_PATH))
    conn.row_factory = sqlite3.Row
    brands = conn.execute("SELECT slug, brand_name FROM franchisors ORDER BY brand_name").fetchall()

    issues_by_brand: dict[str, list[str]] = {}
    scores: list[tuple[str, int, dict, str | None]] = []  # (name, score, components, slug)

    for b in brands:
        slug = b["slug"]
        name = b["brand_name"]
        flags = []
        try:
            d = site_gen.fetch_brand_detail(conn, slug)
            if not d:
                flags.append("fetch_brand_detail returned None")
                continue
            be = d.get("breakeven") or {}
            chart = d.get("item19_chart_data") or {}

            # 1. Breakeven > 20 years
            hi = be.get("high_years")
            lo = be.get("low_years")
            if lo and lo > 20:
                flags.append(f"breakeven_low={lo}y (suspicious)")
            if hi and hi > 30:
                flags.append(f"breakeven_high={hi}y (suspicious)")

            # 2. Duplicate chart labels
            labels = chart.get("labels") or []
            if labels:
                dup = len(labels) - len(set(labels))
                if dup > 0:
                    flags.append(f"chart_duplicate_labels={dup}")

            # 3. Brand with NULL industry
            brand_industry = d.get("brand", {}).get("industry")
            if not brand_industry:
                flags.append("industry=NULL")

            # 4. fees quality_flag (range violations from db.replace_fees)
            quality_flag = (d.get("fees") or {}).get("quality_flag")
            if quality_flag:
                flags.append(f"fees_quality_flag={quality_flag[:60]}")

            # 5. Item 19 says has_item19=true but no chart
            import re as _re
            fdd = d.get("latest_fdd") or {}
            if fdd.get("has_item19") and not labels:
                records = d.get("item19_records") or []
                currency_metrics = {"gross_sales", "total_revenue", "gross_profit", "net_profit", "ebitda"}
                chartable = [
                    r for r in records
                    if r.get("metric_name") in currency_metrics
                    and r.get("value_avg") is not None
                    and not _re.search(r"per\s+(capita|person|household|subterritory|territory|room|guest|night|day|job)",
                                       (r.get("metric_raw") or "").lower())
                    and not _re.search(r"\b(revpar|adr|daily\s+rate|daily\s+room\s+rate)\b",
                                       (r.get("metric_raw") or "").lower())
                    and not _re.search(r"month\s*\d+", (r.get("metric_raw") or "").lower())
                ]
                from collections import Counter as _C
                by_metric = _C(r.get("metric_name") for r in chartable)
                top = by_metric.most_common(1)[0][1] if by_metric else 0
                if top >= 3:
                    flags.append(f"has_item19=true, {top} chartable records but no chart rendered")

            # Quality score
            parse_errs = _has_parse_errors(slug, conn)
            score, comps = quality_score(d, parse_errs, quality_flag)
            scores.append((name, score, comps, slug))

        except Exception as e:
            flags.append(f"ERROR: {e}")

        if flags:
            issues_by_brand[name] = flags

    print(f"=== BRAND-PAGE AUDIT — {len(brands)} brands ===\n")
    if not issues_by_brand:
        print("  All brand pages render cleanly. 0 issues.")
    else:
        print(f"  {len(issues_by_brand)} brands with issues:\n")
        for name, flags in sorted(issues_by_brand.items()):
            print(f"  {name}:")
            for f in flags:
                print(f"    - {f}")

    # Quality score dashboard
    if scores:
        scores.sort(key=lambda x: (x[1], x[0].lower()))
        print(f"\n=== QUALITY SCORE (0-20) — sorted ascending ===\n")
        # Distribution
        from collections import Counter
        dist = Counter(s[1] for s in scores)
        print("  Score distribution:")
        for sc in sorted(dist.keys(), reverse=True):
            bar = "█" * dist[sc]
            print(f"    {sc:2d}: {dist[sc]:3d}  {bar}")
        avg = sum(s[1] for s in scores) / len(scores)
        print(f"\n  Average: {avg:.1f}  · Median: {sorted(s[1] for s in scores)[len(scores)//2]}\n")

        print("  Bottom 15 (needs attention):")
        for name, score, comps, slug in scores[:15]:
            missing = [k for k, v in comps.items() if v == 0]
            print(f"    {score:2d}/20  {name[:50]:50s} missing: {','.join(missing)}")

        print(f"\n  Top 10 (gold standard):")
        for name, score, comps, slug in scores[-10:][::-1]:
            print(f"    {score:2d}/20  {name}")


if __name__ == "__main__":
    main()
