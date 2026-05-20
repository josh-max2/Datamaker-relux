"""Phase 1 first-30: hand-coded WI scraper for a single franchisor (Mr. Rooter).

No abstraction yet. Just: search the portal → pick the currently-Registered filing →
click Download → save PDF → hash it.

Architectural seam test: feed the output into src.extract afterwards to confirm
the scraper output is compatible with the existing pipeline.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")

SEARCH_URL = "https://apps.dfi.wi.gov/apps/FranchiseSearch/MainSearch.aspx"
QUERY = "Mr. Rooter"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

OUT_DIR = Path("data/wi_scrape")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA, accept_downloads=True)
        page = ctx.new_page()

        print(f"[1] Loading search page...")
        page.goto(SEARCH_URL, wait_until="networkidle")

        print(f"[2] Searching for {QUERY!r}...")
        page.fill("input[name='txtName']", QUERY)
        page.click("#btnSearch")
        page.wait_for_load_state("networkidle")

        # The result rows are plain HTML — we want the row whose status is "Registered"
        # (i.e., not "Expired"). Pull the table rows via inner_text and parse.
        print(f"[3] Parsing results to find the currently-Registered filing...")
        body = page.inner_text("body")
        registered_id = None
        for line in body.split("\n"):
            line_stripped = line.strip()
            # Format observed during recon:
            # "640790\tMr. Rooter SPV LLC\tMr. Rooter\t4/2/2026\t4/2/2027\tRegistered\tDetails"
            if "Registered" in line_stripped and "Rooter" in line_stripped:
                m = re.match(r"^(\d{6})\b", line_stripped)
                if m:
                    registered_id = m.group(1)
                    print(f"    -> id={registered_id}  ({line_stripped[:100]!r})")
                    break

        if not registered_id:
            print("    !! No 'Registered' Mr. Rooter row found in results.")
            browser.close()
            sys.exit(1)

        # The "Details" link for that row — find by matching the id in the href
        print(f"[4] Locating Details link for id={registered_id}...")
        details_href = page.eval_on_selector_all(
            "a",
            f"els => els.filter(a => a.href && a.href.includes('id={registered_id}')).map(a => a.href)"
        )
        if not details_href:
            print(f"    !! No Details link found containing id={registered_id}")
            browser.close()
            sys.exit(1)
        detail_url = details_href[0]
        print(f"    -> {detail_url}")

        print(f"[5] Loading detail page...")
        page.goto(detail_url, wait_until="networkidle")

        # Click the Download button and capture the download
        print(f"[6] Clicking Download...")
        with page.expect_download(timeout=60000) as dl_info:
            page.click("#upload_downloadFile")
        download = dl_info.value
        suggested_name = download.suggested_filename
        target = OUT_DIR / f"mr_rooter_wi_id{registered_id}.pdf"
        download.save_as(str(target))
        print(f"    -> saved {target} (suggested: {suggested_name})")

        # Hash
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        size_mb = target.stat().st_size / 1024 / 1024
        print(f"\n[7] Verification:")
        print(f"    path:    {target.resolve()}")
        print(f"    size:    {size_mb:.2f} MB")
        print(f"    sha256:  {digest}")
        print(f"    source:  {detail_url}")

        browser.close()


if __name__ == "__main__":
    main()
