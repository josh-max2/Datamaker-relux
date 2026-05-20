"""Audit the pilot manifest. Surfaces:
  - Per-brand status (scraped? extracted? cost? metadata complete?)
  - Item 19 patterns (records count, has_item19=false rate, cohort_name distribution)
  - Low-confidence flags (any item with confidence <0.7)
  - Parse errors (JSON parse failures from truncated output)
  - Section-not-found rates (find_section misses)
  - Probable scanned-PDF candidates (extraction returned nothing useful)
  - Cost totals + outlier costs

Use after the pilot finishes.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

MANIFEST = Path("output/_pilot_wi_home_services.json")
data = json.loads(MANIFEST.read_text(encoding="utf-8"))

print(f"=== PILOT AUDIT ({len(data)} brands) ===\n")

# Overall scrape + extract status
scrape_status = Counter(e.get("phase_a", {}).get("status", "?") for e in data.values())
extract_status = Counter(e.get("phase_b", {}).get("status", "?") for e in data.values())
print(f"Phase A (scrape) statuses: {dict(scrape_status)}")
print(f"Phase B (extract) statuses: {dict(extract_status)}")

# Cost totals
total_cost = 0.0
costs: list[tuple[str, float]] = []
for brand, e in data.items():
    c_str = e.get("phase_b", {}).get("total_cost_usd")
    if c_str:
        try:
            c = float(c_str)
            costs.append((brand, c))
            total_cost += c
        except ValueError:
            pass
print(f"\nTotal API cost: ${total_cost:.2f}")
if costs:
    avg = total_cost / len(costs)
    print(f"  per FDD avg: ${avg:.3f}  (min ${min(c for _, c in costs):.3f}, max ${max(c for _, c in costs):.3f})")
    top = sorted(costs, key=lambda x: -x[1])[:3]
    print(f"  most expensive: {[(b, f'${c:.3f}') for b, c in top]}")

# Item-level confidence + record stats
print(f"\n--- Item 19 ---")
i19_no = []
i19_yes = []
i19_low_conf = []
all_cohort_names: Counter = Counter()
for brand, e in data.items():
    i19 = e.get("phase_b", {}).get("item19", {})
    if not i19:
        continue
    has = i19.get("has_item19")
    records = i19.get("records", 0)
    conf = i19.get("confidence", 0) or 0
    if has is False:
        i19_no.append(brand)
    else:
        i19_yes.append((brand, records, conf))
    if has and conf < 0.7:
        i19_low_conf.append((brand, conf))
    # Load full file for cohort distribution
    pdf_stem = Path(e.get("phase_a", {}).get("pdf_path", "")).stem if e.get("phase_a", {}).get("pdf_path") else None
    if has and pdf_stem:
        item19_file = Path("output") / pdf_stem / "item19_fpr.json"
        if item19_file.exists():
            try:
                d = json.loads(item19_file.read_text(encoding="utf-8"))
                for r in d.get("records", []):
                    all_cohort_names[r.get("cohort_name", "?")] += 1
            except Exception:
                pass

print(f"  has_item19=false count: {len(i19_no)} ({', '.join(i19_no[:5])}{'...' if len(i19_no) > 5 else ''})")
print(f"  has_item19=true count: {len(i19_yes)}")
if i19_yes:
    avg_records = sum(r for _, r, _ in i19_yes) / len(i19_yes)
    print(f"    avg records per FDD: {avg_records:.1f}  (range {min(r for _, r, _ in i19_yes)} - {max(r for _, r, _ in i19_yes)})")
print(f"  low-confidence Item 19 (<0.7): {i19_low_conf or 'none'}")
print(f"  cohort_name distribution across all records: {dict(all_cohort_names.most_common(10))}")

# Item 20 stats
print(f"\n--- Item 20 ---")
i20_state_rows = []
i20_parse_errors = []
for brand, e in data.items():
    i20 = e.get("phase_b", {}).get("item20", {})
    if not i20:
        continue
    if "parse_error" in i20:
        i20_parse_errors.append((brand, i20["parse_error"][:80]))
    elif "state_rows" in i20:
        i20_state_rows.append((brand, i20["state_rows"]))
print(f"  parse errors: {i20_parse_errors or 'none'}")
if i20_state_rows:
    rows = [r for _, r in i20_state_rows]
    print(f"  state-year rows extracted: total={sum(rows)}  avg={sum(rows)/len(rows):.0f}  range={min(rows)}-{max(rows)}")

# Metadata completeness
print(f"\n--- Metadata ---")
md_issues = []
for brand, e in data.items():
    md = e.get("phase_b", {}).get("metadata", {})
    missing = [k for k in ("legal_name", "state_of_inc", "filing_year", "issuance_date") if not md.get(k)]
    conf = md.get("confidence", 0) or 0
    if missing or conf < 0.7:
        md_issues.append((brand, missing, conf))
print(f"  brands with missing fields or low confidence: {len(md_issues)}")
for brand, missing, conf in md_issues[:5]:
    print(f"    - {brand}: missing={missing} conf={conf}")

# Probable scanned PDFs (low confidence on most items, or many MISSING items)
print(f"\n--- Candidate scanned-PDF outliers ---")
scanned_suspects = []
for brand, e in data.items():
    if e.get("phase_b", {}).get("status") != "ok":
        continue
    pb = e["phase_b"]
    item_confs = [pb.get(f"item{j}", {}).get("confidence", 0) or 0 for j in (5, 6, 7, 19, 20)]
    low_count = sum(1 for c in item_confs if c < 0.7)
    if low_count >= 3:
        scanned_suspects.append((brand, item_confs))
for brand, confs in scanned_suspects:
    print(f"    - {brand}: confidences={confs}")
if not scanned_suspects:
    print(f"  none — pipeline-level confidence is consistently high")

# Dedup hits
print(f"\n--- Dedup ---")
dedup_hits = [(brand, e["phase_a"].get("sha256", "")[:16]) for brand, e in data.items()
              if e.get("phase_a", {}).get("was_duplicate")]
print(f"  duplicate filings caught: {len(dedup_hits)}")
for brand, h in dedup_hits:
    print(f"    - {brand}: sha={h}...")
