#!/usr/bin/env python3
import sys
from pypdf import PdfReader

pdf_path = r"data\wi_scrape\mosquito_shield_id640877.pdf"
reader = PdfReader(pdf_path)

# Extract specific page ranges
ranges = {
    'cover': [0],
    'item5': [11, 12, 13],  # pages 12-14 (0-indexed = 11-13)
    'item6': [13, 14, 15, 16, 17],  # pages 14-18 (0-indexed = 13-17)
    'item7': [17, 18, 19, 20, 21],  # pages 18-22 (0-indexed = 17-21)
    'item19': [45, 46, 47, 48, 49, 50],  # pages 46-51 (0-indexed = 45-50)
    'item20': [50, 51, 52, 53, 54, 55, 56, 57, 58, 59],  # pages 51-60 (0-indexed = 50-59)
}

for section, pages in ranges.items():
    print(f"\n{'='*60}")
    print(f"=== {section.upper()} ===")
    print(f"{'='*60}")
    for page_num in pages:
        try:
            text = reader.pages[page_num].extract_text()
            print(f"\n--- Page {page_num + 1} ---\n{text}\n")
        except Exception as e:
            print(f"Error reading page {page_num + 1}: {e}")
