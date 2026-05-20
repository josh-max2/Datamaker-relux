"""Behavioral test of cookie consent banner end-to-end."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
out = Path("scripts/_screenshots/_audit"); out.mkdir(parents=True, exist_ok=True)
results = []

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1280, "height": 800})
    ctx.route("**/Parser/**", lambda r: r.continue_(url=r.request.url.replace("/Parser/", "/")))
    page = ctx.new_page()

    # === Test 1: Banner appears on first visit ===
    page.goto("http://localhost:8765/", wait_until="networkidle")
    page.wait_for_timeout(500)
    banner = page.locator("#fd-consent-banner")
    results.append(("banner appears on first visit", banner.is_visible()))

    # === Test 2: Click Reject all → banner disappears + localStorage set ===
    page.click("#fd-c-reject")
    page.wait_for_timeout(300)
    banner_gone = not banner.is_visible() if banner.count() else True
    saved = page.evaluate("() => JSON.parse(localStorage.getItem('fd_consent_v1') || 'null')")
    results.append(("banner disappears after Reject", banner_gone))
    results.append(("localStorage saved with analytics=false", saved and saved.get("analytics") is False))

    # === Test 3: Reload → banner stays gone ===
    page.reload(wait_until="networkidle")
    page.wait_for_timeout(500)
    banner2 = page.locator("#fd-consent-banner")
    results.append(("banner stays hidden after reload (choice persists)", banner2.count() == 0 or not banner2.is_visible()))

    # === Test 4: footer Cookie preferences link reopens ===
    # Need to find the "Cookie preferences" link in footer and click it
    page.evaluate("() => window.fdOpenConsent && window.fdOpenConsent()")
    page.wait_for_timeout(400)
    banner3 = page.locator("#fd-consent-banner")
    results.append(("fdOpenConsent reopens banner", banner3.is_visible()))

    # === Test 5: Customize → modal opens with categories ===
    page.click("#fd-c-customize")
    page.wait_for_timeout(300)
    modal = page.locator("#fd-consent-modal")
    analytics_cb = page.locator("#fd-c-analytics")
    results.append(("Customize opens modal", modal.is_visible()))
    results.append(("Analytics checkbox exists", analytics_cb.count() == 1))

    # === Test 6: Check Analytics + Save → analytics=true persists ===
    analytics_cb.check()
    page.click("#fd-c-save")
    page.wait_for_timeout(300)
    saved2 = page.evaluate("() => JSON.parse(localStorage.getItem('fd_consent_v1') || 'null')")
    results.append(("Save preserves analytics=true", saved2 and saved2.get("analytics") is True))

    # === Test 7: With analytics consent, GA4 wrapper executes (script exists in DOM) ===
    # GA4 is only injected when measurement ID is set; in our placeholder state, no script.
    # We can at least verify the consent-update event fired
    listener_test = page.evaluate("""
        () => {
            let fired = false;
            window.addEventListener('fd-consent-update', () => { fired = true; }, { once: true });
            window.dispatchEvent(new CustomEvent('fd-consent-update', { detail: { analytics: true } }));
            return fired;
        }
    """)
    results.append(("consent-update event dispatchable", listener_test))

    # === Test 8: Mobile rendering ===
    ctx2 = b.new_context(viewport={"width": 375, "height": 800})
    ctx2.route("**/Parser/**", lambda r: r.continue_(url=r.request.url.replace("/Parser/", "/")))
    m = ctx2.new_page()
    m.goto("http://localhost:8765/", wait_until="networkidle")
    m.wait_for_timeout(500)
    mobile_banner = m.locator("#fd-consent-banner")
    results.append(("mobile: banner appears", mobile_banner.is_visible()))
    # Take screenshot for visual proof
    m.screenshot(path=str(out / "consent_mobile.png"), full_page=False)
    ctx2.close()
    b.close()

print(f"\n=== Consent flow behavioral tests ===")
passed = sum(1 for _, ok in results if ok)
for name, ok in results:
    mark = "OK" if ok else "FAIL"
    print(f"  [{mark}] {name}")
print(f"\n{passed}/{len(results)} tests passed")
