"""Generate the internal owner dashboard at docs/dashboard/index.html.

v3 (2026-05-19): decision-support layout, not a table viewer.

Changes from v2 per UX feedback:
  - Hero with title + 4 quick-start preset filter chips (Best ROI <$200k,
    Top food brands, Lowest royalty, Fastest growing)
  - Left sidebar (sticky) holds all filters; main content has charts + table
  - ONE master sortable table replaces the 4 separate top-N tables;
    columns include outlets, investment range, royalty, marketing, median
    revenue, item19 status, filing year
  - 3 charts via Chart.js CDN:
      * Industry breakdown (doughnut)
      * Investment-tier distribution (bar)
      * Royalty-rate distribution (bar)
  - URL param persistence — filters serialize to ?industry=X&maxInvLow=Y
    so links can be shared
  - CSV export of the currently-filtered view (button top-right)
  - Empty state + tooltips on metrics
  - Color coding on royalty cells (green ≤6%, yellow 7-9%, red ≥10%)
  - Color coding on investment_low (green ≤100k, etc.)
  - Default state: ALL 461 brands (no preselected industry)

Still noindex/nofollow (internal-only).
"""
from __future__ import annotations
import json, sqlite3, sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.db import DB_PATH

DOCS_DIR = ROOT.parent / "docs"
OUT_DIR = DOCS_DIR / "dashboard"


def industry_label(slug: str | None) -> str:
    if not slug:
        return "Other"
    return slug.replace("home-services-", "").replace("-", " ").title()


def fetch_brands(conn) -> list[dict]:
    rows = conn.execute("""
        SELECT
            fr.slug, fr.brand_name, fr.legal_name, fr.industry,
            d.filing_year, d.filing_state, d.id AS fdd_id,
            (SELECT COUNT(*) FROM item19_records WHERE fdd_id = d.id) AS n_item19,
            (SELECT MAX(value_median) FROM item19_records
              WHERE fdd_id = d.id AND metric_name IN ('gross_sales','total_revenue')
            ) AS top_revenue,
            (SELECT MAX(outlets_end) FROM item20_locations
              WHERE fdd_id = d.id AND outlet_type='total') AS total_outlets,
            fi.total_investment_low, fi.total_investment_high,
            fi.royalty_pct, fi.marketing_fee_pct, fi.initial_franchise_fee_low
        FROM franchisors fr
        JOIN fdds d ON d.id = (SELECT MAX(d2.id) FROM fdds d2 WHERE d2.franchisor_id = fr.id)
        LEFT JOIN fees_and_investment fi ON fi.fdd_id = d.id
    """).fetchall()

    # Outlet growth, state count, time series, worst floor — per-brand queries.
    # Also Item 19 quality classification for scatter-dot color coding.
    growth_cache = {}
    state_count_cache = {}
    outlet_history_cache = {}
    worst_floor_cache = {}
    quality_kind_cache = {}  # 'broad' | 'thin' | 'none'
    for r in rows:
        fdd_id = r["fdd_id"]
        # Time series for total-type, state='TOTAL' rows
        ts = conn.execute("""
            SELECT year, outlets_end FROM item20_locations
            WHERE fdd_id = ? AND outlet_type='total' AND state='TOTAL'
              AND outlets_end IS NOT NULL
            ORDER BY year
        """, (fdd_id,)).fetchall()
        if len(ts) >= 2 and ts[0]["outlets_end"] and ts[0]["outlets_end"] >= 5:
            first, last = ts[0]["outlets_end"], ts[-1]["outlets_end"]
            growth_cache[fdd_id] = {
                "growth_pct": round(100.0 * (last - first) / first, 1),
                "growth_abs": last - first,
                "first_year": ts[0]["year"],
                "last_year": ts[-1]["year"],
            }
        if ts:
            outlet_history_cache[fdd_id] = [[t["year"], t["outlets_end"]] for t in ts]
        # State count latest year
        sc = conn.execute("""
            SELECT COUNT(DISTINCT state) FROM item20_locations
            WHERE fdd_id = ? AND state IS NOT NULL AND state != 'TOTAL'
              AND outlets_end > 0
              AND year = (SELECT MAX(year) FROM item20_locations WHERE fdd_id = ?)
        """, (fdd_id, fdd_id)).fetchone()[0]
        if sc:
            state_count_cache[fdd_id] = sc
        # Worst-performer floor: the most negative value_min on a profit metric
        wp = conn.execute("""
            SELECT MIN(value_min) AS floor
            FROM item19_records
            WHERE fdd_id = ?
              AND metric_name IN ('net_profit','gross_profit','ebitda','operating_profit')
              AND value_min < 0
        """, (fdd_id,)).fetchone()
        if wp and wp["floor"] is not None:
            worst_floor_cache[fdd_id] = int(wp["floor"])

        # Item 19 quality kind: 'broad' if >=3 distinct franchised cohorts,
        # 'thin' if some item19 but limited, 'none' if no item19.
        i19 = conn.execute("""
            SELECT
                COUNT(DISTINCT cohort_raw) AS n_cohorts,
                SUM(CASE WHEN cohort_name LIKE '%affiliate%' OR cohort_name LIKE '%company%' THEN 1 ELSE 0 END) AS n_affiliate
            FROM item19_records WHERE fdd_id = ?
              AND metric_name IN ('gross_sales','total_revenue')
        """, (fdd_id,)).fetchone()
        if i19 and i19["n_cohorts"]:
            if i19["n_cohorts"] >= 3:
                quality_kind_cache[fdd_id] = "broad"
            else:
                quality_kind_cache[fdd_id] = "thin"

    return [{
        "slug": r["slug"],
        "name": r["brand_name"] or r["legal_name"],
        "industry": r["industry"] or "",
        "industry_label": industry_label(r["industry"]),
        "filing_year": r["filing_year"],
        "filing_state": r["filing_state"] or "",
        "n_item19": r["n_item19"] or 0,
        "top_revenue": int(r["top_revenue"]) if r["top_revenue"] else None,
        "total_outlets": int(r["total_outlets"]) if r["total_outlets"] else None,
        "investment_low": r["total_investment_low"],
        "investment_high": r["total_investment_high"],
        "royalty": r["royalty_pct"],
        "marketing": r["marketing_fee_pct"],
        "initial_fee_low": r["initial_franchise_fee_low"],
        "growth_pct": growth_cache.get(r["fdd_id"], {}).get("growth_pct"),
        "growth_abs": growth_cache.get(r["fdd_id"], {}).get("growth_abs"),
        "growth_span": (f"{growth_cache[r['fdd_id']]['first_year']}-{growth_cache[r['fdd_id']]['last_year']}"
                       if r["fdd_id"] in growth_cache else None),
        "state_count": state_count_cache.get(r["fdd_id"]),
        "outlet_history": outlet_history_cache.get(r["fdd_id"]),
        "worst_floor": worst_floor_cache.get(r["fdd_id"]),
        "i19_quality": quality_kind_cache.get(r["fdd_id"], "none"),
        # closure_rate not available — outlets_closed is 0% populated in our
        # extraction. Column shows "—". Will populate after re-extract.
        "closure_rate": None,
    } for r in rows]


