"""Site-wide DATA audit. Runs across all brands. Two tiers:

  TIER 1 — invariants that must hold. Any FAIL blocks deploy.
  TIER 2 — warnings worth surfacing but not blocking.

Wired into site_gen.main() at the end of the build. Also runnable standalone:
    python scripts/audit_data.py              # full report
    python scripts/audit_data.py --quiet      # only failures
    python scripts/audit_data.py --json out/  # write per-brand JSON

Exit code:
  0  no tier-1 failures
  1  one or more tier-1 failures (deploy blocked)
"""
from __future__ import annotations
import argparse
import importlib
import json
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import site_gen as sg
from src import derived
from src.db import DB_PATH

importlib.reload(sg)
importlib.reload(derived)


# ----------------------------------------------------------------------------
# Tier 1 invariants — block deploy if any fail
# ----------------------------------------------------------------------------

def check_has_item19_consistency(conn) -> list[dict]:
    """fdds.has_item19 must match whether item19_records exists."""
    out = []
    rows = conn.execute("""
        SELECT fr.slug, d.has_item19,
               (SELECT COUNT(*) FROM item19_records WHERE fdd_id=d.id) AS n_records
        FROM fdds d JOIN franchisors fr ON fr.id=d.franchisor_id
        WHERE d.id=(SELECT MAX(d2.id) FROM fdds d2 WHERE d2.franchisor_id=fr.id)
    """).fetchall()
    for r in rows:
        flag, n = bool(r["has_item19"]), r["n_records"]
        if flag != (n > 0):
            out.append({
                "tier": 1, "check": "has_item19_consistency", "slug": r["slug"],
                "detail": f"flag={flag} but n_records={n}",
            })
    return out


def check_item19_value_consistency(conn) -> list[dict]:
    """value_avg and value_median must be within [value_min, value_max] when all present."""
    out = []
    rows = conn.execute("""
        SELECT i.id, fr.slug, i.cohort_raw,
               i.value_min, i.value_median, i.value_avg, i.value_max
        FROM item19_records i
        JOIN fdds d ON d.id=i.fdd_id
        JOIN franchisors fr ON fr.id=d.franchisor_id
        WHERE i.value_min IS NOT NULL AND i.value_max IS NOT NULL
    """).fetchall()
    for r in rows:
        vmin, vmax = r["value_min"], r["value_max"]
        for label, v in (("value_avg", r["value_avg"]), ("value_median", r["value_median"])):
            if v is not None and not (vmin <= v <= vmax):
                out.append({
                    "tier": 1, "check": f"item19_{label}_in_bounds", "slug": r["slug"],
                    "detail": f"record={r['id']} cohort={(r['cohort_raw'] or '')[:40]!r} "
                              f"min={vmin} {label}={v} max={vmax}",
                })
    return out


def check_fees_bounds(conn) -> list[dict]:
    """Royalty in [0,25], marketing in [0,15], investment_low <= investment_high."""
    out = []
    rows = conn.execute("""
        SELECT fr.slug, fi.*
        FROM fees_and_investment fi
        JOIN fdds d ON d.id=fi.fdd_id
        JOIN franchisors fr ON fr.id=d.franchisor_id
        WHERE d.id=(SELECT MAX(d2.id) FROM fdds d2 WHERE d2.franchisor_id=fr.id)
    """).fetchall()
    for r in rows:
        if r["royalty_pct"] is not None and not (0 <= r["royalty_pct"] <= 25):
            out.append({"tier": 1, "check": "royalty_pct_bounds", "slug": r["slug"],
                        "detail": f"royalty_pct={r['royalty_pct']}"})
        if r["marketing_fee_pct"] is not None and not (0 <= r["marketing_fee_pct"] <= 15):
            out.append({"tier": 1, "check": "marketing_pct_bounds", "slug": r["slug"],
                        "detail": f"marketing_fee_pct={r['marketing_fee_pct']}"})
        if (r["total_investment_low"] is not None and r["total_investment_high"] is not None
                and r["total_investment_low"] > r["total_investment_high"]):
            out.append({"tier": 1, "check": "investment_low_le_high", "slug": r["slug"],
                        "detail": f"low={r['total_investment_low']} > high={r['total_investment_high']}"})
        if (r["initial_franchise_fee_low"] is not None and r["initial_franchise_fee_high"] is not None
                and r["initial_franchise_fee_low"] > r["initial_franchise_fee_high"]):
            out.append({"tier": 1, "check": "franchise_fee_low_le_high", "slug": r["slug"],
                        "detail": f"low={r['initial_franchise_fee_low']} > high={r['initial_franchise_fee_high']}"})
    return out


def check_breakeven_plausibility(conn) -> list[dict]:
    """Any computed breakeven > 50 years means data is broken — should have been
    caught by site_gen's defensive cap. If this fires, the cap regressed."""
    out = []
    for slug, in conn.execute("SELECT fr.slug FROM franchisors fr").fetchall():
        ctx = sg.fetch_brand_detail(conn, slug)
        if not ctx:
            continue
        be = ctx.get("breakeven")
        if be and not be.get("unprofitable"):
            for k in ("low_years", "high_years"):
                v = be.get(k)
                if v is not None and v > 50:
                    out.append({"tier": 1, "check": f"breakeven_{k}_plausible", "slug": slug,
                                "detail": f"{k}={v}"})
    return out


