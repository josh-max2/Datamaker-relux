# Search Console mining workflow

**Purpose:** Identify queries where {{site}} is *almost* ranking (page 2-3 of Google results) so we can update the matching pages to win them.

**Frequency:** Run weekly once GSC has accumulated ≥4 weeks of data. Skip during the first 8 weeks post-launch — the data won't have stabilized.

**Time:** 30-45 min/week steady-state.

---

## The workflow

### 1. Pull positions 11-30 queries

In Google Search Console:
- **Performance** report → date range = "Last 3 months"
- Apply filter: **Position** → **Greater than 10**, **Less than or equal to 30**
- Sort by **Impressions** descending
- Export the top 100 rows as CSV

These are queries where:
- Google considers our page relevant enough to surface on page 2-3
- We're getting impressions but few clicks
- A small content improvement can push us into the top 10

### 2. Triage the export

For each row, decide one of three actions:

| If… | Action |
|---|---|
| Query has no matching page on our site | Note for "new content needed" backlog |
| Query matches an existing page but the page doesn't directly answer the query phrase | Update the page — usually a new H2 + paragraph |
| Query is irrelevant (e.g., misspelling, off-topic) | Skip |

### 3. Tier-1 fixes: same-page updates

For each query where we have an existing page that almost ranks:
- Open the page (brand, compare, or category)
- Find the section that *should* match the query
- Add an explicit phrase matching the query intent — usually as an `<h3>` plus a 2-3 sentence answer paragraph
- If the query has a clear question form, consider adding it to the page's FAQ list

Example: "how much does a cleaning franchise cost" pulling Anago's page to position 14 → on Anago's page, add an H3 "Anago franchise cost" with a tight summary of fees + investment range.

### 4. Tier-2 work: new pages or guides

For queries with no obvious page:
- Add to the guides backlog
- Prioritize by impressions × estimated CTR delta

### 5. Track + recheck

Maintain a `gsc_optimization_log.csv` (per query):
```
query, target_page, change_date, position_before, position_after_4wk, impressions_before, impressions_after_4wk
```

Re-check positions 4-6 weeks after each fix. Google needs that long to re-evaluate and re-rank.

---

## Common patterns to look for

| Query pattern | Likely fix |
|---|---|
| "how much does [Brand] cost" | Brand page needs explicit fee summary in opening paragraph |
| "[Brand] franchise profit" | Item 19 section needs prose summary above the table |
| "[Brand] vs [Other]" | Generate compare page if missing; check schema if exists |
| "best [category] franchise" | Avoid — we don't do editorial rankings. Skip these queries. |
| "[category] franchise cost" | Category page needs aggregate cost stats prose |
| "[State] franchise opportunities" | State page should rank — check it exists for that state |
| "how does FDD Item 19 work" | Guides cluster — covered by /guides/understanding-item-19/ |
| "is [Brand] profitable" | Item 19 + closure rate prose summary; never claim profitability directly |
| "[Brand] reviews" | We don't republish reviews; nothing to optimize |
| "[Brand] complaints" | Reframe as Item 20 closure rate + transfer activity disclosure |

---

## What NOT to do

- ❌ Don't keyword-stuff. One natural mention of the target phrase is enough.
- ❌ Don't write "best of" content. Methodology forbids editorial rankings.
- ❌ Don't optimize against queries we can't answer with our data. If we don't have Item 19 for a brand and the query is "[Brand] earnings", the right answer is "this brand doesn't disclose" — not invented numbers.
- ❌ Don't add thin "FAQ" entries just to match a query. The FAQ schema penalty for low-quality FAQ pages is real.
- ❌ Don't change a URL or slug to match a keyword. Keep URLs stable; modify on-page content instead.

---

## Tooling notes

GSC API access (when ready to automate):
- Project the queries-positions report into `scripts/gsc_mine.py`
- Output a weekly priority list to `output/gsc_priorities_{date}.csv`
- Stretch: a Slack/email digest each Monday with the top 10 priorities

We're not on the GSC API yet — manual export is fine until we have ≥6 months of post-launch data.

---

**Last updated:** 2026-05-17
