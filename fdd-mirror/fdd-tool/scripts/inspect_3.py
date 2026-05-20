"""Inspect all 3 candidate FDDs for Item 19 body location. Encoding-safe."""
from pathlib import Path
import re
import sys
import pypdf

# Force UTF-8 stdout so Windows console doesn't choke on special chars
sys.stdout.reconfigure(encoding="utf-8")


def _safe(s: str, n: int = 300) -> str:
    return s[:n].replace("\n", " ").encode("ascii", "replace").decode("ascii")


def inspect(name: str) -> None:
    p = Path("data") / name
    if not p.exists():
        print(f"\n!!! {name} not found")
        return
    reader = pypdf.PdfReader(str(p))
    n = len(reader.pages)
    sz = p.stat().st_size / 1024 / 1024
    print(f"\n========== {name} ({n} pages, {sz:.2f} MB) ==========")
    print("p1:", _safe(reader.pages[0].extract_text() or ""))

    # Find ALL Item 19 mentions and classify
    print("\n  All 'Item 19' / 'ITEM 19' line matches (filter to lines that look like headings):")
    body_candidates = []
    for i, page in enumerate(reader.pages):
        t = page.extract_text() or ""
        # Find heading-style mentions: "ITEM 19" or "Item 19" followed by FPR keywords
        for m in re.finditer(r"(?:^|\n)\s*ITEM\s*19\b[\s\.\-:]*([A-Za-z][A-Za-z ,'/\-]{4,60})", t, re.IGNORECASE | re.MULTILINE):
            snippet = m.group(0).strip()
            # Skip TOC entries (typically end with page number or dots)
            is_toc = bool(re.search(r"\.{3,}|\d+\s*$", t[m.start():m.start() + 200]))
            page_text_len = len(t)
            tag = "TOC?" if is_toc else "BODY?"
            print(f"    [{tag}] p{i+1}: {_safe(snippet, 100)!r}  (page has {page_text_len} chars)")
            if not is_toc:
                body_candidates.append(i + 1)

    if body_candidates:
        body_pg = body_candidates[0]
        print(f"\n  >>> Likely Item 19 BODY starts at page {body_pg}")
        # Dump next 2 pages
        for j in range(body_pg, min(body_pg + 2, n + 1)):
            txt = reader.pages[j - 1].extract_text() or ""
            print(f"\n  ---- PDF page {j} (first 1800 chars) ----")
            print(_safe(txt, 1800))
    else:
        print("\n  >>> NO non-TOC Item 19 candidate found. May have 'we do not make an FPR' language.")
        # Find any pages mentioning "no financial performance" to confirm
        for i, page in enumerate(reader.pages):
            t = page.extract_text() or ""
            if re.search(r"no\s+financial\s+performance", t, re.I) or re.search(r"do\s+not\s+make\s+(?:any\s+)?financial\s+performance", t, re.I):
                print(f"    'no FPR' language found at p{i+1}: {_safe(t, 250)!r}")
                break


for name in ["servpro_2014.pdf", "service_experts_mn.pdf", "rebath_2025_mn.pdf"]:
    inspect(name)
