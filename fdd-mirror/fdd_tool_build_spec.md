# FDD Item 19 Tool — Build Spec v1

A buyer-facing database of franchise financial performance data, sourced from publicly filed Franchise Disclosure Documents (FDDs). Programmatic SEO + affiliate revenue.

---

## 1. Mental model (one paragraph)

Every year, ~4,000 US franchise brands publish a Franchise Disclosure Document (FDD) — a 200+ page legal document mandated by the FTC. Roughly 66% of those FDDs contain an "Item 19" section disclosing actual revenue and profit data for franchised locations. These FDDs are filed publicly in 14 "registration states." We build a pipeline that scrapes those state portals, downloads the PDFs, extracts Item 19 plus a few supporting items, and republishes the data as searchable, comparable, SEO-optimized pages. We monetize via affiliate referrals to franchise consultants and SBA-preferred lenders, plus display ads at scale.

---

## 2. Data sources — every URL, ranked by ease

### Tier 1: Start here

**Wisconsin DFI Franchise Search** — easiest UI
- Search portal: `https://apps.dfi.wi.gov/apps/FranchiseSearch/MainSearch.aspx`
- Search by trade name OR legal entity
- Filing details page has a direct PDF download link at the bottom
- Coverage: ~1,500–2,000 actively registered franchisors

**NASAA Electronic Filing Depository (EFD)** — cleanest cross-state source
- Portal: `https://www.nasaaefd.org`
- Multiple states route filings through this depository
- Search tab → "Franchise Search" → enter franchisor name
- May return multiple state filings for one franchisor (good for deduplication)

### Tier 2: Largest volume

**California DFPI DOCQNET** — largest single state by volume
- Search portal: `https://docqnet.dfpi.ca.gov`
- Unified search: `https://dfpi.ca.gov/search`
- Application type filter: select "Uniform Franchise Registration Application"
- Note: Cal-EASi (the old system) was retired June 18, 2014. All current filings are in DOCQNET.
- Older filings (pre-2014) require a Public Records Act request: `https://portal.dfpi.ca.gov/csp?id=ssp_pra_request`
- New submissions are filed through FRANSES, but public retrieval is still via DOCQNET

### Tier 3: Useful supplements

**Minnesota CARDS** — best for historical comparisons
- Portal: `https://cards.web.commerce.state.mn.us/franchise-registrations`
- MUST include a year filter or it returns all registrations ever
- Search by franchisor name or franchise offered
- Older filings remain accessible — useful for year-over-year revenue trend pages

**Indiana SOS** — clean and modern but new
- Portal: `https://securities.sos.in.gov/public-portfolio-search/`
- Select "Franchise" as registration type
- Coverage limit: launched 2019, only 2019+ filings available

### Sources to skip in MVP
- New York, Maryland, Virginia, Washington, Hawaii, Rhode Island, Michigan, North Dakota, South Dakota: registration states but no clean public download portal. Most require FOIA-style requests.
- Illinois: registration state but limited online access.

### Scraping strategy
- Use **Playwright** (not requests/bs4) — these portals are JS-heavy with stateful search forms
- Build one scraper per portal as a separate module
- Always hash the downloaded PDF (SHA-256) — the same franchisor files near-identical FDDs in multiple states; you want to dedupe
- Rate limit: 1 request per 2-3 seconds to be polite

---

## 3. Database schema (SQLite for MVP, migrate to Postgres later)