# ----------------------------------------------------------------------------
# Tier 2 warnings
# ----------------------------------------------------------------------------

def check_item19_disclosure_quality(conn) -> list[dict]:
    """Surface brands whose Item 19 is thin / affiliate-only / longitudinal —
    these get a yellow warning callout on the brand page. Audit just tracks
    the count so we can monitor whether it grows with new ingest."""
    out = []
    rows = conn.execute("""
        SELECT fr.slug, d.id AS fdd_id
        FROM franchisors fr
        JOIN fdds d ON d.franchisor_id=fr.id
            AND d.id=(SELECT MAX(d2.id) FROM fdds d2 WHERE d2.franchisor_id=fr.id)
    """).fetchall()
    for r in rows:
        item19 = [dict(x) for x in conn.execute(
            "SELECT * FROM item19_records WHERE fdd_id=?", (r["fdd_id"],)).fetchall()]
        if not item19:
            continue
        q = derived.item19_disclosure_quality(item19)
        if q["kind"] in ("longitudinal_affiliate", "affiliate_only"):
            out.append({"tier": 2, "check": "item19_affiliate_only_disclosure",
                        "slug": r["slug"],
                        "detail": f"kind={q['kind']}  n_affiliate_cohorts={q['n_affiliate_cohorts']}"})
    return out


def check_outlet_breakdown_consistency(conn) -> list[dict]:
    """franchised + company_owned should match total (within 1 outlet rounding)."""
    out = []
    rows = conn.execute("""
        SELECT fr.slug, d.id AS fdd_id
        FROM franchisors fr
        JOIN fdds d ON d.franchisor_id=fr.id
            AND d.id=(SELECT MAX(d2.id) FROM fdds d2 WHERE d2.franchisor_id=fr.id)
    """).fetchall()
    for r in rows:
        yearly = [dict(y) for y in conn.execute(
            "SELECT * FROM item20_locations WHERE fdd_id=? AND state='TOTAL' ORDER BY year",
            (r["fdd_id"],)).fetchall()]
        breakdown = derived.outlet_breakdown_from_item20(yearly)
        t, f, c = breakdown["total_latest"], breakdown["franchised_latest"], breakdown["company_owned_latest"]
        if t is not None and f is not None and c is not None:
            if abs((f + c) - t) > 1:
                out.append({"tier": 2, "check": "outlet_breakdown_sum", "slug": r["slug"],
                            "detail": f"franchised({f}) + co_owned({c}) != total({t}) for year={breakdown['latest_year']}"})
    return out


# ----------------------------------------------------------------------------
# Run all + report
# ----------------------------------------------------------------------------

CHECKS = [
    ("has_item19_consistency", check_has_item19_consistency),
    ("item19_value_consistency", check_item19_value_consistency),
    ("fees_bounds", check_fees_bounds),
    ("breakeven_plausibility", check_breakeven_plausibility),
    ("outlet_breakdown_consistency", check_outlet_breakdown_consistency),
    ("item19_disclosure_quality", check_item19_disclosure_quality),
]


def run_audit(conn) -> dict:
    """Run all checks, return {tier1_fails, tier2_warns} lists."""
    all_findings: list[dict] = []
    for name, fn in CHECKS:
        try:
            all_findings.extend(fn(conn))
        except Exception as e:
            all_findings.append({"tier": 1, "check": name, "slug": "(check itself errored)",
                                  "detail": f"{type(e).__name__}: {e}"})
    return {
        "tier1_fails": [f for f in all_findings if f["tier"] == 1],
        "tier2_warns": [f for f in all_findings if f["tier"] == 2],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true", help="Only print failures.")
    ap.add_argument("--json", help="Write detailed JSON report to this path.")
    ap.add_argument("--db", default=str(DB_PATH))
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    if not args.quiet:
        print("Running site-wide data audit...")
        for name, fn in CHECKS:
            pass  # printed below
    result = run_audit(conn)
    tier1, tier2 = result["tier1_fails"], result["tier2_warns"]

    print(f"\nAUDIT SUMMARY: {len(tier1)} tier-1 FAILS  ·  {len(tier2)} tier-2 WARNs")
    if tier1:
        print("\nTIER 1 FAILS (block deploy):")
        for f in tier1:
            print(f"  [{f['check']}]  {f['slug']}  —  {f['detail']}")
    if tier2 and not args.quiet:
        print("\nTIER 2 WARNs:")
        for f in tier2:
            print(f"  [{f['check']}]  {f['slug']}  —  {f['detail']}")

    if args.json:
        Path(args.json).write_text(json.dumps({
            **result,
            "summary": {"tier1_count": len(tier1), "tier2_count": len(tier2)},
        }, indent=2))
        print(f"\nDetailed JSON: {args.json}")

    return 1 if tier1 else 0


if __name__ == "__main__":
    sys.exit(main())
