"""US state tile-grid heatmap renderer.

Renders Item 20 per-state outlet counts as an inline SVG tile grid (5x11),
similar to the FiveThirtyEight / NPR cartogram style. State squares are
colored by quintile; zero-coverage states are light gray.

Tile grid: 8 rows x 11 cols. Geographically approximate but readable
even for small states (RI, DE, DC).

Usage:
    from src.state_map import normalize_state_code, render_state_heatmap_svg
    counts = {"CA": 279, "TX": 191, ...}  # 2-letter codes
    svg = render_state_heatmap_svg(counts, brand_name="Servpro")
"""
from __future__ import annotations

# (row, col) — 0,0 is top-left
US_TILE_GRID = {
    "AK": (5, 0),
    "HI": (7, 0),
    "ME": (0, 10),
    "VT": (1, 9), "NH": (1, 10),
    "WA": (2, 1), "MT": (2, 2), "ND": (2, 3), "MN": (2, 4), "WI": (2, 5), "MI": (2, 6),
    "NY": (2, 9), "MA": (2, 10),
    "OR": (3, 1), "ID": (3, 2), "SD": (3, 3), "IA": (3, 4), "IL": (3, 5), "IN": (3, 6),
    "OH": (3, 7), "PA": (3, 8), "NJ": (3, 9), "CT": (3, 10),
    "CA": (4, 1), "NV": (4, 2), "WY": (4, 3), "NE": (4, 4), "MO": (4, 5), "KY": (4, 6),
    "WV": (4, 7), "VA": (4, 8), "MD": (4, 9), "RI": (4, 10),
    "AZ": (5, 2), "UT": (5, 3), "CO": (5, 4), "KS": (5, 5), "AR": (5, 6), "TN": (5, 7),
    "NC": (5, 8), "DC": (5, 9), "DE": (5, 10),
    "NM": (6, 3), "OK": (6, 4), "LA": (6, 5), "MS": (6, 6), "AL": (6, 7), "SC": (6, 8),
    "TX": (7, 4), "GA": (7, 7), "FL": (7, 8),
}

US_STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii",
    "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine",
    "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}

_NAME_TO_CODE = {v.lower(): k for k, v in US_STATE_NAMES.items()}
_VALID_CODES = set(US_STATE_NAMES.keys())


def normalize_state_code(s: str | None) -> str | None:
    """Return 2-letter US state code, or None for non-US / unknown."""
    if not s:
        return None
    s = str(s).strip()
    if not s:
        return None
    upper = s.upper()
    if upper in _VALID_CODES:
        return upper
    if s.lower() in _NAME_TO_CODE:
        return _NAME_TO_CODE[s.lower()]
    return None


def aggregate_by_state(rows: list[dict]) -> dict[str, int]:
    """Given a list of {state, outlets_end} dicts (one per state row), return
    {state_code: total_outlets}, normalizing names and filtering non-US rows.

    Sums duplicates (rare — e.g. when multiple outlet_type rows exist per state).
    """
    out: dict[str, int] = {}
    for r in rows:
        code = normalize_state_code(r.get("state"))
        if not code:
            continue
        n = r.get("outlets_end")
        if n is None:
            continue
        try:
            n = int(n)
        except (TypeError, ValueError):
            continue
        if n < 0:
            continue
        out[code] = out.get(code, 0) + n
    return out


def _quintile_buckets(values: list[int]) -> list[int]:
    """Compute 4 cutoffs that split positive values into 5 quintile buckets.

    Returns sorted thresholds [q1, q2, q3, q4] where:
      bucket 0: 0 (no outlets)
      bucket 1: 1..q1
      bucket 2: q1+1..q2
      bucket 3: q2+1..q3
      bucket 4: q3+1..q4
      bucket 5: q4+1..max
    """
    positives = sorted(v for v in values if v > 0)
    if not positives:
        return [0, 0, 0, 0]
    n = len(positives)
    if n <= 4:
        # Small set — use unique values as cutoffs
        unique = sorted(set(positives))
        while len(unique) < 4:
            unique.append(unique[-1])
        return unique[:4]
    # Standard quintile cuts at 20/40/60/80%
    cuts = []
    for pct in (0.2, 0.4, 0.6, 0.8):
        idx = max(0, min(n - 1, int(pct * n)))
        cuts.append(positives[idx])
    return cuts


def _bucket_for(value: int, cuts: list[int]) -> int:
    if value <= 0:
        return 0
    for i, c in enumerate(cuts, start=1):
        if value <= c:
            return i
    return 5


# Brand-blue ramp (light → dark)
_BUCKET_COLORS = {
    0: "#f1f5f9",  # zero/no data — light gray
    1: "#dbeafe",  # bottom quintile — very light blue
    2: "#93c5fd",
    3: "#60a5fa",
    4: "#2563eb",
    5: "#1e3a8a",  # top quintile — deep blue
}
_BUCKET_TEXT_COLORS = {
    0: "#64748b",
    1: "#1e293b",
    2: "#1e293b",
    3: "#ffffff",
    4: "#ffffff",
    5: "#ffffff",
}


