"""SQLite schema + connection helpers for the FDD database.

Schema per spec §3. Single-file SQLite for MVP (Postgres later).
Idempotent: `init_db()` creates tables IF NOT EXISTS, so safe to re-run.

Usage:
    from src.db import init_db, get_conn, slugify
    init_db()
    with get_conn() as conn:
        conn.execute("SELECT * FROM franchisors")
"""
from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "db.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS franchisors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    legal_name      TEXT NOT NULL,
    brand_name      TEXT,
    parent_company  TEXT,
    state_of_inc    TEXT,
    industry        TEXT,
    category_naics  TEXT,
    year_founded    INTEGER,
    website         TEXT,
    slug            TEXT UNIQUE NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_franchisors_legal ON franchisors(legal_name);
CREATE INDEX IF NOT EXISTS idx_franchisors_industry ON franchisors(industry);

CREATE TABLE IF NOT EXISTS fdds (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    franchisor_id   INTEGER NOT NULL REFERENCES franchisors(id),
    filing_year     INTEGER NOT NULL,
    filing_state    TEXT NOT NULL,
    filing_date     DATE,
    effective_date  DATE,
    source_url      TEXT NOT NULL,
    local_path      TEXT NOT NULL,
    pdf_sha256      TEXT UNIQUE NOT NULL,
    page_count      INTEGER,
    has_item19      BOOLEAN,
    has_item20      BOOLEAN,
    retrieved_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parsed_at       TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_fdds_franchisor_year ON fdds(franchisor_id, filing_year);
CREATE INDEX IF NOT EXISTS idx_fdds_state ON fdds(filing_state);

CREATE TABLE IF NOT EXISTS item19_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fdd_id          INTEGER NOT NULL REFERENCES fdds(id),
    metric_name     TEXT NOT NULL,
    metric_raw      TEXT,
    cohort_name     TEXT,
    cohort_raw      TEXT,
    outlet_count    INTEGER,
    reporting_period TEXT,
    reporting_year  INTEGER,                 -- structured year (e.g. 2025), separate from free-text reporting_period
    unit_period     TEXT,                    -- 'annual' | 'monthly' | 'weekly' | 'daily' | NULL — see prompts.py
    metric_scope    TEXT,                    -- 'franchisee' | 'market-area' | 'ramp-snapshot' | NULL
    value_avg       NUMERIC,
    value_median    NUMERIC,
    value_min       NUMERIC,
    value_max       NUMERIC,
    percentile_25   NUMERIC,
    percentile_75   NUMERIC,
    pct_above_avg   NUMERIC,
    page_number     INTEGER,
    raw_text        TEXT,
    notes           TEXT,
    confidence      NUMERIC,
    needs_review    BOOLEAN DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_item19_fdd ON item19_records(fdd_id);
CREATE INDEX IF NOT EXISTS idx_item19_metric ON item19_records(metric_name);

CREATE TABLE IF NOT EXISTS item20_locations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fdd_id          INTEGER NOT NULL REFERENCES fdds(id),
    year            INTEGER NOT NULL,
    outlet_type     TEXT,
    state           TEXT,
    outlets_start   INTEGER,
    outlets_opened  INTEGER,
    outlets_closed  INTEGER,
    outlets_terminated INTEGER,
    outlets_nonrenewed INTEGER,
    outlets_reacquired INTEGER,
    outlets_ceased_other INTEGER,
    outlets_transferred INTEGER,
    outlets_end     INTEGER
);
CREATE INDEX IF NOT EXISTS idx_item20_fdd ON item20_locations(fdd_id);
CREATE INDEX IF NOT EXISTS idx_item20_state_year ON item20_locations(state, year);

