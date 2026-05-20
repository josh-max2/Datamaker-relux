"""F5.1 verification: comparison page renders, breadcrumb correct, cross-link from brand page works."""
import asyncio
import json
import sys
from playwright.async_api import async_playwright

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = "http://127.0.0.1:8765/Parser"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await ctx.new_page()

        # 1. Load a compare page directly
        await page.goto(f"{BASE}/compare/bath-fitter-vs-re-bath/")

        h1 = (await page.text_content("h1")).strip()
        print(f"compare h1: {h1!r}")
        assert "Bath Fitter" in h1 and "Re-Bath" in h1

        # 2. Breadcrumb: 3 levels with correct labels
        bc_items = await page.query_selector_all("nav.breadcrumbs ol li")
        bc_labels = [(await li.inner_text()).strip() for li in bc_items]
        print(f"breadcrumb: {bc_labels}")
        assert len(bc_items) == 3
        assert "Home" in bc_labels[0]
        assert "Remodeling" in bc_labels[1]
        assert "vs" in bc_labels[2]

        # 3. Comparison table has both brand columns
        col_headers = await page.eval_on_selector_all(
            "table.compare-table thead th[scope='col']",
            "els => els.map(e => e.innerText.trim())"
        )
        print(f"col headers: {col_headers}")
        assert any("Bath Fitter" in h for h in col_headers)
        assert any("Re-Bath" in h for h in col_headers)

        # 4. Has multiple data rows
        rows = await page.query_selector_all("table.compare-table tbody tr")
        print(f"data rows: {len(rows)}")
        assert len(rows) >= 10

        # 5. JSON-LD parses, includes both brands in "about"
        ld_count = 0
        for s in await page.query_selector_all("script[type='application/ld+json']"):
            body = await s.inner_text()
            d = json.loads(body)
            if d.get("@type") == "Article":
                about = d.get("about", [])
                names = [x.get("alternateName") or x.get("name") for x in about]
                print(f"Article about: {names}")
                assert any("Bath Fitter" in n for n in names)
                assert any("Re-Bath" in n for n in names)
            if d.get("@type") == "BreadcrumbList":
                items = d.get("itemListElement", [])
                assert len(items) == 3
            ld_count += 1
        print(f"json-ld scripts: {ld_count}")

        await page.screenshot(path="scripts/_screenshots/_audit/compare_page.png", full_page=False)

        # 6. From a brand page, the "Compare X head-to-head" list is rendered
        await page.goto(f"{BASE}/franchise/re-bath/")
        compare_links = await page.eval_on_selector_all(
            "ul.compare-with-list a",
            "els => els.map(e => ({text: e.innerText.trim(), href: e.getAttribute('href')}))"
        )
        print(f"compare-with links from re-bath: {compare_links}")
        assert len(compare_links) >= 2
        # Click one and verify it lands on a compare page
        first_href = compare_links[0]["href"]
        await page.goto(f"http://127.0.0.1:8765{first_href}")
        h1_after = (await page.text_content("h1")).strip()
        print(f"after click h1: {h1_after!r}")
        assert "vs" in h1_after
        assert "Re-Bath" in h1_after

        print("ok F5.1 compare pages render + cross-links work + schema valid")
        await browser.close()


asyncio.run(main())
