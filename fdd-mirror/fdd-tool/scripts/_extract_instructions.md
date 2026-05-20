# FDD extraction job — single PDF, then exit

You are processing exactly ONE FDD PDF. Your job is to extract structured data and write it to disk, then exit. Do not ask questions. Do not run extra commands beyond what's needed.

## Setup (use this exact sequence)

1. **Section boundaries** are pre-computed and provided in the "Pre-computed facts" JSON block above. Use those `(start, end)` page ranges directly. **Do not run a Bash command to recompute them.**

2. **For each section + metadata, Read the PDF pages directly.** Use the `Read` tool with the `pages` parameter (e.g. `pages: "87-89"`). PDF reads return rendered pages so you can see tables visually.

3. **Schemas** are inlined above in the "Schemas" code block. **Do not Read `src/prompts.py`.** Apply the SYSTEM_PROMPT ground rules + the item-specific schema for each JSON file you write.

4. **Write 6 JSON files to `output/{PDF_STEM}/`** (one per item + metadata) using the `Write` tool:
   - `metadata.json`         (METADATA_PROMPT schema)
   - `item5_initial_fee.json`     (ITEM5_PROMPT schema)
   - `item6_ongoing_fees.json`    (ITEM6_PROMPT schema)
   - `item7_investment.json`      (ITEM7_PROMPT schema)
   - `item19_fpr.json`            (ITEM19_PROMPT schema — array of records)
   - `item20_outlets.json`        (ITEM20_PROMPT schema)

## Critical extraction rules

- **No projections, no forecasts, no hypothetical examples** — only actual reported historical numbers.
- **Currency**: strip $ and commas; convert "$1.2M" → 1200000; parenthesized values are negative.
- **Confidence**: include a 0.0-1.0 confidence per output. Below 0.7 = flag for review.
- **For Item 19**: every cohort × metric pair = one record. A 3-cohort × 3-metric table = 9 records.
- **For Item 19**: populate the structured fields:
  - `unit_period`: "weekly" if metric says "Average Weekly Unit Sales" / "AWUS" / "per week"; "monthly" if "Average Monthly Sales" / "per month"; "daily" if "RevPAR" / "ADR" / "Daily Rate"; otherwise "annual". Use null for % or unit-less metrics. **Getting this wrong breaks breakeven calculations.**
  - `metric_scope`: "market-area" for "Per Capita" / "Per Subterritory" / "Per Household" / "Per Room" (these are NOT franchisee revenue); "ramp-snapshot" for "Monthly Gross Sales — Month N" series; "franchisee" otherwise.
  - `reporting_year`: integer year extracted from `reporting_period` (e.g., 2025 for "2025 calendar year").
- **For Item 19 no-FPR case**: if `item19_no_fpr` is `true` in the pre-computed facts, OR if the section explicitly states "we do not make any financial performance representations," write `{"records":[],"has_item19":false,"confidence":0.95,"notes":"explicit no-FPR"}` and do not read the Item 19 pages.
- **For Item 20**: extract both `yearly_summary` (Table 1) and `state_year_status` (Table 3). State='TOTAL' for rollup rows.
- **Cohort enum values**: `all_franchised`, `all_company_owned`, `open_lt_12mo`, `open_12_24mo`, `open_24_plus_mo`, `open_36_plus_mo`, `open_48_plus_mo`, `open_60_plus_mo`, `tenure_year_anchored`, `performance_anchored`, `ownership_group_anchored`, `small_format`, `large_format`, `other`.

## Environment — DO NOT use these tools

You are running on Windows. The following CLIs are NOT available and will fail:
- `pdftotext`, `pdftoppm`, `pdf2text`, `pdfgrep` (these are Linux/poppler-only)
- `convert` (ImageMagick), `tesseract` (OCR)
- Any shell pipe involving the above

**Always use the `Read` tool with the `pages` parameter** to view PDF content. Do not attempt to shell out to PDF-processing CLIs.

## Cost-saving directives

- **For Items 5, 6, 7**: use text only (don't request rasterized PDF rendering). These are short, tabular, plain text.
- **For Item 19 no-FPR**: per the pre-computed `item19_no_fpr` flag, skip reading the Item 19 section entirely when true.
- **Known metadata**: if the pre-computed facts include `known_metadata.legal_name` or `known_metadata.effective_date`, use them directly in metadata.json — don't re-extract from the cover page.
- **Don't re-read files**. One pass through.

## What "done" looks like

After writing all 6 JSON files (or fewer if some sections weren't found — write a stub file with `{"_section_not_found": true}` in that case), print exactly:

```
EXTRACTION_DONE pdf_stem={STEM} items_written={N}
```

Then exit. Do not commit anything, do not run ingest, do not regenerate the site. The orchestrator handles those.

## If something fails

If a section can't be located (`sections.itemN` is null), write `{"_section_not_found": true, "_reason": "..."}` to that JSON file and continue with the others. If `Read` fails on a PDF page, write `{"_read_error": "...", "_partial": true}`. Always finish the run — partial results are better than no results.
