"""Render src/lead_magnet/checklist.html to docs/lead-magnets/fdd-buyers-checklist.pdf.

Uses Playwright's page.pdf() — already installed for the WI portal scraper.
Produces print-quality output with:
  - US Letter page size, 1" margins (set via @page CSS)
  - Page number footer ("FranchiseDepth.com · 2026 Edition · Page X of Y") via @page CSS
  - Cover page suppresses the footer (@page :first override in the HTML)
  - Working hyperlinks
  - Subtle diagonal watermark on data-heavy pages
"""
from __future__ import annotations

import datetime
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SRC_HTML = ROOT / "src" / "lead_magnet" / "checklist.html"
REPO_ROOT = ROOT.parent
# Build to a STABLE source location that survives `docs/` regen.
# site_gen.py copies this into docs/lead-magnets/ on every build.
OUT_DIR = ROOT / "src" / "lead_magnet" / "build"
OUT_PDF = OUT_DIR / "fdd-buyers-checklist.pdf"
DOCS_COPY = REPO_ROOT / "docs" / "lead-magnets" / "fdd-buyers-checklist.pdf"


def main():
    if not SRC_HTML.exists():
        sys.exit(f"!! source HTML missing: {SRC_HTML}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    print(f"=== Building FDD Buyer's Checklist PDF ===")
    print(f"  source: {SRC_HTML}")
    print(f"  out:    {OUT_PDF}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            context = browser.new_context()
            page = context.new_page()
            file_url = SRC_HTML.absolute().as_uri()
            page.goto(file_url, wait_until="networkidle")
            # Brief settle for font rendering
            page.wait_for_timeout(300)

            page.pdf(
                path=str(OUT_PDF),
                format="Letter",
                print_background=True,  # render gradients + colored backgrounds on cover
                prefer_css_page_size=True,  # honor @page size + margins from the HTML
                margin={"top": "0in", "right": "0in", "bottom": "0in", "left": "0in"},
                # No headerTemplate/footerTemplate — handled by @page CSS for control
                display_header_footer=False,
            )
        finally:
            browser.close()

    size_kb = OUT_PDF.stat().st_size / 1024
    elapsed = time.time() - t0
    print(f"\n  OK: built {OUT_PDF}  ({size_kb:.0f} KB, {elapsed:.1f}s)")

    # Also copy into docs/ so the current site state has it without needing a regen.
    import shutil
    DOCS_COPY.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(OUT_PDF, DOCS_COPY)
    print(f"  copied -> {DOCS_COPY}")
    print(f"  published at: https://franchisedepth.com/lead-magnets/{OUT_PDF.name}")


if __name__ == "__main__":
    main()