```sql
-- The franchise brand itself
CREATE TABLE franchisors (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  legal_name      TEXT NOT NULL,
  brand_name      TEXT,                    -- the public-facing name people google
  parent_company  TEXT,
  state_of_inc    TEXT,
  industry        TEXT,                    -- e.g., 'food-quick-service', 'fitness', 'home-services'
  category_naics  TEXT,
  year_founded    INTEGER,
  website         TEXT,
  slug            TEXT UNIQUE,             -- url-safe identifier for SEO pages
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- One row per filed FDD per state per year
CREATE TABLE fdds (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  franchisor_id   INTEGER NOT NULL REFERENCES franchisors(id),
  filing_year     INTEGER NOT NULL,
  filing_state    TEXT NOT NULL,
  filing_date     DATE,
  effective_date  DATE,
  source_url      TEXT NOT NULL,           -- where you scraped it from
  local_path      TEXT NOT NULL,           -- where the PDF is stored
  pdf_sha256      TEXT UNIQUE NOT NULL,    -- content hash for dedup
  page_count      INTEGER,
  has_item19      BOOLEAN,
  has_item20      BOOLEAN,
  retrieved_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  parsed_at       TIMESTAMP
);
CREATE INDEX idx_fdds_franchisor_year ON fdds(franchisor_id, filing_year);

-- Item 19 is the meat. Each FDD has 0..N records (cohort × metric combinations)
CREATE TABLE item19_records (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  fdd_id          INTEGER NOT NULL REFERENCES fdds(id),
  metric_name     TEXT NOT NULL,           -- normalized: 'gross_sales', 'gross_profit', 'net_profit', 'aov', 'transactions'
  metric_raw      TEXT,                    -- original label from the PDF (for QA)
  cohort_name     TEXT,                    -- normalized: 'all_franchised', 'open_24mo_plus', 'small_format', etc.
  cohort_raw      TEXT,                    -- original cohort description
  outlet_count    INTEGER,                 -- how many outlets in this cohort
  reporting_period TEXT,                   -- e.g., '2024 fiscal year'
  value_avg       NUMERIC,
  value_median    NUMERIC,
  value_min       NUMERIC,
  value_max       NUMERIC,
  percentile_25   NUMERIC,
  percentile_75   NUMERIC,
  pct_above_avg   NUMERIC,                 -- common: "30% of outlets met or exceeded average"
  page_number     INTEGER,                 -- where in the PDF this came from
  raw_text        TEXT,                    -- the raw extracted paragraph for QA
  confidence      NUMERIC,                 -- 0-1 score Claude assigned to this extraction
  needs_review    BOOLEAN DEFAULT FALSE
);
CREATE INDEX idx_item19_fdd ON item19_records(fdd_id);

-- Item 20: location counts and growth/churn. Easier to parse than Item 19.
CREATE TABLE item20_locations (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  fdd_id          INTEGER NOT NULL REFERENCES fdds(id),
  year            INTEGER NOT NULL,
  outlet_type     TEXT,                    -- 'franchised' or 'company-owned'
  state           TEXT,                    -- 'TOTAL' for the rollup row
  outlets_start   INTEGER,
  outlets_opened  INTEGER,
  outlets_closed  INTEGER,                 -- key churn signal
  outlets_transferred INTEGER,
  outlets_reacquired INTEGER,
  outlets_end     INTEGER
);
CREATE INDEX idx_item20_fdd ON item20_locations(fdd_id);

-- Item 5, 6, 7: initial fee, royalty, total investment range
CREATE TABLE fees_and_investment (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  fdd_id          INTEGER NOT NULL REFERENCES fdds(id),
  initial_franchise_fee_low   NUMERIC,
  initial_franchise_fee_high  NUMERIC,
  royalty_pct                 NUMERIC,
  royalty_min_monthly         NUMERIC,
  marketing_fee_pct           NUMERIC,
  total_investment_low        NUMERIC,
  total_investment_high       NUMERIC,
  liquid_capital_required     NUMERIC,
  net_worth_required          NUMERIC
);

-- For tracking affiliate referrals
CREATE TABLE affiliate_clicks (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  franchisor_id   INTEGER REFERENCES franchisors(id),
  partner         TEXT,                    -- e.g., 'frannet', 'applepie', 'boefly'
  click_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  visitor_hash    TEXT,                    -- anonymized visitor identifier
  page_slug       TEXT,
  utm_data        TEXT                     -- JSON blob
);
```

### Why these specific fields
- `pdf_sha256` is mandatory — same franchisor often files near-identical FDDs in 5+ states; you only want to parse once.
- `confidence` and `needs_review` on Item 19 records — Claude will get some extractions wrong; this flags them for manual QA.
- `metric_raw` and `cohort_raw` preserve the original PDF text — needed when you're debugging why a number looks weird.
- `slug` on franchisors is the URL component for SEO pages (`/franchise/[slug]`).

---

## 4. Parsing Item 19 — the actual technical hard part

Item 19 has no fixed format. The FTC Franchise Rule (16 CFR §436.5(s)) defines what franchisors must disclose but not how to lay it out. You'll see everything from a 2-page revenue table to a 30-page cohort breakdown.

