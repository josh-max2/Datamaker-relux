"""One-time fix: NULL out 4 Glass Doctor value_median values that exceed value_max
(mathematically impossible). Likely an extraction-column confusion in the source
parse. The records keep their avg/min/max/raw_text; only the suspect median is
suppressed pending a Glass Doctor re-extraction.

Records: 14304, 14305, 14309, 14310 (HB Quartile 2, HB Q3, Auto Q3, Auto Q4).
"""
from __future__ import annotations
import sqlite3, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.db import DB_PATH

c = sqlite3.connect(DB_PATH)
c.row_factory = sqlite3.Row

# Identify any value_median that exceeds value_max
bad = c.execute("""
    SELECT id, value_min, value_median, value_max, cohort_raw
    FROM item19_records
    WHERE value_median IS NOT NULL AND value_max IS NOT NULL
      AND value_median > value_max
""").fetchall()
print(f"Records to suppress: {len(bad)}")
for r in bad:
    print(f"  id={r['id']}  median={r['value_median']} max={r['value_max']}  cohort={r['cohort_raw'][:50]}")
if not bad:
    print("Clean — nothing to do.")
    sys.exit(0)

# Null the medians + flag them in notes for future re-extraction
for r in bad:
    note_addition = ("EXTRACTION FLAG 2026-05-19: source raw_text reported "
                     f"median={r['value_median']} > max={r['value_max']} which is impossible. "
                     "Median suppressed; needs re-extraction to recover correct value.")
    c.execute("""
        UPDATE item19_records SET
          value_median = NULL,
          notes = CASE WHEN notes IS NULL OR notes = '' THEN ?
                       ELSE notes || ' | ' || ? END
        WHERE id = ?
    """, (note_addition, note_addition, r["id"]))
c.commit()
print(f"\nCommitted. Set value_median=NULL on {len(bad)} records, notes updated.")
