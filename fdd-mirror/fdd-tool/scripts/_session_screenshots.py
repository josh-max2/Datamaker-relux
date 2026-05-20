"""Screenshot key new + updated pages from this batch run."""
import asyncio, sys
from playwright.async_api import async_playwright

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

BASE = "http://127.0.0.1:8765/Parser"
SHOTS = "scripts/_screenshots/_audit"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await ctx.new_page()

        # 1. State page (new)
        await page.goto(f"{BASE}/state/california/")
        await page.screenshot(path=f"{SHOTS}/state_california.png")
        print("state h1:", (await page.text_content("h1")).strip())

        # 2. Guides hub
        await page.goto(f"{BASE}/guides/")
        await page.screenshot(path=f"{SHOTS}/guides_hub.png")

        # 3. Item 19 guide
        await page.goto(f"{BASE}/guides/understanding-item-19/")
        await page.screenshot(path=f"{SHOTS}/guide_item19.png")

        # 4. Homepage with budget widget
        await page.goto(f"{BASE}/?budget=200000")
        await page.wait_for_timeout(300)
        await page.screenshot(path=f"{SHOTS}/home_budget_widget.png")
        count = await page.text_content("#home-budget-count")
        print(f"home with budget=200k: {count} brands shown")

        # 5. Brand page with similar-cheaper + sparkline + jargon tooltips
        await page.goto(f"{BASE}/franchise/re-bath/")
        await page.evaluate("""() => {
            const h = [...document.querySelectorAll('h2')].find(h => h.innerText.startsWith('Similar'));
            if (h) h.scrollIntoView({block: 'start'});
        }""")
        await page.wait_for_timeout(150)
        await page.screenshot(path=f"{SHOTS}/brand_similar_cheaper.png")

        # 6. Outlet sparkline shot
        await page.goto(f"{BASE}/franchise/bath-fitter/")
        await page.evaluate("""() => {
            const h = [...document.querySelectorAll('h2')].find(h => h.innerText.startsWith('Outlet'));
            if (h) h.scrollIntoView({block: 'start'});
        }""")
        await page.wait_for_timeout(150)
        await page.screenshot(path=f"{SHOTS}/outlet_sparkline.png")

        # 7. Methodology glossary
        await page.goto(f"{BASE}/methodology/#glossary")
        await page.wait_for_timeout(150)
        await page.screenshot(path=f"{SHOTS}/methodology_glossary.png")

        # 8. Press page
        await page.goto(f"{BASE}/press/")
        await page.screenshot(path=f"{SHOTS}/press_page.png")

        # 9. Watermark verification — page source comment
        await page.goto(f"{BASE}/franchise/re-bath/")
        html_head = await page.evaluate("""() => document.documentElement.innerHTML.slice(0, 500)""")
        has_fp = "fd-fingerprint:" in html_head
        print(f"watermark fingerprint comment present: {has_fp}")

        # 10. Brand name unification check
        title = await page.title()
        brand_link = await page.text_content("a.brand")
        print(f"site name in header: {brand_link!r}")
        print(f"page title: {title[:80]}")

        print("ok screenshots complete")
        await browser.close()


asyncio.run(main())
