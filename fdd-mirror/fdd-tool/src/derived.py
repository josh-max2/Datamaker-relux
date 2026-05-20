"""Derived fields module — one source of truth for every cross-section
decision the brand page needs.

Templates and site_gen ad-hoc logic used to make these decisions independently,
which led to internal contradictions (e.g. TL;DR showing 'Median revenue \$300k'
while the Item 19 section said 'does not publicly disclose'). All such derivations
now live here. Functions are pure (no DB writes, no Jinja env).

Functions:
  disclosure_status            — replaces direct use of fdds.has_item19
  franchised_revenue_distribution — single filter for what franchisees earn
  outlet_breakdown_from_item20 — yearly total + franchised + company_owned
  ongoing_fees_text            — human-readable fees string for any fee shape
  revenue_cohort_set_kind      — 'natural' vs 'performance_anchored'
  calc_default_revenue         — calc input default with honest source label
"""
from __future__ import annotations

import re
import statistics
from typing import Iterable


# Cohorts that represent "what FRANCHISEES earn" (not company-owned, not
# performance-anchored top-quartile cherrypicks).
FRANCHISED_BROAD_COHORTS = (
    "all_franchised",
    "open_24_plus_mo", "open_36_plus_mo",
    "open_48_plus_mo", "open_60_plus_mo",
)

# Performance-anchored cohort names — these are FRANCHISOR-DEFINED buckets
# (Top 10%, Bottom Third, etc.) not statistical quartiles. The calc preset
# buttons need to know this to label them honestly.
PERFORMANCE_ANCHORED_COHORT = "performance_anchored"


# -----------------------------------------------------------------------------
# Helpers (imported from site_gen at use-time to avoid circular import)
# -----------------------------------------------------------------------------

def _is_unit_or_market_metric(record: dict) -> bool:
    """Delegate to site_gen's filter so this module stays one source of truth."""
    from src.site_gen import is_unit_or_market_metric
    return is_unit_or_market_metric(record)


def _record_period_multiplier(record: dict) -> int:
    from src.site_gen import record_period_multiplier
    return record_period_multiplier(record)


# -----------------------------------------------------------------------------
# disclosure_status
# -----------------------------------------------------------------------------

def disclosure_status(item19_records: list[dict], has_item19_flag) -> dict:
    """What does this brand actually disclose in Item 19?

    Replaces direct reads of fdds.has_item19. The flag can drift (extraction
    sometimes sets it inconsistently with the records); records are the
    ground truth.

    Returns:
        {
          "kind":     "formal" | "supplemental" | "none",
          "n_records": int,
          "has_revenue_cohort": bool,
          "broad_cohort_present": bool,
          "label":     str,    # human-readable label for the Item 19 section
        }

    kind:
      - "formal":      records exist AND has_item19 flag set — explicit FPR
      - "supplemental": records exist BUT has_item19 flag NOT set — data
                       present but the franchisor labelled it as non-FPR or
                       the flag drifted. We use the data but label it
                       differently so we don't misrepresent the source.
      - "none":        no records.
    """
    n = len(item19_records)
    has_revenue_cohort = any(
        r.get("metric_name") in ("gross_sales", "total_revenue")
        and (r.get("value_avg") or r.get("value_median"))
        for r in item19_records
    )
    broad_cohort_present = any(
        r.get("cohort_name") in FRANCHISED_BROAD_COHORTS
        for r in item19_records
    )
    flag = bool(has_item19_flag)
    if n == 0:
        kind = "none"
        label = "Item 19 not disclosed"
    elif flag:
        kind = "formal"
        label = "Item 19 financial performance representations"
    else:
        kind = "supplemental"
        label = "Item 19 supplemental data (not a formal FPR)"
    return {
        "kind": kind,
        "n_records": n,
        "has_revenue_cohort": has_revenue_cohort,
        "broad_cohort_present": broad_cohort_present,
        "label": label,
    }


# -----------------------------------------------------------------------------
# franchised_revenue_distribution
# -----------------------------------------------------------------------------

