# FranchiseDepth User Features Roadmap

**Last updated:** 2026-05-17
**Status:** Active reference document
**Maintainer:** Josh

---

## Overview

This document catalogs every buyer-facing feature for FranchiseDepth with priority scores, build effort estimates, specs, dependencies, and legal considerations.

Use this as a backlog. Pull features into sprints based on priority + dependency order. Update priority scores when traffic data informs what's actually moving the needle.

---

## Already Shipped (untracked — added 2026-05-17)

Features live in production that aren't catalogued elsewhere in this document. Follow-ups originally flagged here have been resolved this session.

| Feature | Location | Status | Resolution |
|---|---|---|---|
| **Closure rate badge** (🟢 / 🟡 / 🔴) | Brand page fact strip | ✅ Live | **REVIEW RESOLVED 2026-05-17:** Originally labeled "System health: Stable/Mixed/Contracting" — editorial framing. Reframed as "Closure rate: X.X%" with literal arithmetic ("11 of 370 outlet-years"), `title=` tooltip stating the bands are formula-derived, and inline link to methodology §7. No editorial language remains. |
| **Arithmetic breakeven scenario** | Brand page, below fact strip | ✅ Live | **REVIEW RESOLVED 2026-05-17 (FTC §436.5(s)):** Originally a declarative "Typical breakeven: X-Y years". Reframed as "Arithmetic breakeven scenario" with explicit "This is not a projection" disclaimer, method label (reported $ / reported % / industry typical), link to FTC §436.5(s) compliance guide, and per-cohort histogram showing variance. Attorney review still recommended pre-custom-domain. |
| **Top-states bar chart** ("Where they operate") | Brand page | ✅ Live | None — pure data display. |
| **Outlet growth bar chart** | Brand page | ✅ Live | **DECISION 2026-05-17:** Keeping the bar chart; F1.4 sparkline-in-table not built (downgraded — chart is the richer view and the page has room for it). |
| **Source links on Item 19 numbers** (page-N PDF deep-links) | Item 19 table | ✅ Live | Matches F1.9 — tagged Built in master tables. |
| **Verified-from line** ("Verified from {YEAR} FDD, issued {DATE}") | Brand page header | ✅ Live | Matches F1.7 — tagged Built. Extended this session with per-section "Source: {YEAR} FDD · pages X · verified {DATE}" lines (F2.6 fulfillment). |
| **Methodology page** | `/methodology/` | ✅ Live | Expanded from ~700 to 2045 words, 11 sections including data dictionary + update log. F2.1 closed. |
| **Cohort enum: `performance_anchored`, `ownership_group_anchored`, `tenure_year_anchored`** | Extraction prompts | ✅ Live | Schema-level, not user-facing. Documented in the methodology page. |

**Net:** All follow-ups from the original "Already Shipped" table are resolved. Risk badge and breakeven both now satisfy the project's "no editorial framing" principle and FTC §436.5(s) framing requirements respectively.

### New shipped infrastructure (this session, 2026-05-17)

| Item | Location | Notes |
|---|---|---|
| **Site audit script** | `scripts/audit_site.py` | 6 audit dimensions (HTML validity, JSON-LD parse, internal link resolution, FAQ schema-content match, compliance coverage, accessibility). Currently 0 issues across 76 pages. |
| **OG image generator** | `scripts/generate_og_image.py` | Pillow-based 1200×630 social card + favicon set (16/32/180/.ico) |
| **Self-hosted cookie consent** | `templates/_consent.js` | Klaro-style, `fd_consent_v1` localStorage, dispatches `fd-consent-update` events to GA4 wrapper |
| **Consent-gated GA4 wrapper** | `templates/_ga4.js` | Only loads gtag.js after analytics consent; tracks `scroll_75`, `cta_click`, `outbound_click`, `lead_form_submit` |
| **Two-PowerShell extraction architecture** | `scripts/scrape_loop.py` + `scripts/extract_loop.py` | Uses `claude -p` subprocess to invoke Max plan auth (not API credits). Scrubs ANTHROPIC_API_KEY from subprocess env. **Ready to run; not yet started — awaiting user "go".** |
| **Local HTTP serve script** | `scripts/_serve_docs.py` | Serves docs/ at `/Parser/` to match prod URL structure for local testing |

---

## Priority Scoring Framework

| Priority | Meaning | Timeline |
|----------|---------|----------|
| **P0** | Launch blocker — must have before going live to production domain | Pre-launch |
| **P1** | Critical — drives core buyer value or required for monetization | Week 1-2 post-launch |
| **P2** | High value — significant lift to conversion or engagement | Month 1-2 |
| **P3** | Strong improvement — meaningful UX or SEO gain | Month 2-3 |
| **P4** | Polish — incremental improvement | Month 3-6 |
| **P5** | Future/experimental — defer until traffic justifies | Month 6+ |

## Buyer Impact Scale

- **Critical:** Buyer can't make decision without it
- **High:** Significantly improves decision quality
- **Medium:** Useful enhancement
- **Low:** Nice-to-have polish

## Effort Scale

- **XS:** <2 hours
- **S:** 2-6 hours
- **M:** 6-16 hours
- **L:** 16-40 hours
- **XL:** 40+ hours

---

## Category 1: Brand Page Core

These features live on every individual brand page (e.g., `/brand/crumbl-cookies`).

### F1.1 — Opening summary paragraph
- **Priority:** P0
- **Buyer impact:** Critical
- **Effort:** S (4h)
- **Description:** First content block on every brand page — a single paragraph that contains brand name, category, headquarters, initial fee range, total investment range, outlet count, and 5-year growth direction. This paragraph is what AI engines extract for citations.
- **Specs:**
  - Templated generation from DB fields
  - Bold key numbers (fee, investment, outlets)
  - 80-120 words target length
  - Plain English, no jargon
- **Dependencies:** Brand data extracted (have)
- **Legal:** None

### F1.2 — Fact box / quick stats
- **Priority:** P0 (have basic version)
- **Buyer impact:** Critical
- **Effort:** S (already partially built)
- **Description:** Sidebar/top card showing the critical numbers at a glance. Currently exists but needs liquid capital field.
- **Specs:**
  - Initial franchise fee
  - Total investment range
  - Royalty %
  - Marketing fee %
  - Liquid capital required (NEW)
  - Net worth requirement
  - Outlets total (current)
  - States operating in
- **Dependencies:** None
- **Legal:** None

### F1.3 — Item 19 financial performance table
- **Priority:** P0 (have)
- **Buyer impact:** Critical
- **Effort:** Built
- **Description:** Already implemented. Shows cohorts, metrics, average/median/quartiles.
- **Specs:**
  - Source PDF link on every number
  - "Not disclosed" if franchisor didn't include Item 19
  - Cohort labels clearly explained
- **Dependencies:** None
- **Legal:** Source citation required (compliance)

### F1.4 — Outlet growth table + sparkline chart
- **Priority:** P1
- **Buyer impact:** High
- **Effort:** M (8h)
- **Description:** Currently table-only. Add inline sparkline chart showing 5-year outlet growth trend. Pure table is dry.
- **Specs:**
  - Sparkline chart (~150px wide, inline with table)
  - Color-coded: green for growth, red for decline, gray for flat
  - Hover tooltip shows exact year-over-year change
  - Use Chart.js or vanilla SVG
