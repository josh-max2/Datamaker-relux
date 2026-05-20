"""Look at the 31 records still classified as cohort_name='other' to see if we need
another enum value (after performance_anchored was added)."""
import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

manifest = json.loads(Path("output/_pilot_wi_home_services.json").read_text(encoding="utf-8"))
seen_other = []
for brand, e in manifest.items():
    pa = e.get("phase_a", {})
    if pa.get("status") != "ok":
        continue
    pdf_stem = Path(pa["pdf_path"]).stem
    item19 = Path("output") / pdf_stem / "item19_fpr.json"
    if not item19.exists():
        continue
    try:
        d = json.loads(item19.read_text(encoding="utf-8"))
    except Exception:
        continue
    for r in d.get("records", []):
        if r.get("cohort_name") == "other":
            seen_other.append((brand, r.get("cohort_raw", "")[:120], r.get("metric_raw", "")[:60]))

# Group by cohort_raw similarity (just print all, grouped by brand)
by_brand = {}
for b, c, m in seen_other:
    by_brand.setdefault(b, []).append((c, m))

print(f"=== {len(seen_other)} records classified as cohort_name='other' across {len(by_brand)} brands ===\n")
for brand, recs in by_brand.items():
    print(f"\n--- {brand} ({len(recs)} other-records) ---")
    distinct = {(c, m) for c, m in recs}
    for c, m in sorted(distinct):
        print(f"    cohort: {c!r}")
        print(f"    metric: {m!r}")