def franchised_revenue_distribution(item19_records: list[dict]) -> list[float]:
    """Canonical "what franchisees earn" annualized revenue distribution.

    Single filter used by: calc default, calc quartile presets, breakeven,
    TL;DR median revenue, FAQ. Before this module, each call site filtered
    slightly differently — that produced the AMRAMP \$2.1M bug, where the
    calc default mixed company-owned cohorts that the breakeven section
    excluded.

    Filters applied:
      - metric in (gross_sales, total_revenue)
      - has at least value_avg or value_median
      - cohort_name in FRANCHISED_BROAD_COHORTS (no company-owned, no
        performance-anchored top-quartile cherrypicks)
      - not a per-transaction / per-job / ramp-up record (is_unit_or_market_metric)
    Returns sorted ascending. Values are annualized.
    """
    vals: list[float] = []
    for r in item19_records:
        if r.get("metric_name") not in ("gross_sales", "total_revenue"):
            continue
        v = r.get("value_median") or r.get("value_avg")
        if not v:
            continue
        if r.get("cohort_name") not in FRANCHISED_BROAD_COHORTS:
            continue
        if _is_unit_or_market_metric(r):
            continue
        vals.append(float(v) * _record_period_multiplier(r))
    return sorted(v for v in vals if v > 0)


def any_revenue_distribution(item19_records: list[dict]) -> list[float]:
    """Same filter as franchised_revenue_distribution but allows ANY cohort
    (not just broad). Used as a fallback for brands that only disclose
    performance-anchored cohorts (Top/Middle/Bottom Third)."""
    vals: list[float] = []
    for r in item19_records:
        if r.get("metric_name") not in ("gross_sales", "total_revenue"):
            continue
        if r.get("cohort_name") == "all_company_owned":
            continue  # always exclude co-owned
        v = r.get("value_median") or r.get("value_avg")
        if not v:
            continue
        if _is_unit_or_market_metric(r):
            continue
        vals.append(float(v) * _record_period_multiplier(r))
    return sorted(v for v in vals if v > 0)


# -----------------------------------------------------------------------------
# outlet_breakdown_from_item20
# -----------------------------------------------------------------------------

def outlet_breakdown_from_item20(item20_yearly: list[dict]) -> dict:
    """Latest-year outlet counts broken out by franchised vs company-owned.

    Item 20 yearly rows have outlet_type values: 'franchised', 'company-owned',
    'total', and a legacy NULL (== franchised at the time of original ingest).

    Returns:
        {
          "latest_year":          int | None,
          "total_latest":         int | None,
          "franchised_latest":    int | None,
          "company_owned_latest": int | None,
        }

    Howard Hanna case: this lets the heatmap caption render
    "X franchised in N states (Y of Z are company-owned offices)" instead
    of falsely attributing the gap to territories/international.
    """
    if not item20_yearly:
        return {"latest_year": None, "total_latest": None,
                "franchised_latest": None, "company_owned_latest": None}
    years = [r["year"] for r in item20_yearly if r.get("year") is not None]
    if not years:
        return {"latest_year": None, "total_latest": None,
                "franchised_latest": None, "company_owned_latest": None}
    latest = max(years)
    rows_for_year = [r for r in item20_yearly if r.get("year") == latest]
    def pick(t):
        for r in rows_for_year:
            if r.get("outlet_type") == t:
                return r.get("outlets_end")
        return None
    total = pick("total")
    franchised = pick("franchised")
    co_owned = pick("company-owned")
    # Legacy: outlet_type=NULL rows are franchised
    if franchised is None:
        for r in rows_for_year:
            if r.get("outlet_type") is None:
                franchised = r.get("outlets_end")
                break
    return {
        "latest_year": latest,
        "total_latest": total,
        "franchised_latest": franchised,
        "company_owned_latest": co_owned,
    }


# -----------------------------------------------------------------------------
# ongoing_fees_text
# -----------------------------------------------------------------------------

