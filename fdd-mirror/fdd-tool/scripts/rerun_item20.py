"""Re-run only Item 20 after bumping max_tokens."""
import json
from pathlib import Path
from src import claude_client, pdf_utils, prompts

pdf_path = Path("data/crumbl_yale.pdf")
pages = pdf_utils.extract_pages(pdf_path)
body_start = pdf_utils.find_fdd_body_start(pages)
sec = pdf_utils.find_section(pages, 20, body_start_page=body_start)
assert sec, "Item 20 not found"
print(f"Item 20: pages {sec[0]}-{sec[1]}")

text = pdf_utils.section_text(pages, sec[0], sec[1])
end_img = min(sec[1], sec[0] + 8)
pngs = pdf_utils.rasterize_pages(pdf_path, sec[0], end_img, scale=1.7)
images = [pdf_utils.png_to_base64(p) for p in pngs]

res = claude_client.extract(
    prompts.SYSTEM_PROMPT,
    prompts.ITEM20_PROMPT.replace("{TEXT}", text[:80000]),
    images_b64=images,
    max_tokens=claude_client.MAX_TOKENS_LARGE,
)

Path("output/item20_outlets.json").write_text(json.dumps(res.data, indent=2), encoding="utf-8")
print(f"Saved. cost=${res.cost_usd:.4f} input={res.input_tokens} cached={res.cached_input_tokens} output={res.output_tokens}")
if "_parse_error" in res.data:
    print(f"!! parse error still: {res.data['_parse_error']}")
else:
    ys = len(res.data.get("yearly_summary", []))
    sys_ = len(res.data.get("state_year_status", []))
    print(f"Parsed cleanly: {ys} yearly rows, {sys_} state-year rows")
