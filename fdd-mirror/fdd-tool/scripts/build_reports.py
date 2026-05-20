"""Generate customer-facing report pages under /reports/.

Each report is a curated ranking page targeting a high-intent search query
(e.g. "top earning franchises", "cheapest franchises under 100k").

The hub at /reports/ lists all reports. Each report shows the top N brands
with full links to brand pages. Indexable. Schema.org ItemList markup.

Re-run after each ingest:
    python scripts/build_reports.py
"""
from __future__ import annotations
import json, sqlite3, sys, html
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.db import DB_PATH

DOCS_DIR = ROOT.parent / "docs"
REPORTS_DIR = DOCS_DIR / "reports"


def industry_label(slug: str | None) -> str:
    if not slug:
        return "Other"
    return slug.replace("home-services-", "").replace("-", " ").title()


def fmt_dollar(v) -> str:
    if v is None:
        return "—"
    try:
        n = float(v)
    except Exception:
        return "—"
    if n >= 1_000_000:
        return f"${n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"${n/1_000:.0f}K"
    return f"${n:,.0f}"


def fmt_dollar_full(v) -> str:
    if v is None:
        return "—"
    try:
        return f"${float(v):,.0f}"
    except Exception:
        return "—"


def fetch_top_earners(conn, limit=25) -> list[dict]:
    """Top brands by Item 19 median revenue across any cohort."""
    rows = conn.execute("""
        SELECT fr.slug, fr.brand_name, fr.legal_name, fr.industry,
               MAX(i.value_median) AS max_median,
               i.cohort_raw
        FROM item19_records i
        JOIN fdds d ON d.id = i.fdd_id
        JOIN franchisors fr ON fr.id = d.franchisor_id
        WHERE i.metric_name IN ('gross_sales', 'total_revenue')
          AND i.value_median IS NOT NULL
          AND i.value_median > 100000
        GROUP BY fr.id
        ORDER BY max_median DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return [{
        "slug": r["slug"], "brand": r["brand_name"] or r["legal_name"],
        "industry": r["industry"],
        "value": int(r["max_median"]), "value_fmt": fmt_dollar_full(r["max_median"]),
        "context": (r["cohort_raw"] or "")[:50],
    } for r in rows]


def fetch_largest_by_outlets(conn, limit=25) -> list[dict]:
    """Brands with the most US outlets (latest year)."""
    rows = conn.execute("""
        SELECT fr.slug, fr.brand_name, fr.legal_name, fr.industry,
               MAX(CASE WHEN i.outlet_type='total' THEN i.outlets_end END) AS total_outlets
        FROM item20_locations i
        JOIN fdds d ON d.id = i.fdd_id
        JOIN franchisors fr ON fr.id = d.franchisor_id
        WHERE i.year = (SELECT MAX(year) FROM item20_locations WHERE fdd_id=i.fdd_id AND outlet_type='total')
          AND i.outlet_type = 'total'
        GROUP BY fr.id
        ORDER BY total_outlets DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return [{
        "slug": r["slug"], "brand": r["brand_name"] or r["legal_name"],
        "industry": r["industry"],
        "value": int(r["total_outlets"] or 0),
        "value_fmt": f"{int(r['total_outlets'] or 0):,} outlets",
    } for r in rows]


def fetch_cheapest_under(conn, ceiling: int, limit=25) -> list[dict]:
    """Brands with total_investment_low under ceiling."""
    rows = conn.execute("""
        SELECT fr.slug, fr.brand_name, fr.legal_name, fr.industry,
               fi.total_investment_low, fi.total_investment_high, fi.royalty_pct
        FROM fees_and_investment fi
        JOIN fdds d ON d.id = fi.fdd_id
        JOIN franchisors fr ON fr.id = d.franchisor_id
        WHERE fi.total_investment_low IS NOT NULL
          AND fi.total_investment_low > 1000
          AND fi.total_investment_low < ?
        GROUP BY fr.id
        ORDER BY fi.total_investment_low ASC
        LIMIT ?
    """, (ceiling, limit)).fetchall()
    return [{
        "slug": r["slug"], "brand": r["brand_name"] or r["legal_name"],
        "industry": r["industry"],
        "value": int(r["total_investment_low"] or 0),
        "value_fmt": fmt_dollar_full(r["total_investment_low"]),
        "context": f"to {fmt_dollar_full(r['total_investment_high'])}" if r["total_investment_high"] else "",
    } for r in rows]


def fetch_fastest_growing(conn, limit=25) -> list[dict]:
    """Brands with the largest absolute outlet growth (latest year vs earliest)."""
    rows = conn.execute("""
        WITH outlet_series AS (
            SELECT fr.slug, fr.brand_name, fr.legal_name, fr.industry,
                   d.id AS fdd_id,
                   MIN(i.year) AS first_year, MAX(i.year) AS last_year
            FROM item20_locations i
            JOIN fdds d ON d.id = i.fdd_id
            JOIN franchisors fr ON fr.id = d.franchisor_id
            WHERE i.outlet_type = 'total'
            GROUP BY fr.id
            HAVING MAX(i.year) > MIN(i.year)
        )
        SELECT os.slug, os.brand_name, os.legal_name, os.industry,
               (SELECT outlets_end FROM item20_locations WHERE fdd_id=os.fdd_id AND outlet_type='total' AND year=os.first_year LIMIT 1) AS start_outlets,
               (SELECT outlets_end FROM item20_locations WHERE fdd_id=os.fdd_id AND outlet_type='total' AND year=os.last_year LIMIT 1) AS end_outlets,
               os.first_year, os.last_year
        FROM outlet_series os
    """).fetchall()
    enriched = []
    for r in rows:
        start = r["start_outlets"] or 0
        end = r["end_outlets"] or 0
        if start < 10 or end < 20:  # Filter to brands with meaningful scale
            continue
        delta = end - start
        if delta <= 0:
            continue
        enriched.append({
            "slug": r["slug"], "brand": r["brand_name"] or r["legal_name"],
            "industry": r["industry"],
            "value": delta, "value_fmt": f"+{delta:,} outlets",
            "context": f"{start:,} → {end:,} ({r['first_year']}–{r['last_year']})",
        })
    enriched.sort(key=lambda x: x["value"], reverse=True)
    return enriched[:limit]


def fetch_lowest_royalty(conn, limit=25) -> list[dict]:
    """Brands with the lowest royalty rates (most franchisee-friendly)."""
    rows = conn.execute("""
        SELECT fr.slug, fr.brand_name, fr.legal_name, fr.industry,
               fi.royalty_pct
        FROM fees_and_investment fi
        JOIN fdds d ON d.id = fi.fdd_id
        JOIN franchisors fr ON fr.id = d.franchisor_id
        WHERE fi.royalty_pct IS NOT NULL AND fi.royalty_pct > 0 AND fi.royalty_pct < 25
        GROUP BY fr.id
        ORDER BY fi.royalty_pct ASC
        LIMIT ?
    """, (limit,)).fetchall()
    return [{
        "slug": r["slug"], "brand": r["brand_name"] or r["legal_name"],
        "industry": r["industry"],
        "value": float(r["royalty_pct"]),
        "value_fmt": f"{r['royalty_pct']:.1f}% royalty",
    } for r in rows]


def fetch_most_transparent(conn, limit=25) -> list[dict]:
    """Brands with the most Item 19 records (best disclosure breadth)."""
    rows = conn.execute("""
        SELECT fr.slug, fr.brand_name, fr.legal_name, fr.industry,
               COUNT(i.id) AS n_records,
               COUNT(DISTINCT i.cohort_raw) AS n_cohorts
        FROM item19_records i
        JOIN fdds d ON d.id = i.fdd_id
        JOIN franchisors fr ON fr.id = d.franchisor_id
        GROUP BY fr.id
        ORDER BY n_records DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return [{
        "slug": r["slug"], "brand": r["brand_name"] or r["legal_name"],
        "industry": r["industry"],
        "value": r["n_records"],
        "value_fmt": f"{r['n_records']} records",
        "context": f"{r['n_cohorts']} distinct cohorts",
    } for r in rows]


def fetch_newest_filings(conn, limit=25) -> list[dict]:
    """Most-recently-filed FDDs in our corpus."""
    rows = conn.execute("""
        SELECT fr.slug, fr.brand_name, fr.legal_name, fr.industry,
               d.filing_year, d.filing_state, d.effective_date
        FROM fdds d
        JOIN franchisors fr ON fr.id = d.franchisor_id
        WHERE d.filing_year IS NOT NULL AND d.filing_year > 2024
        ORDER BY d.effective_date DESC NULLS LAST, d.id DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return [{
        "slug": r["slug"], "brand": r["brand_name"] or r["legal_name"],
        "industry": r["industry"],
        "value": r["filing_year"],
        "value_fmt": f"{r['filing_state']} {r['filing_year']}",
        "context": f"Effective {r['effective_date']}" if r["effective_date"] else "",
    } for r in rows]


def fetch_best_by_industry(conn, industry: str, limit=15) -> list[dict]:
    """Top brands in a category by item19 median revenue."""
    rows = conn.execute("""
        SELECT fr.slug, fr.brand_name, fr.legal_name,
               MAX(i.value_median) AS max_median,
               (SELECT MAX(outlets_end) FROM item20_locations
                WHERE fdd_id=(SELECT MAX(d2.id) FROM fdds d2 WHERE d2.franchisor_id=fr.id)
                  AND outlet_type='total') AS outlets,
               fi.total_investment_low, fi.royalty_pct
        FROM franchisors fr
        LEFT JOIN fdds d ON d.id = (SELECT MAX(d2.id) FROM fdds d2 WHERE d2.franchisor_id = fr.id)
        LEFT JOIN item19_records i ON i.fdd_id = d.id AND i.metric_name IN ('gross_sales','total_revenue')
        LEFT JOIN fees_and_investment fi ON fi.fdd_id = d.id
        WHERE fr.industry = ?
        GROUP BY fr.id
        ORDER BY max_median DESC NULLS LAST, outlets DESC
        LIMIT ?
    """, (industry, limit)).fetchall()
    out = []
    for r in rows:
        ctx_parts = []
        if r["outlets"]:
            ctx_parts.append(f"{int(r['outlets']):,} outlets")
        if r["total_investment_low"]:
            ctx_parts.append(f"from {fmt_dollar(r['total_investment_low'])}")
        if r["royalty_pct"]:
            ctx_parts.append(f"{r['royalty_pct']}% royalty")
        out.append({
            "slug": r["slug"], "brand": r["brand_name"] or r["legal_name"],
            "industry": industry,
            "value": int(r["max_median"]) if r["max_median"] else None,
            "value_fmt": fmt_dollar_full(r["max_median"]) if r["max_median"] else "—",
            "context": " · ".join(ctx_parts),
        })
    return out


REPORT_DEFINITIONS = [
    {
        "slug": "top-earning-franchises",
        "title": "Top-Earning Franchises by Median Revenue",
        "h1": "Top-Earning Franchises (Item 19 Median Revenue)",
        "meta_description": "The 25 highest-earning U.S. franchises by Item 19 median franchisee revenue, drawn from state-filed FDDs.",
        "intro": "Brands ranked by the highest reported Item 19 median franchisee revenue across any disclosed cohort. Medians beat averages for honesty — averages get pulled by a few high outliers; medians show the middle. Source: state-filed FDDs.",
        "fetch": fetch_top_earners,
        "value_label": "Median revenue",
    },
    {
        "slug": "largest-franchises-by-outlets",
        "title": "Largest U.S. Franchises by Outlet Count",
        "h1": "Largest U.S. Franchises by Outlet Count",
        "meta_description": "The 25 largest U.S. franchises ranked by total outlets in operation, from state-filed Item 20 disclosures.",
        "intro": "Total outlets currently operating in the U.S., per the most recent Item 20 disclosure. Scale is a proxy for brand maturity and system size — but not for franchisee outcomes; pair with the top-earning list to see both dimensions.",
        "fetch": fetch_largest_by_outlets,
        "value_label": "Total outlets",
    },
    {
        "slug": "cheapest-franchises-under-100k",
        "title": "Cheapest Franchises Under $100K",
        "h1": "Cheapest Franchises Under $100,000",
        "meta_description": "Franchises with total initial investment under $100K, ranked by lowest barrier to entry. Source: state-filed Item 7.",
        "intro": "Brands with a total-investment-low under $100,000, per Item 7 of the FDD. Low investment doesn't mean low risk — many cheap franchises have steep royalties or thin Item 19 disclosure. Use this as a starting filter, not a final answer.",
        "fetch": lambda c, l=25: fetch_cheapest_under(c, 100_000, l),
        "value_label": "Lowest investment",
    },
    {
        "slug": "cheapest-franchises-under-250k",
        "title": "Cheapest Franchises Under $250K",
        "h1": "Cheapest Franchises Under $250,000",
        "meta_description": "Franchises with total initial investment under $250K, ranked by lowest barrier to entry.",
        "intro": "Brands where the Item 7 estimated-initial-investment range starts below $250,000. Cheaper bracket — read alongside the royalty rate, because cheap entry + high royalty is a common pattern.",
        "fetch": lambda c, l=25: fetch_cheapest_under(c, 250_000, l),
        "value_label": "Lowest investment",
    },
    {
        "slug": "fastest-growing-franchises",
        "title": "Fastest-Growing U.S. Franchises",
        "h1": "Fastest-Growing U.S. Franchises by Outlet Growth",
        "meta_description": "Franchises with the largest absolute outlet growth across the years disclosed in their latest FDD's Item 20.",
        "intro": "Net outlet growth across the multi-year window each brand reports in Item 20 of its latest FDD. Filters to brands with at least 20 outlets at the end so a 0→3 single-territory burst doesn't beat the McDonald's of the world.",
        "fetch": fetch_fastest_growing,
        "value_label": "Outlet growth",
    },
    {
        "slug": "lowest-royalty-franchises",
        "title": "Lowest-Royalty Franchises",
        "h1": "Lowest-Royalty Franchises (Most Franchisee-Friendly Fees)",
        "meta_description": "Franchises with the lowest ongoing royalty rates, sorted ascending. Royalty is the franchisor's percentage take of franchisee revenue.",
        "intro": "Royalty is the recurring percentage of gross revenue you pay to the franchisor for as long as you own the franchise. Lower is better for franchisee cash flow. Excludes brands with 0% royalty (typically flat-fee structures shown elsewhere in Item 6).",
        "fetch": fetch_lowest_royalty,
        "value_label": "Royalty rate",
    },
    {
        "slug": "most-transparent-franchises",
        "title": "Most-Transparent Franchises by Item 19 Disclosure",
        "h1": "Most-Transparent Franchises (Item 19 Disclosure Breadth)",
        "meta_description": "Franchises that disclose the most detailed Item 19 financial-performance data — quartiles, cohorts, year-over-year.",
        "intro": "Brands ranked by total Item 19 records disclosed in their latest FDD. More records = more cohorts and finer breakdowns to evaluate. Compare against brands with limited Item 19 — both tell you something.",
        "fetch": fetch_most_transparent,
        "value_label": "Item 19 records",
    },
    {
        "slug": "newest-franchises",
        "title": "Newest Franchise Filings",
        "h1": "Newest Franchise Filings (Recently Registered FDDs)",
        "meta_description": "Most-recently-filed Franchise Disclosure Documents in our corpus. New brands actively accepting franchisees.",
        "intro": "Brands whose most recent FDD was filed in 2025 or 2026, sorted by effective date descending. Most have active registration in MN or WI and are accepting franchisee applications.",
        "fetch": fetch_newest_filings,
        "value_label": "Filing",
    },
]


def render_report(rep_def: dict, rows: list[dict], total_brands: int) -> str:
    title_full = f"{rep_def['title']} | FranchiseDepth"
    items_html = []
    for i, r in enumerate(rows, 1):
        ind_pill = f'<span class="ind-pill">{html.escape(industry_label(r.get("industry") or ""))}</span>' if r.get("industry") else ""
        ctx = f'<span class="ctx"> · {html.escape(r["context"])}</span>' if r.get("context") else ""
        items_html.append(
            f'<li><span class="rank">{i}.</span> '
            f'<a class="brand" href="/franchise/{html.escape(r["slug"])}/">{html.escape(r["brand"])}</a> '
            f'{ind_pill}'
            f'<span class="val">{html.escape(r["value_fmt"])}</span>'
            f'{ctx}'
            f'</li>'
        )

    # JSON-LD ItemList markup for SEO
    item_list_jsonld = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": rep_def["title"],
        "description": rep_def["meta_description"],
        "numberOfItems": len(rows),
        "itemListElement": [{
            "@type": "ListItem",
            "position": i + 1,
            "url": f"https://franchisedepth.com/franchise/{r['slug']}/",
            "name": r["brand"],
        } for i, r in enumerate(rows)],
    }

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title_full)}</title>
<meta name="description" content="{html.escape(rep_def['meta_description'])}">
<meta property="og:title" content="{html.escape(rep_def['title'])}">
<meta property="og:description" content="{html.escape(rep_def['meta_description'])}">
<meta property="og:type" content="article">
<meta property="og:url" content="https://franchisedepth.com/reports/{rep_def['slug']}/">
<meta property="og:image" content="https://franchisedepth.com/og-image.png">
<meta property="og:site_name" content="FranchiseDepth">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="https://franchisedepth.com/reports/{rep_def['slug']}/">
<link rel="stylesheet" href="/style.css">
<script type="application/ld+json">{json.dumps(item_list_jsonld)}</script>
</head>
<body>
<nav class="site-nav">
  <div class="nav-inner">
    <a href="/" class="nav-brand">FranchiseDepth</a>
    <a href="/reports/">Reports</a>
    <a href="/compare/">Compare</a>
    <a href="/industries/">Industries</a>
    <a href="/guides/">Guides</a>
    <a href="/about/">About</a>
  </div>
