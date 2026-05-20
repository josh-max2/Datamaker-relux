"""Generate static HTML site into ../docs/ from the SQLite DB.

Builds:
  docs/index.html                        — all brands, searchable
  docs/about/index.html                  — what this site is
  docs/franchise/{slug}/index.html       — one per brand
  docs/category/{slug}/index.html        — one per industry
  docs/sitemap.xml
  docs/robots.txt
  docs/style.css

Run from fdd-tool/:  uv run python -m src.site_gen
"""
from __future__ import annotations

import re
import shutil
import sqlite3
import statistics
import sys
from datetime import datetime
from pathlib import Path

import os
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src import db, derived

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT.parent / "docs"
TEMPLATES_DIR = ROOT / "src" / "templates"

# Custom domain wired up 2026-05-17 — franchisedepth.com points at the GitHub Pages site.
# URL prefix is empty (root). For local dev against /Parser/ subpath, set FD_SITE_PREFIX=/Parser.
# Mirror repo (Datamaker-relux): served from github.io project page, so URLs
# need the /Datamaker-relux/ prefix and absolute URLs use the github.io host.
SITE_PREFIX = os.environ.get("FD_SITE_PREFIX", "/Datamaker-relux")
SITE_NAME = "FranchiseDepth"

# Production host — used for absolute URLs in sitemap.xml, schema, and OG meta.
SITE_HOST = os.environ.get("FD_SITE_HOST", "https://josh-max2.github.io")

# Custom domain to emit as docs/CNAME so GitHub Pages preserves it across deploys.
# Empty = no CNAME file written. Mirror MUST NOT claim franchisedepth.com or
# it will steal the domain from the live parser repo.
CUSTOM_DOMAIN = os.environ.get("FD_CUSTOM_DOMAIN", "")

# Formspree form ID — the part after "/f/" in the endpoint URL.
# All forms POST to https://formspree.io/f/{FORMSPREE_ID}.
# Set FD_FORMSPREE_ID env var to override at build time.
FORMSPREE_ID = os.environ.get("FD_FORMSPREE_ID", "xjgzvgrz")

# Google Analytics 4 measurement ID. Format: G-XXXXXXXXXX
# Loads gtag.js (consent-gated by _ga4.js) on every page. Empty string = no GA4.
# This is the franchisedepth.com GA4 property; the ID is public per Google's design.
GA4_MEASUREMENT_ID = os.environ.get("FD_GA4_ID", "G-ZEPEB3Z67R")

# Microsoft Clarity project ID. Public per Clarity's design.
# Consent-gated by _clarity.js — only loads after the user accepts analytics.
CLARITY_PROJECT_ID = os.environ.get("FD_CLARITY_ID", "wspuk90u8d")

# Google Search Console site-verification token. Public per Google's design.
# Empty string = no verification meta tag. Set once GSC asks for the HTML tag method.
GSC_VERIFICATION_TOKEN = os.environ.get(
    "FD_GSC_VERIFICATION", "K4jBh7vFO-rr4gxM9JotDwBeAtCWdXOm7bEwSMsfv3I"
)

# Bing Webmaster site-authentication token (the "<meta name="msvalidate.01"" value).
# Get one from https://www.bing.com/webmasters/ → Add site → "HTML meta tag" method.
# Empty string = no verification meta tag emitted.
BING_VERIFICATION_TOKEN = os.environ.get("FD_BING_VERIFICATION", "")

# FlexOffers affiliate-network domain-verification token (<meta name="fo-verify">).
# Used during affiliate-program approval to prove domain ownership.
FLEXOFFERS_VERIFICATION_TOKEN = os.environ.get(
    "FD_FLEXOFFERS_VERIFICATION", "7eb2e7cf-9f84-459a-b48f-64cf7a609967"
)

# Impact affiliate-network site-verification token (<meta name="impact-site-verification">).
# Note: Impact uses `value=` attribute, not `content=` (non-standard but their format).
IMPACT_VERIFICATION_TOKEN = os.environ.get(
    "FD_IMPACT_VERIFICATION", "83778c12-e712-4dd7-9e77-9ffb6329f776"
)

# IndexNow API key (single key works for Bing, Yandex, Seznam.cz, Naver).
# Emitted as docs/<KEY>.txt at site root to prove ownership.
# Used by scripts/indexnow_submit.py to push the sitemap to all participating engines.
INDEXNOW_API_KEY = os.environ.get("FD_INDEXNOW_KEY", "108a9bb5a8ed4718a9ff03218f2899f6")


def url_for(rel_path: str) -> str:
    """Build an absolute path that works under SITE_PREFIX."""
    if rel_path.startswith("http"):
        return rel_path
    rel = rel_path.lstrip("/")
    if not rel:
        return SITE_PREFIX + "/"
    return f"{SITE_PREFIX}/{rel}"


def fmt_value(v, label: str | None) -> str:
    """Format a numeric value based on inferred metric type."""
    if v is None:
        return "—"
    label_l = (label or "").lower()
    # Percentage metrics
    if any(s in label_l for s in ("margin", "rate", "%", "percent", "conversion")):
        return f"{v:.1f}%"
    # Per-person micro amounts
    if "per person" in label_l and abs(v) < 100:
        return f"${v:.2f}"
    # Currency (default)
    if abs(v) >= 1000:
        return f"${v:,.0f}"
    return f"${v:,.2f}"


def format_int(v) -> str:
    if v is None:
        return "—"
    return f"{int(v):,}"


# Acronyms to preserve when title-casing industry labels
_ACRONYMS = {"Hvac": "HVAC", "Sba": "SBA", "Bbq": "BBQ", "Hr": "HR"}


# Calculator op-cost defaults by industry slug — operating costs (COGS + rent +
# labor + admin) as a fraction of revenue, before franchisor fees. Single-knob
# replacement for the v1 calculator's 9 separate operating-cost inputs.
# Numbers are industry-typical midpoints, not from per-brand data.
_OP_COST_PCT_BY_INDUSTRY = {
    "food-quick-service": 0.70,       # high COGS + labor + rent
    "hospitality": 0.65,
    "retail-services": 0.60,
    "salon-beauty": 0.55,
    "fitness-wellness": 0.55,         # high rent + equipment
    "automotive-services": 0.55,
    "dry-cleaning": 0.55,
    "pet-services": 0.55,
    "education": 0.50,
    "mobility-accessibility": 0.50,
    "home-services-cleaning": 0.45,
    "home-services-handyman": 0.45,
    "home-services-hvac": 0.45,
    "home-services-inspection": 0.40,
    "home-services-moving": 0.50,
    "home-services-outdoor": 0.45,
    "home-services-painting": 0.45,
    "home-services-plumbing": 0.45,
    "home-services-remodeling": 0.50,
    "home-services-restoration": 0.50,
    "home-services-roofing": 0.50,
    "home-services-senior-care": 0.55,
    "tax-financial": 0.40,
    "staffing-employment": 0.40,
    "real-estate": 0.40,
    "property-management": 0.40,
    "tech-services": 0.40,
    "b2b-supplies": 0.45,
}
_OP_COST_DEFAULT_PCT = 0.50


def op_cost_pct_for(industry: str | None) -> float:
    return _OP_COST_PCT_BY_INDUSTRY.get(industry or "", _OP_COST_DEFAULT_PCT)


def nice_round(value: float | int | None) -> int | None:
    """Round a dollar value to a human-friendly step.

    <$100k     → nearest $5k
    <$500k     → nearest $10k
    <$2M       → nearest $25k
    <$10M      → nearest $100k
    >=$10M     → nearest $500k
    """
    if value is None:
        return None
    v = abs(float(value))
    if v < 100_000:
        step = 5_000
    elif v < 500_000:
        step = 10_000
    elif v < 2_000_000:
        step = 25_000
    elif v < 10_000_000:
        step = 100_000
    else:
        step = 500_000
    return int(round(value / step) * step)


def industry_label(industry: str | None) -> str:
    if not industry:
        return "Other"
    raw = industry.replace("home-services-", "").replace("-", " ").title()
    for bad, good in _ACRONYMS.items():
        raw = raw.replace(bad, good)
    return raw


def compute_growth_direction(outlet_summary: list[dict] | None) -> tuple[str, float | None]:
    """Compute multi-year outlet growth direction from Item 20 yearly totals.

    Returns (label, pct_change). Labels: 'rapidly-growing', 'growing', 'stable',
    'contracting', or 'unknown' when insufficient data.
    """
    if not outlet_summary or len(outlet_summary) < 2:
        return "unknown", None
    first_total = outlet_summary[0].get("total")
    last_total = outlet_summary[-1].get("total")
    if not first_total or not last_total or first_total == 0:
        return "unknown", None
    pct = (last_total - first_total) / first_total * 100
    if pct >= 50:
        return "rapidly-growing", pct
    if pct >= 10:
        return "growing", pct
    if pct >= -5:
        return "stable", pct
    return "contracting", pct


def build_summary_paragraph(brand: dict, latest_fdd: dict, fees: dict | None,
                             total_outlets: int | None, outlet_summary: list[dict] | None,
                             has_item19: bool) -> dict:
    """Build the opening summary paragraph + supporting bolded numbers for a brand page.

    Target 80-120 words. Adapts when data is sparse (e.g., no outlet count or no
    investment range). Returns dict with `html` and `word_count`.
    """
    brand_name = brand.get("brand_name") or brand.get("legal_name") or "This franchise"
    industry = industry_label(brand.get("industry"))
    state = brand.get("state_of_inc") or "the United States"
    filing_year = latest_fdd.get("filing_year") or "the most recent"
    filing_state = latest_fdd.get("filing_state") or "a registration state"
    issuance = latest_fdd.get("effective_date")

    # Fees
    fee_str = ""
    inv_str = ""
    royalty_str = ""
    if fees:
        lo, hi = fees.get("initial_franchise_fee_low"), fees.get("initial_franchise_fee_high")
        if lo and hi and lo != hi:
            fee_str = f"an initial franchise fee of <strong>${lo:,.0f}–${hi:,.0f}</strong>"
        elif lo or hi:
            fee_str = f"an initial franchise fee of <strong>${(lo or hi):,.0f}</strong>"
        inv_lo, inv_hi = fees.get("total_investment_low"), fees.get("total_investment_high")
        if inv_lo and inv_hi:
            inv_str = f"a total investment range of <strong>${inv_lo:,.0f}–${inv_hi:,.0f}</strong>"
        if fees.get("royalty_pct"):
            royalty_str = f"an ongoing royalty of <strong>{fees['royalty_pct']}%</strong> of gross sales"

    # Outlets
    outlets_str = ""
    if total_outlets:
        outlets_str = f"<strong>{total_outlets:,}</strong> outlets reported as of the latest filing year"

    # Growth
    growth_label, growth_pct = compute_growth_direction(outlet_summary)
    growth_phrases = {
        "rapidly-growing": f"a rapidly-growing system (up {growth_pct:.0f}% over the reporting period)" if growth_pct else "a rapidly-growing system",
        "growing": f"a growing system (up {growth_pct:.0f}% over the reporting period)" if growth_pct else "a growing system",
        "stable": "a stable system with little net change in outlet count over the reporting period",
        "contracting": f"a contracting system (down {abs(growth_pct):.0f}% over the reporting period)" if growth_pct else "a contracting system",
        "unknown": "",
    }
    growth_str = growth_phrases.get(growth_label, "")

    # Sentence 1: identity + fees/investment/outlets
    s1_parts = [f"<strong>{brand_name}</strong>"]
    if industry and industry != "Other":
        s1_parts.append(f"is a {industry.lower()} franchise")
    else:
        s1_parts.append("is a franchise")
    if state and state != "the United States":
        s1_parts.append(f"headquartered in {state}")
    s1_components = [s for s in (fee_str, inv_str) if s]
    if outlets_str:
        s1_components.append(outlets_str)
    if s1_components:
        s1_parts.append("offering")
        s1_parts.append(", ".join(s1_components[:-1]) + (", and " if len(s1_components) > 1 else "") + s1_components[-1])
    sentence_one = " ".join(s1_parts) + "."

    # Sentence 2: filing source + recency context
    src_bits = [f"the {filing_year} Franchise Disclosure Document filed in {filing_state}"]
    if issuance:
        src_bits.append(f"with an issuance date of {issuance}")
    sentence_two = "Data below is extracted from " + ", ".join(src_bits) + "."

    # Sentence 3: growth + royalty (rolled together for length)
    s3_parts = []
    if growth_str:
        s3_parts.append(f"The brand is {growth_str}")
    if royalty_str:
        s3_parts.append(f"and charges {royalty_str}")
    sentence_three = (". ".join([p for p in [s3_parts[0] if s3_parts else None] if p]))
    if len(s3_parts) > 1:
        sentence_three = s3_parts[0] + " " + s3_parts[1]
    if sentence_three:
        sentence_three += "."

    # Sentence 4: earnings disclosure
    if has_item19:
        sentence_four = ("The franchisor publicly discloses actual financial performance for "
                         "franchised outlets in Item 19 of the FDD, giving prospective buyers a "
                         "data-backed basis for comparison.")
    else:
        sentence_four = ("The franchisor <strong>does not publicly disclose</strong> outlet-level "
                         "earnings data in Item 19 of the FDD — prospective buyers should validate "
                         "financials directly with current franchisees listed in Item 20.")

    # Sentence 5 (sparse-data brands only): note what's missing, honestly
    missing_bits = []
    if not inv_str: missing_bits.append("total investment range")
    if not outlets_str: missing_bits.append("outlet count")
    if not growth_str: missing_bits.append("multi-year growth trajectory")
    sentence_five = ""
    if len(missing_bits) >= 2:
        sentence_five = ("This filing does not separately disclose " +
                         (", ".join(missing_bits[:-1]) + ", or " + missing_bits[-1]
                          if len(missing_bits) > 2 else " or ".join(missing_bits)) +
                         " — see the source FDD on the state portal for any related data.")

    html = " ".join(s for s in (sentence_one, sentence_two, sentence_three, sentence_four, sentence_five) if s)
    import re as _re
    text_only = _re.sub(r"<[^>]+>", "", html)
    return {"html": html, "word_count": len(text_only.split())}


# Industry-typical operating margins (low, high) per the user's spec.
# Used ONLY for breakeven estimation with explicit disclaimer.
MARGIN_BANDS = {
    "food-quick-service": (0.08, 0.15),
    "home-services-plumbing": (0.18, 0.30),
    "home-services-hvac": (0.18, 0.30),
    "home-services-cleaning": (0.18, 0.30),
    "home-services-restoration": (0.18, 0.30),
    "home-services-roofing": (0.18, 0.30),
    "home-services-painting": (0.18, 0.30),
    "home-services-handyman": (0.18, 0.30),
    "home-services-moving": (0.15, 0.25),
    "home-services-outdoor": (0.18, 0.30),
    "home-services-senior-care": (0.15, 0.25),
    "home-services-remodeling": (0.15, 0.25),
    "real-estate": (0.10, 0.20),
}
DEFAULT_MARGIN = (0.10, 0.20)