### What Item 19 contains (in order of frequency)

1. **Average gross sales** — by cohort (almost always present when Item 19 exists)
2. **Median gross sales** — common, often alongside average
3. **Outlet count per cohort** — always present, defines the denominator
4. **Cohort definitions** — e.g., "franchised outlets open at least 24 months as of FY end"
5. **% of outlets meeting or exceeding average** — common: "32% of outlets met or exceeded the average gross sales"
6. **Quartile or percentile breakdowns** — present in maybe 40% of disclosures
7. **Gross profit / operating profit** — present in maybe 25%
8. **Net profit / EBITDA** — present in maybe 10–15%
9. **Per-customer metrics** — average ticket, transactions per day, etc.

### Cohorts you'll commonly see
- `all franchised outlets`
- `franchised outlets open >X months/years`
- `franchised outlets by store format` (e.g., small vs large)
- `franchised outlets by geography` (rare)
- `company-owned outlets` (always treated as a separate cohort by FTC rules)
- `franchised outlets meeting specific criteria`

### Extraction pipeline (use Claude API)

```python
# Pseudocode for the Item 19 extraction step

def extract_item19(pdf_path: str) -> list[dict]:
    # Step 1: locate the Item 19 section
    full_text = extract_text_with_page_numbers(pdf_path)
    item19_start, item19_end = find_item19_boundaries(full_text)
    item19_text = full_text[item19_start:item19_end]
    
    # If section is short and tabular, also rasterize those pages and send images
    # (Claude vision handles table extraction much better than text)
    item19_pages = rasterize_pages(pdf_path, item19_start_page, item19_end_page)
    
    # Step 2: send to Claude with structured output prompt
    response = claude_extract(item19_text, item19_pages)
    
    # Step 3: validate and tag confidence
    for record in response:
        record['confidence'] = score_extraction(record)
        record['needs_review'] = record['confidence'] < 0.8
    
    return response
```

### The Claude prompt for Item 19 extraction

Save this to a constants file. Iterate carefully — extraction quality compounds.

```
You are extracting structured financial performance data from Item 19 of a
Franchise Disclosure Document (FDD). Item 19 contains "Financial Performance
Representations" (FPRs) governed by 16 CFR §436.5(s).

Return a JSON array. Each array element represents ONE cohort × ONE metric.
If a single table has 3 cohorts × 2 metrics (avg and median gross sales),
that produces 6 separate records.

Schema for each record:
{
  "metric_name": "gross_sales" | "gross_profit" | "net_profit" | "ebitda" |
                 "average_ticket" | "transactions" | "labor_pct" | "occupancy_pct" |
                 "other",
  "metric_raw": "exact label from the document (e.g., 'Average Gross Sales')",
  "cohort_name": "all_franchised" | "all_company_owned" | "open_lt_12mo" |
                 "open_12_24mo" | "open_24_plus_mo" | "small_format" |
                 "large_format" | "other",
  "cohort_raw": "exact cohort description from the document",
  "outlet_count": integer or null,
  "reporting_period": "string describing the time window (e.g., 'fiscal year 2024')",
  "value_avg": number or null,
  "value_median": number or null,
  "value_min": number or null,
  "value_max": number or null,
  "percentile_25": number or null,
  "percentile_75": number or null,
  "pct_above_avg": number 0-100 or null,
  "page_number": integer (the PDF page where this number appears),
  "raw_text": "the surrounding sentence/paragraph this was extracted from",
  "notes": "any caveats (e.g., 'excludes 3 outlets with abnormal closures')"
}

Critical rules:
1. ONLY extract numbers that represent ACTUAL historical performance. Skip
   projections, forecasts, hypothetical examples, or pro forma numbers.
2. Numbers in footnoted "example calculations" or "hypothetical scenarios"
   should be skipped entirely.
3. If a number is described as "estimated" or "approximate", include it but
   note that in the "notes" field.
4. Currency: assume USD unless otherwise stated. Strip dollar signs and
   commas. Convert "$1.2M" to 1200000.
5. If you cannot confidently determine a value, set it to null. Never guess.
6. Per the FTC rule, company-owned outlets and franchised outlets must be
   reported as separate cohorts when both exist. Preserve this separation.
7. Return ONLY the JSON array. No prose, no markdown fences.
```