def render_html(brands: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    data_json = json.dumps(brands, default=str)
    industries = sorted({b["industry_label"] for b in brands if b["industry_label"]})
    industry_opts = "\n".join(f'<option value="{i}">{i}</option>' for i in industries)
    states = sorted({b["filing_state"] for b in brands if b["filing_state"]})
    state_opts = "\n".join(f'<option value="{s}">{s}</option>' for s in states)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FranchiseDepth Dashboard — Internal Decision Support</title>
<meta name="robots" content="noindex,nofollow">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Source+Serif+4:wght@500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js" defer></script>
<style>
:root {{
    --font-body:    'Inter', system-ui, -apple-system, sans-serif;
    --font-display: 'Source Serif 4', Georgia, serif;
    --font-mono:    'IBM Plex Mono', 'JetBrains Mono', 'SF Mono', monospace;
    --bg-base:     #0A0E14;
    --bg-elevated: #131923;
    --bg-overlay:  #1C2332;
    --bg-canvas:   var(--bg-canvas);
    --border-subtle:   rgba(255, 255, 255, 0.06);
    --border-default:  rgba(255, 255, 255, 0.10);
    --border-emphasis: rgba(255, 255, 255, 0.16);
    --text-primary:   #F2F3F5;
    --text-secondary: #9CA3AF;
    --text-tertiary:  #6B7280;
    --text-muted:     #4B5563;
    --accent-primary: var(--accent-primary);
    --accent-warning: #F59E0B;
    --accent-danger:  #EF4444;
    --accent-info:    #60A5FA;
    --accent-gold:    #D4AF37;
    --ease: cubic-bezier(0.4, 0, 0.2, 1);
    --dur-fast: 150ms; --dur: 200ms;
}}
* {{ box-sizing: border-box; }}
body {{
    margin: 0; padding: 0;
    font-family: var(--font-body);
    background: var(--bg-base); color: var(--text-primary); line-height: 1.55;
    min-height: 100vh;
    font-feature-settings: "ss01", "cv11";
    -webkit-font-smoothing: antialiased;
}}
a {{ color: var(--accent-info); transition: color var(--dur-fast) var(--ease); }}
a:hover {{ color: var(--text-primary); }}

/* ===== Hero ===== */
.hero {{
    background: linear-gradient(135deg, var(--bg-elevated) 0%, var(--bg-base) 100%);
    border-bottom: 1px solid var(--border-subtle);
    padding: 40px 24px 28px;
}}
.hero-inner {{ max-width: 1500px; margin: 0 auto; }}
.hero .eyebrow {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-tertiary);
    margin: 0 0 16px;
}}
.hero h1 {{
    margin: 0 0 12px;
    font-family: var(--font-display);
    font-size: clamp(32px, 4.2vw, 48px);
    font-weight: 600;
    line-height: 1.05;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, var(--text-primary) 0%, var(--text-secondary) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}
.hero .lede {{ margin: 0 0 22px; color: var(--text-secondary); font-size: 16px; max-width: 720px; }}
.hero .lede strong {{
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
    color: var(--text-primary);
    font-weight: 500;
}}
.hero .dot {{ color: var(--text-muted); margin: 0 8px; }}
.preset-chips {{ display: flex; flex-wrap: wrap; gap: 8px; }}
.chip {{
    background: rgba(96, 165, 250, 0.12); color: var(--accent-info);
    border: 1px solid var(--accent-info); border-radius: 999px;
    padding: 6px 14px; cursor: pointer; font-size: 13px; font-weight: 600;
    transition: all .15s;
}}
.chip:hover {{ background: var(--accent-info); color: var(--bg-base); }}
.chip.active {{ background: var(--accent-info); color: var(--bg-base); }}

/* ===== Layout: sidebar + main ===== */
.layout {{ display: grid; grid-template-columns: 240px 1fr; max-width: 1500px; margin: 0 auto; }}
.sidebar {{
    background: var(--bg-base); border-right: 1px solid var(--border-default);
    padding: 18px 14px;
    position: sticky; top: 0; align-self: start;
    height: calc(100vh); overflow-y: auto;
}}
.sidebar h3 {{
    margin: 0 0 8px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em;
    color: var(--text-secondary); font-weight: 600;
}}
.main {{ padding: 18px 24px; }}

@media (max-width: 900px) {{
  .layout {{ grid-template-columns: 1fr; }}
  .sidebar {{ position: static; height: auto; border-right: none; border-bottom: 1px solid var(--border-default); }}
}}

/* ===== Filters ===== */
.filter-group {{ margin-bottom: 16px; }}
.filter-group label {{
    display: block; font-size: 11px; color: var(--text-secondary);
    text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; font-weight: 600;
}}
.sidebar input, .sidebar select {{
    width: 100%; padding: 6px 9px;
    background: var(--bg-elevated); border: 1px solid var(--border-default); border-radius: 4px;
    color: var(--text-primary); font-size: 13px; font-family: inherit;
}}
.filter-range {{ display: flex; gap: 4px; align-items: center; }}
.filter-range input {{ min-width: 0; }}
.filter-range .dash {{ color: var(--text-tertiary); font-size: 11px; }}
.btn {{
    background: var(--border-default); color: var(--text-primary); border: none; border-radius: 4px;
    padding: 6px 12px; cursor: pointer; font-size: 12px; font-weight: 600;
    font-family: inherit;
}}
.btn:hover {{ background: var(--border-emphasis); }}
.btn-primary {{ background: var(--accent-info); color: white; }}
.btn-primary:hover {{ background: var(--accent-info); }}

/* ===== KPI strip ===== */
.kpi-strip {{
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px;
}}
.kpi-tile {{
    background: var(--bg-elevated); border: 1px solid var(--border-subtle); border-radius: 12px; padding: 20px 22px;
    transition: border-color var(--dur) var(--ease), transform var(--dur) var(--ease);
}}
.kpi-tile:hover {{ border-color: var(--border-emphasis); transform: translateY(-1px); }}
.kpi-tile h4 {{
    margin: 0 0 8px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em;
    color: var(--text-tertiary); font-weight: 600;
}}
.kpi-tile .kpi-val {{
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
    font-size: 36px; font-weight: 500;
    color: var(--text-primary);
    line-height: 1.05;
    letter-spacing: -0.02em;
}}
.kpi-tile .kpi-sub {{
    color: var(--text-secondary);
    font-size: 12px; margin-top: 6px;
    font-variant-numeric: tabular-nums;
}}

/* ===== Charts row ===== */
.charts-row {{
    display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-bottom: 20px;
}}
.chart-card {{
    background: var(--bg-elevated); border: 1px solid var(--border-default); border-radius: 8px; padding: 14px;
}}
.chart-card h3 {{
    margin: 0 0 8px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em;
    color: var(--text-secondary); font-weight: 600;
}}
.chart-wrap {{ height: 220px; position: relative; }}
@media (max-width: 1100px) {{ .charts-row {{ grid-template-columns: 1fr; }} }}

/* ===== Master table ===== */
.results {{
    background: var(--bg-elevated); border: 1px solid var(--border-default); border-radius: 8px; padding: 14px 16px;
}}
.results-header {{
    display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;
}}
.results-header h3 {{
    margin: 0; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em;
    color: var(--text-secondary); font-weight: 600;
}}
.results-status {{ color: var(--accent-info); font-size: 13px; font-variant-numeric: tabular-nums; }}
.master-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
.master-table th {{
    text-align: left; color: var(--text-secondary); font-weight: 600;
    padding: 8px 10px 8px 0; border-bottom: 1px solid var(--border-default);
    font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em;
    cursor: pointer; user-select: none; white-space: nowrap;
    position: sticky; top: 0; background: var(--bg-elevated); z-index: 1;
}}
.master-table th.sortable::after {{ content: " ↕"; opacity: 0.4; font-size: 10px; }}
.master-table th.sort-asc::after  {{ content: " ↑"; opacity: 1; color: var(--accent-info); }}
.master-table th.sort-desc::after {{ content: " ↓"; opacity: 1; color: var(--accent-info); }}
.master-table td {{
    padding: 7px 10px 7px 0; border-bottom: 1px solid var(--bg-elevated); color: var(--text-primary);
}}
.master-table td.num {{ text-align: right; font-variant-numeric: tabular-nums; font-family: var(--font-mono); }}
.master-table td {{ font-family: var(--font-body); }}
.master-table tr:hover td {{ background: var(--bg-base); }}
.master-table a {{ color: var(--text-primary); text-decoration: none; font-weight: 500; }}
.master-table a:hover {{ color: var(--accent-info); text-decoration: underline; }}
.master-table .ind {{
    display: inline-block; background: rgba(96, 165, 250, 0.12); color: var(--accent-info);
    padding: 1px 6px; border-radius: 3px; font-size: 10px; white-space: nowrap;
}}
.empty {{
    padding: 40px 20px; text-align: center; color: var(--text-tertiary); font-size: 14px;
}}
.empty .ttl {{ color: var(--text-secondary); font-size: 16px; margin-bottom: 6px; }}

/* Color-coded cells */
.val-good {{ color: var(--accent-primary); font-weight: 600; }}
.val-warn {{ color: var(--accent-warning); font-weight: 600; }}
.val-bad  {{ color: var(--accent-danger); font-weight: 600; }}
.val-muted {{ color: var(--text-tertiary); }}

/* Tooltip */
[data-tip] {{ position: relative; }}
[data-tip]:hover::after {{
    content: attr(data-tip);
    position: absolute; bottom: 100%; left: 0; transform: translateY(-4px);
    background: var(--bg-base); border: 1px solid var(--border-emphasis); color: var(--text-primary);
    padding: 5px 9px; font-size: 11px; font-weight: 400;
    border-radius: 4px; white-space: normal; width: 240px;
    line-height: 1.4; text-transform: none; letter-spacing: 0; z-index: 10;
    pointer-events: none;
}}

/* CSV button positioning */
.actions {{ display: flex; gap: 8px; }}
.meta {{ color: var(--text-tertiary); font-size: 11px; margin-top: 12px; }}

/* Multi-select compare */
.compare-fab {{
    position: fixed; bottom: 24px; right: 24px; z-index: 50;
    background: var(--accent-info); color: white; border: none; border-radius: 999px;
    padding: 14px 24px; font-size: 14px; font-weight: 700; font-family: inherit;
    cursor: pointer; box-shadow: 0 4px 16px rgba(29,78,216,0.4);
    transition: all .15s;
}}
.compare-fab:hover {{ background: var(--accent-info); transform: translateY(-2px); box-shadow: 0 6px 20px rgba(29,78,216,0.5); }}
.master-table input[type="checkbox"] {{ cursor: pointer; }}

/* Modal */
.modal {{
    position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 100;
    display: flex; align-items: flex-start; justify-content: center; overflow-y: auto;
    padding: 40px 20px;
}}
.modal-inner {{
    background: var(--bg-base); border: 1px solid var(--border-default); border-radius: 12px;
    max-width: 1400px; width: 100%; padding: 0;
}}
.modal-header {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 16px 24px; border-bottom: 1px solid var(--border-default);
}}
.modal-header h2 {{ margin: 0; font-size: 20px; color: var(--text-primary); }}
.modal-body {{ padding: 20px 24px 24px; overflow-x: auto; }}
.compare-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
.compare-table th, .compare-table td {{
    padding: 10px 12px; border-bottom: 1px solid var(--bg-elevated);
    text-align: left; vertical-align: top;
}}
.compare-table th {{
    background: var(--bg-elevated); color: var(--text-secondary);
    font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em;
}}
.compare-table .row-label {{
    background: var(--bg-base); color: var(--text-secondary); font-size: 11px;
    text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600;
    width: 150px;
}}
.compare-table td:not(.row-label) {{ font-variant-numeric: tabular-nums; }}
.compare-table .brand-cell {{
    color: var(--accent-info); font-weight: 700; font-size: 14px; text-transform: none; letter-spacing: 0;
}}
.compare-table .brand-cell a {{ color: var(--accent-info); text-decoration: none; }}
.compare-table .brand-cell a:hover {{ text-decoration: underline; }}

