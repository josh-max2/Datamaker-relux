"""Audit extraction data quality and accuracy.

Five checks per brand:
  1. SCHEMA: all expected files exist and parse as JSON (no _read_error sentinels).
  2. RANGE: numeric fields fall within plausible bounds (e.g., royalty 0-15%).
  3. CONSISTENCY: cross-field invariants hold (e.g., inv_low <= inv_high).
  4. PDF VERIFY: each item's raw_excerpt is actually present in the PDF source text.
  5. CONFIDENCE: aggregate any confidence < 0.7 flags.

Spot-check (PDF verify) runs on a sample to keep runtime reasonable; --all for full pass.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from src import pdf_utils

OUTPUT_DIR = Path("output")
DATA_DIR = Path("data")

# Plausible numeric ranges (None = no bound).
# Bounds are wide enough to NOT flag legit-but-extreme cases:
# - Hotel/hospitality franchises legitimately invest $15-25M
# - High-marketing categories (painting, junk removal) can exceed 10% marketing
# - Master franchises run $250k+ initial fees (e.g. Alair Homes)
RANGES = {
    "initial_franchise_fee_low":  (0,    1_000_000),
    "initial_franchise_fee_high": (0,    1_000_000),
    "total_investment_low":       (1_000, 25_000_000),
    "total_investment_high":      (1_000, 25_000_000),
    "liquid_capital_required":    (0,     10_000_000),
    "net_worth_required":         (0,     50_000_000),
    "royalty_pct":                (0,     25),
    "marketing_fee_pct":          (0,     15),
    "tech_fee_monthly":           (0,     10_000),
}

EXPECTED_FILES = [
    "metadata.json",
    "item5_initial_fee.json",
    "item6_ongoing_fees.json",
    "item7_investment.json",
    "item19_fpr.json",
    "item20_outlets.json",
]


def load_json(path: Path):
    if not path.exists():
        return None, "missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None, "parse_error"
    if "_read_error" in data or "_partial" in data:
        return data, "read_error"
    if "_parse_error" in data:
        return data, "parse_error"
    return data, "ok"


def find_pdf(stem: str) -> Path | None:
    for sub in ("wi_scrape", "preflight", ""):
        p = DATA_DIR / sub / f"{stem}.pdf" if sub else DATA_DIR / f"{stem}.pdf"
        if p.exists():
            return p
    for p in DATA_DIR.rglob(f"{stem}.pdf"):
        return p
    return None


def normalize_for_match(s: str) -> str:
    """Loose match: collapse whitespace, lowercase, strip punctuation noise."""
    return re.sub(r"\s+", " ", s.lower()).strip()


def check_range(label: str, val, lo, hi) -> str | None:
    if val is None:
        return None
    try:
        v = float(val)
    except (TypeError, ValueError):
        return f"{label}={val!r} not numeric"
    if lo is not None and v < lo:
        return f"{label}={val} below lower bound {lo}"
    if hi is not None and v > hi:
        return f"{label}={val} above upper bound {hi}"
    return None


def audit_brand(stem: str, do_pdf_verify: bool) -> dict:
    d = OUTPUT_DIR / stem
    issues = []
    flags = []
    warnings = []

    # 1. SCHEMA — all files exist
    extracted = {}
    for fname in EXPECTED_FILES:
        data, status = load_json(d / fname)
        if status == "missing":
            issues.append(f"missing: {fname}")
            extracted[fname] = None
            continue
        if status == "read_error":
            issues.append(f"read_error: {fname}")
            extracted[fname] = None
            continue
        if status == "parse_error":
            issues.append(f"parse_error: {fname}")
            extracted[fname] = None
            continue
        extracted[fname] = data

    item5 = extracted.get("item5_initial_fee.json") or {}
    item6 = extracted.get("item6_ongoing_fees.json") or {}
    item7 = extracted.get("item7_investment.json") or {}
    item19 = extracted.get("item19_fpr.json") or {}
    item20 = extracted.get("item20_outlets.json") or {}

    # 2. RANGE
    for label, (lo, hi) in RANGES.items():
        for src in (item5, item6, item7):
            if label in src:
                err = check_range(label, src.get(label), lo, hi)
                if err:
                    issues.append(err)
                break

    # 3. CONSISTENCY
    fee_lo = item5.get("initial_franchise_fee_low")
    fee_hi = item5.get("initial_franchise_fee_high")
    if fee_lo is not None and fee_hi is not None and fee_lo > fee_hi:
        issues.append(f"fee_low ({fee_lo}) > fee_high ({fee_hi})")
    inv_lo = item7.get("total_investment_low")
    inv_hi = item7.get("total_investment_high")
    if inv_lo is not None and inv_hi is not None and inv_lo > inv_hi:
        issues.append(f"inv_low ({inv_lo}) > inv_high ({inv_hi})")
    if item19.get("has_item19") and not item19.get("records"):
        warnings.append("has_item19=true but no records")
    if item19.get("records") and not item19.get("has_item19"):
        warnings.append("records present but has_item19=false")

    # 4. CONFIDENCE flags (anything < 0.7)
    for src_name, src in (("item5", item5), ("item6", item6), ("item7", item7), ("item19", item19)):
        c = src.get("confidence")
        if isinstance(c, (int, float)) and c < 0.7:
            flags.append(f"{src_name}.confidence={c}")

    # 5. PDF SPOT-CHECK — verify raw_excerpt is in the PDF section text
    pdf_verified = None
    pdf_failed = []
    if do_pdf_verify:
        pdf = find_pdf(stem)
        if not pdf or not pdf.exists():
            warnings.append("PDF not found for spot-check")
        else:
            try:
                pages = pdf_utils.extract_pages(pdf)
                full_text = normalize_for_match(" ".join(p.text for p in pages))
                pdf_verified = []
                checks = [
                    ("item5_excerpt", item5.get("raw_excerpt")),
                    ("item7_excerpt", item7.get("raw_excerpt")),
                ]
                for label, excerpt in checks:
                    if not excerpt or not isinstance(excerpt, str):
                        continue
                    # Use first 40 chars of excerpt for loose match
                    needle = normalize_for_match(excerpt[:40])
                    if needle and needle in full_text:
                        pdf_verified.append(label)
                    elif needle:
                        # Try a shorter sub-needle for robustness against minor LLM rewrites
                        short = normalize_for_match(excerpt[:25])
                        if short and short in full_text:
                            pdf_verified.append(label + "(partial)")
                        else:
                            pdf_failed.append(label)
            except Exception as e:
                warnings.append(f"PDF verify error: {e}")

    return {
        "stem": stem,
        "issues": issues,
        "warnings": warnings,
        "confidence_flags": flags,
        "pdf_verified": pdf_verified,
        "pdf_failed": pdf_failed,
        "has_item19": item19.get("has_item19"),
        "n_item19_records": len(item19.get("records") or []),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=15, help="brands to PDF-verify (default 15)")
    ap.add_argument("--all", action="store_true", help="PDF-verify all brands")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    brands = sorted(d.name for d in OUTPUT_DIR.iterdir()
                    if d.is_dir() and not d.name.startswith("_"))
    print(f"=== DATA QUALITY AUDIT ({len(brands)} brands) ===\n")

    random.seed(args.seed)
    if args.all:
        verify_set = set(brands)
    else:
        verify_set = set(random.sample(brands, min(args.sample, len(brands))))
    print(f"PDF spot-check sample: {len(verify_set)} brands\n")

    results = []
    for stem in brands:
        r = audit_brand(stem, do_pdf_verify=(stem in verify_set))
        results.append(r)

    # Aggregate
    n = len(results)
    n_issues = sum(1 for r in results if r["issues"])
    n_warnings = sum(1 for r in results if r["warnings"])
    n_confidence = sum(1 for r in results if r["confidence_flags"])
    issue_types: Counter = Counter()
    for r in results:
        for i in r["issues"]:
            key = i.split(":")[0].split("=")[0].strip()
            issue_types[key] += 1

    print("--- Aggregate ---")
    print(f"  brands w/ issues:           {n_issues}/{n}")
    print(f"  brands w/ warnings:         {n_warnings}/{n}")
    print(f"  brands w/ low-confidence:   {n_confidence}/{n}")
    print(f"\n  issue type breakdown:")
    for k, v in issue_types.most_common():
        print(f"    {v:3d}  {k}")

    # Item 19 stats
    n_item19_true = sum(1 for r in results if r["has_item19"])
    n_item19_records = sum(r["n_item19_records"] for r in results)
    print(f"\n--- Item 19 ---")
    print(f"  has_item19=true brands:     {n_item19_true}/{n}")
    print(f"  total Item 19 records:      {n_item19_records}")

    # PDF verify
    verified = [r for r in results if r["pdf_verified"] is not None]
    pdf_pass = sum(1 for r in verified
                   if r["pdf_verified"] and not r["pdf_failed"])
    pdf_partial = sum(1 for r in verified
                      if r["pdf_verified"] and r["pdf_failed"])
    pdf_fail_only = sum(1 for r in verified
                        if not r["pdf_verified"] and r["pdf_failed"])
    print(f"\n--- PDF spot-check (raw_excerpt → source text) ---")
    print(f"  sample size:                {len(verified)}")
    print(f"  fully verified:             {pdf_pass}")
    print(f"  partially verified:         {pdf_partial}")
    print(f"  no excerpts matched:        {pdf_fail_only}")
    if verified:
        rate = (pdf_pass + pdf_partial) / len(verified) * 100
        print(f"  verification rate:          {rate:.1f}%")

    # Worst offenders (most issues)
    worst = sorted(results, key=lambda r: -len(r["issues"]))[:10]
    print(f"\n--- Top 10 brands with most issues ---")
    for r in worst:
        if not r["issues"]:
            break
        print(f"  {r['stem']}: {len(r['issues'])} issues")
        for i in r["issues"][:3]:
            print(f"      {i}")

    # PDF verify failures (cases where excerpt didn't match source)
    pdf_fail_brands = [r for r in verified if r["pdf_failed"]]
    if pdf_fail_brands:
        print(f"\n--- PDF spot-check FAILS ({len(pdf_fail_brands)}) ---")
        for r in pdf_fail_brands[:10]:
            print(f"  {r['stem']}: missed={r['pdf_failed']}, verified={r['pdf_verified']}")

    print()


if __name__ == "__main__":
    main()
