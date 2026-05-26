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
- ✅ **DONE 2026-05-25** via `scripts/_apply_s3a_quadrant.py` (owner request): removed CSS block, the `<div class="chart-card chart-wide">` card, JS defs (`quadrantSelected`/`QUADRANTS`/`quadrantOf`/`renderQuadrant`/`QUADRANT_BOUNDS`), the `rerender()` filter+call, the afClearAll reset, and both click handlers. 0 console errors; filtering regression PASS. (3 stale code-comments mentioning "quadrant" left — non-executing, harmless.)

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
| 2 | Tab navigation skeleton | ✅ SHIP (Opus reviewed) |
| 3 | Dashboard tab content (incl. quadrant + corpus-coverage removal) | ✅ SHIP (Opus reviewed) |
| 4 | Placeholder tabs (Compare / Watchlist / Reports) | ☐ |
| 5 | Activity feed → header bell dropdown | ☐ |
| 6 | Mobile responsive | ✅ SHIP (Opus reviewed) |
| 7 | Migration cleanup (dead CSS/JS) | ✅ done — JS dead-code already removed inline; dead CSS inventoried for source port (see below) |
| 8 | Verification (computed-style audit + screenshot diff) | ✅ PASS 15/15 |

---

## Polish backlog — from Opus general-appeal audit (2026-05-25)

Owner wants ongoing general-appeal review (centering/alignment/balance), not just spec compliance. Findings:

- ✅ **FIXED §1b:** Hero + 3 KPI cards filled only left ~55% (dead space right). Cause: `.kpi-3` used `repeat(auto-fit, minmax(220px,280px)) + justify-content:start` (leftover from when `.main` was the narrow right column). → `repeat(3, 1fr)`. Now full-width/balanced.
- ✅ **FIXED §1b:** Recent-updates activity feed removed from hero (owner request) — supersedes spec §5 relocation.
- ☐ **§3 (charts):** Industry Mix donut legend clips "Real Es…" — widen legend column / wrap label.
- ☐ **§3 (table):** Brands-table Risk Score mini-bars look near-identical across 96/90/72/100/84 — bind bar width to score, widen dynamic range.
- ☐ **verify §3:** Insight cards row bottom-edge evenness (grid stretch looks OK post-KPI-fix; reconfirm).
- ☐ **nice:** unify card radii/treatment (KPI softer vs insight flatter); hero risk/disclaimer links low-emphasis; table industry pills all-flat-blue (category color-coding?); footer "Generated…noindex" dev strip should be gated so it can't leak to prod.
- ✅ **FIXED §3:** light-mode filter-pill value contrast (`[data-theme=light] .filter-value → --text-primary`).
- ✅ **FIXED §3:** donut legend clip ("Real Es…") — donut widened to 1.4fr; legend now shows all incl. "Real Estate (21)".
- ✅ **FIXED §3:** risk-score mini-bars now proportional (was fixed 24px dash → 42px track + fill width=score%).
- ✅ **FIXED (polish):** donut honesty — top-12 now joined by a neutral-gray non-clickable **"+N more industries"** slice so all brands are represented (tooltip % over true total; click guarded). Automotive/Pet ambers differentiated (`#fbbf24` vs `#ea580c`).
- ✅ **VERIFIED FINE:** insight-card eyebrow baselines already align (grid-stretch + KPI fix) — no change needed.
- ☐ **NICE remaining (marginal):** (a) mobile: donut legend wraps ~6 lines + box-plot y-axis tight at 390px; (b) light-mode general polish pass. Low value; can fold into the source port.

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

