# FDD Tool — Handoff (Datamaker-relux mirror)

Cross-session resume doc. Read this first when picking the mirror back up.

> **This is the design-mirror repo (`josh-max2/Datamaker-relux`).** Code mirrors `josh-max2/Parser`; visual / design changes land here first so `franchisedepth.com` stays untouched. **Live preview:** https://josh-max2.github.io/Datamaker-relux/. Mirror-specific design status lives in §19 of `PROJECT_TRACKER.md`.

**Last updated:** 2026-05-19 evening (Phase 1 luxury redesign shipped on this mirror: typography + dark palette + hero + featured stats + Item 19 badges + combined-fee callout + sticky-tab repaint)
**Owner:** Josh
**Master tracker:** [PROJECT_TRACKER.md](./PROJECT_TRACKER.md) — single source of truth across methodology, features, ops, changelog
**Build spec:** [fdd_tool_build_spec.md](./fdd_tool_build_spec.md) (original plan, preserved for context)

---

## North star

Buyer-facing database of franchise financial performance data, sourced from public FDDs. Programmatic SEO + affiliate revenue (FranNet, ApplePie, etc.). Full plan in the build spec; PROJECT_TRACKER.md is the authoritative status doc; this file is the cross-session resume narrative.

---

## Current state (2026-05-19 evening)

**Live at https://franchisedepth.com.** HTTPS active, custom domain via Porkbun, GitHub Pages from `docs/` on `main`. Sitemap submitted to GSC; IndexNow pinged Bing/Yandex/Seznam/Naver.

| Surface | Stat |
|---|---|
| **Brands in DB** | **461** (+338 from baseline 123 this session) |
| HTML pages on site | ~3,400 (461 brand + 2,410 capped compare + 51 state + 28 category + 8 guide + 9 report + dashboard) |
| Brands with Item 19 disclosed | 316 |
| Item 19 records | 5,448 |
| Item 20 location rows | 43,575 |
| Industries with brands | 28 (all 184 prior NULL brands placed) |
| Compare pages (static) | 2,410 (capped — both brands need item19 + ≥100 outlets) |
| **Customer-facing reports** | **9 — `/reports/` hub + 8 ranking pages** |
| **Internal dashboard** | **`/dashboard/` v6 — interactive filters, 4 Chart.js viz, customizable columns, multi-select compare modal, ★ Watchlist, CSV export** |
| **Luxury redesign preview** | **https://josh-max2.github.io/Datamaker-relux/** (separate mirror repo — Inter+IBM Plex Mono+Source Serif 4, dark palette) |
| Audit | 0 tier-1 fails · 18 tier-2 (non-blocking) |

**Today's brand-count expansion (123 → 461) via three batches:**
1. **MN CARDS 185-brand batch** (+189 net, ~$57 API spend, parallel pools, ~75 min wall-clock)
2. **WI portal Max-plan batch** (+74 net, $0 marginal via `claude -p`, ~2.5 hours sequential)
3. **MN long-tail Max-plan batch** (+75 net, $0 marginal via `claude -p`, ~2.5 hours sequential)

Plus 184 NULL-industry brands manually placed (curated `scripts/fix_null_industries.py`), and Item 19 chart Tier 1.1 fix (chart suppressed on `longitudinal_affiliate` / `affiliate_only` brands).

**Pipeline:** Default = `extract_v2.py` via `claude -p` (Max plan, $0 marginal). API path (`extract.py`) retained for parallel-pool acceleration. Survey/download/extract orchestrators: `survey_wi_missing.py` + `download_wi_candidates.py` + `wi_max_plan_pipeline.py` + `filter_mn_longtail.py` + `max_plan_extract_loop.py` (sequential with localStorage checkpoint).

**State-portal map for future expansion:** Only MN + WI publish FDDs as downloadable PDFs. CA / IL / NY / MD / VA / WA / IN / etc. show registration metadata only — actual FDDs need a Public Records Act request. Tested via CA DocQnet/FRANSES (Microsoft Dynamics CRM portal): "No related documents for this search result." Net: no more brands accessible without a different acquisition strategy.

**What's queued:**