def render_state_heatmap_svg(
    state_outlets: dict[str, int],
    *,
    brand_name: str = "",
    tile_size: int = 32,
    gap: int = 3,
    show_labels: bool = True,
    show_counts: bool = True,
) -> str:
    """Render a tile-grid SVG choropleth.

    Returns the SVG element as a string. Caller embeds inline in HTML.

    state_outlets: {state_code: count} — 2-letter codes, non-negative ints.
    """
    rows_count = 8
    cols_count = 11
    width = cols_count * (tile_size + gap) + gap
    height = rows_count * (tile_size + gap) + gap

    state_outlets = {
        code: int(n) for code, n in state_outlets.items()
        if code in US_TILE_GRID and isinstance(n, (int, float)) and n >= 0
    }
    cuts = _quintile_buckets(list(state_outlets.values()))

    states_covered = sum(1 for n in state_outlets.values() if n > 0)
    total = sum(state_outlets.values())

    parts = [
        f'<svg class="state-heatmap" xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'role="img" aria-labelledby="heatmap-title heatmap-desc" '
        f'preserveAspectRatio="xMidYMid meet">',
        f'<title id="heatmap-title">US outlet distribution{": " + brand_name if brand_name else ""}</title>',
        f'<desc id="heatmap-desc">'
        f'Tile-grid map showing per-state outlet counts. '
        f'{states_covered} states with outlets, {total} total.</desc>',
    ]

    for code, (row, col) in US_TILE_GRID.items():
        x = gap + col * (tile_size + gap)
        y = gap + row * (tile_size + gap)
        n = state_outlets.get(code, 0)
        bucket = _bucket_for(n, cuts)
        fill = _BUCKET_COLORS[bucket]
        text_color = _BUCKET_TEXT_COLORS[bucket]
        state_name = US_STATE_NAMES.get(code, code)
        title = f"{state_name}: {n} outlet{'s' if n != 1 else ''}" if n > 0 else f"{state_name}: no outlets"
        parts.append(
            f'<g class="state-tile" data-state="{code}" data-count="{n}">'
            f'<title>{title}</title>'
            f'<rect x="{x}" y="{y}" width="{tile_size}" height="{tile_size}" '
            f'rx="3" fill="{fill}" stroke="#cbd5e1" stroke-width="0.5"/>'
        )
        if show_labels:
            label_y = y + tile_size / 2 + (3 if not show_counts else -2)
            parts.append(
                f'<text x="{x + tile_size/2}" y="{label_y}" '
                f'text-anchor="middle" dominant-baseline="middle" '
                f'font-size="{tile_size * 0.32:.1f}" font-family="system-ui, sans-serif" '
                f'font-weight="600" fill="{text_color}">{code}</text>'
            )
        if show_counts and n > 0:
            count_y = y + tile_size / 2 + tile_size * 0.28
            count_label = str(n) if n < 1000 else f"{n // 1000}k"
            parts.append(
                f'<text x="{x + tile_size/2}" y="{count_y}" '
                f'text-anchor="middle" dominant-baseline="middle" '
                f'font-size="{tile_size * 0.26:.1f}" font-family="system-ui, sans-serif" '
                f'fill="{text_color}">{count_label}</text>'
            )
        parts.append('</g>')

    parts.append('</svg>')
    return "".join(parts)


def render_legend_svg(state_outlets: dict[str, int], tile_size: int = 16) -> str:
    """Render a small quintile legend matching the heatmap colors."""
    values = [v for v in state_outlets.values() if v > 0]
    if not values:
        return ""
    cuts = _quintile_buckets(values)
    max_v = max(values)
    labels = [
        ("0", _BUCKET_COLORS[0]),
        (f"1-{cuts[0]}", _BUCKET_COLORS[1]),
        (f"{cuts[0]+1}-{cuts[1]}", _BUCKET_COLORS[2]),
        (f"{cuts[1]+1}-{cuts[2]}", _BUCKET_COLORS[3]),
        (f"{cuts[2]+1}-{cuts[3]}", _BUCKET_COLORS[4]),
        (f"{cuts[3]+1}+", _BUCKET_COLORS[5]),
    ]
    # Dedupe labels with same range (happens on small distributions)
    seen, deduped = set(), []
    for lab, col in labels:
        if lab in seen:
            continue
        seen.add(lab)
        deduped.append((lab, col))
    parts = ['<div class="heatmap-legend" role="presentation">']
    for lab, col in deduped:
        parts.append(
            f'<span class="legend-item">'
            f'<span class="legend-swatch" style="background:{col}"></span>'
            f'<span class="legend-label">{lab}</span></span>'
        )
    parts.append('</div>')
    return "".join(parts)
