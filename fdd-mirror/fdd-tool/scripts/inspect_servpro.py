"""Deeper investigation of Servpro 2014: does it have an Item 19 at all?"""
import re
import sys
from pathlib import Path
import pypdf

sys.stdout.reconfigure(encoding="utf-8")
reader = pypdf.PdfReader(str(Path("data/servpro_2014.pdf")))

# Look for ANY Item 19 reference, any format
patterns = [
    (r"item\s*19", "item 19 (case-insensitive)"),
    (r"item\s*xix", "item XIX (roman)"),
    (r"financial\s+performance\s+representation", "FPR phrase"),
    (r"earnings\s+claim", "earnings claim (old name for Item 19)"),
    (r"we do not (?:furnish|provide|make).{0,80}financial\s+performance", "no-FPR language"),
    (r"we do not (?:furnish|provide|make).{0,80}earnings\s+claim", "no-earnings-claim language"),
]

for patt, label in patterns:
    print(f"\n--- {label} ---")
    hits = 0
    for i, page in enumerate(reader.pages):
        t = page.extract_text() or ""
        for m in re.finditer(patt, t, re.IGNORECASE):
            ctx = t[max(0, m.start() - 60):m.end() + 80].replace("\n", " ").encode("ascii", "replace").decode("ascii")
            print(f"  p{i+1}: ...{ctx}...")
            hits += 1
            if hits >= 5:
                break
        if hits >= 5:
            break
    if hits == 0:
        print(f"  (no hits)")

# Also dump page 1 TOC area and a middle page
print("\n\n--- p4-5 (TOC area) ---")
for i in range(3, 6):
    if i < len(reader.pages):
        t = (reader.pages[i].extract_text() or "")
        print(f"p{i+1}: {t[:1200].encode('ascii', 'replace').decode('ascii')}")
