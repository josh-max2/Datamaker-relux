"""Re-extract the 14 parse-error brands with v2 to clean up partial outputs."""
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

STEMS = [
    "1_800_packouts_id640869",
    "1_800_water_damage_id640558",
    "ace_handyman_services_id640620",
    "anago_cleaning_systems_id640323",
    "archadeck_outdoor_living_id640172",
    "bin_blasters_id641294",
    "bumble_roofing_id640145",
    "insulation_commandos_id641053",
    "jdog_junk_removal_hauling_id639762",
    "mr_rooter_wi_id640790",
    "rebath_2025_mn",
    "servpro_2014",
    "the_patch_boys_id640596",
    "two_men_and_a_junk_truck_id641608",
]
PDF_DIR = Path("data/wi_scrape")


def find_pdf(stem):
    p = PDF_DIR / f"{stem}.pdf"
    if p.exists(): return p
    for sub in ["preflight", "yale"]:
        p2 = Path("data") / sub / f"{stem}.pdf"
        if p2.exists(): return p2
    for c in Path("data").rglob(f"{stem}.pdf"):
        return c
    return None


t0 = time.time()
ok = failed = skipped = 0
for i, stem in enumerate(STEMS, 1):
    pdf = find_pdf(stem)
    if not pdf:
        print(f"[{i:2}/{len(STEMS)}] {stem}: NO PDF — skipping")
        skipped += 1
        continue
    out_dir = Path("output") / stem
    if out_dir.exists():
        shutil.rmtree(out_dir)
    print(f"\n[{i:2}/{len(STEMS)}] {stem}")
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

print(f"\n=== Done: {ok} OK, {failed} failed, {skipped} skipped in {(time.time()-t0)/60:.1f} min ===")