- **Dependencies:** Item 20 data (have)
- **Legal:** None

### F1.5 — FAQ section
- **Priority:** P0
- **Buyer impact:** Critical (huge AEO impact)
- **Effort:** **M (~12h total, one-time):** ~10h to build the template + JSON-LD wiring + question library, ~2h to wire the template into the generator and validate output across 5-10 sample brands. Programmatic generation means per-brand cost is zero at runtime.
- **Description:** 5-7 question-and-answer block matching how buyers actually search. Wrapped in JSON-LD FAQPage schema. Drives AI Overview citations.
- **Specs:**
  - Standard questions: "How much does a [Brand] franchise cost?", "How much do [Brand] franchises make?", "What is the royalty fee for [Brand]?", "How many [Brand] locations are there?", "How long until breakeven for [Brand]?", "Is [Brand] a good franchise to buy?", "Where can I open a [Brand] franchise?"
  - Answers in 2-4 sentence paragraphs (NOT bullet points — AI prefers prose)
  - JSON-LD FAQPage schema markup
  - Programmatically generated from DB
- **Dependencies:** Item 19, Item 20 data
- **Legal:** "Breakeven" question must use scenario framing (FTC §436.5(s))

### F1.6 — Industry context paragraph
- **Priority:** P1
- **Buyer impact:** High
- **Effort:** **S (~6h for template) + spot-check time:** template + per-category sentence library is the 6h. Then spot-check a ~10% sample of generated paragraphs (~10 min/brand × maybe 25 brands = ~4h). Do NOT manually review every page at scale.
- **Description:** 2-3 sentences placing the brand in its category. Differentiates pages from raw-data competitors and increases AI citation likelihood.
- **Specs:**
  - Reference 1-2 competitor brands in same category
  - Note distinguishing feature of the brand
  - Manually reviewed for accuracy (not pure auto-generation)
- **Dependencies:** Category classification (have)
- **Legal:** Avoid editorial superlatives ("best", "worst")

### F1.7 — Date stamp / freshness indicator
- **Priority:** P0
- **Buyer impact:** High (trust signal)
- **Effort:** XS (2h)
- **Description:** Prominently displayed: "Based on 2024 FDD filed March 2024" + "Data last verified: [date]". Trust signal for both humans and AI.
- **Specs:**
  - Visible at top of brand page (under hero)
  - Visible in fact box
  - JSON-LD `datePublished` and `dateModified`
- **Dependencies:** Filing date metadata (have)
- **Legal:** None

### F1.8 — Author byline
- **Priority:** P0
- **Buyer impact:** High (E-E-A-T trust signal)
- **Effort:** XS (2h)
- **Description:** "Researched by FranchiseDepth Editorial. Data extracted from state-filed FDDs." (Owner-name TBD; do not hardcode without explicit approval.)
- **Specs:**
  - Below opening paragraph
  - Link to About page
  - JSON-LD `author` property
- **Dependencies:** About page exists
- **Legal:** None

### F1.9 — Source links on every Item 19 number
- **Priority:** P0
- **Buyer impact:** Critical (trust + AEO)
- **Effort:** S (4h)
- **Description:** Every disclosed number in Item 19 table links to the source PDF on the state portal.
- **Specs:**
  - Click on dollar amount → opens source FDD PDF in new tab
  - Tooltip: "Sourced from [State] [Year] FDD"
- **Dependencies:** PDF URLs stored (have)
- **Legal:** Demonstrates data provenance — important compliance signal

### F1.10 — "Other [category] franchises" related brands section
- **Priority:** P0 (have)
- **Buyer impact:** Medium
- **Effort:** Built
- **Description:** Already implemented. Shows up to 4 same-category siblings at bottom of brand page.

### F1.11 — Brand timeline / "About this franchise"
- **Priority:** P3
- **Buyer impact:** Medium
- **Effort:** M (10h template + data)
- **Description:** Founded year, year began franchising, parent company, key milestones.
- **Specs:**
  - Compact horizontal timeline visualization
  - Data extracted from FDD Item 1
  - Parent company link if relevant
- **Dependencies:** Item 1 extraction (not currently in pipeline — would require prompt expansion)
- **Legal:** None

### F1.12 — SBA loan eligibility indicator
- **Priority:** P2
- **Buyer impact:** High
- **Effort:** M (8h)
- **Description:** Badge showing if franchise is on SBA Franchise Directory (eligible for SBA loans).
- **Specs:**
  - Cross-reference against SBA Franchise Directory (public data)
  - Green badge if eligible: "SBA Loan Eligible"
  - Link to SBA's official page for the brand
- **Dependencies:** SBA Franchise Directory scrape (separate one-time data pull)
- **Legal:** None — SBA Directory is fully public

### F1.13 — Veteran program / discount indicator
- **Priority:** P3
- **Buyer impact:** Medium (high for veteran audience)
- **Effort:** S (4h)
- **Description:** Badge if franchise offers veteran discount or VetFran program participation.
- **Specs:**
  - Cross-reference against VetFran member directory
  - Badge: "Veterans: [X]% discount" or "VetFran Member"
- **Dependencies:** VetFran directory scrape
- **Legal:** None

### F1.14 — "Is this franchise still accepting applications?" status
- **Priority:** P3
- **Buyer impact:** High
- **Effort:** M (8h ongoing data verification)
- **Description:** Some FDDs are filed but the franchise has paused new sales. Indicate status if known.
- **Specs:**
  - Status: "Actively seeking franchisees" / "Paused new sales" / "Unknown"
  - Manual research per brand (or extracted from FDD Item 20 if available)
  - Date last verified
- **Dependencies:** Ongoing manual research
- **Legal:** Be careful with claims — frame as "based on most recent public information"

---

## Category 2: Trust & Transparency

### F2.1 — Methodology page (deep)
- **Priority:** P0
- **Buyer impact:** High
- **Effort:** L (16h)
- **Description:** 1500-2000 word page explaining data sources, extraction process, validation, refresh schedule, known gaps.
- **Specs:**
  - Data sources section (link to state portals)
  - Extraction pipeline overview
  - Validation process
  - Refresh schedule (quarterly)
  - Known limitations (no OCR for scanned PDFs, etc.)
  - Update log
  - Data dictionary (field definitions)
- **Dependencies:** None
- **Legal:** Critical for credibility

### F2.2 — About page (with real story)
- **Priority:** P0
- **Buyer impact:** High (E-E-A-T)
- **Effort:** M (10h)
- **Description:** Personal story of why FranchiseDepth exists, your background, credentials.
- **Specs:**
  - 1000+ words
  - Real photo (when comfortable)
  - Credentials (BYU Economics, Revenue Operations Analyst experience)
  - Why this exists (gap in market)
  - What's NOT covered and why
- **Dependencies:** None
- **Legal:** None

