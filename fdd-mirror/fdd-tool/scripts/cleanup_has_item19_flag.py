"""One-time DB cleanup: make fdds.has_item19 consistent with actual records.

The audit (2026-05-19) found 11 brands where the flag was inconsistent with the
records in item19_records. After this script runs:
  - has_item19 = 1 iff item19_records exist for the FDD
  - has_item19 = 0 iff no records exist

After Stage 2 (derived.py), templates use derived.disclosure_status() instead
of reading the flag directly, so correctness no longer depends on this field.
But the field shouldn't lie — running this cleanup keeps the DB honest.

Idempotent — safe to run multiple times.
"""
from __future__ import annotations
import argparse
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.db import DB_PATH


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Show what would change; don't write.")
    ap.add_argument("--db", default=str(DB_PATH))
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    # Find inconsistencies
    rows = conn.execute("""
        SELECT d.id AS fdd_id, fr.slug, fr.brand_name,
               d.has_item19,
               (SELECT COUNT(*) FROM item19_records WHERE fdd_id = d.id) AS n_records
        FROM fdds d
        JOIN franchisors fr ON fr.id = d.franchisor_id
        ORDER BY fr.slug
    """).fetchall()

    to_set_1: list[tuple[int, str]] = []
    to_set_0: list[tuple[int, str]] = []
    for r in rows:
        flag = bool(r["has_item19"])
        has_records = r["n_records"] > 0
        if has_records and not flag:
            to_set_1.append((r["fdd_id"], f"{r['slug']} (n_records={r['n_records']})"))
        elif not has_records and flag:
            to_set_0.append((r["fdd_id"], r["slug"]))

    print(f"Would SET has_item19 = 1 for {len(to_set_1)} FDDs:")
    for fid, label in to_set_1:
        print(f"  fdd.id={fid}  {label}")
    print(f"\nWould SET has_item19 = 0 for {len(to_set_0)} FDDs:")
    for fid, label in to_set_0:
        print(f"  fdd.id={fid}  {label}")

    if args.dry_run:
        print("\n(dry-run — no changes made)")
        return 0

    if not (to_set_1 or to_set_0):
        print("\nNo changes needed. DB is consistent.")
        return 0

    for fid, _ in to_set_1:
        conn.execute("UPDATE fdds SET has_item19 = 1 WHERE id = ?", (fid,))
    for fid, _ in to_set_0:
        conn.execute("UPDATE fdds SET has_item19 = 0 WHERE id = ?", (fid,))
    conn.commit()
    print(f"\nCommitted. Set 1: {len(to_set_1)}, Set 0: {len(to_set_0)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