def ongoing_fees_text(fees: dict | None) -> str:
    """Human-readable summary of ongoing fees, robust to any fee shape:

      "8% royalty + 2% marketing"            — typical (royalty% + marketing%)
      "Marketing fee only — 3% (no royalty)" — Bath Fitter (flat-fee model, royalty=0)
      "$2,083/month royalty"                  — Howard Hanna (royalty_min_monthly only)
      "$350/month combined fees"              — Kumon (monthly minimums, no %)
      "Not separately disclosed"              — when nothing usable
    """
    if not fees:
        return "Not separately disclosed"
    roy_pct = fees.get("royalty_pct")
    mkt_pct = fees.get("marketing_fee_pct")
    roy_min = fees.get("royalty_min_monthly")
    mkt_min = fees.get("marketing_min_monthly")
    tech = fees.get("tech_fee_monthly")

    parts = []

    # Case 1: normal percentages
    has_roy_pct = roy_pct and roy_pct > 0
    has_mkt_pct = mkt_pct and mkt_pct > 0
    if has_roy_pct and has_mkt_pct:
        return f"{_pct(roy_pct)}% royalty + {_pct(mkt_pct)}% marketing"
    if has_roy_pct and not has_mkt_pct:
        return f"{_pct(roy_pct)}% royalty"
    if has_mkt_pct and not has_roy_pct:
        # Royalty is 0 or null — flag the flat-fee model honestly
        if roy_pct == 0:
            return f"Marketing fee only — {_pct(mkt_pct)}% (no royalty)"
        if roy_min and roy_min > 0:
            return f"${_int(roy_min)}/month royalty + {_pct(mkt_pct)}% marketing"
        return f"{_pct(mkt_pct)}% marketing (no royalty disclosed)"

    # Case 2: flat-dollar royalty only (no %)
    if roy_min and roy_min > 0:
        if mkt_min and mkt_min > 0:
            return f"${_int(roy_min)}/month royalty + ${_int(mkt_min)}/month marketing"
        return f"${_int(roy_min)}/month royalty"

    # Case 3: monthly minimums only — Kumon-style
    monthly = sum(v for v in (mkt_min, tech) if v and v > 0)
    if monthly > 0:
        return f"${_int(monthly)}/month combined fees"

    return "Not separately disclosed"


def _pct(v: float) -> str:
    """Format a percentage with minimal trailing zeros (5.5 -> '5.5', 5 -> '5')."""
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s or "0"


def _int(v: float) -> str:
    return f"{int(round(v)):,}"


# -----------------------------------------------------------------------------
# revenue_cohort_set_kind
# -----------------------------------------------------------------------------

def revenue_cohort_set_kind(item19_records: list[dict]) -> str:
    """Returns 'natural' or 'performance_anchored'.

    A brand that ONLY discloses Top/Middle/Bottom Third (or Top 10% / Bottom 5%)
    cohorts hasn't given us a real distribution — it's given us franchisor-
    defined buckets. The calc preset buttons should label these as
    Bottom tier / Middle tier / Top tier instead of Low / Median / High.
    """
    revenue_records = [
        r for r in item19_records
        if r.get("metric_name") in ("gross_sales", "total_revenue")
        and (r.get("value_avg") or r.get("value_median"))
        and not _is_unit_or_market_metric(r)
        and r.get("cohort_name") != "all_company_owned"
    ]
    if not revenue_records:
        return "natural"
    pa_count = sum(1 for r in revenue_records
                   if r.get("cohort_name") == PERFORMANCE_ANCHORED_COHORT)
    if pa_count > 0 and pa_count >= len(revenue_records) / 2:
        return "performance_anchored"
    return "natural"


# -----------------------------------------------------------------------------
# item19_disclosure_quality — what is the SHAPE of this brand's Item 19?
# -----------------------------------------------------------------------------

# Cohort names that represent franchisee experience (the data buyers actually care about)
_FRANCHISED_COHORT_NAMES = (
    "all_franchised",
    "open_24_plus_mo", "open_36_plus_mo", "open_48_plus_mo", "open_60_plus_mo",
    "open_lt_12mo", "open_12_24mo",
    "tenure_year_anchored", "ownership_group_anchored",
)
_AFFILIATE_COHORT_NAMES = ("all_company_owned",)


