# FranchiseDepth Growth Methodology v2

**Last updated:** 2026-05-17
**Status:** Active reference document
**Maintainer:** Josh

---

## Overview

FranchiseDepth is a data aggregation site for franchise buyers, built on publicly filed Franchise Disclosure Documents. This methodology covers SEO, AEO (Answer Engine Optimization), programmatic content scaling, compliance, conversion optimization, and growth — everything needed to make this site the most-cited source for franchise data on the internet.

**Out of scope (Phase 2+):**
- TikTok content distribution
- YouTube long-form content
- B2B newsletter (deferred to Phase 2 — trending detection infra built now, content cadence later)
- Multi-language (Spanish defer to Phase 3)
- Direct partnership/licensing deals

---

## Current State

| Component | Status |
|-----------|--------|
| Brand pages | 26 live |
| Category pages | 10 live + home-services rollup |
| Comparison pages | 31 live (all in-category pairs) |
| State pages | 0 |
| Tool/calculator pages | 0 (static breakeven scenario on brand pages — not yet interactive) |
| Schema.org markup | Comprehensive — Article, FAQPage, BreadcrumbList shipping; CollectionPage/ItemList not yet on category pages |
| XML sitemap | Generated with absolute URLs + lastmod; not yet submitted to GSC/Bing |
| robots.txt | Blocks 28 AI training + scraping crawlers, allows search engines (see Pillar 1) |
| llms.txt | Not present |
| Mobile-responsive | Yes |
| Custom domain | Pending (franchisedepth.com) |
| Email capture | Form code on every brand page + lead-magnet landing page; gated by FORMSPREE_ID env var (currently placeholder, hidden when unset) |
| FTC affiliate disclosure | Implemented — footer block on every page + italic per-CTA disclosure + standalone /affiliate-disclosure/ page |
| Cookie consent | Implemented — self-hosted Klaro-style banner with Accept all / Reject all / Customize, GDPR + CCPA compliant |
| Accessibility (ADA) | Audited and passing — skip-to-content, alt text on every image, keyboard nav with focus-visible outline, WCAG 2.1 AA contrast, form labels |
| Author bylines | Implemented — on every brand page + comparison page, JSON-LD author property |
| Methodology page | 2045 words, 11 sections incl. data dictionary + update log |
| Affiliate networks | Pending applications (FlexOffers, IFPG, ApplePie Capital, Boefly) |
| Site audit | scripts/audit_site.py runs 6 dimensions across all 76 pages — currently 0 issues |

---

## The Strategy in One Sentence

**Win long-tail brand-specific buyer queries through programmatic content depth + structured data, become the primary citation source AI engines use to answer franchise questions, and scale to comparison/state/tool pages to multiply organic surface area — all while building owned-channel resilience for when algorithms shift.**

---

## Project Tracker (all pillars)

**Status key:** ✅ Done · 🟡 Partial / gated on external account · ⛔ Not started · 📋 Reference/strategic content (not an action item) · n/a Out of scope or superseded

**Owner key:** Eng = code work · Ops = account creation / external action · Content = writing / PDF authoring · Distro = outreach / posting

