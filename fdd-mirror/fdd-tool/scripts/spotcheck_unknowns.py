"""Spot-check the 3 'unknown' preflight PDFs: do their Item 19 sections contain
real extractable text, or is Item 19 a rasterized image (JPEG-table failure mode)?

If a PDF passes regex section-finding but Item 19 is image-based, the extraction will
return garbage and we'd only notice on actual extraction. This 30-sec check rules
that out cheaply."""
import re
import sys
from pathlib import Path
import pypdf

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from src import pdf_utils

for name in ["unknown_1056.pdf", "unknown_d0a2.pdf", "unknown_e060.pdf"]:
    p = Path("data/preflight") / name
    print(f"\n========== {name} ==========")
    pages = pdf_utils.extract_pages(p)
    body_start = pdf_utils.find_fdd_body_start(pages)
    sec = pdf_utils.find_section(pages, 19, body_start_page=body_start)
    if not sec:
        print(f"  Item 19 not found (shouldn't happen — passed v2)")
        continue
    start, end = sec
    print(f"  Item 19 located: pages {start}-{end}")
    # Dump first content page of Item 19
    p1 = (pages[start - 1].text or "").encode("ascii", "replace").decode("ascii")
    print(f"  --- p{start} first 1400 chars ---")
    print(p1[:1400])
    # Look for table-like content (numbers, $, %) in the section
    section_text = pdf_utils.section_text(pages, start, end)
    n_dollars = len(re.findall(r"\$\s*[\d,]+", section_text))
    n_percents = len(re.findall(r"\d+(?:\.\d+)?\s*%", section_text))
    n_digits = sum(c.isdigit() for c in section_text)
    print(f"\n  Section stats: {len(section_text)} chars, ${n_dollars} dollar amounts, {n_percents} percentages, {n_digits} digits")
    # Verdict: if Item 19 section has <50 chars or no dollar/percent values, likely image-based
    if len(section_text) < 500:
        verdict = "SUSPICIOUS: very short Item 19 — could be image-based"
    elif n_dollars == 0 and n_percents == 0 and "no" not in section_text.lower()[:300]:
        verdict = "SUSPICIOUS: no $/% in Item 19 (possibly all-image table) — needs visual inspection"
    elif n_dollars > 5 or n_percents > 5:
        verdict = "OK: Item 19 has real numeric text"
    else:
        verdict = "OK: Item 19 has text (no quantitative table - probably 'no FPR' case)"
    print(f"  >>> {verdict}")
