"""Criterion #4 check: do any of the 4 PDFs have hypothetical/projection language near Item 19?
If yes, we need to verify the extraction didn't pull those numbers in."""
import re
import sys
from pathlib import Path
import pypdf

sys.stdout.reconfigure(encoding="utf-8")

pdfs = [
    ("crumbl_yale.pdf", 87, 90),       # Item 19 pages from earlier
    ("service_experts_mn.pdf", 63, 63), # very short Item 19 (no FPR)
    ("rebath_2025_mn.pdf", 57, 60),
    ("servpro_2014.pdf", 100, 110),    # rough range from OCR-recovered TOC
]

PATTERNS = [
    r"hypothetic",
    r"projection",
    r"projected",
    r"for\s+illustration",
    r"for\s+example",
    r"example\s+calculation",
    r"pro\s+forma",
    r"forecast",
    r"estimat(?:ed|e)\s+future",
    r"if\s+you\s+(?:were|are)\s+to",
]

for name, p_start, p_end in pdfs:
    p = Path("data") / name
    if not p.exists():
        print(f"\n!!! {name} not found"); continue
    reader = pypdf.PdfReader(str(p))
    print(f"\n========== {name} (Item 19 region: pages {p_start}-{p_end}) ==========")
    region_text = "\n".join((reader.pages[i].extract_text() or "") for i in range(p_start - 1, min(p_end, len(reader.pages))))
    any_hit = False
    for patt in PATTERNS:
        for m in re.finditer(patt, region_text, re.IGNORECASE):
            ctx = region_text[max(0, m.start() - 80):m.end() + 100].replace("\n", " ").encode("ascii", "replace").decode("ascii")
            print(f"  HIT [{patt}]: ...{ctx}...")
            any_hit = True
    if not any_hit:
        print(f"  (no hypothetical/projection language found in this region)")
