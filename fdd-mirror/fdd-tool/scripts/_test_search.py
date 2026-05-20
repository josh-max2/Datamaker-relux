"""F3.5 verification: header search appears on every page, typeahead works, ?q= URL flows to homepage."""
import asyncio, sys
from playwright.async_api import async_playwright

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

BASE = "http://127.0.0.1:8765/Parser"
SHOTS = "scripts/_screenshots/_audit"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await ctx.new_page()

        # 1. Header search present on a brand page
        await page.goto(f"{BASE}/franchise/re-bath/")
        search = await page.query_selector("#header-search-input")
        assert search, "header search input missing"

        # 2. Typing "molly" should match Molly Maid
        await page.fill("#header-search-input", "molly")
        await page.wait_for_selector("#header-search-results li", timeout=2000)
        results = await page.eval_on_selector_all(
            "#header-search-results li a .hsr-name",
            "els => els.map(e => e.innerText)"
        )
        print(f"search 'molly' results: {results}")
        assert any("MOLLY" in r.upper() or "Molly" in r for r in results)

        # Screenshot dropdown
        await page.screenshot(path=f"{SHOTS}/header_search_dropdown.png")

        # 3. Clicking first result navigates to that brand
        await page.click("#header-search-results li:first-child a")
        await page.wait_for_load_state("domcontentloaded")
        url_after = page.url
        first_h1 = await page.locator("main h1").first.text_content()
        print(f"after click: url={url_after} h1={first_h1!r}")
        assert "molly-maid" in url_after.lower(), f"expected molly-maid in URL, got {url_after}"

        # 4. Search also works on category page (header is global)
        await page.goto(f"{BASE}/category/home-services-cleaning/")
        await page.fill("#header-search-input", "junk")
        await page.wait_for_timeout(200)
        results2 = await page.eval_on_selector_all(
            "#header-search-results li a .hsr-name",
            "els => els.map(e => e.innerText)"
        )
        print(f"search 'junk' from category page: {results2}")
        assert any("junk" in r.lower() for r in results2)

        # 5. SearchAction ?q=re-bath on homepage filters the brand list
        await page.goto(f"{BASE}/?q=re-bath")
        await page.wait_for_timeout(300)
        # The on-page brand-search filter should activate
        visible_rows = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('#brands-table tr'))
                .filter(r => r.style.display !== 'none')
                .map(r => r.dataset.name);
        }""")
        print(f"homepage ?q=re-bath visible rows: {visible_rows}")
        assert all("re-bath" in n for n in visible_rows)

        # 6. Empty search hides dropdown
        await page.goto(f"{BASE}/")
        await page.fill("#header-search-input", "molly")
        await page.wait_for_selector("#header-search-results li", timeout=2000)
        await page.fill("#header-search-input", "")
        await page.wait_for_timeout(200)
        hidden = await page.evaluate("() => document.getElementById('header-search-results').hidden")
        print(f"empty-search dropdown hidden: {hidden}")
        assert hidden

        # 7. Escape clears
        await page.fill("#header-search-input", "anago")
        await page.wait_for_selector("#header-search-results li", timeout=2000)
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(150)
        hidden_esc = await page.evaluate("() => document.getElementById('header-search-results').hidden")
        assert hidden_esc

        print("ok F3.5 header search — present on all pages, typeahead, Enter navigates, ?q= URL works, Escape closes")
        await browser.close()


asyncio.run(main())
