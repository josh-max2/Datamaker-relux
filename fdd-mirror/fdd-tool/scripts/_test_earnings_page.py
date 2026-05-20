"""Quick screenshot + sanity check of the highest-reported-earnings page."""
import asyncio, sys
from playwright.async_api import async_playwright

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await ctx.new_page()

        url = "http://127.0.0.1:8765/category/home-services-cleaning/highest-reported-earnings/"
        await page.goto(url)

        h1 = (await page.text_content("h1")).strip()
        rows = await page.evaluate("() => document.querySelectorAll('#earnings-table tbody tr').length")
        print(f"h1: {h1!r}")
        print(f"table rows: {rows}")

        # Check the brand-name column for at least one cleaning brand
        first_brand = await page.text_content("#earnings-table tbody tr:first-child td:nth-child(2) a")
        print(f"top-ranked brand: {first_brand!r}")

        await page.screenshot(path="scripts/_screenshots/_audit/highest_earnings_cleaning.png")

        # Click an earnings link from the category page
        await page.goto("http://127.0.0.1:8765/category/home-services-cleaning/")
        link = await page.query_selector("a[href*='highest-reported-earnings']")
        print(f"link from category page present: {link is not None}")
        await page.screenshot(path="scripts/_screenshots/_audit/category_with_earnings_link.png")

        await browser.close()


asyncio.run(main())
