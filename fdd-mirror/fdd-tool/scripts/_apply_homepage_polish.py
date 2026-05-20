"""Append homepage-polish CSS to style.css (idempotent via marker)."""
from pathlib import Path

MARKER = "/* === HOMEPAGE LUXURY POLISH (Phase 2) === */"
OVERLAY = '''

''' + MARKER + '''
.hero-luxury {
    padding: 56px 0 32px;
    border-bottom: 1px solid var(--border-subtle);
}
.hero-luxury .eyebrow { margin-bottom: 16px; }
.hero-luxury .display {
    margin: 0 0 16px;
    font-family: var(--font-display);
    font-size: clamp(36px, 5.5vw, 56px);
    font-weight: 600;
    line-height: 1.05;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, var(--text-primary) 0%, var(--text-secondary) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.hero-luxury .subhead {
    font-size: 18px;
    line-height: 1.55;
    color: var(--text-secondary);
    max-width: 680px;
    margin: 0 0 32px;
}

.featured-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin: 0 0 36px;
    padding: 22px 26px;
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
}
.featured-stat {
    border-right: 1px solid var(--border-subtle);
    padding-right: 16px;
}
.featured-stat:last-child { border-right: none; }
.featured-stat-val {
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
    font-size: 36px;
    font-weight: 500;
    color: var(--text-primary);
    letter-spacing: -0.02em;
    line-height: 1.05;
    margin-bottom: 6px;
}
.featured-stat-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-tertiary);
}
@media (max-width: 720px) {
    .featured-stats { grid-template-columns: 1fr; }
    .featured-stat { border-right: none; border-bottom: 1px solid var(--border-subtle); padding-bottom: 12px; }
    .featured-stat:last-child { border-bottom: none; padding-bottom: 0; }
    .featured-stat-val { font-size: 28px; }
}

.category-chips {
    display: flex; flex-wrap: wrap; gap: 8px;
    margin-top: 4px;
}
.category-chips .chip {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 7px 14px;
    background: transparent;
    border: 1px solid var(--border-default);
    border-radius: 999px;
    color: var(--text-secondary);
    font-size: 13px;
    font-weight: 500;
    text-decoration: none;
    transition: all var(--dur-fast) var(--ease);
}
.category-chips .chip:hover {
    background: var(--bg-overlay);
    border-color: var(--border-emphasis);
    color: var(--text-primary);
}
.category-chips .chip.active {
    background: var(--accent-primary);
    border-color: var(--accent-primary);
    color: var(--bg-base);
}
.category-chips .chip-count {
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
    font-size: 11px;
    font-weight: 500;
    color: var(--text-tertiary);
}
.category-chips .chip:hover .chip-count { color: var(--text-secondary); }
.category-chips .chip.active .chip-count { color: var(--bg-base); opacity: 0.75; }

.brand-list-controls {
    display: flex; gap: 16px; align-items: center; flex-wrap: wrap;
    margin: 12px 0 18px;
}
.brand-search-wrap {
    position: relative; flex: 1 1 320px; max-width: 480px;
}
.brand-search-wrap input[type="search"] {
    width: 100%;
    height: 48px;
    padding: 0 56px 0 44px;
    background: var(--bg-elevated);
    border: 1px solid var(--border-default);
    border-radius: 10px;
    color: var(--text-primary);
    font-size: 16px;
    font-family: var(--font-body);
    transition: border-color var(--dur-fast) var(--ease), background var(--dur-fast) var(--ease);
}
.brand-search-wrap input[type="search"]::placeholder { color: var(--text-tertiary); }
.brand-search-wrap input[type="search"]:focus {
    border-color: var(--accent-info);
    background: var(--bg-overlay);
}
.brand-search-wrap .search-icon {
    position: absolute; left: 16px; top: 50%; transform: translateY(-50%);
    color: var(--text-tertiary); font-size: 18px; pointer-events: none;
}
.brand-search-wrap .search-kbd {
    position: absolute; right: 14px; top: 50%; transform: translateY(-50%);
    background: var(--bg-overlay);
    border: 1px solid var(--border-default);
    border-radius: 4px;
    padding: 2px 7px;
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 500;
    color: var(--text-tertiary);
    pointer-events: none;
}

.brand-filter-toggles { display: flex; gap: 6px; flex-wrap: wrap; }
.filter-toggle {
    background: transparent;
    border: 1px solid var(--border-default);
    color: var(--text-secondary);
    padding: 8px 14px;
    border-radius: 8px;
    font-family: var(--font-body);
    font-weight: 500;
    font-size: 13px;
    cursor: pointer;
    transition: all var(--dur-fast) var(--ease);
}
.filter-toggle:hover { background: var(--bg-overlay); color: var(--text-primary); }
.filter-toggle.active {
    background: var(--accent-primary);
    border-color: var(--accent-primary);
    color: var(--bg-base);
}

#home-brands-table td, .data-table.sortable-table td { padding: 14px 12px; }
#home-brands-table th, .data-table.sortable-table th {
    padding: 14px 12px;
    background: var(--bg-canvas);
    color: var(--text-tertiary);
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 1px solid var(--border-default);
    position: sticky; top: 0; z-index: 1;
}
#home-brands-table tr td { border-bottom: 1px solid var(--border-subtle); }
#home-brands-table tr:hover td { background: rgba(255, 255, 255, 0.03); }
#home-brands-table tr:last-child td { border-bottom: none; }

.i19-badge {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 3px 10px;
    border-radius: 6px;
    font-family: var(--font-body);
    font-size: 12px;
    font-weight: 500;
    border: 1px solid;
    white-space: nowrap;
}
.i19-badge.i19-broad {
    background: rgba(16, 185, 129, 0.08);
    border-color: rgba(16, 185, 129, 0.24);
    color: var(--accent-primary);
}
.i19-badge.i19-thin {
    background: rgba(245, 158, 11, 0.08);
    border-color: rgba(245, 158, 11, 0.24);
    color: var(--accent-warning);
}
.i19-badge.i19-none {
    background: rgba(255, 255, 255, 0.03);
    border-color: var(--border-default);
    color: var(--text-tertiary);
}
'''


def main():
    css_path = Path(__file__).resolve().parents[1] / "src" / "templates" / "style.css"
    text = css_path.read_text(encoding="utf-8")
    if MARKER in text:
        print(f"[skip] homepage polish already present in {css_path}")
        return
    css_path.write_text(text + OVERLAY, encoding="utf-8")
    print(f"[done] appended {len(OVERLAY):,} chars to {css_path}")


if __name__ == "__main__":
    main()