/* Growth badge in main table */
.growth-up   {{ color: var(--accent-primary); font-weight: 600; }}
.growth-down {{ color: var(--accent-danger); font-weight: 600; }}
.growth-flat {{ color: var(--text-secondary); }}

/* Watchlist star */
.star {{
    cursor: pointer; color: var(--border-emphasis); font-size: 16px; user-select: none;
    background: none; border: none; padding: 0; font-family: inherit;
}}
.star:hover {{ color: var(--accent-warning); }}
.star.active {{ color: var(--accent-warning); }}

/* Sparkline */
.sparkline {{ width: 100%; height: 50px; display: block; }}
.worst-floor {{ background: #44141414; color: var(--accent-danger); font-weight: 600; }}

/* KPI strip: 2 tiles wide */
.kpi-2 {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 20px; }}

/* Columns toggle dropdown */
.cols-menu-wrap {{ position: relative; display: inline-block; }}
.cols-menu {{
    position: absolute; top: calc(100% + 4px); right: 0; z-index: 20;
    background: var(--bg-base); border: 1px solid var(--border-default); border-radius: 6px;
    padding: 10px 12px; min-width: 220px; max-height: 360px; overflow-y: auto;
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}}
.cols-menu label {{
    display: flex; align-items: center; gap: 8px; padding: 4px 0;
    font-size: 13px; color: var(--text-primary); cursor: pointer; white-space: nowrap;
}}
.cols-menu label:hover {{ color: var(--accent-info); }}
.cols-menu input[type="checkbox"] {{ accent-color: var(--accent-info); }}
.cols-menu .sep {{ height: 1px; background: var(--border-default); margin: 6px 0; }}

/* Bottom-fixed multi-select action bar */
.action-bar {{
    position: fixed; left: 0; right: 0; bottom: 0; z-index: 60;
    background: var(--bg-elevated); border-top: 1px solid var(--accent-info);
    padding: 14px 24px; display: none;
    box-shadow: 0 -4px 16px rgba(0,0,0,0.4);
}}
.action-bar.active {{ display: flex; align-items: center; gap: 16px; justify-content: space-between; }}
.action-bar .selected-count {{
    color: var(--accent-info); font-weight: 700; font-size: 14px;
}}
.action-bar .actions-row {{ display: flex; gap: 8px; }}

/* Filter info icons */
.info-icon {{
    display: inline-block; width: 14px; height: 14px;
    background: var(--border-default); color: var(--text-secondary); border-radius: 50%;
    text-align: center; line-height: 14px; font-size: 10px; font-weight: 700;
    margin-left: 4px; cursor: help;
}}
.check-label {{ display: flex !important; align-items: center; gap: 8px;
                text-transform: none !important; font-size: 13px !important;
                color: var(--text-primary) !important; letter-spacing: 0 !important; cursor: pointer; }}
.check-label input {{ width: auto !important; }}

/* Item 19 status pill */
.i19-broad {{ color: var(--accent-primary); font-weight: 700; }}
.i19-thin  {{ color: var(--accent-warning); font-weight: 700; }}
.i19-none  {{ color: var(--text-tertiary); }}

/* Footer */
.dash-footer {{
    padding: 14px 24px; color: var(--text-tertiary); font-size: 12px;
    border-top: 1px solid var(--bg-elevated); text-align: center;
}}
</style>
</head>
<body>

<div class="hero">
  <div class="hero-inner">
    <p class="eyebrow">FranchiseDepth Analytics</p>
    <h1>Find the right franchise.</h1>
    <p class="lede">Real FDD data across <strong id="hero-count">{len(brands)}</strong> brands<span class="dot">·</span>100% with Item 19, Item 20, and fee data.</p>
    <div class="preset-chips">
      <button class="chip" data-preset="best-roi"        data-tip="100+ outlets, investment low under $200K, royalty under 7%">Best ROI under $200K</button>
      <button class="chip" data-preset="top-food"        data-tip="Industry = food-quick-service, sorted by median revenue">Top food brands</button>
      <button class="chip" data-preset="low-royalty"     data-tip="Royalty 5% or lower">Lowest royalty</button>
      <button class="chip" data-preset="largest-i19"     data-tip="500+ outlets and Item 19 disclosed">Largest with Item 19</button>
      <button class="chip" data-preset="affordable"      data-tip="Investment low under $50K">Under $50K to start</button>
      <button class="chip" data-preset="fastest-growing" data-tip="Outlet growth +20% or more over the disclosed Item 20 window">Fastest growing</button>
    </div>
  </div>
</div>

<div class="layout">

<aside class="sidebar">
  <h3>Filters</h3>
  <div class="filter-group">
    <label>Search</label>
    <input type="text" id="f-search" placeholder="brand name…">
  </div>
  <div class="filter-group">
    <label>Industry</label>
    <select id="f-industry">
      <option value="">All ({len(industries)})</option>
      {industry_opts}
    </select>
  </div>
  <div class="filter-group">
    <label>Investment range (low)</label>
    <div class="filter-range">
      <input type="number" id="f-inv-min" placeholder="min $">
      <span class="dash">–</span>
      <input type="number" id="f-inv-max" placeholder="max $">
    </div>
  </div>
  <div class="filter-group">
    <label>Royalty %</label>
    <div class="filter-range">
      <input type="number" id="f-roy-min" placeholder="min" step="0.5">
      <span class="dash">–</span>
      <input type="number" id="f-roy-max" placeholder="max" step="0.5">
    </div>
  </div>
  <div class="filter-group">
    <label>Min outlets</label>
    <input type="number" id="f-outlets-min" placeholder="0">
  </div>
  <div class="filter-group">
    <label>Filing state</label>
    <select id="f-state">
      <option value="">Any</option>
      {state_opts}
    </select>
  </div>
  <div class="filter-group">
    <label>Has Item 19?</label>
    <select id="f-item19">
      <option value="">Either</option>
      <option value="yes">Yes (disclosed)</option>
      <option value="no">No</option>
    </select>
  </div>
  <div class="filter-group">
    <label class="check-label"><input type="checkbox" id="f-watchlist"> Show only my watchlist</label>
  </div>
  <div class="actions">
    <button class="btn" id="f-reset">Reset</button>
    <button class="btn btn-primary" id="f-copy">Copy URL</button>
  </div>
</aside>

<main class="main">

<div class="kpi-strip kpi-2">
  <div class="kpi-tile">
    <h4 data-tip="Brands matching the current filter set, out of all in the corpus">Brands</h4>
    <div class="kpi-val" id="kpi-brands">0</div>
    <div class="kpi-sub" id="kpi-brands-sub">of {len(brands)}</div>
  </div>
  <div class="kpi-tile">
    <h4 data-tip="Brands that disclose Item 19 financial-performance data in their FDD">Item 19 disclosed</h4>
    <div class="kpi-val" id="kpi-item19">0</div>
    <div class="kpi-sub" id="kpi-item19-sub">0%</div>
  </div>
</div>

<div class="charts-row">
  <div class="chart-card">
    <h3>Industry mix</h3>
    <div class="chart-wrap"><canvas id="chartIndustry"></canvas></div>
  </div>
  <div class="chart-card">
    <h3>Investment-tier distribution</h3>
    <div class="chart-wrap"><canvas id="chartInvestment"></canvas></div>
  </div>
  <div class="chart-card">
    <h3>Royalty-rate distribution</h3>
    <div class="chart-wrap"><canvas id="chartRoyalty"></canvas></div>
  </div>
</div>

<div class="chart-card" style="margin-bottom: 20px;">
  <h3>Revenue vs royalty — find the franchisee-friendly outliers (high revenue, low royalty)</h3>
  <div class="chart-wrap" style="height: 320px;"><canvas id="chartScatter"></canvas></div>
</div>

<div class="results">
  <div class="results-header">
    <h3>Brands</h3>
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
      <span class="results-status" id="results-status">Showing 0 of {len(brands)}</span>
      <div class="cols-menu-wrap">
        <button class="btn" id="cols-btn" data-tip="Toggle which columns appear in the table">Columns ▾</button>
        <div class="cols-menu" id="cols-menu" hidden></div>
      </div>
      <button class="btn btn-primary" id="csv-export" data-tip="Download the filtered set as CSV (all columns, not just visible)">Export CSV</button>
    </div>
  </div>
  <div style="overflow-x: auto; max-height: 600px;">
    <table class="master-table">
      <thead><tr id="master-head"></tr></thead>
      <tbody id="master-body"></tbody>
    </table>
  </div>
  <div class="empty" id="empty-state" style="display:none;">
    <div class="ttl">No brands match these filters.</div>
    Try widening your investment range or clearing the industry filter.
  </div>
</div>

</main>
</div>

<!-- Bottom action bar (appears when ≥1 items selected) -->
<div id="action-bar" class="action-bar">
  <div class="selected-count"><span id="compare-count">0</span> brands selected</div>
  <div class="actions-row">
    <button class="btn btn-primary" id="compare-btn">Compare side-by-side</button>
    <button class="btn" id="compare-csv-bar">Export selected as CSV</button>
    <button class="btn" id="compare-clear">Clear</button>
  </div>
</div>

<!-- Footer with build timestamp + noindex marker -->
<footer class="dash-footer">Generated {now} · noindex/nofollow · internal-only</footer>

<!-- Compare modal -->
<div id="compare-modal" class="modal" style="display:none;">
  <div class="modal-inner">
    <div class="modal-header">
      <h2>Side-by-side comparison</h2>
      <div>
        <button class="btn" id="compare-csv">Export CSV</button>
        <button class="btn" id="compare-close">Close ✕</button>
      </div>
    </div>
    <div class="modal-body" id="compare-body"></div>
  </div>
</div>

<script>
const BRANDS = {data_json};
const els = {{
  search:    document.getElementById('f-search'),
  industry:  document.getElementById('f-industry'),
  invMin:    document.getElementById('f-inv-min'),
  invMax:    document.getElementById('f-inv-max'),
  royMin:    document.getElementById('f-roy-min'),
  royMax:    document.getElementById('f-roy-max'),
  outletsMin: document.getElementById('f-outlets-min'),
  state:     document.getElementById('f-state'),
  item19:    document.getElementById('f-item19'),
  watchlist: document.getElementById('f-watchlist'),
  reset:     document.getElementById('f-reset'),
  copyUrl:   document.getElementById('f-copy'),
  csvBtn:    document.getElementById('csv-export'),
  status:    document.getElementById('results-status'),
  empty:     document.getElementById('empty-state'),
  body:      document.getElementById('master-body'),
}};

// Default sort: top median revenue desc
let sortState = {{ key: 'top_revenue', dir: 'desc' }};

// Multi-select state for compare feature — survives reload via localStorage
const SELECTED_KEY = 'fd-dashboard-selected';
let selectedSlugs = new Set(JSON.parse(localStorage.getItem(SELECTED_KEY) || '[]'));
function saveSelected() {{ localStorage.setItem(SELECTED_KEY, JSON.stringify([...selectedSlugs])); }}
function updateCompareBtn() {{
  const n = selectedSlugs.size;
  const bar = document.getElementById('action-bar');
  bar.classList.toggle('active', n > 0);
  document.getElementById('compare-count').textContent = n;
}}

// Column definitions (drives table header + body + Columns toggle menu)
const COLUMNS = [
  // key, label, sortKey, align, fmt, defaultVisible, alwaysVisible, tooltip
  {{ key: 'name',           label: 'Brand',              sort: 'name',           align: 'left',  default: true,  always: true,
     tip: 'Brand name; click to open brand page',
     render: b => `<a href="/franchise/${{escHtml(b.slug)}}/">${{escHtml(b.name)}}</a>` }},
  {{ key: 'industry_label', label: 'Industry',           sort: 'industry_label', align: 'left',  default: true,
     tip: 'Category. Click any industry-mix slice to filter here.',
     render: b => `<span class="ind">${{escHtml(b.industry_label)}}</span>` }},
  {{ key: 'total_outlets',  label: 'Outlets',            sort: 'total_outlets',  align: 'num',   default: true,
     tip: 'Total outlets in the latest year of Item 20 (franchised + company-owned)',
     render: b => fmtNum(b.total_outlets) }},
  {{ key: 'inv_range',      label: 'Investment range',   sort: 'investment_low', align: 'num',   default: true,
     tip: 'Item 7 total initial investment range (low - high)',
     render: b => {{
       if (b.investment_low == null && b.investment_high == null) return '—';
       const lo = fmtDollar(b.investment_low), hi = fmtDollar(b.investment_high);
       const cls = investmentClass(b.investment_low);
       return `<span class="${{cls}}">${{lo}} – ${{hi}}</span>`;
     }} }},
  {{ key: 'royalty',        label: 'Royalty',            sort: 'royalty',        align: 'num',   default: true,
     tip: 'Ongoing royalty % from Item 6',
     render: b => `<span class="${{royaltyClass(b.royalty)}}">${{fmtPct(b.royalty)}}</span>` }},
  {{ key: 'marketing',      label: 'Marketing fee',      sort: 'marketing',      align: 'num',   default: false,
     tip: 'Marketing/brand-fund % from Item 6',
     render: b => fmtPct(b.marketing) }},
  {{ key: 'top_revenue',    label: 'Median revenue',     sort: 'top_revenue',    align: 'num',   default: true,
     tip: 'Highest median revenue across any Item 19 cohort the brand discloses',
     render: b => fmtDollarFull(b.top_revenue) }},
  {{ key: 'i19_status',     label: 'Item 19',            sort: 'i19_quality',    align: 'left',  default: true,
     tip: 'Disclosure quality: broad (3+ cohorts), thin (1-2 cohorts or affiliate-only), or none',
     render: b => {{
       if (b.i19_quality === 'broad') return '<span class="i19-broad" title="Broad disclosure: 3+ cohorts">✓ Broad</span>';
       if (b.i19_quality === 'thin')  return '<span class="i19-thin" title="Thin disclosure: limited cohorts">△ Thin</span>';
       return '<span class="i19-none">✗ None</span>';
     }} }},
  {{ key: 'closure_rate',   label: 'Closure rate',       sort: 'closure_rate',   align: 'num',   default: false,
     tip: 'Closure rate (per-state outlets_closed / starting outlets) — data sparse in our extraction; column shows — for most brands',
     render: b => b.closure_rate == null ? '<span class="val-muted">—</span>' : fmtPct(b.closure_rate) }},
  {{ key: 'growth_pct',     label: 'Outlet growth',      sort: 'growth_pct',     align: 'num',   default: false,
     tip: 'Outlet growth % over the disclosed Item 20 multi-year window',
     render: b => b.growth_pct == null ? '—'
       : `<span class="${{b.growth_pct > 5 ? 'growth-up' : b.growth_pct < -5 ? 'growth-down' : 'growth-flat'}}">${{b.growth_pct > 0 ? '+' : ''}}${{b.growth_pct}}%</span>` }},
  {{ key: 'state_count',    label: 'US states',          sort: 'state_count',    align: 'num',   default: false,
     tip: 'Distinct US states with outlets in the latest disclosed year',
     render: b => b.state_count != null ? b.state_count : '—' }},
  {{ key: 'filing_state',   label: 'Filing state',       sort: 'filing_state',   align: 'left',  default: false,
     tip: 'State where this FDD was filed. MN and WI are our two main scraping sources.',
     render: b => b.filing_state || '—' }},
  {{ key: 'filing_year',    label: 'FDD year',           sort: 'filing_year',    align: 'num',   default: false,
     tip: 'Filing year of the FDD this data was extracted from',
     render: b => b.filing_year || '—' }},
  {{ key: 'initial_fee',    label: 'Initial franchise fee', sort: 'initial_fee_low', align: 'num', default: false,
     tip: 'Initial franchise fee from Item 5 (low end if range disclosed)',
     render: b => fmtDollar(b.initial_fee_low) }},
  {{ key: 'worst_floor',    label: 'Worst performer floor', sort: 'worst_floor', align: 'num',  default: false,
     tip: 'Lowest disclosed Item 19 profit value (negative = a franchisee lost money). When present, this is a red-flag indicator.',
     render: b => b.worst_floor == null ? '—'
       : `<span class="growth-down">−$${{Math.abs(b.worst_floor).toLocaleString()}}</span>` }},
];

const COL_KEY = 'fd-dashboard-cols';
const defaultVisible = COLUMNS.filter(c => c.default).map(c => c.key);
let visibleColKeys = new Set(JSON.parse(localStorage.getItem(COL_KEY) || JSON.stringify(defaultVisible)));
function saveColumns() {{ localStorage.setItem(COL_KEY, JSON.stringify([...visibleColKeys])); }}
function visibleColumns() {{ return COLUMNS.filter(c => c.always || visibleColKeys.has(c.key)); }}

// Watchlist (separate from compare-selection) — also localStorage-backed
const WATCH_KEY = 'fd-dashboard-watchlist';
let watchlistSlugs = new Set(JSON.parse(localStorage.getItem(WATCH_KEY) || '[]'));
function saveWatchlist() {{ localStorage.setItem(WATCH_KEY, JSON.stringify([...watchlistSlugs])); }}

// URL-encoded filter persistence
const FILTER_KEYS = {{
  search:'q', industry:'industry', invMin:'invMin', invMax:'invMax',
  royMin:'royMin', royMax:'royMax', outletsMin:'outletsMin',
  state:'state', item19:'item19',
}};

function readURL() {{
  const p = new URLSearchParams(window.location.search);
  Object.entries(FILTER_KEYS).forEach(([k, q]) => {{
    if (p.has(q)) els[k].value = p.get(q);
  }});
  if (p.get('watchlist') === '1') els.watchlist.checked = true;
  if (p.has('sortKey')) sortState.key = p.get('sortKey');
  if (p.has('sortDir')) sortState.dir = p.get('sortDir');
}}

function writeURL() {{
  const p = new URLSearchParams();
  Object.entries(FILTER_KEYS).forEach(([k, q]) => {{
    const v = els[k].value;
    if (v) p.set(q, v);
  }});
  if (els.watchlist.checked) p.set('watchlist', '1');
  p.set('sortKey', sortState.key);
  p.set('sortDir', sortState.dir);
  const newUrl = window.location.pathname + (p.toString() ? '?' + p.toString() : '');
  window.history.replaceState(null, '', newUrl);
}}

function applyFilters() {{
  const q = els.search.value.toLowerCase().trim();
  const ind = els.industry.value;
  const invMin = parseFloat(els.invMin.value) || null;
  const invMax = parseFloat(els.invMax.value) || null;
  const royMin = parseFloat(els.royMin.value) || null;
  const royMax = parseFloat(els.royMax.value) || null;
  const outletsMin = parseFloat(els.outletsMin.value) || null;
  const state = els.state.value;
  const i19 = els.item19.value;

  return BRANDS.filter(b => {{
    if (q && !(b.name || '').toLowerCase().includes(q)) return false;
    if (ind && b.industry_label !== ind) return false;
    if (invMin != null && (b.investment_low == null || b.investment_low < invMin)) return false;
    if (invMax != null && (b.investment_low == null || b.investment_low > invMax)) return false;
    if (royMin != null && (b.royalty == null || b.royalty < royMin)) return false;
    if (royMax != null && (b.royalty == null || b.royalty > royMax)) return false;
    if (outletsMin != null && (b.total_outlets == null || b.total_outlets < outletsMin)) return false;
    if (state && b.filing_state !== state) return false;
    if (i19 === 'yes' && b.n_item19 === 0) return false;
    if (i19 === 'no'  && b.n_item19 > 0)  return false;
    if (els.watchlist.checked && !watchlistSlugs.has(b.slug)) return false;
    return true;
  }});
}}

function median(arr) {{
  const c = arr.filter(x => x != null && !isNaN(x)).sort((a,b) => a-b);
  if (!c.length) return null;
  const m = Math.floor(c.length / 2);
  return c.length % 2 ? c[m] : (c[m-1] + c[m]) / 2;
}}

function fmtDollar(v) {{
  if (v == null) return '—';
  if (v >= 1e6) return '$' + (v/1e6).toFixed(1) + 'M';
  if (v >= 1e3) return '$' + Math.round(v/1e3) + 'K';
  return '$' + Math.round(v).toLocaleString();
}}
function fmtDollarFull(v) {{ return v == null ? '—' : '$' + Math.round(v).toLocaleString(); }}
function fmtNum(v) {{ return v == null ? '—' : Math.round(v).toLocaleString(); }}
function fmtPct(v) {{ return v == null ? '—' : Number(v).toFixed(1) + '%'; }}

function escHtml(s) {{
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

// Color-coding heuristics
function royaltyClass(v) {{
  if (v == null) return 'val-muted';
  if (v <= 6) return 'val-good';
  if (v <= 9) return '';
  return 'val-bad';
}}
function investmentClass(v) {{
  if (v == null) return 'val-muted';
  if (v <= 100000) return 'val-good';
  if (v <= 500000) return '';
  return 'val-warn';
}}

function renderKPIs(filtered) {{
  document.getElementById('kpi-brands').textContent = filtered.length.toLocaleString();
  document.getElementById('kpi-brands-sub').textContent = `of ${{BRANDS.length.toLocaleString()}}`;
  const withI19 = filtered.filter(b => b.n_item19 > 0).length;
  const pct = filtered.length ? Math.round(100 * withI19 / filtered.length) : 0;
  document.getElementById('kpi-item19').textContent = withI19.toLocaleString();
  document.getElementById('kpi-item19-sub').textContent = pct + '%';
}}

// ===== Charts =====
let charts = {{ industry: null, investment: null, royalty: null }};

function renderCharts(filtered) {{
  // industry doughnut
  const indCounts = {{}};
  filtered.forEach(b => {{
    const k = b.industry_label || 'Other';
    indCounts[k] = (indCounts[k] || 0) + 1;
  }});
  const indEntries = Object.entries(indCounts).sort((a, b) => b[1] - a[1]).slice(0, 12);
  if (charts.industry) charts.industry.destroy();
  if (typeof Chart === 'undefined') return; // chart.js not loaded yet
  const indTotal = indEntries.reduce((s, e) => s + e[1], 0);
  charts.industry = new Chart(document.getElementById('chartIndustry').getContext('2d'), {{
    type: 'doughnut',
    data: {{ labels: indEntries.map(e => e[0]), datasets: [{{ data: indEntries.map(e => e[1]),
              backgroundColor: ['#60A5FA','#60A5FA','#06b6d4','#0891b2','#0e7490','#155e75',
                                '#10B981','#10B981','#059669','#F59E0B','#f59e0b','#a78bfa'] }}] }},
    options: {{
      plugins: {{
        legend: {{ position: 'right',
                  labels: {{ color: '#9CA3AF', font: {{ size: 10 }}, boxWidth: 10,
                            generateLabels: chart => {{
                              const data = chart.data;
                              return data.labels.map((label, i) => ({{
                                text: `${{label}} (${{data.datasets[0].data[i]}})`,
                                fillStyle: data.datasets[0].backgroundColor[i],
                                strokeStyle: data.datasets[0].backgroundColor[i],
                                index: i,
                              }}));
                            }} }} }},
        tooltip: {{
          backgroundColor: '#0A0E14', borderColor: 'rgba(255,255,255,0.16)', borderWidth: 1,
          titleColor: '#F2F3F5', bodyColor: '#F2F3F5', padding: 10,
          callbacks: {{
            label: ctx => {{
              const pct = (100 * ctx.parsed / indTotal).toFixed(1);
              return `${{ctx.label}}: ${{ctx.parsed}} brands (${{pct}}%) — click to filter`;
            }}
          }}
        }}
      }},
      cutout: '55%', maintainAspectRatio: false,
      onClick: (e, items) => {{
        if (!items.length) return;
        const label = indEntries[items[0].index][0];
        els.industry.value = label;
        rerender();
      }},
    }}
  }});

  // investment-tier bar
  const tiers = [
    {{ label: '< $100K',   min: 0,        max: 100000 }},
    {{ label: '$100K-250K', min: 100000,   max: 250000 }},
    {{ label: '$250K-500K', min: 250000,   max: 500000 }},
    {{ label: '$500K-1M',   min: 500000,   max: 1000000 }},
    {{ label: '$1M-5M',     min: 1000000,  max: 5000000 }},
    {{ label: '$5M+',       min: 5000000,  max: 1e12 }},
  ];
  const tCounts = tiers.map(t => filtered.filter(b => b.investment_low != null && b.investment_low >= t.min && b.investment_low < t.max).length);
  if (charts.investment) charts.investment.destroy();
  charts.investment = new Chart(document.getElementById('chartInvestment').getContext('2d'), {{
    type: 'bar',
    data: {{ labels: tiers.map(t => t.label), datasets: [{{ data: tCounts, backgroundColor: '#60A5FA' }}] }},
    options: {{ plugins: {{ legend: {{ display: false }} }}, scales: {{
        x: {{ ticks: {{ color: '#9CA3AF', font: {{ size: 10 }} }}, grid: {{ color: 'rgba(255,255,255,0.10)' }} }},
        y: {{ ticks: {{ color: '#9CA3AF', font: {{ size: 10 }} }}, grid: {{ color: 'rgba(255,255,255,0.10)' }}, beginAtZero: true }}
    }}, maintainAspectRatio: false }}
  }});

  // royalty bar
  const rb = [
    {{ label: '0-3%',  min: 0,   max: 3 }},
    {{ label: '3-5%',  min: 3,   max: 5 }},
    {{ label: '5-7%',  min: 5,   max: 7 }},
    {{ label: '7-9%',  min: 7,   max: 9 }},
    {{ label: '9-12%', min: 9,   max: 12 }},
    {{ label: '12%+',  min: 12,  max: 100 }},
  ];
  const rbCounts = rb.map(t => filtered.filter(b => b.royalty != null && b.royalty >= t.min && b.royalty < t.max).length);
  if (charts.royalty) charts.royalty.destroy();
  charts.royalty = new Chart(document.getElementById('chartRoyalty').getContext('2d'), {{
    type: 'bar',
    data: {{ labels: rb.map(t => t.label), datasets: [{{ data: rbCounts,
              backgroundColor: rb.map((_, i) => i < 3 ? '#10B981' : i < 4 ? '#F59E0B' : '#EF4444') }}] }},
    options: {{ plugins: {{ legend: {{ display: false }} }}, scales: {{
        x: {{ ticks: {{ color: '#9CA3AF', font: {{ size: 10 }} }}, grid: {{ color: 'rgba(255,255,255,0.10)' }} }},
        y: {{ ticks: {{ color: '#9CA3AF', font: {{ size: 10 }} }}, grid: {{ color: 'rgba(255,255,255,0.10)' }}, beginAtZero: true }}
    }}, maintainAspectRatio: false }}
  }});

  // Revenue vs royalty scatter — color by Item 19 disclosure quality
  // and overlay a "Franchisee-friendly zone" (low royalty + high revenue)
  const scatter = filtered
    .filter(b => b.top_revenue != null && b.royalty != null && b.royalty > 0 && b.top_revenue >= 100000)
    .map(b => ({{
      x: b.royalty, y: b.top_revenue,
      name: b.name, slug: b.slug, industry: b.industry_label,
      i19_quality: b.i19_quality,
    }}));
  const colorFor = q => q === 'broad' ? 'rgba(52,211,153,0.7)'
                     : q === 'thin'  ? 'rgba(251,191,36,0.7)'
                     :                  'rgba(148,163,184,0.5)';
  if (charts.scatter) charts.scatter.destroy();
  // Friendly-zone overlay plugin
  const friendlyZonePlugin = {{
    id: 'friendlyZone',
    beforeDatasetsDraw: (chart) => {{
      const {{ctx, chartArea, scales}} = chart;
      if (!chartArea) return;
      const xRoy = scales.x.getPixelForValue(6);   // royalty <=6%
      const yRev = scales.y.getPixelForValue(500000); // revenue >=$500K
      ctx.save();
      ctx.fillStyle = 'rgba(52,211,153,0.08)';
      ctx.fillRect(chartArea.left, chartArea.top, xRoy - chartArea.left, yRev - chartArea.top);
      ctx.strokeStyle = 'rgba(52,211,153,0.3)';
      ctx.setLineDash([4, 4]);
      ctx.strokeRect(chartArea.left, chartArea.top, xRoy - chartArea.left, yRev - chartArea.top);
      ctx.fillStyle = 'rgba(52,211,153,0.6)';
      ctx.font = '600 11px -apple-system, sans-serif';
      ctx.fillText('Franchisee-friendly zone (low royalty, high revenue)',
                   chartArea.left + 8, chartArea.top + 18);
      ctx.restore();
    }}
  }};
  charts.scatter = new Chart(document.getElementById('chartScatter').getContext('2d'), {{
    type: 'scatter',
    data: {{ datasets: [{{
      data: scatter,
      backgroundColor: scatter.map(p => colorFor(p.i19_quality)),
      pointRadius: 5, pointHoverRadius: 8,
      borderColor: scatter.map(p => colorFor(p.i19_quality).replace('0.7','1').replace('0.5','0.8')),
    }}] }},
    plugins: [friendlyZonePlugin],
    options: {{
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          backgroundColor: '#0A0E14', borderColor: 'rgba(255,255,255,0.16)', borderWidth: 1,
          titleColor: '#F2F3F5', bodyColor: '#F2F3F5', padding: 10,
          callbacks: {{
            title: ctx => ctx[0].raw.name,
            label: ctx => {{
              const p = ctx.raw;
              const qLabel = p.i19_quality === 'broad' ? 'Broad Item 19'
                            : p.i19_quality === 'thin' ? 'Thin Item 19'
                            : 'No Item 19';
              return [
                `Industry: ${{p.industry}}`,
                `Royalty: ${{p.x.toFixed(1)}}%`,
                `Top median revenue: $${{p.y.toLocaleString()}}`,
                `Disclosure: ${{qLabel}}`,
                '(Click to open brand page)',
              ];
            }}
          }}
        }}
      }},
      scales: {{
        x: {{
          title: {{ display: true, text: 'Royalty %', color: '#9CA3AF' }},
          ticks: {{
            color: '#9CA3AF',
            stepSize: 5,
            callback: v => v + '%',
          }},
          grid: {{ color: 'rgba(255,255,255,0.10)' }},
          min: 0, max: 25,
        }},
        y: {{
          title: {{ display: true, text: 'Top median revenue (log scale)', color: '#9CA3AF' }},
          type: 'logarithmic',
          ticks: {{
            color: '#9CA3AF',
            callback: v => {{
              if (v === 1e5)  return '$100K';
              if (v === 1e6)  return '$1M';
              if (v === 1e7)  return '$10M';
              if (v === 1e8)  return '$100M';
              return null;  // suppress fractional log ticks (kills the $0M duplicates)
            }},
          }},
          grid: {{ color: 'rgba(255,255,255,0.10)' }},
          min: 100000,
        }}
      }},
      maintainAspectRatio: false,
      onClick: (e, items) => {{
        if (items.length) window.open(`/franchise/${{scatter[items[0].index].slug}}/`, '_blank');
      }},
    }}
  }});
}}

