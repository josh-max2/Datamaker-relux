"""One-shot script: append the luxury-theme CSS overlay to style.css.
Idempotent — uses a marker to detect if already applied.
"""
from pathlib import Path
import sys

MARKER = "/* === LUXURY THEME OVERLAY (Phase 1) === */"

OVERLAY = """

""" + MARKER + """

/* Canvas + container surfaces */
body { background: var(--bg-base); color: var(--text-primary); }

/* Top header */
.site-header { background: var(--bg-elevated); border-bottom: 1px solid var(--border-subtle); }
.site-header a.brand {
    font-family: var(--font-display);
    font-weight: 600;
    letter-spacing: -0.01em;
    color: var(--text-primary);
}
.site-header nav a { color: var(--text-secondary); transition: color var(--dur-fast) var(--ease); }
.site-header nav a:hover { color: var(--text-primary); text-decoration: none; }

/* Header search */
.header-search input[type="search"] {
    background: var(--bg-base);
    border-color: var(--border-default);
    color: var(--text-primary);
    border-radius: 6px;
    transition: border-color var(--dur-fast) var(--ease);
}
.header-search input[type="search"]:focus { border-color: var(--accent-info); }
.header-search-results { background: var(--bg-elevated); color: var(--text-primary); border-color: var(--border-default); }
.header-search-results li a { color: var(--text-primary); border-color: var(--border-subtle); }
.header-search-results li a:hover { background: var(--bg-overlay); }
.header-search-results .hsr-name { color: var(--text-primary); }
.header-search-results .hsr-industry { color: var(--text-tertiary); }

/* Breadcrumbs */
.breadcrumbs { background: var(--bg-canvas); border-bottom: 1px solid var(--border-subtle); }
.breadcrumbs a { color: var(--accent-info); }
.breadcrumbs .sep { color: var(--text-muted); }

/* Cards */
.card, .panel, .section, .callout, .breakeven-section, .chart-wrap,
.industry-context, .compare-with-list, .data-table, .table-scroll {
    background: var(--bg-elevated);
    border-color: var(--border-subtle);
}
.card { border-radius: 12px; padding: 24px; transition: border-color var(--dur) var(--ease), background var(--dur) var(--ease), transform var(--dur) var(--ease); }
.card:hover { border-color: var(--border-emphasis); transform: translateY(-1px); box-shadow: var(--shadow-card); }

/* Headings */
h1 {
    font-family: var(--font-display);
    font-weight: 600;
    letter-spacing: -0.025em;
    line-height: 1.1;
    color: var(--text-primary);
}
h2, h3, h4, h5, h6 {
    font-family: var(--font-body);
    font-weight: 600;
    letter-spacing: -0.01em;
    color: var(--text-primary);
}

/* Hero primitives */
.eyebrow {
    font-family: var(--font-body);
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-tertiary);
    margin-bottom: 16px;
}
.display {
    font-family: var(--font-display);
    font-size: clamp(36px, 5vw, 56px);
    font-weight: 600;
    line-height: 1.05;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, var(--text-primary) 0%, var(--text-secondary) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    color: var(--text-primary);
    margin: 0 0 12px;
}
.subhead {
    font-size: 18px;
    color: var(--text-secondary);
    line-height: 1.55;
    max-width: 720px;
}
.dot-separator { color: var(--text-muted); margin: 0 8px; }

/* Numeric content */
.numeric, .metric-large, .metric-medium, .metric-small,
.data-table td.num, .data-table .num,
.kpi-val, .kpi-sub, .bar-value,
.fees-table td, .item19-table td,
.report-list .val,
.master-table td.num,
.metric-row .value,
.fast-facts .value, .key-facts .value,
output, time {
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.005em;
}
.metric-large {
    font-size: 36px;
    font-weight: 500;
    letter-spacing: -0.02em;
    color: var(--text-primary);
}
.metric-medium { font-size: 24px; font-weight: 500; }
.metric-small  { font-size: 14px; color: var(--text-secondary); }
.metric-positive { color: var(--accent-primary); }
.metric-negative { color: var(--accent-danger); }
.metric-neutral  { color: var(--text-secondary); }

/* Tables — luxury treatment */
.data-table th {
    text-align: left;
    color: var(--text-tertiary);
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 10px 12px;
    border-bottom: 1px solid var(--border-default);
    background: transparent;
}
.data-table td {
    padding: 10px 12px;
    border-bottom: 1px solid var(--border-subtle);
    color: var(--text-primary);
    transition: background var(--dur-fast) var(--ease);
}
.data-table tr:hover td { background: var(--bg-overlay); }
.data-table a { color: var(--accent-info); text-decoration: none; }
.data-table a:hover { color: var(--text-primary); text-decoration: underline; }

/* Links */
a { color: var(--accent-info); transition: color var(--dur-fast) var(--ease); }
a:hover { color: var(--text-primary); }

/* Buttons */
.btn, .button {
    background: var(--bg-overlay);
    color: var(--text-primary);
    border: 1px solid var(--border-default);
    border-radius: 6px;
    padding: 8px 16px;
    font-family: var(--font-body);
    font-weight: 500;
    cursor: pointer;
    transition: all var(--dur-fast) var(--ease);
}
.btn:hover { border-color: var(--border-emphasis); transform: translateY(-1px); }
.btn-primary {
    background: var(--accent-primary);
    color: var(--bg-base);
    border-color: transparent;
}
.btn-primary:hover { box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25); }

/* Badges */
.ind-pill, .industry-pill, .ind {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    border-radius: 6px;
    font-family: var(--font-body);
    font-size: 12px;
    font-weight: 500;
    border: 1px solid var(--border-default);
    background: var(--bg-overlay);
    color: var(--text-secondary);
}

/* Calculator output panel */
.calculator-output, .calc-output, .roi-walkforward {
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 24px;
}

/* Item19 disclosure warnings — darker palette */
.item19-disclosure-warn {
    background: rgba(245, 158, 11, 0.08);
    border-left-color: var(--accent-warning);
    color: var(--text-primary);
}
.item19-disclosure-strong {
    background: rgba(239, 68, 68, 0.08);
    border-left-color: var(--accent-danger);
    color: var(--text-primary);
}
.item19-disclosure-info {
    background: rgba(96, 165, 250, 0.08);
    border-left-color: var(--accent-info);
    color: var(--text-primary);
}

/* Form elements */
input, select, textarea {
    background: var(--bg-canvas);
    border: 1px solid var(--border-default);
    color: var(--text-primary);
    border-radius: 6px;
    font-family: var(--font-body);
    transition: border-color var(--dur-fast) var(--ease);
}
input:focus, select:focus, textarea:focus {
    border-color: var(--accent-info);
    outline: none;
}
label { color: var(--text-secondary); }

/* Footer */
.site-footer, footer {
    background: var(--bg-elevated);
    border-top: 1px solid var(--border-subtle);
    color: var(--text-tertiary);
}

/* Loading skeleton */
.skeleton {
    background: linear-gradient(90deg, var(--bg-elevated) 0%, var(--bg-overlay) 50%, var(--bg-elevated) 100%);
    background-size: 200% 100%;
    animation: skeleton-shimmer 1.5s infinite;
    border-radius: 4px;
}
@keyframes skeleton-shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

/* Print fallback */
@media print {
    body, .card, .data-table { background: #fff !important; color: #000 !important; }
    .display { color: #000 !important; background: none !important; -webkit-text-fill-color: #000 !important; }
    .site-header { background: #fff !important; }
}
"""


def main():
    css_path = Path(__file__).resolve().parents[1] / "src" / "templates" / "style.css"
    text = css_path.read_text(encoding="utf-8")
    if MARKER in text:
        print(f"[skip] luxury overlay already present in {css_path}")
        return
    css_path.write_text(text + OVERLAY, encoding="utf-8")
    print(f"[done] appended {len(OVERLAY):,} chars of luxury overlay to {css_path}")


if __name__ == "__main__":
    main()
