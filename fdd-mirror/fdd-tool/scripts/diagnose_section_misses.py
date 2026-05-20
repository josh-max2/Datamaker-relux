"""Find out why find_section missed Items 19/20 for JDog and Two Men."""
import re
import sys
from pathlib import Path

import pypdf

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from src import pdf_utils

for pdf_name in ["jdog_junk_removal_hauling_id639762.pdf", "two_men_and_a_junk_truck_id641608.pdf"]:
    p = Path("data/wi_scrape") / pdf_name
    print(f"\n========== {pdf_name} ==========")
    reader = pypdf.PdfReader(str(p))
    n = len(reader.pages)
    print(f"  total pages: {n}")

    # Find any line containing ITEM 19 or Item 19 anywhere
    print(f"\n  All 'ITEM 19' / 'Item 19' line-level matches:")
    for i, page in enumerate(reader.pages):
        t = page.extract_text() or ""
        # Look line by line
        for line in t.split("\n"):
            if re.search(r"\bITEM\s*19\b", line, re.IGNORECASE):
                s = line.strip().encode("ascii", "replace").decode("ascii")[:120]
                print(f"    p{i+1}: {s!r}")

    # Same for ITEM 20
    print(f"\n  All 'ITEM 20' line matches:")
    for i, page in enumerate(reader.pages):
        t = page.extract_text() or ""
        for line in t.split("\n"):
            if re.search(r"\bITEM\s*20\b", line, re.IGNORECASE):
                s = line.strip().encode("ascii", "replace").decode("ascii")[:120]
                print(f"    p{i+1}: {s!r}")

    # And for the canonical Item 19 phrase
    print(f"\n  'FINANCIAL PERFORMANCE' line matches:")
    for i, page in enumerate(reader.pages):
        t = page.extract_text() or ""
        for line in t.split("\n"):
            if re.search(r"FINANCIAL\s+PERFORMANCE", line, re.IGNORECASE):
                s = line.strip().encode("ascii", "replace").decode("ascii")[:120]
                print(f"    p{i+1}: {s!r}")

    # And what find_section actually returns
    pages = pdf_utils.extract_pages(p)
    body_start = pdf_utils.find_fdd_body_start(pages)
    print(f"\n  find_fdd_body_start: page {body_start}")
    for item in (5, 6, 7, 19, 20):
        sec = pdf_utils.find_section(pages, item, body_start_page=body_start)
        print(f"  find_section({item}): {sec}")
