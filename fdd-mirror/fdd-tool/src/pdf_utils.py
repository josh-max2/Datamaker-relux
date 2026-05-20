"""PDF helpers: text extraction, FDD section boundary detection, page rasterization."""
from __future__ import annotations

import base64
import io
import re
from dataclasses import dataclass
from pathlib import Path

import pypdf
import pypdfium2 as pdfium

# Canonical FTC-mandated Item titles. The body of the FDD almost always has these
# as inline headers. Using the title (not just "ITEM N") avoids matching TOC entries
# and cross-references — TOCs typically render the number without the full title.
#
# Title patterns use [\s,]+ between words to tolerate stray commas inserted by some
# franchisors (e.g., JDog: "FINANCIAL PERFORMANCE, REPRESENTATIONS").
ITEM_TITLES = {
    1: r"THE FRANCHISOR(?:,?\s+AND\s+ANY\s+PARENTS)?",
    2: r"BUSINESS[\s,]+EXPERIENCE",
    3: r"LITIGATION",
    4: r"BANKRUPTCY",
    5: r"INITIAL[\s,]+FEES?",
    6: r"OTHER[\s,]+FEES",
    7: r"ESTIMATED[\s,]+INITIAL[\s,]+INVESTMENT",
    8: r"RESTRICTIONS[\s,]+ON[\s,]+SOURCES",
    9: r"FRANCHISEE'?S?[\s,]+OBLIGATIONS",
    10: r"FINANCING",
    11: r"FRANCHISOR'?S?[\s,]+ASSISTANCE",
    12: r"TERRITORY",
    13: r"TRADEMARKS",
    14: r"PATENTS",
    15: r"OBLIGATION[\s,]+TO[\s,]+PARTICIPATE",
    16: r"RESTRICTIONS[\s,]+ON[\s,]+WHAT",
    17: r"RENEWAL",
    18: r"PUBLIC[\s,]+FIGURES",
    19: r"FINANCIAL[\s,]+PERFORMANCE[\s,]+REPRESENTATIONS?",
    20: r"OUTLETS[\s,]+AND[\s,]+FRANCHISEE?S?[\s,]+INFORMATION",
    21: r"FINANCIAL[\s,]+STATEMENTS",
    22: r"CONTRACTS",
    23: r"RECEIPTS?",
}

# Separator chars allowed between "ITEM N" and the title. Includes:
#   - common ASCII punctuation: . - : , (also period+space variants)
#   - en-dash (U+2013) and em-dash (U+2014) — often rendered as "?" by pypdf
#     when the PDF's font subset doesn't include them
_ITEM_SEP_CLASS = r"[\.\-:,?–—\s]*"


@dataclass
class PageText:
    page_num: int  # 1-indexed
    text: str


def extract_pages(pdf_path: Path) -> list[PageText]:
    """Return (page_num, text) for every page in the PDF."""
    reader = pypdf.PdfReader(str(pdf_path))
    return [PageText(i + 1, reader.pages[i].extract_text() or "") for i in range(len(reader.pages))]


def find_section(pages: list[PageText], item_num: int, body_start_page: int = 1) -> tuple[int, int] | None:
    """Find the (start_page, end_page) of `item_num` within the FDD body.

    Distinguishes body headings from TOC entries: a TOC page has many ITEM references
    and often dot-leaders; a body page has the heading followed by substantial prose.
    Returns 1-indexed inclusive page range, or None if not found.
    """
    title_pattern = ITEM_TITLES.get(item_num)
    if not title_pattern:
        return None

    start_re = re.compile(rf"\bITEM\s+{item_num}\b{_ITEM_SEP_CLASS}{title_pattern}", re.IGNORECASE)
    item_ref_re = re.compile(r"\bITEM\s+\d{1,2}\b", re.IGNORECASE)
    # Looser fallback A: just "ITEM N" alone on a line (some FDDs put the title
    # on the next line due to layout/wrapping). Anchored to start-of-line so
    # we don't match inline references like "as defined in Item 20...".
    lone_re = re.compile(rf"(?m)^\s*ITEM\s+{item_num}\b\s*$", re.IGNORECASE)
    # Looser fallback B: Famous Dave's-style headings drop the "ITEM" prefix
    # entirely: e.g., "5.  INITIAL FEES". Require the title pattern to follow
    # so we don't false-positive on numbered prose.
    bare_re = re.compile(rf"(?m)^\s*{item_num}\b{_ITEM_SEP_CLASS}{title_pattern}", re.IGNORECASE)

    # TOC heuristic: dot-leaders ("....." 5+ dots in a row) or explicit TOC header.
    # Bare-number TOCs ("5. INITIAL FEES .....") don't have "ITEM N" refs so the
    # item_ref_re count below misses them — this catches those.
    toc_re = re.compile(r"\.{5,}|TABLE\s+OF\s+CONTENTS", re.IGNORECASE)

    candidates: list[tuple[int, int, int, bool]] = []  # (page, other_refs, text_len, is_toc)
    for p in pages:
        if p.page_num < body_start_page:
            continue
        if start_re.search(p.text) or lone_re.search(p.text) or bare_re.search(p.text):
            other_refs = max(0, len(item_ref_re.findall(p.text)) - 1)
            is_toc = bool(toc_re.search(p.text))
            candidates.append((p.page_num, other_refs, len(p.text), is_toc))

    if not candidates:
        return None

    # Body pages have few cross-references (<= 4), substantial content (> 1500 chars),
    # and no TOC markers (dot-leaders, "Table of Contents").
    body_cands = [c for c in candidates if c[1] <= 4 and c[2] > 1500 and not c[3]]
    if body_cands:
        start_page = body_cands[0][0]
    else:
        # Fall back to last candidate — TOC comes before body in standard FDDs.
        start_page = candidates[-1][0]

    # End = start of next ITEM heading after start_page (also body, not TOC)
    next_re = re.compile(rf"\bITEM\s+(\d+)\b{_ITEM_SEP_CLASS}([A-Z][A-Za-z\s,/'’]{{6,}})", re.IGNORECASE)
    end_page = pages[-1].page_num
    for p in pages:
        if p.page_num <= start_page:
            continue
        # Skip TOC-like pages when looking for end boundary
        if len(item_ref_re.findall(p.text)) > 5:
            continue
        for m in next_re.finditer(p.text):
            try:
                next_n = int(m.group(1))
            except ValueError:
                continue
            if next_n > item_num:
                end_page = p.page_num
                break
        if end_page != pages[-1].page_num:
            break

    return (start_page, end_page)


