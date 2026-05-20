"""Aggregate token usage across the latest extraction run.

Reads output/_extract_loop.json and summarizes:
- Total brands processed
- Per-source breakdown: LLM extractions, SHA-deduped, content-deduped,
  pre-flight rejected, failed
- Total tokens (input, output, cache hit, cache miss) and $ equivalent
- Average per LLM-extracted brand

Usage:
    uv run python scripts/token_report.py             # all-time
    uv run python scripts/token_report.py --since-id N  # only extractions added in this run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

MANIFEST = Path("output/_extract_loop.json")

# Anthropic Sonnet 4.6 rates (USD per million tokens)
INPUT_RATE = 3.00
OUTPUT_RATE = 15.00
CACHE_WRITE_RATE = 3.75  # input × 1.25
CACHE_READ_RATE = 0.30   # input × 0.10


def cost_estimate(usage: dict) -> float:
    """Compute USD cost from token counts at Sonnet 4.6 API rates."""
    in_t = usage.get("input_tokens", 0) or 0
    out_t = usage.get("output_tokens", 0) or 0
    cache_w = usage.get("cache_creation_input_tokens", 0) or 0
    cache_r = usage.get("cache_read_input_tokens", 0) or 0
    # If total_cost_usd is provided directly (Max plan reports actual), prefer it
    if usage.get("total_cost_usd") is not None:
        return float(usage["total_cost_usd"])
    return (
        in_t * INPUT_RATE / 1_000_000
        + out_t * OUTPUT_RATE / 1_000_000
        + cache_w * CACHE_WRITE_RATE / 1_000_000
        + cache_r * CACHE_READ_RATE / 1_000_000
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-failed", action="store_true",
                        help="Include failed-extraction token costs too")
    args = parser.parse_args()

    if not MANIFEST.exists():
        print(f"No manifest at {MANIFEST}. Run scripts/extract_loop.py first.")
        sys.exit(1)

    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    exts = m.get("extractions", {})
    if not exts:
        print("Manifest has no extractions yet.")
        sys.exit(0)

    n_total = len(exts)
    n_ok = sum(1 for e in exts.values() if e.get("ok"))
    n_failed = sum(1 for e in exts.values()
                   if not e.get("ok") and not e.get("preflight_failed") and not e.get("dedup_copied_from"))
    n_sha = sum(1 for e in exts.values() if e.get("dedup_method") == "sha256")
    n_content = sum(1 for e in exts.values()
                    if (e.get("dedup_method") or "").startswith("content"))
    n_preflight = sum(1 for e in exts.values() if e.get("preflight_failed"))
    n_llm = n_ok - n_sha - n_content

    # Aggregate token usage across LLM extractions (and failures if requested)
    total_in = total_out = total_cache_w = total_cache_r = 0
    total_cost = 0.0
    llm_with_usage = []
    for stem, e in exts.items():
        usage = e.get("usage")
        if not usage:
            continue
        is_ok_llm = e.get("ok") and not e.get("dedup_method")
        is_failed = not e.get("ok") and not e.get("preflight_failed") and not e.get("dedup_method")
        if is_ok_llm or (args.include_failed and is_failed):
            in_t = usage.get("input_tokens", 0) or 0
            out_t = usage.get("output_tokens", 0) or 0
            cw = usage.get("cache_creation_input_tokens", 0) or 0
            cr = usage.get("cache_read_input_tokens", 0) or 0
            cost = cost_estimate(usage)
            total_in += in_t
            total_out += out_t
            total_cache_w += cw
            total_cache_r += cr
            total_cost += cost
            if is_ok_llm:
                llm_with_usage.append((stem, in_t, out_t, cw, cr, cost,
                                       e.get("elapsed_sec", 0)))

    print(f"=== Extraction Token Report ({MANIFEST}) ===\n")
    print(f"Total tracked:           {n_total}")
    print(f"  ok (LLM extracted):    {n_llm}")
    print(f"  ok (SHA dedup):        {n_sha}   [LLM cost avoided]")
    print(f"  ok (content dedup):    {n_content}   [LLM cost avoided]")
    print(f"  preflight rejected:    {n_preflight}   [LLM cost avoided]")
    print(f"  failed:                {n_failed}")
    print()
    print(f"=== LLM extractions only (cost incurred) ===")
    if n_llm == 0:
        print("  (none yet)")
        return
    print(f"  count:                 {n_llm}")
    print(f"  input tokens:          {total_in:>15,}")
    print(f"  output tokens:         {total_out:>15,}")
    if total_cache_w:
        print(f"  cache-write tokens:    {total_cache_w:>15,}")
    if total_cache_r:
        print(f"  cache-read tokens:     {total_cache_r:>15,}")
    print(f"  total in+out:          {total_in + total_out:>15,}")
    print(f"  $ equivalent (API):    ${total_cost:.2f}")
    print()
    if n_llm > 0:
        avg_in = total_in / n_llm
        avg_out = total_out / n_llm
        avg_cost = total_cost / n_llm
        avg_total = (total_in + total_out + total_cache_w + total_cache_r) / n_llm
        print(f"  per-extraction avg:    in={avg_in:>8,.0f}  out={avg_out:>7,.0f}  total={avg_total:>8,.0f}  ${avg_cost:.4f}")

    # Dedup savings — what would those have cost if we'd LLM'd them too
    if n_llm > 0:
        per_llm_cost = total_cost / n_llm
        avoided_cost = (n_sha + n_content + n_preflight) * per_llm_cost
        print(f"  $ avoided via dedup:   ${avoided_cost:.2f}   ({n_sha + n_content + n_preflight} extractions skipped at avg ${per_llm_cost:.4f}/each)")

    # Sample top + bottom
    if llm_with_usage:
        llm_with_usage.sort(key=lambda x: x[1] + x[2])  # by total tokens
        print()
        print(f"  Cheapest extractions:")
        for stem, i, o, _, _, c, t in llm_with_usage[:3]:
            print(f"    {stem:50}  in={i:>7,}  out={o:>6,}  ${c:.4f}  {t}s")
        print(f"  Most expensive extractions:")
        for stem, i, o, _, _, c, t in llm_with_usage[-3:]:
            print(f"    {stem:50}  in={i:>7,}  out={o:>6,}  ${c:.4f}  {t}s")


if __name__ == "__main__":
    main()