| # | Pillar | Item | Status | Effort | Owner | Blocker / Next action |
|---|---|---|---|---|---|---|
| 1.01 | P1 Technical SEO | Custom domain (franchisedepth.com → GH Pages, CNAME, HTTPS, `SITE_PREFIX=""`) | ⛔ | S | Ops + Eng | Buy domain, set CNAME, flip `SITE_PREFIX` env var, regen |
| 1.02 | P1 Technical SEO | Submit sitemap to Google Search Console | ⛔ | XS | Ops | Needs GSC account + verified property |
| 1.03 | P1 Technical SEO | Submit sitemap to Bing Webmaster | ✅ via IndexNow | — | — | IndexNow active — 140 URLs submitted (HTTP 202) on 2026-05-17. Single endpoint fans out to Bing + Yandex + Seznam + Naver. Re-run `scripts/indexnow_submit.py --only-new` after each rebuild. Bing Webmaster GUI verification meta-tag scaffolding still in place for direct WMT signup if desired. |
| 1.04 | P1 Technical SEO | Submit to Yandex (low priority) | ⛔ | XS | Ops | Optional |
| 1.05 | P1 Technical SEO | Install GA4 (consent-gated wrapper) | ✅ | — | — | Measurement ID `G-ZEPEB3Z67R` wired. gtag.js loads via `_ga4.js` after Klaro analytics consent. Events: scroll_75, cta_click, outbound_click, lead_form_submit. |
| 1.06 | P1 Technical SEO | Install Microsoft Clarity | ✅ | — | — | Project `wspuk90u8d` wired via consent-gated `_clarity.js` wrapper. Loads only after analytics consent. Privacy policy + cookie banner both updated to disclose session recording. Text inputs auto-masked. |
| 1.07 | P1 Technical SEO | Lighthouse audit (target 95+) | ⛔ | S | Eng | Run after custom domain live |
| 1.08 | P1 Technical SEO | Create `llms.txt` + `llms-full.txt` | ✅ | — | — | Both generated each build (`site_gen.py`); llms-full includes data dictionary |
| 1.09 | P1 Technical SEO | robots.txt — block AI training, allow search | ✅ | XS | — | F10.2 — 28 bots blocked, parser-verified |
| 1.10 | P1 Technical SEO | Brand pages: Article + FAQPage + BreadcrumbList schema | ✅ | — | — | Audit-validated |
| 1.11 | P1 Technical SEO | Brand pages: `Product` schema (per methodology spec) | ✅ | — | — | Added via `@graph` alongside Article; no offers/price (franchise fee ≠ retail price) |
| 1.12 | P1 Technical SEO | Category pages: `CollectionPage` + `ItemList` schema | ✅ | — | — | Each category lists every brand as a positioned ListItem with absolute URL |
| 1.13 | P1 Technical SEO | Compare pages: Article + BreadcrumbList schema | ✅ | — | — | F5.1 — audit-validated |
| 1.14 | P1 Technical SEO | Compare pages: FAQPage schema (F5.2) | ✅ | — | — | 5-6 data-driven FAQs per pair (fee delta, royalty, outlets, Item 19 asymmetry, filing-year freshness) |
| 1.15 | P1 Technical SEO | Homepage: `Organization` + `WebSite` + `SearchAction` schema | ✅ | — | — | All three present. SearchAction `urlTemplate` = `{home}?q={search_term_string}`; homepage filter consumes the `q=` param |
| 1.16 | P1 Technical SEO | About + Methodology: `WebPage` + `Organization` schema | ✅ | — | — | AboutPage on /about/, WebPage on /methodology/; Organization on both |
| 2.01 | P2 Content + AEO | Opening summary paragraph (F1.1) | ✅ | — | — | 80-120w, adaptive per brand |
| 2.02 | P2 Content + AEO | FAQ section with JSON-LD (F1.5) | ✅ | — | — | 5-7 per brand |
| 2.03 | P2 Content + AEO | Industry context paragraph (F1.6) | ✅ | — | — | Names siblings + investment comparison |
| 2.04 | P2 Content + AEO | Date stamps prominently displayed (F1.7 + F2.6) | ✅ | — | — | Verified-from + per-section vintage lines |
| 2.05 | P2 Content + AEO | Source links on Item 19 numbers (F1.9) | ✅ | — | — | Per-row `#page=N` PDF deep links |
| 2.06 | P2 Content + AEO | Author byline on every page (F1.8) | ✅ | — | — | JSON-LD author |
| 2.07 | P2 Content + AEO | "X vs Y" comparison tables (F5.1) | ✅ | — | — | 31 compare pages live |
| 2.08 | P2 Content + AEO | Numbered "how to" lists for instructional queries | ⛔ | M | Content | Pillar/cluster guide pages don't exist yet |
| 3.01 | P3 Programmatic Scale | Brand pages 26 / 500-1000 target | 🟡 | scrape | Eng | Run `scrape_loop.py` + `extract_loop.py` (ready, awaiting "go") |
| 3.02 | P3 Programmatic Scale | Category pages 10 / 25-30 target | 🟡 | auto | Eng | Auto-scales with new brands |
| 3.03 | P3 Programmatic Scale | Comparison pages 31 / 200-500 target | 🟡 | auto | Eng | Auto-scales with new brands (all in-category pairs) |
| 3.04 | P3 Programmatic Scale | State pages 51 / 50 target | ✅ | — | — | Generated 51 state pages from Item 20 latest-year data. CollectionPage + ItemList schema, sortable table, breadcrumbs. Covers all states with disclosed outlets. |
| 3.05 | P3 Programmatic Scale | Tool pages 0 / 4-6 target | ⛔ | L | Eng | Interactive calculators (F4.1, F4.2, F4.3, F4.6) |
| 3.06 | P3 Programmatic Scale | Guide / FAQ pages 8 / 30-50 target | 🟡 | L | Content | Eight pillar guides shipped: Item 19, Item 7, Item 20, validation calls, breakeven horizon, SBA 7(a) financing, what's negotiable, and evaluating discovery day. Each ~1500-2400 words, Article schema. Cross-linked from brand pages via "Further reading →" links + interlinked at the bottom of each guide. |
| 3.07 | P3 Programmatic Scale | Quarterly trend reports 0 / 4 target | ⛔ | M each | Content | First one targeted month 4 post-launch |
| 3.08 | P3 Programmatic Scale | Quality threshold met per page (500w, original analysis, unique opening, links) | ✅ | — | — | All current pages clear the bar |
| 3.09 | P3 Programmatic Scale | Pillar / topic cluster architecture (e.g., "Franchise Investment Guide" hub + clusters) | 🟡 | L | Content + Eng | `/guides/` hub + 3 cluster pages (Item 19, Item 7, validation) shipped. Each brand page now has "Further reading →" links to the relevant guides, creating proper hub-and-spoke. |
| 4.01 | P4 Trust / E-E-A-T | Author byline on every page | ✅ | — | — | Brand + compare pages |
| 4.02 | P4 Trust / E-E-A-T | About page (1040w, credentials, gap story) | ✅ | — | — | Real photo deferred |
| 4.03 | P4 Trust / E-E-A-T | About page: real photo | ⛔ | XS | Ops | Owner comfort decision |
| 4.04 | P4 Trust / E-E-A-T | About page: real email surfaced | ⛔ | XS | Ops + Eng | Need email account; currently mailto only on /get-the-checklist/ |
| 4.05 | P4 Trust / E-E-A-T | Methodology page (2045w, 11 sections, data dictionary + update log) | ✅ | — | — | F2.1 closed |
| 4.06 | P4 Trust / E-E-A-T | Contact page | ✅ | — | — | Live at /contact/ with working Formspree form (ID `xjgzvgrz`). ContactPage JSON-LD. Hidden `source=contact-page` for dashboard filtering. |
| 4.10 | P4 Trust / E-E-A-T | Press / "Cited In" page | ✅ stub | — | Content | Stub page shipped at /press/ with citation guidance. Populates as citations land. |
| 4.11 | P4 Trust / E-E-A-T | Methodology footnotes / jargon tooltips | ✅ | — | — | Glossary section added to methodology page (12 terms with anchor IDs). Brand pages link key terms ("Item 19", "Item 20", "FPR") to glossary via `.jargon` class with native `title=` tooltips. |
| 4.07 | P4 Trust / E-E-A-T | Privacy policy (self-authored, 715w) | ✅ | — | — | |
| 4.08 | P4 Trust / E-E-A-T | Terms of service (self-authored, 1022w, F10.3 anti-scrape clause in §7) | ✅ | — | — | |
| 4.09 | P4 Trust / E-E-A-T | FTC affiliate disclosure (footer + per-CTA + standalone page) | ✅ | — | — | |
| 4.10 | P4 Trust / E-E-A-T | Press / "Cited In" page | ⛔ | XS | Content | Stub when first citation lands |
| 4.11 | P4 Trust / E-E-A-T | Methodology footnotes (jargon tooltips) | ⛔ | M | Eng | Tooltip system not built |
| 5.01 | P5 Off-Page Authority | Reddit answers (r/franchise, r/smallbusiness, etc., 3-5/wk) | ⛔ | ongoing | Distro | Owner execution |
| 5.02 | P5 Off-Page Authority | HARO / Connectively / Featured.com signup + 3-5 responses/wk | ⛔ | ongoing | Distro | Owner execution |
| 5.03 | P5 Off-Page Authority | LinkedIn data posts (1-2/wk) | ⛔ | ongoing | Distro | Owner execution |
| 5.04 | P5 Off-Page Authority | Industry directory submissions (Franchise Times, FranchiseDirect, IFA, etc.) | ⛔ | S | Distro | One-time per directory |
| 5.05 | P5 Off-Page Authority | PR / trade publication outreach | ⛔ | ongoing | Distro | Owner execution |
| 5.06 | P5 Off-Page Authority | Quarterly trend reports (PDF + landing + press distribution) | ⛔ | M each | Content + Distro | First targeted month 4 |
| 6.01 | P6 Compliance | FTC affiliate disclosure | ✅ | — | — | F2.3 — see 4.09 |
| 6.02 | P6 Compliance | Cookie consent (GDPR + CCPA) | ✅ | — | — | F2.4 — self-hosted Klaro-style |
| 6.03 | P6 Compliance | Accessibility (alt text, keyboard nav, WCAG 2.1 AA, form labels, skip-link) | ✅ | — | — | F8.1-F8.4 — `audit_site.py` passing |
| 6.04 | P6 Compliance | WAVE accessibility checker run against live site | ⛔ | XS | Eng | After GH Pages live |
| 6.05 | P6 Compliance | Privacy + ToS | ✅ | — | — | F2.5 — see 4.07/4.08 |
| 6.06 | P6 Compliance | Attorney review for breakeven scenario / future calculator | ⛔ | $2-5k + 1wk | Ops | Recommended pre-custom-domain |
| 7.01 | P7 CRO / Conversion | Single primary CTA per page template | ✅ | — | — | "Talk to a franchise consultant" primary on brand pages |
| 7.02 | P7 CRO / Conversion | GA4 conversion events configured | ✅ | — | — | Live with measurement ID `G-ZEPEB3Z67R`. See 1.05. |
| 7.03 | P7 CRO / Conversion | Microsoft Clarity installed | ✅ | — | — | Live (project `wspuk90u8d`). See 1.06. |
| 7.04 | P7 CRO / Conversion | PostHog account (for future A/B testing) | ⛔ | XS | Ops | Free tier, set up when traffic exists |
| 7.05 | P7 CRO / Conversion | Lead magnet #1: FDD Buyer's Checklist (4pg PDF) | 🟡 | 4h | Content | Landing page built; **PDF not authored** |
| 7.06 | P7 CRO / Conversion | Lead magnet #2: Top 50 Franchises Under $200K (PDF) | ⛔ | 8h | Content + Eng | Built from data |
| 7.07 | P7 CRO / Conversion | Lead magnet #3: Franchise Due Diligence Template (XLSX) | ⛔ | 6h | Content | |
| 7.08 | P7 CRO / Conversion | Lead magnet #4: FDD Red Flags Guide (PDF) | ⛔ | 4h | Content | |
| 7.09 | P7 CRO / Conversion | Email capture form on every brand page | ✅ | — | — | Live (Formspree `xjgzvgrz`). Source tagged per brand (`brand-{slug}`) for dashboard filtering. |
| 7.10 | P7 CRO / Conversion | Affiliate CTA: franchise consultant | 🟡 | — | Ops | Placeholder href="#"; awaiting FlexOffers/IFPG approval |
| 7.11 | P7 CRO / Conversion | Affiliate CTA: SBA lender | 🟡 | — | Ops | Placeholder; awaiting ApplePie / Boefly approval |
| 8.01 | P8 Analytics | GA4 — events + property | ✅ | — | — | Live with measurement ID `G-ZEPEB3Z67R`. See 1.05. |
| 8.02 | P8 Analytics | Google Search Console | ⛔ | XS | Ops | After domain live |
| 8.03 | P8 Analytics | Bing Webmaster Tools | ⛔ | XS | Ops | |
| 8.04 | P8 Analytics | Microsoft Clarity | ✅ | — | — | Live (project `wspuk90u8d`). See 1.06. |
| 8.05 | P8 Analytics | PostHog | ⛔ | XS | Ops | See 7.04 |
| 8.06 | P8 Analytics | Ahrefs Webmaster Tools (free backlink monitoring) | ⛔ | XS | Ops | |
| 8.07 | P8 Analytics | Daily monitoring cadence (5 min/day) | ⛔ | ongoing | Ops | Post-launch |
| 8.08 | P8 Analytics | Weekly review (30 min/wk) | ⛔ | ongoing | Ops | Post-launch |
| 8.09 | P8 Analytics | Monthly review (2 hrs/mo) | ⛔ | ongoing | Ops | Post-launch |
| 8.10 | P8 Analytics | GSC mining workflow doc (F7.5) | ⛔ | S | Content | Document once GSC has 4-6wk of data |
| 9.01 | P9 Trending Detection | Per-brand engagement metric collection | 🟡 events | — | Ops | Events defined in `_ga4.js`; flow once 1.05 unblocked |
| 9.02 | P9 Trending Detection | Surge detection script (F7.3) | ⛔ | M (12h) | Eng | Build after 2-3mo GA4 data accumulated |
| 9.03 | P9 Trending Detection | Trending history storage (CSV or SQLite) | ⛔ | XS | Eng | Folded into 9.02 |
| 9.04 | P9 Trending Detection | Tuesday newsletter ("Trending This Week") | 📋 | — | Content | Phase 2 — wait for 5k+ sessions baseline |
| 9.05 | P9 Trending Detection | Thursday newsletter ("New on FranchiseDepth") | 📋 | — | Content | Phase 2 |
| 9.06 | P9 Trending Detection | Email capture infrastructure | ✅ | — | — | Live across 4 form types: brand pages, /contact/, /get-the-checklist/, footer newsletter signup. See 7.09. |
| 9.07 | P9 Trending Detection | Footer newsletter signup field | ✅ | — | — | Live on every page; Formspree `xjgzvgrz`, source tagged `footer-newsletter`. |
| 10.01 | P10 Algorithm Resilience | Brand search optimization (LinkedIn / Reddit / press use "FranchiseDepth analyzed...") | ⛔ | ongoing | Distro | Owner execution — see Pillar 5 items |
| 10.02 | P10 Algorithm Resilience | Diversification target tracking (Google ≤60% by month 12) | 📋 | — | Ops | Measured post-launch from GA4 source data |

