"""Snap full-page screenshots of the Domino's brand page on the live site."""
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

URL = "https://franchisedepth.com/franchise/domino-s-pizza/"
OUT = Path(__file__).resolve().parent / "_snaps"
OUT.mkdir(exist_ok=True)

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, device_scale_factor=2)
    page = ctx.new_page()
    page.goto(URL, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(2000)  # let charts render

    # Full-page screenshot
    full_path = OUT / "dominos_full.png"
    page.screenshot(path=str(full_path), full_page=True)
    print(f"  full-page: {full_path.stat().st_size // 1024} KB")

    # Also capture viewport sections by scrolling to identifiable elements
    section_targets = [
        ("hero", "h1"),
        ("fact-box", ".fact-box, .quick-stats, .meta-grid"),
        ("item19_chart", "#item19Chart, [class*='item19']"),
        ("outlet_chart", "#outletChart, [class*='outlet']"),
        ("state_heatmap", ".state-heatmap, [class*='heatmap']"),
        ("state_bars", "#stateChart"),
        ("compare_block", "[class*='compare']"),
    ]
    for label, sel in section_targets:
        try:
            els = page.query_selector_all(sel)
            for i, el in enumerate(els[:1]):
                if el and el.is_visible():
                    el.scroll_into_view_if_needed()
                    page.wait_for_timeout(400)
                    p = OUT / f"dominos_{label}.png"
                    el.screenshot(path=str(p))
                    print(f"  section {label}: {p.stat().st_size // 1024} KB")
                    break
        except Exception as e:
            print(f"  ! {label}: {e}")

    browser.close()

print(f"\nDone. Snaps in {OUT}")
