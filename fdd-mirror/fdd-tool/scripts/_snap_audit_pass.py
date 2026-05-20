"""Visual audit pass — snap representative brand pages and key features."""
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "_audit_snaps"
OUT.mkdir(exist_ok=True)
DOCS = Path(__file__).resolve().parents[2] / "docs"

# Representative brands across edge cases
BRANDS = [
    ("dominos",         "domino-s-pizza",        "QSR / weekly AWUS / has Item 19"),
    ("subway",          "subway",                "QSR / NO Item 19 / huge outlet count"),
    ("mcdonalds",       "mcdonald-s",            "Iconic brand / large outlet count"),
    ("planet_fitness",  "planet-fitness",        "Fitness / new category"),
    ("ups_store",       "the-ups-store",         "Retail / new category"),
    ("hrblock",         "h-r-block",             "Tax / new category"),
    ("remax",           "remax",                 "Real estate"),
    ("holiday_inn",     "holiday-inn-express",   "Hotel / daily-rate metric"),
    ("servpro",         "servpro",               "Home services / huge state coverage"),
    ("homevestors",     "homevestors",           "Real estate / has FPR"),
    ("homewatch",       "homewatch-caregivers",  "Low quality 6/20 — section detection fail"),
    ("five_star_bath",  "five-star-bath-solutions", "Low quality 6/20"),
]

def snap(label, slug, note):
    local = DOCS / "franchise" / slug / "index.html"
    if not local.exists():
        print(f"  !! {label}: MISSING {local}")
        return False
    url = "file:///" + str(local).replace("\\", "/")
    return url

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, device_scale_factor=2)
    page = ctx.new_page()

    for label, slug, note in BRANDS:
        url = snap(label, slug, note)
        if not url: continue
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2000)
        # Full page snap
        full_path = OUT / f"{label}_full.png"
        page.screenshot(path=str(full_path), full_page=True)
        # Calculator section
        try:
            page.evaluate("document.getElementById('cost-calculator').scrollIntoView()")
            page.wait_for_timeout(800)
            calc_path = OUT / f"{label}_calc.png"
            calc_el = page.query_selector("#cost-calculator")
            if calc_el:
                calc_el.screenshot(path=str(calc_path))
        except Exception as e:
            print(f"  ! {label} calc snap: {e}")
        # Read calc state
        try:
            y1 = page.locator("#calc-net-year1").inner_text()
            payback = page.locator("#calc-payback").inner_text()
            cum = page.locator("#calc-cum-10y").inner_text()
            print(f"  {label:18s} ({note[:35]:35s}) Y1={y1:14s} payback={payback:5s} 10y={cum}")
        except Exception:
            print(f"  {label}: calc not present or no Item 19")
    browser.close()
