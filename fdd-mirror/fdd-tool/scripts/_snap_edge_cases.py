"""Screenshot brand pages and compare pages representing visual edge cases."""
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "_snaps_edge"
OUT.mkdir(exist_ok=True)
DOCS = Path(__file__).resolve().parents[2] / "docs"

PAGES = [
    ("subway",          "subway",                              "no Item 19 disclosed"),
    ("mcdonalds",       "mcdonald-s",                          "13k outlets"),
    ("dunkin",          "dunkin",                              "10k outlets"),
    ("dumpster_dudez",  "dumpster-dudez",                      "33y breakeven (long)"),
    ("crumbl",          "crumbl",                              "few cohorts"),
    ("anytime_fitness", "anytime-fitness",                     "high outlet count"),
    ("compare_food",    "compare/burger-king-vs-mcdonald-s",   "compare page (food)"),
    ("compare_fitness", "compare/anytime-fitness-vs-planet-fitness", "compare page (fitness)"),
    ("hometowne",       "hometowne-studios-by-red-roof-hometowne-studios-suites-hometowne-inn-hometown-in", "hotel — daily rate metric"),
]

with sync_playwright() as pw:
    browser = pw.chromium.launch()

    # Desktop first
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, device_scale_factor=2)
    page = ctx.new_page()

    for label, slug, note in PAGES:
        if slug.startswith("compare/"):
            local = DOCS / slug / "index.html"
        else:
            local = DOCS / "franchise" / slug / "index.html"
        if not local.exists():
            print(f"  !! missing: {local}")
            continue
        url = "file://" + str(local.resolve()).replace("\\", "/")
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2000)
        out_path = OUT / f"{label}_full.png"
        page.screenshot(path=str(out_path), full_page=True)
        kb = out_path.stat().st_size // 1024
        print(f"  desktop {label} ({note}): {kb} KB -> {out_path.name}")

    # Mobile re-snap for layout check
    ctx_m = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    page_m = ctx_m.new_page()
    for label, slug, _ in [PAGES[1], PAGES[3], PAGES[6]]:  # mcdonalds, dumpster, compare
        if slug.startswith("compare/"):
            local = DOCS / slug / "index.html"
        else:
            local = DOCS / "franchise" / slug / "index.html"
        if not local.exists():
            continue
        url = "file://" + str(local.resolve()).replace("\\", "/")
        page_m.goto(url, wait_until="networkidle", timeout=60000)
        page_m.wait_for_timeout(1500)
        out_path = OUT / f"{label}_mobile.png"
        page_m.screenshot(path=str(out_path), full_page=True)
        kb = out_path.stat().st_size // 1024
        print(f"  mobile  {label}: {kb} KB -> {out_path.name}")

    browser.close()

print(f"\nSnaps in {OUT}")