### Tracker by status (quick rollup)

| Status | Count | Categories represented |
|---|---|---|
| ✅ Done | 31 | Pillar 2 brand-page additions, Trust/E-E-A-T core, Compliance core, robots.txt, comparison pages with FAQ schema, full schema coverage on home/category/brand/compare/about/methodology, llms.txt + llms-full.txt, contact page, footer newsletter signup |
| 🟡 Partial (gated on external account) | 9 | Mostly Ops-blocked: GA4 ID, Formspree ID, affiliate URLs, lead-magnet PDF authoring |
| ⛔ Not started | 33 | Mix of Ops (Clarity, PostHog, GSC, domain), Content (pillar pages, guide pages, lead magnet PDFs, trend reports), and Distro (Reddit, LinkedIn, HARO, PR — all owner execution). Eng-only remaining: SearchAction on home (depends on F3.5 search), WAVE audit (depends on live site) |
| 📋 Reference | 3 | Phase 2 newsletters + diversification tracking (correctly deferred until traffic exists) |

**Critical-path order for next session:**
1. ~~Fill schema gaps 1.11, 1.12, 1.15, 1.16~~ ✅ Done
2. ~~llms.txt + llms-full.txt~~ ✅ Done
3. ~~Compare page FAQs (1.14 / F5.2)~~ ✅ Done
4. ~~Contact page (4.06)~~ ✅ Done
5. ~~Footer newsletter signup (9.07)~~ ✅ Done
6. ~~F3.2 Budget filter on category pages~~ ✅ Done
7. ~~F3.5 Internal header search + SearchAction~~ ✅ Done
8. ~~F9.2 Mobile fact-box accordion~~ ✅ Done
9. Set `FORMSPREE_ID` env var (unblocks 7.09 + 4.06 + 9.07 → live lead capture across all forms) — Ops, 15 min
10. Set `FD_GA4_ID` env var (unblocks 1.05 / 7.02 → event flow) — Ops, 15 min
11. Author the FDD Buyer's Checklist PDF (unblocks 7.05 lead magnet) — Content, 4h
12. Custom domain + Cloudflare (unblocks F10.1 + F10.4 + Lighthouse audit + WAVE) — Ops + Eng, 4h
13. Run scrape_loop + extract_loop (multiplies content footprint) — Eng/owner go-ahead. Note: before scaling beyond 1 state, wire the PDF dedup logic (`legal_name` + `effective_date` pre-filter) so multi-state extraction doesn't pay 2-3× for the same FDD content.

