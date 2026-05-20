"""Content-level PDF dedup: extracts (legal_name, effective_date) from page 1 cheaply
to detect multi-state filings of the same underlying FDD without paying for re-extraction.

Why this matters: WI, MN, CA, IN, NY all receive the SAME franchisor's FDD with
state-specific cover pages + addenda. SHA-256 dedup misses these (the bytes differ);
content dedup catches them. Cost: ~10ms per PDF + zero LLM tokens.

The dedup key has two granularities:
- "full":  {legal_slug}|{YYYY-MM-DD}      — exact match across states
- "year":  {legal_slug}|{YYYY}            — fallback when only the year is parseable

Usage:
    from scripts._pdf_dedup import extract_content_key
    key = extract_content_key(Path("data/wi_scrape/foo.pdf"))
    # key is None if no legal_name found; otherwise a dict
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Optional


# Corporate-form suffixes that mark the end of a legal name
CORP_SUFFIX = (
    r"LLC|L\.L\.C\.|Inc\.?|Incorporated|Corporation|Corp\.?|Co\.?|Company|"
    r"Ltd\.?|Limited|LP|L\.P\.|LLP|L\.L\.P\.|PLLC|P\.L\.L\.C\."
)

# Find a legal name on its own line, ending in a corp suffix.
# Used when PDF extraction preserves line structure.
LEGAL_NAME_LINE = re.compile(
    r"^\s*([A-Za-z0-9][A-Za-z0-9 &'?.\-,]{2,100}(?:,?\s+(?:" + CORP_SUFFIX + r"))\.?)\s*$",
    re.MULTILINE,
)

# Fallback: legal name appearing inline (not anchored to line). Matches names
# ending in corp suffix that are preceded by whitespace or start of string and
# followed by whitespace, period, or end. Tighter char class to reduce false positives.
LEGAL_NAME_INLINE = re.compile(
    r"(?:^|[\s])([A-Z][A-Za-z0-9 &'?.\-]{2,80},?\s+(?:" + CORP_SUFFIX + r"))(?=[\s.,]|$)"
)

# Inline date "April 15, 2026" without a keyword anchor (used as last-resort)
INLINE_MONTH_DAY_YEAR = re.compile(
    r"((?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},?\s+\d{4})"
)

# Keyword phrases that introduce a date on FDD cover pages.
# Built as multi-word so we don't accidentally match inside body prose.
DATE_KEYWORD = (
    r"(?:"
    r"Issuance\s+Date|"
    r"Issue\s+Date|"
    r"Effective\s+Date|"
    r"Date\s+of\s+Issuance|"
    r"Version\s+Date|"
    r"V\s?ersion\s+Date|"            # PDF extraction sometimes inserts a space: "V ersion"
    r"date\s+of\s+issuance\s+of\s+this\s+Disclosure(?:\s+(?:Statement|Document))?"
    r")"
)

# "<keyword>[ :]<month> <day>, <year>"
DATE_PATTERNS = [
    re.compile(
        DATE_KEYWORD
        + r"\s*[:\-]?\s*(?:is\s+)?"
        + r"((?:January|February|March|April|May|June|July|August|September|October|November|December)"
        + r"\s+\d{1,2},?\s+\d{4})",
        re.IGNORECASE,
    ),
    re.compile(
        DATE_KEYWORD + r"\s*[:\-]?\s*(?:is\s+)?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        re.IGNORECASE,
    ),
    re.compile(
        DATE_KEYWORD + r"\s*[:\-]?\s*(?:is\s+)?(\d{4}-\d{2}-\d{2})",
        re.IGNORECASE,
    ),
]

# Year-only fallback patterns ("2026 FDD", "FDD ... 2026", "Version 2026", etc.)
YEAR_PATTERNS = [
    re.compile(r"(?:FDD|Disclosure\s+Document)\s*[:\-]?\s*[#\s]*(\d{4})"),
    re.compile(r"\b(\d{4})\s+(?:FDD|Franchise\s+Disclosure)"),
    re.compile(r"\bFDD[\s\-]+(\d{4})\b"),
    re.compile(r"\b(?:Year|Version)\s*[:\-]?\s*(\d{4})\b"),
]


def _slugify(s: str) -> str:
    """Normalize a legal name to a stable dedup slug."""
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    # Strip corporate suffixes (we want "abc inc" and "abc, inc." to match)
    s = re.sub(
        r"\b(llc|l\.l\.c\.|inc\.?|incorporated|corporation|corp\.?|company|co\.?|"
        r"ltd\.?|limited|lp|l\.p\.|llp|l\.l\.p\.|pllc)\b",
        "",
        s,
    )
    # Strip punctuation, collapse whitespace
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def _normalize_date(raw: str) -> Optional[str]:
    """Best-effort YYYY-MM-DD normalization."""
    raw = raw.strip().rstrip(",.")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return raw
    months = {
        "january": "01", "february": "02", "march": "03", "april": "04",
        "may": "05", "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12",
    }
    m = re.match(r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})", raw)
    if m:
        mon = months.get(m.group(1).lower())
        if mon:
            return f"{m.group(3)}-{mon}-{int(m.group(2)):02d}"
    m = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", raw)
    if m:
        mo, d, y = m.groups()
        y = "20" + y if len(y) == 2 else y
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    return None


def extract_page1_text(pdf_path: Path) -> str:
    """Extract just page 1 text from a PDF. Cheap: ~10ms with pypdf."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        if not reader.pages:
            return ""
        return reader.pages[0].extract_text() or ""
    except Exception:
        return ""