def find_fdd_body_start(pages: list[PageText]) -> int:
    """Find the page where the actual FDD starts (skips academic prefaces like the Yale case)."""
    cover_re = re.compile(r"FRANCHISE\s+DISCLOSURE\s+DOCUMENT", re.IGNORECASE)
    inc_re = re.compile(r"(LLC|Inc\.?|Corporation|Limited)", re.IGNORECASE)
    # Look for a page that has the cover phrase AND a corporate suffix nearby
    for p in pages:
        if cover_re.search(p.text) and inc_re.search(p.text):
            # Heuristic: the cover page is usually short and centered. Yale's case study
            # pages contain the phrase as a title but have lots of body text.
            if len(p.text) < 2500:
                return p.page_num
    return 1


# Cover-page detection regexes (used by find_cover_page)
_COVER_FDD_RE = re.compile(r"FRANCHISE\s+DISCLOSURE\s+DOCUMENT", re.IGNORECASE)
_COVER_CORP_RE = re.compile(r"\b(LLC|L\.L\.C\.|Inc\.?|Incorporated|Corporation|Corp\.?|Limited|Ltd\.?|Company|Co\.|LP|L\.P\.|LLP)\b", re.IGNORECASE)
_COVER_PHONE_RE = re.compile(r"\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}")
_COVER_WEBSITE_RE = re.compile(r"\bwww\.[A-Za-z0-9.-]+\.\w+\b")
_COVER_ZIP_RE = re.compile(r"\b\d{5}(?:-\d{4})?\b")
_COVER_ISSUANCE_RE = re.compile(r"(Issuance|Effective)\s+Date\s*:?", re.IGNORECASE)
_COVER_TOC_RE = re.compile(r"TABLE\s+OF\s+CONTENTS|How\s+to\s+Use\s+This", re.IGNORECASE)


def find_cover_page(pages: list[PageText], scan_first_n: int = 25) -> int:
    """Find the actual FDD cover page (where the legal name, address, and issuance date live).

    Distinct from find_fdd_body_start: the cover comes BEFORE the legal preamble
    (notices, state addenda, "How to Use This Document," TOC). Returns 1-indexed page.

    Scoring among pages 1..scan_first_n:
      +3 "FRANCHISE DISCLOSURE DOCUMENT" present
      +2 corporate suffix present
      +1 phone number
      +1 website
      +1 5-digit ZIP
      +1 'Issuance Date' / 'Effective Date' on this OR the next page
      -2 'TABLE OF CONTENTS' / 'How to Use This' on this page (not a cover)
    Falls back to page 1 if nothing scores above 3.
    """
    best_page = 1
    best_score = 0
    n = min(len(pages), scan_first_n)
    for i in range(n):
        p = pages[i]
        score = 0
        if _COVER_FDD_RE.search(p.text):
            score += 3
        if _COVER_CORP_RE.search(p.text):
            score += 2
        if _COVER_PHONE_RE.search(p.text):
            score += 1
        if _COVER_WEBSITE_RE.search(p.text):
            score += 1
        if _COVER_ZIP_RE.search(p.text):
            score += 1
        # Issuance date often on the immediately-following page
        if _COVER_ISSUANCE_RE.search(p.text):
            score += 1
        elif i + 1 < n and _COVER_ISSUANCE_RE.search(pages[i + 1].text):
            score += 1
        if _COVER_TOC_RE.search(p.text):
            score -= 2
        if score > best_score:
            best_score = score
            best_page = p.page_num
    return best_page if best_score >= 4 else 1


def section_text(pages: list[PageText], start: int, end: int) -> str:
    """Concatenate text for pages [start, end] inclusive, with page markers."""
    parts = []
    for p in pages:
        if start <= p.page_num <= end:
            parts.append(f"\n=== PDF PAGE {p.page_num} ===\n{p.text}")
    return "\n".join(parts)


def rasterize_pages(pdf_path: Path, start: int, end: int, scale: float = 2.0) -> list[bytes]:
    """Render pages [start, end] (1-indexed inclusive) as PNG bytes."""
    pdf = pdfium.PdfDocument(str(pdf_path))
    out: list[bytes] = []
    try:
        for i in range(start - 1, min(end, len(pdf))):
            page = pdf[i]
            bitmap = page.render(scale=scale)
            pil = bitmap.to_pil()
            buf = io.BytesIO()
            pil.save(buf, format="PNG", optimize=True)
            out.append(buf.getvalue())
    finally:
        pdf.close()
    return out


def png_to_base64(png_bytes: bytes) -> str:
    return base64.standard_b64encode(png_bytes).decode("ascii")
