"""Entity resolution + dedup for franchisors across multi-state filings.

Two layers of identity matching, in precedence order:

  1. (existing) pdf_sha256 → fdds → franchisor_id
       Same file bytes already ingested under a franchisor.

  2. (new here) brand_name_key + industry — see find_franchisor_match()
       Different PDFs (state addendums, year-to-year refiling) but same
       brand. brand_name normalization is aggressive (lowercase, strip all
       non-alphanumeric) so "Domino's Pizza" and "DOMINOS PIZZA" collapse.

  3. (existing fallback) slug match

Layer 2 invariants for the write path:
  - NEVER changes the slug of an existing franchisor (slugs are public URLs
    in the live sitemap; mutating one orphans pages and breaks SEO).
  - Only fills NULL fields on the existing franchisor — does not overwrite
    populated ones. Cross-state ingest can have differing legal_name forms
    ("DOMINO'S PIZZA, LLC" vs "Dominos Pizza Franchising LLC"); the first
    one ingested wins.

Run scripts/dedup_audit.py for a separate (non-write-path) merge tool that
handles cases where duplicates already exist in the DB.
"""
from __future__ import annotations

import re
import sqlite3


_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def normalize_brand_name(raw: str | None) -> str:
    """Lowercase + strip all non-alphanumeric.

    Tested against cross-state variants (apostrophes, slashes, hyphens, case):
      "Domino's Pizza", "DOMINO'S PIZZA", "Dominos Pizza"  →  "dominospizza"
      "RE/MAX", "REMAX", "Re/Max"                           →  "remax"
      "Mr. Rooter", "MR ROOTER", "Mr Rooter"                →  "mrrooter"

    Returns empty string for None or all-whitespace input.
    """
    if not raw:
        return ""
    return _NON_ALNUM_RE.sub("", raw.lower())


def find_franchisor_match(
    conn: sqlite3.Connection,
    *,
    brand_name: str | None,
    industry: str | None,
    state_of_inc: str | None = None,
) -> int | None:
    """Return existing franchisor.id for the same brand, or None.

    Match key: (brand_name_key, industry). Industry is required as a guard
    against false positives — generic brand names ("ProClean") could collide
    across very different businesses.

    When multiple candidates match brand_name_key + industry, state_of_inc
    breaks the tie if available; otherwise returns the lowest id (oldest row).
    """
    key = normalize_brand_name(brand_name)
    if not key or not industry:
        return None
    rows = conn.execute(
        "SELECT id, state_of_inc FROM franchisors "
        "WHERE brand_name_key = ? AND industry = ? "
        "ORDER BY id ASC",
        (key, industry),
    ).fetchall()
    if not rows:
        return None
    if len(rows) == 1:
        return int(rows[0][0])
    # Tiebreaker: prefer state_of_inc agreement
    if state_of_inc:
        for r in rows:
            if r[1] and r[1] == state_of_inc:
                return int(r[0])
    return int(rows[0][0])
