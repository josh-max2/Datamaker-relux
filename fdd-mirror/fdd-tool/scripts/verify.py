"""Independent oracle check: do Yale's pages 1-22 (analysis) cite the same numbers
my extractor pulled from pages 87-89 (Crumbl FDD body)? Also check the '140 outlets' anomaly."""
import re
from pathlib import Path
import pypdf

reader = pypdf.PdfReader(str(Path("data/crumbl_yale.pdf")))
yale_text = "\n".join((reader.pages[i].extract_text() or "") for i in range(22))  # Yale pages 1-22
full_text = "\n".join((reader.pages[i].extract_text() or "") for i in range(len(reader.pages)))

# Key numbers from our Item 19 extraction
checks = {
    "324 (cohort size)": ["324"],
    "$1,838,908 (avg revenue)": ["1,838,908", "1838908"],
    "$4,022,090 (high revenue)": ["4,022,090", "4022090"],
    "$298,319 (avg net profit)": ["298,319", "298319"],
    "46.3% (above-avg revenue)": ["46.3", "46%"],
    "47.16% (sample coverage)": ["47.16", "47%"],
}

print("=== Independent oracle check (Yale pages 1-22) ===")
for label, needles in checks.items():
    hits = [n for n in needles if n in yale_text]
    if hits:
        # Show context
        for n in hits:
            idx = yale_text.find(n)
            ctx = yale_text[max(0, idx - 80):idx + 100].replace("\n", " ")
            print(f"  [HIT] {label}: ...{ctx}...")
    else:
        print(f"  [miss] {label}")

print("\n=== '140 outlets' anomaly check (full PDF) ===")
for m in re.finditer(r"\b140\b", full_text):
    idx = m.start()
    ctx = full_text[max(0, idx - 60):idx + 120].replace("\n", " ")
    # only print if context mentions outlets/locations/stores/franchis
    if re.search(r"outlet|location|store|franchis", ctx, re.IGNORECASE):
        print(f"  ...{ctx}...")
