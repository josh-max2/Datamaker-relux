"""Extraction prompts for FDD Items. One per item. System prompt is shared across all calls
so it can be prompt-cached for cost savings. Sized > 1024 tokens so Sonnet's
ephemeral cache fires on calls 2-N of each FDD (10× cheaper input than uncached)."""

SYSTEM_PROMPT = """You extract structured financial and operational data from US Franchise
Disclosure Documents (FDDs). FDDs are public-record documents franchisors file with the FTC
and state regulators (CA, IL, IN, MD, MI, MN, NY, ND, RI, SD, VA, WA, WI, HI) under
16 CFR §436 — the FTC Franchise Rule. The Rule requires a 23-item disclosure structure;
this pipeline targets a focused subset that drives the buyer-facing site: cover-page metadata
(franchisor identity, filing year, state of incorporation, effective date), Item 5 (initial
franchise fee), Item 6 (other ongoing fees), Item 7 (estimated initial investment), Item 19
(financial performance representations, when disclosed — about 33% of franchisors choose to),
and Item 20 (outlets and franchisee information, including state-by-state activity tables).

GROUND RULES (apply to every extraction):

1. OUTPUT FORMAT — Return ONLY a JSON object matching the schema in the user message.
   No prose preamble. No markdown fences. No commentary after. No explanation of your
   reasoning. The first character of your response must be `{` and the last must be `}`.
   If you need to note something, use the appropriate field in the schema (`notes`,
   `fee_notes`, etc.) — never write prose outside the JSON object.

2. JSON ESCAPING — Inside string values, escape ALL embedded double quotes with `\\"`.
   For example, an FDD that uses defined terms like ("Franchise Fee") must be rendered as
   "\\"Franchise Fee\\"" inside your JSON string. Failure to escape produces invalid JSON.
   Escape literal newlines as \\n and tabs as \\t.

3. ACTUAL VALUES ONLY — Only extract numbers that represent ACTUAL historical or
   currently-required values. Skip projections, hypothetical scenarios ("if you generate
   $1M in sales..."), forward-looking estimates, sample calculations, marketing pro-forma,
   or anything labeled "for illustrative purposes". The franchisor's own disclosed actuals
   are authoritative; nothing else is.

4. NULL FOR MISSING — If a value isn't disclosed, set the field to `null`. Never guess,
   extrapolate, or fill in a "reasonable default". An empty field is more useful than a
   wrong field. Capture the franchisor's intent: if they explicitly say "not required",
   that's null, not 0.

5. CURRENCY NORMALIZATION — Always USD unless explicitly noted otherwise. Strip "$",
   thousands commas, and surrounding parentheses. Convert "$1.2M" to 1200000.
   Convert "$1.5 million" to 1500000. Convert "(160,202.58)" to -160202.58 — accounting
   convention uses parentheses for negative values. Convert "$25-$150/month" to two
   separate fields (low=25, high=150) when the schema supports a range.

6. PERCENTAGES — Strip "%" and return as a number where the schema labels a percentage
   field. 5.5% becomes 5.5, not 0.055. The schema documents which fields expect
   percentages — read it carefully.

7. OCR ARTIFACTS — Source text may contain OCR errors: broken spacing, missing characters,
   "$1,234.56" rendered as "$1.234.56", "I" for "1", "O" for "0", letters concatenated
   without spaces. Use surrounding context to disambiguate. If still unclear, set the
   field to null and add a note explaining the ambiguity. Do NOT silently coerce
   ambiguous OCR to a guess.

8. COHORT ANCHORING (relevant to Item 19) — Item 19 reports performance for one or more
   "cohorts" of outlets. Use the most specific cohort_name that fits:
     - all_franchised / all_company_owned: brand-wide aggregates
     - open_24_plus_mo / 36 / 48 / 60: tenure-based ("open at least N months")
     - tenure_year_anchored: when the cohort is defined by an absolute year boundary
       ("Open Prior to 2022", "Opened in 2019 or earlier")
     - performance_anchored: ranked by performance ("Top 10%", "Top 100 outlets", "Top
       quartile by gross sales")
     - ownership_group_anchored: by how many units a single franchisee owns
       ("Single-Unit Franchisees", "5-7 Unit Group", "FOGs with 8-24 Active Franchises")
   Always also preserve the verbatim cohort label in cohort_raw.

9. TIME UNITS — When extracting performance values, identify the time unit. Most FDDs
   report annual figures, but some use weekly (AWUS = Average Weekly Unit Sales), monthly
   (Average Monthly Sales), or daily (RevPAR / ADR for hospitality). Set unit_period
   accordingly — downstream breakeven math depends on this being correct, and an
   off-by-12 or off-by-52 error materially misleads buyers.

10. CONFIDENCE — Set a confidence score 0.0-1.0 for the overall extraction quality you
    achieved on this item. A 1.0 means: schema fully populated where source supports it,
    no ambiguity, no OCR damage. A 0.5 means: you got the structure but had to make
    judgment calls or skip some fields. A 0.3 or lower means: significant uncertainty,
    likely needs human review. Confidence should reflect the EVIDENCE in the document,
    not your sense of the data's reasonableness.
"""

