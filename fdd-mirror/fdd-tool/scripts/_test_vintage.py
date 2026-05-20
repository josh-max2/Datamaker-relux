"""F2.6 verification: per-section data-vintage lines render, byline shows source-verified date."""
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await ctx.new_page()

        await page.goto("http://127.0.0.1:8765/Parser/franchise/re-bath/")

        vlines = await page.query_selector_all("p.data-vintage")
        print(f"vintage line count: {len(vlines)}")
        assert len(vlines) >= 3, f"expected >=3 vintage lines, got {len(vlines)}"
        for i, v in enumerate(vlines):
            t = (await v.inner_text()).strip()
            print(f"  [{i}] {t}")
            assert "Source:" in t
            assert "FDD" in t
            assert "verified" in t

        # Byline shows source verified
        byline = await page.inner_text("p.byline")
        print(f"byline: {byline.strip()}")
        assert "Source verified" in byline, "byline missing 'Source verified'"
        assert "Page regenerated" in byline, "byline missing 'Page regenerated'"

        # Item 19 vintage should include page range (Re-Bath has multi-page Item 19)
        item19_v = await page.evaluate("""() => {
            const h = [...document.querySelectorAll('h2')].find(h => h.innerText.includes('Item 19'));
            return h ? h.nextElementSibling.innerText : null;
        }""")
        print(f"item19 vintage: {item19_v}")
        assert item19_v and "page" in item19_v.lower()

        # Scroll into a section that has a vintage line and snap a viewport shot
        await page.evaluate("""() => {
            const h = [...document.querySelectorAll('h2')].find(h => h.innerText.startsWith('Fees'));
            if (h) h.scrollIntoView({block: 'start'});
        }""")
        await page.screenshot(path="scripts/_screenshots/_audit/vintage_brand.png", full_page=False)
        print("ok F2.6 vintage rendered")
        await browser.close()


asyncio.run(main())
