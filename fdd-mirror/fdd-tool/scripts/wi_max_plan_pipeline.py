"""End-to-end WI pipeline (Max plan, $0 marginal cost):

Picks up where download_wi_candidates.py left off:
  1. Read the WI download manifest (output/_pilot_wi_max_plan.json)
  2. For each entry that has a PDF on disk, build a queue entry
  3. Sequentially extract via extract_v2.py (claude -p)
  4. Save progress per PDF
  5. After every BATCH_SIZE PDFs, run ingest_outputs.py + audit_data.py

Resume-safe: re-run anytime; already-extracted PDFs are skipped.
"""
from __future__ import annotations
import argparse, json, subprocess, sys, time
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
PROGRESS = ROOT / "output" / "_wi_max_plan_progress.json"


def fully_extracted(stem: str) -> bool:
    out = ROOT / "output" / stem
    if not out.exists():
        return False
    summary = out / "_run_summary.json"
    if not summary.exists():
        return False
    # Need at least items 5/6/7 OR clear partial result
    required = ["metadata.json", "item5_initial_fee.json", "item6_ongoing_fees.json",
                "item7_investment.json", "item19_fpr.json", "item20_outlets.json"]
    return all((out / fn).exists() for fn in required)


def run_extract(pdf_path: Path) -> tuple[bool, float, str]:
    """Spawn extract_v2.py. Returns (ok, elapsed_sec, msg)."""
    t0 = time.time()
    cmd = [str(ROOT / ".venv" / "Scripts" / "python.exe"),
           str(ROOT / "scripts" / "extract_v2.py"),
           str(pdf_path), "--model", "sonnet"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=900, encoding="utf-8")
        elapsed = time.time() - t0
        ok = proc.returncode == 0 and fully_extracted(pdf_path.stem)
        msg = "ok" if ok else (proc.stderr[-200:] or proc.stdout[-200:] or "")[:200]
        return ok, elapsed, msg
    except subprocess.TimeoutExpired:
        return False, time.time() - t0, "TIMEOUT"


def run_ingest_and_audit():
    """Run ingest_outputs + audit, return (audit_clean, n_tier1, n_tier2)."""
    print("    >> Running ingest...")
    subprocess.run([str(ROOT / ".venv" / "Scripts" / "python.exe"),
                    str(ROOT / "scripts" / "ingest_outputs.py")],
                   capture_output=True)
    # Run cleanup queries
    cleanup_cmd = [str(ROOT / ".venv" / "Scripts" / "python.exe"), "-c",
                   "import sqlite3, sys; sys.path.insert(0, '.'); from src.db import DB_PATH; "
                   "conn = sqlite3.connect(DB_PATH); "
                   "conn.execute('DELETE FROM item19_records WHERE value_min IS NOT NULL AND value_max IS NOT NULL "
                   "AND ((value_avg IS NOT NULL AND (value_avg < value_min OR value_avg > value_max)) "
                   "OR (value_median IS NOT NULL AND (value_median < value_min OR value_median > value_max)))'); "
                   "conn.execute('UPDATE fdds SET has_item19 = CASE WHEN (SELECT COUNT(*) FROM item19_records WHERE fdd_id = fdds.id) > 0 THEN 1 ELSE 0 END'); "
                   "conn.commit()"]
    subprocess.run(cleanup_cmd, capture_output=True)
    # Audit
    audit = subprocess.run([str(ROOT / ".venv" / "Scripts" / "python.exe"),
                            str(ROOT / "scripts" / "audit_data.py")],
                           capture_output=True, text=True, encoding="utf-8")
    out = audit.stdout
    # Extract tier counts
    import re
    m = re.search(r"(\d+) tier-1 FAILS.+?(\d+) tier-2", out)
    n1 = int(m.group(1)) if m else -1
    n2 = int(m.group(2)) if m else -1
    return (n1 == 0), n1, n2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="output/_pilot_wi_max_plan.json")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--batch-size", type=int, default=10,
                    help="Run ingest+audit after every N successful extracts")
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    # Skip dedup'd entries
    manifest = [e for e in manifest if not e.get("was_duplicate")]
    print(f"Manifest: {len(manifest)} non-duplicate entries\n")

    progress = {"started_at": datetime.now().isoformat(), "results": []}
    if PROGRESS.exists():
        progress = json.loads(PROGRESS.read_text(encoding="utf-8"))
        progress.setdefault("results", [])
    done_paths = {r["pdf_path"] for r in progress["results"] if r.get("ok")}

    n_processed = n_ok = n_fail = n_skipped = 0
    batch_count = 0
    t_start = time.time()

    for i, entry in enumerate(manifest, 1):
        if n_processed >= args.limit:
            break
        pdf_path = Path(entry["pdf_path"])
        stem = pdf_path.stem
        brand = entry.get("franchise_name") or entry.get("franchisor") or stem

        if pdf_path.as_posix() in done_paths or fully_extracted(stem):
            n_skipped += 1
            continue

        if not pdf_path.exists():
            print(f"  [SKIP] {i:>3}/{len(manifest)} {brand}: PDF missing")
            n_skipped += 1
            continue

        n_processed += 1
        print(f"  [{n_processed}] {brand[:50]:<52}", flush=True)
        ok, elapsed, msg = run_extract(pdf_path)
        if ok:
            n_ok += 1
            batch_count += 1
            mark = "OK"
        else:
            n_fail += 1
            mark = "FAIL"
        print(f"      -> {mark} ({elapsed:.0f}s){' ' + msg if mark == 'FAIL' else ''}")

        progress["results"].append({
            "pdf_path": pdf_path.as_posix(), "brand": brand,
            "ok": ok, "elapsed_sec": round(elapsed, 1),
            "error": "" if ok else msg,
            "finished_at": datetime.now().isoformat(),
        })
        progress["totals"] = {"processed": n_processed, "ok": n_ok, "failed": n_fail,
                               "skipped": n_skipped, "elapsed_sec": round(time.time() - t_start, 1)}
        PROGRESS.write_text(json.dumps(progress, indent=2), encoding="utf-8")

        # Periodic audit checkpoint
        if batch_count >= args.batch_size:
            print(f"\n    === Checkpoint: ingest + audit after {batch_count} new extracts ===")
            clean, t1, t2 = run_ingest_and_audit()
            print(f"    >> Audit: tier-1 fails={t1}  tier-2 warns={t2}  {'GREEN' if clean else 'RED'}\n")
            batch_count = 0

    # Final ingest + audit
    print(f"\nFinal ingest + audit...")
    clean, t1, t2 = run_ingest_and_audit()
    print(f"Audit: tier-1 fails={t1}  tier-2 warns={t2}  {'GREEN' if clean else 'RED'}")

    print(f"\n{'='*60}")
    print(f"DONE: processed={n_processed} ok={n_ok} failed={n_fail} skipped={n_skipped}")
    print(f"Wall clock: {(time.time() - t_start)/60:.1f}m")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