def item19_disclosure_quality(item19_records: list[dict]) -> dict:
    """Classify the SHAPE of a brand's Item 19 so the template can render an
    appropriate warning (or no warning, for genuinely-broad disclosure).

    The "covering N cohort × metric records" label on a thin-disclosure brand
    has misled readers — it implies breadth that isn't there. This function
    drives a yellow warning callout above the Item 19 section for brands
    whose disclosure is thin, affiliate-only, longitudinal-only, or
    performance-anchored.

    Returns:
        {
          "kind":  "broad_distribution" | "thin_franchised" | "performance_anchored"
                   | "longitudinal_affiliate" | "affiliate_only" | "none",
          "n_franchised_revenue_records":  int,
          "n_affiliate_revenue_records":   int,
          "n_franchised_cohorts":          int,   # distinct cohort_raw
          "n_affiliate_cohorts":           int,
          "max_franchised_outlets":        int,   # max outlet_count across franchised
          "max_affiliate_outlets":         int,
          "warning_html":                  str | None,
          "warning_severity":              "info" | "warn" | "strong" | None,
        }
    """
    revenue_records = [
        r for r in item19_records
        if r.get("metric_name") in ("gross_sales", "total_revenue")
        and (r.get("value_avg") or r.get("value_median"))
        and not _is_unit_or_market_metric(r)
    ]
    franchised = [r for r in revenue_records
                  if r.get("cohort_name") in _FRANCHISED_COHORT_NAMES]
    affiliate = [r for r in revenue_records
                 if r.get("cohort_name") in _AFFILIATE_COHORT_NAMES]
    pa = [r for r in revenue_records
          if r.get("cohort_name") == "performance_anchored"]

    n_fr_cohorts = len({r.get("cohort_raw") for r in franchised})
    n_af_cohorts = len({r.get("cohort_raw") for r in affiliate})

    max_fr_outlets = max((r.get("outlet_count") or 0 for r in franchised), default=0)
    max_af_outlets = max((r.get("outlet_count") or 0 for r in affiliate), default=0)

    info = {
        "n_franchised_revenue_records": len(franchised),
        "n_affiliate_revenue_records": len(affiliate),
        "n_franchised_cohorts": n_fr_cohorts,
        "n_affiliate_cohorts": n_af_cohorts,
        "max_franchised_outlets": max_fr_outlets,
        "max_affiliate_outlets": max_af_outlets,
    }

    # Classification
    if not revenue_records:
        kind = "none"
        warning_html = None
        warning_severity = None
    elif not franchised and affiliate:
        if n_af_cohorts == 1:
            kind = "longitudinal_affiliate"
            warning_html = _warn_longitudinal_affiliate(max_af_outlets)
        else:
            kind = "affiliate_only"
            warning_html = _warn_affiliate_only(max_af_outlets)
        warning_severity = "strong"
    elif franchised and n_fr_cohorts >= 3:
        kind = "broad_distribution"
        # No warning — this is the case the chart is designed for
        warning_html = None
        warning_severity = None
    elif franchised and n_fr_cohorts <= 2:
        kind = "thin_franchised"
        warning_html = _warn_thin_franchised(n_fr_cohorts, max_fr_outlets,
                                              has_affiliate=bool(affiliate))
        warning_severity = "warn"
    elif pa:
        kind = "performance_anchored"
        warning_html = _warn_performance_anchored(len(pa))
        warning_severity = "warn"
    else:
        kind = "none"
        warning_html = None
        warning_severity = None

    return {"kind": kind, "warning_html": warning_html,
            "warning_severity": warning_severity, **info}


def _warn_longitudinal_affiliate(n_outlets: int) -> str:
    return (
        "<strong>Limited Item 19 disclosure.</strong> "
        "This FDD reports earnings data for <strong>a single franchisor-affiliate outlet</strong> "
        "across multiple years — not a representative sample of franchisee performance. "
        "An affiliate outlet is typically operated by the franchisor or a related party, "
        "often without paying royalties and with operating advantages a buying franchisee "
        "would not share. Don't anchor your expectations on these numbers — "
        "<a href=\"/guides/understanding-item-19/\">read why this is a yellow flag</a> "
        "and validate directly with current franchisees (Item 20 lists them)."
    )