function renderHeader() {{
  const head = document.getElementById('master-head');
  const cols = visibleColumns();
  const colCount = cols.length + 2; // +checkbox +star
  let html = `
    <th style="width: 28px;"><input type="checkbox" id="check-all" title="Select all visible"></th>
    <th style="width: 28px;" title="★ = saved to your watchlist (persists in this browser)">★</th>
  `;
  cols.forEach(c => {{
    const cls = `sortable ${{c.align === 'num' ? 'num' : ''}}`.trim();
    const tip = c.tip ? ` data-tip="${{escHtml(c.tip)}}"` : '';
    html += `<th class="${{cls}}" data-sort="${{c.sort}}"${{tip}}>${{escHtml(c.label)}}</th>`;
  }});
  head.innerHTML = html;
  // Apply current sort indicator
  head.querySelectorAll('th').forEach(th => {{
    th.classList.remove('sort-asc', 'sort-desc');
    if (th.dataset.sort === sortState.key) {{
      th.classList.add(sortState.dir === 'asc' ? 'sort-asc' : 'sort-desc');
    }}
  }});
  // Reattach check-all listener
  const checkAll = document.getElementById('check-all');
  if (checkAll) {{
    checkAll.addEventListener('change', (e) => {{
      const visibleSlugs = [...els.body.querySelectorAll('.row-check')].map(cb => cb.dataset.slug);
      if (e.target.checked) visibleSlugs.forEach(s => selectedSlugs.add(s));
      else visibleSlugs.forEach(s => selectedSlugs.delete(s));
      saveSelected(); updateCompareBtn(); rerender();
    }});
  }}
  return colCount;
}}

