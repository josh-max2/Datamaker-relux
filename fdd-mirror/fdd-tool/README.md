# fdd-tool

Extracts structured financial data from Franchise Disclosure Documents (FDDs) using Claude.

**Project context, validation history, and decision log:** see [../HANDOFF.md](../HANDOFF.md).
**Original build spec:** see [../fdd_tool_build_spec.md](../fdd_tool_build_spec.md).

## Layout

```
fdd-tool/
├── main.py             # CLI entry point
├── pyproject.toml      # uv-managed deps
├── .env                # ANTHROPIC_API_KEY (gitignored)
├── src/                # The pipeline
│   ├── pdf_utils.py    # text + page rasterization + FDD section + cover detection
│   ├── prompts.py      # extraction prompts (system + 5 items + metadata)
│   ├── claude_client.py # SDK wrapper with caching + streaming
│   ├── extract.py      # orchestrator: PDF -> 6 JSON files
│   └── scrapers/
│       └── wisconsin.py # WI portal Playwright scraper with dedup + rate limit
├── scripts/            # One-off validation, inspection, and preflight scripts
├── data/               # Source PDFs (gitignored — see HANDOFF for sourcing)
│   └── preflight/      # 19 modern MN-filed FDDs used for the OCR preflight survey
└── output/{pdf_stem}/  # Extraction outputs, namespaced per PDF (gitignored)
```

## Run

```bash
# Default fixture (Crumbl 2023 — must be downloaded into data/ first)
uv run python main.py

# Specific PDF
uv run python main.py data/your_fdd.pdf

# Scrape a WI franchisor (uses src/scrapers/wisconsin.py)
uv run python -c "from src.scrapers.wisconsin import WisconsinScraper, latest_active
from pathlib import Path
with WisconsinScraper() as s:
    filings = s.search('Servpro')
    print(s.download(latest_active(filings), Path('data/wi_scrape')))"

# Scripts (one-offs) — always run from the fdd-tool/ directory:
uv run python scripts/preflight_analyze_v2.py
uv run python scripts/pilot_wi_home_services.py    # 20-brand pilot batch
```

Each extraction takes ~30-90 seconds and costs ~$0.30-$0.50 in Claude API calls.

## Status

Phase 0 (extraction validation) complete. Phase 1 (Wisconsin Playwright scraper) is the next build. See HANDOFF for full state.