def _warn_affiliate_only(n_outlets: int) -> str:
    return (
        "<strong>Limited Item 19 disclosure.</strong> "
        f"This FDD reports earnings data only for <strong>company-owned / affiliate outlets</strong>"
        f"{f' (max {n_outlets} outlets in any cohort)' if n_outlets else ''} — "
        "no franchisee performance data is disclosed. Affiliate outlets typically "
        "operate without paying royalties and with operating advantages a buying franchisee "
        "would not share. <a href=\"/guides/understanding-item-19/\">Read why this is a "
        "yellow flag</a> and validate directly with current franchisees (Item 20 lists them)."
    )


def _warn_thin_franchised(n_cohorts: int, max_outlets: int, has_affiliate: bool) -> str:
    parts = []
    if n_cohorts == 1:
        parts.append("This FDD discloses a single franchisee cohort"
                     f"{f' (n={max_outlets} outlets)' if max_outlets else ''} — "
                     "not a distribution across performance bands or tenure groups.")
    else:
        parts.append(f"This FDD discloses {n_cohorts} franchisee cohorts"
                     f"{f' (max {max_outlets} outlets in any cohort)' if max_outlets else ''} — "
                     "limited resolution compared to brands that report quartiles or tenure bands.")
    if has_affiliate:
        parts.append("Affiliate-outlet data is also disclosed but excluded from the chart "
                     "below (affiliate outlets aren't representative of typical franchisee "
                     "performance).")
    parts.append("Cross-reference with current franchisees in Item 20 before drawing conclusions.")
    return "<strong>Thin Item 19 disclosure.</strong> " + " ".join(parts)


def _warn_performance_anchored(n_records: int) -> str:
    return (
        "<strong>Performance-anchored cohorts only.</strong> "
        f"This FDD reports {n_records} record(s) in franchisor-defined buckets "
        "(Top/Middle/Bottom Third, Top 10%, etc.) — not a continuous distribution. "
        "Cohorts at the high end overstate typical experience; cohorts at the low end "
        "may understate brand-wide stability. Use the tier values as scenarios, "
        "not as percentiles."
    )


# -----------------------------------------------------------------------------
# fee_benchmark_callout — flags when royalty/marketing is materially above
# or below the industry median in our DB
# -----------------------------------------------------------------------------

def industry_fee_medians(conn, industry: str | None, exclude_franchisor_id: int | None) -> dict:
    """Compute the median royalty% and marketing% across all OTHER brands in
    this industry. Returns {n_peers, royalty_median, marketing_median}.

    Used by fee_benchmark_callout() to decide whether a brand's terms are
    notably above/below market. Live query because the DB grows incrementally
    and we don't want stale snapshots.
    """
    if not industry:
        return {"n_peers": 0, "royalty_median": None, "marketing_median": None}
    rows = conn.execute("""
        SELECT fi.royalty_pct, fi.marketing_fee_pct
        FROM fees_and_investment fi
        JOIN fdds d ON d.id = fi.fdd_id
            AND d.id = (SELECT MAX(d2.id) FROM fdds d2 WHERE d2.franchisor_id = d.franchisor_id)
        JOIN franchisors fr ON fr.id = d.franchisor_id
        WHERE fr.industry = ? AND fr.id != ?
    """, (industry, exclude_franchisor_id or -1)).fetchall()
    royalties = sorted(r[0] for r in rows if r[0] is not None and r[0] > 0)
    marketings = sorted(r[1] for r in rows if r[1] is not None and r[1] > 0)
    return {
        "n_peers": len(rows),
        "royalty_median": statistics.median(royalties) if royalties else None,
        "marketing_median": statistics.median(marketings) if marketings else None,
    }


