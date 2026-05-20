"""Fix: my color sweep replaced CSS hex codes inside JS strings with var(--X).
Chart.js can't resolve CSS variables — needs literal colors.

This script replaces 'var(--TOKEN)' (single-quoted, JS-context) with the
actual hex value. Leaves CSS-context var(--TOKEN) (no quotes) untouched.
"""
from pathlib import Path

DASH = Path(__file__).resolve().parents[1] / "scripts" / "build_dashboard.py"

JS_RESOLVES = {
    "'var(--bg-base)'":         "'#0A0E14'",
    "'var(--bg-elevated)'":     "'#131923'",
    "'var(--bg-overlay)'":      "'#1C2332'",
    "'var(--bg-canvas)'":       "'#0F141C'",
    "'var(--border-default)'":  "'rgba(255,255,255,0.10)'",
    "'var(--border-emphasis)'": "'rgba(255,255,255,0.16)'",
    "'var(--border-subtle)'":   "'rgba(255,255,255,0.06)'",
    "'var(--text-primary)'":    "'#F2F3F5'",
    "'var(--text-secondary)'":  "'#9CA3AF'",
    "'var(--text-tertiary)'":   "'#6B7280'",
    "'var(--text-muted)'":      "'#4B5563'",
    "'var(--accent-primary)'":  "'#10B981'",
    "'var(--accent-warning)'":  "'#F59E0B'",
    "'var(--accent-danger)'":   "'#EF4444'",
    "'var(--accent-info)'":     "'#60A5FA'",
    "'var(--accent-gold)'":     "'#D4AF37'",
}


def main():
    text = DASH.read_text(encoding="utf-8")
    n = 0
    for k, v in JS_RESOLVES.items():
        before = text.count(k)
        text = text.replace(k, v)
        n += before
    DASH.write_text(text, encoding="utf-8")
    print(f"Reverted {n} JS-context var() back to hex/rgba literals.")


if __name__ == "__main__":
    main()