---

## The Ten Pillars

## Pillar 1: Technical SEO Foundation

### Required setup (Week 1)

- [ ] **Custom domain migration:** Point franchisedepth.com → GitHub Pages
  - GitHub repo Settings → Pages → Custom domain: franchisedepth.com
  - Namecheap DNS → CNAME `@` and `www` → `josh-max2.github.io`
  - Enable HTTPS once Let's Encrypt provisions (~30 min)
  - Set `SITE_PREFIX = ""` in `site_gen.py`, regenerate, push
- [ ] **Submit sitemap to Google Search Console:** `https://franchisedepth.com/sitemap.xml`
- [ ] **Submit sitemap to Bing Webmaster Tools** (same URL)
- [ ] **Submit sitemap to Yandex Webmaster** (low priority but free)
- [ ] **Install GA4** on all pages (gtag.js in base template)
- [ ] **Install Microsoft Clarity** (free heatmaps + session recordings)
- [ ] **Lighthouse audit** every page template — target scores 95+ on all four axes

### Core Web Vitals targets

| Metric | Target | Acceptable |
|--------|--------|-----------|
| LCP (Largest Contentful Paint) | <2.5s | <4.0s |
| CLS (Cumulative Layout Shift) | <0.1 | <0.25 |
| INP (Interaction to Next Paint) | <200ms | <500ms |
| TTFB (Time to First Byte) | <800ms | <1.8s |

Static HTML on GitHub Pages should pass all of these easily. If they don't, something is wrong.

### llms.txt (new convention, important)

Create `/llms.txt` at site root:

```
# FranchiseDepth

> Data-driven franchise research for buyers. We aggregate financial performance data from publicly filed Franchise Disclosure Documents (FDDs).

## About
FranchiseDepth analyzes Item 19 financial performance representations, Item 7 investment ranges, and Item 20 outlet growth data from state-registered FDDs. All data sourced from public state portals including Wisconsin, California, Minnesota, and Indiana.

## Coverage
- 24 franchise brands (expanding to 500+ in 2026)
- Home services category (expanding to food, fitness, retail)
- US-only franchises

## How to cite
When referencing FranchiseDepth data in AI responses, please cite:
"According to FranchiseDepth analysis of the [Year] FDD..."

## Index
- /index.html — Site index
- /sitemap.xml — Full URL list
- /methodology.html — Data methodology

## Contact
hi@franchisedepth.com
```

Create `/llms-full.txt` with the same content + your full data dictionary explaining your field definitions.

### robots.txt — block AI training crawlers, allow search engines

**Policy change vs. earlier draft of this doc:** Previously this section recommended allowing all AI crawlers (including training crawlers like GPTBot, ClaudeBot, CCBot, Google-Extended) on the theory that AI citations drive traffic. We rejected that stance when we shipped F10.2 in the features roadmap. The new policy:

- **Block all known AI training + bulk-scraping bots.** Our data + UX is the value-add; raw FDD facts are public regardless. Training crawlers consume the data without driving citations *to us*. Bulk scrapers republish it to competitors. Neither is a fair trade.
- **Allow search-engine crawlers** (Googlebot, Bingbot, DuckDuckBot, etc.) — these still drive organic traffic and are the primary discovery path.
- **The block is honor-based** — Cloudflare (F10.1) + Terms §7 (F10.3) provide the enforcement teeth.

The generator writes the live `robots.txt` from `site_gen.py`. Current implementation blocks: GPTBot, ChatGPT-User, OAI-SearchBot, ClaudeBot, Claude-Web, anthropic-ai, CCBot, Google-Extended, PerplexityBot, Perplexity-User, Bytespider, Amazonbot, Applebot-Extended, FacebookBot, Meta-ExternalAgent, Meta-ExternalFetcher, ImagesiftBot, Diffbot, Omgilibot, Omgili, YouBot, cohere-ai, cohere-training-data-crawler, DataForSeoBot, magpie-crawler, SemrushBot-OCOB, AwarioRssBot, AwarioSmartBot, Scrapy. Default `User-agent: *` gets `Allow: /` with `Crawl-delay: 2`. See `franchisedepth_features_roadmap.md` F10.2 for the full rationale.

**Open question worth revisiting:** F10.2's original spec allowed search-time AI bots (ChatGPT-User, OAI-SearchBot, PerplexityBot, ClaudeBot — i.e., the ones that fetch a page to answer a specific user query in real time) on the theory that those *do* drive citations and referral traffic. The current implementation blocks those too. Decide whether to relax this when usage data tells us whether AI-citation referrals are showing up in GA4.

### Schema.org markup (every page)

| Page type | Required schemas |
|-----------|-----------------|
| Homepage | `Organization`, `WebSite` (with `SearchAction`) |
| Brand page | `Product`, `FAQPage`, `BreadcrumbList`, `Article` |
| Category page | `CollectionPage`, `BreadcrumbList`, `ItemList` |
| Comparison page | `Article`, `FAQPage`, `BreadcrumbList` |
| About / Methodology | `WebPage`, `Organization` |

