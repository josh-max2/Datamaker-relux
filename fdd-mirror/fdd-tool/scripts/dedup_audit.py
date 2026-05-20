"""Audit + merge tool for duplicate franchisor rows.

The cross-state dedup logic in src/dedup.py protects the WRITE path: future
ingests with brand_name + industry matching an existing row reuse that row
instead of creating a new one.

This tool covers cases where duplicates already exist in the DB — e.g., the
MN CARDS expansion landed Subway twice before the write-path check was added,
or a normalization rule was changed and old rows no longer collapse.

Usage:
    # Audit only (default — dry run, JSON to stdout)
    python scripts/dedup_audit.py

    # Audit + propose merges (still dry run; shows which IDs would be merged)
    python scripts/dedup_audit.py --propose-merges

    # Actually merge — DESTRUCTIVE. Re-points fdds.franchisor_id, deletes
    # the obsolete franchisor rows. Slug of the KEPT row is preserved.
    python scripts/dedup_audit.py --merge

Merge rule (when a group has >1 franchisor row):
    Keep the row with the OLDEST id (most likely to have published URLs +
    backlinks). All other rows in the group are dropped after re-pointing
    their FDDs to the keeper. The keeper's slug is never changed.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.db import DB_PATH, init_db  # noqa: E402
from src.dedup import normalize_brand_name  # noqa: E402


def find_duplicate_groups(conn: sqlite3.Connection) -> list[dict]:
    """Return groups of franchisor rows that share brand_name_key + industry."""
    rows = conn.execute("""
        SELECT brand_name_key, industry, COUNT(*) AS n, GROUP_CONCAT(id) AS ids
        FROM franchisors
        WHERE brand_name_key IS NOT NULL AND brand_name_key != ''
              AND industry IS NOT NULL
        GROUP BY brand_name_key, industry
        HAVING n > 1
        ORDER BY n DESC
    """).fetchall()

    groups = []
    for r in rows:
        ids = [int(x) for x in r["ids"].split(",")]
        member_rows = conn.execute(
            f"SELECT id, legal_name, brand_name, slug, industry, state_of_inc, created_at "
            f"FROM franchisors WHERE id IN ({','.join('?' for _ in ids)}) "
            f"ORDER BY id ASC",
            ids,
        ).fetchall()
        members = []
        for m in member_rows:
            fdd_count = conn.execute(
                "SELECT COUNT(*) FROM fdds WHERE franchisor_id = ?", (m["id"],)
            ).fetchone()[0]
            members.append({
                "id": m["id"],
                "legal_name": m["legal_name"],
                "brand_name": m["brand_name"],
                "slug": m["slug"],
                "industry": m["industry"],
                "state_of_inc": m["state_of_inc"],
                "created_at": m["created_at"],
                "fdd_count": fdd_count,
            })
        # Keep the lowest id (oldest, most likely indexed in SEO).
        keeper = members[0]
        drops = members[1:]
        groups.append({
            "brand_name_key": r["brand_name_key"],
            "industry": r["industry"],
            "n_franchisors": r["n"],
            "keeper": keeper,
            "drops": drops,
        })
    return groups


def merge_group(conn: sqlite3.Connection, group: dict) -> dict:
    """Re-point all child rows from group['drops'] to group['keeper'] and
    delete the drop franchisor rows. Returns a report of what was done.

    Children to re-point:
      - fdds.franchisor_id (cascades to item19_records, item20_locations,
        fees_and_investment via their fdd_id FKs — no action needed there)
      - affiliate_clicks.franchisor_id
    """
    keep_id = group["keeper"]["id"]
    drop_ids = [d["id"] for d in group["drops"]]
    report = {
        "keeper_id": keep_id,
        "keeper_slug": group["keeper"]["slug"],
        "drop_ids": drop_ids,
        "fdds_repointed": 0,
        "clicks_repointed": 0,
    }
    for drop_id in drop_ids:
        cur = conn.execute(
            "UPDATE fdds SET franchisor_id = ? WHERE franchisor_id = ?",
            (keep_id, drop_id),
        )
        report["fdds_repointed"] += cur.rowcount
        cur = conn.execute(
            "UPDATE affiliate_clicks SET franchisor_id = ? WHERE franchisor_id = ?",
            (keep_id, drop_id),
        )
        report["clicks_repointed"] += cur.rowcount
        conn.execute("DELETE FROM franchisors WHERE id = ?", (drop_id,))
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--propose-merges", action="store_true",
                    help="Show which IDs would be merged (still dry-run).")
    ap.add_argument("--merge", action="store_true",
                    help="DESTRUCTIVE: actually perform the merge. Use with care.")
    ap.add_argument("--db", default=str(DB_PATH),
                    help="Path to the SQLite DB (default: data/db.sqlite).")
    args = ap.parse_args()

    init_db(Path(args.db))  # ensures brand_name_key column exists
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    groups = find_duplicate_groups(conn)

    if not groups:
        print(json.dumps({
            "status": "clean",
            "duplicate_groups": 0,
            "message": "No duplicate franchisor groups found.",
        }, indent=2))
        return 0

    if args.merge:
        # Destructive path. Commit per-group so a failure partway leaves
        # the DB in a usable (though partially-merged) state.
        reports = []
        for g in groups:
            rep = merge_group(conn, g)
            conn.commit()
            reports.append({**rep, "brand_name_key": g["brand_name_key"]})
        print(json.dumps({
            "status": "merged",
            "groups_merged": len(reports),
            "reports": reports,
        }, indent=2))
        return 0

    # Dry run (default) — surface what was found.
    out = {
        "status": "duplicates_found",
        "duplicate_groups": len(groups),
        "groups": groups,
    }
    if args.propose_merges:
        for g in out["groups"]:
            g["proposed_action"] = {
                "keep_id": g["keeper"]["id"],
                "keep_slug": g["keeper"]["slug"],
                "drop_ids": [d["id"] for d in g["drops"]],
                "note": "Run with --merge to execute. Slug stability preserved.",
            }
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
