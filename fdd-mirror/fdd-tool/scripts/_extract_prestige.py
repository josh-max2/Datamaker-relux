"""Sequentially extract the 23 prestige-batch PDFs using extract_v2.

Hardcoded list — avoids running the orchestrator (which would also grab the
30 lower-priority pending PDFs the user wants to skip).
"""
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PDF_DIR = Path("data/wi_scrape")
PRESTIGE_IDS = [
    641453,  # Subway
    640986,  # McDonald's
    640454,  # Dunkin'
    640450,  # Burger King
    640493,  # Taco Bell
    640460,  # Wendy's
    640422,  # Pizza Hut
    640477,  # Domino's
    640412,  # KFC
    640926,  # Jersey Mike's
    639418,  # Planet Fitness
    640660,  # Anytime Fitness
    640671,  # Orangetheory
    641588,  # Massage Envy
    641224,  # The UPS Store
    639774,  # H&R Block
    640577,  # Great Clips
    641106,  # Snap-on
    640775,  # RE/MAX
    640567,  # Century 21
    640569,  # Coldwell Banker
    640784,  # Holiday Inn Express
    640500,  # Kumon
]


def find_pdf(portal_id: int) -> Path | None:
    for p in PDF_DIR.glob(f"*_id{portal_id}.pdf"):
        return p
    return None


def main():
    targets = []
    for pid in PRESTIGE_IDS:
        p = find_pdf(pid)
        if p:
            targets.append(p)
        else:
            print(f"!! missing PDF for id={pid}")

    print(f"\n=== Extracting {len(targets)} prestige PDFs sequentially ===\n")
    ok = failed = 0
    t0 = time.time()
    for i, pdf in enumerate(targets, start=1):
        # Skip if already extracted
        meta = Path("output") / pdf.stem / "metadata.json"
        if meta.exists():
            print(f"[{i:2}/{len(targets)}] {pdf.stem}: SKIP (already extracted)")
            ok += 1
            continue
        print(f"\n[{i:2}/{len(targets)}] {pdf.stem}")
        result = subprocess.run(
            [sys.executable, "scripts/extract_v2.py", str(pdf)],
            capture_output=True, text=True, encoding="utf-8"
        )
        tail = "\n".join(result.stdout.strip().splitlines()[-2:])
        print(f"    {tail}")
        if result.returncode == 0 and "OK in" in result.stdout:
            ok += 1
        else:
            failed += 1
            print(f"    !! returncode={result.returncode}")
    elapsed = time.time() - t0
    print(f"\n=== Done: {ok} OK, {failed} failed in {elapsed/60:.1f} min ===")


if __name__ == "__main__":
    main()