### What to do when Item 19 isn't present
~34% of FDDs have no Item 19 (the franchisor chose not to disclose). Still parse Items 5/6/7/20 from those FDDs — fees, investment, and location counts are valuable on their own. Flag `has_item19 = false` on the FDD row so SEO pages can say "this franchisor does not publicly disclose Item 19 financial performance data."

---

## 5. Parsing the easier items (do these first, build confidence)

### Item 5 — Initial franchise fee
- Almost always a single number or simple range
- Look for headings like "Initial Franchise Fee" or "Franchise Fee"
- Extract: low, high, and any variations by territory/format

### Item 6 — Other fees (royalty, marketing)
- Tabular format, well-structured
- Royalty is usually a % of gross sales (4-8% typical) or a flat monthly minimum
- Marketing/ad fund is usually 1-4% of gross sales
- Look for "Royalty" and "Marketing Fund" or "Brand Fund" rows

### Item 7 — Estimated initial investment
- Always tabular with low/high columns
- Look for "Total Investment" or "Total Estimated Initial Investment" row
- Subcomponents include: real estate, equipment, training, initial inventory, working capital
- Extract just the totals for MVP; subcomponents can come later

### Item 20 — Outlet information
- Highly structured tables required by the FTC rule
- Five years of data per table
- Tables for: (1) franchised outlets activity, (2) company-owned outlets activity, (3) state-by-state breakdown, (4) projected openings, (5) franchisees who left the system
- Extract the activity tables — opens, closes, transfers are the signal for system health

---

## 6. What to build in what order

### Week 1 — Single pipeline end-to-end
- [ ] Scaffold Python project (Poetry, SQLite, Playwright, Anthropic SDK)
- [ ] Wisconsin scraper: list all current franchisors, download all FDDs
- [ ] PDF deduplication via SHA-256
- [ ] Database schema migration
- [ ] Extract Items 5, 6, 7, 20 from 10 sample FDDs (manually verify)

### Week 2 — Item 19 extraction
- [ ] Build the Claude extraction prompt, iterate on 20 sample FDDs
- [ ] Add confidence scoring + manual review CSV export
- [ ] Process all Wisconsin FDDs (~1,500 documents)
- [ ] Spot-check accuracy on 50 random extractions

### Week 3 — California scraper
- [ ] California DOCQNET scraper (harder UI than Wisconsin)
- [ ] Cross-state deduplication (same franchisor in WI and CA → one franchisor record, two FDD records)
- [ ] Aim for ~3,500 unique franchisors across both states

### Week 4 — Web frontend
- [ ] Next.js scaffold with `/franchise/[slug]` route
- [ ] Single-franchisor page template: header, key stats, Item 19 tables, location count, investment range
- [ ] Sitemap generation
- [ ] Schema.org markup (Organization, FAQPage, Product schemas)

### Week 5 — Comparison pages and category pages
- [ ] `/compare/[slug1]-vs-[slug2]` routes
- [ ] `/category/[industry]` rollup pages with averages across all franchisors in category
- [ ] Internal linking (every brand page links to its category and top 3 comparison pages)

### Week 6 — Affiliate plumbing
- [ ] Apply to FranNet, IFPG, FBA affiliate programs
- [ ] Apply to ApplePie Capital, Boefly, FranFund affiliate programs
- [ ] Build click tracking (the affiliate_clicks table)
- [ ] CTAs on every page: "Talk to a franchise consultant" and "Get pre-qualified for an SBA loan"

### Week 7+ — Iterate based on what ranks
- [ ] Add Minnesota for historical trend pages (year-over-year revenue charts)
- [ ] Add Indiana for cross-validation
- [ ] Build free tools as lead magnets: "Franchise Affordability Calculator," "Royalty Cost Calculator"
- [ ] Programmatic backlink outreach to franchise consultants (offer them embed widgets)

---

## 7. Affiliate networks — who pays what

