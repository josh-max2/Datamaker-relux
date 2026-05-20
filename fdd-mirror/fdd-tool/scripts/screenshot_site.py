"""Screenshot key pages of the site for visual review.

NOTE: Site uses /Parser/ URL prefix for GitHub Pages, so on localhost we need to
hit /Parser/... too. Since the local server serves docs/ at root, we instead
override BASE_URL and follow the prefix-stripped paths.
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path("scripts/_screenshots")
OUT.mkdir(parents=True, exist_ok=True)

# localhost server serves docs/ at /. The site was built with /Parser/ prefix,
# so absolute paths in HTML will be like /Parser/franchise/.../. We just navigate
# straight to file paths using the prefixless form by stripping /Parser from URLs
# on the fly. Simpler: directly navigate to the underlying file structure.

BASE = "http://localhost:8765"  # docs/ root → docs/index.html
# But the HTML links inside say /Parser/... — they'll 404 against this server.
# We use route() to rewrite or just navigate manually to the file paths.

PAGES = [
    ("index", "/"),
    ("about", "/about/"),
    ("category_home_services", "/category/home-services/"),
    ("brand_re_bath", "/franchise/re-bath/"),
    ("brand_crumbl", "/franchise/crumbl/"),
    ("brand_servpro_no_fpr", "/franchise/servpro/"),
    ("brand_mr_rooter_multicohort", "/franchise/mr-rooter/"),
    ("brand_mr_handyman_ownership_cohorts", "/franchise/mr-handyman/"),
]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for w in (1280, 375):  # desktop, mobile
            ctx = browser.new_context(viewport={"width": w, "height": 800})
            # Rewrite /Parser/... → / on the local server
            ctx.route("**/Parser/**", lambda route: route.continue_(
                url=route.request.url.replace("/Parser/", "/")))
            page = ctx.new_page()
            for name, path in PAGES:
                url = f"{BASE}{path}"
                try:
                    page.goto(url, wait_until="networkidle", timeout=20000)
                    out_file = OUT / f"{name}_{w}.png"
                    page.screenshot(path=str(out_file), full_page=True)
                    print(f"  ok {name} @ {w}px -> {out_file}")
                except Exception as e:
                    print(f"  !! {name} @ {w}px: {e}")
            ctx.close()
        browser.close()


if __name__ == "__main__":
    main()