### Full E2E interaction audit (2026-05-26) — `scripts/_e2e_audit.py`
Playwright sweep: clicked every control, hovered tooltip elements, asserted expected state changes, collected all console/page errors. **37 PASS / 0 FAIL / 0 console errors / 0 page errors.** Covered: 4 tabs (panel+hash), search, all 7 filter pills (each filters), active chips + clear-all, all 11 Tools controls present, z-badge toggle, bulk-lookup modal, 6 preset chips, insight cards (apply filter), Your Score compute-on-set + reset-to-N/A, 3 charts on canvas, table column sort, view modes table/cards/map (map = 190 tiles), row star/pin/multi-select→compare-bar/drill-down open+close, columns menu, CSV export, 33 [data-tip] hovers.
- **Found + fixed (real):** (1) `.action-bar` z-60 sat under the weight-drawer z-80 → could cover the compare buttons → bumped to **z-90**. (2) "Fastest growing" chip tooltip promised "+20% or more" (a filter) but the preset is **sort-only** (no growth filter input exists) → tooltip corrected to "Sorted by outlet growth — highest first."

### Polish round — external-agent 8.5→9.0 list (2026-05-26)
Addressed the reviewer's 7-item list (judgment applied per "as needed"):
- ✅ **#1 empty score-distribution band** → added a functional **"⚖ Set Your Score weights →"** CTA in the prompt (opens the weights drawer) instead of a dead gap.
- ✅ **#3 methodology/disclaimer links** → from weak gray text to **bordered pills with accent icons** ("? How Your Score works", "ⓘ Disclaimer").
- ✅ **#4 insight-card asymmetry** → trimmed the "Financial Disclosure" card sub to match the others' length (insights.json).
- ✅ **#5 weights drawer clipped** → added `max-height: calc(100vh - 72px); overflow-y:auto` — drawer now fully visible (verified box top 411 / bottom 900 at 900px vh).
- ⏭ **#2 move Year/Filing-state to Tools** → SKIPPED (judgment): bar already `flex-wrap`s gracefully <1100px; relocating live controls = high-risk/low-reward narrow-width-only gain.
- ✅ **#6 σ-badge colors** → VERIFIED already favorability-coded (`directional = z×polarity` → z-good/z-bad/z-neut green/red/slate; no yellow class). The "cream" was royalty cell coloring, a separate thing. No change — wouldn't "fix" working logic.
- ✅ **#7 Map view** → VERIFIED functional (tile-map renders 190 state tiles w/ outlet counts). Kept (not half-shipped).
- **MEDIAN REVENUE header** "clip" → not reproducing at standard width (table scrolls-x); narrow-viewport artifact. No change.
- Verified: 0 console errors. Shots: `polish2_*`. (Reviewer's meta-rec — diminishing returns, pivot to launch-prep/source-port — noted.)

### Members-only gate — REMOVED for testing (2026-05-25)
- Owner: **no pay gates or blocks while testing.** The mock login/disclosure interstitial (committed `f395b61dc`) was reverted (`7ffdaeae6`) so the dashboard is freely accessible. The prototype lives on in `scripts/_apply_gate.py` — re-run it to bring the gate back when the member tier + attorney-approved disclosure are ready. (Persona "What brings you here?" modal is left as-is — skippable, pre-existing, not a gate; flag if it should go too.)

### Composite-score reframe — "Your Score" (2026-05-25, owner litigation directive)
- **Goal:** the score is the USER's, not ours — N/A until the user sets weights; renamed off "risk"; framed as their analysis. (Phase 1 of the [[project-composite-score-reframe]] direction; login-gate + attorney disclosure copy = Phase 2, needs auth infra.)
- **Applied via:** `scripts/_apply_score_reframe.py` (idempotent). Verify: `scripts/_verify_reframe.py`.
- **Edits (`docs/dashboard/index.html` + `insights.json`):**
  - `recomputeRiskScores()` gated on `weightsSet` (= localStorage has a saved weight set) → every brand `risk_score = null` until the user sets weights; `saveWeights()` flips `weightsSet=true` (the existing slider→save wiring is the "fill them out" trigger); `w-reset` now CLEARS back to N/A.
  - Table column `Risk score` → **`Your Score ⓘ`** + tooltip "based on the weights YOU select… your analysis, not our rating."
  - Drawer `⚖ Risk weights` → `⚖ Your Score weights`; body copy reframed to the user's analysis; toggle button + tip renamed.
  - Box-plot title → "Your Score distribution… (your analysis using your weights, not a rating)"; axis labels → "Your Score"; **`#score-prompt` shown via `body.score-unset`** until weights set (canvas hidden); drill panel + compare-row label → "Your Score".
  - Personas now sort by `top_revenue` (neutral fact), not the user-driven score.
  - `insights.json`: removed the "363 brands score ≥70 on our composite" card → neutral "Brands that disclose Item 19 earnings" (no house verdict).
- **Verified (`_verify_reframe.py`):** on load 0 score badges / cells show "—" / `body.score-unset` / box-plot prompt visible; after setting one weight → 300 scores compute, prompt clears, box-plot renders; header = "YOUR SCORE ⓘ"; 0 console errors. Fixed a flex letter-stack bug in the prompt (→ block text).
- **Opus review = ITERATE → fixed.** Reframe lands (column/box-plot prompt/KPIs read as user-owned). Must-fix it caught: hero link still said "How we calculate risk scores →" → renamed **"How Your Score works →"**; swept all user-facing "risk score" strings (box-plot dataset label, CSV header, 3 PDF labels → "Your Score"). NICEs done: emphasized `#weight-toggle-btn` (accent) when `score-unset` so the entry point is obvious; collapsed the box-plot card void; prompt block-flow fix.
- **NOT done (Phase 2, gated):** dashboard login-gating + the disclosure-at-login copy (needs real auth backend §17.4 + attorney-written copy). **Attorney to confirm:** (a) the green/amber/red badge thresholds (≥70/≥45) are OUR cutoffs applied to the user's composite — arguably still editorializing; (b) the "Disclaimer →"/methodology copy covers the scoring framing + "not our rating"; (c) sub-scores (closure proxy etc.) remain our interpretation of FDD facts. (Flagged by Opus.)


<!-- Template:
### §X.Y — <title>  (<date>)
- Goal / Edits (file:line) / Before→After shots / Vision verdict / Console / Opus
-->

### §8 — Verification  (2026-05-25)
- **`scripts/_verify_s8.py` — 15/15 PASS:** filter-bar `position:sticky`; tabs `display:flex`; active tab has accent underline; dashboard panel visible / compare hidden; `.kpi-3` = 3 cols; `.distributions-row` = 3 cols; **sidebar / quadrant / hero activity-feed / corpus-coverage all REMOVED**; all 11 sampled control IDs present (filter engine intact); risk-bar fills vary by score; deep-link `#compare` opens Compare; 0 console errors.
- Final screenshot set: `final_{desktop_dark,desktop_dark_full,desktop_light,mobile_dark_full}.png` (vs `baseline_*`).
- Cross-section regressions: none (each section re-ran filtering/tabs/console checks).

### §7 — Migration cleanup  (2026-05-25)
- **Dead JS already removed inline during the rebuild:** quadrant block (§3.4), and the legacy sidebar mobile-drawer JS was null-safed then repurposed (§1/§6). No dead JS throws (§8 = 0 console errors).
- **Dead CSS — NOT stripped from the mirror artifact (intentional).** §7 as specced targets the *source* (`build_dashboard.py` / `style.css`); cleaning the generated static file is low-value + regen-fragile. Verified dead (0 DOM usage) → **remove during the source port:** `.sidebar`, `.sidebar h3`, `.sidebar input/select`, `.filter-group`, `.filter-group label`, `.dashboard-activity-feed` + `.activity-feed-*`, `.sidebar-mobile-handle`, `.sidebar-mobile-close`, `.views-block`/`.bench-block`/`.export-block`, and the full `.quadrant-*`/`.q-*`/`.qx-axis`/`.qy-axis` block. **Keep (still used):** `.filter-range`, `.persona-pill`, `.views-actions`/`.bench-actions`/`.export-actions`, `.btn`, `.check-label`, `.bulk-lookup-trigger`, `.info-icon`.

### §6 — Mobile responsive  (2026-05-25)
- **Goal:** usable mobile — filter bar → drawer, scrollable tabs, stacked KPIs/charts, table mobile.
- **Edits (`docs/dashboard/index.html`, all in `@media (max-width:767px)`):** repurposed the dead `.sidebar` drawer infra → the top filter bar is now a **bottom-sheet drawer** opened by the existing FAB (`openMobileDrawer/closeMobileDrawer` retargeted to `#dashboard-filter-bar`; FAB toggles); pills full-width, popovers render **inline** (`position:static`, no clipping); `.dashboard-filter-bar.mobile-open` z-index 80 (beats the §1 z-40 rule via higher specificity) so it sits above the backdrop; FAB z-85 + **hidden while drawer open** (was occluding bottom rows); tab strip `overflow-x:auto`; `.results-header` stacks column (fixed "Brands" vertical letter-wrap). KPIs/distributions already stack; `#view-table` already scrolls-x (cards view is the mobile default).
- **Verified (`_verify_s6.py`):** FAB opens drawer; popover opens inline; Food QSR→157; FAB badge→"Filters 1"; FAB hides when open; backdrop closes; FAB returns; desktop filter bar still inline/sticky (not regressed); 0 console errors.
- **Opus:** **SHIP** after 3 must-fixes (FAB occlusion → hide-when-open; sheet bottom padding; "Brands" heading vertical-stack → results-header column). NICE deferred: donut legend wraps ~6 lines at 390px, box-plot y-axis tight on mobile, toolbar buttons 3 ragged rows, hero chip vertical gap.

### §3 — Dashboard tab content  (2026-05-25)
- **Goal:** remove quadrant + Corpus Coverage duplicate; order KPIs→insights→distributions→box→table; donut wider (1.4/1/1); fix risk-score bars; light-mode pill contrast.
- **Edits (`docs/dashboard/index.html`):** §3.4 quadrant removed (see ledger; `_apply_s3a_quadrant.py`); removed `.activity-feed` "Corpus coverage" card; wrapped the 3 distribution charts in `.distributions-row` (grid 1.4fr/1fr/1fr), risk box stays full-width `.charts-grid`; `.risk-badge .bar` fixed 24px → 42px track + `.bar-fill` width=`${risk_score}%` (badge markup updated); `[data-theme=light] .filter-value` → `--text-primary`.
- **Before→After:** `s3_after_*`, element shots `s3_distributions-row.png`, `s3_results.png`.
- **Verified:** 0 console errors; filtering/tabs/deep-link regression PASS.
- **Opus:** **SHIP** (4/4: corpus gone, donut legend unclipped incl. "Real Estate (21)", risk bars proportional 72<100, order correct; 0 must-fix). 3 NICE deferred (see polish backlog).

### §2 — Tab navigation skeleton  (2026-05-25)
- **Goal:** tab bar (Dashboard/Compare/Watchlist/Reports) between hero and filter bar; Dashboard = default + all existing content; Compare/Watchlist = empty-states, Reports = link grid; filter bar persistent; filter state persists across tabs; hash routing.
- **Applied via:** `scripts/_apply_s2.py` (idempotent). Verify: `scripts/_verify_s2.py`.
- **Edits (`docs/dashboard/index.html`):** tab bar `<nav.dashboard-tabs>` before filter bar; `.layout` marked `#tab-panel-dashboard.tab-panel`; 3 sibling panels before the action-bar; tab CSS + hash-routing JS (`fdSwitchTab`, chart.resize-on-show). **Bug fix:** `writeURL()` now appends `location.hash` so filter-URL-sync no longer strips the active tab (was breaking deep-links + wiping the tab on filter change). No watchlist badge (per §0).
- **Before→After:** `s2_after_*`, `s2_tab_compare/watchlist/reports.png`.
- **Functional (`_verify_s2.py`):** PASS — default=dashboard; 4 charts on dashboard; tab clicks swap panels + set hash; deep-link `#reports` reload opens Reports; filter (Food QSR→157) persists across tab round-trip; 0 console errors.
- **Opus:** ITERATE→resolved. Must-fix was Reports grid orphan card (auto-fit 5+1) → `repeat(3,1fr)` balanced 3×2. Also addressed NICE: empty-state icons → circular containers; +8px top spacing on tab bar. Verdict otherwise SHIP-class (placement, accent-underline active state, empty-states, filter-chip persistence).

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

