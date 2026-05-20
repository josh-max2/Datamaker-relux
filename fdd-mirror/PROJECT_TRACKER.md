# FranchiseDepth — Master Project Tracker

**Last updated:** 2026-05-18 (F4.7 v2 calculator upgrades shipped — quartile presets, percentile context, breakdown, industry callouts, share URL)
**Status:** Site live at https://franchisedepth.com · 123 brands · 794 pages · per-brand calculator now uses Item 19 distribution + industry peer medians
**Owner:** Josh

> Single source of truth across methodology, features, launch tasks, and operations.
> Legend: ✅ done · 🟡 partial / in flight · ⛔ blocked / not started · 📋 reference only · ⏳ owner-action pending
> For deep detail on any item, see the source trackers: `franchisedepth_methodology_v2.md`, `franchisedepth_features_roadmap.md`.

---

## 0. Live status snapshot

| Metric | Current | Target | Notes |
|---|---|---|---|
| **Live site URL** | https://franchisedepth.com | — | HTTPS active; redirect to HTTPS pending (Pages setting) |
| **Brands in DB** | 461 | 500 | +338 from baseline 123. **Phase 4 strategy: brand expansion harvested via MN long-tail (+75 net) — now near 500 cap** |
| **Phase 4 quality block (§16)** | 8/16 done | 16/16 | Done: worst-performer callout, royalty flag, robots.txt AI bots, fdd_age_badge helper, Item 19 thin-disclosure audit, FDD age sweep, **Item 19 chart fix (Tier 1.1 — chart suppressed for affiliate-only kinds, adaptive label, warning banner)**, **misleading "cohort × metric" label fixed**. Pending: calculator sanity, TL;DR card, sticky tabs, byline, waitlist, /pricing/, /best-of/ pages |
| **HTML pages on site** | ~9500 | — | 386 brand pages + compare/state/category/leaderboard/guide; grows with each ingest |
| **Pillar guides shipped** | 8 | 30-50 | Pillar 3 progress |
| **State pages** | 51 | 50 | target met |
| **Compare pages (static, per-pair)** | 275 | grows N²/2 with brands | auto-generated; in-category only |
| **Compare pages (interactive tool, v2)** | 1 | — | F4.4 ✅ — 11 comparison rows, closure-rate badge, shareable URLs via `?brands=…` |
| **Per-brand US state heatmap** | 85/95+ | — | inline SVG tile grid, quintile color, on every brand with ≥3 US states |
| **Homepage filter toggles** | All / Item 19 / Missing info | — | 67 brands with Item 19, 7 missing main info |
| **FDD Buyer's Checklist PDF** | ✅ shipped | — | 10 pages, 178KB, at `/lead-magnets/fdd-buyers-checklist.pdf` |
| **Sitemap submitted to GSC** | ✅ | — | **791 pages discovered**, status Success |
| **IndexNow** | ✅ | — | 790 URLs submitted (Bing/Yandex/Seznam/Naver) |
| **Item 19 records in DB** | 5,448 | — | across 316 disclosed-Item-19 brands |
| **Item 20 location rows** | 43,575 | — | per-state outlet data; powers heatmaps |
| **Audit issues** | 0 tier-1 | 0 | clean; 18 tier-2 warnings (outlet sum mismatches, affiliate-only disclosures) |
| **Internal dashboard** | live | — | /dashboard/ — KPIs, coverage gauges, industry dist, top performers; noindex |
| **Cost per FDD (v2 avg)** | ~$0.17 | <$0.25 | target beaten |
| **Cost per FDD (v1 fallback, Haiku)** | ~$0.23-0.30 | <$0.50 | Haiku-mode |
| **API-equiv $ for +90 brands** | ~$25-30 | — | $0 actual on Max plan |

---

## 1. Domain, hosting, and DNS

### 1.1 Domain registration (Porkbun)

| Item | Status | Next step |
|---|---|---|
| Domain `franchisedepth.com` purchased | ✅ | — |
| 2-year registration | ✅ | — |
| Auto-renew | ⏳ | Verify enabled in Porkbun |
| Domain lock | ⏳ | Verify enabled in Porkbun |
| WHOIS privacy | ⏳ | Verify enabled in Porkbun |

### 1.2 DNS records (9 active in Porkbun)

| Record | Status |
|---|---|
| 4× A records → GitHub Pages IPs (185.199.108-111.153) | ✅ |
| CNAME `www` → josh-max2.github.io | ✅ |
| 2× MX records (Porkbun forwarding) | ✅ |
| TXT SPF record | ✅ |
| TXT google-site-verification | ✅ |

### 1.3 Email forwarding (Porkbun, free)

| Item | Status | Next step |
|---|---|---|
| `hi@franchisedepth.com` | ⏳ | Configure forwarding to personal inbox |
| `hello@franchisedepth.com` | ⏳ | Same (referenced in privacy + contact) |
| `support@franchisedepth.com` | ⏳ | Optional |

### 1.4 GitHub Pages hosting

| Item | Status | Next step |
|---|---|---|
| Repo `github.com/josh-max2/Parser` | ✅ | — |
| Pages serving from `/docs` on `main` | ✅ | — |
| Custom domain set in Settings → Pages | ✅ | — |
| DNS check | ✅ Successful | — |
| HTTPS cert active | ✅ | — |
| **Enforce HTTPS** | ⏳ | Tick checkbox in Settings → Pages (forces http→https redirect) |
| `SITE_PREFIX = ""` (root URLs, no /Parser/) | ✅ | — |
| CNAME auto-emission in site_gen.py | ✅ | — |
| Sitemap.xml absolute URLs | ✅ | — |
| All canonical/og URLs absolute | ✅ | — |

---

## 2. Analytics, tracking, and forms

### 2.1 Google Analytics 4

| Item | Status |
|---|---|
| Property created | ✅ |
| Measurement ID `G-ZEPEB3Z67R` | ✅ |
| Consent-gated `_ga4.js` wrapper | ✅ |
| Custom events: scroll_75, cta_click, outbound_click, lead_form_submit | ✅ |
| **Real-time verification after deploy** | ⏳ — visit https://franchisedepth.com/, click "Accept all", check GA4 realtime |

### 2.2 Microsoft Clarity

| Item | Status |
|---|---|
| Project created | ✅ |
| Project ID `wspuk90u8d` | ✅ |
| Consent-gated `_clarity.js` wrapper | ✅ |
| Privacy policy updated to disclose session recording + 13-month retention | ✅ |
| Text inputs auto-masked | ✅ |
| Linked from Bing Webmaster Tools | 🟡 — initiated, pending verification |

### 2.3 Formspree (lead capture backend)

| Item | Status |
|---|---|
| Account created | ✅ |
| Form ID `xjgzvgrz` | ✅ |
| **4 forms live across site** | ✅ — brand page emails, footer signup, contact, /get-the-checklist/ |
| Honeypot anti-spam | ✅ on all forms |
| Hidden `source=*` for dashboard filtering | ✅ |
| **Test submission post-deploy** | ⏳ — submit test form, confirm email arrives |
| Notification email destination | ⏳ — set to hi@franchisedepth.com once Porkbun forwarding live |

---

## 3. Search engines + verification

### 3.1 Google Search Console

| Item | Status |
|---|---|
| Domain property added | ✅ |
| DNS TXT verification | ✅ Verified |
| HTML meta tag (alternate) | ✅ deployed (`K4jBh7vFO-rr4gxM9JotDwBeAtCWdXOm7bEwSMsfv3I`) |
| **Submit sitemap.xml** | ✅ — submitted 2026-05-17, status Success, 791 pages discovered |
| Email alerts | ⏳ — Settings → Users → enable preferences |
| International Targeting (US) | ⏳ — Legacy Tools |

### 3.2 Bing Webmaster Tools

| Item | Status |
|---|---|
| Property added | ✅ |
| Verification | ✅ via GSC import (auto-verified) |
| **IndexNow integration** | ✅ live (key file emitted, submission script built) |
| First IndexNow submission | ✅ 140 URLs accepted (HTTP 202) |
| `msvalidate.01` meta-tag scaffolding | ✅ ready (drop in `FD_BING_VERIFICATION` env var if WMT prefers) |
| Microsoft Clarity link | 🟡 — initiated |
| Notifications enabled | ⏳ |
| Site Scan run | ⏳ — after launch stabilizes |

