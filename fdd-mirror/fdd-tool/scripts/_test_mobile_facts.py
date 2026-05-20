"""F9.2 verification: on mobile viewport, fact box shows only 4 facts + toggle button; expanding shows all."""
import asyncio, sys
from playwright.async_api import async_playwright

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

BASE = "http://127.0.0.1:8765/Parser"
SHOTS = "scripts/_screenshots/_audit"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()

        # Mobile viewport (iPhone 13 width)
        mobile = await browser.new_context(viewport={"width": 390, "height": 844})
        page = await mobile.new_page()

        # Re-Bath has 5 facts (Industry, Total investment, Liquid capital, Total outlets, Closure rate)
        await page.goto(f"{BASE}/franchise/re-bath/")
        await page.wait_for_selector(".facts")

        total_facts = await page.evaluate("() => document.querySelectorAll('.facts .fact').length")
        print(f"total .fact elements: {total_facts}")
        assert total_facts >= 5

        # On mobile, only first 4 should be visible
        visible_facts = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('.facts .fact'))
                .filter(f => f.offsetParent !== null).length;
        }""")
        print(f"mobile visible facts before expand: {visible_facts}")
        assert visible_facts == 4, f"expected 4 visible, got {visible_facts}"

        # Toggle button must be visible
        toggle_visible = await page.is_visible(".facts-toggle")
        print(f"toggle button visible: {toggle_visible}")
        assert toggle_visible

        # Screenshot collapsed
        await page.evaluate("() => document.querySelector('.facts').scrollIntoView({block: 'start'})")
        await page.screenshot(path=f"{SHOTS}/mobile_facts_collapsed.png")

        # Click to expand
        await page.click(".facts-toggle")
        await page.wait_for_timeout(150)

        visible_after = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('.facts .fact'))
                .filter(f => f.offsetParent !== null).length;
        }""")
        print(f"mobile visible facts after expand: {visible_after}")
        assert visible_after == total_facts

        # Label should change
        label = await page.text_content(".facts-toggle-label")
        print(f"toggle label after expand: {label!r}")
        assert "fewer" in label.lower()

        # aria-expanded
        aria = await page.get_attribute(".facts-toggle", "aria-expanded")
        assert aria == "true"

        await page.screenshot(path=f"{SHOTS}/mobile_facts_expanded.png")

        # Desktop viewport: button should be hidden, all facts visible
        desktop = await browser.new_context(viewport={"width": 1280, "height": 800})
        d_page = await desktop.new_page()
        await d_page.goto(f"{BASE}/franchise/re-bath/")
        d_visible = await d_page.evaluate("""() => {
            return Array.from(document.querySelectorAll('.facts .fact'))
                .filter(f => f.offsetParent !== null).length;
        }""")
        print(f"desktop visible facts: {d_visible}")
        assert d_visible == total_facts, f"desktop should show all facts; got {d_visible}/{total_facts}"
        d_toggle_visible = await d_page.is_visible(".facts-toggle")
        print(f"desktop toggle visible: {d_toggle_visible}")
        assert not d_toggle_visible, "toggle should be hidden on desktop"

        print("ok F9.2 mobile fact-box accordion — mobile collapses to 4, expand works, desktop unchanged")
        await browser.close()


asyncio.run(main())