def compute_risk_badge(conn: sqlite3.Connection, fdd_id: int) -> dict | None:
    """Risk badge from Item 20 state-year closure data.

    closure_rate = sum(terminated + nonrenewed + ceased_other) / sum(outlets_start)
    Buckets: <3% green, 3-7% yellow, >7% red. Returns None if insufficient data.
    """
    rows = conn.execute("""
        SELECT
            COALESCE(SUM(outlets_terminated), 0) AS terminated,
            COALESCE(SUM(outlets_nonrenewed), 0) AS nonrenewed,
            COALESCE(SUM(outlets_ceased_other), 0) AS ceased,
            COALESCE(SUM(outlets_start), 0) AS starts,
            MIN(year) AS yr_min, MAX(year) AS yr_max
        FROM item20_locations
        WHERE fdd_id = ? AND state != 'TOTAL'
    """, (fdd_id,)).fetchone()
    if not rows or not rows["starts"]:
        return None
    total_closures = (rows["terminated"] or 0) + (rows["nonrenewed"] or 0) + (rows["ceased"] or 0)
    rate = total_closures / rows["starts"]
    if rate < 0.03:
        tier, label = "green", "Stable"
    elif rate < 0.07:
        tier, label = "yellow", "Mixed"
    else:
        tier, label = "red", "Contracting"
    yr_span = ""
    if rows["yr_min"] and rows["yr_max"]:
        if rows["yr_min"] == rows["yr_max"]:
            yr_span = f" in {rows['yr_min']}"
        else:
            yr_span = f" from {rows['yr_min']}–{rows['yr_max']}"
    return {
        "tier": tier, "label": label,
        "rate_pct": round(rate * 100, 1),
        "closures": total_closures,
        "starts": rows["starts"],
        "year_span": yr_span,
    }


_UNIT_TO_MULTIPLIER = {"weekly": 52, "monthly": 12, "daily": 365, "annual": 1}


def infer_period_multiplier(metric_raw: str | None) -> int:
    """LEGACY fallback for records without a structured unit_period field.

    Returns multiplier to annualize a value. 52 for weekly, 12 for monthly, 1 otherwise.
    Newer extractions populate `unit_period` directly — use record_period_multiplier()
    which prefers the structured field.
    """
    if not metric_raw:
        return 1
    t = str(metric_raw).lower()
    if "weekly" in t or "per week" in t or "awus" in t or "aws " in t:
        return 52
    if "monthly" in t or "per month" in t:
        return 12
    if "daily" in t or "revpar" in t or "adr" in t or "per day" in t or "per night" in t:
        return 365
    return 1


def record_period_multiplier(record: dict) -> int:
    """Return annualization multiplier for an item19 record.

    Prefers structured `unit_period` field; falls back to metric_raw text inference
    for legacy records (extracted before 2026-05-18 schema update).
    """
    unit = record.get("unit_period")
    if unit and unit in _UNIT_TO_MULTIPLIER:
        return _UNIT_TO_MULTIPLIER[unit]
    return infer_period_multiplier(record.get("metric_raw"))


def is_unit_or_market_metric(record: dict) -> bool:
    """Return True if record should be EXCLUDED from breakeven / chart computations.

    Prefers structured `metric_scope` field; falls back to metric_raw regex
    inference for legacy records.
    """
    scope = record.get("metric_scope")
    if scope == "market-area" or scope == "ramp-snapshot":
        return True
    if scope == "franchisee":
        return False  # explicitly franchisee — don't apply legacy filter
    # Legacy inference (records without metric_scope).
    # Scan BOTH metric_raw and cohort_raw — non-annual signals can land in either
    # (e.g. "Gross Sales by Job Size" puts the signal in metric_raw; "Top 50%
    # by Average Job Size" puts it in cohort_raw).
    raw = ((record.get("metric_raw") or "") + " " + (record.get("cohort_raw") or "")).lower()
    if re.search(r"month\s*\d+", raw):
        return True
    if re.search(r"per\s+(capita|person|household|subterritory|territory|room|guest|night|day|job|ticket|transaction|sale|order|invoice|appointment)", raw):
        return True
    # "by Job Size" / "by Average Ticket Size" / "by Transaction Size" — per-unit
    # averages reported alongside per-outlet revenue. These collapse breakeven math
    # (inv / per-job value × margin = absurd years). House Doctors triggered this.
    # Deliberately excluding "per owner" / "per customer" — those are often
    # annual revenue per franchisee, not per-transaction.
    if re.search(r"\bby\s+(?:average\s+)?(?:job|ticket|transaction|sale|order|invoice|appointment)(?:\s+size)?\b", raw):
        return True
    if re.search(r"\b(revpar|adr|daily\s+rate|daily\s+room\s+rate)\b", raw):
        return True
    return False


def annualized_value(record: dict, value_key: str = "value_avg") -> float | None:
    """Return the annualized value for an item19 record. Uses unit_period if present."""
    v = record.get(value_key)
    if v is None:
        return None
    try:
        return float(v) * record_period_multiplier(record)
    except (TypeError, ValueError):
        return None