function renderColsMenu() {{
  const menu = document.getElementById('cols-menu');
  let html = '<div style="font-size:11px;color:var(--text-secondary);font-weight:600;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px;">Show columns</div>';
  COLUMNS.forEach(c => {{
    const checked = c.always || visibleColKeys.has(c.key) ? 'checked' : '';
    const disabled = c.always ? 'disabled' : '';
    html += `<label><input type="checkbox" data-col="${{c.key}}" ${{checked}} ${{disabled}}> ${{escHtml(c.label)}}${{c.always ? ' <span style="color:var(--text-tertiary);font-size:11px;">(always)</span>' : ''}}</label>`;
  }});
  html += `<div class="sep"></div>
    <button class="btn" id="cols-default" style="width:100%;">Reset to defaults</button>`;
  menu.innerHTML = html;
}}

function renderTable(filtered) {{
  els.status.textContent = `Showing ${{filtered.length.toLocaleString()}} of ${{BRANDS.length.toLocaleString()}}`;
  const colCount = renderHeader();
  if (filtered.length === 0) {{
    els.body.innerHTML = '';
    els.empty.style.display = '';
    return;
  }}
  els.empty.style.display = 'none';
  const sorted = [...filtered].sort((a, b) => {{
    let av = a[sortState.key], bv = b[sortState.key];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    if (typeof av === 'string' || typeof bv === 'string') {{
      return sortState.dir === 'asc'
        ? String(av).localeCompare(String(bv))
        : String(bv).localeCompare(String(av));
    }}
    return sortState.dir === 'asc' ? (av - bv) : (bv - av);
  }});
  const VISIBLE_CAP = 300;
  const slice = sorted.slice(0, VISIBLE_CAP);
  const cols = visibleColumns();
  els.body.innerHTML = slice.map(b => {{
    const checked = selectedSlugs.has(b.slug) ? 'checked' : '';
    const starred = watchlistSlugs.has(b.slug) ? 'active' : '';
    let cells = `
      <td><input type="checkbox" class="row-check" data-slug="${{escHtml(b.slug)}}" ${{checked}}></td>
      <td><button class="star ${{starred}}" data-watch="${{escHtml(b.slug)}}" title="${{starred ? 'Remove from watchlist' : 'Add to watchlist'}}">★</button></td>
    `;
    cols.forEach(c => {{
      const cls = c.align === 'num' ? 'num' : '';
      cells += `<td class="${{cls}}">${{c.render(b)}}</td>`;
    }});
    return `<tr>${{cells}}</tr>`;
  }}).join('');
  if (sorted.length > VISIBLE_CAP) {{
    els.body.innerHTML += `<tr><td colspan="${{colCount}}" style="text-align:center;color:var(--text-tertiary);padding:14px;">+ ${{(sorted.length - VISIBLE_CAP).toLocaleString()}} more rows hidden — narrow filters or sort to surface them</td></tr>`;
  }}
}}

