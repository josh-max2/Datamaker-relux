"""Sequential extract loop using `claude -p` (Max plan, $0 marginal cost).

Reads a priority queue JSON and runs extract_v2.py on each PDF one at a time.
Per-PDF outputs land in output/{stem}/ atomically — if credits run out, all
completed extracts persist. Progress saved to output/_max_plan_progress.json
after each PDF so we can resume.

Resume behavior: PDFs that already have a full set of extract files
(metadata + item5/6/7/19/20) are skipped.

Usage:
    python scripts/max_plan_extract_loop.py output/_max_plan_queue.json
    python scripts/max_plan_extract_loop.py output/_max_plan_queue.json --model sonnet
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PROGRESS_PATH = ROOT / "output" / "_max_plan_progress.json"


def fully_extracted(stem: str) -> bool:
    """A PDF is 'fully extracted' if all 6 standard output files exist AND
    none of the item5/6/7 files are _section_not_found. (Items 19/20 may be
    legitimately not found.)"""
    out = ROOT / "output" / stem
    required = ["metadata.json", "item5_initial_fee.json", "item6_ongoing_fees.json",
                "item7_investment.json", "item19_fpr.json", "item20_outlets.json"]
    for fn in required:
        p = out / fn
        if not p.exists():
            return False
    # Also check item5/6/7 aren't bare "_section_not_found" stubs
    for fn in ("item5_initial_fee.json", "item6_ongoing_fees.json", "item7_investment.json"):
        try:
            data = json.loads((out / fn).read_text(encoding="utf-8"))
            if data.get("_section_not_found"):
                return False
        except Exception:
            return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("queue", help="Priority queue JSON (output of survey/builder)")
    ap.add_argument("--model", default="sonnet", help="claude alias (sonnet, opus, haiku)")
    ap.add_argument("--limit", type=int, default=100, help="Max PDFs to process")
    ap.add_argument("--force", action="store_true",
                    help="Re-extract even if already fully extracted")
    args = ap.parse_args()

    queue = json.loads(Path(args.queue).read_text(encoding="utf-8"))
    print(f"Loaded queue: {len(queue)} entries")
    print(f"Model: {args.model}  limit: {args.limit}\n")

    # Load existing progress (for resume)
    progress = {}
    if PROGRESS_PATH.exists():
        progress = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
    progress.setdefault("results", [])
    progress.setdefault("started_at", datetime.now().isoformat())
    done_paths = {r["pdf_path"] for r in progress["results"] if r.get("ok")}

    n_processed = 0
    n_skipped = 0
    n_ok = 0
    n_fail = 0
    total_elapsed = 0
    started = time.time()

    for i, entry in enumerate(queue, 1):
        if n_processed >= args.limit:
            break
        pdf_path = Path(entry["pdf_path"])
        stem = pdf_path.stem
        brand = entry.get("brand", stem)

        if not args.force and (pdf_path.as_posix() in done_paths or fully_extracted(stem)):
            n_skipped += 1
            continue

        n_processed += 1
        print(f"[{n_processed}/{args.limit}] ({i}/{len(queue)}) {brand} ({entry.get('reason', '')})")

        t0 = time.time()
        # Spawn extract_v2.py as a subprocess; it handles claude -p call
        cmd = [str(ROOT / ".venv" / "Scripts" / "python.exe"),
               str(ROOT / "scripts" / "extract_v2.py"),
               str(pdf_path), "--model", args.model]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                   timeout=900, encoding="utf-8")
            elapsed = time.time() - t0
            total_elapsed += elapsed
            ok = proc.returncode == 0 and fully_extracted(stem)
            if ok:
                n_ok += 1
                # Pull cost from extract_v2 manifest if available
                manifest = json.loads((ROOT / "output" / "_extract_v2.json").read_text(encoding="utf-8")) \
                    if (ROOT / "output" / "_extract_v2.json").exists() else {"extractions": {}}
                entry_manifest = manifest.get("extractions", {}).get(stem, {})
                cost = (entry_manifest.get("usage") or {}).get("total_cost_usd")
                cost_str = f"${cost:.4f}" if cost else "?"
                print(f"  -> OK ({elapsed:.0f}s, api-equiv {cost_str})")
                progress["results"].append({
                    "pdf_path": pdf_path.as_posix(), "brand": brand,
                    "ok": True, "elapsed_sec": round(elapsed, 1),
                    "api_equiv_usd": cost,
                    "finished_at": datetime.now().isoformat(),
                })
            else:
                n_fail += 1
                err = proc.stderr[-200:] if proc.stderr else (proc.stdout[-200:] if proc.stdout else "no output")
                print(f"  -> FAIL ({elapsed:.0f}s): rc={proc.returncode}  err={err.strip()[:120]}")
                progress["results"].append({
                    "pdf_path": pdf_path.as_posix(), "brand": brand,
                    "ok": False, "elapsed_sec": round(elapsed, 1),
                    "error": err[:500],
                    "finished_at": datetime.now().isoformat(),
                })
        except subprocess.TimeoutExpired:
            n_fail += 1
            elapsed = time.time() - t0
            print(f"  -> TIMEOUT ({elapsed:.0f}s)")
            progress["results"].append({
                "pdf_path": pdf_path.as_posix(), "brand": brand,
                "ok": False, "elapsed_sec": round(elapsed, 1), "error": "TIMEOUT",
                "finished_at": datetime.now().isoformat(),
            })

        # Save progress after EVERY PDF so credit-out doesn't lose state
        progress["last_updated"] = datetime.now().isoformat()
        progress["totals"] = {"processed": n_processed, "ok": n_ok, "failed": n_fail,
                               "skipped": n_skipped, "elapsed_sec": round(time.time() - started, 1)}
        PROGRESS_PATH.write_text(json.dumps(progress, indent=2), encoding="utf-8")

    wall = time.time() - started
    print(f"\n{'='*60}\nSUMMARY\n{'='*60}")
    print(f"  Processed: {n_processed}  OK: {n_ok}  Failed: {n_fail}  Skipped: {n_skipped}")
    print(f"  Wall clock: {wall:.0f}s ({wall/60:.1f}m)")
    print(f"  Progress: {PROGRESS_PATH}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
