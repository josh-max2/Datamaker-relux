"""Bucket each preflight PDF as born-digital / partial / fully-scanned.

Per-page test: a page is 'scanned-like' if it has <200 extracted chars OR
alphabetic-char ratio <0.50. Allow up to 10% scanned-like pages per PDF (covers,
signature pages, blank dividers) before flagging.

Buckets:
  born_digital:   <=10% scanned-like pages
  partial:        10-75% scanned-like
  fully_scanned:  >75% scanned-like
"""
import re
import sys
from pathlib import Path

import pypdf

sys.stdout.reconfigure(encoding="utf-8")

ALPHA_RE = re.compile(r"[A-Za-z]")
PRINTABLE_RE = re.compile(r"[\x20-\x7E\n\r\t]")


def analyze_page(text: str) -> tuple[bool, dict]:
    n = len(text)
    if n < 200:
        return True, {"len": n, "alpha_ratio": None, "reason": "too short"}
    alpha = len(ALPHA_RE.findall(text))
    printable = len(PRINTABLE_RE.findall(text))
    alpha_ratio = alpha / n
    printable_ratio = printable / n
    if alpha_ratio < 0.50:
        return True, {"len": n, "alpha_ratio": round(alpha_ratio, 2), "reason": f"low alpha ratio ({alpha_ratio:.2f})"}
    if printable_ratio < 0.85:
        return True, {"len": n, "alpha_ratio": round(alpha_ratio, 2), "reason": f"low printable ratio ({printable_ratio:.2f})"}
    return False, {"len": n, "alpha_ratio": round(alpha_ratio, 2), "reason": "ok"}


def analyze_pdf(path: Path) -> dict:
    reader = pypdf.PdfReader(str(path))
    n = len(reader.pages)
    scanned_pages = 0
    scanned_detail: list[tuple[int, dict]] = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        is_bad, info = analyze_page(text)
        if is_bad:
            scanned_pages += 1
            scanned_detail.append((i + 1, info))
    bad_pct = scanned_pages / n * 100
    if bad_pct <= 10:
        bucket = "born_digital"
    elif bad_pct <= 75:
        bucket = "partial"
    else:
        bucket = "fully_scanned"
    return {
        "pages": n,
        "size_mb": round(path.stat().st_size / 1024 / 1024, 2),
        "scanned_pages": scanned_pages,
        "bad_pct": round(bad_pct, 1),
        "bucket": bucket,
        "scanned_detail": scanned_detail[:5],  # first 5 bad pages for inspection
    }


results: dict[str, dict] = {}
preflight = Path("data/preflight")
for pdf in sorted(preflight.glob("*.pdf")):
    print(f"Analyzing {pdf.name}...")
    results[pdf.name] = analyze_pdf(pdf)

# Also analyze the 4 already-validated PDFs as a sanity check
validated = Path("data")
for name in ["crumbl_yale.pdf", "service_experts_mn.pdf", "rebath_2025_mn.pdf", "servpro_2014.pdf"]:
    p = validated / name
    if p.exists():
        print(f"Analyzing (validated) {name}...")
        results[f"_validated_{name}"] = analyze_pdf(p)

print("\n" + "=" * 80)
print(f"{'PDF':<40} {'Pages':>6} {'MB':>6} {'Bad%':>6} {'Bucket':<14}")
print("=" * 80)
buckets = {"born_digital": 0, "partial": 0, "fully_scanned": 0}
preflight_buckets = {"born_digital": 0, "partial": 0, "fully_scanned": 0}
for name, info in sorted(results.items()):
    print(f"{name:<40} {info['pages']:>6} {info['size_mb']:>6} {info['bad_pct']:>5}% {info['bucket']:<14}")
    buckets[info["bucket"]] += 1
    if not name.startswith("_validated_"):
        preflight_buckets[info["bucket"]] += 1

print("\n" + "=" * 80)
print("PREFLIGHT BUCKET SUMMARY (excluding the 4 validated PDFs):")
total = sum(preflight_buckets.values())
for b, c in preflight_buckets.items():
    pct = c / total * 100 if total else 0
    print(f"  {b:<15} {c:>3} / {total}  ({pct:.1f}%)")

print("\nVALIDATED PDFs (for reference):")
for name, info in sorted(results.items()):
    if name.startswith("_validated_"):
        print(f"  {name}: {info['bucket']} ({info['bad_pct']}% bad pages)")