### F2.3 — FTC affiliate disclosure
- **Priority:** P0 (legal requirement)
- **Buyer impact:** Low (but required)
- **Effort:** XS (2h)
- **Description:** Federally required. Site-wide footer disclosure + per-CTA disclosure.
- **Specs:**
  - Footer text on every page
  - Italic disclaimer above every affiliate CTA
  - Link to full affiliate disclosure policy page
- **Dependencies:** Affiliate links exist
- **Legal:** 16 CFR Part 255 — required by FTC

### F2.4 — Cookie consent banner
- **Priority:** P0 (legal requirement)
- **Buyer impact:** Low (but required)
- **Effort:** XS (2h)
- **Description:** GDPR + CCPA compliance + required for ad networks.
- **Specs:**
  - CookieYes free tier
  - Bottom banner (not interstitial)
  - "Accept all" / "Reject all" / "Customize" buttons
- **Dependencies:** None
- **Legal:** GDPR/CCPA required for EU/California visitors

### F2.5 — Privacy policy + Terms of Service
- **Priority:** P0 (legal requirement)
- **Buyer impact:** Low (but required)
- **Effort:** S (4h with Termly)
- **Description:** Generated boilerplate appropriate for data aggregation + affiliate site.
- **Specs:**
  - Termly or Iubenda generated
  - Linked from footer
- **Dependencies:** None
- **Legal:** Standard requirement

### F2.6 — "Last verified" timestamps on every data field
- **Priority:** P1
- **Buyer impact:** High (trust)
- **Effort:** S (6h)
- **Description:** Inline timestamp on every data section showing when last verified against source.
- **Specs:**
  - Format: "Verified: 2024-MM-DD"
  - Hoverable
  - Auto-updates on data refresh
- **Dependencies:** Refresh pipeline records dates
- **Legal:** Demonstrates due diligence

### F2.7 — "Data not disclosed" honest empty states
- **Priority:** P1
- **Buyer impact:** High (counterintuitive trust signal)
- **Effort:** S (4h)
- **Description:** When franchisor didn't disclose something (e.g., no Item 19), show this prominently instead of hiding it.
- **Specs:**
  - "Item 19 not disclosed by franchisor" message
  - Explanation of what this means
  - Link to methodology page section on disclosure norms
- **Dependencies:** None
- **Legal:** None

### F2.8 — Methodology footnotes throughout
- **Priority:** P3
- **Buyer impact:** Medium
- **Effort:** M (10h)
- **Description:** Small superscript footnotes on jargon or methodology choices that pop tooltips.
- **Specs:**
  - "Median initial fee" → footnote explaining what's included
  - "Industry-typical margin" → footnote explaining where the number comes from
  - Click for full explanation on methodology page
- **Dependencies:** Methodology page exists
- **Legal:** None

### F2.9 — Press / "Cited In" page (stub now, populate later)
- **Priority:** P4
- **Buyer impact:** Medium
- **Effort:** XS (2h initially)
- **Description:** Empty framework page that will list press mentions and citations.
- **Specs:**
  - Logo grid format
  - Link to each article
  - Stub copy: "Recently cited by..." (populate when real citations exist)
- **Dependencies:** Will have content as PR efforts succeed
- **Legal:** None

---

## Category 3: Discovery & Navigation

### F3.1 — Sortable category page tables
- **Priority:** P1
- **Buyer impact:** High
- **Effort:** S (6h)
- **Description:** Current category pages show static table. Add column-sort.
- **Specs:**
  - Click any column header to sort asc/desc
  - Default sort: outlet count desc
  - Persists in URL query param for shareability
  - Works without JS (initial sort) + with JS (interactive)
- **Dependencies:** None
- **Legal:** None

### F3.2 — "For your budget" filter
- **Priority:** P2
- **Buyer impact:** High
- **Effort:** M (8h)
- **Description:** Slider on category pages: "Show franchises I can afford with $X liquid capital."
- **Specs:**
  - Slider: $25k - $1M
  - Filters table to brands where liquid capital required ≤ user's input
  - Updates URL for shareability
  - Highest-engagement filter on most franchise sites
- **Dependencies:** Liquid capital field populated (F1.2)
- **Legal:** None

### F3.3 — Category-level state filter
- **Priority:** P3
- **Buyer impact:** High
- **Effort:** M (8h)
- **Description:** On category pages: "Show me brands with strong [state] presence."
- **Specs:**
  - State dropdown
  - Filters to brands with >5% of outlets in selected state
  - Default to user's detected state (with override)
- **Dependencies:** Per-brand state distribution data (have via Item 20)
- **Legal:** None

### F3.4 — Industry chip navigation in hero
- **Priority:** P0 (have)
- **Buyer impact:** Medium
- **Effort:** Built
- **Description:** Already implemented. 10 clickable category chips in homepage hero.

### F3.5 — Internal search
- **Priority:** P4
- **Buyer impact:** Medium
- **Effort:** M (8h)
- **Description:** Site search bar in header.
- **Specs:**
  - Pagefind (static-friendly, no server) or Algolia (free tier)
  - Search across brand names, categories, FAQ content
  - Show suggestions as user types
- **Dependencies:** Pages exist to index
- **Legal:** None

### F3.6 — Breadcrumb navigation
- **Priority:** P1
- **Buyer impact:** Medium (more for SEO than UX)
- **Effort:** XS (3h)
- **Description:** Trail showing user's location: Home > Home Services > Crumbl.
- **Specs:**
  - Visible on every page below header
  - JSON-LD BreadcrumbList schema
- **Dependencies:** None
- **Legal:** None

### F3.7 — Mobile bottom nav
- **Priority:** P3
- **Buyer impact:** Medium
- **Effort:** M (8h)
- **Description:** Sticky bottom nav on mobile with key sections.
- **Specs:**
  - Browse, Compare, Calculate, Search icons
  - Only visible on mobile (<700px)
  - Highlights current section
- **Dependencies:** Tools exist
- **Legal:** None

---

## Category 4: Interactive Tools