1. **Phase 4 Tier 1.2 — calculator math sanity warnings** (Domino's-style implausible Y1 net check)
2. **Phase 4 Tier 2 — TL;DR Key Facts card** (compact, AEO-citation-friendly) at the top of each brand page
3. **Phase 4 Tier 4 — paid-tier validation** (waitlist form + `/pricing/` preview + "Best Performing" SEO pages). No engineering until 4 gates green: ≥50 waitlist + ≥5 consultant calls + 500 brands + §16 complete.
4. **Brand-page polish** (deferred from feedback): Item 19 revenue-distribution callout, lead-form consolidation (3→2), compare-similar-brands visual differentiation.
5. **Mirror redesign Phase 2-3** (Datamaker-relux only): more chart customization, editorial pull-quotes, premium loading states. Mirror serves at github.io subpath; parser repo untouched.

Full open work list in `PROJECT_TRACKER.md` §16 (Phase 4 quality fixes), §17 (paid tier strategy), §18 (revenue projections).

---

## Historical phases (preserved for context)

The sections below cover Phase 0 (extraction validation) and Phase 1 (WI scraper + 20-brand pilot) from 2026-05-16. They documented the early gates and pilot findings that justified scaling the pipeline; live-site decisions since then are in `PROJECT_TRACKER.md` §13 (changelog).

### Phase 0 — Narrow run validation (2026-05-16) — PASS on born-digital, KNOWN GAP on scanned

Validated on 4 FDDs covering distinct failure modes. Phase 0 gate per advisor + user direction was: "Item 19 numeric values match source PDF, cohorts correctly identified, outlet counts/reporting periods correct, no hypothetical leakage" — verified on **3 of 4** FDDs (Servpro 2014 is a scanned PDF, exposing a known infrastructure gap, not a prompt bug).

| Step | Status | Notes |
|---|---|---|
| Crumbl 2023 (easy case) | ✅ PASS | 17/17 numeric values match. 3 records, 1 cohort. |
| Service Experts 2025 (no-FPR case) | ✅ PASS | Correctly identified `has_item19=false`. Item 20 yearly summary 100% match (0 franchised + 78→89 company-owned). Tests franchised/company-owned separation. |
| ReBath 2025 (multi-cohort + multi-metric STRESS test) | ✅ PASS | 32 records across 4 cohorts × 8 metrics. 5 spot-checks all match (CPL, Marketing, Jobs Sold, Gross Sales/Unit, Gross Margin). |
| Servpro 2014 (scanned PDF) | ⚠️ KNOWN GAP | OCR-grade text extraction. Items 5/6/20 partially extracted with low self-confidence (0.45); Items 7/19 section-find regex couldn't find headings in OCR garbage. Need OCR step before extraction. |
| Build Wisconsin scraper (Playwright) | Not started | Next phase — extraction quality is locked. |
| `src/db.py` — full schema | Not started | Deferred until we move beyond JSON outputs. |

**Phase 0 verdict:** Born-digital FDDs of varying complexity (simple/multi-cohort/no-FPR) extract reliably with the current prompts. Scanned PDFs require an OCR preprocessing step before this pipeline can handle them. Ready to move to scraper.

**Phase 1 first-30 (2026-05-16, same day):** WI Playwright scraper for one franchisor (Mr. Rooter) end-to-end seam validated. Scraper installed Playwright + chromium, did portal recon, found the search → result → click-Download flow programmatically, downloaded the current 2026 Mr. Rooter FDD (id=640790, 3.94 MB), SHA-256 captured. Pipe through `src.extract` ran clean: all 5 items located, 6 JSONs written, $0.35 total. Architectural seam confirmed.

**Phase 1 pilot (2026-05-16, same day):** Generalized scraper into `src/scrapers/wisconsin.py` (context-managed, rate-limited, SHA-256 dedup). Ran 20 home-services franchisors end-to-end. Mix: 4 large (Servpro, 1-800-GOT-JUNK, Roto-Rooter, Two Men), 10 mid (The Maids, Molly Maid, Merry Maids, Anago, Lawn Doctor, Bath Fitter, Ace Handyman, Junk King, Mr. Handyman, JDog), 6 small (Bin Blasters, Bumble Roofing, Insulation Commandos, Patch Boys, Lightspeed Restoration, Mosquito Sheriff). **20/20 scraped, 20/20 extracted, total ~$6.50** (incl. $0.53 in gap-fill re-extractions after the regex fix). See "Pilot findings" below.

### Phase 1 pilot findings (20 home-services FDDs from WI portal)

**Headline numbers:**
- Scrape success: 20/20
- Extract success (after fixes below): 20/20
- Total cost: ~$6.50 (avg $0.30/FDD; min $0.04 for no-FPR brands, max $0.49)
- Item 19 has_item19=false rate: 5/20 = 25% (lower than spec's ~34% estimate)
- Item 19 records produced: 151 (avg 11.6 per brand-with-FPR, range 0-27)
- Item 20 state-year rows: 1,779 total (avg 105/FDD, max 153, **no parse errors** — streaming + 32k max_tokens holding)
- Dedup hits: 0 (expected — single-state pilot, no near-duplicates)

**Three real bugs/gaps surfaced (all fixed in-loop):**

1. **Section regex too strict on separators** — `find_section` missed JDog Items 19/20 and Two Men Items 5/7/19/20.
   - JDog uses `"ITEM 19 - FINANCIAL PERFORMANCE, REPRESENTATIONS"` (dash + **comma inside title**)
   - Two Men uses `"Item 19? FINANCIAL PERFORMANCE..."` where `?` is pypdf's fallback for unicode en-dash (U+2013)
   - Fix: expanded separator class to `[\.\-:,?–—\s]*` and changed title patterns to allow comma between words. After fix: all 5 sections located in both PDFs. Re-extracted, $0.53 additional cost.

2. **Cohort enum gap: multi-unit ownership groups** — Mr. Handyman (5 records), Merry Maids (13 records) define cohorts by how many units a franchisee owns ("Single-Unit Franchisees Group", "5-7 Unit Group", "FOGs with 8-24 Active Franchises"). 18 of 31 `"other"` records were this pattern.
   - Fix: added `ownership_group_anchored` to enum + prompt explainer. Same flexible-anchor pattern as `tenure_year_anchored` and `performance_anchored`.

3. **Anago metadata JSON parse error** — model returned correct data ("Anago Franchising, Inc.", Florida, 2026) but with a JSON escape issue that broke `json.loads`. Recoverable from `_raw` field — needs a lenient parser fallback in `claude_client.py`. Backlog item, not blocking.

**One scraper data-quality finding:**
- Searching `"Two Men and a Truck"` in WI portal returned the **spinoff brand** `Two Men and a Junk Truck SPE LLC` (id=641608) — same parent LLC, different trade name. `latest_active()` doesn't know to prefer one over another. Backlog: ambiguous-search disambiguation (compare trade_name to query for stricter match).

**Three brands with minor metadata gaps** (not blocking):
- The Maids International: `state_of_inc` null (rest fine, conf 0.95)
- Anago: see (3) above — recoverable
- Mosquito Sheriff: `filing_year`/`issuance_date` null (cover layout edge case)

**Cohort distribution across 151 records** (with `ownership_group_anchored` now in place, future runs will reclassify):
- `performance_anchored`: 38 (quartiles common in home services — Top 10/25/50/75/100%)
- `all_franchised`: 34
- `other`: 31 → most are now `ownership_group_anchored` after the enum fix
- `open_24_plus_mo`: 27
- `open_12_24mo`: 6
- `all_company_owned`: 5
- `open_lt_12mo`: 3
- `open_36_plus_mo`: 3
- `open_48_plus_mo`: 2
- `open_60_plus_mo`: 2

**What didn't surface (yet):**
- No scanned-PDF outliers (preflight prediction held: all 20 modern WI filings are born-digital)
- No hypothetical/projection leakage (still vacuously satisfied; needs a <2-year-old brand to test)
- No JPEG-table Item 19s

### Phase 1 first-30 findings (Mr. Rooter from WI portal)

**What worked first-try:**
- WI form structure (`txtName` input, `#btnSearch` submit, ASP.NET `__VIEWSTATE` hidden fields) discovered programmatically
- Playwright `page.expect_download()` cleanly captures the server-side POST → PDF response
- Result-page parsing of the tab-separated row format identified the currently-Registered filing among 14 historical filings (2013-2026)
- Scraped PDF runs through existing `src.extract` unchanged: all 5 items located, all extract successfully

**New finding — third Item 19 cohort pattern:**
Crumbl used one cohort. ReBath used tenure-anchored years. **Mr. Rooter uses quartile-based cohorts** ("Top 10%", "Top 25%", etc.). All three are now in the test corpus. The `cohort_name` enum doesn't have a quartile value — they fall back to `"other"` with `cohort_raw` preserving the source label. Same enum-gap pattern as ReBath's "Open Prior to 2022". Worth adding `quartile_top_N` to the enum at some point, but not blocking.

**Small extraction quality finding (backlog):**
Mr. Rooter metadata confidence was 0.62 (vs Crumbl/Service Experts/ReBath at 0.95+). `legal_name`, `state_of_inc`, `issuance_date` came back null because `src.extract` only sends `body_start..body_start+4` for metadata, and Mr. Rooter's cover page with that info is deeper. Fix is to search for the cover page specifically rather than assume it's near `body_start`.

### Phase 0 criterion-by-criterion (final scoring, post advisor round 2)

| Criterion | Crumbl | Service Experts | ReBath | Servpro 2014 |
|---|---|---|---|---|
| Item 19 numeric values match source | ✅ 17/17 | ✅ (no-FPR correctly flagged) | ✅ 5/5 spot-checks | ❌ section not found (OCR garbage) |
| Cohorts correctly identified | ✅ 1 cohort | ✅ franchised vs co-owned separated | ✅ 4 cohorts column-aligned | N/A |
| Outlet counts + reporting periods correct | ✅ 324, 2022 | ✅ 0/78→89, 2022-24 | ✅ 113/2/16/95, 2024 | partial |
| No hypothetical numbers leaked | ✅ vacuous (none in source) | ✅ vacuous | ✅ vacuous | N/A |
| Item 20 spot-check | ✅ yearly+state rows match | ✅ yearly match | ✅ yearly + AL match | not done |

Criterion 4 ("no hypothetical leakage") is **vacuously satisfied across this sample** — none of the 4 source PDFs contain hypothetical/projected numbers mixed with actuals. The system prompt's "skip projections" rule was never tested by a positive case. **Future TODO:** when batching the WI corpus, find a brand that publishes model-store projections in Item 19 (often "new-build" franchises do this) and verify the rule fires.

### Preflight before Phase 1 (WI scraper) — DONE 2026-05-16

**Method:** Couldn't directly download from WI portal (stateful ASP.NET form, no Playwright yet), so used **Minnesota CARDS as a proxy** — modern multi-state franchisors file the same PDF in every registration state. Pulled 19 distinct 2024-2025 FDDs from MN CARDS via Google site-search discovery. WI has 1,879 active franchisor registrations (per `apps.dfi.wi.gov/apps/franchiseefiling/activeFilings.aspx`); MN's filings overlap heavily with that list.

**Operational test:** does the section finder locate Items 5/6/7 AND (Item 19 OR Item 20) — i.e., everything the pipeline needs.

**Result: 19 / 19 = 100% born-digital** (all 5 items located cleanly on every PDF). Confirms Servpro 2014's failure is the rare exception (11-year-old pre-electronic filing).

**Decision applied:** per the user's rule "fully-scanned <5% → OCR is true backlog":
- ✅ OCR stays in backlog
- ✅ Proceed to Path B (WI Playwright scraper)

**Caveats — three sharper ones (per advisor 2nd-round review):**

1. **Proxy population bias** — every MN sample is a franchisor who *chose to register in MN*. That selects for franchisors with mature legal/compliance ops — exactly the cohort most likely to file born-digital PDF/A. The WI long tail (small/regional brands that registered once in 2017 and never amended) is *under-represented* by this sample. So 100% born-digital is real **for multi-state-active modern franchisors**; it's an upper bound for the WI population broadly. The decision (OCR is backlog) still holds — 0% in the sampled cohort gives plenty of room before tripping the 5% threshold — but expect *some* scanned outliers in the WI long tail.

2. **What the test measures** — `preflight_analyze_v2.py` checks whether the section-finder regex can navigate the PDF (find Items 5/6/7/19/20 by heading text). This is the right operational gate for "does my code run today" but it's narrower than "is OCR needed for high-quality extraction." A PDF could pass v2 (headings extract fine) and still have its Item 19 *table* rendered as an embedded raster image, which only surfaces as garbage at extraction time. Mitigation: spot-checked 3 of the 19 by inspecting Item 19 text density (HPB Blinds, i9 Sports, one unbranded studio franchise) — all have real numeric text. No JPEG-table failure mode in this sample.

3. **Temporal scope** — measures *current registrations only*. Pre-2018 historical filings (Servpro 2014 era) are more likely to be scanned. If we ever want longitudinal data (10-year trend lines per franchisor), OCR moves back to Phase 1.

**Sample analyzed** (`fdd-tool/data/preflight/`): All County, Always Best Care, Big Blue Swim, Decimal, First Day Franchising, Get-A-Grip, Happier at Home, MB Franchise Holdings, Office Pride, @properties, SAMBAZON, Supercuts, Tea Pulse, Velox Valuations, Yasubee Ramen (×2 versions), HPB Blinds and Shutters, i9 Sports, one unbranded studio franchise. Verticals: home services, real estate, F&B, hair care, valuation, fitness, retail.

**Scripts:** `preflight_download.py`, `preflight_analyze_v2.py` (v1 used a too-strict char-ratio heuristic that false-positived on signature/exhibit pages — v2 uses the actual section-finder, which is the operational gate. v1 kept as cautionary tale).

---

## Stack decisions (locked in)

- **Python** via `uv` (NOT Poetry — spec says Poetry but Josh's global pref is uv)
- **SQLite** for MVP, Postgres later
- **Playwright** for scraping (portals are JS-heavy)
- **Anthropic SDK** for extraction — Sonnet 4.6 for Item 19, Haiku 4.5 for easy items (cost optimization)
- **Prompt caching** on the extraction system prompt (90% off after first call)

---

## Validation results — 4 FDDs

Cost summary across all 4 runs: **$1.47 total** (Crumbl $0.52, Service Experts $0.18, ReBath $0.44, Servpro $0.33). Within budget.

### Crumbl 2023 (Yale-mirrored) — EASY case

**Item 19:** 17/17 PDF-table values match. 1 cohort (324 franchised outlets), 3 metrics (Total Revenue, Gross Profit, Net Profit), 4 stats each + 3 pct-above-avg. Negative `$(160,202.58)` correctly parsed to `-160202.58`. Model flagged a real source-data anomaly ("140 outlets" dangling reference, verified via grep).

**Item 20:** 9 yearly + 153 state-year rows. Yearly summary exact (Franchised 54→141→325→688 across 2020-2022).

**Independent oracle:** Yale's prose independently confirms the 324-outlet cohort and 47% coverage. Dollar values were embedded in Yale's "Figure 4" (image), not text — so those rely on the PDF table itself as the source of truth.

### Service Experts 2025 (MN CARDS) — NO-FPR + franchised/company-owned separation

**Item 19:** `has_item19=false`, records=[], confidence 0.98. Source PDF explicitly says "We do not make any representations about a franchisee's future financial performance..." — correctly identified.

**Item 20:** Franchised 2022/2023/2024 = 0/0/0. Company-Owned = 78→81→89. Total = 78→81→89. All match PDF exactly. Item 20 also includes "We began offering franchises in April 2025" which explains why franchised is 0 — first-time franchise offering.

**Items 5-7:** Initial fee $25,000-$59,900 (varies by Start-Up/Conversion type), royalty + investment all extracted cleanly.

### ReBath 2025 (MN CARDS) — STRESS test (multi-cohort + multi-metric)

**Item 19:** 32 records extracted = 4 cohorts × 8 metrics. Cohorts: Total Open 1+ Years (113), Open in 2023 (2), Open in 2022 (16), Open Prior to 2022 (95). Metrics: Marketing $/Unit, Marketing $/Person, CPL, Conversion Rate, Total Jobs Sold, Gross Sales/Unit, Gross Margin, Net Income.

5 cross-cohort spot-checks (verified against the source PDF directly):
- Marketing $/Person: 0.23 / 0.32 / 0.15 / 0.24 ✅
- CPL: 162 / 169 / 160 / 162 ✅
- Total Jobs Sold: 24,912 / 270 / 1,745 / 22,897 ✅
- Gross Sales/Unit: 3,904,233 / 2,441,964 / 2,008,432 / 4,254,310 ✅
- Gross Margin: 51.7% / 65.3% / 53.9% / 51.3% ✅

**Schema gap found:** the "Open Prior to 2022" cohort (95 outlets) got `cohort_name: "other"` because my enum only has `open_24_plus_mo`. The `cohort_raw` field preserved the real value, so no info loss — but for clean rollup pages, the enum needs `open_36_plus_mo` and `open_48_plus_mo`.

### Servpro 2014 (fddexchange.com) — SCANNED PDF failure mode

The text extraction returns OCR garbage: `"^a^tranchlsorsupplementsthelnformatlonprovldedlnthls"`, `"$4344,000.00"` (two numbers run together). My section-finder regex couldn't locate Item 7 or Item 19 in the garbled text.

Items 5, 6, 20 *were* found by regex (their headings happened to survive OCR enough) and the model attempted extraction with appropriately low self-confidence (0.45). Notes flagged OCR artifacts explicitly.

**Known gap:** the pipeline needs an OCR preprocessing step (Tesseract or Claude vision OCR) before scanned PDFs can be reliably parsed. This was already listed as a gap in the original confidence-calibration section; Servpro confirmed it.

---

## Cost model (updated as we learn)

Per-FDD extraction estimate (Sonnet 4.6 + vision):
- Input text: ~25k tokens → $0.075
- Input images: ~8k tokens → $0.024
- Output JSON: ~1.5k → $0.023
- **Per FDD: ~$0.12**

Phase budgets:
- Narrow run (5 FDDs + iteration): **~$2-5**
- Wisconsin batch (1,500 FDDs): **~$180**
- + California batch (~2,000 more): **+$240**
- Re-runs (budget 2x): **+$400**
- **MVP total: ~$650-800 one-time**

Annual refresh: ~$500-700/yr.

---

## Confidence (parsing reliability)

| Item | Confidence | Failure modes to watch |
|---|---|---|
| Item 5 (initial fee) | 95% | Variations by territory |
| Item 6 (royalty/marketing) | 90% | Tiered royalties |
| Item 7 (total investment) | 90% | Subcomponents — skip for MVP |
| Item 20 (outlets) | 85% | Transferred vs reacquired columns |
| Item 19 (financial perf) | 65-75% | No fixed format; hypotheticals; scanned PDFs; footnotes |

**Known gap:** spec has no OCR fallback for scanned-image PDFs. Add to backlog.

---

## Open questions / decisions to make

1. **OCR fallback** — what % of WI FDDs are scanned images? Need a quick survey before Phase 1. If <5%, defer. If >15%, add Tesseract or Claude vision OCR step.
2. **Entity resolution strategy** — same brand files in WI + CA + MN. Match by legal_name fuzzy? By NAICS + brand fuzzy? Decision needed before CA scraper (Phase 2).
3. **What counts as a "qualified" Item 19 record for SEO display?** confidence ≥ 0.8? Manual review pass? Both?
4. **Hosting target for Next.js frontend** — Vercel default or something cheaper at scale?

---

## File layout (actual — as of 2026-05-16, post audit cleanup)

```
parser/
├── fdd_tool_build_spec.md         # The original plan
├── HANDOFF.md                     # This file
└── fdd-tool/
    ├── README.md                  # Points to this HANDOFF; documents run commands
    ├── pyproject.toml             # uv-managed deps: anthropic, pypdf, pdfplumber, pypdfium2, pillow, python-dotenv
    ├── .gitignore                 # Now ignores .env, data/, output/
    ├── .env                       # ANTHROPIC_API_KEY (gitignored)
    ├── main.py                    # CLI entry: forwards to src.extract
    ├── src/                       # The pipeline (the only "production" code)
    │   ├── __init__.py
    │   ├── pdf_utils.py           # text extract, body start, cover page, Item N boundary, page rasterizer
    │   ├── prompts.py             # 6 prompts: SYSTEM + METADATA + 5 Items (cohort_name enum: 12 values + flexible anchors)
    │   ├── claude_client.py       # SDK wrapper with prompt caching + streaming for large outputs
    │   ├── extract.py             # main orchestrator: PDF -> 6 JSON files
    │   └── scrapers/
    │       └── wisconsin.py       # WI portal Playwright scraper (context-managed, dedup, rate limit)
    ├── scripts/                   # One-off validation, inspection, preflight, Phase 1 work (run from fdd-tool/)
    │   ├── inspect_pdf.py, inspect_item19.py, inspect_new_pdfs.py, inspect_3.py, inspect_servpro.py, inspect_mr_rooter_cover.py
    │   ├── verify.py, verify_service_experts.py, verify_rebath_item20.py
    │   ├── check_hypotheticals.py
    │   ├── rerun_item20.py, reverify_mr_rooter.py
    │   ├── preflight_download.py, preflight_analyze.py (v1 deprecated), preflight_analyze_v2.py (the keeper), spotcheck_unknowns.py
    │   ├── recon_wi_portal.py            # Phase 1: WI form / network reconnaissance
    │   ├── scrape_wi_mr_rooter.py        # Phase 1 first-30: hand-coded single-franchisor scraper
    │   ├── pilot_wi_home_services.py     # Phase 1 pilot: scrape + extract 20 home-services brands
    │   ├── audit_pilot.py                # Audits the pilot manifest (note: reads manifest, not output JSONs)
    │   ├── diagnose_section_misses.py    # Diagnosed JDog/Two Men section-regex misses
    │   ├── reextract_missed.py           # Re-ran missed sections after regex fix
    │   └── inspect_other_cohorts.py      # Surfaced the multi-unit ownership cohort pattern
    ├── data/
    │   ├── crumbl_yale.pdf        # 456-page Yale combo (Crumbl 2023 FDD)
    │   ├── service_experts_mn.pdf # 222-page Service Experts 2025 (from MN CARDS)
    │   ├── rebath_2025_mn.pdf     # 276-page ReBath 2025 (from MN CARDS) — multi-cohort
    │   ├── servpro_2014.pdf       # 127-page Servpro 2014 — SCANNED, OCR garbage
    │   ├── molly_maid_panda.pdf   # 4-page preview only (kept as reference of why panda mirror doesn't work)
    │   ├── preflight/             # 19 modern (2024-2025) FDDs from MN CARDS for the preflight survey
    │   └── wi_scrape/             # Phase 1: 21 scraped WI FDDs (Mr. Rooter + 20 home-services pilot)
    └── output/
        ├── crumbl_yale/
        ├── service_experts_mn/
        ├── rebath_2025_mn/
        └── servpro_2014/
            # each contains: metadata, item5/6/7/19/20 JSONs
```

---

## How to resume next session

1. Read **PROJECT_TRACKER.md** first — that's the live status doc.
2. Skim this file's **"Current state (2026-05-18)"** section for narrative context. Historical phase sections below are preserved as record, not current.
3. Check `git log --oneline -20` to see the most recent ships.
4. When work ships, update PROJECT_TRACKER §0 / §4 / §13, then bump the "Last updated" line at the top of this file.

### Suggested next action (post-F4.7 v2):

The calculator improvements just shipped (3bb9fdb). Next-highest-leverage items, in order:

1. **Dedup + entity resolution** — before any multi-state scrape we need to handle "same brand, different state filing." Approach: SHA-256 on PDF bytes for exact-duplicates; fuzzy `legal_name` + NAICS for near-duplicates from different states. Cheap to build, blocks the MN CARDS expansion.

2. **MN CARDS expansion (+500–700 brands)** — direct PDF URL pattern works without Playwright. Discovery via `site:cards.web.commerce.state.mn.us` Google search + the registration list. Estimated 1-2 days of pipeline runs at $0.17/FDD ≈ $85–120 API-equivalent.

3. **Attorney review** — calculator + Item 19 framing review. Not blocking, but the tracker's milestone is "before $2.5k/mo revenue or significant traffic." Schedule it.

4. **Pillar 5 (off-page distribution)** — Reddit / niche forum / podcast outreach. Owner execution work, not Claude Code.

5. **Email-this-analysis lead capture** (deferred from F4.7 v2 spec) — Formspree form on the calculator with hidden fields populated from current inputs, sends user a copy of their calc breakdown. Acts as a second lead-magnet path alongside the PDF.

### Historical pilot backlog (Phase 0 + Phase 1, may still be relevant):

### Phase 1 pilot backlog (from 2026-05-16, may still be relevant):
1. **Lenient JSON parser** in `claude_client.py` — Anago-style escape errors are recoverable from raw text. Try `json.loads`, fall back to regex extraction, fall back to raw.
2. **Search disambiguation** in `WisconsinScraper.search()` — when query matches multiple distinct franchisors (Two Men and a Truck vs Two Men and a Junk Truck), prefer the trade_name with strongest substring match to the query.
3. **Investigate Mosquito Sheriff metadata** — cover layout edge case missed `filing_year`/`issuance_date`. Probably an unusual cover format.
4. **Manifest staleness** — `audit_pilot.py` reads `_pilot_wi_home_services.json` not the actual extracted JSONs. After gap-fill re-extractions the manifest got stale. Either rebuild manifest from output dirs, or re-run pilot end-to-end.

### Small backlog items surfaced during Phase 0 + Phase 1 first-30:
1. **OCR fallback for scanned PDFs** — preflight (2026-05-16) confirms this is true backlog: 0/19 modern MN filings are scanned. Only relevant if/when we add pre-2018 historical filings.
2. ~~**Expand `cohort_name` enum**~~ — DONE 2026-05-16. Added `open_36_plus_mo`, `open_48_plus_mo`, `open_60_plus_mo`, `tenure_year_anchored` to ITEM19_PROMPT.
3. **Add a confidence threshold filter** when materializing to DB — records with `confidence < 0.7` go to a review queue, not the public-facing tables.
4. **`find_fdd_body_start`** still returns page 2 for some PDFs (Service Experts, ReBath) — works because `find_section` now does its own TOC filtering, but the function is misleading. Either fix or delete.
5. **Hypothetical/projection disambiguation test** — deferred per user feedback. When processing the full WI corpus, look for franchisors with <2 years operating history (they'll publish pro-forma projections in Item 19). Verify the prompt's "skip projections" rule fires correctly against real data, rather than pre-finding a test FDD now.
6. **Add `quartile_top_N` to `cohort_name` enum** — Mr. Rooter (2026 WI) uses "Top 10%", "Top 25%" cohorts. Currently fall back to `"other"` with `cohort_raw` preserved. Worth a dedicated enum value for clean rollup pages.
7. ~~**Metadata extraction page-range**~~ — FIXED 2026-05-16. Added `find_cover_page()` with a scoring heuristic; metadata prompt now uses `cover_page-1..cover_page+2`. Mr. Rooter confidence 0.62 → 0.99, all fields populated.
8. **Add `quartile_top_N`** → REPLACED with flexible `performance_anchored` (2026-05-16). Same pattern: `ownership_group_anchored` added when pilot surfaced multi-unit ownership cohorts.

---

## Decision log

| Date | Decision | Why |
|---|---|---|
| 2026-05-16 | uv over Poetry | Josh's global Python stack |
| 2026-05-16 | Narrow run = 5 FDDs before 1,500 | Cheap validation gate |
| 2026-05-16 | Sonnet 4.6 for Item 19, Haiku 4.5 for easy items | ~30% cost reduction with negligible accuracy loss on tabular items |
| 2026-05-16 | Used Sonnet 4.6 for ALL items in narrow run (not Haiku for easy items yet) | Wanted clean baseline before introducing model heterogeneity; can swap easy items to Haiku in Phase 1 |
| 2026-05-16 | Item 20 needs streaming + max_tokens=32000 | State-by-state tables are long; default 8192 truncates output mid-JSON |
| 2026-05-16 | Used Yale-mirrored Crumbl PDF instead of WI portal for narrow run | Yale serves a real FDD as a public PDF; WI portal needs Playwright session-aware scraper which is deferred. Production pipeline still targets state portals per spec §2. |
| 2026-05-16 | MN CARDS is a viable source for 2-3 brands at zero scraper cost | The `cards.web.commerce.state.mn.us/documents/{GUID}/download?...` URL pattern is stable and works with a browser User-Agent + Referer. Found Service Experts and ReBath this way. Google `site:cards.web.commerce.state.mn.us` is the discovery mechanism. |
| 2026-05-16 | Fixed `find_section` to filter TOC entries | TOC pages have 15+ ITEM references; body pages have ≤4. Now requires a body candidate with `<=4 other refs AND >1500 chars` before falling back to the last candidate. Crumbl worked despite the bug because Yale prefix hid the TOC; Service Experts/ReBath exposed it. |
| 2026-05-16 | Added per-PDF namespaced output dirs (`output/{pdf_stem}/`) | So extractions on multiple FDDs don't overwrite each other. |
| 2026-05-16 | `max_tokens` parameterized + streaming for >8192 | Item 20's state-by-state table can exceed 8192 output tokens; SDK refuses non-streaming for max_tokens that might exceed 10-min timeout. |
| 2026-05-16 | Expanded `cohort_name` enum with deep-tenure values | ReBath surfaced the gap (95-outlet "Open Prior to 2022" cohort fell back to `"other"`); mature brands (McDonald's, Subway) will hit this too. |
| 2026-05-16 | Used MN CARDS as preflight proxy for WI scanned-ratio survey | WI portal needs Playwright; MN CARDS exposes direct download URLs. Modern multi-state franchisors file the same PDF across states, so the bucketing answer is portable. Documented as a proxy with caveats. |
| 2026-05-16 | OCR stays in backlog (preflight 19/19 born-digital) | Empirical: 0% scanned in modern MN-filed FDDs (sample n=19). Triggers the `<5%` arm of the user's decision rule. Revisit if/when we ingest pre-2018 historical filings. |