ITEM5_PROMPT = """Extract Item 5 (Initial Franchise Fee) from the text below.

Schema:
{
  "initial_franchise_fee_low": number | null,    // lowest possible initial fee in USD
  "initial_franchise_fee_high": number | null,   // highest possible initial fee in USD
  "fee_notes": "string | null",                  // brief description of variations, discounts, or conditions
  "raw_excerpt": "string",                       // verbatim sentence(s) from the doc containing the fee
  "confidence": number                           // 0.0 to 1.0
}

If the fee is a single number, set both low and high to that number.

Text:
---
{TEXT}
---
"""

ITEM6_PROMPT = """Extract Item 6 (Other Fees - ongoing) from the text below.

Schema:
{
  "royalty_pct": number | null,             // % of gross sales (4-8% typical)
  "royalty_min_monthly": number | null,     // USD minimum monthly royalty floor if any
  "marketing_fee_pct": number | null,       // % of gross sales for brand fund / ad fund
  "marketing_min_monthly": number | null,   // USD minimum monthly marketing contribution
  "tech_fee_monthly": number | null,        // USD monthly technology fee if disclosed
  "fee_notes": "string | null",             // brief notes on tiered rates or unusual structures
  "raw_excerpt": "string",                  // verbatim row(s) from the Item 6 table
  "confidence": number
}

Text:
---
{TEXT}
---
"""

ITEM7_PROMPT = """Extract Item 7 (Estimated Initial Investment) from the text below.

Item 7 is always a table with low and high columns. Extract only the TOTAL row.

Schema:
{
  "total_investment_low": number | null,    // USD, sum of all line items, low column
  "total_investment_high": number | null,   // USD, sum of all line items, high column
  "liquid_capital_required": number | null, // USD, if separately stated
  "net_worth_required": number | null,      // USD, if separately stated
  "raw_excerpt": "string",                  // verbatim of the total row from the table
  "confidence": number
}

Text:
---
{TEXT}
---
"""