### F4.1 — Interactive breakeven scenario calculator
- **Priority:** P2
- **Buyer impact:** Critical
- **Effort:** L (20h with legal review)
- **Description:** User-input sliders for annual revenue, operating margin, investment. Computes breakeven years live.
- **Specs:**
  - On every brand page (uses brand's disclosed Item 19 averages as defaults)
  - 3 sliders: revenue, margin, investment
  - Live calculation displayed
  - "Show the math" expandable section
  - Heavy disclaimer: "Illustrative scenario, not a projection"
- **Dependencies:** Item 19 data, category margin defaults
- **Legal:** **CRITICAL** — Must be framed as user-driven scenario (NOT declarative forecast) per FTC §436.5(s). Pre-launch franchise attorney review recommended.

### F4.2 — ROI walk-forward chart
- **Priority:** P3
- **Buyer impact:** High
- **Effort:** L (16h)
- **Description:** Year-by-year cumulative profit visualization.
- **Specs:**
  - 10-year time horizon
  - Two bands: P25 conservative, P75 optimistic
  - Crosses $0 line at breakeven point
  - Chart.js or Recharts
- **Dependencies:** Same as breakeven calc
- **Legal:** Same framing requirements as F4.1

### F4.3 — "For your budget" recommendation widget
- **Priority:** P3
- **Buyer impact:** High
- **Effort:** M (10h)
- **Description:** Site-wide tool: "How much can you invest?" → returns 10 matching franchises.
- **Specs:**
  - Available from homepage hero
  - Input: liquid capital amount
  - Output: ranked list of franchises matching budget
  - Each result links to brand page
- **Dependencies:** Liquid capital data
- **Legal:** Avoid "best" or "recommended" framing — use "matches your budget"

### F4.4 — Multi-brand comparison tool
- **Priority:** P3
- **Buyer impact:** High
- **Effort:** L (16h)
- **Description:** Select 2-3 brands from a picker, see side-by-side comparison.
- **Specs:**
  - Brand picker (typeahead)
  - Up to 3 brands at once
  - Comparison table with all key metrics
  - "Compare side-by-side" CTA on every brand page
- **Dependencies:** Brand pages exist
- **Legal:** None

### F4.5 — Per-brand US choropleth map
- **Priority:** P3
- **Buyer impact:** High
- **Effort:** L (16h)
- **Description:** US map below fact box showing outlet density per state for this brand.
- **Specs:**
  - D3 choropleth
  - Color intensity = outlet count
  - Hover for state details
  - Mobile: simplified bar chart fallback
- **Dependencies:** Item 20 state distribution data
- **Legal:** None

### F4.6 — SBA loan estimator widget
- **Priority:** P4
- **Buyer impact:** Medium
- **Effort:** M (10h)
- **Description:** Estimates SBA 7(a) loan eligibility and approximate monthly payment for the franchise investment.
- **Specs:**
  - Input: down payment, credit score range, term length
  - Output: estimated monthly payment, total interest
  - CTA: "Get matched with an SBA lender" (affiliate)
- **Dependencies:** SBA Franchise Directory data (F1.12)
- **Legal:** "Estimate" framing — not financial advice

---

## Category 5: Comparison Pages

### F5.1 — Comparison page generator `/compare/[a]-vs-[b]/`
- **Priority:** P2
- **Buyer impact:** Critical (highest converting page type)
- **Effort:** L (24h)
- **Description:** Auto-generated pages comparing any two brands. Highest SEO + conversion leverage.
- **Specs:**
  - URL: `/compare/crumbl-vs-insomnia-cookies/`
  - Side-by-side comparison table
  - "Which is right for you?" framing (NOT "which is better")
  - 5-10 high-value pairs initially, then 100, then long-tail
  - Linked from both brand pages
  - JSON-LD Article schema
- **Dependencies:** Brand pages exist
- **Legal:** Avoid editorial "winner" framing

### F5.2 — Comparison page FAQ section
- **Priority:** P2
- **Buyer impact:** High
- **Effort:** S (4h)
- **Description:** Each comparison page has its own FAQs: "Is X cheaper than Y?", "Does X have more locations than Y?", etc.
- **Specs:**
  - 4-6 questions per comparison
  - JSON-LD FAQPage schema
  - Auto-generated from comparison data
- **Dependencies:** F5.1
- **Legal:** None

### F5.3 — "Similar but cheaper" recommendations
- **Priority:** P4
- **Buyer impact:** High
- **Effort:** M (10h)
- **Description:** On brand pages: "Similar to [Brand] but with lower investment: [X], [Y], [Z]."
- **Specs:**
  - Same category, lower investment band
  - 3 recommended alternatives
  - Each links to comparison page
- **Dependencies:** Category classification, investment data
- **Legal:** None

---

## Category 6: Conversion Features

### F6.1 — Email capture form (every brand page)
- **Priority:** P0
- **Buyer impact:** High (for future newsletter)
- **Effort:** S (4h)
- **Description:** Capture email tied to lead magnet incentive. Build the list now even though newsletter is Phase 2.
- **Specs:**
  - "Get the FDD Buyer's Checklist (free PDF)" CTA
  - Email-only form
  - Stores in SQLite for now
  - Migrate to Beehiiv when Phase 2 newsletter launches
- **Dependencies:** Lead magnet PDF (F6.5)
- **Legal:** Privacy policy must mention email collection

### F6.2 — Affiliate CTA: "Talk to a franchise consultant"
- **Priority:** P0
- **Buyer impact:** Critical (primary revenue)
- **Effort:** S (4h once approval lands)
- **Description:** Currently `href="#"` placeholder. Wire to real affiliate link.
- **Specs:**
  - Affiliate URL (FlexOffers or Vellko once approved)
  - Visible on every brand page
  - Italic disclosure above
- **Dependencies:** Affiliate approval
- **Legal:** FTC disclosure required (F2.3)

### F6.3 — Affiliate CTA: "Get matched with an SBA lender"
- **Priority:** P1
- **Buyer impact:** High
- **Effort:** S (4h)
- **Description:** Secondary CTA for financing-stage buyers.
- **Specs:**
  - Affiliate URL (Lendio via FlexOffers, ApplePie Capital eventually)
  - Below primary CTA
  - "Get matched with a lender for your $X investment"
- **Dependencies:** Affiliate approval
- **Legal:** FTC disclosure

### F6.4 — Prelaunch form (Tally/Formspree)
- **Priority:** P0 (interim until affiliate approval)
- **Buyer impact:** High
- **Effort:** XS (1h)
- **Description:** Don't leave dead `href="#"` placeholders live. While affiliate apps process, capture leads via Tally form.
- **Specs:**
  - Tally form: name, email, investment budget
  - Replaces affiliate CTA URL during approval window
  - Email manually fulfilled or held until affiliate access lands
- **Dependencies:** None
- **Legal:** Privacy disclosure for email collection

### F6.5 — Lead magnet: "FDD Buyer's Checklist" PDF
- **Priority:** P1
- **Buyer impact:** High
- **Effort:** S (4h content + 2h design)
- **Description:** 4-page PDF: what to look for in an FDD, what red flags mean, what questions to ask current franchisees.
- **Specs:**
  - Branded PDF
  - Genuinely useful (not a sales pitch)
  - Delivered via email after form submission
  - Builds email list
- **Dependencies:** Email capture (F6.1)
- **Legal:** None

### F6.6 — Lead magnet: "Top 50 Franchises Under $200K"
- **Priority:** P2
- **Buyer impact:** High
- **Effort:** M (8h)
- **Description:** PDF report ranking 50 franchises by investment range, with data summaries.
- **Specs:**
  - Branded PDF
  - Built from your data (low marginal cost)
  - Updated quarterly
- **Dependencies:** F6.5 infrastructure
- **Legal:** Use "filtered by investment" not "best" framing

### F6.7 — Sticky CTA on long pages
- **Priority:** P3
- **Buyer impact:** Medium
- **Effort:** S (4h)
- **Description:** As user scrolls past hero, sticky bottom bar appears with primary CTA.
- **Specs:**
  - Mobile only (clutters desktop)
  - Dismissible
  - Same CTA as page primary
- **Dependencies:** None
- **Legal:** Don't qualify as "interstitial" per Google guidelines

### F6.8 — Exit intent capture (cautious implementation)
- **Priority:** P4
- **Buyer impact:** Medium
- **Effort:** S (6h)
- **Description:** When user moves mouse to close tab, offer lead magnet. Use sparingly — annoying if overdone.
- **Specs:**
  - Triggers ONCE per session max
  - Only on brand pages
  - Easy to dismiss
  - Offer is the lead magnet PDF
- **Dependencies:** Lead magnet exists
- **Legal:** None

---

## Category 7: Analytics & Trending Tracking

These features power the trending detection infrastructure for the future Phase 2 newsletter.

### F7.1 — GA4 event tracking
- **Priority:** P0
- **Buyer impact:** Indirect (data quality for product decisions)
- **Effort:** S (6h)
- **Description:** Track key events for funnel analysis.
- **Specs:**
  - Events: page_view, scroll_75_percent, cta_click, outbound_click, lead_form_submit, calculator_use, comparison_view
  - Brand pageview with brand_name custom dimension
  - Category pageview with category custom dimension
- **Dependencies:** GA4 installed
- **Legal:** None (covered by cookie consent)

### F7.2 — Microsoft Clarity heatmaps
- **Priority:** P1
- **Buyer impact:** Indirect (UX improvement input)
- **Effort:** XS (1h)
- **Description:** Free tool — heatmaps + session recordings.
- **Specs:**
  - Install on all pages
  - Review weekly for CRO opportunities
- **Dependencies:** None
- **Legal:** Privacy policy must mention session recording

### F7.3 — Trending detection script
- **Priority:** P2
- **Buyer impact:** Indirect (powers future newsletter)
- **Effort:** M (12h)
- **Description:** Weekly Python script that queries GA4 + GSC APIs and outputs trending brands.
- **Specs:**
  - Top 10 most-viewed brands (7d rolling)
  - Top 10 fastest-growing brands (week-over-week delta)
  - New brands with breakout interest (>100 views in first 7 days)
  - Stores history in SQLite for later newsletter content
- **Dependencies:** GA4 + GSC API access
- **Legal:** None

### F7.4 — Internal "trending now" widget
- **Priority:** P3
- **Buyer impact:** Medium (social proof)
- **Effort:** S (6h)
- **Description:** Homepage widget: "Most researched this week" with top 5 brands.
- **Specs:**
  - Updates weekly from trending detection script
  - Each brand links to its page
  - Don't claim "popular" — just say "most viewed"
- **Dependencies:** F7.3
- **Legal:** Pure traffic data, no editorial claim

### F7.5 — Search Console mining workflow
- **Priority:** P2
- **Buyer impact:** Indirect (drives content prioritization)
- **Effort:** S (4h to document workflow)
- **Description:** Document weekly process for mining GSC for content opportunities.
- **Specs:**
  - Filter queries position 11-30
  - Identify high-impression / low-CTR pages
  - Update those pages with better content
  - Re-check in 4-6 weeks
- **Dependencies:** Search Console setup
- **Legal:** None

---

## Category 8: Accessibility (ADA Compliance)

### F8.1 — Alt text on every image
- **Priority:** P0 (legal requirement)
- **Buyer impact:** Low (but legal)
- **Effort:** S (4h audit)
- **Description:** Every image needs descriptive alt text.
- **Specs:**
  - Audit existing images
  - Add alt text to template generation
  - Decorative images: empty alt=""
- **Dependencies:** None
- **Legal:** ADA Title III

### F8.2 — Keyboard navigation
- **Priority:** P0
- **Buyer impact:** Low (but legal)
- **Effort:** S (4h audit + fixes)
- **Description:** All interactive elements reachable and operable via keyboard.
- **Specs:**
  - Tab through entire page
  - Skip-to-content link at top
  - Focus indicators visible
- **Dependencies:** None
- **Legal:** ADA Title III

### F8.3 — Color contrast WCAG 2.1 AA
- **Priority:** P0
- **Buyer impact:** Low (but legal)
- **Effort:** S (4h audit)
- **Description:** Text must meet 4.5:1 contrast ratio against background.
- **Specs:**
  - Audit color palette
  - Adjust grays that fall short
  - WAVE accessibility checker validation
- **Dependencies:** None
- **Legal:** ADA Title III

### F8.4 — Form labels associated with inputs
- **Priority:** P0
- **Buyer impact:** Low (but legal)
- **Effort:** XS (2h)
- **Description:** Every form input has a label or aria-label.
- **Specs:**
  - `<label for="">` on all inputs
  - Email capture, contact form, lead magnet forms
- **Dependencies:** Forms exist
- **Legal:** ADA Title III

---

## Category 9: Mobile-Specific

### F9.1 — Mobile card layout for tables (have)
- **Priority:** P0 (have)
- **Buyer impact:** High
- **Effort:** Built
- **Description:** Tables transform to cards below 700px.

### F9.2 — Mobile-optimized fact box
- **Priority:** P1
- **Buyer impact:** High
- **Effort:** S (4h)
- **Description:** Fact box on brand pages collapses to expandable accordion on mobile.
- **Specs:**
  - First 4 fields visible
  - "Show all details" expands rest
  - Smooth animation
- **Dependencies:** Fact box exists
- **Legal:** None

### F9.3 — Mobile-friendly calculators
- **Priority:** P2
- **Buyer impact:** High
- **Effort:** M (8h)
- **Description:** Sliders, inputs, charts all work cleanly on touch.
- **Specs:**
  - Large tap targets (44x44px minimum)
  - Number inputs use mobile numeric keyboard
  - Chart fits in viewport
- **Dependencies:** Calculator features
- **Legal:** None

---

## Category 10: Anti-Scraping & Content Protection

**Honest framing first:** A 100%-unscrapable public website is impossible. Anything a browser can render, a headless browser can scrape. The goal of this category is **raise the cost of scraping high enough that most actors give up and most copies are detectable**, not to make extraction impossible.

What we're protecting:
1. **Our normalized data + UX** (the value-add). Raw FDD facts are public; we don't claim ownership over those.
2. **Our extraction taxonomy** (cohort enum names, schema choices, presentation patterns).
3. **The work of our pipeline** (cleaning + categorization), not the underlying records.

### F10.1 — Cloudflare in front of the custom domain
- **Priority:** P0 (immediately when a custom domain is wired)
- **Buyer impact:** Indirect (security + perf)
- **Effort:** S (4h, one-time setup)
- **Description:** Point the custom domain at GitHub Pages via Cloudflare proxy. Free tier provides bot detection, rate limiting, basic DDoS protection, and challenge pages for suspicious traffic. Single largest defense available on a static site.
- **Specs:**
  - CNAME `www.franchisedepth.com` → `josh-max2.github.io` via Cloudflare proxy (orange cloud ON)
  - Enable "Bot Fight Mode" (free tier)
  - Enable "Security Level: Medium" (challenges suspicious IPs)
  - Page Rules: rate limit `/franchise/*` to 30 req/min per IP (catches bulk scrapers)
  - Enable Turnstile on any form submissions (F6.1 email capture)
- **Dependencies:** Custom domain registered
- **Legal:** Cloudflare's ToS — fine for this use case

### F10.2 — robots.txt + scraper directives
- **Priority:** P0
- **Buyer impact:** Low (only honors good actors)
- **Effort:** XS (1h)
- **Description:** Already have a robots.txt. Extend it to explicitly block known AI training crawlers and aggregators while keeping search engines welcome.
- **Specs:**
  - Allow: `Googlebot, Bingbot, DuckDuckBot, ChatGPT-User, OAI-SearchBot, PerplexityBot, ClaudeBot` (search-time AI, NOT training)
  - Disallow: `CCBot (Common Crawl), GPTBot (OpenAI training), Google-Extended (Google AI training), anthropic-ai (Claude training), facebookexternalhit/Meta-ExternalAgent, Bytespider (TikTok), Amazonbot, Applebot-Extended` (these crawl for training-data scraping)
  - Disallow: `/sitemap.xml` itself is NOT blocked (search engines need it)
  - Add `Crawl-delay: 10` for any User-agent (slows down legitimate crawlers but stops fast scrapers)
- **Dependencies:** None
- **Legal:** robots.txt has no legal force but establishes the site's stated wishes — useful for DMCA / cease-and-desist later

### F10.3 — Terms of Service prohibiting automated extraction
- **Priority:** P0
- **Buyer impact:** Low (legal cover)
- **Effort:** XS (folded into F2.5 Privacy + ToS)
- **Description:** Explicit clause in ToS prohibiting scraping, bulk download, automated extraction, and use for AI training. Combined with hCaptcha/Turnstile on access, this enabled successful lawsuits against scrapers (LinkedIn v. hiQ, Meta v. Bright Data).
- **Specs:**
  - Clause: "You may not use any automated means (bots, scrapers, crawlers, etc.) to access, copy, harvest, scrape, or extract any data from this site, except for: (a) major search engine crawlers operating in good faith, (b) the user's own personal-use browser. Bulk downloads or republication require written permission."
  - Clause: "Use of this site's content for training machine learning models is expressly prohibited."
- **Dependencies:** F2.5 (covers this)
- **Legal:** Strengthens DMCA + tortious-interference claims

### F10.4 — Honeypot fingerprint links
- **Priority:** P1
- **Buyer impact:** None
- **Effort:** XS (2h)
- **Description:** Hidden links visible only to crawlers. Any IP that hits them is auto-blocked by Cloudflare. Cheap and effective against naive scrapers.
- **Specs:**
  - Add `<a href="/__honeypot/trap-pots-a7b2k.html" style="display:none" aria-hidden="true" tabindex="-1">.</a>` in the base template
  - Cloudflare Worker (free tier): IPs that hit `/__honeypot/*` get added to firewall block list for 24h
  - Real users will never see or follow this link; crawlers indexing all links will
- **Dependencies:** F10.1 (Cloudflare)
- **Legal:** None — we're not impersonating anyone

### F10.5 — Hidden watermarks for copy detection
- **Priority:** P2
- **Buyer impact:** None (detection only)
- **Effort:** S (4h)
- **Description:** Inject unique, low-visibility identifiers into every page so scraped copies are detectable via Google search later.
- **Specs:**
  - HTML comment with a per-page hash: `<!-- fd-fingerprint:{sha8_of_brand_slug} -->`
  - Microscopic invisible zero-width characters in the brand name (`<span aria-hidden>&zwj;&zwnj;</span>`) — varies per brand
  - Periodic Google search for `"site:any-domain rare-distinctive-phrase-we-coined"` to find copies
  - When copies are found: DMCA takedown to host + Google
- **Dependencies:** None
- **Legal:** Watermarking is legal; DMCA process documented

### F10.6 — JS-rendered Item 19 tables (controversial)
- **Priority:** P3 (NOT recommended unless seeing real scraping problems)
- **Buyer impact:** Negative (hurts SEO, AEO, accessibility)
- **Effort:** M (10h)
- **Description:** Render Item 19 tables via JavaScript instead of static HTML. Defeats `curl`/`wget` and basic scrapers, but Playwright still extracts. Also hurts Google indexing and AI engines that can't run JS.
- **Specs:**
  - Store Item 19 data as a JSON blob in `<script type="application/json">`
  - Hydrate table client-side
- **Dependencies:** None
- **Legal:** None
- **TRADEOFF NOTE:** This actively harms our SEO + AEO goals. Only consider if scraping is causing concrete revenue damage. Probably never the right call for this project.

### F10.7 — Image-based pricing displays (NOT recommended)
- **Priority:** P5
- **Buyer impact:** Strongly negative
- **Effort:** M
- **Description:** Render dollar amounts as inline images so simple text scrapers can't extract them. Used by real estate aggregators.
- **TRADEOFF NOTE:** Catastrophic for accessibility (screen readers fail), SEO (no text), AEO (AI engines can't cite), and UX. **Do not implement.** Included only to document that we considered and rejected it.

### F10.8 — API rate limits + Cloudflare bot scoring
- **Priority:** P2
- **Buyer impact:** Low
- **Effort:** S (4h)
- **Description:** When/if we add an API (no current plans), apply per-IP rate limits and Cloudflare bot scoring at the edge.
- **Specs:**
  - 60 req/min anonymous; require API key for higher
  - Block requests with bot score >30 (Cloudflare's heuristic)
- **Dependencies:** F10.1, an actual API
- **Legal:** None

### Anti-scraping summary

**Realistic protection stack:**
1. Custom domain → **Cloudflare proxy** (F10.1) → GitHub Pages — single biggest win
2. **robots.txt** blocking training crawlers (F10.2)
3. **ToS clause** prohibiting scraping (F10.3) — legal cover
4. **Honeypot links** auto-blocking obvious scrapers (F10.4)
5. **Watermarks** for detecting + DMCA'ing copies (F10.5)

**What this stack stops:** drive-by `curl`/`wget` scripts, naive Python `requests`/`BeautifulSoup` scrapers, AI training crawlers (CCBot, GPTBot, etc.), bulk-download attempts (rate-limited).

**What it doesn't stop:** a determined competitor running headless Playwright through residential proxies. That's industry-wide unsolvable on a public site. For that, the defense is data freshness (we update more often than they can re-scrape) + value-add UX (they copy data but not the product).

---

## Master Feature List by Priority

### P0 (Launch blockers) — must be live before custom domain points to site

| ID | Feature | Effort | Hours | Status |
|----|---------|--------|-------|--------|
| F1.1 | Opening summary paragraph | S | 4 | ✅ Built (80-120w, adaptive per brand) |
| F1.2 | Fact box / quick stats | S | 2 | ✅ Built (incl. liquid capital + closure rate) |
| F1.3 | Item 19 table | — | 0 | ✅ Built |
| F1.5 | FAQ section | M | 12 | ✅ Built (5-7 per brand, JSON-LD FAQPage) |
| F1.7 | Date stamp | XS | 0 | ✅ Built (verified-from + source-verified + page-regenerated) |
| F1.8 | Author byline | XS | 2 | ✅ Built (every brand + compare page, JSON-LD author) |
| F1.9 | Source links | S | 0 | ✅ Built (page-N PDF links) |
| F1.10 | Related brands | — | 0 | ✅ Built |
| F2.1 | Methodology page | L | 10 | ✅ Built (2045 words, 11 sections, data dictionary + update log) |
| F2.2 | About page | M | 10 | ✅ Built (1040 words, BYU Econ + RevOps credentials) — no real photo yet |
| F2.3 | FTC affiliate disclosure | XS | 2 | ✅ Built (footer + per-CTA italic + standalone page) |
| F2.4 | Cookie consent | XS | 2 | ✅ Built (self-hosted Klaro-style, GDPR + CCPA) |
| F2.5 | Privacy policy + ToS | S | 4 | ✅ Built (self-authored: 715 + 1022 words, Terms §7 has anti-scrape clause) |
| F3.4 | Industry chips | — | 0 | ✅ Built |
| F6.1 | Email capture form | S | 4 | 🟡 Form code shipped on brand + lead-magnet pages; gated by `FORMSPREE_ID` env var (currently placeholder, hidden). Mailto fallback on /get-the-checklist/ |
| F6.2 | Affiliate CTA (when approved) | S | 4 | 🟡 Placeholders live (href="#") on every brand page; awaiting affiliate approval |
| F6.4 | Prelaunch Tally form (interim) | XS | 1 | 🟡 Built as Formspree path (not Tally); needs `FORMSPREE_ID` env var |
| F7.1 | GA4 events | S | 6 | 🟡 Wrapper shipped (`_ga4.js`, consent-gated, tracks scroll_75/cta_click/outbound_click/lead_form_submit). Needs `FD_GA4_ID` env var |
| F8.1 | Alt text audit | S | 4 | ✅ Built (audit passing across 76 pages) |
| F8.2 | Keyboard navigation | S | 4 | ✅ Built (skip-to-content, focus-visible) |
| F8.3 | Color contrast WCAG 2.1 AA | S | 4 | ✅ Built (#94a3b8 → #64748b for muted text) |
| F8.4 | Form labels | XS | 2 | ✅ Built (audit passing) |
| F9.1 | Mobile cards | — | 0 | ✅ Built |
| **NEW** | Open Graph + Twitter meta tags | XS | 2 | ✅ Built |
| **NEW** | Favicon + apple-touch-icon | XS | 1 | ✅ Built (Pillow-generated set: 16/32/180/.ico) |
| **NEW** | 404 page | XS | 2 | ✅ Built (live brand-name search via embedded JSON index) |
| **NEW** | Social share image (OG image) | XS | 2 | ✅ Built (1200×630 PNG, Pillow-generated) |
| **NEW** | Risk badge compliance review (see Already-Shipped table) | XS | 2 | ✅ Resolved (reframed as "Closure rate: X%" with arithmetic explanation) |
| **NEW** | Breakeven disclaimer review (see Already-Shipped table) | XS | 2 | ✅ Resolved (reframed as "Arithmetic scenario", "Not a projection", §436.5(s) link) |
| F10.1 | Cloudflare in front of custom domain | S | 4 | ⛔ Blocked by custom-domain decision |
| F10.2 | robots.txt scraper directives | XS | 1 | ✅ Built (28 AI training/scraping bots blocked, parser-verified) |
| F10.3 | ToS anti-scraping clause | XS | folded into F2.5 | ✅ Built (Terms §7) |
| F10.4 | Honeypot fingerprint links | XS | 2 | ⛔ Blocked by F10.1 (needs Cloudflare to enforce IP block) |

**Status as of 2026-05-17:** 26 of 32 P0 items ✅ built. 4 items 🟡 partial (gated by external accounts: Formspree ID, GA4 measurement ID, affiliate approvals). 2 items ⛔ blocked by custom-domain + Cloudflare setup (F10.1 + F10.4).

**Remaining engineering work for P0:** ~6 hours total (F10.1 Cloudflare config + F10.4 honeypot), gated on the custom domain being wired up. The site can ship to GitHub Pages today; revenue features turn on as external accounts approve.

### P1 (Critical — within 2 weeks of launch)

| ID | Feature | Effort | Status |
|----|---------|--------|--------|
| F1.4 | Outlet growth sparkline | M | ✅ Built (inline SVG sparkline + trajectory text + delta indicator above the bar chart on every brand page; e.g., "139 outlets in 2022 → 140 in 2024 ▲ 0.7%") |
| F1.6 | Industry context paragraph | S | ✅ Built (names siblings + investment-band comparison; returns empty for singletons) |
| F2.6 | Last verified timestamps | S | ✅ Built (per-section vintage line + byline source-verified date) |
| F2.7 | "Not disclosed" empty states | S | ✅ Built throughout (Item 19, liquid capital, fees, item20) |
| F3.1 | Sortable category tables | S | ✅ Built (click-to-sort with ▲/▼ indicators, text/num/bool typed) |
| F3.6 | Breadcrumb navigation | XS | ✅ Built (43 pages, JSON-LD BreadcrumbList, parser-validated) |
| F6.3 | SBA lender CTA | S | 🟡 Placeholder href="#" live; awaiting affiliate approval |
| F6.5 | Lead magnet PDF | S | 🟡 Landing page shipped (/get-the-checklist/); **PDF itself not authored** |
| F7.2 | Microsoft Clarity | XS | ⛔ Not installed |
| F9.2 | Mobile fact box | S | ✅ Built (mobile <700px collapses fact box to first 4; "Show all details"/"Show fewer" toggle; only injected when brand has >4 facts; desktop unchanged; aria-expanded wired) |

**Status:** 6 of 10 P1 items ✅ built. 2 🟡 partial (lead magnet needs PDF authored; SBA CTA needs affiliate URL). 2 ⛔ open (Clarity install + mobile fact-box accordion).

### P2 (High value — month 1-2)

| ID | Feature | Effort | Status |
|----|---------|--------|--------|
| F1.12 | SBA loan eligibility | M | ⛔ **Spec outdated.** The SBA Franchise Directory was discontinued in 2023. SBA 7(a) franchise eligibility is now determined per-lender, per-deal, based on whether the franchisor's FDD meets SBA's affiliation/control criteria (SOP 50 10 7.1, Section A, Chapter 2). No central directory to cross-reference. **Revised plan:** add a per-brand "SBA 7(a) financing eligibility" note that explains the process generically rather than claiming brand-specific eligibility we can't verify. Or skip in favor of higher-value items. |
| F3.2 | "For your budget" filter | M | ✅ Built (slider on category pages, filters by total_investment_low ≤ budget, URL `?budget=N` for shareability, no-inv-data brands always shown, reset button) |
| F4.1 | Interactive breakeven calculator | L | 🟡 **Static** scenario shipped instead (with histogram chart). Interactive sliders not built; pre-launch attorney review still required for either form |
| F5.1 | Comparison page generator | L | ✅ Built (31 pages, all in-category pairs, Article + Breadcrumb schema, cross-links from brand pages) |
| F5.2 | Comparison FAQs | S | ✅ Built (5-6 data-driven FAQs per pair: fee delta, royalty, outlets, Item 19 asymmetry, freshness; JSON-LD FAQPage) |
| F6.6 | Lead magnet PDF #2 ("Top 50 Under $200K") | M | ⛔ Not built |
| F7.3 | Trending detection script | M | ⛔ Not built (depends on GA4 data flow) |
| F7.5 | GSC mining workflow doc | S | ⛔ Not documented |
| F9.3 | Mobile calculators | M | n/a (no interactive calculators built yet) |
| F10.5 | Watermarks for copy detection | S | ⛔ Not built |
| F10.8 | API rate limits (if API ships) | S | n/a (no API ships) |

**Status:** 1 of 11 P2 items ✅ built (F5.1). 1 🟡 partial (F4.1 declarative form shipped). 6 ⛔ open. 2 n/a.

### P3 (Strong improvement — month 2-3)

| ID | Feature | Effort |
|----|---------|--------|
| F1.11 | Brand timeline | M |
| F1.13 | Veteran program indicator | S |
| F1.14 | "Accepting applications" status | M |
| F2.8 | Methodology footnotes | M |
| F3.3 | Category-level state filter | M |
| F3.7 | Mobile bottom nav | M |
| F4.2 | ROI walk-forward chart | L | ✅ Built (10-year cumulative profit Chart.js line on every brand page with disclosed breakeven; two lines optimistic + conservative; crosses zero at breakeven year; same FTC §436.5(s) framing as static breakeven scenario)
| F4.3 | Budget recommendation widget | M |
| F4.4 | Multi-brand comparison tool | L |
| F4.5 | Per-brand US choropleth | L |
| F6.7 | Sticky CTA on long pages | S |
| F7.4 | "Trending now" widget | S |
| F10.6 | JS-rendered Item 19 (NOT recommended — see body) | M |

**Total P3 build time:** ~85 hours (includes F10.6 contingency)

### P4 (Polish — month 3-6)

| ID | Feature | Effort | Status |
|----|---------|--------|--------|
| F2.9 | Press / Cited In page | XS | ✅ Built (/press/ stub with citation guidance + WebPage schema) |
| F3.5 | Internal search | M | ✅ Built (global header search bar on every page, typeahead by brand name + industry, click/Enter navigates, Escape closes; SearchAction wired into homepage WebSite schema with `?q=` URL param) |
| F4.6 | SBA loan estimator | M | ⛔ Not built |
| F5.3 | "Similar but cheaper" recs | M | ✅ Built (on brand pages, surfaces up to 3 same-category brands with lower total_investment_low, sorted ascending) |
| F6.8 | Exit intent capture | S | ⛔ Not built |

**Total P4 build time:** ~30 hours

### P5 (Future / experimental)

Reserved for features that emerge from user feedback or analytics. Examples:
- User accounts / save franchises (requires auth infrastructure)
- Print/PDF export of brand summary
- Glossary tooltips on every jargon term
- Brand parent company hierarchy navigation
- Notable franchisees data
- Multi-language Spanish support
- API for institutional buyers
- White-label widget for partner sites

---

## Build Sequence Recommendation

**Updated 2026-05-17 — sequence collapsed into a single intensive session.** The original week-by-week plan assumed ~10h/week solo cadence; actual execution shipped weeks 1-7 worth of work in one session. What remains below is what's actually left.

### ✅ Done (originally Weeks 1-7)
Foundation P0 (methodology, about, FAQ, summary paragraph) · Compliance + trust P0 (FTC disclosure, cookie consent, privacy + ToS, accessibility audit, risk-badge reframe, breakeven reframe) · Conversion infrastructure (email capture form, Formspree wiring, GA4 events, OG/social/favicon/404) · P1 batch (sortable tables, breadcrumbs, "not disclosed" empty states, last-verified timestamps, industry context paragraphs) · F5.1 comparison page generator (advanced from P2)

### 🟡 Gated on external accounts (no code work needed)
- Set `FORMSPREE_ID` env var → unblocks F6.1 + F6.4 (live lead capture on every brand page)
- Set `FD_GA4_ID` env var → unblocks F7.1 (event tracking flows)
- Affiliate approvals (FlexOffers / IFPG / ApplePie / Boefly) → unblock F6.2 + F6.3 (replace placeholder href="#")
- Custom domain + DNS → unblocks F10.1 Cloudflare → unblocks F10.4 honeypot
- Submit sitemap to GSC + Bing once domain wired

### ⛔ Genuine remaining engineering work
| Priority | Item | Effort | Notes |
|---|---|---|---|
| P1 | F6.5 PDF author the FDD Buyer's Checklist (4 pages) | 4h content | Landing page exists; PDF is the missing piece |
| P1 | F7.2 Microsoft Clarity install | 1h | Free, drop-in script tag |
| P1 | F9.2 Mobile fact-box accordion | 4h | Collapse to first-4-fields + "show all" on <700px |
| P2 | F4.1 Interactive breakeven calculator | 20h + attorney review | Promote static scenario to slider-based; pre-launch attorney sign-off recommended |
| P2 | F5.2 Compare page FAQs | 4h | 4-6 questions per pair, JSON-LD FAQPage |
| P2 | F1.12 SBA loan eligibility | 8h | Cross-reference SBA Franchise Directory |
| P2 | F7.3 Trending detection script | 12h | Wait for ~2-3mo of GA4 data first |
| P3+ | Pillar pages / topic clusters (methodology v2 Pillar 3) | M-L | "Franchise Investment Guide" pillar + cluster pages |
| Scale | Run scrape_loop + extract_loop | 0 dev | Pipeline ready — owner "go" to start |

**Avoid the temptation to build P3+ features before completing the gated/remaining items above.** Compliance, trust signals, conversion infra, and the data scrape compound; polish doesn't.

---

## Legal Considerations Summary

Features requiring legal review or special handling:

| Feature | Concern | Action |
|---------|---------|--------|
| F4.1 Breakeven calculator | FTC §436.5(s) FPR | Interactive scenario framing, $2-5k attorney review pre-launch |
| F4.2 ROI walk-forward | FTC §436.5(s) FPR | Same as F4.1 |
| F4.6 SBA loan estimator | Avoid "financial advice" framing | "Estimate" language, disclaimer |
| F2.3 FTC affiliate disclosure | 16 CFR Part 255 | Required on every page |
| F2.4 Cookie consent | GDPR + CCPA | Required for EU/CA visitors |
| F2.5 Privacy + ToS | General requirement | Use Termly/Iubenda generator |
| F8.1-F8.4 Accessibility | ADA Title III | Required, lawsuit risk increasing |
| F6.1 Email capture | Privacy disclosure | Mention in privacy policy |
| F1.14 "Accepting applications" status | Avoid making claims | Frame as "based on public info" |
| F5.3 "Similar but cheaper" | Avoid editorial framing | Pure data-driven, no rankings |
| F10.3 ToS anti-scraping clause | CFAA enforcement basis | Explicit prohibition strengthens scraper lawsuits |
| F10.5 Watermark detection | DMCA process | Document takedown procedure |

---

## Document Maintenance

**Update this document when:**
- Feature priority changes based on traffic data
- New feature requested or discovered
- Legal/compliance requirement changes
- Feature completed (mark with date)

**Quarterly review:** Re-score priorities based on what's actually moving traffic/conversions.

**Last review:** 2026-05-17
**Next review:** 2026-08-17