function rerender() {{
  const filtered = applyFilters();
  renderKPIs(filtered);
  renderCharts(filtered);
  renderTable(filtered);
  writeURL();
}}

// ===== Wire events =====
['search','industry','invMin','invMax','royMin','royMax','outletsMin','state','item19','watchlist'].forEach(k => {{
  els[k].addEventListener('input', rerender);
  els[k].addEventListener('change', rerender);
}});

// Star toggle (delegated)
els.body.addEventListener('click', (e) => {{
  if (!e.target.matches('.star')) return;
  const slug = e.target.dataset.watch;
  if (watchlistSlugs.has(slug)) {{
    watchlistSlugs.delete(slug);
    e.target.classList.remove('active');
    e.target.title = 'Add to watchlist';
  }} else {{
    watchlistSlugs.add(slug);
    e.target.classList.add('active');
    e.target.title = 'Remove from watchlist';
  }}
  saveWatchlist();
}});

// Header click → sort (delegated since headers are re-rendered)
document.getElementById('master-head').addEventListener('click', (e) => {{
  const th = e.target.closest('th.sortable');
  if (!th) return;
  if (sortState.key === th.dataset.sort) {{
    sortState.dir = sortState.dir === 'asc' ? 'desc' : 'asc';
  }} else {{
    sortState.key = th.dataset.sort;
    sortState.dir = th.classList.contains('num') ? 'desc' : 'asc';
  }}
  rerender();
}});

