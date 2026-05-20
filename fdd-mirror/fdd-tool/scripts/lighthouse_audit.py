"""Wrapper around Lighthouse CLI to audit the locally-served docs/ across key pages.

Prerequisites:
  npm install -g lighthouse
  (and Chrome installed)

Usage:
  # In one shell:
  uv run python scripts/_serve_docs.py

  # In another:
  uv run python scripts/lighthouse_audit.py [--pages "home brand category compare"]

Reports go to scripts/_lighthouse_reports/ as JSON + HTML.

Target: 95+ across Performance, Accessibility, Best Practices, SEO on every page type.
This is a pre-launch sanity check — don't run against production unless you want crUX noise.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://127.0.0.1:8765/Parser"
REPORT_DIR = Path("scripts/_lighthouse_reports")
TARGET_SCORE = 0.95  # 95+

PAGE_SET = {
    "home":       "/",
    "brand":      "/franchise/re-bath/",
    "category":   "/category/home-services-cleaning/",
    "compare":    "/compare/bath-fitter-vs-re-bath/",
    "state":      "/state/california/",
    "guide":      "/guides/understanding-item-19/",
    "methodology": "/methodology/",
    "about":      "/about/",
    "contact":    "/contact/",
}


def find_lighthouse() -> str:
    for name in ("lighthouse", "lighthouse.cmd"):
        path = shutil.which(name)
        if path:
            return path
    print("ERROR: lighthouse CLI not found. Install with:  npm install -g lighthouse")
    sys.exit(1)


def run_one(lh: str, page: str, url: str) -> dict:
    out = REPORT_DIR / f"{page}.report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        lh, url,
        "--quiet",
        "--chrome-flags=--headless",
        "--output=json",
        f"--output-path={out}",
        "--only-categories=performance,accessibility,best-practices,seo",
    ]
    print(f"  auditing {page:12} {url}")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        print(f"    FAILED: {proc.stderr[-300:]}")
        return {}
    data = json.loads(out.read_text(encoding="utf-8"))
    scores = {k: round(v["score"] * 100, 1) if v.get("score") is not None else None
              for k, v in data["categories"].items()}
    return scores


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--pages", nargs="+", default=list(PAGE_SET.keys()))
    args = p.parse_args()

    lh = find_lighthouse()
    print(f"=== Lighthouse audit (target {int(TARGET_SCORE*100)}+ on all axes) ===")
    print(f"  reports → {REPORT_DIR.resolve()}\n")

    results = {}
    for page in args.pages:
        path = PAGE_SET.get(page)
        if not path:
            print(f"  unknown page key: {page}; skipping")
            continue
        results[page] = run_one(lh, page, BASE + path)

    print("\n=== Summary ===")
    fails = 0
    for page, scores in results.items():
        if not scores:
            continue
        line = f"  {page:12}"
        for axis, score in scores.items():
            tag = " " if (score or 0) >= TARGET_SCORE * 100 else "!"
            if tag == "!": fails += 1
            line += f"  {axis[:6]}={score}{tag}"
        print(line)
    print(f"\n{fails} axis-page combinations below {int(TARGET_SCORE*100)}.")


if __name__ == "__main__":
    main()
