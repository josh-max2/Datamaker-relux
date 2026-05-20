"""F3.2 verification: budget filter slider works, count updates, URL syncs, brands without inv data always show."""
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

        # Cleaning has 5 brands — good test set
        await page.goto(f"{BASE}/category/home-services-cleaning/")
        await page.wait_for_selector("#budget-slider")

        # Initial state: all brands visible
        initial_count = await page.text_content("#budget-count")
        total_rows = await page.evaluate("() => document.querySelectorAll('#category-table tbody tr').length")
        print(f"initial visible: {initial_count} / total rows: {total_rows}")
        assert int(initial_count) == total_rows

        # Read each row's inv-low to know what to test
        rows_data = await page.evaluate("""() => Array.from(document.querySelectorAll('#category-table tbody tr')).map(r => ({
            brand: r.cells[0].innerText.trim(),
            invLow: r.dataset.invLow
        }))""")
        print("rows data:")
        for r in rows_data:
            print(f"  {r['brand']:30} inv_low={r['invLow']!r}")

        # Drag slider down to $100,000 — should hide brands where inv_low > 100000 (most cleaning brands)
        await page.evaluate("""() => {
            const s = document.getElementById('budget-slider');
            s.value = '100000';
            s.dispatchEvent(new Event('input', {bubbles: true}));
        }""")
        await page.wait_for_timeout(200)

        budget_display = await page.text_content("#budget-display")
        visible_after = await page.text_content("#budget-count")
        url = page.url
        print(f"after slider→100k: display={budget_display!r} visible={visible_after} url={url}")
        assert "$100,000" in budget_display
        assert "budget=100000" in url

        # Count expected: rows where invLow blank/0 (always shown) OR <= 100000
        expected = sum(
            1 for r in rows_data
            if r["invLow"] in ("", "0") or float(r["invLow"] or 0) <= 100000
        )
        print(f"expected visible: {expected}, actual: {visible_after}")
        assert int(visible_after) == expected

        # Verify brands without inv data are still visible
        no_inv_brands = [r["brand"] for r in rows_data if r["invLow"] in ("", "0")]
        if no_inv_brands:
            for brand in no_inv_brands:
                visible = await page.evaluate(f"""(brandName) => {{
                    const rows = document.querySelectorAll('#category-table tbody tr');
                    for (const r of rows) {{
                        if (r.cells[0].innerText.trim() === brandName) {{
                            return r.style.display !== 'none';
                        }}
                    }}
                    return false;
                }}""", brand)
                assert visible, f"brand {brand} without inv data should always be visible"
            print(f"verified {len(no_inv_brands)} no-inv-data brand(s) always visible: {no_inv_brands}")

        # Take a screenshot showing filter applied
        await page.evaluate("() => document.querySelector('.budget-filter').scrollIntoView({block: 'start'})")
        await page.screenshot(path=f"{SHOTS}/budget_filter_applied.png")

        # Reset button restores all
        await page.click("#budget-reset")
        await page.wait_for_timeout(200)
        reset_count = await page.text_content("#budget-count")
        print(f"after reset: visible={reset_count}")
        assert int(reset_count) == total_rows

        # URL-share test: load with ?budget=200000
        await page.goto(f"{BASE}/category/home-services-cleaning/?budget=200000")
        await page.wait_for_selector("#budget-slider")
        await page.wait_for_timeout(150)
        url_init = await page.text_content("#budget-display")
        url_visible = await page.text_content("#budget-count")
        print(f"URL-load budget=200000: display={url_init!r} visible={url_visible}")
        assert "$200,000" in url_init
        expected_200k = sum(
            1 for r in rows_data
            if r["invLow"] in ("", "0") or float(r["invLow"] or 0) <= 200000
        )
        assert int(url_visible) == expected_200k

        print("ok F3.2 budget filter — slider + count + URL share + reset all work")
        await browser.close()


asyncio.run(main())
