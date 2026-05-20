"""Locate where the actual Crumbl FDD starts inside the Yale combo PDF, and find Item 19's page range."""
import re
from pathlib import Path

import pypdf

pdf_path = Path("data/crumbl_yale.pdf")
reader = pypdf.PdfReader(str(pdf_path))
n = len(reader.pages)
print(f"Total pages: {n}")

texts = [(reader.pages[i].extract_text() or "") for i in range(n)]

# Find FDD cover-page candidates
COVER_RE = re.compile(r"FRANCHISE DISCLOSURE DOCUMENT", re.IGNORECASE)
print("\n--- Pages containing 'FRANCHISE DISCLOSURE DOCUMENT' ---")
for i, t in enumerate(texts):
    if COVER_RE.search(t):
        print(f"  p{i+1}: {t[:120].strip()[:120]!r}")

# Find pages that look like Item 19 section START (heading line, not a cross-reference)
# Pattern: line that begins with "ITEM 19" optionally followed by a header label
ITEM19_HEAD_RE = re.compile(r"(?m)^\s*ITEM\s+19\b.{0,80}", re.IGNORECASE)
ITEM20_HEAD_RE = re.compile(r"(?m)^\s*ITEM\s+20\b.{0,80}", re.IGNORECASE)

print("\n--- 'ITEM 19' line matches (page: matched text) ---")
for i, t in enumerate(texts):
    for m in ITEM19_HEAD_RE.finditer(t):
        snippet = m.group(0).strip()[:90]
        print(f"  p{i+1}: {snippet!r}")

print("\n--- 'ITEM 20' line matches ---")
for i, t in enumerate(texts):
    for m in ITEM20_HEAD_RE.finditer(t):
        snippet = m.group(0).strip()[:90]
        print(f"  p{i+1}: {snippet!r}")

# Look for "FINANCIAL PERFORMANCE REPRESENTATIONS" which is Item 19's canonical heading
FPR_RE = re.compile(r"FINANCIAL\s+PERFORMANCE\s+REPRESENTATIONS?", re.IGNORECASE)
print("\n--- Pages with 'FINANCIAL PERFORMANCE REPRESENTATION' ---")
for i, t in enumerate(texts):
    if FPR_RE.search(t):
        print(f"  p{i+1}")
