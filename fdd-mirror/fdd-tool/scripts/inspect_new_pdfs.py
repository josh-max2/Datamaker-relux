"""Quick sanity check on newly-downloaded PDFs."""
from pathlib import Path
import re
import pypdf

for name in ["molly_maid_panda.pdf", "service_experts_mn.pdf"]:
    p = Path("data") / name
    if not p.exists():
        print(f"\n!!! {name} not found")
        continue
    reader = pypdf.PdfReader(str(p))
    n = len(reader.pages)
    print(f"\n========== {name} ({n} pages, {p.stat().st_size/1024:.1f} KB) ==========")
    # Dump first page
    print("--- p1 (first 500 chars) ---")
    print((reader.pages[0].extract_text() or "")[:500])
    # Look for FDD body markers and Item 19
    full = "\n".join((reader.pages[i].extract_text() or "") for i in range(n))
    print(f"\n'FRANCHISE DISCLOSURE DOCUMENT' hits: {len(re.findall(r'FRANCHISE\s+DISCLOSURE\s+DOCUMENT', full, re.I))}")
    print(f"'ITEM 19' hits: {len(re.findall(r'ITEM\s+19', full, re.I))}")
    print(f"'FINANCIAL PERFORMANCE' hits: {len(re.findall(r'FINANCIAL\s+PERFORMANCE', full, re.I))}")
    # Find Item 19 page if present
    for i, page in enumerate(reader.pages):
        t = page.extract_text() or ""
        if re.search(r"ITEM\s+19\s+FINANCIAL\s+PERFORMANCE", t, re.I):
            print(f"  Item 19 heading at page {i+1}")
            break
