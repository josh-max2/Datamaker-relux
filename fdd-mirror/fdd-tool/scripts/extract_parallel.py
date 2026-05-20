"""Run extract.py concurrently across N PDFs using ThreadPoolExecutor.

Each worker calls src.extract.run() on a different PDF. The extract module
is thread-safe (no module globals; each call captures its own out_dir).
The Anthropic SDK is thread-safe for sync calls.

Per-PDF errors are isolated — one failure doesn't kill the batch. Workers
write to disk in their own output dirs so no I/O conflict.

Defaults:
  - 4 concurrent workers (well under Anthropic rate limits)
  - verbose=False per worker (interleaved output would be noise; aggregate
    progress is printed instead)

Usage:
    python scripts/extract_parallel.py output/_pilot_mn_5.json
    python scripts/extract_parallel.py output/_pilot_mn_5.json --workers 5
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import extract


def extract_one(pdf_path: Path) -> dict:
    """Worker function: run extract on one PDF. Returns a result dict.
    Errors are caught and returned rather than raised — keeps the pool
    healthy if one PDF has a problem.
    """
    t0 = time.time()
    try:
        out_dir = extract.run(pdf_path, verbose=False)
        # Load the summary
        summary_path = out_dir / "_run_summary.json"
        if summary_path.exists():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        else:
            summary = {}
        return {
            "pdf": str(pdf_path),
            "out_dir": str(out_dir),
            "elapsed_sec": round(time.time() - t0, 1),
            "total_cost_usd": summary.get("total_cost_usd"),
            "items": summary.get("items", {}),
            "status": "ok",
        }
    except Exception as e:
        return {
            "pdf": str(pdf_path),
            "elapsed_sec": round(time.time() - t0, 1),
            "status": "error",
            "error": f"{type(e).__name__}: {e}",
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", help="Path to a pilot manifest JSON (list of entries with `pdf_path`)")
    ap.add_argument("--workers", type=int, default=4,
                    help="Concurrent workers (default 4). Anthropic Tier 1 supports more, "
                         "but 4 keeps you well under any RPM/TPM ceiling.")
    ap.add_argument("--out", help="Path to write aggregate result JSON (default: output/_parallel_results.json)")
    args = ap.parse_args()

    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pdfs = []
    for entry in manifest:
        p = Path(entry["pdf_path"])
        if p.exists():
            pdfs.append(p)
        else:
            print(f"  [SKIP missing PDF] {entry.get('franchisor')}: {p}")

    if not pdfs:
        print("No PDFs to process.")
        return 1

    print(f"Manifest: {manifest_path}")
    print(f"PDFs to extract: {len(pdfs)}")
    print(f"Workers: {args.workers}\n")

    t_start = time.time()
    results: list[dict] = []
    completed = 0

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(extract_one, pdf): pdf for pdf in pdfs}
        for fut in as_completed(futures):
            pdf = futures[fut]
            result = fut.result()
            results.append(result)
            completed += 1
            cost_str = f"${result['total_cost_usd']:.4f}" if result.get("total_cost_usd") else "—"
            status_mark = "✓" if result["status"] == "ok" else "✗"
            print(f"  [{completed}/{len(pdfs)}] {status_mark} {pdf.stem[:55]:<57}  "
                  f"{result['elapsed_sec']:>6.1f}s  {cost_str:>9}")
            if result["status"] == "error":
                print(f"           ERROR: {result['error']}")

    t_total = time.time() - t_start
    success = [r for r in results if r["status"] == "ok"]
    failed = [r for r in results if r["status"] != "ok"]
    total_cost = sum(r.get("total_cost_usd", 0) or 0 for r in success)
    avg_pdf_time = sum(r["elapsed_sec"] for r in success) / max(1, len(success))

    print(f"\n{'='*80}\nBATCH SUMMARY\n{'='*80}")
    print(f"  Total wall-clock     : {t_total:.1f}s  ({t_total/60:.1f}m)")
    print(f"  Succeeded            : {len(success)}/{len(pdfs)}")
    print(f"  Failed               : {len(failed)}")
    print(f"  Total cost           : ${total_cost:.4f}")
    print(f"  Avg per-PDF cost     : ${total_cost/max(1,len(success)):.4f}")
    print(f"  Avg per-PDF time     : {avg_pdf_time:.1f}s (sequential equiv: {len(success)*avg_pdf_time/60:.1f}m)")
    print(f"  Speedup vs sequential: {(len(success)*avg_pdf_time/t_total):.1f}×")

    out_path = Path(args.out) if args.out else (ROOT / "output" / "_parallel_results.json")
    out_path.write_text(json.dumps({
        "manifest": str(manifest_path),
        "workers": args.workers,
        "started_at": datetime.fromtimestamp(t_start).isoformat(),
        "total_wall_clock_sec": round(t_total, 1),
        "results": results,
    }, indent=2), encoding="utf-8")
    print(f"\n  Aggregate JSON       : {out_path}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
