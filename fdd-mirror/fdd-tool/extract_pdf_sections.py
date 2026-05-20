#!/usr/bin/env python3
import sys
import json

try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader

pdf_path = r"data\wi_scrape\maaco_maaco_collision_repair_auto_painti_id639408.pdf"
reader = PdfReader(pdf_path)

# Extract pages for each section
sections = {
    "cover": [2],
    "item5": list(range(31, 33)),
    "item6": list(range(34, 40)),
    "item7": list(range(39, 45)),
    "item19": list(range(73, 76)),
    "item20": list(range(78, 88))
}

output = {}

for section, pages in sections.items():
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"SECTION: {section}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    all_text = []
    for page_num in pages:
        try:
            page = reader.pages[page_num - 1]
            text = page.extract_text()
            all_text.append(text)
            print(f"--- PAGE {page_num} extracted ---", file=sys.stderr)
        except Exception as e:
            print(f"ERROR on page {page_num}: {e}", file=sys.stderr)
            sys.exit(1)

    output[section] = "\n".join(all_text)

# Write to JSON for processing
with open("extracted_sections.json", "w") as f:
    json.dump(output, f, indent=2)

print("\nExtraction complete. Data in extracted_sections.json", file=sys.stderr)