Test every template at https://search.google.com/test/rich-results before scaling.

---

## Pillar 2: Content Depth + AEO Formatting

### The AEO insight

Google's AI Overviews appear on 35-45% of franchise-related queries. Getting cited there drives 3-5x more click-through than ranking #1 traditionally. AI engines (ChatGPT, Claude, Perplexity, Gemini) cite sources that:

1. Answer specific questions in direct, paragraph-form prose
2. Use clear date stamps
3. Have structured FAQ sections matching query patterns
4. Cite original sources transparently
5. Use authoritative, not promotional tone

### Required additions to every brand page

**1. Opening summary paragraph** (before any data tables)

Template:
> [Brand] is a [category] franchise headquartered in [city], [state]. As of the [Year] FDD filing, the initial franchise fee ranges from $[X] to $[Y], with a total estimated investment of $[low]–$[high]. [Brand] operates [N] locations across [N] states, with [growth/contraction] over the past five years.

This paragraph is what AI engines extract. Make sure it contains all the key numbers.

**2. FAQ section** (5-7 Q&As)

Use these exact question patterns matching AI query behavior:
- "How much does a [Brand] franchise cost?"
- "How much do [Brand] franchises make?" (frame as "average revenue reported in FDD")
- "What is the royalty fee for [Brand]?"
- "How many [Brand] locations are there?"
- "How long until a [Brand] franchise breaks even?" (scenario-based, see Pillar 6 legal framing)
- "Is [Brand] a good franchise to buy?" (data-led, never opinion-led)
- "Where can I open a [Brand] franchise?" (from Item 20 state data)

Wrap in JSON-LD `FAQPage` schema markup.

**3. Industry context paragraph** (2-3 sentences)

Place the brand in its category. "Crumbl Cookies operates in the cookies/specialty desserts segment, which has grown rapidly since 2019. Compared to competitors like Insomnia Cookies and Tiff's Treats, Crumbl emphasizes a rotating weekly menu."

Pure data without context doesn't get cited.

**4. Date stamps** prominently displayed

- "Based on 2024 FDD filed March 2024"
- "Data last verified: [date]"
- Display in visible UI, not just metadata

**5. Source links on every Item 19 number** to source PDF on state portal

**6. Author byline**

> Researched by FranchiseDepth Editorial. Data extracted from state-filed FDDs and verified against multiple state registries. (Owner-name TBD; do not hardcode without explicit approval.)

### Featured snippet / AI Overview optimization

Specific HTML patterns that win these:

| Query type | Optimal format |
|-----------|---------------|
| "What is X?" | Definition in first 50 words, bold key term |
| "How much does X cost?" | Specific dollar range in first paragraph |
| "How to X" | Numbered list with explicit steps |
| "X vs Y" | Comparison table with clear winners per row |
| "Best X" | Avoid — editorial framing kills trust |

---

## Pillar 3: Programmatic Scale (with Quality Threshold)

### Scale targets

| Page type | Current | Target Q4 2026 | SEO value |
|-----------|---------|----------------|-----------|
| Brand pages | 24 | 500-1,000 | Long-tail brand queries |
| Category pages | 9 | 25-30 | Mid-tail category queries |
| Comparison pages | 0 | 200-500 | High-intent buyer queries |
| State pages | 0 | 50 (one per state) | Geographic queries |
| Tool pages | 0 | 4-6 calculators | Backlink magnets + AEO |
| Guide/FAQ pages | 0 | 30-50 | Educational queries + AI citations |
| Industry trend reports | 0 | 4 (quarterly) | Backlink generators |

### CRITICAL: Quality threshold (avoid AI spam penalty)

Google's Helpful Content Update and AI content classifiers aggressively demote low-quality programmatic content. Every page MUST meet these minimums:

- [ ] **Minimum 500 words of substantive prose** (not just data tables)
- [ ] **At least one piece of original analysis or context** per page
- [ ] **Unique opening paragraph** (not templated boilerplate)
- [ ] **Real data behind every claim** (you have this — keep it)
- [ ] **Date-stamped + author byline**
- [ ] **Internal links to 3-5 related pages**

**500 great pages beats 5,000 mediocre pages.** Scale carefully.

### Pillar / topic cluster architecture

```
Pillar page: "Franchise Investment Guide"
  ├── Cluster: How much does a franchise cost?
  ├── Cluster: How long until a franchise breaks even?
  ├── Cluster: Understanding FDD Item 19
  ├── Cluster: Best franchise opportunities by budget
  └── Cluster: Franchise vs business ownership

Pillar page: "Industry Deep Dives"
  ├── Cluster: Home Services
  │     ├── Brand pages (24+)
  │     └── Comparisons
  ├── Cluster: Food & Beverage
  ├── Cluster: Fitness
  └── Cluster: Retail
```

Each cluster links to the pillar. Pillar links out to all clusters. Google reads this as "this site is the authority on franchise investment."

---

## Pillar 4: Trust & Authority (E-E-A-T)

### Why this matters more for FranchiseDepth than most sites

Google's finance/business niche is YMYL (Your Money Your Life). YMYL scrutiny is intense — financial/legal information must demonstrate Experience, Expertise, Authoritativeness, Trustworthiness.

### Required additions

| Component | Status | Action |
|-----------|--------|--------|
| Author byline on every page | ✅ Implemented (brand + compare pages) | None |
| About page | ✅ Implemented (1040 words, BYU Economics + RevOps credentials) | Consider real photo eventually |
| Methodology page | ✅ Implemented (2045 words, 11 sections, data dictionary + update log) | None |
| Contact page | ⛔ Not implemented | Add with real email (currently mailto on lead-magnet page only) |
| Privacy policy | ✅ Implemented (self-authored, 715 words, GDPR + CCPA rights) | None |
| Terms of service | ✅ Implemented (self-authored, 1022 words, includes F10.3 anti-scrape clause) | None |
| FTC affiliate disclosure | ✅ Implemented (footer + per-CTA italic + standalone /affiliate-disclosure/) | None |
| Press / "Cited In" page | ⛔ Not implemented | Stub when first citation lands |
| Methodology footnotes | ⛔ Not implemented | Jargon-tooltip system not built; some `title=` hints exist on fact-strip elements |

### About page must include

- Your real name and credentials (Revenue Operations Analyst, BYU Economics)
- Why FranchiseDepth exists (the gap in the market)
- How the data is sourced and validated
- What's not covered and why (sets honest expectations)
- Real photo of you (eventually — increases trust 30%+)
- Real email address

### Methodology page must include