// Columns menu toggle + items
document.getElementById('cols-btn').addEventListener('click', (e) => {{
  e.stopPropagation();
  const menu = document.getElementById('cols-menu');
  menu.hidden = !menu.hidden;
}});
document.addEventListener('click', (e) => {{
  const menu = document.getElementById('cols-menu');
  if (!menu.hidden && !e.target.closest('.cols-menu-wrap')) menu.hidden = true;
}});
document.getElementById('cols-menu').addEventListener('change', (e) => {{
  if (!e.target.matches('input[data-col]')) return;
  const key = e.target.dataset.col;
  if (e.target.checked) visibleColKeys.add(key);
  else visibleColKeys.delete(key);
  saveColumns(); rerender();
}});
document.getElementById('cols-menu').addEventListener('click', (e) => {{
  if (e.target.id !== 'cols-default') return;
  visibleColKeys = new Set(defaultVisible);
  saveColumns(); renderColsMenu(); rerender();
}});

els.reset.addEventListener('click', () => {{
  ['search','invMin','invMax','royMin','royMax','outletsMin'].forEach(k => els[k].value = '');
  els.industry.value = '';
  els.state.value = '';
  els.item19.value = '';
  els.watchlist.checked = false;
  rerender();
}});

// Bottom action bar: Clear + Export selected
document.getElementById('compare-clear').addEventListener('click', () => {{
  selectedSlugs.clear(); saveSelected(); updateCompareBtn(); rerender();
}});
document.getElementById('compare-csv-bar').addEventListener('click', () => {{
  document.getElementById('compare-csv').click();  // reuse modal export logic if modal closed, else trigger directly
}});

els.copyUrl.addEventListener('click', () => {{
  writeURL();
  navigator.clipboard.writeText(window.location.href).then(() => {{
    const orig = els.copyUrl.textContent;
    els.copyUrl.textContent = 'Copied!';
    setTimeout(() => {{ els.copyUrl.textContent = orig; }}, 1500);
  }});
}});

