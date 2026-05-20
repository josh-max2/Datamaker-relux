"""Dump ReBath Item 20 source pages for manual spot-check vs extraction."""
import sys
from pathlib import Path
import json
import pypdf

sys.stdout.reconfigure(encoding="utf-8")
reader = pypdf.PdfReader(str(Path("data/rebath_2025_mn.pdf")))

# Item 20 is at PDF pages 60-67
for i in range(59, 64):
    t = (reader.pages[i].extract_text() or "").encode("ascii", "replace").decode("ascii")
    print(f"\n========== PDF PAGE {i+1} ==========")
    print(t[:2200])

# Print extracted yearly_summary for comparison
data = json.loads(Path("output/rebath_2025_mn/item20_outlets.json").read_text(encoding="utf-8"))
print("\n\n========== EXTRACTED yearly_summary ==========")
for row in data.get("yearly_summary", []):
    print(f"  {row}")

print("\n========== EXTRACTED state_year_status (first 6 rows) ==========")
for row in data.get("state_year_status", [])[:6]:
    print(f"  {row}")

print(f"\nTotal state_year_status rows: {len(data.get('state_year_status', []))}")