</nav>
<main class="report-page">
<header class="report-header">
  <p class="report-breadcrumb"><a href="/reports/">← All reports</a></p>
  <h1>{html.escape(rep_def['h1'])}</h1>
  <p class="report-intro">{html.escape(rep_def['intro'])}</p>
  <p class="report-meta">Source: state-filed FDDs · {total_brands} brands in corpus · Updated {datetime.now().strftime('%B %Y')}</p>
</header>

<ol class="report-list">
{''.join(items_html)}
</ol>

<section class="report-cta">
  <h2>Researching a specific franchise?</h2>
  <p>Each brand above links to its full profile: Item 5 fees, Item 7 investment range, Item 19 revenue cohorts, Item 20 outlet history, plus a built-in cost calculator. <a href="/">Browse all 461 brands →</a></p>
</section>

<section class="report-related">
  <h2>More rankings</h2>
  <ul class="related-reports">
    <li><a href="/reports/top-earning-franchises/">Top-Earning Franchises</a></li>
    <li><a href="/reports/largest-franchises-by-outlets/">Largest by Outlet Count</a></li>
    <li><a href="/reports/cheapest-franchises-under-100k/">Cheapest Under $100K</a></li>
    <li><a href="/reports/cheapest-franchises-under-250k/">Cheapest Under $250K</a></li>
    <li><a href="/reports/fastest-growing-franchises/">Fastest-Growing</a></li>
    <li><a href="/reports/lowest-royalty-franchises/">Lowest Royalty Rates</a></li>
    <li><a href="/reports/most-transparent-franchises/">Most Transparent (Item 19)</a></li>
    <li><a href="/reports/newest-franchises/">Newest Filings</a></li>
  </ul>
