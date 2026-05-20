import pdfplumber
import os

pdf_path = "data/wi_scrape/keyrenter_property_management_id641287.pdf"

sections = {
    "cover": (0, 1),
    "item5": (10, 13),
    "item6": (12, 17),
    "item7": (19, 24),
    "item19": (49, 58),
    "item20": (57, 63)
}

os.makedirs("temp_extracts", exist_ok=True)

with pdfplumber.open(pdf_path) as pdf:
    for section, (start, end) in sections.items():
        text = ""
        for page_num in range(start, end):
            if page_num < len(pdf.pages):
                page_text = pdf.pages[page_num].extract_text() or ""
                text += page_text + "\n---PAGE BREAK---\n"

        # Save to temp file
        with open(f"temp_extracts/{section}.txt", "w", encoding="utf-8") as f:
            f.write(text)

        print(f"Extracted {section} ({end-start} pages)")

print("Done")