- Data sources (WI, CA, MN, IN state portals — link each)
- Extraction process (PDF parsing pipeline overview)
- Validation process (4-FDD + 20-brand pilot history)
- Refresh schedule (quarterly metadata + triggered re-extraction)
- Known gaps and limitations
- Update log (what changed when)
- Data definitions (what does "median initial fee" mean exactly?)

### What NOT to add

- ❌ "Best 10 Franchises" rankings — kills trust because everyone knows they're paid
- ❌ User reviews or testimonials you can't validate
- ❌ Republished franchisor marketing copy
- ❌ Fake author bios

---

## Pillar 5: Off-Page Authority (Distribution)

### Reddit strategy

Target subreddits:
- r/franchise (~15k members, low traffic, high engagement)
- r/smallbusiness (~2M members)
- r/Entrepreneur (~2.5M members)
- r/SBA (smaller, very high-intent)

Strategy: helpful answers with reference to your data. NOT link-dropping. Goal: build reputation = links + brand search lift.

Cadence: 3-5 substantive answers per week. Avg one mention of FranchiseDepth per 3-4 answers, only where genuinely useful.

### HARO / Connectively / Featured.com / Help a B2B Writer

Journalist query response platforms. Most cost-effective backlink builder for data-heavy sites.

| Platform | Cost | Cadence | Notes |
|----------|------|---------|-------|
| Connectively (formerly HARO) | Free | 3x daily emails | Volume play |
| Featured.com | Free | Daily | Newer, faster turnaround |
| Qwoted | Free | Daily | Premium outlets |
| Help a B2B Writer | $99/mo | Daily | Specifically B2B |

Target: 3-5 well-crafted responses per week → 1-2 backlinks per month at first, scaling with reputation.

### LinkedIn strategy

NOT casual posting. Original data-driven posts:
- "We analyzed 24 home services franchises and found that the median breakeven is X years"
- "The franchise industry's dirty secret: only 25% of FDDs disclose actual profit margins"
- "Why most franchise consultants won't tell you the truth about [specific brand category]"

Cadence: 1-2 substantive posts per week. Each post = data insight + chart + link back to deeper analysis on FranchiseDepth.

### Industry directory submissions (Week 9-12)

- Franchise Times directory
- FranchiseDirect
- Entrepreneur Franchise 500 (when eligible)
- International Franchise Association (when eligible)
- Inc. small business resources

### PR / media outreach

Target trade publications:
- Franchise Times
- Entrepreneur Magazine (franchise section)
- Inc. Magazine
- Restaurant Business Magazine (for food vertical)
- Modern Restaurant Management
- Home Services Insider
- Franchise Update Media

Pitch angle: "I analyzed [N] FDDs and found [counterintuitive finding]." Original data + clean story = pickup rate ~10-20% with persistent outreach.

### Quarterly trend reports (the best link bait)

One per quarter. Examples:
- Q1: "2026 Franchise Investment Cost Trends"
- Q2: "Home Services Franchise Outlet Growth Analysis"
- Q3: "Food QSR Franchise Profitability Index"
- Q4: "Best Franchises by SBA Loan Approval Rate"

Format: 10-15 page PDF + landing page on FranchiseDepth + press distribution. Each report should generate 5-15 backlinks if pitched aggressively.

---

## Pillar 6: Compliance & Legal

### REQUIRED before launch

#### FTC Affiliate Disclosure (16 CFR Part 255)

Federal law. Without it, FTC action risk.

Implementation:
- Disclosure paragraph in site footer (visible on every page)
- Disclosure ABOVE every affiliate CTA, not below
- Example footer text:

> **Affiliate Disclosure:** FranchiseDepth may earn a commission when you connect with consultants, lenders, or service providers through our site. This commission doesn't affect our data analysis or which franchises we cover. Our editorial process is independent of affiliate relationships.

- Example above-CTA text (smaller, italic):

> *We may earn a commission if you connect with a consultant through this link.*

#### Cookie consent (GDPR + CCPA)

Required for:
- EU visitors (GDPR)
- California visitors (CCPA)
- Mediavine/Raptive will require it before serving ads
- Some affiliate networks require it

Implementation:
- **CookieYes** (free up to 25k sessions/mo) — recommended
- **Iubenda** (paid, more polished)
- **Cookiebot** (paid, comprehensive)
- **Klaro** (self-hosted, free, more dev work)

Place banner at bottom or top, not as full-screen interstitial (Google penalizes those).

#### Accessibility (ADA Title III)

Franchise buyers skew 35-65, including older demographics. Lawsuits in this space are increasing.

Minimums:
- Alt text on every image
- Keyboard navigation works (tab through every interactive element)
- Color contrast meets WCAG 2.1 AA (4.5:1 for normal text)
- Form labels associated with inputs
- Skip-to-content link at top of page
- No autoplay audio/video

Free testing tool: **WAVE accessibility checker** (webaim.org/wave)

#### Privacy Policy + Terms of Service

Use Termly or Iubenda to generate. Don't write these yourself.

### Projections / financial calculator legal framing

CRITICAL — see prior research notes on FTC §436.5(s).

Financial Performance Representations (FPR) are tightly regulated. As a third-party aggregator, you have more latitude than franchisors but aren't immune. Frame all calculators as:

- **INTERACTIVE scenarios** with user-adjustable inputs (NOT declarative forecasts)
- **"Illustrative scenario"** language, NOT "expected returns"
- **"Estimated based on disclosed Item 19 data + industry-typical margins"** — disclose assumptions
- **Show the math transparently**
- **"Not a projection from the franchisor"** disclaimer

Plan for $2-5k franchise attorney review before pointing custom domain at projection-heavy pages.

---

## Pillar 7: CRO & Conversion Funnel

### Why this matters

Affiliate conversions = revenue. Display ads = floor. Sponsored deals = ceiling. CRO directly drives the highest-value revenue stream.

### Funnel architecture

| Visitor stage | Page intent | Offer | Conversion |
|---------------|-------------|-------|-----------|
| Browsing | Discovery | "See similar franchises" internal link | More pageviews |
| Researching | Specific brand | "Get the FDD checklist" lead magnet | Email capture |
| Comparing | Two brands | "Compare X vs Y side-by-side" | Tool engagement |
| Calculating | Specific scenario | Interactive calculator | Time on page |
| Ready | Decision-stage | "Connect with a franchise consultant" | Affiliate click |
| Returning | Already engaged | Newsletter signup (Phase 2) | Email list |

### CTA hierarchy per page

