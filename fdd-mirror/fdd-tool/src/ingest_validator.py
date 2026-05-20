"""Ingest-time validator. Runs after every replace_item19_records /
replace_item20_locations / replace_fees write in db.py.

Catches issues at write time so they never reach the rendered site. Findings
are logged to a quality_issues table (created on demand) — the audit gate
(scripts/audit_data.py) reads from the same source.

Philosophy:
  - Validators ONLY observe + log; they don't reject writes. A bad ingest
    still lands in the DB so the user can inspect, but it's flagged.
  - Pure functions: given a record list, return a list of issues.
  - Idempotent: clearing + re-flagging on every ingest is fine.
"""
from __future__ import annotations

import sqlite3


# ---------------------------------------------------------------------------
# Pure validators
# ---------------------------------------------------------------------------

def validate_item19_records(fdd_id: int, records: list[dict]) -> list[dict]:
    """Return list of {severity, check, detail} issues for these records.

    Severity:
      "fail"  — mathematically impossible (median > max, etc.)
      "warn"  — suspicious (per-job-shaped value sneaking through)
    """
    issues: list[dict] = []
    for r in records:
        rid = r.get("id") or r.get("metric_name", "?")
        vmin = r.get("value_min")
        vmed = r.get("value_median")
        vavg = r.get("value_avg")
        vmax = r.get("value_max")
        cohort = (r.get("cohort_raw") or r.get("cohort_name") or "")[:40]

        # FAIL: value_median or value_avg outside [min, max]
        if vmin is not None and vmax is not None:
            if vavg is not None and not (vmin <= vavg <= vmax):
                issues.append({
                    "severity": "fail",
                    "check": "value_avg_out_of_bounds",
                    "detail": f"cohort={cohort!r}  min={vmin} avg={vavg} max={vmax}",
                })
            if vmed is not None and not (vmin <= vmed <= vmax):
                issues.append({
                    "severity": "fail",
                    "check": "value_median_out_of_bounds",
                    "detail": f"cohort={cohort!r}  min={vmin} median={vmed} max={vmax}",
                })

        # WARN: suspicious low revenue value with no outlet_count (likely per-X)
        if (r.get("metric_name") in ("gross_sales", "total_revenue")
                and vavg is not None and vavg > 0 and vavg < 25_000
                and r.get("outlet_count") is None):
            issues.append({
                "severity": "warn",
                "check": "suspicious_low_revenue_no_outlet_count",
                "detail": f"cohort={cohort!r}  value_avg={vavg} — likely a per-transaction value",
            })

        # WARN: outlet_count of 0
        if r.get("outlet_count") == 0:
            issues.append({
                "severity": "warn",
                "check": "outlet_count_zero",
                "detail": f"cohort={cohort!r}",
            })

    return issues


def validate_item20_yearly(fdd_id: int, yearly: list[dict], state_year: list[dict]) -> list[dict]:
    """Check Item 20 yearly identity: franchised + company_owned ≈ total."""
    issues: list[dict] = []
    # Reshape yearly rows: {year: {franchised, company_owned, total}}
    by_year: dict[int, dict] = {}
    for r in yearly:
        y = r.get("year")
        if y is None:
            continue
        by_year.setdefault(y, {"franchised": None, "company_owned": None, "total": None})
        ot = r.get("outlet_type")
        if ot in ("franchised", "company-owned", "total"):
            key = ot.replace("-", "_")
            by_year[y][key] = r.get("outlets_end")
    for y, vals in by_year.items():
        f, c, t = vals["franchised"], vals["company_owned"], vals["total"]
        if f is not None and c is not None and t is not None:
            if abs((f + c) - t) > 1:
                issues.append({
                    "severity": "warn",
                    "check": "item20_yearly_identity",
                    "detail": f"year={y}  franchised({f}) + co_owned({c}) != total({t})",
                })
    return issues


def validate_fees(fdd_id: int, fees: dict) -> list[dict]:
    """Bounds + consistency on the fees_and_investment row."""
    issues: list[dict] = []
    if fees.get("royalty_pct") is not None and not (0 <= fees["royalty_pct"] <= 25):
        issues.append({"severity": "fail", "check": "royalty_pct_bounds",
                       "detail": f"royalty_pct={fees['royalty_pct']}"})
    if fees.get("marketing_fee_pct") is not None and not (0 <= fees["marketing_fee_pct"] <= 15):
        issues.append({"severity": "fail", "check": "marketing_pct_bounds",
                       "detail": f"marketing_fee_pct={fees['marketing_fee_pct']}"})
    low, high = fees.get("total_investment_low"), fees.get("total_investment_high")
    if low is not None and high is not None and low > high:
        issues.append({"severity": "fail", "check": "investment_low_gt_high",
                       "detail": f"low={low} > high={high}"})
    flow, fhigh = fees.get("initial_franchise_fee_low"), fees.get("initial_franchise_fee_high")
    if flow is not None and fhigh is not None and flow > fhigh:
        issues.append({"severity": "fail", "check": "franchise_fee_low_gt_high",
                       "detail": f"low={flow} > high={fhigh}"})
    return issues


# ---------------------------------------------------------------------------
# Persistence (the quality_issues table)
# ---------------------------------------------------------------------------

def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS quality_issues (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            fdd_id      INTEGER NOT NULL REFERENCES fdds(id),
            source      TEXT NOT NULL,    -- 'item19' | 'item20' | 'fees'
            severity    TEXT NOT NULL,    -- 'fail' | 'warn'
            check_name  TEXT NOT NULL,
            detail      TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_quality_issues_fdd ON quality_issues(fdd_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_quality_issues_severity ON quality_issues(severity)")


def log_issues(conn: sqlite3.Connection, fdd_id: int, source: str,
               issues: list[dict], replace_prior: bool = True) -> None:
    """Persist issues to quality_issues. If replace_prior, clears prior issues
    from the same fdd+source first (so reruns don't double-log)."""
    if not issues and not replace_prior:
        return
    _ensure_table(conn)
    if replace_prior:
        conn.execute("DELETE FROM quality_issues WHERE fdd_id=? AND source=?",
                     (fdd_id, source))
    for i in issues:
        conn.execute(
            "INSERT INTO quality_issues (fdd_id, source, severity, check_name, detail) "
            "VALUES (?, ?, ?, ?, ?)",
            (fdd_id, source, i["severity"], i["check"], i.get("detail")),
        )
    conn.commit()