def compute_breakeven(industry: str | None, fees: dict | None, item19: list[dict]) -> dict | None:
    """Breakeven date range from existing data.

    Preference order (best evidence first):
      1. Reported net_profit dollar values     → use directly as annual profit
      2. Reported net_profit margin % + revenue → multiply
      3. Reported revenue × industry-typical net margin (rough estimate)

    Returns dict with low_years/high_years and `method` describing which path was used.
    None when neither investment range nor any revenue/profit data exists.
    """
    if not fees:
        return None
    inv_low = fees.get("total_investment_low") or 0
    inv_high = fees.get("total_investment_high") or 0
    if not (inv_low and inv_high):
        return None
    inv_mid = (inv_low + inv_high) / 2

    # Skip ramp-up snapshots, market-area metrics, and per-unit-time hotel metrics.
    # Uses the unified is_unit_or_market_metric() helper which prefers the
    # structured metric_scope field over metric_raw text inference.
    _is_ramp_snapshot = is_unit_or_market_metric

    # Collect candidate profit signals, annualizing weekly/monthly values.
    revenue_records = [
        {**r, "value_avg_annual": annualized_value(r)}
        for r in item19
        if r.get("metric_name") in ("gross_sales", "total_revenue")
        and r.get("value_avg")
        and not _is_ramp_snapshot(r)
    ]
    net_profit_records = [
        {**r, "value_avg_annual": annualized_value(r)}
        for r in item19
        if r.get("metric_name") == "net_profit"
        and r.get("value_avg") is not None
        and not _is_ramp_snapshot(r)
    ]

    method = None
    profits: list[float] = []
    notes: dict = {}

    # Path 1: net_profit reported as dollar values (value > 100 and probably not a %)
    dollar_profits = [r["value_avg_annual"] for r in net_profit_records
                      if r["value_avg_annual"] and abs(r["value_avg_annual"]) > 1000]
    if dollar_profits:
        profits = dollar_profits
        method = "reported_net_profit_dollars"
        notes["n_cohorts"] = len(dollar_profits)

    # Path 2: net_profit reported as margin percent (value between -100 and 100)
    elif net_profit_records and revenue_records:
        # NOTE: margin % is unit-less — don't annualize. Use raw value_avg.
        pct_margins = [r["value_avg"] / 100.0 for r in net_profit_records
                       if r["value_avg"] is not None and -100 < r["value_avg"] < 100]
        if pct_margins:
            avg_revs = [r["value_avg_annual"] for r in revenue_records]
            # Optimistic: max revenue × max margin. Conservative: min × min.
            profits = [max(avg_revs) * max(pct_margins), min(avg_revs) * min(pct_margins)]
            method = "reported_net_margin_pct"
            notes["n_cohorts"] = len(pct_margins)
            notes["margin_low_pct"] = round(min(pct_margins) * 100, 1)
            notes["margin_high_pct"] = round(max(pct_margins) * 100, 1)

    # Path 3: only revenue available → apply industry-typical margin band.
    # When the brand reports performance-anchored cohorts (Top 10%, Top 25%, etc.),
    # using max(revenue) inflates the optimistic case to absurdity. Prefer broad
    # cohorts; fall back to median of whatever's reported.
    if not profits and revenue_records:
        broad_revs = [r["value_avg_annual"] for r in revenue_records
                      if r.get("cohort_name") in (
                          "all_franchised", "all_company_owned",
                          "open_24_plus_mo", "open_36_plus_mo",
                          "open_48_plus_mo", "open_60_plus_mo")]
        if broad_revs:
            rev_use = broad_revs
        else:
            # Use the median cohort revenue instead of the extremes
            sorted_revs = sorted(r["value_avg_annual"] for r in revenue_records)
            n = len(sorted_revs)
            mid = sorted_revs[n // 2]
            # ±20% around the median for the band
            rev_use = [mid * 0.8, mid * 1.2]
        m_low, m_high = MARGIN_BANDS.get(industry or "", DEFAULT_MARGIN)
        profits = [max(rev_use) * m_high, min(rev_use) * m_low]
        method = "industry_typical_margin"
        notes["n_cohorts"] = len(revenue_records)
        notes["margin_low_pct"] = round(m_low * 100)
        notes["margin_high_pct"] = round(m_high * 100)
        notes["used_broad_cohorts"] = bool(broad_revs)

    if not profits:
        return None

    profit_opt = max(profits)
    profit_cons = min(profits)
    if profit_opt <= 0:
        return {"unprofitable": True, "method": method, "investment_midpoint": int(inv_mid),
                "industry_label": industry_label(industry), **notes}

    low_years = inv_mid / profit_opt
    high_years = inv_mid / profit_cons if profit_cons > 0 else None

    # Headline plausibility: if even the OPTIMISTIC case exceeds 50 years, the
    # underlying figures aren't reliable — likely a per-job or per-transaction
    # value leaked through the metric filter. Treat as "no breakeven estimate".
    if low_years > 50:
        return None

    return {
        "low_years": round(low_years, 1),
        "high_years": round(high_years, 1) if high_years and high_years < 50 else None,
        "investment_midpoint": int(inv_mid),
        "method": method,
        "industry_label": industry_label(industry),
        **notes,
    }


def compute_roi_walkforward(breakeven: dict | None, n_years: int = 10) -> dict | None:
    """F4.2: 10-year cumulative profit walk-forward from the breakeven scenario.

    Two scenarios: optimistic (uses high-end annual profit) and conservative (low-end).
    Both start at -investment_midpoint at year 0 and grow linearly. The optimistic line
    crosses zero at breakeven.low_years; the conservative at breakeven.high_years.

    Same compliance framing as the breakeven scenario itself — arithmetic walk on
    disclosed inputs, not a forecast.
    """
    if not breakeven or breakeven.get("unprofitable"):
        return None
    inv = breakeven.get("investment_midpoint")
    low_years = breakeven.get("low_years")
    high_years = breakeven.get("high_years") or low_years
    if not inv or not low_years:
        return None

    # annual_profit_high = inv / low_years (years to break = inv / profit)
    annual_profit_high = inv / low_years
    annual_profit_low = inv / high_years if high_years else annual_profit_high

    years = list(range(n_years + 1))
    optimistic = [round(y * annual_profit_high - inv, 0) for y in years]
    conservative = [round(y * annual_profit_low - inv, 0) for y in years]

    return {
        "years": years,
        "optimistic": optimistic,
        "conservative": conservative,
        "investment_midpoint": inv,
        "annual_profit_low": round(annual_profit_low, 0),
        "annual_profit_high": round(annual_profit_high, 0),
        "low_years": low_years,
        "high_years": high_years,
        "method": breakeven.get("method"),
    }


def compute_breakeven_chart_data(industry: str | None, fees: dict | None,
                                  item19: list[dict], breakeven: dict | None) -> dict | None:
    """Per-cohort breakeven range data for visualization.

    Returns chart dict with one entry per revenue cohort showing (low_years, high_years)
    range. Skipped when only one cohort exists or breakeven can't be computed.
    """
    if not breakeven or breakeven.get("unprofitable"):
        return None
    if not fees or not (fees.get("total_investment_low") and fees.get("total_investment_high")):
        return None
    inv_mid = (fees["total_investment_low"] + fees["total_investment_high"]) / 2

    # Find revenue cohorts (skip ramp-up snapshots and market-area metrics)
    # Uses the unified is_unit_or_market_metric() — prefers structured metric_scope
    rev_records = [r for r in item19
                   if r.get("metric_name") in ("gross_sales", "total_revenue")
                   and r.get("value_avg")
                   and not is_unit_or_market_metric(r)]
    if len(rev_records) < 2:
        return None  # single cohort = no histogram to show

    method = breakeven.get("method", "industry_typical_margin")

    # Margin band: prefer reported, fall back to industry-typical
    if method == "reported_net_margin_pct":
        m_low = breakeven.get("margin_low_pct", 10) / 100
        m_high = breakeven.get("margin_high_pct", 20) / 100
    elif method == "reported_net_profit_dollars":
        # Net profit reported directly — use a tight ±25% band around the reported value
        # to acknowledge variance even when the franchisor disclosed actual profit
        m_low = m_high = None  # different math below
    else:
        m_low, m_high = MARGIN_BANDS.get(industry or "", DEFAULT_MARGIN)

    # Disambiguate cohort labels with reporting_period when they repeat
    raw_cohorts_list = [(r.get("cohort_raw") or r.get("cohort_name") or "").strip() for r in rev_records]
    dup_cohorts = {c for c in raw_cohorts_list if raw_cohorts_list.count(c) > 1}

    cohorts: list[dict] = []
    for r in rev_records:
        cohort = (r.get("cohort_raw") or r.get("cohort_name") or "").strip()
        if cohort in dup_cohorts and r.get("reporting_period"):
            period_str = str(r["reporting_period"])
            m = re.search(r"\b(20\d{2})\b", period_str)
            if m: period_str = m.group(1)
            cohort = f"{cohort} ({period_str})"
        if len(cohort) > 70:
            cohort = cohort[:67] + "…"
        # Annualize weekly/monthly values before computing
        rev = r["value_avg"] * record_period_multiplier(r)
        if method == "reported_net_profit_dollars":
            # Use the cohort's matching net_profit if available; otherwise skip
            matching_nps = [n for n in item19
                            if n.get("metric_name") == "net_profit"
                            and n.get("cohort_raw") == r.get("cohort_raw")
                            and n.get("value_avg")]
            if not matching_nps:
                continue
            profit = matching_nps[0]["value_avg"] * record_period_multiplier(matching_nps[0])
            if profit <= 0:
                continue
            yrs = inv_mid / profit
            low_y, high_y = yrs * 0.85, yrs * 1.15  # ±15% band
            mid_y = yrs
        else:
            profit_hi = rev * m_high  # optimistic
            profit_lo = rev * m_low   # conservative
            if profit_lo <= 0 or profit_hi <= 0:
                continue
            low_y = inv_mid / profit_hi   # optimistic = fewer years
            high_y = inv_mid / profit_lo  # conservative = more years
            mid_y = (low_y + high_y) / 2
        # Defensive sanity check: skip any cohort that produces breakeven >50yr
        # at any end. A 50-year breakeven means the underlying value is per-job /
        # per-transaction / a top-1% outlier slipping past the metric-scope filter.
        # Empty bars and missing midpoints look like rendering bugs to readers; dropping
        # the row is cleaner than showing it broken.
        if low_y > 50 or high_y > 50 or mid_y > 50:
            continue
        cohorts.append({
            "cohort": cohort,
            "low_years": round(low_y, 1),
            "high_years": round(high_y, 1),
            "mid_years": round(mid_y, 1),
            "outlet_count": r.get("outlet_count"),
        })

    if len(cohorts) < 2:
        return None

    return {
        "cohorts": cohorts,
        "method": method,
        "industry_label": breakeven.get("industry_label", ""),
        "investment_midpoint": int(inv_mid),
    }


def source_url_for_record(source_url: str, page_number: int | None) -> str:
    """Append #page=N anchor for PDF deep-linking. Works for state portal URLs that
    serve PDFs directly. State-portal POSTback URLs won't anchor — falls back to plain URL."""
    if not page_number or not source_url:
        return source_url or ""
    if source_url.lower().endswith(".pdf") or "/download" in source_url.lower():
        sep = "&" if "?" in source_url else "#"
        # Many viewers respect #page=N; for portals doing dynamic-download this is best-effort
        return f"{source_url}#page={page_number}"
    return source_url


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def fetch_brand_summaries(conn: sqlite3.Connection) -> list[dict]:
    """Pull a row per franchisor with their latest FDD's key fees + has_item19."""
    rows = conn.execute("""
        SELECT
            f.id, f.legal_name, f.brand_name, f.slug, f.industry, f.state_of_inc,
            d.id AS fdd_id, d.filing_year, d.filing_state, d.has_item19,
            d.effective_date, d.source_url, d.retrieved_at,
            fi.initial_franchise_fee_low AS fee_low,
            fi.initial_franchise_fee_high AS fee_high,
            fi.royalty_pct,
            fi.marketing_fee_pct,
            fi.tech_fee_monthly,
            fi.liquid_capital_required,
            fi.total_investment_low AS inv_low,
            fi.total_investment_high AS inv_high
        FROM franchisors f
        JOIN fdds d ON d.franchisor_id = f.id
            AND d.id = (SELECT MAX(d2.id) FROM fdds d2 WHERE d2.franchisor_id = f.id)
        LEFT JOIN fees_and_investment fi ON fi.fdd_id = d.id
        ORDER BY f.brand_name COLLATE NOCASE
    """).fetchall()
    summaries = [dict(r) for r in rows]
    # Compute additional customer-perspective fields per brand
    from src import state_map as _sm
    for s in summaries:
        latest = conn.execute("""
            SELECT outlets_end FROM item20_locations
            WHERE fdd_id = ? AND state = 'TOTAL' AND outlet_type = 'total'
            ORDER BY year DESC LIMIT 1
        """, (s["fdd_id"],)).fetchone()
        s["total_outlets"] = latest[0] if latest else None
        # Closure rate from compute_risk_badge
        rb = compute_risk_badge(conn, s["fdd_id"])
        s["closure_rate_pct"] = rb["rate_pct"] if rb else None
        s["closure_tier"] = rb["tier"] if rb else None

        # Outlet growth: latest year vs prior year (TOTAL row)
        growth_rows = conn.execute("""
            SELECT year, outlets_end FROM item20_locations
            WHERE fdd_id = ? AND state = 'TOTAL' AND outlet_type = 'total'
              AND outlets_end IS NOT NULL
            ORDER BY year DESC LIMIT 2
        """, (s["fdd_id"],)).fetchall()
        if len(growth_rows) == 2 and growth_rows[1][1]:
            s["outlet_growth_pct"] = round((growth_rows[0][1] - growth_rows[1][1]) / growth_rows[1][1] * 100, 1)
        else:
            s["outlet_growth_pct"] = None

        # State count (US only) + top 3 states
        state_rows = conn.execute("""
            SELECT state, outlets_end FROM item20_locations
            WHERE fdd_id = ? AND state NOT IN ('TOTAL', '') AND outlet_type IS NULL
              AND year = (SELECT MAX(year) FROM item20_locations
                          WHERE fdd_id = ? AND state NOT IN ('TOTAL', '')
                            AND outlet_type IS NULL)
        """, (s["fdd_id"], s["fdd_id"])).fetchall()
        us_states = []
        for st_raw, n in state_rows:
            code = _sm.normalize_state_code(st_raw)
            if code and n and n > 0:
                us_states.append((code, n))
        us_states.sort(key=lambda x: -x[1])
        s["n_states"] = len(us_states)
        s["top_3_states"] = [c for c, _ in us_states[:3]]

        # Franchised vs company-owned mix (latest year)
        mix_rows = conn.execute("""
            SELECT outlet_type, outlets_end FROM item20_locations
            WHERE fdd_id = ? AND state = 'TOTAL'
              AND year = (SELECT MAX(year) FROM item20_locations
                          WHERE fdd_id = ? AND state = 'TOTAL')
        """, (s["fdd_id"], s["fdd_id"])).fetchall()
        franchised = company = total = None
        for ot, n in mix_rows:
            if ot == 'franchised': franchised = n
            elif ot in ('company-owned', 'company_owned'): company = n
            elif ot == 'total': total = n
        if franchised is not None and total:
            s["franchised_pct"] = round(franchised / total * 100, 0)
        elif franchised is not None and company is not None and (franchised + company) > 0:
            s["franchised_pct"] = round(franchised / (franchised + company) * 100, 0)
        else:
            s["franchised_pct"] = None

        # All-in royalty + marketing as combined %
        roy = s.get("royalty_pct") or 0
        mkt = s.get("marketing_fee_pct") or 0
        s["all_in_pct"] = round(roy + mkt, 1) if (roy or mkt) else None
    return summaries


def fetch_brand_detail(conn: sqlite3.Connection, slug: str) -> dict | None:
    brand_row = conn.execute("SELECT * FROM franchisors WHERE slug = ?", (slug,)).fetchone()
    if not brand_row:
        return None
    brand = dict(brand_row)

    fdd_row = conn.execute(
        "SELECT * FROM fdds WHERE franchisor_id = ? ORDER BY filing_year DESC, id DESC LIMIT 1",
        (brand["id"],),
    ).fetchone()
    if not fdd_row:
        return None
    fdd = dict(fdd_row)

    fees_row = conn.execute("SELECT * FROM fees_and_investment WHERE fdd_id = ?", (fdd["id"],)).fetchone()
    fees = dict(fees_row) if fees_row else None

    item19_rows = conn.execute(
        "SELECT * FROM item19_records WHERE fdd_id = ? ORDER BY id",
        (fdd["id"],),
    ).fetchall()
    item19 = [dict(r) for r in item19_rows]

    # Item 20 yearly summary (where state='TOTAL')
    yearly_rows = conn.execute(
        "SELECT year, outlet_type, outlets_start, outlets_end FROM item20_locations "
        "WHERE fdd_id = ? AND state = 'TOTAL' ORDER BY year, outlet_type",
        (fdd["id"],),
    ).fetchall()
    yearly = [dict(r) for r in yearly_rows]
    # Reshape into per-year rows with franchised/company_owned/total
    by_year: dict[int, dict] = {}
    for row in yearly:
        y = row["year"]
        by_year.setdefault(y, {"year": y, "franchised": None, "company_owned": None, "total": None})
        ot = (row["outlet_type"] or "").lower().replace("-", "_")
        if ot == "franchised":
            by_year[y]["franchised"] = row["outlets_end"]
        elif ot in ("company_owned", "company-owned", "companyowned"):
            by_year[y]["company_owned"] = row["outlets_end"]
        elif ot == "total":
            by_year[y]["total"] = row["outlets_end"]
    outlet_summary = sorted(by_year.values(), key=lambda r: r["year"]) if by_year else []

    # Total outlets in latest year + zero-inference for company-owned
    total_outlets = None
    if outlet_summary:
        for row in outlet_summary:
            # If we have franchised + total but no company-owned, the difference is co-owned (often 0)
            if row["franchised"] is not None and row["total"] is not None and row["company_owned"] is None:
                row["company_owned"] = max(0, row["total"] - row["franchised"])
            # If franchised + co-owned exist but no total, compute it
            if row["total"] is None and row["franchised"] is not None:
                row["total"] = (row["franchised"] or 0) + (row["company_owned"] or 0)
        latest = outlet_summary[-1]
        total_outlets = latest["total"] or (
            (latest["franchised"] or 0) + (latest["company_owned"] or 0)
        ) or None

    # Top-10 states by outlets (latest year)
    state_rows = conn.execute("""
        SELECT state, outlets_end
        FROM item20_locations
        WHERE fdd_id = ? AND state != 'TOTAL'
          AND year = (SELECT MAX(year) FROM item20_locations
                      WHERE fdd_id = ? AND state != 'TOTAL')
        ORDER BY outlets_end DESC
    """, (fdd["id"], fdd["id"])).fetchall()
    top_states = [{"state": r["state"], "outlets": r["outlets_end"] or 0}
                  for r in state_rows if r["outlets_end"]][:10]

    # Chart data
    outlet_chart_data = None
    if outlet_summary:
        outlet_chart_data = {
            "years": [str(y["year"]) for y in outlet_summary],
            "franchised": [y["franchised"] or 0 for y in outlet_summary],
            "company_owned": [y["company_owned"] or 0 for y in outlet_summary],
        }

    state_chart_data = None
    if top_states:
        state_chart_data = {
            "states": [s["state"] for s in top_states],
            "outlets": [s["outlets"] for s in top_states],
        }

    # Per-state heatmap: aggregate ALL state rows for the latest year (not just top 10).
    # Uses state_map.aggregate_by_state() to normalize "California" -> "CA" and drop
    # non-US (Canada, Australia, ALL STATES). Render only if >=3 US states with outlets.
    state_heatmap_svg = None
    state_heatmap_legend = None
    state_heatmap_stats = None
    all_state_rows = conn.execute("""
        SELECT state, outlets_end
        FROM item20_locations
        WHERE fdd_id = ? AND state NOT IN ('TOTAL', '')
          AND year = (SELECT MAX(year) FROM item20_locations
                      WHERE fdd_id = ? AND state NOT IN ('TOTAL', ''))
          AND outlet_type IS NULL
    """, (fdd["id"], fdd["id"])).fetchall()
    if all_state_rows:
        from src import state_map
        state_counts = state_map.aggregate_by_state([dict(r) for r in all_state_rows])
        covered = sum(1 for n in state_counts.values() if n > 0)
        if covered >= 3:
            state_heatmap_svg = state_map.render_state_heatmap_svg(
                state_counts, brand_name=brand.get("brand_name") or "")
            state_heatmap_legend = state_map.render_legend_svg(state_counts)
            top1 = max(state_counts.items(), key=lambda x: x[1])
            state_heatmap_stats = {
                "states_covered": covered,
                "total_outlets_mapped": sum(state_counts.values()),
                "top_state": top1[0],
                "top_state_outlets": top1[1],
                "top_state_name": state_map.US_STATE_NAMES.get(top1[0], top1[0]),
            }

    # Item 19 visualization: pick the top metric by record count and chart its cohorts.
    # Only currency metrics (gross_sales, total_revenue, gross_profit, net_profit) — % metrics
    # are mixed-scale and would dominate the axis.
    item19_chart_data = None
    # Suppress the multi-bar cohort chart when the underlying disclosure is
    # longitudinal_affiliate (one single-outlet cohort across years) — that
    # rendering reads as "5 different franchisees" when it's actually one
    # affiliate outlet over 5 years. Tier 1.1 fix per Phase 4 strategy.
    # affiliate_only is the same shape (single-outlet, multi-year) so also suppressed.
    _quality_for_chart = derived.item19_disclosure_quality(item19) if item19 else None
    _suppress_chart_kinds = {"longitudinal_affiliate", "affiliate_only"}
    if item19 and _quality_for_chart and _quality_for_chart.get("kind") in _suppress_chart_kinds:
        pass  # explicitly skip chart construction; warning banner already explains
    elif item19:
        from collections import Counter
        currency_metrics = {"gross_sales", "total_revenue", "gross_profit", "net_profit", "ebitda"}
        candidates = [r for r in item19
                      if r.get("metric_name") in currency_metrics
                      and r.get("value_avg") is not None
                      and not re.search(r"month\s*\d+", (r.get("metric_raw") or "").lower())]
        # Dedupe: when a brand reports BOTH "Average Monthly Sales" AND
        # "Average Annual Sales" for the same cohort+period, the monthly row
        # is just an annualization of the annual row — drop it.
        if candidates:
            seen_annual = {(c.get("cohort_raw"), c.get("reporting_period"), c.get("metric_name"))
                           for c in candidates if record_period_multiplier(c) == 1}
            candidates = [c for c in candidates
                          if record_period_multiplier(c) == 1
                          or (c.get("cohort_raw"), c.get("reporting_period"), c.get("metric_name")) not in seen_annual]
        if candidates:
            # Pick the metric with the most cohorts
            most_common_metric = Counter(r["metric_name"] for r in candidates).most_common(1)[0][0]
            recs = [r for r in candidates if r["metric_name"] == most_common_metric]
            # Skip chart if only 1 cohort — a single bar isn't informative
            if len(recs) >= 2:
                # Filter out market-area / ramp-snapshot / per-unit-time metrics.
                # Uses unified is_unit_or_market_metric() helper.
                recs = [r for r in recs if not is_unit_or_market_metric(r)]
            # Prefer franchised over affiliate: when BOTH cohort kinds are
            # present (Dumpster Dudez bug), exclude affiliate from the chart.
            # Affiliate cohorts (typically a single corporate flagship store)
            # aren't representative of franchisee performance — they get
            # mentioned in the warning callout instead.
            FRANCHISED_COHORT_NAMES = ("all_franchised", "open_24_plus_mo",
                "open_36_plus_mo", "open_48_plus_mo", "open_60_plus_mo",
                "open_lt_12mo", "open_12_24mo",
                "tenure_year_anchored", "ownership_group_anchored")
            has_franchised = any(r.get("cohort_name") in FRANCHISED_COHORT_NAMES for r in recs)
            if has_franchised:
                recs = [r for r in recs if r.get("cohort_name") != "all_company_owned"]
            if len(recs) >= 2:
                # If two distinct metric_raw variants exist (e.g. "per Franchisee" vs
                # "per Subterritory") that share cohorts, pick the dominant one.
                # BUT: when raws differ only by year suffix or by distribution bucket,
                # they're legitimately distinct dimensions — keep all.
                def _strip_year(s):
                    return re.sub(r"\b(20\d{2}|fy\s?20\d{2})\b", "", (s or "").lower()).strip()
                stripped = {_strip_year(r.get("metric_raw") or "") for r in recs}
                # Only filter when there are 2 distinct raws AND they collapse to ≤1 stripped form
                # (i.e. they're really variants of the same metric, not year-tagged versions).
                raw_set = {(r.get("metric_raw") or "") for r in recs}
                if len(raw_set) == 2 and len(stripped) >= 1:
                    from collections import Counter as _C
                    by_raw = _C((r.get("metric_raw") or "") for r in recs)
                    # Only dedupe if both variants have similar count (likely twin variants)
                    counts = [c for _, c in by_raw.most_common()]
                    if min(counts) / max(counts) > 0.7:
                        dom = by_raw.most_common(1)[0][0]
                        recs = [r for r in recs if (r.get("metric_raw") or "") == dom]
            if len(recs) >= 2:
                # Detect whether values need annualization (weekly/monthly metric_raw)
                multiplier = record_period_multiplier(recs[0])
                period_note = (
                    " (annualized — disclosed weekly)" if multiplier == 52 else
                    " (annualized — disclosed monthly)" if multiplier == 12 else
                    ""
                )
                # Disambiguate labels: when multiple records share the same cohort_raw,
                # append the reporting_period so each row is uniquely identified.
                raw_labels = [(r.get("cohort_raw") or r.get("cohort_name") or "") for r in recs]
                dup_cohorts = {c for c in raw_labels if raw_labels.count(c) > 1}

                # Compute a common prefix across labels — if every label shares the same
                # opening 30+ chars, we'll strip it so the distinguishing tail is visible.
                def _common_prefix(strs):
                    if not strs:
                        return ""
                    s0 = strs[0]
                    for i, c in enumerate(s0):
                        if any(i >= len(s) or s[i] != c for s in strs):
                            return s0[:i]
                    return s0
                cp = _common_prefix(raw_labels)
                # Only strip if the prefix is meaningful (>=30 chars) and leaves at
                # least 8 chars of distinguishing tail in every label.
                strip_prefix = len(cp) >= 30 and all(len(s) - len(cp) >= 8 for s in raw_labels)
                if strip_prefix:
                    # Trim back to last word boundary in the prefix to avoid mid-word cuts.
                    last_space = cp.rfind(" ")
                    if last_space > 10:
                        cp = cp[:last_space + 1]

                labels, lows, highs, ranges, medians, fmt_lo, fmt_hi, fmt_med = [], [], [], [], [], [], [], []
                for r, raw_label in zip(recs, raw_labels):
                    coh = raw_label
                    needs_period = raw_label in dup_cohorts and r.get("reporting_period")
                    if strip_prefix and coh.startswith(cp):
                        coh = "… " + coh[len(cp):]
                    if needs_period:
                        period_str = str(r["reporting_period"])
                        m = re.search(r"\b(20\d{2})\b", period_str)
                        if m: period_str = m.group(1)
                        coh = f"{coh} ({period_str})"
                    # Preserve date suffixes that often live at the end of long cohort
                    # descriptions. Bump truncation to 130 chars; CSS will wrap.
                    if len(coh) > 130: coh = coh[:127] + "…"
                    labels.append(coh)
                    lo = (r.get("value_min") or r.get("value_avg") or 0) * multiplier
                    hi = (r.get("value_max") or r.get("value_avg") or 0) * multiplier
                    med = (r.get("value_median") or r.get("value_avg") or 0) * multiplier
                    lows.append(lo); highs.append(hi)
                    ranges.append([lo, hi])
                    medians.append(med)
                    label_for_fmt = recs[0].get("metric_raw") or most_common_metric
                    fmt_lo.append(fmt_value(lo, label_for_fmt))
                    fmt_hi.append(fmt_value(hi, label_for_fmt))
                    fmt_med.append(fmt_value(med, label_for_fmt))
                metric_display = recs[0].get("metric_raw") or most_common_metric.replace("_", " ").title()
                if multiplier > 1:
                    metric_display += period_note
                item19_chart_data = {
                    "metric": metric_display,
                    "labels": labels,
                    "ranges": ranges,
                    "medians": medians,
                    "formatted_lows": fmt_lo,
                    "formatted_highs": fmt_hi,
                    "formatted_medians": fmt_med,
                    "unit_prefix": "$",
                }

    summary = build_summary_paragraph(
        brand=brand, latest_fdd=fdd, fees=fees,
        total_outlets=total_outlets, outlet_summary=outlet_summary,
        has_item19=bool(fdd.get("has_item19")),
    )
    industry_context = build_industry_context(conn, brand, fees, total_outlets)
    breakeven = compute_breakeven(brand.get("industry"), fees, item19)
    breakeven_chart = compute_breakeven_chart_data(brand.get("industry"), fees, item19, breakeven)
    roi_walkforward = compute_roi_walkforward(breakeven)
    faqs = build_faqs(
        brand=brand, latest_fdd=fdd, fees=fees, item19=item19,
        total_outlets=total_outlets, top_states=top_states,
        risk_badge=compute_risk_badge(conn, fdd["id"]),
        breakeven=breakeven,
    )

    # Inline outlet sparkline (F1.4) — small SVG path from per-year totals
    outlet_sparkline = None
    if outlet_summary and len(outlet_summary) >= 2:
        totals = [(y["year"], y["total"]) for y in outlet_summary if y["total"] is not None]
        if len(totals) >= 2:
            ys = [t[1] for t in totals]
            xs = [t[0] for t in totals]
            lo, hi = min(ys), max(ys)
            span = max(hi - lo, 1)
            W, H = 120, 24
            n = len(totals)
            # Map each (year, total) to (x, y) in SVG coords
            points = []
            for i, total in enumerate(ys):
                px = round(i / (n - 1) * (W - 2) + 1, 1)
                py = round(H - 2 - (total - lo) / span * (H - 4), 1)
                points.append((px, py))
            path_d = "M " + " L ".join(f"{x} {y}" for x, y in points)
            start, end = ys[0], ys[-1]
            pct_change = ((end - start) / start * 100) if start else 0
            direction = "up" if end > start else ("down" if end < start else "flat")
            outlet_sparkline = {
                "path_d": path_d,
                "width": W,
                "height": H,
                "start_year": xs[0],
                "end_year": xs[-1],
                "start_total": start,
                "end_total": end,
                "pct_change": round(pct_change, 1),
                "direction": direction,
            }

    # Page range for Item 19 records (used by data-vintage line under that section)
    pages = sorted({r.get("page_number") for r in item19 if r.get("page_number")})
    if not pages:
        item19_page_range = None
    elif len(pages) == 1:
        item19_page_range = str(pages[0])
    else:
        item19_page_range = f"{pages[0]}–{pages[-1]}"

    # Calculator defaults — delegated to src/derived.py so this file doesn't
    # duplicate filter / cohort-selection logic that other call sites
    # (breakeven, TL;DR median revenue, FAQ) also need. derived is imported
    # at module level (see top of file).
    cdr = derived.calc_default_revenue(item19, dict(fees) if fees else None,
                                        nice_round_fn=nice_round)
    calc_revenue_default = cdr["value"]
    calc_revenue_source = cdr["honest_label"]

    # Revenue distribution for quartile presets.
    # Use the FULL franchised distribution (or any-cohort fallback for brands
    # that only disclose performance-anchored). The cohort-kind label is
    # passed to the template so preset buttons can be labelled honestly.
    revenue_distribution = derived.franchised_revenue_distribution(item19)
    if not revenue_distribution:
        revenue_distribution = derived.any_revenue_distribution(item19)
    cohort_kind = derived.revenue_cohort_set_kind(item19)
    revenue_p25 = revenue_p50 = revenue_p75 = None
    if len(revenue_distribution) >= 3:
        # True percentiles (linear interpolation across the sorted list).
        def _pctile(arr, p):
            idx = max(0, min(len(arr) - 1, int(round((p / 100.0) * (len(arr) - 1)))))
            return nice_round(arr[idx])
        revenue_p25 = _pctile(revenue_distribution, 25)
        revenue_p50 = _pctile(revenue_distribution, 50)
        revenue_p75 = _pctile(revenue_distribution, 75)

    inv_mid = None
    if fees and fees.get("total_investment_low") and fees.get("total_investment_high"):
        inv_mid = nice_round((fees["total_investment_low"] + fees["total_investment_high"]) / 2)

    # Disclosure status + outlet breakdown — both used by templates instead of
    # the raw has_item19 flag / heatmap-gap math. See src/derived.py.
    disclosure = derived.disclosure_status(item19, fdd["has_item19"] if fdd else False)
    outlet_breakdown = derived.outlet_breakdown_from_item20(yearly)
    fees_ongoing_text = derived.ongoing_fees_text(dict(fees) if fees else None)
    item19_quality = derived.item19_disclosure_quality(item19)
    worst_performer = derived.worst_performer_callout(item19)
    item20_warning = derived.item20_disclosure_warning(outlet_summary)
    fdd_age = derived.fdd_age_badge(
        fdd.get("filing_year") if fdd else None,
        datetime.now().year)
    industry_medians = derived.industry_fee_medians(
        conn, brand.get("industry"), brand.get("id"))
    fee_benchmark = derived.fee_benchmark_callout(
        dict(fees) if fees else None, industry_medians,
        industry_label(brand.get("industry")))

    # Similar-brand calculator links: 4 brands in same industry, sorted by total_outlets desc
    similar_brand_calc_links = []
    if brand.get("industry"):
        sim_rows = conn.execute("""
            SELECT fr.slug, fr.brand_name, fr.legal_name
            FROM franchisors fr
            JOIN fdds d ON d.franchisor_id = fr.id
                AND d.id = (SELECT MAX(d2.id) FROM fdds d2 WHERE d2.franchisor_id = fr.id)
            LEFT JOIN item20_locations l ON l.fdd_id = d.id AND l.state = 'TOTAL' AND l.outlet_type = 'total'
            WHERE fr.industry = ? AND fr.id != ?
            GROUP BY fr.id
            ORDER BY MAX(COALESCE(l.outlets_end, 0)) DESC
            LIMIT 4
        """, (brand["industry"], brand["id"])).fetchall()
        similar_brand_calc_links = [
            {"slug": r["slug"], "name": r["brand_name"] or r["legal_name"]}
            for r in sim_rows
        ]

    # Investment low/high also rounded for display in the simplified tool.
    inv_low_rounded = nice_round((fees or {}).get("total_investment_low"))
    inv_high_rounded = nice_round((fees or {}).get("total_investment_high"))

    calculator_defaults = {
        "revenue": calc_revenue_default,
        "revenue_source": calc_revenue_source,
        "revenue_p25": revenue_p25,
        "revenue_p50": revenue_p50,
        "revenue_p75": revenue_p75,
        "investment": inv_mid,
        "investment_low": inv_low_rounded,
        "investment_high": inv_high_rounded,
        "royalty": (fees or {}).get("royalty_pct"),
        "marketing": (fees or {}).get("marketing_fee_pct"),
        "tech_fee_monthly": (fees or {}).get("tech_fee_monthly"),
        "op_cost_pct": int(round(op_cost_pct_for(brand.get("industry")) * 100)),
        "industry_label": industry_label(brand.get("industry")),
        "similar_brand_links": similar_brand_calc_links,
        "brand_name": brand.get("brand_name") or brand.get("legal_name"),
        "brand_slug": brand.get("slug"),
        "filing_year": fdd.get("filing_year") if fdd else None,
        "n_item19_records": len(revenue_distribution),
        # Derived fields (one source of truth, used by template):
        "cohort_kind": cohort_kind,       # 'natural' or 'performance_anchored'
        "ongoing_fees_text": fees_ongoing_text,
        "disclosure_kind": disclosure["kind"],   # 'formal'|'supplemental'|'none'
        "disclosure_label": disclosure["label"],
        "outlet_breakdown": outlet_breakdown,    # franchised vs co-owned for gap caption
    }
    import json as _j
    calculator_defaults_json = _j.dumps(calculator_defaults)

    return {
        "brand": brand,
        "latest_fdd": fdd,
        "fees": fees,
        "item19_records": item19,
        "item19_page_range": item19_page_range,
        "outlet_summary": outlet_summary,
        "total_outlets": total_outlets,
        "top_states": top_states,
        "calculator_defaults": calculator_defaults,
        "calculator_defaults_json": calculator_defaults_json,
        "disclosure": disclosure,
        "outlet_breakdown": outlet_breakdown,
        "ongoing_fees_text": fees_ongoing_text,
        "item19_quality": item19_quality,
        "worst_performer": worst_performer,
        "fee_benchmark": fee_benchmark,
        "item20_warning": item20_warning,
        "fdd_age": fdd_age,
        "risk_badge": compute_risk_badge(conn, fdd["id"]),
        "breakeven": breakeven,
        "breakeven_chart": breakeven_chart,
        "roi_walkforward": roi_walkforward,
        "outlet_chart_data": outlet_chart_data,
        "state_chart_data": state_chart_data,
        "state_heatmap_svg": state_heatmap_svg,
        "state_heatmap_legend": state_heatmap_legend,
        "state_heatmap_stats": state_heatmap_stats,
        "item19_chart_data": item19_chart_data,
        "outlet_sparkline": outlet_sparkline,
        "summary": summary,
        "industry_context": industry_context,
        "faqs": faqs,
        "reading_time_min": _estimate_brand_page_reading_time(
            summary=summary, item19=item19, outlet_summary=outlet_summary,
            top_states=top_states, breakeven=breakeven, faqs=faqs,
        ),
    }


def _estimate_brand_page_reading_time(*, summary, item19, outlet_summary,
                                       top_states, breakeven, faqs) -> int:
    """Approximate reading time in minutes (rounded up to integer).

    Rough word counts per section (based on typical rendered content) divided
    by 220 wpm. Heuristic — not exact — but better than a static number.
    """
    words = 200  # base: header + TL;DR + tagline + closing CTA copy
    if summary and summary.get("word_count"):
        words += int(summary["word_count"])
    if breakeven and not breakeven.get("unprofitable"):
        words += 250
    words += 350  # calculator section (UI labels + disclaimer)
    if item19:
        words += 60 + len(item19) * 10  # table header + per-row scan time
    if outlet_summary:
        words += 80 + len(outlet_summary) * 8
    if top_states:
        words += 50
    if faqs:
        words += sum(len((f.get("answer_html") or "").split()) + 6 for f in faqs)
    return max(1, round(words / 220))


def build_faqs(brand: dict, latest_fdd: dict, fees: dict | None, item19: list[dict],
                total_outlets: int | None, top_states: list[dict], risk_badge: dict | None,
                breakeven: dict | None) -> list[dict]:
    """Build 5-7 FAQ entries per brand. Each is a {question, answer_html, answer_text}.
    Answers in 2-4 sentences of prose (no bullets — AI prefers prose).
    Skips questions where we have no honest answer.
    """
    bn = brand.get("brand_name") or brand.get("legal_name") or "this franchise"
    fy = latest_fdd.get("filing_year") or "the latest"
    out: list[dict] = []

    # 1. How much does X franchise cost?
    if fees and (fees.get("total_investment_low") or fees.get("initial_franchise_fee_low")):
        inv_lo, inv_hi = fees.get("total_investment_low"), fees.get("total_investment_high")
        fee_lo, fee_hi = fees.get("initial_franchise_fee_low"), fees.get("initial_franchise_fee_high")
        ans_parts = []
        if inv_lo and inv_hi:
            ans_parts.append(f"Based on the {fy} Franchise Disclosure Document, the estimated total initial investment for a {bn} franchise ranges from <strong>${inv_lo:,.0f} to ${inv_hi:,.0f}</strong>.")
        if fee_lo and fee_hi and fee_lo != fee_hi:
            ans_parts.append(f"The initial franchise fee alone is <strong>${fee_lo:,.0f}–${fee_hi:,.0f}</strong>, with the balance covering real estate, equipment, training, working capital, and other line items in Item 7 of the FDD.")
        elif fee_lo or fee_hi:
            ans_parts.append(f"The initial franchise fee alone is <strong>${(fee_lo or fee_hi):,.0f}</strong>, with the balance covering real estate, equipment, training, working capital, and other line items in Item 7 of the FDD.")
        ans_parts.append("Actual costs vary by location, build-out scope, and local market conditions.")
        out.append({
            "question": f"How much does a {bn} franchise cost?",
            "answer_html": " ".join(ans_parts),
        })

    # 2. How much do X franchises make?
    if latest_fdd.get("has_item19") and item19:
        # Find the most prominent revenue metric
        rev_records = [r for r in item19 if r.get("metric_name") in ("gross_sales", "total_revenue") and r.get("value_avg")]
        if rev_records:
            broad = next((r for r in rev_records if r.get("cohort_name") in ("all_franchised", "all_company_owned")), None)
            ref = broad or rev_records[0]
            avg = ref.get("value_avg")
            cohort_text = ref.get("cohort_raw") or "the reported franchised cohort"
            ans = (
                f"In the {fy} FDD, {bn} disclosed average reported revenue of <strong>${avg:,.0f}</strong> for {cohort_text}. "
                f"Item 19 includes additional cohorts and metrics — see the financial performance table above for the full distribution including median, low, and high values."
                f" These are historical figures for outlets the franchisor selected for disclosure; results vary by location and operator."
            )
            out.append({"question": f"How much do {bn} franchises make?", "answer_html": ans})
        else:
            out.append({
                "question": f"How much do {bn} franchises make?",
                "answer_html": (f"{bn} discloses some financial performance data in Item 19 of the {fy} FDD, but it doesn't fit a single headline revenue figure. "
                                f"See the Item 19 table on this page for the full disclosure, and validate with current franchisees listed in Item 20.")
            })
    else:
        out.append({
            "question": f"How much do {bn} franchises make?",
            "answer_html": (f"{bn} <strong>does not publicly disclose</strong> outlet-level earnings data in Item 19 of the {fy} FDD. "
                            f"Prospective buyers should request validation calls with current franchisees (listed in Item 20 of the FDD) to discuss typical revenue and margins.")
        })

    # 3. What is the royalty fee?
    if fees and fees.get("royalty_pct"):
        royalty = fees["royalty_pct"]
        mkt = fees.get("marketing_fee_pct")
        ans = f"The royalty fee for {bn} is <strong>{royalty}% of gross sales</strong>, payable to the franchisor on an ongoing basis."
        if mkt:
            ans += f" An additional <strong>{mkt}%</strong> marketing/brand-fund fee also applies."
        ans += f" These rates are stated in Item 6 of the {fy} FDD and are subject to change at the franchisor's discretion."
        out.append({"question": f"What is the royalty fee for {bn}?", "answer_html": ans})

    # 4. How many locations are there?
    if total_outlets:
        states_count = len(top_states) if top_states else None
        ans = f"As of the latest filing year, {bn} reported <strong>{total_outlets:,} outlets</strong> system-wide."
        if states_count:
            top_state = top_states[0]
            ans += f" The largest concentration is in {top_state['state']} ({top_state['outlets']:,} outlets); the brand operates across {states_count}+ states."
        ans += " See the outlet growth chart on this page for year-over-year change."
        out.append({"question": f"How many {bn} locations are there?", "answer_html": ans})

    # 5. How long until breakeven? (FTC §436.5(s) compliant — scenario language)
    if breakeven and not breakeven.get("unprofitable") and breakeven.get("low_years"):
        lo = breakeven["low_years"]
        hi = breakeven.get("high_years")
        method = breakeven.get("method", "industry_typical_margin")
        if method == "reported_net_profit_dollars":
            basis = "the franchisor's directly-reported net profit values"
        elif method == "reported_net_margin_pct":
            basis = "the franchisor's reported net income margin"
        else:
            basis = f"industry-typical operating margins of {breakeven.get('margin_low_pct', '?')}–{breakeven.get('margin_high_pct', '?')}%"
        range_str = f"{lo}–{hi} years" if hi else f"~{lo} years"
        ans = (
            f"Under a scenario combining the investment midpoint disclosed in this FDD with {basis}, "
            f"<strong>breakeven would occur in roughly {range_str}</strong>. "
            f"This is an arithmetic estimate, not a projection or guarantee — actual outcomes depend on location, owner involvement, financing terms, local market conditions, and operating discipline. "
            f"The FDD's Item 19 disclosures (above) and direct franchisee conversations are the authoritative inputs for any real estimate."
        )
        out.append({"question": f"How long until breakeven for {bn}?", "answer_html": ans})

    # 6. Where can I open one?
    if top_states:
        states_list = ", ".join(s["state"] for s in top_states[:5])
        ans = (
            f"Per the latest FDD, {bn} currently operates outlets in multiple states with the largest concentrations in <strong>{states_list}</strong>. "
            f"Open territory availability depends on the franchisor's then-current development plans — contact the franchisor directly via the website or franchise development team listed in Item 1 of the source FDD for specific territory availability."
        )
        out.append({"question": f"Where can I open a {bn} franchise?", "answer_html": ans})

    # 7. Is the system stable? (uses risk badge data)
    if risk_badge:
        tier = risk_badge["tier"]
        rate = risk_badge["rate_pct"]
        closures = risk_badge["closures"]
        starts = risk_badge["starts"]
        if tier == "green":
            health = "stable"
            extra = "indicating consistent system health."
        elif tier == "yellow":
            health = "mixed"
            extra = "worth examining year-over-year for individual franchisee outcomes."
        else:
            health = "elevated"
            extra = "buyers should investigate the underlying drivers carefully with current and former franchisees."
        ans = (
            f"Based on Item 20 of the {fy} FDD, {bn} reported a closure rate of <strong>{rate}%</strong> "
            f"({closures} closures across {starts:,} outlet-years over the reporting period) — a {health} signal {extra} "
            f"Note that closure rate alone doesn't capture profitability or owner satisfaction; review Item 20 in full and contact franchisees directly."
        )
        out.append({"question": f"Is {bn} a stable franchise system?", "answer_html": ans})

    # ----- Fallbacks — only used to backfill sparse brands to 5-FAQ minimum -----
    fallbacks: list[dict] = []
    industry = industry_label(brand.get("industry"))
    if industry and industry != "Other":
        ind_lower = industry.lower()
        fallbacks.append({
            "question": f"What kind of franchise is {bn}?",
            "answer_html": (
                f"{bn} is classified as a <strong>{ind_lower}</strong> franchise based on its registered business activities. "
                f"This category covers brands operating in similar service or product areas — see the {ind_lower} category page for direct comparisons with other brands in the same segment."
            ),
        })
    fs = latest_fdd.get("filing_state") or "a registration state"
    iss = latest_fdd.get("effective_date")
    iss_text = f" with an issuance date of {iss}" if iss else ""
    fallbacks.append({
        "question": f"How recent is the data shown for {bn}?",
        "answer_html": (
            f"All data on this page is extracted from {bn}'s {fy} Franchise Disclosure Document filed in {fs}{iss_text}. "
            f"Franchisors must file an updated FDD annually if they continue offering franchises in a registration state, so this represents the most recent publicly-filed disclosure available at extraction time. "
            f"Always cross-reference against the source filing for material decisions."
        ),
    })
    src_url = latest_fdd.get("source_url")
    if src_url:
        fallbacks.append({
            "question": f"Where can I read the source {bn} FDD?",
            "answer_html": (
                f"The {fy} {bn} FDD is publicly filed and accessible via the {fs} state registration portal — "
                f"<a href=\"{src_url}\" rel=\"nofollow\">view the source filing here</a>. "
                f"State portals are the authoritative source; if any number on this page disagrees with the source PDF, trust the source."
            ),
        })

    # Backfill to 5 minimum; cap total at 7
    while len(out) < 5 and fallbacks:
        out.append(fallbacks.pop(0))
    return out[:7]


def build_industry_context(conn: sqlite3.Connection, brand: dict, fees: dict | None,
                            total_outlets: int | None) -> str:
    """2-3 sentence paragraph placing the brand in its industry context.

    Pure data-derived. No editorial superlatives. Names same-industry siblings
    when present and compares headline numbers (investment, outlets) within the cohort.
    """
    industry = brand.get("industry")
    if not industry:
        return ""
    label = industry_label(industry).lower()
    bn = brand.get("brand_name") or brand.get("legal_name") or "this brand"

    # Pull other same-industry brands' headline numbers
    siblings = conn.execute("""
        SELECT f.brand_name, f.legal_name, f.slug,
               fi.total_investment_low AS inv_low,
               fi.total_investment_high AS inv_high,
               (SELECT MAX(l.outlets_end) FROM item20_locations l
                JOIN fdds d2 ON d2.id = l.fdd_id
                WHERE d2.franchisor_id = f.id AND l.state = 'TOTAL'
                  AND l.outlet_type = 'total') AS outlets
        FROM franchisors f
        JOIN fdds d ON d.franchisor_id = f.id
            AND d.id = (SELECT MAX(d2.id) FROM fdds d2 WHERE d2.franchisor_id = f.id)
        LEFT JOIN fees_and_investment fi ON fi.fdd_id = d.id
        WHERE f.industry = ? AND f.id != ?
        ORDER BY f.brand_name COLLATE NOCASE
    """, (industry, brand.get("id"))).fetchall()
    siblings_list = [dict(r) for r in siblings]

    # Cohort stats
    n_in_cat = len(siblings_list) + 1
    if n_in_cat == 1:
        # Only brand in its industry
        category_size_phrase = (f"{bn} is the only {label} franchise currently in our database — "
                                f"as we extract more state filings, additional comparables will appear.")
    else:
        category_size_phrase = f"It sits alongside {n_in_cat - 1} other {label} franchise{'s' if n_in_cat > 2 else ''} in our database"
        # Compare investment
        inv_self = ((fees or {}).get("total_investment_low") or 0) + ((fees or {}).get("total_investment_high") or 0)
        inv_self = inv_self / 2 if inv_self else 0
        sibling_invs = [(s["inv_low"] or 0 + s["inv_high"] or 0) / 2 for s in siblings_list if s.get("inv_low")]
        if inv_self and sibling_invs:
            median_sib = sorted(sibling_invs)[len(sibling_invs) // 2]
            if inv_self < median_sib * 0.7:
                category_size_phrase += " with a lower-than-typical investment requirement"
            elif inv_self > median_sib * 1.3:
                category_size_phrase += " with a higher-than-typical investment requirement"
            else:
                category_size_phrase += " with an investment requirement in line with category peers"
        category_size_phrase += "."

    # Name 1-2 comparables (alphabetical, deterministic)
    comparable_phrase = ""
    if siblings_list:
        names = [(s["brand_name"] or s["legal_name"]) for s in siblings_list[:2]]
        comparable_phrase = f" Other {label} franchises tracked here include {' and '.join(names)}."

    # Outlets context
    outlets_phrase = ""
    if total_outlets and siblings_list:
        sibling_outlets = [s["outlets"] for s in siblings_list if s.get("outlets")]
        if sibling_outlets:
            median_outlets = sorted(sibling_outlets)[len(sibling_outlets) // 2]
            if total_outlets > median_outlets * 2:
                outlets_phrase = f" By outlet count ({total_outlets:,}), {bn} is one of the larger operators in this category."
            elif total_outlets < median_outlets * 0.5:
                outlets_phrase = f" With {total_outlets:,} outlets, {bn} is on the smaller side of this category."

    return category_size_phrase + comparable_phrase + outlets_phrase


def build_compare_faqs(a: dict, b: dict) -> list[dict]:
    """F5.2: 5-6 data-driven FAQs comparing two brands. Each FAQ is {question, answer_html}.
    Only asks questions we can honestly answer from the data."""
    a_name = a["brand"]["brand_name"] or a["brand"]["legal_name"]
    b_name = b["brand"]["brand_name"] or b["brand"]["legal_name"]
    a_fees = a.get("fees") or {}
    b_fees = b.get("fees") or {}
    out: list[dict] = []

    # Q1: Initial fee comparison
    a_fee = a_fees.get("initial_franchise_fee_low") or a_fees.get("initial_franchise_fee_high")
    b_fee = b_fees.get("initial_franchise_fee_low") or b_fees.get("initial_franchise_fee_high")
    if a_fee and b_fee:
        cheaper, costlier = (a_name, b_name) if a_fee < b_fee else (b_name, a_name)
        delta = abs(a_fee - b_fee)
        out.append({
            "question": f"Is {a_name} cheaper than {b_name} to start?",
            "answer_html": (
                f"Based on the initial franchise fee disclosed in each franchisor's most recent FDD, "
                f"<strong>{cheaper}</strong> has the lower starting fee — about <strong>${delta:,.0f}</strong> less than {costlier}. "
                f"This compares only the franchise fee itself, not the total investment range (which includes build-out, equipment, working capital, and other line items). "
                f"See the comparison table above for both totals."
            ),
        })

    # Q2: Investment range
    a_inv_low = a_fees.get("total_investment_low")
    a_inv_high = a_fees.get("total_investment_high")
    b_inv_low = b_fees.get("total_investment_low")
    b_inv_high = b_fees.get("total_investment_high")
    if a_inv_low and a_inv_high and b_inv_low and b_inv_high:
        a_mid = (a_inv_low + a_inv_high) / 2
        b_mid = (b_inv_low + b_inv_high) / 2
        lower, higher = (a_name, b_name) if a_mid < b_mid else (b_name, a_name)
        out.append({
            "question": f"Which has the lower total investment, {a_name} or {b_name}?",
            "answer_html": (
                f"The franchisor-disclosed total investment range is "
                f"<strong>${a_inv_low:,.0f}–${a_inv_high:,.0f}</strong> for {a_name} and "
                f"<strong>${b_inv_low:,.0f}–${b_inv_high:,.0f}</strong> for {b_name}. "
                f"By midpoint, <strong>{lower}</strong> has the lower investment requirement. "
                f"Your actual cost depends on location, build-out specifics, and whether you self-finance — see each brand's full Item 7 disclosure for the line-item breakdown."
            ),
        })

    # Q3: Royalty
    a_r = a_fees.get("royalty_pct")
    b_r = b_fees.get("royalty_pct")
    if a_r is not None and b_r is not None:
        if a_r == b_r:
            txt = f"Both charge a <strong>{a_r}%</strong> royalty on gross sales — identical."
        else:
            lower_pct, higher_pct = (a_name, b_name) if a_r < b_r else (b_name, a_name)
            txt = (f"<strong>{a_name}</strong> charges <strong>{a_r}%</strong> and "
                   f"<strong>{b_name}</strong> charges <strong>{b_r}%</strong> of gross sales. "
                   f"<strong>{lower_pct}</strong> has the lower royalty rate. "
                   f"Royalty differences compound: 1 percentage point on $500k gross sales = $5,000 per year.")
        out.append({"question": f"What royalty does {a_name} vs {b_name} charge?", "answer_html": txt})

    # Q4: Outlet counts
    a_out = a.get("total_outlets")
    b_out = b.get("total_outlets")
    if a_out and b_out:
        bigger = a_name if a_out > b_out else b_name
        out.append({
            "question": f"Which has more locations, {a_name} or {b_name}?",
            "answer_html": (
                f"As of the latest reporting year, <strong>{a_name}</strong> reported "
                f"<strong>{a_out:,}</strong> outlets and <strong>{b_name}</strong> reported "
                f"<strong>{b_out:,}</strong>. <strong>{bigger}</strong> is the larger system. "
                f"Bigger isn't automatically better — it can mean more brand recognition but also "
                f"a more saturated territory map. Check each brand's outlet-growth chart for the trend over time."
            ),
        })

    # Q5: Item 19 disclosure asymmetry
    a_i19 = a["latest_fdd"].get("has_item19")
    b_i19 = b["latest_fdd"].get("has_item19")
    if a_i19 != b_i19:
        discloser = a_name if a_i19 else b_name
        non = b_name if a_i19 else a_name
        out.append({
            "question": f"Does {a_name} or {b_name} disclose Item 19 financial performance?",
            "answer_html": (
                f"<strong>{discloser}</strong> includes an Item 19 Financial Performance Representation "
                f"in its most recent FDD; <strong>{non}</strong> does not. "
                f"Item 19 disclosure is voluntary but expected of credible franchisors — its absence "
                f"means you'll need to rely entirely on validation calls with current franchisees "
                f"(listed in Item 20 of the FDD) to gauge earnings."
            ),
        })
    elif a_i19 and b_i19:
        out.append({
            "question": f"Do both {a_name} and {b_name} disclose Item 19 earnings?",
            "answer_html": (
                f"Yes — both franchisors include Item 19 Financial Performance Representations "
                f"in their most recent FDDs. {a_name} reports {len(a.get('item19_records', []))} "
                f"cohort × metric records; {b_name} reports {len(b.get('item19_records', []))}. "
                f"See each brand's Item 19 table for the full breakdown."
            ),
        })

    # Q6: Source year asymmetry / freshness
    a_y = a["latest_fdd"].get("filing_year")
    b_y = b["latest_fdd"].get("filing_year")
    if a_y and b_y and a_y != b_y:
        newer = a_name if a_y > b_y else b_name
        out.append({
            "question": f"Which comparison data is more current?",
            "answer_html": (
                f"<strong>{a_name}</strong>'s data is from the <strong>{a_y}</strong> FDD; "
                f"<strong>{b_name}</strong>'s is from the <strong>{b_y}</strong> FDD. "
                f"<strong>{newer}</strong>'s figures reflect more recent operations. "
                f"Franchisors file annually, so the year gap will close on the next refresh."
            ),
        })

    return out[:6]


def fetch_compare_with(conn: sqlite3.Connection, brand_id: int, brand_slug: str,
                        industry: str | None, limit: int = 4) -> list[dict]:
    """Same-category peers for the brand-page "Compare head-to-head" list.

    Returns up to `limit` peers ordered by outlet count desc (biggest brands
    first — those are the high-intent comparisons). Each peer has:
      - peer_slug: for ?brands= deeplink
      - pair_slug: static compare URL (alphabetized) IF both qualify, else None
      - has_static_page: bool — template uses to pick static vs interactive URL

    Static-page eligibility matches the capped generator: both brands need
    item19 disclosed AND >=100 total outlets.
    """
    if not industry:
        return []

    COMPARE_MIN_OUTLETS = 100

    # Self-eligibility for the static page
    self_row = conn.execute("""
        SELECT
            COALESCE(MAX(CASE WHEN i20.outlet_type='total' THEN i20.outlets_end END), 0) AS total_outlets,
            (SELECT COUNT(*) FROM item19_records WHERE fdd_id=d.id) AS n_item19
        FROM franchisors fr
        JOIN fdds d ON d.id = (SELECT MAX(d2.id) FROM fdds d2 WHERE d2.franchisor_id = fr.id)
        LEFT JOIN item20_locations i20 ON i20.fdd_id = d.id
        WHERE fr.id = ?
    """, (brand_id,)).fetchone()
    self_eligible = bool(self_row and self_row["n_item19"] > 0 and (self_row["total_outlets"] or 0) >= COMPARE_MIN_OUTLETS)

    rows = conn.execute("""
        SELECT
            f.brand_name, f.legal_name, f.slug,
            COALESCE(MAX(CASE WHEN i20.outlet_type='total' THEN i20.outlets_end END), 0) AS total_outlets,
            (SELECT COUNT(*) FROM item19_records WHERE fdd_id=d.id) AS n_item19
        FROM franchisors f
        JOIN fdds d ON d.id = (SELECT MAX(d2.id) FROM fdds d2 WHERE d2.franchisor_id = f.id)
        LEFT JOIN item20_locations i20 ON i20.fdd_id = d.id
        WHERE f.industry = ? AND f.id != ?
        GROUP BY f.id
        ORDER BY total_outlets DESC, f.brand_name COLLATE NOCASE
        LIMIT ?
    """, (industry, brand_id, limit)).fetchall()
    out = []
    for r in rows:
        peer_eligible = r["n_item19"] > 0 and (r["total_outlets"] or 0) >= COMPARE_MIN_OUTLETS
        has_static = self_eligible and peer_eligible
        a, b = sorted([brand_slug, r["slug"]])
        out.append({
            "brand_name": r["brand_name"] or r["legal_name"],
            "peer_slug": r["slug"],
            "pair_slug": f"{a}-vs-{b}" if has_static else None,
            "has_static_page": has_static,
        })
    return out


def fetch_highest_reported_earnings(conn: sqlite3.Connection, industry: str) -> list[dict]:
    """For each brand in the category that discloses Item 19, pick the most representative
    headline revenue figure (prefer broad-cohort + median + gross_sales/total_revenue).
    Returns a list ranked highest-first.

    Picker preference (most → least preferred):
      1. Broad cohort (all_franchised, all_company_owned, open_X_plus_mo) — most representative
      2. Tenure-anchored cohort (tenure_year_anchored)
      3. Performance-anchored cohort (Top 25% etc.) — least representative; clearly labeled
    Within the chosen cohort, prefer:
      gross_sales median → gross_sales avg → total_revenue median → total_revenue avg

    Compliance framing: we rank by what each franchisor REPORTED. Not editorial.
    Cohort label is always shown so readers know what's being compared.
    """
    BROAD_COHORTS = (
        "all_franchised", "all_company_owned",
        "open_lt_12mo", "open_12_24mo", "open_24_plus_mo",
        "open_36_plus_mo", "open_48_plus_mo", "open_60_plus_mo",
    )
    TENURE_COHORTS = ("tenure_year_anchored",)
    PERF_COHORTS = ("performance_anchored",)
    REVENUE_METRICS = ("gross_sales", "total_revenue")

    rows = conn.execute("""
        SELECT f.id AS brand_id, f.brand_name, f.legal_name, f.slug,
               d.id AS fdd_id, d.filing_year, d.filing_state, d.source_url,
               r.metric_name, r.metric_raw, r.cohort_name, r.cohort_raw,
               r.outlet_count, r.reporting_period,
               r.value_median, r.value_avg, r.value_min, r.value_max, r.page_number
        FROM franchisors f
        JOIN fdds d ON d.franchisor_id = f.id
            AND d.id = (SELECT MAX(d2.id) FROM fdds d2 WHERE d2.franchisor_id = f.id)
        JOIN item19_records r ON r.fdd_id = d.id
        WHERE f.industry = ? AND r.metric_name IN ('gross_sales', 'total_revenue')
              AND (r.value_median IS NOT NULL OR r.value_avg IS NOT NULL)
    """, (industry,)).fetchall()

    # Group by brand
    by_brand: dict[int, list[dict]] = {}
    for r in rows:
        by_brand.setdefault(r["brand_id"], []).append(dict(r))

    def score_record(r: dict) -> tuple:
        """Lower tuple = better candidate."""
        c = r.get("cohort_name") or "other"
        if c in BROAD_COHORTS: tier = 0
        elif c in TENURE_COHORTS: tier = 1
        elif c in PERF_COHORTS: tier = 2
        else: tier = 3
        # Prefer all_franchised specifically over other broad cohorts
        cohort_subrank = 0 if c == "all_franchised" else 1
        # Prefer gross_sales over total_revenue
        metric_rank = 0 if r["metric_name"] == "gross_sales" else 1
        # Prefer median over avg (we'll use whichever is non-null)
        has_median = 0 if r.get("value_median") is not None else 1
        return (tier, cohort_subrank, metric_rank, has_median)

    picked: list[dict] = []
    for brand_id, recs in by_brand.items():
        if not recs:
            continue
        recs.sort(key=score_record)
        best = recs[0]
        value = best.get("value_median") or best.get("value_avg")
        if value is None:
            continue
        is_median = best.get("value_median") is not None
        picked.append({
            "brand_id": brand_id,
            "brand_name": best["brand_name"],
            "legal_name": best["legal_name"],
            "slug": best["slug"],
            "filing_year": best["filing_year"],
            "filing_state": best["filing_state"],
            "source_url": best["source_url"],
            "page_number": best.get("page_number"),
            "metric_raw": best.get("metric_raw") or best["metric_name"].replace("_", " ").title(),
            "cohort_raw": best.get("cohort_raw") or best.get("cohort_name") or "—",
            "cohort_name": best.get("cohort_name") or "",
            "outlet_count": best.get("outlet_count"),
            "reporting_period": best.get("reporting_period"),
            "value": float(value),
            "is_median": is_median,
            "value_label": "Median" if is_median else "Average",
        })

    picked.sort(key=lambda x: x["value"], reverse=True)
    return picked


def fetch_similar_cheaper(conn: sqlite3.Connection, brand_id: int, industry: str | None,
                           current_inv_low: int | None, limit: int = 3) -> list[dict]:
    """F5.3: same-category brands with lower total-investment-low than this brand.
    Returns empty list if no current investment data, or no cheaper peers exist."""
    if not industry or not current_inv_low:
        return []
    rows = conn.execute("""
        SELECT f.brand_name, f.legal_name, f.slug, f.industry,
               d.filing_year,
               fi.initial_franchise_fee_low AS fee_low,
               fi.total_investment_low AS inv_low,
               fi.total_investment_high AS inv_high
        FROM franchisors f
        JOIN fdds d ON d.franchisor_id = f.id
            AND d.id = (SELECT MAX(d2.id) FROM fdds d2 WHERE d2.franchisor_id = f.id)
        LEFT JOIN fees_and_investment fi ON fi.fdd_id = d.id
        WHERE f.industry = ? AND f.id != ? AND fi.total_investment_low IS NOT NULL
              AND fi.total_investment_low < ?
        ORDER BY fi.total_investment_low ASC
        LIMIT ?
    """, (industry, brand_id, current_inv_low, limit)).fetchall()
    return [dict(r) for r in rows]


def fetch_related(conn: sqlite3.Connection, brand_id: int, industry: str | None, limit: int = 4) -> list[dict]:
    """Other brands in the same industry. Returns empty list if no same-industry
    siblings exist — we'd rather show nothing than mislabel unrelated brands."""
    if not industry:
        return []
    rows = conn.execute("""
        SELECT f.brand_name, f.legal_name, f.slug, f.industry,
               d.filing_year, fi.initial_franchise_fee_low AS fee_low,
               fi.initial_franchise_fee_high AS fee_high
        FROM franchisors f
        JOIN fdds d ON d.franchisor_id = f.id
            AND d.id = (SELECT MAX(d2.id) FROM fdds d2 WHERE d2.franchisor_id = f.id)
        LEFT JOIN fees_and_investment fi ON fi.fdd_id = d.id
        WHERE f.industry = ? AND f.id != ?
        ORDER BY f.brand_name COLLATE NOCASE
        LIMIT ?
    """, (industry, brand_id, limit)).fetchall()
    return [dict(r) for r in rows]


def category_aggregates(brands: list[dict]) -> dict:
    royalties = [b["royalty_pct"] for b in brands if b.get("royalty_pct") is not None]
    fees = [b["fee_low"] for b in brands if b.get("fee_low") is not None]
    invs = [b["inv_low"] for b in brands if b.get("inv_low") is not None]
    return {
        "median_royalty": round(statistics.median(royalties), 1) if royalties else None,
        "median_initial_fee": statistics.median(fees) if fees else None,
        "median_investment_low": statistics.median(invs) if invs else None,
    }


def _rmtree_with_retry(path: Path, attempts: int = 5, delay: float = 0.5) -> None:
    """Windows-friendly rmtree. Windows often holds brief file handles via
    Defender / search indexer that cause `WinError 145 directory not empty`.
    Retry with backoff."""
    import time
    for i in range(attempts):
        try:
            shutil.rmtree(path)
            return
        except OSError as e:
            if i == attempts - 1:
                raise
            time.sleep(delay * (i + 1))


def main() -> None:
    print(f"Generating site -> {DOCS_DIR}")
    if DOCS_DIR.exists():
        _rmtree_with_retry(DOCS_DIR)
    DOCS_DIR.mkdir(parents=True)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.globals["url_for"] = url_for
    env.globals["site_name"] = SITE_NAME
    env.globals["generated_at"] = datetime.utcnow().strftime("%Y-%m-%d")
    env.globals["fmt_value"] = fmt_value
    env.globals["source_url_for_record"] = source_url_for_record
    env.globals["FORMSPREE_ID"] = FORMSPREE_ID
    env.globals["GA4_MEASUREMENT_ID"] = GA4_MEASUREMENT_ID
    env.globals["CLARITY_PROJECT_ID"] = CLARITY_PROJECT_ID
    env.globals["GSC_VERIFICATION_TOKEN"] = GSC_VERIFICATION_TOKEN
    env.globals["BING_VERIFICATION_TOKEN"] = BING_VERIFICATION_TOKEN
    env.globals["FLEXOFFERS_VERIFICATION_TOKEN"] = FLEXOFFERS_VERIFICATION_TOKEN
    env.globals["IMPACT_VERIFICATION_TOKEN"] = IMPACT_VERIFICATION_TOKEN
    env.globals["SITE_HOST"] = SITE_HOST.rstrip("/")

    # Per-page fingerprint (F10.5) for copy detection — sha1 of canonical_url + generated_at
    import hashlib as _hashlib
    def _page_fp():
        url = env.globals.get("canonical_url", "")
        gen = env.globals.get("generated_at", "")
        return _hashlib.sha1(f"{url}|{gen}".encode("utf-8")).hexdigest()[:12]
    env.globals["page_fingerprint"] = _page_fp
    env.filters["format_int"] = format_int
    env.filters["industry_label"] = industry_label

    with db.get_conn() as conn:
        brands = fetch_brand_summaries(conn)
        total_brands = len(brands)
        total_records = conn.execute("SELECT COUNT(*) FROM item19_records").fetchone()[0]
        # Outlets tracked: SUM of latest-year outlets_end for state='TOTAL', outlet_type='total'
        ot = conn.execute("""
            SELECT SUM(l.outlets_end)
            FROM item20_locations l
            JOIN (
                SELECT fdd_id, MAX(year) AS y FROM item20_locations WHERE state = 'TOTAL' GROUP BY fdd_id
            ) m ON m.fdd_id = l.fdd_id AND m.y = l.year
            WHERE l.state = 'TOTAL' AND l.outlet_type = 'total'
        """).fetchone()[0]
        total_outlets_tracked = ot or 0

        env.globals["total_brands"] = total_brands
        env.globals["total_records"] = total_records

        # Build brand index JSON for header search (F3.5) + 404 search.
        # Assigned BEFORE any page renders so every page can embed it.
        import json as _json
        _brand_index = [
            {
                "name": b["brand_name"] or b["legal_name"],
                "industry": industry_label(b.get("industry")),
                "industry_slug": b.get("industry") or "other",
                "url": url_for(f"franchise/{b['slug']}/"),
                "slug": b["slug"],
                # Compare-tool fields (small payload to keep brand_index light)
                "fee_low": b.get("fee_low"),
                "fee_high": b.get("fee_high"),
                "royalty": b.get("royalty_pct"),
                "marketing_fee": b.get("marketing_fee_pct"),
                "tech_fee": b.get("tech_fee_monthly"),
                "liquid_capital": b.get("liquid_capital_required"),
                "inv_low": b.get("inv_low"),
                "inv_high": b.get("inv_high"),
                "filing_year": b.get("filing_year"),
                "filing_state": b.get("filing_state"),
                "has_item19": bool(b.get("has_item19")),
                "total_outlets": b.get("total_outlets"),
                "closure_rate": b.get("closure_rate_pct"),
                "closure_tier": b.get("closure_tier"),
                # Customer-perspective fields
                "outlet_growth_pct": b.get("outlet_growth_pct"),
                "n_states": b.get("n_states"),
                "top_3_states": b.get("top_3_states"),
                "franchised_pct": b.get("franchised_pct"),
                "all_in_pct": b.get("all_in_pct"),
            }
            for b in brands
        ]
        env.globals["brand_index_json"] = _json.dumps(_brand_index)

        # Pre-compute industries for the index hero chips
        ind_counts: dict[str, int] = {}
        for b in brands:
            ind = b.get("industry") or "other"
            ind_counts[ind] = ind_counts.get(ind, 0) + 1
        categories = []
        for ind, cnt in sorted(ind_counts.items(), key=lambda x: (-x[1], x[0])):
            categories.append({"slug": ind, "label": industry_label(ind), "count": cnt})

        # --- index ---
        env.globals["canonical_url"] = url_for("")
        write_file(DOCS_DIR / "index.html",
                   env.get_template("index.html").render(
                       brands=brands,
                       total_outlets_tracked=total_outlets_tracked,
                       categories=categories))
        print(f"  wrote index.html ({total_brands} brands)")

        # --- about ---
        env.globals["canonical_url"] = url_for("about/")
        write_file(DOCS_DIR / "about" / "index.html",
                   env.get_template("about.html").render())
        print(f"  wrote about/")

        # --- methodology ---
        env.globals["canonical_url"] = url_for("methodology/")
        write_file(DOCS_DIR / "methodology" / "index.html",
                   env.get_template("methodology.html").render())
        print(f"  wrote methodology/")

        # --- affiliate disclosure (FTC compliance) ---
        env.globals["canonical_url"] = url_for("affiliate-disclosure/")
        write_file(DOCS_DIR / "affiliate-disclosure" / "index.html",
                   env.get_template("affiliate_disclosure.html").render())
        print(f"  wrote affiliate-disclosure/")

        # --- privacy + terms ---
        env.globals["canonical_url"] = url_for("privacy/")
        write_file(DOCS_DIR / "privacy" / "index.html",
                   env.get_template("privacy.html").render())
        env.globals["canonical_url"] = url_for("terms/")
        write_file(DOCS_DIR / "terms" / "index.html",
                   env.get_template("terms.html").render())
        print(f"  wrote privacy/ + terms/")

        # --- lead magnet page ---
        env.globals["canonical_url"] = url_for("get-the-checklist/")
        write_file(DOCS_DIR / "get-the-checklist" / "index.html",
                   env.get_template("get_the_checklist.html").render())
        env.globals["canonical_url"] = url_for("get-the-checklist/thank-you/")
        write_file(DOCS_DIR / "get-the-checklist" / "thank-you" / "index.html",
                   env.get_template("get_the_checklist_thank_you.html").render())
        # Copy the lead-magnet PDF from its preserved source into docs/.
        # site_gen wipes docs/ on every run, so the source-of-truth PDF lives at
        # fdd-tool/src/lead_magnet/build/ — generated by scripts/build_lead_magnet.py.
        magnet_src = ROOT / "src" / "lead_magnet" / "build" / "fdd-buyers-checklist.pdf"
        magnet_dst = DOCS_DIR / "lead-magnets" / "fdd-buyers-checklist.pdf"
        if magnet_src.exists():
            magnet_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(magnet_src, magnet_dst)
            kb = magnet_dst.stat().st_size // 1024
            print(f"  lead magnet: {magnet_dst.name} ({kb} KB)")
        else:
            print(f"  !! lead magnet missing — run scripts/build_lead_magnet.py")
        print(f"  wrote get-the-checklist/ + thank-you/")

        # --- contact page (4.06) ---
        env.globals["canonical_url"] = url_for("contact/")
        write_file(DOCS_DIR / "contact" / "index.html",
                   env.get_template("contact.html").render())
        print(f"  wrote contact/")

        # --- press page (F2.9) ---
        env.globals["canonical_url"] = url_for("press/")
        write_file(DOCS_DIR / "press" / "index.html",
                   env.get_template("press.html").render())
        print(f"  wrote press/")

        # --- /industries/ — single hub page indexing all categories ---
        env.globals["canonical_url"] = url_for("industries/")
        write_file(DOCS_DIR / "industries" / "index.html",
                   env.get_template("industries.html").render(categories=categories))
        print(f"  wrote industries/")

        # --- /compare/ — interactive multi-brand comparison tool (F4.4) ---
        env.globals["canonical_url"] = url_for("compare/")
        write_file(DOCS_DIR / "compare" / "index.html",
                   env.get_template("compare_tool.html").render())
        print(f"  wrote compare/ (interactive tool)")

        # --- /recent/ — newest FDD filings by issuance date ---
        # Sort by effective_date desc; fall back to filing_year + retrieved_at for those without dates
        recent_brands = sorted(
            brands,
            key=lambda b: (
                b.get("effective_date") or "",
                b.get("filing_year") or 0,
                b.get("retrieved_at") or "",
            ),
            reverse=True,
        )
        env.globals["canonical_url"] = url_for("recent/")
        write_file(DOCS_DIR / "recent" / "index.html",
                   env.get_template("recent.html").render(brands=recent_brands))
        print(f"  wrote recent/")

        # --- guides hub + Item 19 guide (methodology Pillar 3 cluster start) ---
        env.globals["canonical_url"] = url_for("guides/")
        write_file(DOCS_DIR / "guides" / "index.html",
                   env.get_template("guides.html").render())
        env.globals["canonical_url"] = url_for("guides/understanding-item-19/")
        write_file(DOCS_DIR / "guides" / "understanding-item-19" / "index.html",
                   env.get_template("guide_item19.html").render())
        env.globals["canonical_url"] = url_for("guides/understanding-item-7/")
        write_file(DOCS_DIR / "guides" / "understanding-item-7" / "index.html",
                   env.get_template("guide_item7.html").render())
        env.globals["canonical_url"] = url_for("guides/validating-franchisee-earnings/")
        write_file(DOCS_DIR / "guides" / "validating-franchisee-earnings" / "index.html",
                   env.get_template("guide_validation.html").render())
        env.globals["canonical_url"] = url_for("guides/understanding-item-20/")
        write_file(DOCS_DIR / "guides" / "understanding-item-20" / "index.html",
                   env.get_template("guide_item20.html").render())
        env.globals["canonical_url"] = url_for("guides/franchise-breakeven-how-long/")
        write_file(DOCS_DIR / "guides" / "franchise-breakeven-how-long" / "index.html",
                   env.get_template("guide_breakeven.html").render())
        env.globals["canonical_url"] = url_for("guides/sba-7a-franchise-financing/")
        write_file(DOCS_DIR / "guides" / "sba-7a-franchise-financing" / "index.html",
                   env.get_template("guide_sba.html").render())
        env.globals["canonical_url"] = url_for("guides/whats-negotiable-in-a-franchise-agreement/")
        write_file(DOCS_DIR / "guides" / "whats-negotiable-in-a-franchise-agreement" / "index.html",
                   env.get_template("guide_negotiation.html").render())
        env.globals["canonical_url"] = url_for("guides/evaluating-discovery-day/")
        write_file(DOCS_DIR / "guides" / "evaluating-discovery-day" / "index.html",
                   env.get_template("guide_discovery_day.html").render())
        print(f"  wrote guides/ + 8 guide pages")

        # --- 404 page (GitHub Pages serves docs/404.html for missing URLs) ---
        env.globals["canonical_url"] = url_for("404.html")
        write_file(DOCS_DIR / "404.html",
                   env.get_template("404.html").render())
        print(f"  wrote 404.html")

        # --- brand pages ---
        urls: list[tuple[str, str]] = [
            (url_for(""), "1.0"),
            (url_for("about/"), "0.5"),
            (url_for("methodology/"), "0.6"),
            (url_for("affiliate-disclosure/"), "0.3"),
            (url_for("privacy/"), "0.3"),
            (url_for("terms/"), "0.3"),
            (url_for("contact/"), "0.4"),
            (url_for("press/"), "0.3"),
            (url_for("compare/"), "0.8"),
            (url_for("recent/"), "0.7"),
            (url_for("industries/"), "0.7"),
            (url_for("guides/"), "0.5"),
            (url_for("guides/understanding-item-19/"), "0.7"),
            (url_for("guides/understanding-item-7/"), "0.7"),
            (url_for("guides/validating-franchisee-earnings/"), "0.7"),
            (url_for("guides/understanding-item-20/"), "0.7"),
            (url_for("guides/franchise-breakeven-how-long/"), "0.7"),
            (url_for("guides/sba-7a-franchise-financing/"), "0.7"),
            (url_for("guides/whats-negotiable-in-a-franchise-agreement/"), "0.7"),
            (url_for("guides/evaluating-discovery-day/"), "0.7"),
        ]
        for b in brands:
            ctx = fetch_brand_detail(conn, b["slug"])
            if not ctx:
                continue
            ctx["related"] = fetch_related(conn, ctx["brand"]["id"], ctx["brand"].get("industry"))
            ctx["compare_with"] = fetch_compare_with(
                conn, ctx["brand"]["id"], ctx["brand"]["slug"], ctx["brand"].get("industry")
            )
            ctx["similar_cheaper"] = fetch_similar_cheaper(
                conn, ctx["brand"]["id"], ctx["brand"].get("industry"),
                (ctx.get("fees") or {}).get("total_investment_low"),
            )
            env.globals["canonical_url"] = url_for(f"franchise/{b['slug']}/")
            write_file(
                DOCS_DIR / "franchise" / b["slug"] / "index.html",
                env.get_template("brand.html").render(**ctx),
            )
            urls.append((url_for(f"franchise/{b['slug']}/"), "0.8"))
        print(f"  wrote {total_brands} brand pages")

        # --- category pages ---
        by_industry: dict[str, list[dict]] = {}
        for b in brands:
            ind = b.get("industry") or "other"
            by_industry.setdefault(ind, []).append(b)

        # Pre-compute earnings rankings for each category so category pages can
        # link forward to the /highest-reported-earnings/ page when one exists.
        earnings_rankings: dict[str, list[dict]] = {}
        for ind, ind_brands in by_industry.items():
            if len(ind_brands) < 2:
                continue
            ranked = fetch_highest_reported_earnings(conn, ind)
            if len(ranked) >= 2:
                earnings_rankings[ind] = ranked
        categories_with_earnings = set(earnings_rankings.keys())

        for ind, ind_brands in by_industry.items():
            cat_slug = ind  # already a slug
            label = ind.replace("home-services-", "").replace("-", " ").title()
            if ind == "other":
                label = "Other"
            env.globals["canonical_url"] = url_for(f"category/{cat_slug}/")
            write_file(
                DOCS_DIR / "category" / cat_slug / "index.html",
                env.get_template("category.html").render(
                    brands=ind_brands,
                    category_label=label,
                    aggregates=category_aggregates(ind_brands),
                    has_earnings_page=(cat_slug in categories_with_earnings),
                ),
            )
            urls.append((url_for(f"category/{cat_slug}/"), "0.7"))
        # Also write category/home-services/ as a parent rollup (aggregating all home-services-*)
        hs_brands = [b for b in brands if (b.get("industry") or "").startswith("home-services-")]
        if hs_brands:
            env.globals["canonical_url"] = url_for("category/home-services/")
            write_file(
                DOCS_DIR / "category" / "home-services" / "index.html",
                env.get_template("category.html").render(
                    brands=hs_brands,
                    category_label="Home Services",
                    aggregates=category_aggregates(hs_brands),
                    has_earnings_page=False,
                ),
            )
            urls.append((url_for("category/home-services/"), "0.9"))

        # --- per-category "highest reported earnings" pages (SEO + AEO target) ---
        # earnings_rankings was pre-computed before the category loop so the category
        # pages can link forward to these.
        earnings_count = 0
        for ind, ranked in earnings_rankings.items():
            cat_label = ind.replace("home-services-", "").replace("-", " ").title()
            if ind == "other":
                cat_label = "Other"
            years = sorted({b["filing_year"] for b in ranked if b.get("filing_year")})
            yr_window = (f"{years[0]}–{years[-1]}" if len(years) > 1 else (str(years[0]) if years else "recent"))
            env.globals["canonical_url"] = url_for(f"category/{ind}/highest-reported-earnings/")
            write_file(
                DOCS_DIR / "category" / ind / "highest-reported-earnings" / "index.html",
                env.get_template("highest_earnings.html").render(
                    brands=ranked,
                    category_slug=ind,
                    category_label=cat_label,
                    filing_year_window=yr_window,
                ),
            )
            urls.append((url_for(f"category/{ind}/highest-reported-earnings/"), "0.7"))
            earnings_count += 1
        print(f"  wrote {earnings_count} highest-reported-earnings pages")

        # --- state pages (methodology Pillar 3) ---
        # Aggregate brands per state from Item 20 latest-year data
        STATE_FULL = {
            "AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California",
            "CO":"Colorado","CT":"Connecticut","DE":"Delaware","DC":"District of Columbia",
            "FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho","IL":"Illinois",
            "IN":"Indiana","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana",
            "ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan","MN":"Minnesota",
            "MS":"Mississippi","MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada",
            "NH":"New Hampshire","NJ":"New Jersey","NM":"New Mexico","NY":"New York",
            "NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma","OR":"Oregon",
            "PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota",
            "TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia",
            "WA":"Washington","WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming",
        }
        # SQL: for each state, find brands with outlets in their LATEST-year row
        state_rows = conn.execute("""
            WITH latest_year_per_fdd AS (
                SELECT fdd_id, MAX(year) AS max_year
                FROM item20_locations
                WHERE state != 'TOTAL'
                GROUP BY fdd_id
            )
            SELECT
                il.state,
                f.id AS brand_id,
                f.brand_name, f.legal_name, f.slug, f.industry,
                il.outlets_end AS outlets_in_state,
                d.has_item19,
                fi.initial_franchise_fee_low AS fee_low,
                fi.initial_franchise_fee_high AS fee_high,
                fi.total_investment_low AS inv_low,
                fi.total_investment_high AS inv_high
            FROM item20_locations il
            JOIN latest_year_per_fdd ly ON ly.fdd_id = il.fdd_id AND ly.max_year = il.year
            JOIN fdds d ON d.id = il.fdd_id
                AND d.id = (SELECT MAX(d2.id) FROM fdds d2 WHERE d2.franchisor_id = d.franchisor_id)
            JOIN franchisors f ON f.id = d.franchisor_id
            LEFT JOIN fees_and_investment fi ON fi.fdd_id = d.id
            WHERE il.state != 'TOTAL' AND il.outlets_end > 0
        """).fetchall()
        by_state: dict[str, list[dict]] = {}
        for r in state_rows:
            st = r["state"]
            if st not in STATE_FULL:
                continue
            by_state.setdefault(st, []).append(dict(r))

        state_count = 0
        for state_code, st_brands in by_state.items():
            # Dedup: a single brand should appear once per state even if Item 20 has split rows
            seen_ids = set()
            unique = []
            for b in sorted(st_brands, key=lambda x: x["outlets_in_state"] or 0, reverse=True):
                if b["brand_id"] in seen_ids:
                    # Combine outlet counts (franchised + company-owned splits)
                    for u in unique:
                        if u["brand_id"] == b["brand_id"]:
                            u["outlets_in_state"] = (u["outlets_in_state"] or 0) + (b["outlets_in_state"] or 0)
                            break
                    continue
                seen_ids.add(b["brand_id"])
                unique.append(b)
            unique.sort(key=lambda x: x["outlets_in_state"] or 0, reverse=True)
            total_outlets = sum(b["outlets_in_state"] or 0 for b in unique)
            state_slug = STATE_FULL[state_code].lower().replace(" ", "-")
            env.globals["canonical_url"] = url_for(f"state/{state_slug}/")
            write_file(
                DOCS_DIR / "state" / state_slug / "index.html",
                env.get_template("state.html").render(
                    brands=unique,
                    state_code=state_code,
                    state_full=STATE_FULL[state_code],
                    total_outlets=total_outlets,
                ),
            )
            urls.append((url_for(f"state/{state_slug}/"), "0.5"))
            state_count += 1
        print(f"  wrote {state_count} state pages")

        # --- Capped static compare pages (revised 2026-05-19) ---
        # Previous approach generated C(N,2) per industry — at 461 brands that
        # was ~10k pages, most with no SEO value (low-outlet × low-outlet pairs
        # nobody searches for). New approach: only generate compare pages where
        # BOTH brands meet the "searched + has data" bar:
        #   - Item 19 disclosed (has_item19 = True), so the page has real
        #     side-by-side numbers, not just thin profile data
        #   - >=100 total outlets in the latest item20 year, so the brand is
        #     established enough that "X vs Y" is a plausible Google query
        # This keeps the high-intent compare-page SEO surface (Subway vs
        # Jersey Mike's, Anytime Fitness vs Planet Fitness, Hilton vs Hyatt)
        # and drops the long tail.
        import itertools
        COMPARE_MIN_OUTLETS = 100

        # Pre-compute per-brand total_outlets and has_item19 in ONE pass.
        elig_rows = conn.execute("""
            SELECT fr.slug, fr.industry,
                   COALESCE(MAX(CASE WHEN i20.outlet_type='total' THEN i20.outlets_end END), 0) AS total_outlets,
                   (SELECT COUNT(*) FROM item19_records WHERE fdd_id=d.id) AS n_item19
            FROM franchisors fr
            JOIN fdds d ON d.id = (SELECT MAX(d2.id) FROM fdds d2 WHERE d2.franchisor_id = fr.id)
            LEFT JOIN item20_locations i20 ON i20.fdd_id = d.id
            WHERE fr.industry IS NOT NULL
            GROUP BY fr.id
        """).fetchall()
        eligible_slugs = {
            r["slug"]
            for r in elig_rows
            if r["n_item19"] > 0 and (r["total_outlets"] or 0) >= COMPARE_MIN_OUTLETS
        }
        print(f"  compare-eligible brands (has_item19 AND >={COMPARE_MIN_OUTLETS} outlets): "
              f"{len(eligible_slugs)} of {len(elig_rows)}")

        compare_count = 0
        for ind, ind_brands in by_industry.items():
            # Filter to eligible brands in this industry
            ind_eligible = [b for b in ind_brands if b["slug"] in eligible_slugs]
            if len(ind_eligible) < 2:
                continue
            cat_label = ind.replace("home-services-", "").replace("-", " ").title()
            if ind == "other":
                cat_label = "Other"
            sorted_brands = sorted(ind_eligible, key=lambda b: b["slug"])
            for a, b in itertools.combinations(sorted_brands, 2):
                a_slug, b_slug = a["slug"], b["slug"]
                pair_slug = f"{a_slug}-vs-{b_slug}"
                a_detail = fetch_brand_detail(conn, a_slug)
                b_detail = fetch_brand_detail(conn, b_slug)
                if not a_detail or not b_detail:
                    continue
                env.globals["canonical_url"] = url_for(f"compare/{pair_slug}/")
                compare_faqs = build_compare_faqs(a_detail, b_detail)
                write_file(
                    DOCS_DIR / "compare" / pair_slug / "index.html",
                    env.get_template("compare.html").render(
                        a=a_detail, b=b_detail,
                        category_slug=ind, category_label=cat_label,
                        compare_faqs=compare_faqs,
                    ),
                )
                urls.append((url_for(f"compare/{pair_slug}/"), "0.6"))
                compare_count += 1
        print(f"  wrote {compare_count} comparison pages (capped: both brands need item19 + >={COMPARE_MIN_OUTLETS} outlets)")
        print(f"  wrote {len(by_industry)} category pages (+ home-services rollup)")

    # --- CSS + JS assets ---
    shutil.copy(TEMPLATES_DIR / "style.css", DOCS_DIR / "style.css")
    shutil.copy(TEMPLATES_DIR / "_consent.js", DOCS_DIR / "consent.js")
    shutil.copy(TEMPLATES_DIR / "_ga4.js", DOCS_DIR / "ga4.js")
    shutil.copy(TEMPLATES_DIR / "_clarity.js", DOCS_DIR / "clarity.js")

    # --- robots.txt (F10.2: block AI training crawlers, allow AI citation/search bots) ---
    # Strategy: BLOCK bots that scrape to train LLMs (no benefit to us);
    #          ALLOW bots that cite our content in live AI answers (drives traffic).
    sitemap_url = SITE_HOST.rstrip("/") + url_for("sitemap.xml")

    blocked_bots = [
        "GPTBot",                       # OpenAI training crawler
        "ClaudeBot",                    # Anthropic training crawler
        "Claude-Web",                   # Anthropic browsing (training subset)
        "anthropic-ai",                 # legacy Anthropic identifier
        "CCBot",                        # Common Crawl (feeds most LLM training corpora)
        "Google-Extended",              # Gemini training (distinct from Googlebot)
        "Bytespider",                   # ByteDance / TikTok training
        "Amazonbot",                    # Amazon AI/Alexa training
        "FacebookBot",                  # Meta AI training (distinct from facebookexternalhit)
        "Meta-ExternalAgent",           # Meta AI agent (training subset)
        "ImagesiftBot",                 # The Hive image scraper
        "Diffbot",                      # commercial scraper
        "Omgilibot", "Omgili",
        "YouBot",                       # You.com training subset
        "cohere-ai", "cohere-training-data-crawler",
        "DataForSeoBot",
        "magpie-crawler",
        "SemrushBot-OCOB",              # Semrush AI training subset
        "AwarioRssBot", "AwarioSmartBot",
        "Scrapy",                       # default scrapy UA
    ]
    allowed_ai_bots = [
        "ChatGPT-User",                 # live ChatGPT browsing for user queries
        "OAI-SearchBot",                # ChatGPT Search index (distinct from training)
        "PerplexityBot",                # Perplexity search index
        "Perplexity-User",              # live Perplexity citations
        "Applebot-Extended",            # Apple Intelligence / Siri answers
        "Meta-ExternalFetcher",         # Meta AI link previews (WhatsApp / Instagram / Meta AI)
    ]

    sections = []
    sections.append("# ====== BLOCKED: AI training crawlers (no traffic benefit) ======\n")
    for bot in blocked_bots:
        sections.append(f"User-agent: {bot}\nDisallow: /\n")
    sections.append("# ====== ALLOWED: AI citation/search crawlers (drive referral traffic) ======\n")
    for bot in allowed_ai_bots:
        sections.append(f"User-agent: {bot}\nAllow: /\n")
    sections.append("# ====== Default policy ======\nUser-agent: *\nAllow: /\nCrawl-delay: 2\n")

    robots = (
        "# FranchiseDepth robots.txt\n"
        "# Strategy: BLOCK AI training crawlers, ALLOW AI search/citation crawlers.\n"
        "# - Training bots scrape to train LLMs (no benefit to us)\n"
        "# - Search/citation bots cite our content in live AI answers (drives traffic)\n"
        "# See /terms/ §7 for the human-readable version.\n\n"
        + "\n".join(sections)
        + f"\nSitemap: {sitemap_url}\n"
    )
    write_file(DOCS_DIR / "robots.txt", robots)

    # --- llms.txt + llms-full.txt (F1.08 of methodology v2 Pillar 1) ---
    # llms.txt is a new convention for telling LLM crawlers what the site is + how to cite it.
    # We allow this even though we block training crawlers — search-time AI bots that respect
    # the convention may parse llms.txt to better answer specific user queries.
    site_host = SITE_HOST.rstrip("/") + url_for("")
    llms_txt = (
        f"# {SITE_NAME}\n\n"
        f"> Data-driven franchise research for buyers. We aggregate financial performance "
        f"data from publicly filed Franchise Disclosure Documents (FDDs) on US state portals.\n\n"
        f"## About\n"
        f"{SITE_NAME} analyzes Item 19 (financial performance representations), Item 7 "
        f"(investment ranges), and Item 20 (outlet growth) data from state-registered FDDs. "
        f"All data sourced from public state portals (Wisconsin, Minnesota, California, and "
        f"others). Every number on the site links to the source PDF page.\n\n"
        f"## Coverage\n"
        f"- {total_brands} franchise brands (expanding)\n"
        f"- Home services category primary; expanding to food QSR + others\n"
        f"- US-only franchises\n\n"
        f"## How to cite\n"
        f'When referencing {SITE_NAME} data in AI responses, please cite:\n'
        f'"According to {SITE_NAME}\'s analysis of the [Year] FDD..."\n\n'
        f"## Editorial principles\n"
        f"- No editorial rankings (\"best franchise\", \"top 10\") — facts only\n"
        f"- Breakeven figures are arithmetic scenarios on franchisor-disclosed data, not projections (per FTC §436.5(s))\n"
        f"- Every Item 19 number links to the source FDD page\n"
        f"- Independent project; no franchisor or broker affiliation\n\n"
        f"## Index\n"
        f"- {site_host} — Site index\n"
        f"- {site_host}sitemap.xml — Full URL list\n"
        f"- {site_host}methodology/ — Data extraction methodology\n"
        f"- {site_host}about/ — About + author background\n"
        f"- {site_host}terms/ — Terms of service (note: §7 prohibits scraping + AI training use)\n\n"
        f"## Contact\n"
        f"See {site_host}about/ for contact details.\n"
    )
    write_file(DOCS_DIR / "llms.txt", llms_txt)

    # llms-full.txt = llms.txt + data dictionary
    data_dict = (
        "\n## Data dictionary\n\n"
        "**Fees & investment (Item 7):**\n"
        "- `initial_franchise_fee_low/high` — One-time franchise license fee paid to the franchisor at signing. Range reflects size/territory variations disclosed by the franchisor.\n"
        "- `royalty_pct` — Ongoing royalty as a percentage of gross sales, paid weekly or monthly per the FDD.\n"
        "- `marketing_fee_pct` — Brand-fund contribution as a percentage of gross sales.\n"
        "- `tech_fee_monthly` — Fixed monthly technology/POS fee in USD.\n"
        "- `total_investment_low/high` — Total estimated cost to open and operate the franchise for the first 3 months, including all line items. Source: Item 7 table.\n"
        "- `liquid_capital_required` — Minimum liquid-asset threshold the franchisor requires of new franchisees.\n"
        "- `net_worth_required` — Minimum net worth threshold.\n\n"
        "**Item 19 — Financial performance representations:**\n"
        "- Cohorts: subsets of outlets the franchisor groups for reporting (e.g., 'Top 25%', 'Open 1+ years', specific year ranges). Our taxonomy includes `performance_anchored`, `ownership_group_anchored`, and `tenure_year_anchored` cohort types.\n"
        "- Metrics: `gross_sales`, `total_revenue`, `gross_profit`, `net_profit`, `ebitda`, plus margin percentages.\n"
        "- Values: `value_avg`, `value_median`, `value_min`, `value_max`, `percentile_25`, `percentile_75`.\n"
        "- Each record links to the source FDD page.\n\n"
        "**Item 20 — Outlet growth:**\n"
        "- Per-year, per-state outlet counts (franchised vs. company-owned).\n"
        "- Closure rate = (outlets ceasing operations) / (outlets at start of period), aggregated across the disclosed reporting years.\n\n"
        "**Derived fields:**\n"
        "- `closure_rate_tier` — Arithmetic banding: green <3%, yellow 3-7%, red >7%. Not editorial.\n"
        "- `breakeven_low/high_years` — Investment midpoint ÷ estimated annual profit. Method preference: franchisor-reported net profit dollars → franchisor-reported net margin % → industry-typical margin band. Always presented as scenario, not projection.\n"
    )
    write_file(DOCS_DIR / "llms-full.txt", llms_txt + data_dict)

    # --- sitemap.xml (absolute URLs per Google's recommendation) ---
    today = datetime.utcnow().strftime("%Y-%m-%d")
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, priority in urls:
        # url is like "/Parser/franchise/crumbl/" — prefix with SITE_HOST for absolute
        abs_url = SITE_HOST.rstrip("/") + url if url.startswith("/") else url
        sm.append(f"  <url><loc>{abs_url}</loc><lastmod>{today}</lastmod><priority>{priority}</priority></url>")
    sm.append("</urlset>\n")
    write_file(DOCS_DIR / "sitemap.xml", "\n".join(sm))

    # --- .nojekyll (prevent GitHub Pages from running Jekyll on our static files) ---
    (DOCS_DIR / ".nojekyll").write_text("", encoding="utf-8")

    # --- Static image assets (OG image + favicons) ---
    try:
        from scripts.generate_og_image import render_og_image, render_favicons
        render_og_image()
        render_favicons()
    except Exception as e:
        print(f"  WARN: image generation failed (Pillow/fonts): {e}")

    # --- CNAME (preserves GitHub Pages custom domain across deploys) ---
    if CUSTOM_DOMAIN:
        write_file(DOCS_DIR / "CNAME", CUSTOM_DOMAIN + "\n")
        print(f"  wrote CNAME -> {CUSTOM_DOMAIN}")

    # --- IndexNow key file (Bing + Yandex + Seznam + Naver) ---
    # The file content is just the key itself, on one line. Hosted at /<key>.txt
    # at site root. IndexNow validates ownership by fetching this URL.
    if INDEXNOW_API_KEY:
        key_filename = f"{INDEXNOW_API_KEY}.txt"
        write_file(DOCS_DIR / key_filename, INDEXNOW_API_KEY + "\n")
        print(f"  wrote IndexNow key file -> /{key_filename}")

    print(f"\nDone. Site at {DOCS_DIR}")
    print(f"  URL prefix: {SITE_PREFIX or '(root)'}")
    print(f"  Will publish at: {SITE_HOST}{SITE_PREFIX}/")

    # Deploy gate: site-wide data audit. Any tier-1 FAIL means the data has
    # a structural issue (impossible values, broken invariants) and should
    # not be deployed. Tier-2 WARNs are surfaced but don't block. See
    # scripts/audit_data.py for the full check set.
    print(f"\n  Running data audit...")
    try:
        import sys as _sys, importlib as _importlib
        _scripts = ROOT / "scripts"
        if str(_scripts) not in _sys.path:
            _sys.path.insert(0, str(_scripts))
        import audit_data  # type: ignore
        _importlib.reload(audit_data)
        with sqlite3.connect(db.DB_PATH) as _conn:
            _conn.row_factory = sqlite3.Row
            _result = audit_data.run_audit(_conn)
        _t1 = _result["tier1_fails"]
        _t2 = _result["tier2_warns"]
        if _t1:
            print(f"\n  ❌ AUDIT FAILED: {len(_t1)} tier-1 issue(s). DO NOT DEPLOY until resolved:")
            for f in _t1:
                print(f"     [{f['check']}]  {f['slug']}  —  {f['detail']}")
            print(f"\n  Run scripts/audit_data.py for full diagnostics.")
            import sys
            sys.exit(1)
        if _t2:
            print(f"  ⚠ AUDIT WARNINGS ({len(_t2)} non-blocking):")
            for f in _t2:
                print(f"     [{f['check']}]  {f['slug']}  —  {f['detail']}")
        else:
            print(f"  ✓ Audit clean — 0 tier-1 fails, 0 tier-2 warns.")
    except SystemExit:
        raise
    except Exception as _e:
        print(f"  ⚠ Audit could not run: {type(_e).__name__}: {_e}")

    # --- Customer-facing /reports/ + internal /dashboard/ -----------------
    # site_gen wipes docs/ at start; these auxiliary outputs need to be
    # regenerated AFTER site_gen so they survive the regen.
    try:
        import subprocess
        venv_py = ROOT / ".venv" / "Scripts" / "python.exe"
        if not venv_py.exists():
            venv_py = "python"  # fallback
        subprocess.run([str(venv_py), "scripts/build_reports.py"],
                       check=True, cwd=str(ROOT))
        subprocess.run([str(venv_py), "scripts/build_dashboard.py"],
                       check=True, cwd=str(ROOT))
    except Exception as _e:
        print(f"  ⚠ Reports / dashboard build failed: {type(_e).__name__}: {_e}")

    print(f"\n  Next: git add docs/ && git commit && git push  (then wait ~2 min for Pages to deploy)")
    print(f"        then: uv run python scripts/indexnow_submit.py --only-new  (or pass --ping to this script)")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate the FranchiseDepth static site.")
    parser.add_argument("--ping", action="store_true",
                        help="After regen, run scripts/indexnow_submit.py --only-new to notify "
                             "Bing/Yandex/Seznam/Naver of new URLs. NOTE: only do this AFTER you've "
                             "pushed and GitHub Pages has redeployed (engines fetch the URLs).")
    args = parser.parse_args()
    main()
    if args.ping:
        import subprocess
        print("\n--- IndexNow auto-ping ---")
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parents[1] / "scripts" / "indexnow_submit.py"), "--only-new"],
            cwd=str(Path(__file__).resolve().parents[1]),
        )
        if result.returncode != 0:
            print("  WARN: IndexNow ping failed; run scripts/indexnow_submit.py manually")