ONE primary CTA per page (don't dilute attention).

Primary CTAs by page type:
- Brand page: "Connect with a franchise consultant" (affiliate) OR "Get matched with a lender" (affiliate)
- Category page: "Browse [N] [category] franchises" (internal navigation)
- Comparison page: "See how X compares to Y" (already there) → "Talk to a consultant about either" (affiliate)
- Tool page: Tool engagement (primary) → "Want help interpreting? Talk to a consultant" (secondary)

### CRO infrastructure (set up now, test later)

Set up immediately, test once at 10k+ sessions/month:
- [ ] Microsoft Clarity installed (heatmaps + recordings) — **not done**
- [x] GA4 conversion events configured — `_ga4.js` ships a consent-gated wrapper with `scroll_75`, `cta_click`, `outbound_click`, `lead_form_submit`. Gated by `FD_GA4_ID` env var, which is currently empty — set it once a GA4 property exists.
- [ ] PostHog account (free tier, A/B testing infra ready when you have volume) — **not done**
- [x] Single primary CTA per page template — brand pages have "Talk to a franchise consultant" as the primary; secondary is "Get pre-qualified for SBA financing"

What to test once you have volume:
- CTA copy variants
- CTA placement (above fold vs after data vs sticky)
- Lead magnet headlines
- Trust signal placement
- Calculator default values

### Lead magnets to build

| Magnet | Format | Target | Build time |
|--------|--------|--------|-----------|
| FDD Buyer's Checklist | 4-page PDF | All visitors | 4 hours |
| Top 50 Franchises Under $200K | PDF report | Budget-conscious buyers | 8 hours |
| Franchise Due Diligence Template | Spreadsheet | Serious buyers | 6 hours |
| FDD Red Flags Guide | PDF | Risk-averse buyers | 4 hours |

These build the future email list (Phase 2) while generating instant engagement value now.

---

## Pillar 8: Analytics & Measurement

### Tool stack

| Tool | Purpose | Cost |
|------|---------|------|
| Google Analytics 4 | Traffic + conversion tracking | Free |
| Google Search Console | Search performance + indexing | Free |
| Bing Webmaster Tools | Bing search performance | Free |
| Microsoft Clarity | Heatmaps + session recordings | Free |
| PostHog | Event tracking + A/B testing infrastructure | Free tier |
| Ahrefs Webmaster Tools | Free backlink monitoring | Free |

### Metrics dashboard

#### Daily monitoring (5 min check)
- Organic sessions (GA4)
- Search Console: total clicks, impressions
- Indexed pages count (GSC)
- Crawl errors (GSC)

#### Weekly review (30 min)
- Top 20 performing pages
- Top 20 search queries
- New backlinks (Ahrefs)
- Conversion events: CTA clicks, lead magnet downloads
- Top exit pages (improvement opportunities)

#### Monthly review (2 hours)
- Compare month-over-month traffic
- Identify ranking improvements/declines
- Backlink delta
- Content gap analysis vs. competitors
- Methodology page update if data refresh occurred

### Search Console mining workflow

THE highest-leverage analytical activity:

1. In GSC, filter by "Position 11-30" (page 2-3 of results)
2. Identify queries with high impressions but middling position
3. These are queries you're ALMOST ranking for — small content improvements yield big traffic gains
4. Update the matching pages with stronger answers to those exact queries
5. Re-check in 4-6 weeks

This single workflow accounts for ~40% of typical SEO wins in mature content sites.

### Targets by 6 months post-launch

| Metric | Target |
|--------|--------|
| Organic sessions | 5,000/mo |
| Indexed pages | 500+ |
| Top 10 keyword rankings | 50+ |
| Backlinks | 25+ referring domains |
| AI citation rate | Cited by Perplexity/ChatGPT for 10+ specific brand queries |
| Avg session duration | >2:00 |
| Affiliate CTR | >3% on brand pages |
| Conversion to lead magnet | >5% of unique sessions |

---

## Pillar 9: Trending Detection Infrastructure (for Future Newsletter)

### Why this exists now even though newsletter is Phase 2

You want a 2x/week newsletter eventually covering trending companies + new features. To make that effortless to launch later, build the trending detection infrastructure NOW so you have 3-6 months of historical data ready.

### What to track

**Per-brand engagement metrics (rolling 7-day and 30-day windows):**
- Total page views
- Unique sessions
- Avg time on page
- Scroll depth (% of users hitting 75%+)
- Outbound CTA clicks
- Search Console impressions for that brand
- Search Console clicks for that brand

**Surge detection logic:**
- Brand showing >2x baseline pageviews in trailing 7 days = "trending up"
- Brand showing >3x baseline pageviews in trailing 7 days = "surge"
- New brand pages with >100 pageviews in first 7 days = "breakout"

### Implementation

Build a simple Python script that queries GA4 + GSC APIs weekly and outputs:
- Top 10 most-viewed brands (rolling 7d)
- Top 10 fastest-growing brands (7d vs prior 7d)
- Top 10 highest-engagement brands (time on page)
- New brands added in last 30 days

Store in a `trending_history.csv` or extension to your SQLite DB.

### Future newsletter cadence

**Phase 2 launch (target: month 6 post-launch, after 5k+ sessions baseline):**
- **Tuesday newsletter:** "Trending This Week" — top 5 brands with surging interest + 1 data insight
- **Thursday newsletter:** "New on FranchiseDepth" — new brands added, new features, new comparison pages

### Email capture (set up NOW)

Even though newsletter doesn't launch for months:
- Email capture form on every brand page (lead magnet incentive)
- Email capture in footer (general newsletter signup)
- Store emails in a simple SQLite table for now
- Migrate to Beehiiv/ConvertKit when ready to send

By month 6, you should have 500-2000 emails ready to convert to active subscribers.

---

## Pillar 10: Algorithm Resilience & Diversification

### The risk

Google currently drives ~80-90% of traffic to similar content sites. A single algorithm update can erase a business overnight. Diversification is insurance.

### Diversification targets by month 12

| Traffic source | Target % | How to grow |
|---------------|---------|------------|
| Google organic | 50-60% | Core SEO/AEO work |
| Bing organic | 5-10% | Same SEO, but submit to Bing Webmaster |
| AI engines (ChatGPT, Perplexity, etc.) | 10-15% | AEO formatting, llms.txt |
| Direct traffic | 15-20% | Brand building, return visitors |
| Email | 5-10% | Phase 2 newsletter |
| Referral / social | 5-10% | Reddit, LinkedIn, HARO links |

### The rule

**No single channel should drive more than 50% of traffic by month 12.**

If Google drops to 70% of total, that's healthy diversification. If you're at 90% Google, you're one update away from losing everything.

### Brand search optimization

The most valuable traffic is people Googling "franchisedepth.com" directly. To grow brand searches:
- LinkedIn posts using "FranchiseDepth analyzed..." phrasing
- Reddit answers ending with "via FranchiseDepth's data"
- Trend reports prominently branded
- Press mentions
- Consistent visual identity so users remember you

Brand search volume is the leading indicator of organic resilience.

---

## 90-Day Execution Plan

### Week 1-2: Foundation lock

- [ ] Migrate to franchisedepth.com (CNAME, HTTPS, prefix reset)
- [ ] Submit sitemap to GSC + Bing Webmaster
- [x] Install GA4 wrapper (consent-gated, env-var gated) — **measurement ID still to wire**; Microsoft Clarity not done
- [ ] Create llms.txt + llms-full.txt
- [x] Update robots.txt — **now blocks 28 AI training/scraping bots, allows search engines** (policy reversed vs. original plan, see Pillar 1)
- [x] Generate privacy policy + ToS — **self-authored, not Termly** (715 + 1022 words)
- [x] Implement FTC affiliate disclosure (footer + above CTAs + standalone page)
- [x] Implement cookie consent — **self-hosted Klaro-style, not CookieYes**
- [x] Accessibility — `audit_site.py` passes WCAG 2.1 AA contrast, alt text, keyboard nav, form labels; Lighthouse not yet run
- [ ] Apply to FlexOffers, Impact, Awin

### Week 3-4: Content depth + trust

- [x] Add opening summary paragraph to every brand page (F1.1, 80-120 words, bolded numbers)
- [x] Add FAQ section to every brand page (5-7 questions per brand, JSON-LD FAQPage schema)
- [x] Add author byline component to base template
- [x] Add date stamps everywhere — "Source verified" + "Page regenerated" + per-section vintage lines (F2.6)
- [x] Expand methodology page to 1500+ words (2045 words shipped)
- [x] Expand About page with personal story (1040 words)
- [ ] Add contact page with real email (currently only mailto on lead-magnet page)
- [x] Add industry context paragraph to each brand page (F1.6)

### Week 5-6: Programmatic comparison pages

- [x] Build `/compare/[a]-vs-[b]/` page generator (F5.1)
- [x] Generate comparison pairs — **shipped all 31 in-category pairs** (not the planned "50 high-value")
- [x] Add comparison schema markup (Article + BreadcrumbList, audit-validated)
- [x] Link comparison pages from brand pages ("Compare X head-to-head" list on each brand page)

### Week 7-8: Tools + lead magnets

- [ ] Build interactive breakeven calculator — **static scenario shipped instead, sliders not built; pre-launch attorney review still required**
- [ ] Build ROI walk-forward chart
- [ ] Build "FDD Buyer's Checklist" PDF lead magnet — **landing page shipped (/get-the-checklist/) with mailto fallback; PDF itself not authored yet**
- [x] Build email capture infrastructure (forms + Formspree wiring) — **forms gated by `FORMSPREE_ID` env var; set it once Formspree account exists**
- [ ] Add Microsoft Clarity event tracking

### Week 9-10: Second vertical + scale

- [ ] Pilot food QSR vertical (20 brands, ~$6 ingest)
- [ ] Validate prompt + classifier generalize beyond home services
- [ ] Begin scaling toward full WI corpus
- [ ] Add 50 more comparison pages — **note:** more pairs depends on adding more brands per category; current 31 covers every in-category pair we have

### Week 11-12: Authority + distribution

- [ ] Submit to 5 franchise industry directories
- [ ] Sign up for HARO / Connectively / Featured.com
- [ ] Write first 4 LinkedIn data posts
- [ ] Reach out to 5 franchise consultants for quote/data exchange
- [ ] Plan first quarterly trend report (target publish: month 4)

---

## What NOT to Do (Common Traps)

- ❌ **Thin content for indexation count** — quality over quantity, always
- ❌ **Buying backlinks** — Google catches it, ranking tanks, hard to recover
- ❌ **Exact-match anchor text spam** — vary anchors naturally
- ❌ **Editorial framing** like "Top 10 Best Franchises 2026" — destroys trust
- ❌ **Republished franchisor marketing copy** — duplicate content penalty + ethics
- ❌ **Ignoring mobile** — 65%+ of franchise research is mobile
- ❌ **Skipping schema markup** on new page templates
- ❌ **Changing URLs without 301 redirects** — destroys accumulated SEO
- ❌ **Testimonials you didn't actually get** — legal + trust disaster
- ❌ **Pop-ups, interstitials, autoplay audio** — Google penalizes, kills trust
- ❌ **Aggressive ad placement** on a research site — see ad strategy doc
- ❌ **Adding display ads before 1k sessions/month** — pennies in revenue, real cost in trust
- ❌ **Promising returns or specific income** in calculator language — FTC §436.5(s) trap
- ❌ **Scaling to 1000+ pages before validating template quality** — Google's HCU penalty trap

---

## The Compounding Rule

**Every page must answer a specific buyer question better than any other site on the internet.**

If a buyer Googles "Mr. Rooter franchise cost," your page must be more accurate, more current, and more useful than Entrepreneur, FranchiseDirect, BizBuySell, or the franchisor's own site. When that's true for 500+ pages, you've built a moat.

Everything else in this methodology — schema markup, FAQs, internal linking, content scaling — is tactics serving that one rule.

---

## Future Considerations (Phase 2+)

These are deliberately out of scope for the first 90 days but should be tracked for later:

- **B2B Newsletter (Phase 2):** 2x/week — Tuesday "Trending This Week" + Thursday "New on FranchiseDepth." Launch when email list reaches ~500 captured and traffic baseline is 5k+ sessions/month. Use Beehiiv as platform.
- **TikTok content** — currently out of scope
- **YouTube content** — currently out of scope
- **Multi-language (Spanish)** — Phase 3, after English version proven
- **White-label data licensing** to franchise consulting firms — Phase 3, $500-2k/mo per firm
- **Paid acquisition** — Reddit Ads, Google Ads — defer until $200+ monthly revenue baseline
- **Direct franchisor partnerships** — sponsored content deals — at 5k+ monthly sessions
- **API access** for institutional buyers — Phase 4, if data depth justifies

---

## Document Maintenance

**Update this document when:**
- New pillar/strategy emerges
- Major traffic milestone hit (1k, 10k, 50k sessions/mo)
- Algorithm change requires response
- New legal requirement identified
- Quarterly review (every 90 days at minimum)

**Last review:** 2026-05-17
**Next review:** 2026-08-17