def fee_benchmark_callout(brand_fees: dict | None, industry_medians: dict,
                           industry_label: str | None) -> dict | None:
    """When brand's royalty or marketing deviates >25% from category median,
    surface as an info callout. Both above-market AND below-market are
    surfaced — buyers should know either way.

    Returns None when there isn't enough peer data (<3 peers) or the brand's
    fees aren't materially different.
    """
    if not brand_fees or industry_medians.get("n_peers", 0) < 3:
        return None
    deviations = []
    brand_roy = brand_fees.get("royalty_pct")
    med_roy = industry_medians.get("royalty_median")
    if brand_roy and med_roy and brand_roy > 0:
        deviation_pct = (brand_roy - med_roy) / med_roy * 100
        if abs(deviation_pct) >= 25:
            direction = "upper" if deviation_pct > 0 else "lower"
            deviations.append({
                "fee": "royalty",
                "brand_val": brand_roy,
                "peer_median": med_roy,
                "direction": direction,
                "deviation_pct": round(deviation_pct, 0),
            })
    brand_mkt = brand_fees.get("marketing_fee_pct")
    med_mkt = industry_medians.get("marketing_median")
    if brand_mkt and med_mkt and brand_mkt > 0:
        deviation_pct = (brand_mkt - med_mkt) / med_mkt * 100
        if abs(deviation_pct) >= 25:
            direction = "upper" if deviation_pct > 0 else "lower"
            deviations.append({
                "fee": "marketing fee",
                "brand_val": brand_mkt,
                "peer_median": med_mkt,
                "direction": direction,
                "deviation_pct": round(deviation_pct, 0),
            })
    if not deviations:
        return None
    label = industry_label or "category"
    return {
        "industry_label": label,
        "n_peers": industry_medians["n_peers"],
        "deviations": deviations,
    }


# -----------------------------------------------------------------------------
# fdd_age_badge — freshness indicator for the page header
# -----------------------------------------------------------------------------

def fdd_age_badge(filing_year: int | None, current_year: int) -> dict | None:
    """Categorize the source FDD's freshness for the brand-page header.

    Filing year vs. current year:
      0-1y  current   — green
      2y    aging     — yellow
      3+y   stale     — red

    Returns dict with 'tier', 'years_old', 'label', or None when filing_year missing.
    """
    if not filing_year:
        return None
    years_old = max(0, current_year - int(filing_year))
    if years_old <= 1:
        tier = "current"
        label = "Current FDD"
    elif years_old == 2:
        tier = "aging"
        label = f"FDD is {years_old} years old"
    else:
        tier = "stale"
        label = f"FDD is {years_old} years old"
    return {"tier": tier, "years_old": years_old, "label": label,
            "filing_year": filing_year}

def item20_disclosure_warning(outlet_summary: list[dict] | None) -> str | None:
    """When Item 20 yearly summary has 1-2 years of data, surface that as a
    limitation. A 2-point chart isn't a trend — it's a snapshot pair. Buyers
    should know before drawing conclusions.

    Returns warning_html string or None (no warning needed when ≥3 years).
    """
    if not outlet_summary:
        return None
    n_years = len(outlet_summary)
    if n_years >= 3:
        return None
    if n_years == 1:
        return ("<strong>Limited Item 20 disclosure.</strong> "
                "Only one year of outlet-growth data reported — no trend "
                "is visible from a single point. Compare against the franchisor "
                "directly or ask current franchisees how the system has grown.")
    return ("<strong>Limited Item 20 disclosure.</strong> "
            "Only two years of outlet-growth data reported — that's a year-over-year "
            "delta, not a trend. Newer franchises and recently re-filed FDDs often "
            "show this; revisit when more years are disclosed.")


# -----------------------------------------------------------------------------
# worst_performer_callout — surfaces negative low values in Item 19
# -----------------------------------------------------------------------------

# Profit-shaped metric names — a negative low value here means an actual loss.
# Revenue (gross_sales / total_revenue) can be "low" without indicating a loss;
# we only surface losses on profit metrics.
_PROFIT_METRIC_NAMES = ("net_profit", "gross_profit", "ebitda", "operating_profit")


