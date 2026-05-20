"""Re-run metadata + Item 19 on Mr. Rooter after the fixes.

Confirms:
  - find_cover_page picks page 2 (not body_start=4)
  - metadata extraction now returns legal_name, state_of_inc, issuance_date
  - Item 19 records now use performance_anchored for Top X% cohorts
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from src import claude_client, pdf_utils, prompts

pdf_path = Path("data/wi_scrape/mr_rooter_wi_id640790.pdf")
pages = pdf_utils.extract_pages(pdf_path)
body_start = pdf_utils.find_fdd_body_start(pages)
cover_page = pdf_utils.find_cover_page(pages)
print(f"body_start={body_start}, cover_page={cover_page}")

# Metadata
cover_start = max(1, cover_page - 1)
cover_end = min(len(pages), cover_page + 2)
print(f"\n[metadata] sending pages {cover_start}-{cover_end}")
text = pdf_utils.section_text(pages, cover_start, cover_end)
res = claude_client.extract(
    prompts.SYSTEM_PROMPT,
    prompts.METADATA_PROMPT.replace("{TEXT}", text[:30000]),
)
print(f"  cost=${res.cost_usd:.4f}")
out_path = Path("output/mr_rooter_wi_id640790/metadata.json")
out_path.write_text(json.dumps(res.data, indent=2), encoding="utf-8")
print(f"  saved -> {out_path}")
print(f"  legal_name={res.data.get('legal_name')!r}")
print(f"  state_of_inc={res.data.get('state_of_inc')!r}")
print(f"  issuance_date={res.data.get('issuance_date')!r}")
print(f"  confidence={res.data.get('confidence')}")

# Item 19 with new enum
sec = pdf_utils.find_section(pages, 19, body_start_page=body_start)
print(f"\n[item19] section pages {sec[0]}-{sec[1]}")
text = pdf_utils.section_text(pages, sec[0], sec[1])
pngs = pdf_utils.rasterize_pages(pdf_path, sec[0], min(sec[1], sec[0] + 7), scale=1.7)
images = [pdf_utils.png_to_base64(p) for p in pngs]
res = claude_client.extract(
    prompts.SYSTEM_PROMPT,
    prompts.ITEM19_PROMPT.replace("{TEXT}", text[:80000]),
    images_b64=images,
)
print(f"  cost=${res.cost_usd:.4f}, images={len(images)}")
out_path = Path("output/mr_rooter_wi_id640790/item19_fpr.json")
out_path.write_text(json.dumps(res.data, indent=2), encoding="utf-8")
print(f"  saved -> {out_path}")
print(f"  records={len(res.data.get('records', []))}")
# Count cohort_name distribution
from collections import Counter
cohorts = Counter(r.get("cohort_name") for r in res.data.get("records", []))
print(f"  cohort_name distribution: {dict(cohorts)}")
