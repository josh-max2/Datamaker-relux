# Dashboard rebuild — change log & control doc

Living record of the **tabbed dashboard rebuild** executed directly on this mirror
(`docs/dashboard/index.html`). One row per edit cycle: what changed, before/after
shots, verdict. Spec = the "FranchiseDepth — Tabbed dashboard rebuild" spec.

---

## §0 — Scope adaptations (how this run differs from the spec)

The spec was written against the **parser source build** (`scripts/build_dashboard.py`,
`src/templates/style.css`, `src/static/js/*.js`) and **guessed at class names**. This run
edits the **mirror's static `docs/dashboard/index.html` only** — nothing flows back to
parser source or production until the owner approves the design.

| Spec assumption | Reality on this build | Adaptation |
|---|---|---|
| Edit `scripts/build_dashboard.py` + `src/templates/*.css/js` | Mirror is a single static `docs/dashboard/index.html` (4,918 lines) with inline `<style>` + inline `<script>` | Edit the inline blocks in `index.html` directly; split to real `.css`/`.js` only if it clearly helps |
| "Ship each section to production" | Production must stay untouched | "Ship" = commit to this mirror repo (`josh-max2/Datamaker-relux`); robots Disallow + no CNAME stay |
| Tabler icons (`<i class="ti ti-…">`) assumed loaded | **Not loaded** — current UI uses emoji | Add `@tabler/icons-webfont` `<link>` in §1.2 (filter bar is first user) |
| §5 activity feed → header bell in `base.html` | base.html is pre-rendered into this page | §5 = edit the dashboard's inlined header only (spec self-recommends Option A) |
| §4.2 Watchlist badge "5" | No real watchlist | Drop the hardcoded badge in §2 |
| §7.4 update parser `PROJECT_TRACKER.md` | Parser source is out of scope | Defer until owner approves merge-back |
| §8.3 `scripts/_screenshot_matrix.py` | Doesn't exist | `fdd-tool/scripts/_preview_mirror.py` IS that script |
| Filters live in sidebar DOM (`#f-industry` etc.); JS reads them by ID | Same | **Migration strategy: relocate the existing filter controls into the top bar preserving their IDs so the filter engine keeps working, then layer popovers + URL sync on top.** Avoids a broken intermediate (spec anti-pattern #3). |

**Visual-analysis loop:** I cannot post into the `claude.ai/chat/…` web URL (no tool reaches it).
Substitute = inline vision check on every sub-section + an **Opus review subagent** fed the
before/after PNGs once per major section. Same outcome, runs here.

---

## §0.1 — Spec name → real selector translation table

| Spec name | Real selector(s) | Location |
|---|---|---|
| `.dashboard-layout` | `.layout` | HTML 1646 |
| `.dashboard-sidebar` | `aside.sidebar#sidebar` (persona pill, saved views, `.filter-group`×N, mobile handle/close) | HTML 1648–1799 |
| `.dashboard-main` | `main.main` | HTML 1801 |
| `.filter-section` | `.filter-group` | HTML 1677+ |
| filter controls | `#f-search`, `#f-industry`, investment/royalty `.filter-range`, item19, state, outlets, year | inside sidebar |
| active filter chips | `.active-filters #activeFilters` (`.filter-chip`) | HTML 1804; JS ~3055 |
| brands table wrapper | `.results` → `.results-header` + `#results-status` ("Showing N of 631") + table | HTML 1874 |
| drill-down panel | `#drill-panel.drill-panel` | HTML 2032 |
| persona modal | `#persona-modal.persona-modal`; key `fd-dashboard-persona`; auto-opens ~4731 | HTML 2044; JS 3375+ |
| mobile filter FAB | `#mobile-filter-fab.mobile-filter-fab` | HTML 1937 |

### Quadrant removal ledger (§3.4 / §7 — delete HTML + CSS + JS together, one commit)
- **CSS** 1357–1414: `.quadrant-wrap`, `.quadrant-tile`, `.q-head/.q-icon/.q-name/.q-count/.q-desc/.q-egs/.q-egs-empty`, `.quadrant-frame`, `.quadrant-body`, `.quadrant-note`, `.quadrant-active-chip`, `.quadrant-bound`, `@media …{.quadrant-wrap}`
- **HTML** 1850–1858: chart-title "Revenue × royalty matrix…", `.quadrant-frame` → `.quadrant-body` → `#quadrantMatrix.quadrant-wrap`, `.quadrant-note#quadrantNote`
- **JS**: `QUADRANT_BOUNDS`@2072; comment 2607–2608; block 2977–3086 (`quadrantSelected`, `QUADRANTS`, `quadrantOf()`, `renderQuadrant()`, `renderQuadrant` call inside `rerender()`, click handlers on `#quadrantMatrix` + `#quadrantNote`, `quadrantClear`)
- ⚠ Removing only the HTML leaves dead JS that throws on init (`getElementById('quadrantMatrix')` → null). Delete all three layers + the `renderQuadrant()` call site in one pass, then confirm console clean.

### "Corpus Coverage" duplicate (remove in §3.2)
- The "CORPUS COVERAGE" card after the KPIs restates the KPI info (416/631 = 66%, 28 industries). Locate + delete.

---

## Harness & assets (durable)

- **Screenshotter:** `parser/fdd-tool/scripts/_preview_mirror.py <label> [shots] [url_path]`
  - serves `Datamaker-relux/docs` with a handler that strips `/Datamaker-relux`; seeds `fd-theme` + `fd-dashboard-persona=buyer` so the ICP modal never blocks shots; captures console/page errors.
  - presets: `desktop_dark` `desktop_dark_full` `desktop_light` `mobile_dark` `mobile_dark_full` (default = `desktop_dark,desktop_dark_full`).
  - output: `parser/fdd-tool/diag/redesign/<label>_<preset>.png` (untracked).
- **Baseline (do not overwrite):** `diag/redesign/baseline_{desktop_dark,desktop_dark_full,desktop_light,mobile_dark_full}.png` — captured before any edit. ✅ clean, no console errors.
- **Cadence:** vision-check every sub-section (1440 dark fold + full); add light + 390 mobile for layout/typography sections (§3, §6). Opus subagent once per major section.

---

## Execution order & status

| § | Section | Status |
|---|---|---|
| 0 | Harness + baseline + this doc | ✅ done |
| 1 | Foundation — top filter bar (remove sidebar) | ✅ SHIP (Opus reviewed) |
| 2 | Tab navigation skeleton | ☐ |
| 3 | Dashboard tab content (incl. quadrant + corpus-coverage removal) | ☐ |
| 4 | Placeholder tabs (Compare / Watchlist / Reports) | ☐ |
| 5 | Activity feed → header bell dropdown | ☐ |
| 6 | Mobile responsive | ☐ |
| 7 | Migration cleanup (dead CSS/JS) | ☐ |
| 8 | Verification (computed-style audit + screenshot diff) | ☐ |

---

## §1 design decision (owner, 2026-05-25)

**Preserve all power-user features in a "Tools ▾" menu.** The real sidebar holds 8 blocks;
the spec's top bar only homed the 7 filters + 3 actions. Resolution:

- **Left of bar:** 7 filter pills → Industry, Investment, Royalty, Item 19, Filing state, Min outlets, Year (Time Machine moves here).
- **Right of bar:** quick actions `[Risk weights]` `[Export ▾CSV]` + **`Tools ▾`** overflow holding: Mode/persona, Saved views (load/save/delete), My tags, Custom benchmark, Export presets, Bulk lookup, Guided picker.
- **Nothing dropped.** Honors "don't reduce info density for power users."
- **Migration:** relocate existing controls (keep their IDs: `#f-industry`, `#f-search`, `#bench-select`, `#views-select`, etc.) so the filter engine keeps reading them; URL-sync layer added after the structural move is verified.

---

## Change log

<!-- Template:
### §X.Y — <title>  (<date>)
- Goal / Edits (file:line) / Before→After shots / Vision verdict / Console / Opus
-->

### §1 — Top filter bar (remove sidebar)  (2026-05-25)
- **Goal:** remove left sidebar; all filters in a horizontal sticky top bar that persists; relocate every control (preserve IDs so the filter engine is untouched); move Time Machine into a Year pill; preserve all power features in `Tools ▾`.
- **Applied via:** `parser/fdd-tool/scripts/_apply_s1.py` (idempotent; undo = `git -C ../Datamaker-relux checkout docs/dashboard/index.html`). Verification harnesses: `_preview_mirror.py`, `_verify_s1.py`.
- **Edits (all in `docs/dashboard/index.html`):**
  - removed `aside.sidebar#sidebar` (was 1648–1799); removed `.time-machine` from hero (was 1623–1631); moved `#activeFilters` into the bar.
  - inserted `.dashboard-filter-bar` before `.layout`: search input + 7 pills (`industry/investment/royalty/item19/state/outlets/year`) each opening a popover holding the real control (IDs preserved); `Tools ▾` popover holds persona/saved-views/watchlist/z-badges/tags/benchmark/export-presets/bulk-lookup/guided-picker/reset/copy.
  - `.layout` grid→`display:block`; `.main` full-width; added §1 filter-bar CSS block; added popover-toggle + pill-label-sync `<script>`.
  - null-safed the legacy sidebar mobile-drawer JS (`#sidebar`/`#sidebar-mobile-close` removed) to stop a throw — §6 will rewire the FAB.
- **Deviations from spec:** Risk weights / Export CSV / PDF stay in the `.results-header` (already there; §3.6 wants the view-toggle there too) — bar's right side is just `Tools ▾`. Spec's `overflow-x:auto` on the bar dropped → `flex-wrap:wrap` (overflow-x would clip popovers). Filter→URL-sync (§1.5) deferred to a follow-up; engine's own state handling intact. Tabler icons link NOT yet added (no pill uses an icon yet; add when §2 tabs need them).
- **Before→After:** `baseline_*` → `s1_after_*`; popovers `s1_verify_industry_open.png`, `s1_verify_tools_open.png`.
- **Vision verdict (inline):** PASS — sidebar gone, bar clean, KPIs full-width, hero retains chips+activity feed, full page renders.
- **Functional (`_verify_s1.py`):** PASS — Industry→Food QSR filtered `631`→`Showing 157 of 631`; pill synced + active; Tools popover holds all 20 control IDs; Year popover has `#tm-slider`.
- **Console:** clean (0 errors).
- **Opus:** **SHIP.** Sidebar gone, sticky bar correct (`top:var(--header-height); z-index:40`), Tools popover scrolls (max-height 72vh) so all 20 features reachable, dark/light/mobile not broken. **Deferred nit:** light-mode `.filter-value` contrast is flat (selected values don't pop like dark mode) — batch into a later polish pass. Mobile "Filters 0" FAB now redundant → fold into §6.

