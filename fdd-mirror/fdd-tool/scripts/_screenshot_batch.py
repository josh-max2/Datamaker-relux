"""Screenshot the new + updated pages from this batch for visual verification."""
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

        # 1. Contact page
        await page.goto(f"{BASE}/contact/")
        await page.screenshot(path=f"{SHOTS}/contact_page.png")
        print("contact h1:", (await page.text_content("h1")).strip())

        # 2. Compare page — scroll to FAQ section
        await page.goto(f"{BASE}/compare/bath-fitter-vs-re-bath/")
        # Click open the first FAQ for visual proof
        await page.evaluate("""() => {
            const h = [...document.querySelectorAll('h2')].find(h => h.innerText.startsWith('Frequently asked'));
            if (h) h.scrollIntoView({block: 'start'});
        }""")
        await page.wait_for_timeout(300)
        await page.evaluate("""() => {
            const d = document.querySelector('section.faq details.faq-item');
            if (d) d.setAttribute('open', '');
        }""")
        await page.screenshot(path=f"{SHOTS}/compare_with_faqs.png")
        faq_count = await page.evaluate("() => document.querySelectorAll('section.faq details.faq-item').length")
        print(f"compare page FAQ count: {faq_count}")

        # 3. Footer (whole page screenshot of contact, then check footer)
        await page.goto(f"{BASE}/")
        # Scroll to footer
        await page.evaluate("() => document.querySelector('footer').scrollIntoView()")
        await page.wait_for_timeout(300)
        await page.screenshot(path=f"{SHOTS}/footer_signup_area.png")
        footer_form = await page.query_selector("form.footer-signup")
        # Should NOT be there when FORMSPREE_ID is placeholder
        print(f"footer signup form visible (should be None since placeholder): {footer_form}")

        # 4. Home page (verify Organization+WebSite schema rendered)
        await page.goto(f"{BASE}/")
        ld_count = await page.evaluate("() => document.querySelectorAll('script[type=\"application/ld+json\"]').length")
        print(f"home JSON-LD scripts: {ld_count}")
        await page.screenshot(path=f"{SHOTS}/home_page.png")

        await browser.close()


asyncio.run(main())
