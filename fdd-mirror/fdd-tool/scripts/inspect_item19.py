"""Dump full text of pages 85-92 to find exact Item 19 boundaries in the Crumbl FDD."""
from pathlib import Path
import pypdf

reader = pypdf.PdfReader(str(Path("data/crumbl_yale.pdf")))
for i in range(84, 92):
    txt = reader.pages[i].extract_text() or ""
    print(f"\n========== PDF PAGE {i+1} ==========")
    print(txt[:2500])