### Franchise consultants (lead-gen, pays per qualified lead)
| Partner | Payout | Notes |
|---------|--------|-------|
| FranNet | $200–500 | Largest network, strict lead quality criteria |
| IFPG (Int'l Franchise Professionals Group) | $200–400 | More flexible on lead criteria |
| FBA (Franchise Brokers Association) | varies | Often a flat fee per lead |
| World Franchise Group | $250–500 | International coverage |

### SBA preferred lenders (pays per funded loan, much higher payouts)
| Partner | Payout | Notes |
|---------|--------|-------|
| ApplePie Capital | $500–2000 | Franchise-specific, fastest approval |
| Boefly | $500–1500 | Marketplace model, wider reach |
| FranFund | $500–1500 | Strong on retirement-fund-rollover (ROBS) financing |
| SmartBiz | $300–800 | Broader small-business focus, less franchise-specific |

### Display ads (once you have traffic scale)
| Network | Min traffic | RPM |
|---------|------------|-----|
| Ezoic | ~10k sessions/mo | $5–15 |
| Mediavine | 50k sessions/mo | $20–50 |
| Raptive (AdThrive) | 100k sessions/mo | $30–60 |

---

## 8. Legal/compliance notes (read these before launch)

1. **FDDs are public records.** Item 19 data is published by the franchisor with full knowledge it will be read by the public. Republishing the data is not infringement.
2. **Don't reproduce FDD text verbatim.** The franchisor still holds copyright on the writing. Extract data, summarize methodology in your own words, link back to the source. Quotes under 15 words are fine for context.
3. **Always cite the source.** Every Item 19 record displayed should link back to the state filing it came from.
4. **Disclaimer block on every page:** "Data sourced from publicly filed Franchise Disclosure Documents. Historical results do not guarantee future performance."
5. **Do not provide investment advice.** Your pages display data; they do not recommend purchases. Affiliate CTAs should say "Talk to a franchise consultant" not "This franchise is a good investment."
6. **Watch for franchisor amendments.** FDDs are updated annually and sometimes mid-year. Stale Item 19 data is misleading. Show the filing date prominently. Re-pull annually.
7. **One-time legal review (~$2-5k):** before launch, have a franchise attorney review the disclaimer language, data presentation conventions, and affiliate disclosure compliance.

---

## 9. Source files Claude Code should create on day 1

```
fdd-tool/
├── pyproject.toml
├── README.md
├── .env.example                  # ANTHROPIC_API_KEY, DB_PATH, etc.
├── src/
│   ├── __init__.py
│   ├── db.py                     # SQLite schema + migrations
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base.py               # Abstract scraper interface
│   │   ├── wisconsin.py          # Wisconsin DFI scraper
│   │   ├── california.py         # CA DOCQNET scraper (week 3)
│   │   ├── minnesota.py          # MN CARDS scraper (week 7+)
│   │   └── indiana.py            # Indiana SOS scraper (week 7+)
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── pdf_utils.py          # Text extraction, page rasterization, section finding
│   │   ├── item5_fees.py         # Initial fee parser
│   │   ├── item6_ongoing_fees.py # Royalty/marketing fee parser
│   │   ├── item7_investment.py   # Total investment range parser
│   │   ├── item19_fpr.py         # Financial Performance Representation parser (the hard one)
│   │   └── item20_outlets.py     # Outlet count tables parser
│   ├── extraction/
│   │   ├── __init__.py
│   │   ├── claude_client.py      # Anthropic SDK wrapper with retries
│   │   └── prompts.py            # All prompts in one place for easy iteration
│   ├── normalization/
│   │   ├── __init__.py
│   │   ├── entity_resolution.py  # Match same franchisor across state filings
│   │   └── industry_mapping.py   # NAICS → human-readable category
│   └── cli.py                    # Command-line entry points
└── data/
    ├── pdfs/                     # Downloaded FDDs, organized by state/year
    ├── extracted/                # JSON dumps of extraction output for QA
    └── db.sqlite                 # The actual database
```

---

## 10. The first command Josh runs tonight

```bash
# Scaffold the project
mkdir fdd-tool && cd fdd-tool
poetry init -n
poetry add anthropic playwright pypdf2 pdfplumber pillow sqlalchemy click rich
poetry run playwright install chromium

# Hand this file to Claude Code:
claude code "Read fdd_tool_build_spec.md. Build the project structure in
section 9. Start with src/db.py (full schema from section 3) and
src/scrapers/wisconsin.py (using the URL and approach from section 2).
Stop after those two files for review."
```

That's it. Build, ship, iterate.
