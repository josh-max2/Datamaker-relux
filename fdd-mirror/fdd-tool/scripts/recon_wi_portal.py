"""Reconnaissance: programmatically inspect the WI franchise search flow.

Step-by-step:
  1. Open MainSearch.aspx
  2. Inspect the form (input names, form action, hidden ASP.NET fields)
  3. Fill the search box with 'Mr. Rooter'
  4. Submit
  5. Capture the result page HTML + any clickable links
  6. If results visible, navigate to one detail page
  7. Inspect detail page for the PDF download mechanism

Outputs all observations to stdout. No PDF download yet — that's the scraper script.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")

SEARCH_URL = "https://apps.dfi.wi.gov/apps/FranchiseSearch/MainSearch.aspx"
QUERY = "Mr. Rooter"


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ))
        page = ctx.new_page()

        # Capture all network requests for inspection
        requests: list[tuple[str, str]] = []
        page.on("request", lambda r: requests.append((r.method, r.url)))

        print(f"[1] GET {SEARCH_URL}")
        page.goto(SEARCH_URL, wait_until="networkidle")
        print(f"    title={page.title()!r}, url={page.url}")

        print("\n[2] Form inputs on MainSearch.aspx:")
        inputs = page.eval_on_selector_all(
            "input, select, button",
            "els => els.map(e => ({tag: e.tagName, type: e.type, name: e.name, id: e.id, value: (e.value||'').slice(0,40)}))"
        )
        for inp in inputs:
            print(f"    {inp}")

        # Search box is typically the only visible text input. Find it.
        search_input_selector = None
        for inp in inputs:
            if inp.get("tag") == "INPUT" and inp.get("type") == "text" and inp.get("name"):
                search_input_selector = f"input[name='{inp['name']}']"
                print(f"\n  Picked search box: {search_input_selector}")
                break

        if not search_input_selector:
            print("  !! Could not identify search input — aborting")
            return

        print(f"\n[3] Filling with {QUERY!r}")
        page.fill(search_input_selector, QUERY)

        # Find the submit button
        submit_selector = None
        for inp in inputs:
            if inp.get("type") in ("submit", "button") and ("search" in (inp.get("value", "") or "").lower() or "search" in (inp.get("id", "") or "").lower()):
                if inp.get("id"):
                    submit_selector = f"#{inp['id']}"
                elif inp.get("name"):
                    submit_selector = f"[name='{inp['name']}']"
                break
        if not submit_selector:
            # Fall back to the first submit button
            for inp in inputs:
                if inp.get("type") == "submit":
                    if inp.get("id"):
                        submit_selector = f"#{inp['id']}"
                    elif inp.get("name"):
                        submit_selector = f"[name='{inp['name']}']"
                    break

        print(f"  Submit selector: {submit_selector}")

        print("\n[4] Submitting search...")
        if submit_selector:
            page.click(submit_selector)
        else:
            page.press(search_input_selector, "Enter")
        page.wait_for_load_state("networkidle")
        print(f"    after submit: url={page.url}")
        print(f"    title={page.title()!r}")

        print("\n[5] Result page links (first 30, filtered):")
        links = page.eval_on_selector_all(
            "a",
            "els => els.map(e => ({text: (e.innerText||'').trim().slice(0,80), href: e.href})).filter(l => l.text && l.href)"
        )
        for link in links[:30]:
            if "FranchiseSearch" in link.get("href", "") or "details" in link.get("href", "").lower():
                print(f"    {link}")

        # Also: look for results-table rows specifically
        print("\n[5b] Any visible 'Mr Rooter' / 'Rooter' text on the result page:")
        body_text = page.inner_text("body")
        for line in body_text.split("\n"):
            if "rooter" in line.lower():
                print(f"    > {line.strip()[:200]}")

        # Find the first detail-page link
        detail_url = None
        for link in links:
            if "details.aspx" in link.get("href", "").lower():
                detail_url = link["href"]
                print(f"\n  Picked detail URL: {detail_url}")
                break

        if not detail_url:
            print("\n  !! No details.aspx link found in result page. Saving result HTML for inspection.")
            Path("scripts/_recon_search_result.html").write_text(page.content(), encoding="utf-8")
            print(f"     -> saved {Path('scripts/_recon_search_result.html').resolve()}")
        else:
            print(f"\n[6] GET detail page: {detail_url}")
            page.goto(detail_url, wait_until="networkidle")
            print(f"    title={page.title()!r}, url={page.url}")

            print("\n[7] Detail page links / buttons / forms (looking for PDF download mechanism):")
            detail_links = page.eval_on_selector_all(
                "a, button, input[type='submit'], input[type='button']",
                "els => els.map(e => ({tag: e.tagName, type: e.type||'', text: (e.innerText||e.value||'').trim().slice(0,80), href: e.href||'', onclick: (e.getAttribute('onclick')||'').slice(0,200), name: e.name||'', id: e.id||''}))"
            )
            for el in detail_links:
                text = el.get("text", "")
                onclick = el.get("onclick", "")
                href = el.get("href", "")
                if "download" in text.lower() or "pdf" in text.lower() or "pdf" in href.lower() or "download" in onclick.lower() or "doPostBack" in onclick:
                    print(f"    {el}")

            # Save detail page HTML for offline inspection too
            Path("scripts/_recon_detail.html").write_text(page.content(), encoding="utf-8")
            print(f"\n    saved detail HTML -> {Path('scripts/_recon_detail.html').resolve()}")

        print("\n[8] All non-asset network requests (search + detail fetch chain):")
        for method, url in requests:
            if any(s in url for s in (".css", ".js", ".png", ".gif", ".woff", ".ico", "google", "fonts")):
                continue
            print(f"    {method} {url}")

        browser.close()


if __name__ == "__main__":
    main()