### 3.3 Verification meta tags deployed

| Network / tool | Token | Status |
|---|---|---|
| Google Search Console | `K4jBh7vFO-rr4gxM9JotDwBeAtCWdXOm7bEwSMsfv3I` | ✅ live in `<head>` |
| FlexOffers | `7eb2e7cf-9f84-459a-b48f-64cf7a609967` | ✅ live (`fo-verify`) |
| Impact | `83778c12-e712-4dd7-9e77-9ffb6329f776` | ✅ live (`impact-site-verification`) |
| IndexNow | `108a9bb5a8ed4718a9ff03218f2899f6` | ✅ key file at `/{key}.txt` |
| Bing Webmaster | — | scaffolded only (`msvalidate.01`) |

### 3.4 Discoverability files

| File | Status |
|---|---|
| `robots.txt` | ✅ blocks 23 training crawlers; **allows 6 AI citation/search crawlers** (ChatGPT-User, OAI-SearchBot, PerplexityBot, Perplexity-User, Applebot-Extended, Meta-ExternalFetcher) for AI-citation traffic |
| `sitemap.xml` | ✅ 167+ URLs, absolute, with `<lastmod>` |
| `llms.txt` | ✅ |
| `llms-full.txt` | ✅ includes data dictionary |
| `CNAME` | ✅ persisted across regens |

---

## 4. Site content

### 4.1 Page inventory

