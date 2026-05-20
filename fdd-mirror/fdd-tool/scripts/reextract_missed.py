"""Re-extract only the items that were missed in the pilot run, after the regex fix.
Cheap targeted fix-up rather than re-running the full pilot."""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from src import claude_client, pdf_utils, prompts

TASKS = [
    ("jdog_junk_removal_hauling_id639762", [19, 20]),
    ("two_men_and_a_junk_truck_id641608", [5, 7, 19, 20]),
]

PROMPT_MAP = {
    5: ("item5_initial_fee", prompts.ITEM5_PROMPT, False),
    6: ("item6_ongoing_fees", prompts.ITEM6_PROMPT, False),
    7: ("item7_investment", prompts.ITEM7_PROMPT, False),
    19: ("item19_fpr", prompts.ITEM19_PROMPT, True),
    20: ("item20_outlets", prompts.ITEM20_PROMPT, True),
}

total = 0.0
for stem, items in TASKS:
    pdf = Path("data/wi_scrape") / f"{stem}.pdf"
    out_dir = Path("output") / stem
    out_dir.mkdir(parents=True, exist_ok=True)
    pages = pdf_utils.extract_pages(pdf)
    body = pdf_utils.find_fdd_body_start(pages)
    print(f"\n=== {stem} (body_start={body}) ===")
    for item in items:
        fname, tmpl, use_vision = PROMPT_MAP[item]
        sec = pdf_utils.find_section(pages, item, body_start_page=body)
        if not sec:
            print(f"  item{item}: STILL not found after fix!")
            continue
        text = pdf_utils.section_text(pages, sec[0], sec[1])
        kwargs = {}
        if use_vision:
            end_img = min(sec[1], sec[0] + 7)
            pngs = pdf_utils.rasterize_pages(pdf, sec[0], end_img, scale=1.7)
            kwargs["images_b64"] = [pdf_utils.png_to_base64(p) for p in pngs]
            if item == 20:
                kwargs["max_tokens"] = claude_client.MAX_TOKENS_LARGE
        res = claude_client.extract(
            prompts.SYSTEM_PROMPT,
            tmpl.replace("{TEXT}", text[:80000]),
            **kwargs,
        )
        (out_dir / f"{fname}.json").write_text(json.dumps(res.data, indent=2), encoding="utf-8")
        total += res.cost_usd
        print(f"  item{item}: ${res.cost_usd:.4f}  (pages {sec[0]}-{sec[1]})")

print(f"\nTotal additional cost: ${total:.4f}")