def worst_performer_callout(item19_records: list[dict]) -> dict | None:
    """If Item 19 includes a profit metric with a NEGATIVE low value, surface
    it. A franchisee reporting a loss is the most journalistically important
    number on the page — most franchise sites hide this; we surface it.

    Returns dict or None:
        {
          "loss_amount":   int,            # absolute dollar loss
          "metric":        str,            # human label ("net profit", "gross profit", etc.)
          "year":          int | None,
          "cohort":        str,
          "outlet_count":  int | None,     # total outlets in the cohort
          "html":          str,            # rendered callout HTML
        }
    """
    candidates = []
    for r in item19_records:
        if r.get("metric_name") not in _PROFIT_METRIC_NAMES:
            continue
        vmin = r.get("value_min")
        if vmin is None or vmin >= 0:
            continue
        if _is_unit_or_market_metric(r):
            continue
        candidates.append(r)
    if not candidates:
        return None
    # Pick the most extreme loss (most negative value_min)
    worst = min(candidates, key=lambda r: r["value_min"])
    loss_amount = int(round(abs(worst["value_min"])))
    metric_label = (worst.get("metric_raw") or worst.get("metric_name", "profit")).lower()
    # Extract year from reporting_period if present
    year = worst.get("reporting_year")
    if year is None and worst.get("reporting_period"):
        m = re.search(r"\b(20\d{2})\b", str(worst["reporting_period"]))
        if m:
            year = int(m.group(1))
    cohort = (worst.get("cohort_raw") or "").strip()
    outlet_count = worst.get("outlet_count")
    high = worst.get("value_max")
    high_str = f"${int(round(high)):,}" if high and high > 0 else None

    # Build the callout HTML
    parts = [
        f"<strong>The worst-performing outlet in this Item 19 cohort reported a "
        f"<span class=\"loss-amount\">${loss_amount:,} loss</span>"
    ]
    if metric_label and "profit" in metric_label:
        parts.append(f" on {metric_label}")
    if year:
        parts.append(f" in {year}")
    parts.append(".</strong>")
    if high_str:
        parts.append(f" The best in the same cohort reported {high_str}.")
    parts.append(" Averages hide outcome variance — the floor is where unit economics fail, "
                 "and it's worth understanding what separates the bottom outlets from the rest "
                 "before signing.")
    return {
        "loss_amount": loss_amount,
        "metric": metric_label,
        "year": year,
        "cohort": cohort,
        "outlet_count": outlet_count,
        "html": "".join(parts),
    }


# -----------------------------------------------------------------------------
# calc_default_revenue
# -----------------------------------------------------------------------------

def calc_default_revenue(item19_records: list[dict],
                          fees: dict | None,
                          *,
                          nice_round_fn,
                          ) -> dict:
    """The calculator's default revenue value + honest source label.

    Returns:
        {
          "value":         int | None,    # nice-rounded; None when no signal
          "source":        "franchised-median" | "any-cohort-median" |
                           "investment-heuristic" | None,
          "honest_label":  str,           # for the hint text under the input
        }

    When value is None, the template should render the input EMPTY with a
    placeholder like "enter your estimate" — never fall back to a hardcoded
    \$500k placeholder that looks like real data (Mastercare bug).
    """
    # Layer 1: franchised broad-cohort median
    franchised = franchised_revenue_distribution(item19_records)
    if franchised:
        return {
            "value": nice_round_fn(statistics.median(franchised)),
            "source": "franchised-median",
            "honest_label": f"Median of {len(franchised)} broad franchised cohort"
                            + ("s" if len(franchised) != 1 else "")
                            + " in this FDD",
        }
    # Layer 2: any-cohort median (excludes company-owned, includes performance-anchored)
    any_revs = any_revenue_distribution(item19_records)
    if any_revs:
        return {
            "value": nice_round_fn(statistics.median(any_revs)),
            "source": "any-cohort-median",
            "honest_label": f"Median across {len(any_revs)} disclosed cohort"
                            + ("s" if len(any_revs) != 1 else "")
                            + " — no broad-cohort data, so this is the best signal available",
        }
    # Layer 3: heuristic from investment IF investment is large enough that
    # 30% gives a meaningful number
    inv_low = fees.get("total_investment_low") if fees else None
    inv_high = fees.get("total_investment_high") if fees else None
    if inv_low and inv_high:
        inv_mid = (inv_low + inv_high) / 2
        if inv_mid >= 500_000:
            return {
                "value": nice_round_fn(inv_mid * 0.30),
                "source": "investment-heuristic",
                "honest_label": "Rough heuristic — no Item 19 disclosed. "
                                "30% of investment midpoint. Replace with a real estimate.",
            }
    # No signal — caller renders empty input with placeholder
    return {
        "value": None,
        "source": None,
        "honest_label": "No Item 19 disclosed. Enter a revenue figure you can "
                        "justify from franchisee validation calls or industry data.",
    }
