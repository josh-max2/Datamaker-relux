"""Run extract.py on the 5 MN pilot PDFs sequentially. Capture per-brand
timing + cost + tokens. Then ingest into DB and run audit gate.

Usage:
    python scripts/extract_mn_5.py
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import extract


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "output" / "_pilot_mn_5.json"


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    print(f"Loaded {len(manifest)} entries from {MANIFEST}\n")

    results = []
    for i, entry in enumerate(manifest, 1):
        pdf = Path(entry["pdf_path"])
        if not pdf.exists():
            print(f"[{i}] SKIP {entry['franchisor']}: pdf missing {pdf}")
            continue
        print(f"\n{'='*80}")
        print(f"[{i}/{len(manifest)}]  {entry['franchisor']}")
        print(f"  PDF: {pdf}")
        print(f"{'='*80}")
        t0 = time.time()
        try:
            extract.run(pdf)
            dt = time.time() - t0
            # Load the summary
            summary_path = ROOT / "output" / pdf.stem / "_run_summary.json"
            if summary_path.exists():
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
                results.append({
                    "franchisor": entry["franchisor"],
                    "pdf_stem": pdf.stem,
                    "elapsed_sec": round(dt, 1),
                    "total_cost_usd": summary.get("total_cost_usd"),
                    "items": summary.get("items", {}),
                })
                print(f"\n  COMPLETE in {dt:.1f}s — ${summary.get('total_cost_usd', 0):.4f}")
            else:
                print(f"\n  Summary not written: {summary_path}")
        except Exception as e:
            print(f"\n  FAIL: {type(e).__name__}: {e}")
            results.append({
                "franchisor": entry["franchisor"],
                "pdf_stem": pdf.stem,
                "error": f"{type(e).__name__}: {e}",
            })

    # Write aggregate report
    aggregate_path = ROOT / "output" / "_pilot_mn_5_extracts.json"
    aggregate_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\n\n{'='*80}\nAGGREGATE\n{'='*80}")
    total_cost = sum(r.get("total_cost_usd", 0) or 0 for r in results)
    total_time = sum(r.get("elapsed_sec", 0) or 0 for r in results)
    n_success = sum(1 for r in results if "total_cost_usd" in r)
    print(f"Success: {n_success}/{len(manifest)}")
    print(f"Total cost: ${total_cost:.4f}  (avg ${total_cost/max(1,n_success):.4f}/FDD)")
    print(f"Total time: {total_time:.1f}s  (avg {total_time/max(1,n_success):.1f}s/FDD)")
    print(f"Aggregate: {aggregate_path}")


if __name__ == "__main__":
    main()