ITEM19_PROMPT = """Extract Item 19 (Financial Performance Representations) from the text and images below.

Item 19 contains 0 or more "cohort × metric" measurements. Each cohort is a defined group
of outlets (e.g., "324 franchised outlets open all of 2022"). Each metric is a financial
measure (gross sales, gross profit, net profit, etc.). A single table showing 3 metrics
× 1 cohort produces 3 records. A table with 3 cohorts × 3 metrics produces 9 records.

Return: {"records": [...], "has_item19": boolean, "confidence": number, "notes": "string | null"}

Each record schema:
{
  "metric_name": "gross_sales" | "gross_profit" | "net_profit" | "ebitda" |
                 "total_revenue" | "average_ticket" | "transactions" |
                 "labor_pct" | "occupancy_pct" | "other",
  "metric_raw": "string",                  // exact label from doc (e.g., "Total Revenue")
  "cohort_name": "all_franchised" | "all_company_owned" | "open_lt_12mo" |
                 "open_12_24mo" | "open_24_plus_mo" | "open_36_plus_mo" |
                 "open_48_plus_mo" | "open_60_plus_mo" | "tenure_year_anchored" |
                 "performance_anchored" | "ownership_group_anchored" |
                 "small_format" | "large_format" | "other",
  // Tenure buckets: open_60_plus_mo covers 5+ years (60+ months), use it for "72 months" too.
  // Use "tenure_year_anchored" when the cohort is defined by an absolute year boundary
  // (e.g., "Open Prior to 2022", "Opened in 2019 or earlier"). Capture the year in cohort_raw.
  // Use "performance_anchored" for cohorts ranked by performance: "Top 10%", "Top 25%",
  // "Top 100 outlets by revenue", "Outlets above $1M gross sales". Threshold in cohort_raw.
  // Use "ownership_group_anchored" when the cohort is sliced by how many units a single
  // franchisee owns: "Single-Unit Franchisees", "2-Unit Group", "5-7 Unit Group",
  // "Franchise Ownership Groups with N Active Franchises". Group size in cohort_raw.
  "cohort_raw": "string",                  // exact cohort description from doc
  "outlet_count": integer | null,          // # of outlets in this cohort
  "reporting_period": "string | null",     // e.g., "2022 calendar year"
  "reporting_year": integer | null,        // year as int — if reporting_period is "2025 calendar year", this is 2025
  "unit_period": "annual" | "monthly" | "weekly" | "daily" | null,
                                           // The TIME UNIT of value_avg/min/max/median.
                                           // - "weekly" if metric is "Average Weekly Unit Sales", "AWUS", "per week"
                                           // - "monthly" if metric is "Average Monthly Sales", "per month"
                                           // - "daily" if metric is "RevPAR", "ADR", "Daily Rate" (hospitality)
                                           // - "annual" otherwise (this is the default — most FDDs)
                                           // - null if value is a % or unit-less (royalty %, occupancy %)
                                           // CRITICAL: if you set this wrong, downstream breakeven calculations
                                           // will be off by 12× or 52×. Read the metric label carefully.
  "metric_scope": "franchisee" | "market-area" | "ramp-snapshot" | null,
                                           // How to interpret the value:
                                           // - "franchisee" (default): real franchisee-level revenue/profit
                                           // - "market-area": per-capita, per-subterritory, per-household — NOT franchisee revenue
                                           // - "ramp-snapshot": one of a Month 1..N first-year build-up series
                                           // - null if unsure
                                           // CRITICAL: market-area and ramp-snapshot values should NOT be used
                                           // as annual revenue for breakeven; the site filters them out when this is set.
  "value_avg": number | null,
  "value_median": number | null,
  "value_min": number | null,
  "value_max": number | null,
  "percentile_25": number | null,
  "percentile_75": number | null,
  "pct_above_avg": number | null,          // 0-100, e.g., "46.3% met or exceeded the average"
  "page_number": integer | null,           // PDF page where this record's data appears
  "raw_text": "string",                    // short excerpt of source text/table row
  "notes": "string | null"                 // caveats or extraction warnings
}

Important: if Item 19 explicitly says the franchisor makes NO financial performance
representation, set has_item19=false and return records=[].

If the section IS present but you cannot find the actual numbers (e.g., they were in
images you can't read), set has_item19=true, records=[], confidence < 0.4, and explain
in notes.

Text:
---
{TEXT}
---
"""

ITEM20_PROMPT = """Extract Item 20 (Outlets and Franchisee Information) from the text and images below.

Item 20 has up to 5 tables. Focus on Table 1 (Systemwide Outlet Summary) and Table 3
(Status of Franchised Outlets) — these capture growth and churn.

Return: {"yearly_summary": [...], "state_year_status": [...], "confidence": number, "notes": "string | null"}

Each yearly_summary record (from Table 1):
{
  "year": integer,
  "outlet_type": "franchised" | "company-owned" | "total",
  "outlets_start": integer | null,
  "outlets_end": integer | null,
  "net_change": integer | null
}

Each state_year_status record (from Table 3 — one row per state × year):
{
  "year": integer,
  "state": "string",                  // "AL", "CA", etc., OR "TOTAL" if rollup row
  "outlets_start": integer | null,
  "outlets_opened": integer | null,
  "outlets_terminated": integer | null,
  "outlets_nonrenewed": integer | null,
  "outlets_reacquired": integer | null,
  "outlets_ceased_other": integer | null,
  "outlets_end": integer | null
}

If a table is very long (50+ rows), extract ALL rows. Do not summarize or skip.

Text:
---
{TEXT}
---
"""

METADATA_PROMPT = """Identify the franchisor and filing metadata from the cover/early pages below.

Schema:
{
  "legal_name": "string | null",      // e.g., "Crumbl Franchising, LLC"
  "brand_name": "string | null",      // public name customers know (e.g., "Crumbl")
  "state_of_inc": "string | null",    // e.g., "Utah"
  "filing_year": integer | null,      // year on the FDD cover
  "issuance_date": "string | null",   // ISO date if stated, e.g., "2023-03-28"
  "website": "string | null",
  "raw_excerpt": "string",
  "confidence": number
}

Text:
---
{TEXT}
---
"""
