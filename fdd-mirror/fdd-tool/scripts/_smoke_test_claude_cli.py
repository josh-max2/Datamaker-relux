"""Smoke test: run ONE PDF through the spawned-Claude flow and compare to the
existing API-based extraction. Saves to a temp dir so we don't disturb production.

Run from fdd-tool/:
    uv run python scripts/_smoke_test_claude_cli.py
"""
import json
import shutil
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

# Import the invoke_claude function from extract_loop (but redirect output dir)
import scripts.extract_loop as el

# Pick a small-ish PDF that's already extracted (for comparison)
TEST_PDF_NAME = "1_800_packouts_id640869.pdf"
SMOKE_OUTPUT_BASE = Path("output_smoketest")

def main():
    pdf = Path("data/wi_scrape") / TEST_PDF_NAME
    if not pdf.exists():
        print(f"!! test PDF missing: {pdf}")
        sys.exit(1)

    # Patch the OUTPUT_DIR globally so spawned claude writes into the temp area
    SMOKE_OUTPUT_BASE.mkdir(exist_ok=True)
    el.OUTPUT_DIR = SMOKE_OUTPUT_BASE
    target_dir = SMOKE_OUTPUT_BASE / pdf.stem
    if target_dir.exists():
        shutil.rmtree(target_dir)

    print(f"=== smoke test: {TEST_PDF_NAME} ===")
    print(f"  output dir: {target_dir.resolve()}")
    print(f"  claude bin: {el.CLAUDE_BIN}")
    print(f"  timeout:    {el.PER_INVOCATION_TIMEOUT_SEC}s")
    print(f"  env scrub:  ANTHROPIC_API_KEY removed from spawned env\n")

    # Override the prompt's output dir to point to the smoke test location
    original_build = el.build_prompt
    def build_for_smoke(pdf_path):
        p = original_build(pdf_path)
        # Replace any references to `output/` in the prompt with our temp dir
        p = p.replace("output/{PDF_STEM}", f"{SMOKE_OUTPUT_BASE}/{pdf_path.stem}")
        p = p.replace(f"output/{pdf_path.stem}", f"{SMOKE_OUTPUT_BASE}/{pdf_path.stem}")
        return p
    el.build_prompt = build_for_smoke

    t0 = time.time()
    success, out_tail, elapsed = el.invoke_claude(pdf)
    print(f"\n=== claude -p exited ===")
    print(f"  success:  {success}")
    print(f"  elapsed:  {elapsed}s")
    print(f"  output tail:")
    print(out_tail[-1500:])

    # Inventory what was written
    print(f"\n=== files written to {target_dir} ===")
    if target_dir.exists():
        for f in sorted(target_dir.iterdir()):
            sz = f.stat().st_size
            print(f"  {f.name}  ({sz} bytes)")
        # Compare against original API extraction
        print(f"\n=== diff vs original API extraction ===")
        original = Path("output") / pdf.stem
        for name in ("metadata.json", "item5_initial_fee.json", "item6_ongoing_fees.json",
                     "item7_investment.json", "item19_fpr.json", "item20_outlets.json"):
            smoke_f = target_dir / name
            orig_f = original / name
            if not smoke_f.exists() and not orig_f.exists():
                continue
            if not smoke_f.exists():
                print(f"  {name}: MISSING in smoke output (original has it)")
                continue
            if not orig_f.exists():
                print(f"  {name}: only in smoke (original missing)")
                continue
            try:
                a = json.loads(smoke_f.read_text(encoding="utf-8"))
                b = json.loads(orig_f.read_text(encoding="utf-8"))
                # Compare a few key fields
                if name == "metadata.json":
                    keys = ("legal_name", "brand_name", "state_of_inc", "filing_year")
                elif name.startswith("item5"):
                    keys = ("initial_franchise_fee_low", "initial_franchise_fee_high")
                elif name.startswith("item19"):
                    a_r = a.get("records", [])
                    b_r = b.get("records", [])
                    print(f"  {name}: smoke={len(a_r)} records, original={len(b_r)} records, "
                          f"has_item19 smoke={a.get('has_item19')} orig={b.get('has_item19')}")
                    continue
                elif name.startswith("item20"):
                    a_y = len(a.get("yearly_summary", []))
                    b_y = len(b.get("yearly_summary", []))
                    print(f"  {name}: smoke yearly={a_y}, original yearly={b_y}")
                    continue
                else:
                    keys = None
                if keys:
                    matches = sum(1 for k in keys if a.get(k) == b.get(k))
                    print(f"  {name}: {matches}/{len(keys)} key fields match — "
                          f"smoke={[a.get(k) for k in keys]}, "
                          f"orig={[b.get(k) for k in keys]}")
            except Exception as e:
                print(f"  {name}: compare failed: {e}")
    else:
        print(f"  (no files written — smoke test FAILED)")

if __name__ == "__main__":
    main()
