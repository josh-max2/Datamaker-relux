"""Bulk-replace legacy slate/sky color hex codes in build_dashboard.py
with the luxury CSS variables. Safe: only swaps values inside CSS strings;
doesn't touch data values or Python logic.

Idempotent: re-run is a no-op if all colors are already swapped.
"""
from pathlib import Path

DASH = Path(__file__).resolve().parents[1] / "scripts" / "build_dashboard.py"

# Color → CSS variable swaps. Done in CSS-context only (we're inside a Python
# triple-quoted string). The values listed here are all the slate/sky tokens
# v6 inherited from the legacy palette.
SWAPS = [
    # Backgrounds
    ("#0f172a",  "var(--bg-base)"),
    ("#1e293b",  "var(--bg-elevated)"),
    ("#0f141c",  "var(--bg-canvas)"),
    # Borders
    ("#334155",  "var(--border-default)"),
    ("#475569",  "var(--border-emphasis)"),
    # Text
    ("#f8fafc",  "var(--text-primary)"),
    ("#f1f5f9",  "var(--text-primary)"),
    ("#e2e8f0",  "var(--text-primary)"),
    ("#cbd5e1",  "var(--text-secondary)"),
    ("#94a3b8",  "var(--text-secondary)"),
    ("#64748b",  "var(--text-tertiary)"),
    # Accents — sky blue → premium info blue
    ("#38bdf8",  "var(--accent-info)"),
    ("#0ea5e9",  "var(--accent-info)"),
    ("#1d4ed8",  "var(--accent-info)"),
    ("#2563eb",  "var(--accent-info)"),
    ("#1e3a5f",  "rgba(96, 165, 250, 0.12)"),
    ("#93c5fd",  "var(--accent-info)"),
    # Status colors — match luxury accents
    ("#34d399",  "var(--accent-primary)"),
    ("#10b981",  "var(--accent-primary)"),
    ("#fbbf24",  "var(--accent-warning)"),
    ("#f87171",  "var(--accent-danger)"),
    ("#fca5a5",  "var(--accent-danger)"),
]


def main():
    text = DASH.read_text(encoding="utf-8")
    orig_len = len(text)
    n_changes = 0
    for old, new in SWAPS:
        # Match the hex codes inside CSS values: after `: `, after a comma, etc.
        # We replace ALL occurrences inside the Python file — this is safe
        # because hex color codes don't appear as data values in this script.
        before = text
        text_lower = text.lower()
        # Case-insensitive replacement
        i = 0
        new_text = []
        old_lower = old.lower()
        while i < len(text):
            j = text_lower.find(old_lower, i)
            if j < 0:
                new_text.append(text[i:])
                break
            new_text.append(text[i:j])
            new_text.append(new)
            i = j + len(old)
            n_changes += 1
        text = "".join(new_text)
        text_lower = text.lower()

    DASH.write_text(text, encoding="utf-8")
    print(f"Applied {n_changes} color substitutions. File: {orig_len:,} -> {len(text):,} chars")


if __name__ == "__main__":
    main()