els.csvBtn.addEventListener('click', () => {{
  const filtered = applyFilters();
  const cols = ['slug','name','industry_label','total_outlets','investment_low','investment_high','royalty','marketing','top_revenue','n_item19','filing_year','filing_state'];
  const header = ['Brand slug','Brand','Industry','Outlets','Inv low','Inv high','Royalty %','Marketing %','Top median revenue','Item 19 records','Filing year','Filing state'];
  const escCsv = v => {{
    if (v == null) return '';
    const s = String(v);
    return /[,"\\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  }};
  const rows = [header.join(',')];
  filtered.forEach(b => rows.push(cols.map(c => escCsv(b[c])).join(',')));
  const blob = new Blob([rows.join('\\n')], {{ type: 'text/csv' }});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = `franchisedepth-${{filtered.length}}-brands-${{new Date().toISOString().slice(0,10)}}.csv`;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
}});

// Quick-start preset chips
const PRESETS = {{
  'best-roi':        () => {{ resetAll(); els.outletsMin.value = '100'; els.invMax.value = '200000'; els.royMax.value = '7'; }},
  'top-food':        () => {{ resetAll(); els.industry.value = 'Food Quick Service'; sortState = {{key:'top_revenue', dir:'desc'}}; }},
  'low-royalty':     () => {{ resetAll(); els.royMax.value = '5'; sortState = {{key:'royalty', dir:'asc'}}; }},
  'largest-i19':     () => {{ resetAll(); els.outletsMin.value = '500'; els.item19.value = 'yes'; sortState = {{key:'total_outlets', dir:'desc'}}; }},
  'affordable':      () => {{ resetAll(); els.invMax.value = '50000'; sortState = {{key:'investment_low', dir:'asc'}}; }},
  'fastest-growing': () => {{ resetAll(); sortState = {{key:'growth_pct', dir:'desc'}}; }},
}};
function resetAll() {{
  ['search','invMin','invMax','royMin','royMax','outletsMin'].forEach(k => els[k].value = '');
  els.industry.value = ''; els.state.value = ''; els.item19.value = ''; els.watchlist.checked = false;
}}
document.querySelectorAll('.chip').forEach(chip => {{
  chip.addEventListener('click', () => {{
    document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
    const fn = PRESETS[chip.dataset.preset];
    if (fn) {{ fn(); rerender(); }}
  }});
}});

// ===== Multi-select compare wiring =====
// Row checkbox toggle (delegated)
els.body.addEventListener('change', (e) => {{
  if (!e.target.matches('.row-check')) return;
  const slug = e.target.dataset.slug;
  if (e.target.checked) selectedSlugs.add(slug);
  else selectedSlugs.delete(slug);
  saveSelected();
  updateCompareBtn();
}});

// Select-all-visible
document.getElementById('check-all').addEventListener('change', (e) => {{
  const visibleSlugs = [...els.body.querySelectorAll('.row-check')].map(cb => cb.dataset.slug);
  if (e.target.checked) {{
    visibleSlugs.forEach(s => selectedSlugs.add(s));
  }} else {{
    visibleSlugs.forEach(s => selectedSlugs.delete(s));
  }}
  saveSelected(); updateCompareBtn();
  // Re-render to flip the row checkboxes
  rerender();
}});

// Open compare modal
document.getElementById('compare-btn').addEventListener('click', () => {{
  const slugs = [...selectedSlugs];
  const picked = BRANDS.filter(b => selectedSlugs.has(b.slug));
  if (!picked.length) return;
  const rows = [
    ['Industry',          b => `<span class="ind">${{escHtml(b.industry_label)}}</span>`],
    ['Outlet trajectory', b => `<canvas class="sparkline" data-slug="${{escHtml(b.slug)}}"></canvas>`],
    ['Total outlets',     b => fmtNum(b.total_outlets)],
    ['Outlet growth',     b => b.growth_pct == null ? '—' : `<span class="${{b.growth_pct > 5 ? 'growth-up' : b.growth_pct < -5 ? 'growth-down' : 'growth-flat'}}">${{b.growth_pct > 0 ? '+' : ''}}${{b.growth_pct}}%</span> <span class="val-muted">${{b.growth_span || ''}}</span>`],
    ['US states',         b => b.state_count != null ? b.state_count : '—'],
    ['Investment low',    b => `<span class="${{investmentClass(b.investment_low)}}">${{fmtDollarFull(b.investment_low)}}</span>`],
    ['Investment high',   b => fmtDollarFull(b.investment_high)],
    ['Royalty %',         b => `<span class="${{royaltyClass(b.royalty)}}">${{fmtPct(b.royalty)}}</span>`],
    ['Marketing %',       b => fmtPct(b.marketing)],
    ['Initial franchise fee', b => fmtDollarFull(b.initial_fee_low)],
    ['Top median revenue', b => fmtDollarFull(b.top_revenue)],
    ['Worst-performer floor (Item 19 profit ⌄)', b => b.worst_floor == null ? '—' : `<span class="growth-down">−$${{Math.abs(b.worst_floor).toLocaleString()}}</span>`],
    ['Item 19 records',   b => b.n_item19 || 0],
    ['Filing year',       b => b.filing_year || '—'],
    ['Filing state',      b => b.filing_state || '—'],
  ];
  const html = `
    <table class="compare-table">
      <thead><tr>
        <th class="row-label">Metric</th>
        ${{picked.map(b => `<th class="brand-cell"><a href="/franchise/${{escHtml(b.slug)}}/">${{escHtml(b.name)}}</a></th>`).join('')}}
      </tr></thead>
      <tbody>
        ${{rows.map(([label, fn]) => `
          <tr>
            <td class="row-label">${{escHtml(label)}}</td>
            ${{picked.map(b => `<td>${{fn(b)}}</td>`).join('')}}
          </tr>
        `).join('')}}
      </tbody>
    </table>
  `;
  document.getElementById('compare-body').innerHTML = html;
  document.getElementById('compare-modal').style.display = 'flex';
  // Draw outlet-history sparklines per brand
  picked.forEach(b => {{
    if (!b.outlet_history || b.outlet_history.length < 2) return;
    const canvas = document.querySelector(`.sparkline[data-slug="${{b.slug.replace(/"/g, '\\\\"')}}"]`);
    if (!canvas) return;
    new Chart(canvas.getContext('2d'), {{
      type: 'line',
      data: {{ labels: b.outlet_history.map(p => p[0]),
              datasets: [{{ data: b.outlet_history.map(p => p[1]),
                           borderColor: '#60A5FA', backgroundColor: 'rgba(56,189,248,0.15)',
                           tension: 0.3, fill: true, pointRadius: 2, borderWidth: 2 }}] }},
      options: {{ plugins: {{ legend: {{ display: false }}, tooltip: {{ callbacks: {{
                    label: ctx => `${{ctx.parsed.x ? ctx.parsed.x : ctx.label}}: ${{ctx.parsed.y.toLocaleString()}} outlets`
                  }} }} }},
                  scales: {{ x: {{ display: false }}, y: {{ display: false }} }},
                  maintainAspectRatio: false }}
    }});
  }});
}});

document.getElementById('compare-close').addEventListener('click', () => {{
  document.getElementById('compare-modal').style.display = 'none';
}});
document.getElementById('compare-modal').addEventListener('click', (e) => {{
  if (e.target.id === 'compare-modal') {{
    document.getElementById('compare-modal').style.display = 'none';
  }}
}});

// Export compare CSV
document.getElementById('compare-csv').addEventListener('click', () => {{
  const picked = BRANDS.filter(b => selectedSlugs.has(b.slug));
  const cols = ['slug','name','industry_label','total_outlets','growth_pct','state_count','investment_low','investment_high','royalty','marketing','initial_fee_low','top_revenue','n_item19','filing_year','filing_state'];
  const header = ['slug','brand','industry','outlets','growth_pct','states','inv_low','inv_high','royalty','marketing','initial_fee','top_rev','item19_records','filing_year','filing_state'];
  const escCsv = v => v == null ? '' : (/[,"\\n]/.test(String(v)) ? '"' + String(v).replace(/"/g,'""') + '"' : String(v));
  const lines = [header.join(',')];
  picked.forEach(b => lines.push(cols.map(c => escCsv(b[c])).join(',')));
  const blob = new Blob([lines.join('\\n')], {{ type: 'text/csv' }});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `franchisedepth-compare-${{picked.length}}-${{new Date().toISOString().slice(0,10)}}.csv`;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
}});

// Init
readURL();
renderColsMenu();
updateCompareBtn();
window.addEventListener('load', rerender);  // wait for Chart.js
rerender();
</script>

</body>
</html>
"""


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    brands = fetch_brands(conn)
    html = render_html(brands)
    out_path = OUT_DIR / "index.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Wrote {out_path} ({len(html):,} bytes)")
    print(f"Dashboard v3: {len(brands)} brands · sidebar filters · 3 charts · master table · CSV export · URL state · 6 preset chips")


if __name__ == "__main__":
    main()
