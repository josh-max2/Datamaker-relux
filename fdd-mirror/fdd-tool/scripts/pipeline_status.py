"""One-command pipeline health dashboard.

Shows: DB state, PDF inventory, extraction outcomes, dedup savings,
error counts, recent activity. Safe to run anytime — read-only.

Usage: uv run python scripts/pipeline_status.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
PDF_DIR = Path("data/wi_scrape")
OUTPUT_DIR = Path("output")
DB_PATH = Path("data/db.sqlite")
MANIFEST = OUTPUT_DIR / "_extract_loop.json"
SEARCH_CACHE = OUTPUT_DIR / "_search_cache.json"
SHA_INDEX = OUTPUT_DIR / "_sha_to_stem.json"
CONTENT_INDEX = OUTPUT_DIR / "_content_to_stem.json"
CANDIDATES = Path("scripts/candidates.txt")

# Estimated cost per claude -p invocation (Max plan token equivalent at API rates)
# Used only for displaying "cost avoided via dedup" — Max plan itself doesn't bill.
APPROX_COST_PER_EXTRACTION_USD = 0.35


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def main() -> None:
    print(f"FranchiseDepth pipeline status — {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # === Database state ===
    section("Database (data/db.sqlite)")
    if not DB_PATH.exists():
        print("  no database yet")
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        for table in ("franchisors", "fdds", "item19_records", "item20_locations", "fees_and_investment"):
            n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table:25} {n:>6,}")
        # Breakdown by industry
        print("  by industry:")
        for row in conn.execute("""
            SELECT industry, COUNT(*) AS n FROM franchisors
            GROUP BY industry ORDER BY n DESC
        """):
            print(f"    {row['industry'] or '(none)':40} {row['n']:>4}")
        # Brands with item19
        has_19 = conn.execute("""
            SELECT COUNT(*) FROM fdds WHERE has_item19 = 1
        """).fetchone()[0]
        total_fdds = conn.execute("SELECT COUNT(*) FROM fdds").fetchone()[0]
        print(f"  FDDs with Item 19: {has_19}/{total_fdds} ({100*has_19/total_fdds:.0f}%)" if total_fdds else "  no FDDs")
        conn.close()

    # === Candidate funnel ===
    section("Candidate funnel (scrape_loop)")
    if CANDIDATES.exists():
        cands = [ln.strip() for ln in CANDIDATES.read_text(encoding="utf-8").splitlines() if ln.strip()]
        print(f"  candidates.txt:        {len(cands):>5}")
    cache = {}
    if SEARCH_CACHE.exists():
        try:
            cache = json.loads(SEARCH_CACHE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    print(f"  previously searched:   {len(cache):>5}")
    if cache:
        statuses = Counter(v.get("status", "?") for v in cache.values())
        for s, n in sorted(statuses.items(), key=lambda kv: -kv[1]):
            print(f"    {s:30} {n:>4}")

    # === PDF inventory ===
    section("PDF inventory (data/wi_scrape/)")
    if not PDF_DIR.exists():
        print("  no PDF dir")
    else:
        pdfs = list(PDF_DIR.glob("*.pdf"))
        total_size_mb = sum(p.stat().st_size for p in pdfs) / 1024 / 1024
        print(f"  PDFs downloaded:       {len(pdfs):>5}  ({total_size_mb:.1f} MB total)")
        # How many have output/{stem}/metadata.json
        extracted = sum(1 for p in pdfs if (OUTPUT_DIR / p.stem / "metadata.json").exists())
        print(f"  with metadata.json:    {extracted:>5}")
        print(f"  pending extraction:    {len(pdfs) - extracted:>5}")

    # === Extraction outcomes ===
    section("Extraction outcomes (_extract_loop.json)")
    if not MANIFEST.exists():
        print("  no manifest yet")
    else:
        try:
            m = json.loads(MANIFEST.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print("  manifest is malformed")
            return
        exts = m.get("extractions", {})
        if not exts:
            print("  no extractions yet")
        else:
            ok = sum(1 for e in exts.values() if e.get("ok"))
            failed = sum(1 for e in exts.values() if not e.get("ok") and not e.get("preflight_failed"))
            preflight_skipped = sum(1 for e in exts.values() if e.get("preflight_failed"))
            sha_deduped = sum(1 for e in exts.values() if e.get("dedup_method") == "sha256")
            content_deduped = sum(1 for e in exts.values()
                                   if e.get("dedup_method", "").startswith("content"))
            llm_extracted = ok - sha_deduped - content_deduped
            print(f"  total tracked:         {len(exts):>5}")
            print(f"  ok (LLM extracted):    {llm_extracted:>5}")
            print(f"  ok (SHA dedup):        {sha_deduped:>5}")
            print(f"  ok (content dedup):    {content_deduped:>5}")
            print(f"  preflight rejected:    {preflight_skipped:>5}  (saved ~${preflight_skipped * APPROX_COST_PER_EXTRACTION_USD:.2f})")
            print(f"  failed:                {failed:>5}")
            cost_avoided = (sha_deduped + content_deduped + preflight_skipped) * APPROX_COST_PER_EXTRACTION_USD
            print(f"  ~$ avoided via dedup:  ${cost_avoided:.2f} ({sha_deduped + content_deduped + preflight_skipped} extractions skipped)")
            # Recent failures
            recent_failures = [
                (stem, e) for stem, e in exts.items()
                if not e.get("ok") and not e.get("preflight_failed")
            ]
            recent_failures.sort(key=lambda kv: kv[1].get("last_attempt_at", ""), reverse=True)
            if recent_failures:
                print(f"  last 5 failures:")
                for stem, e in recent_failures[:5]:
                    reason = e.get("validation_reason") or e.get("last_output_tail", "")[-150:].strip()
                    print(f"    {stem:50} attempts={e.get('attempt_count', 1)}  {reason[:120]!r}")
            # Average extraction time (LLM only)
            elapsed_times = [
                e.get("elapsed_sec", 0) for e in exts.values()
                if e.get("ok") and not e.get("dedup_method") and not e.get("preflight_failed")
            ]
            if elapsed_times:
                avg = sum(elapsed_times) / len(elapsed_times)
                print(f"  avg LLM extract time:  {avg:.0f}s  ({min(elapsed_times)}-{max(elapsed_times)}s range)")

    # === Dedup indices ===
    section("Dedup indices")
    if SHA_INDEX.exists():
        sha_idx = json.loads(SHA_INDEX.read_text(encoding="utf-8"))
        print(f"  SHA → stem entries:    {len(sha_idx):>5}")
    if CONTENT_INDEX.exists():
        content_idx = json.loads(CONTENT_INDEX.read_text(encoding="utf-8"))
        print(f"  content-key entries:   {len(content_idx):>5}")
        # Sample content keys
        sample = list(content_idx.items())[:3]
        for k, v in sample:
            print(f"    {k:50} → {v}")

    # === Site state ===
    section("Generated site")
    if DOCS_DIR.exists():
        html_pages = sum(1 for _ in DOCS_DIR.rglob("*.html"))
        print(f"  HTML pages:            {html_pages:>5}")
        if (DOCS_DIR / "sitemap.xml").exists():
            sitemap_urls = (DOCS_DIR / "sitemap.xml").read_text(encoding="utf-8").count("<url>")
            print(f"  URLs in sitemap.xml:   {sitemap_urls:>5}")
        last_built = (DOCS_DIR / "index.html").stat().st_mtime
        if last_built:
            print(f"  last regen:            {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_built))}")

    print()


if __name__ == "__main__":
    main()