| Type | Count | Status |
|---|---|---|
| Homepage | 1 | ✅ Organization + WebSite + SearchAction schema |
| Brand pages | 60 | ✅ growing; Article + Product + FAQPage + Breadcrumb schema |
| Category pages | 11 | ✅ CollectionPage + ItemList schema |
| Compare pages (static, 1-on-1 per pair) | 172 | ✅ all in-category pairs (post-classifier fix); Article + FAQPage + Breadcrumb |
| **/compare/** (interactive tool, F4.4 v2) | 1 | ✅ — typeahead picker for 2-3 brands; 11 rows (industry, source FDD, fee, royalty, marketing fund, monthly tech fee, total investment, liquid capital, total outlets, closure-rate badge w/ tier color, Item 19 disclosed); shareable `?brands=slug1,slug2,slug3` URL + Copy share link button; auto-redirects to static page when 2 same-category brands picked |
| **/highest-reported-earnings/** (per category) | 4 | ✅ ranked by reported Item 19, compliance-safe framing |
| State pages | 51 | ✅ one per state with disclosed outlets |
| **/industries/** hub | 1 | ✅ category index |
| **/recent/** | 1 | ✅ newest FDDs by issuance date |
| **/guides/** hub | 1 | ✅ |
| Guide pages | 8 | ✅ (see 4.2) |
| /contact/ | 1 | ✅ ContactPage schema |
| /press/ | 1 | ✅ stub |
| /about/ | 1 | ✅ 1040w, BYU + RevOps credentials |
| /methodology/ | 1 | ✅ 2045w, 11 sections, data dictionary, glossary, update log |
| /privacy/ | 1 | ✅ 715w, GDPR + CCPA |
| /terms/ | 1 | ✅ 1022w, includes anti-scrape clause §7 |
| /affiliate-disclosure/ | 1 | ✅ FTC §255 compliant |
| /get-the-checklist/ | 1 | 🟡 landing page live, PDF not authored yet |
| 404 page | 1 | ✅ with live brand search |

### 4.2 Pillar guide cluster (Pillar 3 cluster architecture)

| Guide | Words | Status | Next |
|---|---|---|---|
| Understanding FDD Item 7 | ~1700 | ✅ | — |
| Understanding FDD Item 19 | ~1900 | ✅ | — |
| Understanding FDD Item 20 | ~2200 | ✅ | — |
| Validating franchisee earnings | ~2000 | ✅ | — |
| How long to break even | ~2000 | ✅ | — |
| SBA 7(a) franchise financing | ~2200 | ✅ | — |
| What's negotiable in a franchise agreement | ~2400 | ✅ | — |
| Evaluating discovery day | ~2700 | ✅ | — |
| (more guides queued — target 30-50 total) | — | ⛔ | choose topic + author |

### 4.3 Brand-page features (per-brand)

| Feature | Status |
|---|---|
| F1.1 Opening summary paragraph (80-120w, bold key numbers) | ✅ |
| F1.2 Fact box / quick stats | ✅ |
| F1.3 Item 19 financial performance table | ✅ |
| F1.4 Outlet sparkline (inline SVG above bar chart) | ✅ |
| F1.5 FAQ section (5-7 Q&A, JSON-LD FAQPage) | ✅ |
| F1.6 Industry context paragraph | ✅ |
| F1.7 Date stamp + freshness | ✅ |
| F1.8 Author byline | ✅ |
| F1.9 Source links on every Item 19 number | ✅ |
| F1.10 Related brands grid | ✅ |
| F1.11 Brand timeline / "About this franchise" | ⛔ requires Item 1 extraction |
| F1.12 SBA loan eligibility badge | ⛔ spec outdated (SBA Directory discontinued 2023); see §11 |
| F1.13 Veteran program / discount indicator | ⛔ needs VetFran directory scrape |
| F1.14 "Accepting applications" status | ⛔ manual research |
| F2.6 Per-section data-vintage line ("Source verified") | ✅ |
| F2.7 "Not disclosed" honest empty states | ✅ |
| F4.2 ROI walk-forward chart (10-yr cumulative) | ✅ |
| **F4.7 Interactive cost calculator (simple/advanced modes + chart)** | ✅ pre-filled with brand-specific FDD defaults; chart updates live; affiliate CTA + full disclaimer block (FTC §436.5(s), 16 CFR 255, no-warranty, no-advice) |
| **F4.7v2 Calculator: quartile presets + percentile context + breakdown + industry callouts + share URL** | ✅ Pessimistic/Median/Optimistic preset buttons (P25/P50/P75 from Item 19 distribution); live percentile-rank context for revenue input ("Your $X is at the Yth percentile of {brand} franchisees"); itemized Y1 money-flow breakdown table; industry-benchmark callouts (royalty/marketing/investment vs same-industry peer medians); similar-brand cross-links (top 4 industry peers); shareable URL via query-string state sync |
| F4.8 Top-of-page anchor nav (TOC chips) | ✅ Summary / Fast facts / Breakeven / Calculator / Fees / Item 19 / Outlets / States / FAQ / Sources |
| F4.5 D3 US choropleth | ⛔ deferred — bar chart serves |
| F4.11 Jargon tooltips → methodology glossary | ✅ |
| F5.3 "Similar but cheaper" recommendations | ✅ |
| F9.2 Mobile fact-box accordion | ✅ |
| F10.5 Watermark fingerprint comment | ✅ |
| Compare-with peer links | ✅ |

### 4.4 Site-wide features

| Feature | Status |
|---|---|
| F3.1 Sortable category tables | ✅ + same pattern on state/recent/earnings pages |
| F3.2 "For your budget" filter (category pages) | ✅ |
| F3.3 Homepage filter toggles (All / Item 19 only / Missing main info) | ✅ — 3-state segmented control, combined with search + budget slider |
| F3.4 Industry chip navigation (homepage hero) | ✅ |
| F3.5 Global header search bar + typeahead | ✅ |
| F3.6 Breadcrumb navigation + JSON-LD | ✅ on 140+ pages |
| F4.3 Homepage "what can you invest" budget widget | ✅ |
| F4.6 Per-brand US state outlet heatmap (tile grid) | ✅ — 85/95 brand pages, 51-tile SVG, quintile color |
| F5.1 Comparison page generator (`/compare/X-vs-Y/`) | ✅ |
| F5.2 Comparison page FAQs | ✅ 5-6 Q&A per pair |
| F7.1 GA4 events configured | ✅ |
| F7.2 Microsoft Clarity | ✅ |
| F8.1-F8.4 Accessibility (alt text, keyboard nav, WCAG AA, form labels) | ✅ audit clean |
| Single primary CTA per page template | ✅ |
| Footer newsletter signup (Formspree-gated) | ✅ |
| Footer FTC disclosure | ✅ |
| Open Graph + Twitter Card meta tags | ✅ |
| Favicon set (16/32/180 + .ico) | ✅ |
| OG share image (1200×630, Pillow-generated) | ✅ |
| Cookie consent banner (Klaro-style, GDPR + CCPA) | ✅ |
| Self-hosted privacy + ToS | ✅ |
| Affiliate CTAs (placeholder href) | 🟡 — replace href when networks approve |

---

## 5. Content pipeline (scrape, extract, ingest)

### 5.1 Scraping (Wisconsin portal)

| Component | Status |
|---|---|
| `scripts/scrape_loop.py` (Playwright + WI portal) | ✅ |
| Search cache (`_search_cache.json`) — never re-search a name | ✅ |
| Existing-DB-brands exact-match skip | ✅ |
| SHA-256 dedup at download | ✅ |
| Backlog cap (`--max-pending`) | ✅ |
| Rate-limit (2.5s between portal requests) | ✅ |
| Multi-state portal scrapers (MN, CA, NY, IN) | ⛔ deferred — current pipeline cost-safe for multi-state via content dedup |

### 5.2 Extraction (Max-plan via `claude -p`)

| Component | Status |
|---|---|
| `scripts/extract_loop.py` orchestrator | ✅ |
| **v2 fast-path: text-only single-prompt via Haiku** | ✅ ~$0.17/FDD avg |
| v1 fallback: multi-turn vision (now also on Haiku, was Sonnet) | ✅ ~$0.30/FDD |
| Quality fallback triggers (sections missing / table-as-image Item 19) | ✅ |
| Pre-flight PDF filter (skip non-FDDs) | ✅ |
| Post-extraction validation (broken JSON / missing fields → retry) | ✅ |
| SHA-256 dedup (`_sha_to_stem.json`) | ✅ |
| Content-key dedup (`_content_to_stem.json`) | ✅ |
| Rate-limit detection (don't increment attempt_count) | ✅ |
| Permanent-fail sentinel (3-strike) | ✅ |
| Pre-computed section boundaries (no Bash call) | ✅ |
| Inlined schemas (no Read of `src/prompts.py`) | ✅ |
| Item 19 no-FPR pre-scan (skip if explicit no-FPR) | ✅ |
| Known metadata pre-extraction | ✅ |
| `--output-format=json` for token tracking | ✅ |
| ANTHROPIC_API_KEY scrubbed (forces OAuth/Max plan) | ✅ |
| Auto re-ingest + regen every 5 successful extractions | ✅ |

### 5.3 Ingest & site regen

| Component | Status |
|---|---|
| `scripts/ingest_outputs.py` (JSON → SQLite) | ✅ |
| Lenient JSON parser fallback (recovers from escape errors) | ✅ |
| `src/site_gen.py` static site generator | ✅ |
| Auto-emits CNAME, IndexNow key file, OG image, favicons | ✅ |
| `--ping` flag → auto-runs IndexNow submit | ✅ |
| Per-page fingerprint watermark | ✅ |

### 5.4 Monitoring & reporting scripts

| Script | Purpose | Status |
|---|---|---|
| `scripts/pipeline_status.py` | DB state, PDF inventory, extraction outcomes, dedup savings | ✅ |
| `scripts/token_report.py` | Aggregate token + $ across manifest | ✅ |
| `scripts/audit_site.py` | 6-dimension site audit (HTML, JSON-LD, links, FAQ, compliance, a11y) | ✅ |
| `scripts/lighthouse_audit.py` | Wraps Lighthouse CLI for local audit | ✅ ready (needs `npm install -g lighthouse`) |
| `scripts/indexnow_submit.py` | POSTs sitemap URLs to api.indexnow.org | ✅ |
| `scripts/_pdf_dedup.py` | Content-key extraction from page 1 | ✅ |
| `scripts/_backfill_content_index.py` | One-time content-index backfill | ✅ |

### 5.5 Cost optimization timeline (this session)

| Stage | Cost / FDD | Reduction |
|---|---|---|
| Original v1 (multi-turn vision, Sonnet, full prompt re-read) | ~$1.00 | baseline |
| + Bash dropped, schemas inlined, no-FPR skip | ~$0.95 | -5% |
| + Pre-computed sections, known metadata | ~$0.89 | -11% |
| **v2 single-prompt text-only Haiku** | **~$0.17** | **-83%** |
| **v1 fallback Sonnet → Haiku** | **~$0.30** | (fallback only) |
| **Blended avg (v2 + Haiku-fallback)** | **~$0.20** | **-80% from baseline** |

---

## 6. Affiliate networks & monetization

### 6.1 Affiliate program applications

| Network | Status | Next step |
|---|---|---|
| FlexOffers | 🟡 application submitted 2026-05-17 (under review, 5 business days) | Watch email for approval |
| Impact | ❌ **Marketplace declined 2026-05-17** (common for new domains without traffic). Account active for direct brand partnerships + program invitations. | Pursue direct brand programs via brand-specific sign-up links. **Reapply ~2026-09-01 with traffic data.** |
| Awin | ⛔ not yet applied | Apply at https://awin.com/us/publishers ($5 refundable deposit) |
| Vellko Media | ⛔ deferred — apply once traffic baseline | At 1k+ sessions/mo |

### 6.2 Direct partnerships (revenue-triggered, Phase 2)

| Partner | Trigger | Status |
|---|---|---|
| FranNet (franchise consultant network) | 5k+ sessions/mo | ⛔ |
| IFPG (International Franchise Professionals Group) | 5k+ sessions/mo | ⛔ |
| ApplePie Capital (SBA franchise lender) | 5k+ sessions/mo | ⛔ |
| BoeFly (franchise financing marketplace) | 5k+ sessions/mo | ⛔ |
| FranChoice | 5k+ sessions/mo | ⛔ |
| FranServe | 5k+ sessions/mo | ⛔ |

### 6.3 CTAs & lead capture

| Item | Status |
|---|---|
| "Talk to a franchise consultant" affiliate CTA (placeholder) | 🟡 — replace href once FlexOffers approved |
| "Get pre-qualified for SBA financing" affiliate CTA (placeholder) | 🟡 — replace href once approved |
| Per-CTA FTC disclosure (italic above each) | ✅ |
| Site-wide FTC disclosure (footer) | ✅ |
| Standalone /affiliate-disclosure/ page | ✅ |

### 6.4 Lead magnets

| Magnet | Format | Status | Next step |
|---|---|---|---|
| FDD Buyer's Checklist | 10-page PDF | ✅ **shipped** at `/lead-magnets/fdd-buyers-checklist.pdf` (178 KB, 2,709 words) | Optional v1.1 polish: author byline, "Last updated" date, "What you'll learn" box. Configure Formspree autoresponder email |
| Top 50 Franchises Under $200K | PDF report | ⛔ | After magnet #1 working |
| Franchise Due Diligence Template | Spreadsheet | ⛔ | Defer |
| FDD Red Flags Guide | PDF | ⛔ | Defer |

---

## 7. Compliance & legal

### 7.1 Required at launch

| Item | Status |
|---|---|
| FTC affiliate disclosure (16 CFR Part 255) — footer + per-CTA + page | ✅ |
| Cookie consent (GDPR + CCPA) | ✅ |
| Privacy policy (self-authored) | ✅ |
| Terms of service (self-authored, incl. anti-scrape §7) | ✅ |
| Accessibility (ADA Title III: alt text, keyboard, WCAG AA, form labels) | ✅ |
| WAVE accessibility check against live site | ⏳ — run after launch settles |
| Lighthouse audit (target 95+ all axes) | ⏳ — run after launch settles |

### 7.2 Compliance reviews resolved

| Item | Resolution |
|---|---|
| Closure rate badge (was "System Health: Stable/Mixed/Contracting") | ✅ reframed as "Closure rate: X%" with explicit arithmetic explanation |
| Breakeven scenario (was declarative) | ✅ reframed as "Arithmetic breakeven scenario", "not a projection", FTC §436.5(s) link |

### 7.3 Compliance items requiring attorney

| Item | Cost | Trigger |
|---|---|---|
| Franchise attorney review of interactive calculators (F4.1) | $2-5k | Before custom-domain projection-heavy launch |
| Trademark filing for "FranchiseDepth" (USPTO TEAS) | ~$350 self-filed | $2,500/mo recurring (3 mo) |

### 7.4 Anti-scraping & content protection (Category 10)

| Feature | Status |
|---|---|
| F10.2 robots.txt — blocks training crawlers, allows AI citation/search bots | ✅ |
| F10.3 ToS anti-scraping clause (§7) | ✅ |
| F10.5 Watermarks (per-page fingerprint comment) | ✅ |
| F10.1 Cloudflare proxy | ⛔ requires Cloudflare account setup |
| F10.4 Honeypot fingerprint links | ⛔ requires F10.1 (Cloudflare for IP block) |
| F10.6 JS-rendered Item 19 | n/a — methodology explicitly recommends against |

---

## 8. Monitoring, security, reliability

### 8.1 Uptime monitoring

| Item | Status | Next step |
|---|---|---|
| UptimeRobot account | ⛔ | Sign up at https://uptimerobot.com (free plan) |
| Monitor 1: https://franchisedepth.com (5min) | ⛔ | After signup |
| Monitor 2: sitemap.xml (15min) | ⛔ | After signup |

### 8.2 Backup (Backblaze B2)

| Item | Status | Next step |
|---|---|---|
| Backblaze B2 account | ⛔ | Sign up at https://www.backblaze.com/b2 (free up to 10GB) |
| Bucket `franchisedepth-backup` (private) | ⛔ | Create after signup |
| Backup script for SQLite DB + source PDFs + docs/ | ⛔ | Build after credentials saved |

### 8.3 Security — 2FA audit

| Account | Status |
|---|---|
| GitHub | ⏳ verify 2FA enabled |
| Porkbun | ⏳ verify 2FA enabled |
| Google (GA4 + GSC) | ⏳ verify |
| Microsoft (Bing + Clarity) | ⏳ verify |
| Anthropic | ⏳ verify |
| Affiliate networks | ⏳ verify as available |
| Recovery codes saved offline | ⏳ print or password manager |

---

## 9. Distribution & off-page authority (Pillar 5)

**All items are owner execution — no code lever.**

| Channel | Cadence target | Status |
|---|---|---|
| Reddit (r/franchise, r/smallbusiness, r/Entrepreneur) | 3-5 substantive answers/week | ⛔ |
| HARO / Connectively / Featured.com | 3-5 responses/week | ⛔ |
| LinkedIn data-driven posts | 1-2/week | ⛔ |
| Industry directory submissions (Franchise Times, FranchiseDirect, IFA) | One-time | ⛔ |
| PR / trade publication outreach | Ongoing | ⛔ |
| Quarterly trend reports (PDF + landing) | First targeted month 4 | ⛔ |

### Social handles (claim for brand protection)

| Platform | Handle | Status |
|---|---|---|
| Twitter/X | `@franchisedepth` | ⛔ |
| LinkedIn Company | "FranchiseDepth" | ⛔ |
| Reddit | `u/franchisedepth` | ⛔ |
| Bluesky | `@franchisedepth.bsky.social` | ⛔ |
| YouTube | `@franchisedepth` | ⛔ |
| Threads | `@franchisedepth` | ⛔ |

---

## 10. Analytics & measurement (Pillar 8)

| Tool | Purpose | Status |
|---|---|---|
| GA4 | Traffic + conversion | ✅ live |
| Google Search Console | Search performance | ✅ verified, sitemap pending submit |
| Bing Webmaster Tools | Bing search performance | ✅ verified + IndexNow |
| Microsoft Clarity | Heatmaps + session replay | ✅ live |
| PostHog | A/B testing infrastructure | ⛔ free tier signup when ready |
| Ahrefs Webmaster Tools | Backlink monitoring | ⛔ free signup |

### Review cadences (start once traffic exists)

| Cadence | Time | What |
|---|---|---|
| Daily (5 min) | — | Check GA4 sessions, GSC clicks, indexing, crawl errors |
| Weekly (30 min) | — | Top 20 pages, top 20 queries, new backlinks, conversion events, top exits |
| Monthly (2 hours) | — | MoM traffic, ranking deltas, backlink delta, gap analysis, methodology update if data refreshed |

### Search Console mining workflow

| Item | Status |
|---|---|
| `docs_internal/gsc_mining_workflow.md` documented | ✅ |
| Run weekly once GSC has ≥4 weeks of data | ⏳ — start ~4 weeks post-launch |

---

## 11. Future / deferred / Phase 2+

### 11.1 Phase 2 (post-traffic baseline)

| Item | Trigger | Status |
|---|---|---|
| B2B Newsletter (Tue Trending + Thu New) | 500+ emails + 5k sessions/mo | ⛔ Beehiiv platform planned |
| Trending detection script | 2-3 months GA4 data | ⛔ infra ready, awaits data |
| First quarterly trend report | Month 4 | ⛔ |

### 11.2 Phase 3+

| Item | Status |
|---|---|
| **Cost calculator: FRED live indicators** | ⛔ deferred — wire in live SBA prime rate, CPI, regional wage growth via FRED API to update calculator defaults dynamically |
| **Cost calculator: median wage by state** | ⛔ deferred — pull BLS state-level wage data to forecast employee-labor input based on user's state |
| **Cost calculator: per-industry COGS / margin defaults** | ⛔ deferred — already have MARGIN_BANDS by industry; expose as default fills in advanced mode |
| **Cost calculator: shareable scenario URLs** | ⛔ deferred — encode all calc inputs as `?calc=...` query for sharing/bookmarking |
| **Cost calculator: PDF/CSV export of scenario** | ⛔ deferred — let users download their assumptions + chart |
| Spanish multi-language | ⛔ |
| TikTok content | ⛔ explicitly out of scope |
| YouTube content | ⛔ explicitly out of scope |
| White-label data licensing | ⛔ at $500-2k/mo per firm |
| API access for institutional buyers | ⛔ Phase 4 |
| Direct franchisor partnerships | ⛔ at 5k+ sessions |
| Paid acquisition (Reddit Ads, Google Ads) | ⛔ defer until $200+ monthly revenue baseline |

### 11.3 Revenue-triggered

| Trigger | Tasks |
|---|---|
| $500/mo recurring (2 mo) | Google Workspace email upgrade, HARO B2B Writer sub, re-eval Mediavine Journey |
| $1,000/mo recurring (3 mo) | LLC formation (WY or UT), EIN, business bank (Mercury/Relay), Wave bookkeeping, W-9s to affiliate networks, 25% tax set-aside |
| $2,500/mo recurring (3 mo) | USPTO trademark, franchise attorney review of calculators, Ahrefs/Semrush sub, Raptive ad apply |
| $5,000/mo recurring | Cyber liability + E&O insurance, direct consultant partnerships, first contractor hire |

### 11.4 Agent SDK migration (June 15+)

| Step | Status |
|---|---|
| `agent_sdk_migration_guide.md` written | ✅ |
| Claude Code to latest | ⏳ pre-June 15 |
| `claude login` (Max 20x auth verified) | ⏳ |
| Pick migration path: A (claude -p subprocess) or B (Agent SDK Python) | ⏳ — B preferred for cache_control breakpoints |
| Compatibility shim per guide | ⏳ |
| Side-by-side test on 5 FDDs | ⏳ |
| Claim $200 credit | ⏳ June arrival |
| `USE_AGENT_SDK=true` switch | ⏳ |
| 50-brand food QSR validation pilot (~$15) | ⏳ |
| 750-brand expansion (~$220 mostly from credit) | ⏳ |

**Expected cost cut once migrated:** 30-50% on top of current v2 baseline (via real prompt caching across invocations, not just within).

---

## 12. Open risks

| Risk | Mitigation |
|---|---|
| HTTPS cert sometimes takes 24h or fails | ✅ already provisioned; re-add domain if it fails |
| DNS propagation variance | ✅ all records verified |
| **CNAME deletion on regen** | ✅ mitigated — site_gen.py auto-emits |
| Affiliate approval rejections | Have FlexOffers + Impact + Awin in queue |
| Google HCU classifier flag (low-quality programmatic) | Quality threshold met (500w+ per page, real analysis, unique opening) |
| Anthropic credit policy changes | Agent SDK migration is the lever |
| Source FDD format changes | Lenient JSON parser + v1 fallback recover most cases |
| Item 19 image-only tables (Haiku can't read) | ✅ v1 vision fallback wired |
| Max-plan window exhaustion mid-batch | ✅ rate-limit detection sleeps + retries |
| pdf_utils section detection misses | ✅ v1 fallback when sections empty |
| **Impact Marketplace decline** | Lean on FlexOffers + Awin in the interim; reapply Impact ~2026-09-01 with traffic data. Account stays active for direct-brand program invites |
| **Item 19 chart misrepresents thin-disclosure brands** | Section 16.1 — 172 brands flagged; thin-disclosure detection + longitudinal-line-chart fallback + warning banner before mass-apply |
| **Calculator math edge cases hurt credibility** | Section 16.2 — sanity-check rules (Y1 net 5-15% of revenue, payback 3-7yr); auto-warning when outputs implausible |
| **Stale FDD data on fast-growing brands** | Section 16.3 — age audit + re-extraction queue for brands >18mo old; Crumbl (2023) is priority |
| **Paid tier launched too early without validation** | Section 17 — explicit validation gates: 50+ waitlist + 5 consultant calls + 500 brands + Tier 1 fixes complete |
| **Pricing too high vs. competitor Vetted Biz ($64-80)** | Founding member tier locks in 50% off ($19/$39) for first 100 |

---

## 13. Credential & ID vault

> Never put actual passwords or API secrets here. Public IDs only.

| Service | Public ID | Where credentials |
|---|---|---|
| GitHub | `josh-max2` | Password manager + 2FA |
| Porkbun | franchisedepth.com | Password manager + 2FA |
| Google (GA4 + GSC) | `G-ZEPEB3Z67R` | Password manager + 2FA |
| Microsoft Clarity | `wspuk90u8d` | Password manager + 2FA |
| Formspree | `xjgzvgrz` | Password manager |
| Bing IndexNow | `108a9bb5a8ed4718a9ff03218f2899f6` | Password manager |
| FlexOffers | (pending approval) | Password manager |
| Impact | (in progress) | Password manager |
| Awin | (not yet) | Password manager |
| UptimeRobot | (not yet) | Password manager |
| Backblaze B2 | (not yet) | Password manager + secure file |
| Anthropic | (account) | Password manager + 2FA |

---

## 14. Documentation references

| Document | Purpose |
|---|---|
| **PROJECT_TRACKER.md** (this doc) | **Single source of truth — use this** |
| `franchisedepth_methodology_v2.md` | 10-pillar growth methodology + per-row project tracker (deep detail) |
| `franchisedepth_features_roadmap.md` | Feature backlog with priorities P0–P5 |
| `franchisedepth_year_1_income_costs` | Interactive income/cost dashboard |
| `agent_sdk_migration_guide.md` | Agent SDK refactor instructions (June 15+) |
| `fdd_tool_build_spec.md` | Original technical spec |
| `HANDOFF.md` | Cross-session resume context |
| `fdd-tool/docs_internal/gsc_mining_workflow.md` | GSC priorities cadence |
| ~~`franchisedepth_launch_tracker.md`~~ (other-AI artifact) | **Superseded by this PROJECT_TRACKER.md — do not edit** |

---

## 15. Critical-path order — what to do next

### 🔥 DO RIGHT NOW

| # | Action | Time | Blocks |
|---|---|---|---|
| **1** | **Tick "Enforce HTTPS" in GitHub Pages settings** | **5 sec** | Closes http→https redirect gap |
| ~~2~~ | ~~Submit sitemap.xml in GSC~~ | ✅ **DONE** | 791 pages discovered, status Success |
| **3** | **Enable Formspree autoresponder email** for the lead-magnet form | 2 min | Auto-sends checklist PDF link without manual reply. Form → Notifications → Autoresponse → enable + paste short template with PDF URL |

### Within next session (~1.5 hours total)

| # | Action | Time | Why it matters |
|---|---|---|---|
| 3 | Configure Porkbun email forwarding | 5 min | Unlocks `hi@`, `hello@`, `support@` references in privacy + contact |
| 4 | Verify Porkbun auto-renew + WHOIS privacy + domain lock | 5 min | Domain protection (one expired domain = total loss) |
| 5 | 2FA audit across 5+ accounts | 30 min | Security hygiene |
| 6 | Claim social handles (Twitter, LinkedIn, Reddit, Bluesky, YouTube, Threads) | 30 min | Brand protection — squatters move fast |
| 7 | Pursue Impact direct-brand programs (via brand-specific sign-up links) | 15 min | Marketplace was declined; direct programs still open |
| 8 | Setup UptimeRobot monitor | 10 min | First alert when site goes down |

### Within next week (~5 hours)

| # | Action | Time | Why |
|---|---|---|---|
| ~~9~~ | ~~Author FDD Buyer's Checklist PDF~~ | ✅ **DONE** | 10 pages, 178 KB, deployed at `/lead-magnets/fdd-buyers-checklist.pdf`. Forms have `_next` redirect to thank-you page. Optional v1.1 polish: author byline, "Last updated" date, "What you'll learn" box |
| 10 | Setup Backblaze B2 + backup script | 30 min Ops + 1h Eng | Disaster recovery for DB + extracted JSON |
| 11 | Wait for FlexOffers approval, then swap affiliate hrefs | passive | When email arrives, ~1h of href substitutions |

### Ongoing

| # | Action | Why |
|---|---|---|
| 12 | Start Pillar 5 distribution work (Reddit, HARO, LinkedIn) | Biggest unstarted pillar — owner execution only, no code lever |
| 13 | Keep running scrape + extract loops toward 500-1000 brand target | Pipeline is cost-safe + idle-safe; let it run |
| 14 | **Agent SDK migration (June 15+)** | 30-50% further cost cut + true cross-invocation prompt caching |
| 15 | Reapply to Impact Marketplace ~2026-09-01 | When traffic data supports the application |

---

## 16. Quality audit & fixes — Phase 4 Tier 1-3

> Strategy decision **2026-05-19**: pause brand-count expansion past 386 until credibility issues on existing pages are fixed. The free brand database is the SEO/AEO moat — quality there is more valuable than scale right now.

### 16.1 Item 19 chart audit (thin-disclosure misrepresentation)

| Item | Status | Notes |
|---|---|---|
| Identify thin-disclosure brands | ✅ DONE | 172 brands flagged; Dumpster Dudez confirmed |
| Detection logic in pipeline | ✅ DONE | `item19_disclosure_quality()` in `src/derived.py:322` returns kind ∈ {longitudinal_affiliate, affiliate_only, thin_franchised, performance_anchored, broad_distribution, none} + warning severity |
| Differential render for thin-disclosure | ✅ DONE | Chart suppressed for longitudinal_affiliate/affiliate_only kinds (Planet Fitness, Popeyes, Peet's verified zero chart canvas); thin_franchised still shows chart with adaptive label; warning banner renders in yellow/red box above chart via `.item19-disclosure-warning .item19-disclosure-{warn,strong}` CSS |
| Misleading "cohort × metric" label fixed | ✅ DONE | Chart-note now adaptive per disclosure kind in `src/templates/brand.html:580-592` |
| Verified on samples | ✅ DONE | 5 brands verified: Dumpster Dudez (thin_franchised, chart shows w/ adaptive label), Planet Fitness + Popeyes + Peet's Coffee (chart suppressed, red warning shown), Batteries Plus + 1-800-Got-Junk + Amazing Athletes (broad_distribution, normal chart) |
| Mass-apply across all 461 brand pages | ✅ DONE | Pipeline change applies automatically on `site_gen.py` regen |
| Future-proof in `site_gen.py` | ✅ DONE | Same logic auto-applies on every regen |

**Status: Tier 1.1 SHIPPED 2026-05-19.**

### 16.2 Calculator math sanity audit

| Item | Status | Notes |
|---|---|---|
| Sanity rules defined | ⛔ TODO | Y1 net = 5-15% of revenue for QSR; payback = 3-7 years typical; flag outside ranges |
| Per-brand sanity sweep | ⛔ TODO | Specific brand needing review: Domino's showed Y1 $780k net / 1-yr payback @ $1.29M rev — implausible |
| Verify math invariants | ⛔ TODO | Owner labor opp-cost subtracted; debt service when financing>0; tax applies to profit not revenue; operating cost defaults reasonable (60-75% food/QSR, 55-70% services) |
| UI warning when implausible | ⛔ TODO | Small caption below output: "Operating costs may be too low for this category" |
| Fix list + auto-fixes | ⛔ TODO | Brands with sanity issues get default-value corrections |

### 16.3 FDD age audit

| Item | Status | Notes |
|---|---|---|
| `fdd_age_badge()` function | ✅ DONE | `src/derived.py:548` — returns badge dict from filing_year |
| Brand-by-brand age inventory | ⛔ TODO | Identify brands with FDDs older than 18mo and 24mo cutoffs |
| Re-extraction queue for stale brands | ⛔ TODO | Crumbl (2023) is priority; check WI/CA/MN/IL for newer filings |
| Prominent page warning when no newer FDD | ⛔ TODO | "Note: This FDD is X months old" |

### 16.4 Brand-page template improvements (Tier 2)

| Item | Status | Notes |
|---|---|---|
| 16.4.1 TL;DR / Key Facts card on every brand page | ⛔ TODO | Position above tab nav; sticky-friendly; structured-data markup; this is what AI search will quote |
| 16.4.2 Sticky section tab navigation | ⛔ TODO | `position: sticky`, top offset preserves TL;DR briefly; z-50; highlight active section; mobile collapse |
| 16.4.3 Author byline + trust signals + about page rebuild | ⛔ TODO | Site-owner byline → /about/; "Last updated" prominent; about page needs real photo + background + LinkedIn + methodology link. **Owner name TBD — do not hardcode without explicit approval** |
| 16.4.4 Worst-performer Item 19 callout | ✅ DONE | `worst_performer_callout()` in `src/derived.py:606` — wired in `site_gen.py:1180` |
| 16.4.5 Above-market royalty flag | ✅ DONE | `fee_benchmark_callout()` in `src/derived.py:496` — wired in `site_gen.py:1187` |

### 16.5 Infrastructure fixes (Tier 3)

| Item | Status | Notes |
|---|---|---|
| 16.5.1 robots.txt unblocks AI search bots | ✅ DONE | `docs/robots.txt` allows ChatGPT-User, OAI-SearchBot, PerplexityBot, Perplexity-User, Applebot-Extended, Meta-ExternalFetcher; emitted by `site_gen.py:2331` so regen preserves it |

---

## 17. Paid tier strategy & validation — Phase 4 Tier 4-5

> Strategy decision **2026-05-19**: layer a B2B paid analytics tier on top of the free brand database. Free tier stays free forever (it's the SEO/AEO moat). Paid tier is additive, not a replacement.

### 17.1 Tier structure & pricing — DECIDED

| Decision | Detail |
|---|---|
| **Two tiers at launch** | Researcher $29/mo · Professional $79/mo |
| **Free Forever** | Existing brand database, calculators, comparisons — no change |
| **Enterprise** | "Contact us" link; no pricing surface initially |
| **Year 2 add** | Pro tier $149/mo (cross-brand API, custom reports) |
| **Founding members** | First 100 customers lock in 50% off forever: Researcher $19/mo, Professional $39/mo |

### 17.2 Validation infrastructure (no engineering of actual paid product yet)

| Item | Status | Notes |
|---|---|---|
| 17.2.1 Paid tier waitlist signup form | ⛔ TODO | Formspree tag `waitlist:premium`; placements: homepage hero-adjacent, top-10 traffic-potential brand pages (food/QSR), methodology, about; redirect to thank-you with founding-member counter (e.g. "You're #14 of 100"); 1-2 validation questions |
| 17.2.2 "Best Performing" SEO landing pages | ⛔ TODO | `/best-performing-franchises/`, `/best-food-franchises/`, `/best-fitness-franchises/`, `/best-home-services-franchises/`, `/best-franchises-under-100k/`, `/best-franchises-under-250k/`, `/best-franchises-by-state/[state]/` (51 pages). Teaser top-5 visible, rest gated behind "Upgrade to Researcher tier — $29/mo". Each embeds waitlist form |
| 17.2.3 `/pricing/` preview page (no purchase enabled) | ⛔ TODO | Three columns: Free / Researcher / Professional. Public founding-member counter. CTA links to waitlist form |
| 17.2.4 LinkedIn outreach to 10 franchise consultants | ⛔ TODO | Manual; target by end of week; validate feature priorities |

### 17.3 Validation gates — block engineering until met

> Engineering of auth/Stripe/dashboard does **not** begin until all four gates are green:

| Gate | Status |
|---|---|
| 17.3.1 ≥50 waitlist signups (demand) | ⛔ Not yet (signup form not built) |
| 17.3.2 ≥5 consultant conversations completed (feature validation) | ⛔ Not yet |
| 17.3.3 500 brand coverage hit (data depth) | 🟡 386 / 500 (77% of way) |
| 17.3.4 Section 16 Tier 1 fixes complete (quality) | ⛔ Not yet (16.1, 16.2, 16.3 pending) |

### 17.4 Engineering (BLOCKED until 17.3 all green)

| Item | Status |
|---|---|
| 17.4.1 Auth (email + password) | ⏸️ BLOCKED on 17.3 |
| 17.4.2 Stripe subscription integration | ⏸️ BLOCKED |
| 17.4.3 Database query API (filter/sort across brands) | ⏸️ BLOCKED |
| 17.4.4 Filtering/sorting UI | ⏸️ BLOCKED |
| 17.4.5 CSV exports | ⏸️ BLOCKED |
| 17.4.6 State-level dashboards (auto-generated from DB) | ⏸️ BLOCKED |
| 17.4.7 5-10 brand comparison view (vs. free 2-brand) | ⏸️ BLOCKED |
| 17.4.8 Subscription management UI | ⏸️ BLOCKED |
| 17.4.9 14-day free trial flow | ⏸️ BLOCKED |

### 17.5 Scale to 500 brands (also Phase 4 Tier 5.1)

| Item | Status |
|---|---|
| Scale 313-500 (188 new brands) | ⏸️ **BLOCKED** on Section 16 quality fixes + June 15 Anthropic credit refresh. **Note: now at 386, so only +114 needed** |
| Apply Section 16 quality logic during extraction | ⛔ TODO when 16.x ships |

---

## 18. Revenue projections (updated 2026-05-19)

| Scenario | Year 1 Total | Year 2 Total | Year 2 Exit MRR |
|---|---|---|---|
| Affiliate only (original conservative) | $3,150 | $29,170 | $3,750 |
| + Paid tier launching Month 4 (conservative) | $18-25k | $99-139k | $9,170+ |
| + Paid tier launching Month 4 (realistic) | $25-35k | $130-180k | $14k+ |
| + Paid tier stretch (Tier 3 Pro added Year 2) | $35-50k | $180-250k+ | $20k+ |

Inputs underlying these scenarios: 386 brands shipping today → 500 by Q3 2026 (post-Anthropic-credit-refresh); ~$29 ARPU at Researcher tier with founding 50% off averaging closer to ~$23 ARPU first 100; Professional tier at $79/$39; assumes traffic ramp from current near-zero to 5-10k MoM organic by end of Year 1.

---

## Update log

| Date | Change |
|---|---|
| 2026-05-17 morning | Document created. Domain + GitHub Pages + DNS verified. |
| 2026-05-17 midday | GA4 + Clarity + Formspree wired. FlexOffers + Impact verification meta tags deployed. GSC verified via DNS. Bing via IndexNow. |
| 2026-05-17 afternoon | All 8 pillar guides shipped. New page types: 51 state pages, /industries/, /recent/, /press/, /contact/, /highest-reported-earnings/, /guides/ hub. ROI walk-forward chart on brand pages. |
| 2026-05-17 evening | **Pipeline cost optimization: v1 $0.99/FDD → v2 $0.17/FDD (7x cheaper).** Single-prompt text-only Haiku architecture. Quality fallback to v1 vision when needed (also now on Haiku). Pre-flight + post-validation guards. Token tracking. Pipeline-status dashboard. Currently scaling brand count toward +100. |
| 2026-05-17 late evening | Impact Marketplace **declined** (typical for new domains); account stays open for direct-brand programs and program invitations — reapply ~2026-09-01 with traffic data. PROJECT_TRACKER.md confirmed as single source of truth; other-AI launch tracker marked superseded. |
| 2026-05-17 night | **F4.4 Interactive multi-brand comparison tool shipped** at `/compare/`. Typeahead picker for 2-3 brands, client-side comparison table, auto-redirect to dedicated `/compare/A-vs-B/` static page when 2 same-category brands picked. Header nav: "Compare" added. Site grew from 169 → 584 pages (70 brand pages, 420 in-category compare pairs after ingest). |
| 2026-05-17 late night | **Architecture Fix Option A — NULL industry classifier**: `derive_industry()` in `scripts/ingest_outputs.py` overhauled with 7 new categories (automotive-services, salon-beauty, pet-services, staffing-employment, tech-services, mobility-accessibility, b2b-supplies) and richer brand-name patterns. NULL industry brands: 26 → 1. Static compare pages dropped from 420 to 172 (false cross-category pairs eliminated). Total site: 584 → 352 pages. |
| 2026-05-17 late night | **F4.4 v2 — Compare tool enhancements**: 6 → 11 rows (added marketing/brand fund %, monthly tech fee, liquid capital required, total outlets latest year, closure-rate badge w/ green/yellow/red tier, Item 19 disclosed?). Shareable URLs: `?brands=slug1,slug2,slug3` query param → preloads picks on page load; "Copy share link" button copies current state to clipboard. `fetch_brand_summaries()` extended to compute total_outlets + closure_rate per brand from Item 20 latest-year + risk-badge logic. Audit: 0 issues. |
| 2026-05-17 late night | **Prestige cohort scrape + extract**. Identified top-25 highest-search franchises absent from corpus (food/QSR, fitness, hotels, retail, real-estate categories). Scraped 23/25 from WI portal (~3 min, 94% hit rate; 2 misses: The Joint Chiropractic, 7-Eleven — both filed but not currently Registered in WI). Extracted all 23 via v2 in 45 min, avg $0.18/FDD. **Brands jumped 100 → 123**: now covering Subway, McDonald's, Dunkin', Burger King, Taco Bell, Wendy's, Pizza Hut, Domino's, KFC, Jersey Mike's, Planet Fitness, Anytime Fitness, Orangetheory, Massage Envy, UPS Store, H&R Block, Great Clips, Snap-on, RE/MAX, Century 21, Coldwell Banker, Holiday Inn Express, Kumon. Item 19 records: 797 → 926. Item 20 locations: ~10k → 12,805. Audit: 0 issues. Side-fix: flattened Domino's item7 (Traditional + Non-Traditional store types into single range). |
| 2026-05-17 late night | **Per-brand US state outlet heatmap shipped**. Built `src/state_map.py` with FiveThirtyEight-style tile grid (51 squares, quintile color scale, accessible). Renders inline SVG (~24KB) on 85/95 brand pages (89% — gated on ≥3 US states). HomeVestors: 47 states/861 outlets/top=Texas; Servpro: 50 states/2354 outlets/top=California. State name normalization handles "California"→"CA", filters non-US (Canada, Australia). |
| 2026-05-18 | **F4.7 Cost calculator shipped on every brand page**. Interactive client-side calculator: simple mode (5 inputs) + advanced mode (13 inputs covering revenue/investment/franchisor fees/COGS/rent/overhead/owner-labor/employee-labor/loan/rate/term/growth/tax). Outputs: Y1 net, payback year, 10-yr cumulative, live Chart.js cumulative-profit line. Defaults pre-filled from each brand's FDD (Item 7 midpoint, royalty/marketing/tech fees) + Item 19 broad-cohort median (annualized via unit_period). Affiliate CTAs ("Talk to a consultant", "Get pre-qualified for SBA") placed below output where viewer is high-intent. Airtight disclaimer block: educational-only, FTC §436.5(s) framing, 16 CFR 255 affiliate disclosure, no-warranty, no-advice. Top-of-page TOC nav (F4.8) added with anchor links to every major section. All inputs aria-labeled for a11y. 0 audit issues. |
| 2026-05-18 | **F4.7 v2 calculator upgrade — moat-leveraging features shipped**. Per-brand additions: (1) **Quartile preset buttons** Pessimistic/Median/Optimistic using bottom-25%/median/top-25% of that brand's Item 19 revenue distribution (annualized across cohorts), only changes revenue (other inputs preserved). (2) **Live percentile-rank context** under revenue input — "Your $1.29M is at the 55th percentile of Domino's Pizza franchisees who reported Item 19 data in the 2026 FDD (n=10)" with median/p25/p75 reference values. (3) **Itemized Y1 money-flow breakdown** in collapsible details — Revenue → COGS, royalty, marketing, tech fee, employee labor, rent, insurance, owner-labor opp cost, debt service, taxes → Your Y1 net. (4) **Industry-benchmark callouts** — "Royalty (5.5%) is 15% below the Food Quick Service median of 6.5% (n=10 peers)". Suppresses callouts when this brand's input = 0 (undisclosed). (5) **Similar-brand calculator links** — top 4 industry peers by total outlets, two-column. (6) **Shareable URL** — Copy-link button serializes all 16 inputs into query-string (`?rev=X&inv=Y&roy=Z&...`); restoreFromURL on load auto-applies + flips advanced mode if any advanced param present. Server-side: `fetch_brand_detail()` extended to compute revenue_distribution + P25/P50/P75 + industry_benchmarks (peer medians via JOIN on industry) + similar_brand_links. Template: preset row + percentile span + breakdown details + industry callouts div + share button + similar-brand list. CSS: 6 new component classes. JS: percentileRank() + renderBreakdown() + renderIndustryCallouts() + restoreFromURL() + share-link handler. Tested end-to-end on Domino's: 12-row breakdown, 4 similar brands, share URL round-trips correctly. |
| 2026-05-17 late night | **Lead magnet shipped — FDD Buyer's Checklist PDF** at `/lead-magnets/fdd-buyers-checklist.pdf`. 10 pages, 178 KB, 2,709 words. Cover (brand-blue gradient + accent bar) + Page 1 (What an FDD is, 16 CFR 436, 14-day rule, 5 key items) + Page 2 (7 Item 19 red flags) + Page 3 (5 franchisee validation questions + bonus exit question) + Page 4 (15-item pre-investment checklist with checkboxes) + Page 5 (14-term glossary) + Page 6 (route back to brand pages / compare / industries / guides). Built via Playwright `page.pdf()` against custom HTML+CSS (`src/lead_magnet/checklist.html` + `scripts/build_lead_magnet.py`). New `/get-the-checklist/thank-you/` page with direct download link. All Formspree forms (3 places: lead landing, brand pages, footer) now have `_next` redirect to thank-you page. Direct-download CTA also on landing page (no email required). PDF preserved in `src/lead_magnet/build/` so it survives `docs/` regen — site_gen.py auto-copies on each build. |
| 2026-05-17 late night | **robots.txt restructured for AI-citation traffic**. Split into two explicit groups: BLOCK training crawlers (23: GPTBot, ClaudeBot, CCBot, Google-Extended, Bytespider, etc.) + ALLOW AI citation/search crawlers (6: ChatGPT-User, OAI-SearchBot, PerplexityBot, Perplexity-User, Applebot-Extended, Meta-ExternalFetcher). Rationale: training bots scrape to build LLMs (no benefit), citation bots cite our content in live AI answers (drives referral traffic). |
| 2026-05-17 late night | **Homepage filter toggles (F3.3)**. 3-state segmented control: All brands / Item 19 disclosed only (67) / Missing main info (7). Combines with existing search + budget slider in unified `applyFilters()`. URL-sync via `?filter=item19` / `?filter=missing` query param + `?q=` and `?budget=`. Data attributes on each row + card (`data-has-item19`, `data-missing-info`). "Missing main info" defined as 2+ of fee/royalty/investment fields NULL. |
| 2026-05-17 late night | **GSC sitemap submission succeeded — 791 pages discovered**. Initial submission returned "Couldn't fetch" (cache propagation lag) then resolved on resubmission. Google now has full surface; indexing typically 2-7 days for first batch, 2-4 weeks for full crawl. IndexNow ping (790 URLs) already fanned out to Bing/Yandex/Seznam/Naver. |
| 2026-05-17 late night | **Data accuracy audit + stub fix**. Built `scripts/audit_data_quality.py` with 5 checks: schema (file presence/parse), range sanity (fees, royalty, investment within plausible bounds), cross-field consistency (low ≤ high), PDF spot-check (raw_excerpt grep-back into source PDF), confidence flag aggregation. Key findings: **PDF spot-check 95% verification rate** (LLM not hallucinating — quoted excerpts ARE in PDFs), 0 cross-field consistency violations across 88 brands. Surfaced 18 brands with `_read_error` stub outputs from early v1 attempts before pdftoppm was removed. **Fixed 7 fully-stub brands** (101 Mobility, Aire Serv, Dryer Vent Wizard, AdvantaClean, Aire-Master, Alair Homes, CertaPro Franchising) by deleting output dirs + re-running `extract_v2.py`. Cost: $0.89 API-equiv (~$0 actual on Max plan). Item 19 records: 717 → 797 (+80). Brands in DB: 88 → 92. Remaining 19 audit issues are different problem class (parse errors, missing files) for later. |
| 2026-05-19 | **MN long-tail batch + dashboard ship — DB jumps 386 → 461 brands (+75 net via claude -p).** Filter pass on MN's 424 previously-excluded brands identified 86 candidates with franchise-indicator legal-name patterns AND not already in DB. Downloaded 83 (3 fails), extracted 76 of 78 new ones (97% success). Notable adds: JL Beers, Sports Bra, Tails N' Trails, Pet Passages, JPAR Real Estate, Up Closets, ACT Autism Care Therapy, Mulberry's Garment Care, Layne's Chicken Fingers, MGallery Hotel, Project LeanNation, ManageMowed, Pizza Inn, Ferncrest, Haven, Sign Gypsies, BOR Restoration, USA Ninja Challenge. **Internal dashboard shipped at /dashboard/** — KPI tiles, coverage gauges (item19 71%, item20 74%, fees 96%), industry distribution (food-QSR leads), investment tiers, royalty histogram, top performers, most/least-expensive, recent additions, filing-state coverage, data freshness. Self-contained HTML, noindex. Also Tier 1.3 FDD age audit closed: 290 brands at current year (75%), only 22 are 2+ years old. Final state: 461 franchisors, 466 fdds, 5,448 item19 records (316 brands), 43,575 item20 rows. Audit: 0 tier-1, 18 tier-2 warnings. |
| 2026-05-19 | **Phase 4 strategy doc imported — new sections 16/17/18 added.** Strategic pause: stop adding brands past 386 until quality fixes in §16 ship. Tier-1 priorities: (a) Item 19 thin-disclosure chart misrepresentation (172 brands flagged; Dumpster Dudez confirmed — 5 dots all for the same 1-outlet "sole affiliate" cohort 2021-25); (b) calculator math sanity warnings (Domino's-style implausible Y1 net); (c) FDD age audit + re-extract queue (Crumbl 2023 priority). Tier-2: TL;DR Key Facts card, sticky section tabs, site-owner byline + about page rebuild. Tier-3: robots.txt for AI search bots (✅ already done). Tier-4 (paid-tier validation, no engineering yet): waitlist form + /pricing/ preview + "Best Performing" SEO pages. Section 17 captures the paid-tier strategy: Researcher $29/mo + Professional $79/mo (founding members lock 50% off; first 100 only). Engineering BLOCKED until 4 validation gates green (≥50 waitlist, ≥5 consultant calls, 500 brands, §16 complete). Update-log line is part of audit, not deployment work. |
| 2026-05-19 | **WI portal Max-plan batch — DB jumps 312 → 386 brands (+74 net via `claude -p`, $0 marginal API cost).** Surveyed WI for the 193 recognizable brands missing from DB; 85 had Registered filings. Downloaded 79 net-new PDFs via Playwright scraper (6 dedup hits against existing wi_scrape). Extracted 77 of 79 sequentially via `extract_v2.py` (claude -p, sonnet, single-shot all-items prompt) at ~2 min/PDF over ~2.5 hours. 2 stubborn fails (Jiffy Lube, Firehouse Subs — claude session quirks). Notable additions: **Hyatt, Wyndham, Best Western, Days Inn, Hampton Inn, La Quinta, Super 8, Red Roof Inn, Popeyes, Sonic, Wingstop, Five Guys, Buffalo Wild Wings, Cinnabon, Smoothie King, Jamba Juice, Tim Hortons, Caribou, Dairy Queen, Baskin-Robbins, Carvel, Hooters, Mathnasium, Goddard, Primrose, Kiddie Academy, Toppers Pizza, Mr. Transmission, Engel & Völkers, Better Homes & Gardens, Realty Executives, College Hunks, Two Men and a Truck, Budget Blinds, Mosquito Squad, Big O Tires, Tuffy, U.S. Lawns, Hand & Stone, Drybar, European Wax, Petland, Dogtopia, FastSigns, AlphaGraphics, Minuteman Press**. Pipeline: `survey_wi_missing.py` (substring/prefix recognition match, dedup against DB keys + fuzzy substring) → `download_wi_candidates.py` (Playwright, SHA dedup, resume-safe per-PDF save) → `wi_max_plan_pipeline.py` (sequential extract_v2.py, periodic ingest+audit). Final stats: 386 franchisors, 389 fdds, 5,186 item19 records (274 brands with item19), 39,112 item20 rows. Audit: 0 tier-1, 9 tier-2 warnings. |
| 2026-05-19 | **MN CARDS 185-brand batch shipped — DB jumps 123 → 312 brands (+189 net).** Curated recognition list (~500 brand names with substring + prefix matching). Survey identified 186 recognizable candidates across MN 2024-2026 Clean FDDs; fuzzy DB-side dedup (substring on brand_name_key) caught 23 already-have-newer overlaps. Downloaded 185/186 PDFs (1 stubborn 429 — Toppers Pizza). Extracted 185 PDFs across 5 parallel pools (3 simultaneous at peak), total wall-clock ~75 min, total cost ~$57. Mid-batch fixes: (a) `find_brand_match()` w/ substring (≥5 chars) + prefix (<5 chars) matching against both `franchise_name` and `franchisor` (legal name); (b) MN scraper 429 retry-with-backoff (30s/60s/120s); (c) re-extracted 2 PDFs whose Item 19 hit the 32k-token salvage path (107/127 records → clean re-extract); (d) deleted 13 item19 records with inconsistent value bounds (model misinterpretation of quartile/cohort tables — affected 7 brands, 0.3% of records). **Final DB: 312 franchisors, 313 fdds, 4,550 item19 records, 29,562 item20 rows. Audit: 0 tier-1, 6 tier-2 warnings (non-blocking).** Notable additions: Chick-fil-A, Choice Hotels, Midas, F45, Marco's Pizza, Papa John's, Panda Express, A&W, Pizza Ranch, Window World, Right at Home, Wings Etc, Wetzel's Pretzels, Tropical Smoothie, Cold Stone, Pinkberry, Blimpie, Taco Time, Taco John's, World Gym, Soccer Stars, Wendy's update, etc. Side-fix uncovered: `upsert_fdd()` doesn't UPDATE existing rows (only INSERT), so re-ingest after re-extract didn't refresh `has_item19` — patched in-place via `UPDATE fdds SET has_item19 = ...` and noted for future refactor. |

---

*Update this file whenever an item closes or a new item emerges. Keep it as the single source of truth.*
