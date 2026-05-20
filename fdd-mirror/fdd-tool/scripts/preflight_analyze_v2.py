"""Real preflight test: can the section finder locate the items the pipeline needs?

A PDF passes if find_section returns valid ranges for at least Items 5, 6, 7, AND
either 19 or 20. That's the operational gate for the extraction pipeline.

Failures are candidates for OCR preprocessing.
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")  # so `from src import ...` works when run from fdd-tool/

from src import pdf_utils

NEEDED = [5, 6, 7, 19, 20]


def test_pdf(path: Path) -> dict:
    pages = pdf_utils.extract_pages(path)
    body_start = pdf_utils.find_fdd_body_start(pages)
    found: dict[int, tuple[int, int] | None] = {}
    for item in NEEDED:
        found[item] = pdf_utils.find_section(pages, item, body_start_page=body_start)
    n_found = sum(1 for v in found.values() if v)
    # Operational gate: must find at least 5, 6, 7 AND (19 or 20)
    must_have = found[5] and found[6] and found[7]
    nice_to_have = found[19] or found[20]
    operational = bool(must_have and nice_to_have)
    return {
        "total_pages": len(pages),
        "body_start": body_start,
        "items_found": n_found,
        "items_found_detail": {f"item{k}": (v if v else "MISSING") for k, v in found.items()},
        "operational_pass": operational,
    }


def bucket(info: dict) -> str:
    n = info["items_found"]
    if info["operational_pass"]:
        return "born_digital"  # pipeline can run on this PDF
    if n >= 2:
        return "partial"  # some items found, OCR could rescue the rest
    return "fully_scanned"  # nothing found, needs OCR before pipeline can touch it


preflight_dir = Path("data/preflight")
validated_dir = Path("data")
results: dict[str, dict] = {}

for pdf in sorted(preflight_dir.glob("*.pdf")):
    print(f"Testing {pdf.name}...")
    results[pdf.name] = test_pdf(pdf)

for name in ["crumbl_yale.pdf", "service_experts_mn.pdf", "rebath_2025_mn.pdf", "servpro_2014.pdf"]:
    p = validated_dir / name
    if p.exists():
        print(f"Testing (validated) {name}...")
        results[f"_v_{name}"] = test_pdf(p)

print("\n" + "=" * 90)
print(f"{'PDF':<42} {'Pages':>6} {'Items':>6} {'Pass':>6} {'Bucket':<14}")
print("=" * 90)
preflight_b = {"born_digital": 0, "partial": 0, "fully_scanned": 0}
for name, info in sorted(results.items()):
    b = bucket(info)
    pass_str = "Y" if info["operational_pass"] else "N"
    print(f"{name:<42} {info['total_pages']:>6} {info['items_found']:>6} {pass_str:>6} {b:<14}")
    if not name.startswith("_v_"):
        preflight_b[b] += 1

print("\n" + "=" * 90)
print("PREFLIGHT SAMPLE (19 modern MN-filed FDDs):")
total = sum(preflight_b.values())
for b, c in preflight_b.items():
    pct = c / total * 100 if total else 0
    print(f"  {b:<15} {c:>3} / {total}  ({pct:.1f}%)")

print("\nValidated PDFs (sanity check):")
for name, info in sorted(results.items()):
    if name.startswith("_v_"):
        b = bucket(info)
        pass_str = "OK" if info["operational_pass"] else "FAIL"
        missing = [k for k, v in info["items_found_detail"].items() if v == "MISSING"]
        print(f"  {name}: {b} [{pass_str}] - missing: {missing}")

print("\nFailures from preflight sample (items that section-finder missed):")
for name, info in sorted(results.items()):
    if name.startswith("_v_"): continue
    missing = [k for k, v in info["items_found_detail"].items() if v == "MISSING"]
    if missing:
        print(f"  {name}: missing {missing}")
