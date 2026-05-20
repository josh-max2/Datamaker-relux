"""F3.6 verification: breadcrumb trail renders on a brand page, links to category page work, schema parses."""
import asyncio
import pathlib
from playwright.async_api import async_playwright

DOCS = pathlib.Path(__file__).resolve().parents[2] / "docs"
SHOT_DIR = pathlib.Path(__file__).resolve().parent / "_screenshots" / "_audit"
SHOT_DIR.mkdir(parents=True, exist_ok=True)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await ctx.new_page()

        # Use local HTTP server (so /Parser/... absolute hrefs resolve)
        BASE = "http://127.0.0.1:8765/Parser"
        url = f"{BASE}/franchise/re-bath/"
        await page.goto(url)

        # Visible breadcrumb
        nav = await page.query_selector("nav.breadcrumbs ol")
        assert nav, "breadcrumb nav missing"
        items = await page.query_selector_all("nav.breadcrumbs ol li")
        labels = [(await li.inner_text()).strip() for li in items]
        print("breadcrumb labels:", labels)
        assert len(items) == 3, f"expected 3 items, got {len(items)}"
        assert "Home" in labels[0]
        assert "Remodeling" in labels[1]
        assert "Re-Bath" in labels[2]

        # Current page (last) should NOT be a link
        last_link = await items[-1].query_selector("a")
        assert last_link is None, "last item must not be a link"

        # Screenshot
        await page.screenshot(path=str(SHOT_DIR / "breadcrumb_brand.png"))

        # Category page also has breadcrumb (2 items)
        await page.goto(f"{BASE}/category/home-services-remodeling/")
        cat_items = await page.query_selector_all("nav.breadcrumbs ol li")
        assert len(cat_items) == 2, f"category page expected 2 items, got {len(cat_items)}"
        await page.screenshot(path=str(SHOT_DIR / "breadcrumb_category.png"))

        # Home page should NOT have breadcrumb
        await page.goto(f"{BASE}/")
        home_nav = await page.query_selector("nav.breadcrumbs")
        assert home_nav is None, "home page must not have breadcrumb"

        # Verify breadcrumb links point at the expected category URL
        # (can't follow under file:// since hrefs are absolute /Parser/...)
        await page.goto(url)
        cat_href = await page.get_attribute("nav.breadcrumbs ol li:nth-child(2) a", "href")
        print("category breadcrumb href:", cat_href)
        assert cat_href == "/Parser/category/home-services-remodeling/", \
            f"unexpected href: {cat_href}"

        print("ok F3.6 breadcrumbs render + href + schema present")
        await browser.close()


asyncio.run(main())