</section>

<footer class="report-footer">
  <p>Data extracted from publicly-filed Franchise Disclosure Documents. Not investment advice. Always read the source FDD before signing — links on each brand page.</p>
</footer>
</main>
</body>
</html>"""


def render_hub(report_summaries: list[dict], total_brands: int) -> str:
    cards = []
    for rs in report_summaries:
        cards.append(f"""
<a href="/reports/{rs['slug']}/" class="report-card">
  <h3>{html.escape(rs['title'])}</h3>
  <p>{html.escape(rs['intro_short'])}</p>
  <span class="report-card-cta">View ranking →</span>
</a>""")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Franchise Reports & Rankings | FranchiseDepth</title>
<meta name="description" content="Curated rankings of U.S. franchises by revenue, outlet count, investment, growth, royalty, and disclosure quality. Source: state-filed FDDs.">
<meta property="og:title" content="Franchise Reports & Rankings | FranchiseDepth">
<meta property="og:description" content="Top-earning, largest, cheapest, fastest-growing, and most transparent franchises — ranked from state-filed FDDs.">
<meta property="og:type" content="website">
<meta property="og:url" content="https://franchisedepth.com/reports/">
<meta property="og:image" content="https://franchisedepth.com/og-image.png">
<link rel="canonical" href="https://franchisedepth.com/reports/">
<link rel="stylesheet" href="/style.css">
</head>
<body>
<nav class="site-nav">
  <div class="nav-inner">
    <a href="/" class="nav-brand">FranchiseDepth</a>
    <a href="/reports/" class="active">Reports</a>
    <a href="/compare/">Compare</a>
    <a href="/industries/">Industries</a>
    <a href="/guides/">Guides</a>
    <a href="/about/">About</a>
  </div>
</nav>
<main class="report-hub">
<header class="report-hub-header">
  <h1>Franchise Reports & Rankings</h1>
  <p class="lede">Eight curated rankings of U.S. franchises, drawn from {total_brands} brands' state-filed Franchise Disclosure Documents. Updated {datetime.now().strftime('%B %Y')}.</p>
</header>

<section class="report-grid">
{''.join(cards)}
</section>

<section class="report-hub-explainer">
  <h2>Why we publish these rankings</h2>
  <p>Every number on these pages comes from a Franchise Disclosure Document — the legally-required filing every franchisor makes with state regulators. We extract Item 5 (initial fees), Item 6 (royalty + ongoing fees), Item 7 (total investment range), Item 19 (financial performance representations), and Item 20 (outlet counts), then rank brands by metric.</p>
  <p>Use the rankings as a screening tool. Then drill into individual brand pages — they have the full FDD breakdown, a cost calculator, and head-to-head comparisons.</p>
</section>
</main>
</body>
</html>"""


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    total_brands = conn.execute("SELECT COUNT(*) FROM franchisors").fetchone()[0]

    report_summaries = []
    for rep_def in REPORT_DEFINITIONS:
        rows = rep_def["fetch"](conn)
        intro_short = rep_def["intro"][:140] + ("…" if len(rep_def["intro"]) > 140 else "")
        report_summaries.append({
            "slug": rep_def["slug"], "title": rep_def["title"],
            "intro_short": intro_short, "n_items": len(rows),
        })
        out = REPORTS_DIR / rep_def["slug"] / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_report(rep_def, rows, total_brands), encoding="utf-8")
        print(f"  wrote /reports/{rep_def['slug']}/  ({len(rows)} items)")

    # Hub
    hub_path = REPORTS_DIR / "index.html"
    hub_path.write_text(render_hub(report_summaries, total_brands), encoding="utf-8")
    print(f"  wrote /reports/  (hub with {len(report_summaries)} report cards)")
    print(f"\nDone. {len(REPORT_DEFINITIONS) + 1} report pages written.")


if __name__ == "__main__":
    main()
