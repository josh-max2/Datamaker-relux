# FranchiseDepth — public franchise economics database

Buyer-facing database of franchise financial performance data, extracted from publicly filed Franchise Disclosure Documents (FDDs). Monetized via affiliate referrals (franchise consultants + SBA preferred lenders) and a lead-magnet PDF.

- **Live site:** https://franchisedepth.com
- **Hosting:** GitHub Pages from `docs/` on `main`, custom domain via Porkbun, HTTPS active
- **Scope (2026-05-18):** 123 brands · 794 pages · 67 brands with Item 19 · 926 Item 19 records · 12,805 Item 20 location rows · 8 pillar guides · 51 state pages · 275 static compare pages
- **Single source of truth:** [`PROJECT_TRACKER.md`](./PROJECT_TRACKER.md) — read this first
- **Cross-session resume doc:** [`HANDOFF.md`](./HANDOFF.md)

---

## What's in this repo

```
parser/
├── PROJECT_TRACKER.md              # ★ Master tracker — domain, features, ops, changelog
├── HANDOFF.md                      # Cross-session pickup doc
├── README.md                       # This file
├── fdd_tool_build_spec.md          # Original build spec (preserved for context)
├── franchisedepth_methodology_v2.md
├── franchisedepth_features_roadmap.md
├── fdd-tool/                       # Python pipeline (extraction + scraper + DB + site gen)
│   ├── src/
│   │   ├── pdf_utils.py            # PDF text + section finder + cover detector
│   │   ├── prompts.py              # Claude extraction prompts (v1 + v2)
│   │   ├── claude_client.py        # Anthropic SDK wrapper
│   │   ├── extract.py              # v1 vision pipeline (fallback)
│   │   ├── extract_v2.py           # v2 single-prompt Haiku pipeline ($0.17/FDD avg)
│   │   ├── db.py                   # SQLite schema
│   │   ├── site_gen.py             # SQLite -> docs/ HTML (Jinja2)
│   │   ├── state_map.py            # Per-brand US tile-grid heatmaps (SVG)
│   │   ├── scrapers/wisconsin.py   # WI DFI Playwright scraper
│   │   ├── scrapers/minnesota.py   # MN CARDS portal scraper (next-state expansion)
│   │   ├── lead_magnet/            # FDD Buyer's Checklist PDF source + build
│   │   └── templates/              # brand.html, index.html, category.html, ...
│   ├── scripts/                    # Audit, ingest, validation, snap scripts
│   ├── output/                     # Per-FDD JSON extractions (committed — facts, not text)
│   ├── data/                       # Source PDFs (gitignored — copyright)
│   └── franchise.db                # SQLite (gitignored — regenerable from output/)
└── docs/                           # Generated static site (GitHub Pages source)
    ├── index.html                  # Homepage w/ sortable brand table + filter toggles
    ├── franchise/{slug}/           # 123 brand pages (calculator + Item 19 + heatmap + ...)
    ├── compare/                    # Interactive multi-brand picker + 275 static A-vs-B pages
    ├── industries/, state/, recent/, guides/, ...
    └── lead-magnets/fdd-buyers-checklist.pdf
```

## Key features

**Per-brand pages** include a sortable Item 19 table, US-state outlet heatmap (89% of brands), 10-year ROI walk-forward chart, peer comparison links, and an interactive cost calculator with:
- Pessimistic / Median / Optimistic preset buttons sourced from that brand's Item 19 quartile distribution
- Live percentile-rank context ("Your $X is at the Yth percentile of {brand} franchisees")
- Itemized Y1 money-flow breakdown
- Industry-benchmark callouts (royalty/marketing/investment vs same-category peer medians)
- Similar-brand calculator cross-links (top 4 peers by outlet count)
- Shareable URL (query-string state sync of all 16 inputs)

**Site-wide:**
- Sortable category tables, "For your budget" filter, industry chip nav, header typeahead search
- Closure-rate badges (green/yellow/red tier), data-vintage labels per section
- Lead capture (Formspree) → FDD Buyer's Checklist PDF (10 pages, 178 KB)
- Sitemap submitted to GSC (791 pages discovered), IndexNow pinged (Bing / Yandex / Seznam / Naver)
- GA4 + Microsoft Clarity, consent-gated

## Local development

```powershell
cd fdd-tool

# Install deps
uv sync
uv run playwright install chromium  # only if running scrapers

# Re-ingest existing JSONs into SQLite
uv run python scripts/ingest_outputs.py

# Regenerate the static site
uv run python -m src.site_gen

# Commit + push to redeploy
git add docs/
git commit -m "Regenerate site"
git push
```

## Pipeline economics (2026-05-18)

- **v2 extraction:** $0.17/FDD avg (single-prompt Haiku, text-only) — beats $0.25 target
- **v1 fallback:** $0.23–0.30/FDD (Haiku vision, only when v2 quality gate fails)
- **+90 brands from baseline:** ~$25–30 API-equivalent (effective $0 on Max plan)
- **Hosting:** $0 (GitHub Pages)
- **Domain:** Porkbun (`franchisedepth.com`, 2-year registration)

See `PROJECT_TRACKER.md` §0 for the current operating snapshot and §13 changelog for a chronological ship log.
