"""Run all 5 Item extractions on a single FDD PDF. Writes one JSON per Item to output/.

This module is THREAD-SAFE: each call to run() gets its own output directory
captured locally (no module globals). Multiple PDFs can be extracted
concurrently via threading or ProcessPoolExecutor without interfering.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from . import claude_client, pdf_utils, prompts

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output"


def run(pdf_path: Path, out_dir: Path | None = None, *, verbose: bool = True) -> Path:
    """Run all 5 Item extractions on one PDF.

    Args:
      pdf_path: source PDF.
      out_dir: directory to write JSONs to. Defaults to OUTPUT_DIR/<pdf-stem>.
        Each parallel worker should call with its own pdf_path; the default
        out_dir derivation keeps outputs separated naturally.
      verbose: print progress to stdout (set False under parallel workers
        where interleaved output is noise).

    Returns:
      The output directory path that was written to.
    """
    out_dir = out_dir or (OUTPUT_DIR / pdf_path.stem)
    out_dir.mkdir(parents=True, exist_ok=True)

    def _say(msg: str) -> None:
        if verbose:
            print(msg)

    def _save(name: str, payload: dict) -> Path:
        out = out_dir / f"{name}.json"
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return out

    _say(f"Output dir: {out_dir}")
    _say(f"Loading: {pdf_path}")
    pages = pdf_utils.extract_pages(pdf_path)
    body_start = pdf_utils.find_fdd_body_start(pages)
    _say(f"  {len(pages)} pages total; FDD body starts at PDF page {body_start}")

    # Discover where each Item begins/ends
    sections = {}
    for item_num in (5, 6, 7, 19, 20):
        sec = pdf_utils.find_section(pages, item_num, body_start_page=body_start)
        if sec:
            _say(f"  Item {item_num}: PDF pages {sec[0]}-{sec[1]} ({sec[1]-sec[0]+1} pages)")
        else:
            _say(f"  Item {item_num}: NOT FOUND")
        sections[item_num] = sec

    total_cost = 0.0
    summary = {"pdf": str(pdf_path), "body_start_page": body_start, "items": {}}

    # ----- Metadata (cover page) -----
    cover_page = pdf_utils.find_cover_page(pages)
    cover_range_start = max(1, cover_page - 1)
    cover_range_end = min(len(pages), cover_page + 2)
    _say(f"\n[1/6] Metadata (cover page {cover_page}, sending pages {cover_range_start}-{cover_range_end})...")
    cover_text = pdf_utils.section_text(pages, cover_range_start, cover_range_end)
    res = claude_client.extract(
        prompts.SYSTEM_PROMPT,
        prompts.METADATA_PROMPT.replace("{TEXT}", cover_text[:30000]),
    )
    _save("metadata", res.data)
    total_cost += res.cost_usd
    summary["items"]["metadata"] = {"cost_usd": round(res.cost_usd, 4),
                                     "input_tokens": res.input_tokens,
                                     "cached": res.cached_input_tokens,
                                     "output_tokens": res.output_tokens}
    _say(f"  saved -> {out_dir.name}/metadata.json  (${res.cost_usd:.4f})")

    # ----- Items 5, 6, 7 (text-only) -----
    text_only = {
        5: ("item5_initial_fee", prompts.ITEM5_PROMPT),
        6: ("item6_ongoing_fees", prompts.ITEM6_PROMPT),
        7: ("item7_investment", prompts.ITEM7_PROMPT),
    }
    for i, (item_num, (filename, prompt_tpl)) in enumerate(text_only.items(), start=2):
        sec = sections.get(item_num)
        if not sec:
            _say(f"\n[{i}/6] Item {item_num}: skipped (section not found)")
            continue
        _say(f"\n[{i}/6] Item {item_num} (text-only, pages {sec[0]}-{sec[1]})...")
        text = pdf_utils.section_text(pages, sec[0], sec[1])
        res = claude_client.extract(
            prompts.SYSTEM_PROMPT,
            prompt_tpl.replace("{TEXT}", text[:60000]),
        )
        _save(filename, res.data)
        total_cost += res.cost_usd
        summary["items"][f"item{item_num}"] = {"cost_usd": round(res.cost_usd, 4),
                                                "input_tokens": res.input_tokens,
                                                "cached": res.cached_input_tokens,
                                                "output_tokens": res.output_tokens}
        _say(f"  saved -> {out_dir.name}/{filename}.json  (${res.cost_usd:.4f})")

    # ----- Items 19, 20 (text + vision) -----
    vision_items = {
        19: ("item19_fpr", prompts.ITEM19_PROMPT),
        20: ("item20_outlets", prompts.ITEM20_PROMPT),
    }
    for i, (item_num, (filename, prompt_tpl)) in enumerate(vision_items.items(), start=5):
        sec = sections.get(item_num)
        if not sec:
            _say(f"\n[{i}/6] Item {item_num}: skipped (section not found)")
            continue
        # Cap rasterized pages to control cost (each image ~ $0.005 input)
        page_cap = 8
        end_for_images = min(sec[1], sec[0] + page_cap - 1)
        _say(f"\n[{i}/6] Item {item_num} (text+vision, pages {sec[0]}-{sec[1]}, rasterizing {sec[0]}-{end_for_images})...")
        text = pdf_utils.section_text(pages, sec[0], sec[1])
        pngs = pdf_utils.rasterize_pages(pdf_path, sec[0], end_for_images, scale=1.7)
        images_b64 = [pdf_utils.png_to_base64(p) for p in pngs]
        res = claude_client.extract(
            prompts.SYSTEM_PROMPT,
            prompt_tpl.replace("{TEXT}", text[:80000]),
            images_b64=images_b64,
            # Item 19 routinely produces 10-15k tokens of output on brands with rich
            # cohort tables (multiple cohorts × multiple metrics). Item 20 produces
            # similar output for state-by-state data. Both need streaming + 32k cap;
            # the 8k default truncates and the lenient parser produces 0-1 records.
            max_tokens=claude_client.MAX_TOKENS_LARGE if item_num in (19, 20) else claude_client.MAX_TOKENS,
        )
        _save(filename, res.data)
        total_cost += res.cost_usd
        summary["items"][f"item{item_num}"] = {"cost_usd": round(res.cost_usd, 4),
                                                "input_tokens": res.input_tokens,
                                                "cached": res.cached_input_tokens,
                                                "output_tokens": res.output_tokens,
                                                "images_sent": len(images_b64)}
        _say(f"  saved -> {out_dir.name}/{filename}.json  (${res.cost_usd:.4f}, {len(images_b64)} images)")

    summary["total_cost_usd"] = round(total_cost, 4)
    _save("_run_summary", summary)
    _say(f"\nDone. Total cost: ${total_cost:.4f}")
    _say(f"Outputs in: {out_dir}")
    return out_dir


def main() -> None:
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "crumbl_yale.pdf"
    if not pdf_path.exists():
        sys.exit(f"PDF not found: {pdf_path}")
    run(pdf_path)


if __name__ == "__main__":
    main()