CREATE TABLE IF NOT EXISTS fees_and_investment (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fdd_id          INTEGER NOT NULL UNIQUE REFERENCES fdds(id),
    initial_franchise_fee_low   NUMERIC,
    initial_franchise_fee_high  NUMERIC,
    royalty_pct                 NUMERIC,
    royalty_min_monthly         NUMERIC,
    marketing_fee_pct           NUMERIC,
    marketing_min_monthly       NUMERIC,
    tech_fee_monthly            NUMERIC,
    total_investment_low        NUMERIC,
    total_investment_high       NUMERIC,
    liquid_capital_required     NUMERIC,
    net_worth_required          NUMERIC,
    fee_notes                   TEXT
);

CREATE TABLE IF NOT EXISTS affiliate_clicks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    franchisor_id   INTEGER REFERENCES franchisors(id),
    partner         TEXT,
    click_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    visitor_hash    TEXT,
    page_slug       TEXT,
    utm_data        TEXT
);
"""


def slugify(text: str) -> str:
    """Convert a brand/legal name into a URL-safe slug."""
    s = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return s[:80] or "unknown"


def init_db(path: Path = DB_PATH) -> None:
    """Create all tables (idempotent). Creates parent dir if missing.
    Runs migrations for any columns added after the table was first created."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns introduced after initial schema creation. Idempotent."""
    # item19_records: add unit_period, metric_scope, reporting_year if missing
    existing = {r[1] for r in conn.execute("PRAGMA table_info(item19_records)").fetchall()}
    for col, typ in [
        ("reporting_year", "INTEGER"),
        ("unit_period", "TEXT"),
        ("metric_scope", "TEXT"),
    ]:
        if col not in existing:
            conn.execute(f"ALTER TABLE item19_records ADD COLUMN {col} {typ}")
    # fees_and_investment: add quality_flag for range-validation rejections
    existing_fi = {r[1] for r in conn.execute("PRAGMA table_info(fees_and_investment)").fetchall()}
    if "quality_flag" not in existing_fi:
        conn.execute("ALTER TABLE fees_and_investment ADD COLUMN quality_flag TEXT")
    # franchisors: brand_name_key for cross-state entity resolution (2026-05-18)
    existing_fr = {r[1] for r in conn.execute("PRAGMA table_info(franchisors)").fetchall()}
    if "brand_name_key" not in existing_fr:
        conn.execute("ALTER TABLE franchisors ADD COLUMN brand_name_key TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_franchisors_brand_key ON franchisors(brand_name_key, industry)")
        # Backfill existing rows
        from src.dedup import normalize_brand_name
        rows = conn.execute("SELECT id, brand_name, legal_name FROM franchisors").fetchall()
        for r in rows:
            # Prefer brand_name; fall back to legal_name when brand_name is null
            source = r[1] or r[2]
            key = normalize_brand_name(source)
            conn.execute("UPDATE franchisors SET brand_name_key = ? WHERE id = ?", (key, r[0]))
    conn.commit()


