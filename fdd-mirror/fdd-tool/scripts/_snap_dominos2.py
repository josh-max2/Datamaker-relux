"""Snap individual sections at full readable resolution."""
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
    page.wait_for_timeout(2500)

    # Capture page in slices of 1000px (full-page is too compressed)
    full_height = page.evaluate("document.body.scrollHeight")
    print(f"  page height: {full_height}px")
    slice_h = 1000
    n_slices = (full_height + slice_h - 1) // slice_h
    for i in range(n_slices):
        y = i * slice_h
        page.evaluate(f"window.scrollTo(0, {y})")
        page.wait_for_timeout(400)
        p = OUT / f"dominos_slice_{i+1:02d}.png"
        page.screenshot(path=str(p), clip={"x": 0, "y": 0, "width": 1280, "height": min(slice_h, full_height - y)})
        print(f"  slice {i+1}/{n_slices}: y={y}")

    browser.close()
