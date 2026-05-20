"""Locate the actual cover page of the Mr. Rooter PDF — where legal_name etc. live."""
import sys
from pathlib import Path
import pypdf
import re

sys.stdout.reconfigure(encoding="utf-8")
reader = pypdf.PdfReader(str(Path("data/wi_scrape/mr_rooter_wi_id640790.pdf")))

# Dump first 12 pages briefly. Mark which has "FRANCHISE DISCLOSURE DOCUMENT" + LLC + an address pattern.
addr_re = re.compile(r"\b[A-Z]{2}\s+\d{5}\b")  # state + zip
corp_re = re.compile(r"\b(LLC|Inc\.?|Corporation|Limited)\b")
fdd_re = re.compile(r"FRANCHISE\s+DISCLOSURE\s+DOCUMENT", re.IGNORECASE)
issuance_re = re.compile(r"(Issuance|Effective)\s+Date", re.IGNORECASE)

for i in range(12):
    t = (reader.pages[i].extract_text() or "")
    safe = t.replace("\n", " ").encode("ascii", "replace").decode("ascii")
    has_fdd = bool(fdd_re.search(t))
    has_corp = bool(corp_re.search(t))
    has_addr = bool(addr_re.search(t))
    has_issuance = bool(issuance_re.search(t))
    n = len(t)
    marker = "<<< COVER CANDIDATE" if has_fdd and has_corp and has_addr else ""
    print(f"\n== p{i+1} ({n} chars; fdd={has_fdd} corp={has_corp} addr={has_addr} issuance={has_issuance}) {marker}")
    print(safe[:600])