@contextmanager
def get_conn(path: Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    """Context-managed connection with row_factory=Row for dict-like access."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def upsert_franchisor(conn: sqlite3.Connection, *, pdf_sha256: str | None = None, **fields) -> int:
    """Insert or update franchisor.

    Lookup order (first match wins):
      1. pdf_sha256 — if provided AND an existing FDD with this sha is already
         attached to a franchisor, reuse that franchisor. Prevents duplicate
         rows when metadata changes between re-extractions of the same PDF
         (stub legal_name 'foo_id12345' → real 'Foo, LLC').
      2. brand_name_key + industry (added 2026-05-18 for cross-state dedup) —
         same brand filed under different state portals produces different
         pdf_sha256 values; this layer reuses the existing franchisor.
      3. slug — fallback for new brands not yet ingested anywhere.

    Cross-state match (layer 2) is conservative:
      - NEVER updates the existing slug — slugs are public URLs.
      - Only fills NULL fields, doesn't overwrite populated ones.

    Returns franchisor.id.
    """
    slug = fields.get("slug")
    if not slug:
        raise ValueError("slug is required")

    # Compute brand_name_key from the incoming brand_name (or legal_name fallback)
    # so it gets persisted on insert AND used for layer-2 lookup.
    from src.dedup import normalize_brand_name, find_franchisor_match
    incoming_key = normalize_brand_name(fields.get("brand_name") or fields.get("legal_name"))
    if incoming_key and "brand_name_key" not in fields:
        fields["brand_name_key"] = incoming_key

    existing = None
    matched_by = None
    # 1. Existing FDD pdf_sha256 → franchisor link
    if pdf_sha256:
        row = conn.execute(
            "SELECT franchisor_id AS id FROM fdds WHERE pdf_sha256 = ?",
            (pdf_sha256,),
        ).fetchone()
        if row:
            existing = row
            matched_by = "pdf_sha256"
    # 2. Cross-state brand_name match
    if not existing:
        match_id = find_franchisor_match(
            conn,
            brand_name=fields.get("brand_name") or fields.get("legal_name"),
            industry=fields.get("industry"),
            state_of_inc=fields.get("state_of_inc"),
        )
        if match_id is not None:
            existing = {"id": match_id}
            matched_by = "brand_name_key"
    # 3. Fall back to slug
    if not existing:
        existing = conn.execute("SELECT id FROM franchisors WHERE slug = ?", (slug,)).fetchone()
        if existing:
            matched_by = "slug"

    if existing:
        fid = int(existing["id"])
        if matched_by == "brand_name_key":
            # Cross-state match: fill NULLs only, never touch slug.
            # Query only the columns the incoming payload would update.
            candidate_cols = [k for k in fields if k != "slug"]
            if candidate_cols:
                # Whitelist column names against the actual schema to avoid SQL injection.
                schema_cols = {r[1] for r in conn.execute("PRAGMA table_info(franchisors)").fetchall()}
                safe_cols = [c for c in candidate_cols if c in schema_cols]
                if safe_cols:
                    row = conn.execute(
                        f"SELECT {', '.join(safe_cols)} FROM franchisors WHERE id = ?",
                        (fid,),
                    ).fetchone()
                    current = dict(zip(safe_cols, row)) if row else {}
                else:
                    current = {}
            else:
                current = {}
            update_fields = {
                k: v for k, v in fields.items()
                if v is not None and k != "slug" and (current.get(k) is None or current.get(k) == "")
            }
        else:
            # pdf_sha256 or slug match: full upsert (existing behavior).
            update_fields = {k: v for k, v in fields.items() if v is not None}
        if update_fields:
            sets = ", ".join(f"{k} = ?" for k in update_fields)
            params = tuple(update_fields.values()) + (fid,)
            conn.execute(
                f"UPDATE franchisors SET {sets}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                params,
            )
        return fid

    # New franchisor — insert
    cols = ", ".join(fields.keys())
    placeholders = ", ".join("?" for _ in fields)
    cur = conn.execute(
        f"INSERT INTO franchisors ({cols}) VALUES ({placeholders})",
        tuple(fields.values()),
    )
    return int(cur.lastrowid)


def upsert_fdd(conn: sqlite3.Connection, **fields) -> int:
    """Insert or update by pdf_sha256. Returns fdd.id."""
    sha = fields.get("pdf_sha256")
    if not sha:
        raise ValueError("pdf_sha256 is required")
    existing = conn.execute("SELECT id FROM fdds WHERE pdf_sha256 = ?", (sha,)).fetchone()
    if existing:
        return int(existing["id"])
    cols = ", ".join(fields.keys())
    placeholders = ", ".join("?" for _ in fields)
    cur = conn.execute(f"INSERT INTO fdds ({cols}) VALUES ({placeholders})", tuple(fields.values()))
    return int(cur.lastrowid)


def _validate_after_write(conn: sqlite3.Connection, fdd_id: int, source: str,
                          *, item19_records=None, yearly=None, state_year=None,
                          fees=None) -> None:
    """Run the ingest validator after a write. Failures and warnings are logged
    to the quality_issues table; nothing is rejected. Audit gate
    (scripts/audit_data.py) reads from quality_issues for the deploy check.
    Best-effort: validator failures must never prevent the write itself."""
    try:
        from src.ingest_validator import (
            validate_item19_records, validate_item20_yearly,
            validate_fees, log_issues,
        )
        if source == "item19" and item19_records is not None:
            issues = validate_item19_records(fdd_id, item19_records)
        elif source == "item20" and yearly is not None and state_year is not None:
            issues = validate_item20_yearly(fdd_id, yearly, state_year)
        elif source == "fees" and fees is not None:
            issues = validate_fees(fdd_id, fees)
        else:
            return
        log_issues(conn, fdd_id, source, issues)
    except Exception:
        # Validator errors must never break the ingest path.
        pass


def replace_item19_records(conn: sqlite3.Connection, fdd_id: int, records: list[dict]) -> int:
    """Delete + reinsert all Item 19 records for an FDD. Returns count inserted.

    Captures the structured unit_period / metric_scope / reporting_year fields
    (added 2026-05-18) when the LLM provides them. Legacy records without these
    fields get NULL; site_gen falls back to metric_raw text inference.
    """
    conn.execute("DELETE FROM item19_records WHERE fdd_id = ?", (fdd_id,))
    cols = ("metric_name", "metric_raw", "cohort_name", "cohort_raw", "outlet_count",
            "reporting_period", "reporting_year", "unit_period", "metric_scope",
            "value_avg", "value_median", "value_min", "value_max",
            "percentile_25", "percentile_75", "pct_above_avg", "page_number",
            "raw_text", "notes", "confidence", "needs_review")
    for r in records:
        conf = r.get("confidence")
        needs_review = (conf is not None and conf < 0.7)
        # Derive reporting_year from reporting_period text if not provided
        reporting_year = r.get("reporting_year")
        if reporting_year is None and r.get("reporting_period"):
            m = re.search(r"\b(20\d{2})\b", str(r["reporting_period"]))
            if m: reporting_year = int(m.group(1))
        vals = (
            r.get("metric_name"), r.get("metric_raw"),
            r.get("cohort_name"), r.get("cohort_raw"),
            r.get("outlet_count"), r.get("reporting_period"),
            reporting_year, r.get("unit_period"), r.get("metric_scope"),
            r.get("value_avg"), r.get("value_median"),
            r.get("value_min"), r.get("value_max"),
            r.get("percentile_25"), r.get("percentile_75"),
            r.get("pct_above_avg"), r.get("page_number"),
            r.get("raw_text"), r.get("notes"),
            conf, needs_review,
        )
        conn.execute(
            f"INSERT INTO item19_records (fdd_id, {', '.join(cols)}) VALUES (?, {', '.join('?' for _ in cols)})",
            (fdd_id, *vals),
        )
    _validate_after_write(conn, fdd_id, "item19", item19_records=records)
    return len(records)


def _normalize_state_for_ingest(raw: str | None) -> str | None:
    """Normalize state codes at ingest time.

    Returns:
      - 2-letter US state code ("CA", "TX", etc.) — when input matches a US state
      - "TOTAL" — preserved (used for systemwide rollup rows)
      - None — when input is non-US (Canada provinces, "AUSTRALIA", "ALL STATES",
        "DC_VA" etc.); these rows get dropped at ingest

    This prevents the inconsistent-state-name class of bugs where "California"
    and "CA" coexisted in the same column.
    """
    if not raw:
        return None
    s = str(raw).strip()
    if not s:
        return None
    upper = s.upper()
    if upper == "TOTAL":
        return "TOTAL"
    # Lazy import to avoid circular deps with state_map
    try:
        from src.state_map import normalize_state_code
    except ImportError:
        from state_map import normalize_state_code
    return normalize_state_code(s)


def replace_item20_locations(conn: sqlite3.Connection, fdd_id: int,
                              yearly: list[dict], state_year: list[dict]) -> int:
    """Delete + reinsert Item 20 rows. Combines yearly_summary + state_year_status.

    State codes are normalized to 2-letter US codes at insert time.
    Non-US rows (Canada, Australia, etc.) are dropped silently.
    """
    conn.execute("DELETE FROM item20_locations WHERE fdd_id = ?", (fdd_id,))
    n = 0
    for row in yearly:
        # yearly_summary rows always go in as "TOTAL" — no state normalization
        conn.execute(
            "INSERT INTO item20_locations (fdd_id, year, outlet_type, state, outlets_start, outlets_end) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (fdd_id, row.get("year"), row.get("outlet_type"), "TOTAL",
             row.get("outlets_start"), row.get("outlets_end")),
        )
        n += 1
    for row in state_year:
        normalized = _normalize_state_for_ingest(row.get("state"))
        if not normalized:
            continue  # drop non-US rows
        conn.execute(
            "INSERT INTO item20_locations (fdd_id, year, state, outlets_start, outlets_opened, "
            "outlets_terminated, outlets_nonrenewed, outlets_reacquired, outlets_ceased_other, outlets_end) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (fdd_id, row.get("year"), normalized,
             row.get("outlets_start"), row.get("outlets_opened"),
             row.get("outlets_terminated"), row.get("outlets_nonrenewed"),
             row.get("outlets_reacquired"), row.get("outlets_ceased_other"),
             row.get("outlets_end")),
        )
        n += 1
    _validate_after_write(conn, fdd_id, "item20", yearly=yearly, state_year=state_year)
    return n


# Plausible bounds per fee field. Values outside the bound are dropped (set to None)
# at ingest, AND a quality_flag is recorded so we know the brand needs review.
# Bounds are intentionally wide — they catch garbage, not edge cases.
_FEE_BOUNDS = {
    "initial_franchise_fee_low":  (0,     1_000_000),
    "initial_franchise_fee_high": (0,     1_000_000),
    "royalty_pct":                (0,     25),
    "royalty_min_monthly":        (0,     50_000),
    "marketing_fee_pct":          (0,     15),
    "marketing_min_monthly":      (0,     50_000),
    "tech_fee_monthly":           (0,     10_000),
    "total_investment_low":       (1_000, 25_000_000),
    "total_investment_high":      (1_000, 25_000_000),
    "liquid_capital_required":    (0,     10_000_000),
    "net_worth_required":         (0,     50_000_000),
}


def _validate_fee(key: str, value, flags: list[str]):
    """Range-check a fee field. Returns the value if plausible, None if out-of-bounds.
    Appends a quality_flag describing the rejection."""
    if value is None:
        return None
    lo, hi = _FEE_BOUNDS.get(key, (None, None))
    if lo is None and hi is None:
        return value
    try:
        v = float(value)
    except (TypeError, ValueError):
        flags.append(f"{key}=non_numeric")
        return None
    if (lo is not None and v < lo) or (hi is not None and v > hi):
        flags.append(f"{key}={value}_out_of_range")
        return None
    return value


def replace_fees(conn: sqlite3.Connection, fdd_id: int, item5: dict | list,
                  item6: dict | list, item7: dict | list) -> None:
    """Replace (insert or update) the fees_and_investment row for an FDD.

    Tolerates item5/6/7 being a LIST of dicts (e.g., Domino's reports
    Traditional + Non-Traditional store types separately). When list-shaped,
    flattens to the broadest range (min(low), max(high)) and notes it.

    Range-validates each field against _FEE_BOUNDS. Out-of-range values are
    dropped (set NULL) and the rejection is recorded in `quality_flag`.
    """
    def _flatten(blob, key_lo: str, key_hi: str):
        """Reduce a list-of-objects to a single dict using broadest range."""
        if not isinstance(blob, list):
            return blob if isinstance(blob, dict) else {}
        if not blob:
            return {}
        lows = [x.get(key_lo) for x in blob if isinstance(x, dict) and x.get(key_lo) is not None]
        highs = [x.get(key_hi) for x in blob if isinstance(x, dict) and x.get(key_hi) is not None]
        # Carry over the first dict's scalar fields (royalty, notes, etc.)
        flat = dict(blob[0]) if isinstance(blob[0], dict) else {}
        if lows: flat[key_lo] = min(lows)
        if highs: flat[key_hi] = max(highs)
        # Carry over notes if multiple
        notes = " | ".join(x.get("fee_notes", "") for x in blob if isinstance(x, dict) and x.get("fee_notes"))
        if notes: flat["fee_notes"] = notes[:500]
        return flat

    item5 = _flatten(item5, "initial_franchise_fee_low", "initial_franchise_fee_high")
    item6 = _flatten(item6, "royalty_pct", "royalty_pct")  # royalty is scalar; takes 1st dict
    item7 = _flatten(item7, "total_investment_low", "total_investment_high")

    flags: list[str] = []
    raw = {
        "initial_franchise_fee_low":  item5.get("initial_franchise_fee_low"),
        "initial_franchise_fee_high": item5.get("initial_franchise_fee_high"),
        "royalty_pct":                item6.get("royalty_pct"),
        "royalty_min_monthly":        item6.get("royalty_min_monthly"),
        "marketing_fee_pct":          item6.get("marketing_fee_pct"),
        "marketing_min_monthly":      item6.get("marketing_min_monthly"),
        "tech_fee_monthly":           item6.get("tech_fee_monthly"),
        "total_investment_low":       item7.get("total_investment_low"),
        "total_investment_high":      item7.get("total_investment_high"),
        "liquid_capital_required":    item7.get("liquid_capital_required"),
        "net_worth_required":         item7.get("net_worth_required"),
    }
    clean = {k: _validate_fee(k, v, flags) for k, v in raw.items()}

    # Consistency check: low <= high
    if (clean["initial_franchise_fee_low"] is not None
        and clean["initial_franchise_fee_high"] is not None
        and clean["initial_franchise_fee_low"] > clean["initial_franchise_fee_high"]):
        clean["initial_franchise_fee_low"], clean["initial_franchise_fee_high"] = (
            clean["initial_franchise_fee_high"], clean["initial_franchise_fee_low"])
        flags.append("fee_low_high_swapped")
    if (clean["total_investment_low"] is not None
        and clean["total_investment_high"] is not None
        and clean["total_investment_low"] > clean["total_investment_high"]):
        clean["total_investment_low"], clean["total_investment_high"] = (
            clean["total_investment_high"], clean["total_investment_low"])
        flags.append("inv_low_high_swapped")

    quality_flag = "; ".join(flags) if flags else None

    conn.execute("DELETE FROM fees_and_investment WHERE fdd_id = ?", (fdd_id,))
    conn.execute(
        """INSERT INTO fees_and_investment (
            fdd_id, initial_franchise_fee_low, initial_franchise_fee_high,
            royalty_pct, royalty_min_monthly, marketing_fee_pct, marketing_min_monthly,
            tech_fee_monthly, total_investment_low, total_investment_high,
            liquid_capital_required, net_worth_required, fee_notes, quality_flag
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (fdd_id,
         clean["initial_franchise_fee_low"], clean["initial_franchise_fee_high"],
         clean["royalty_pct"], clean["royalty_min_monthly"],
         clean["marketing_fee_pct"], clean["marketing_min_monthly"],
         clean["tech_fee_monthly"],
         clean["total_investment_low"], clean["total_investment_high"],
         clean["liquid_capital_required"], clean["net_worth_required"],
         (item5.get("fee_notes") or item6.get("fee_notes") or "")[:1000] or None,
         quality_flag),
    )
    _validate_after_write(conn, fdd_id, "fees", fees=clean)