def extract_pages_text(pdf_path: Path, n_pages: int = 3) -> str:
    """Extract first N pages' text — used as fallback when page 1 doesn't have what we need."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        parts = []
        for i in range(min(n_pages, len(reader.pages))):
            try:
                parts.append(reader.pages[i].extract_text() or "")
            except Exception:
                continue
        return "\n".join(parts)
    except Exception:
        return ""


def extract_legal_name(text: str) -> Optional[str]:
    """Find a single-line legal name ending in a corporate suffix.
    Strategy: find all matches, prefer the one closest to (and after) the
    'FRANCHISE DISCLOSURE DOCUMENT' header — that's the franchisor's legal entity.
    Fall back to the first matching line if no header found.
    """
    if not text:
        return None
    header_match = re.search(r"FRANCHISE\s+DISCLOSURE\s+DOCUMENT", text, re.IGNORECASE)
    header_pos = header_match.start() if header_match else -1

    # Tier 1: line-anchored matches
    for m in LEGAL_NAME_LINE.finditer(text):
        if header_pos >= 0 and m.start() < header_pos:
            continue
        candidate = m.group(1).strip().rstrip(".")
        if _is_plausible_legal_name(candidate):
            return candidate

    # Tier 2: inline matches near header (mash-of-text PDFs)
    if header_pos >= 0:
        # Search window: 0–1200 chars after header
        window = text[header_pos:header_pos + 1200]
        for m in LEGAL_NAME_INLINE.finditer(window):
            candidate = m.group(1).strip().rstrip(".")
            if _is_plausible_legal_name(candidate):
                return candidate

    # Tier 3: any line-anchored match (without header constraint)
    for m in LEGAL_NAME_LINE.finditer(text):
        candidate = m.group(1).strip().rstrip(".")
        if _is_plausible_legal_name(candidate):
            return candidate

    return None


def _is_plausible_legal_name(s: str) -> bool:
    """Filter out obvious false positives."""
    if len(s) < 4 or len(s) > 120:
        return False
    low = s.lower()
    # Skip boilerplate phrases
    blacklist = (
        "franchise disclosure", "table of contents", "exhibit", "section",
        "this disclosure", "you may wish", "you must receive", "important",
    )
    if any(b in low for b in blacklist):
        return False
    # Skip company-description phrases that masquerade as names. Drop articles only
    # when followed by lowercase (descriptive phrase). "The Maids International" is a
    # real name; "a Delaware limited liability company" is a description.
    if re.match(r"^(?:a|an|the)\s+[a-z]", s):
        return False
    # Skip if the name is just "X Corporation" / "X Company" without a proper noun
    # (e.g., "Delaware Corporation" picked up from "a Delaware corporation")
    state_names = {
        "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
        "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
        "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine",
        "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
        "missouri", "montana", "nebraska", "nevada", "ohio", "oklahoma", "oregon",
        "pennsylvania", "tennessee", "texas", "utah", "vermont", "virginia",
        "washington", "wisconsin", "wyoming",
    }
    first_word = low.split()[0] if low else ""
    if first_word in state_names:
        return False
    return True


def extract_effective_date(text: str) -> Optional[str]:
    """Best-effort effective/issuance date. Returns ISO YYYY-MM-DD or None."""
    if not text:
        return None
    # Tier 1: keyword-anchored patterns
    for pat in DATE_PATTERNS:
        m = pat.search(text)
        if m:
            norm = _normalize_date(m.group(1))
            if norm:
                return norm
    # Tier 2: inline month-day-year, but only if near "FDD" or "Disclosure" header (first 1500 chars)
    # This catches "Bin Blasters. Multi-State FDD April 15, 2026" patterns.
    window = text[:1500]
    if re.search(r"(?:FDD|Disclosure\s+Document|Multi-?State)", window, re.IGNORECASE):
        m = INLINE_MONTH_DAY_YEAR.search(window)
        if m:
            norm = _normalize_date(m.group(1))
            if norm:
                return norm
    return None


def extract_year_fallback(text: str) -> Optional[str]:
    """When we can't find a full date, look for the FDD's filing/version year."""
    if not text:
        return None
    for pat in YEAR_PATTERNS:
        m = pat.search(text)
        if m:
            year = m.group(1)
            # Sanity-check: FDDs are filed for current/recent years
            try:
                y = int(year)
                if 2010 <= y <= 2035:
                    return year
            except ValueError:
                continue
    return None


def extract_content_key(pdf_path: Path) -> Optional[dict]:
    """Returns a dedup descriptor, or None if no legal_name found at all.
    The dedup_key has two granularities — callers should try `full_key` first
    and fall back to `year_key` when comparing.

    Returns:
        {
          "legal_name": "Re-Bath, LLC",
          "legal_slug": "re-bath",
          "effective_date": "2025-03-15" | None,
          "year": "2025",
          "full_key": "re-bath|2025-03-15" | None,
          "year_key": "re-bath|2025",
          "confidence": "high" | "medium" | "low"
        }
        or None if even the legal name couldn't be extracted.
    """
    text = extract_page1_text(pdf_path)
    legal_name = extract_legal_name(text)
    effective_date = extract_effective_date(text)

    if not legal_name or not effective_date:
        text3 = extract_pages_text(pdf_path, n_pages=3)
        legal_name = legal_name or extract_legal_name(text3)
        effective_date = effective_date or extract_effective_date(text3)
        text = text3 or text

    if not legal_name:
        return None

    slug = _slugify(legal_name)
    if not slug:
        return None

    # Year fallback
    year = effective_date[:4] if effective_date else extract_year_fallback(text)

    confidence = "high" if effective_date else ("medium" if year else "low")
    full_key = f"{slug}|{effective_date}" if effective_date else None
    year_key = f"{slug}|{year}" if year else None

    return {
        "legal_name": legal_name,
        "legal_slug": slug,
        "effective_date": effective_date,
        "year": year,
        "full_key": full_key,
        "year_key": year_key,
        "confidence": confidence,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: python _pdf_dedup.py <pdf_path>")
        sys.exit(1)
    p = Path(sys.argv[1])
    result = extract_content_key(p)
    if result:
        for k, v in result.items():
            print(f"{k:15} {v}")
    else:
        print("could not extract (full extraction will proceed)")
