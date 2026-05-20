"""Verify Service Experts Item 20 extraction by dumping source pages."""
import sys
from pathlib import Path
import pypdf

sys.stdout.reconfigure(encoding="utf-8")
reader = pypdf.PdfReader(str(Path("data/service_experts_mn.pdf")))

# Item 20 is at PDF pages 63-72 per the extraction run
for i in range(62, 67):
    t = (reader.pages[i].extract_text() or "").encode("ascii", "replace").decode("ascii")
    print(f"\n========== PDF PAGE {i+1} ==========")
    print(t[:3000])
