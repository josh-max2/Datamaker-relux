"""Pilot batch: scrape + extract 20 home-services franchisors from WI portal.

Mix per user's spec:
  - Large (likely 100+ outlets): Servpro, 1-800-GOT-JUNK, Roto-Rooter, Two Men and a Truck
  - Mid: The Maids, Molly Maid, Merry Maids, Anago, Lawn Doctor, Bath Fitter,
         Ace Handyman, Junk King, Mr. Handyman, JDog
  - Small/regional: Bin Blasters, Bumble Roofing, Insulation Commandos,
                    Patch Boys, Lightspeed Restoration, Mosquito Sheriff

Two phases:
  Phase A — scrape: find each franchisor's currently-Registered filing and download PDF
  Phase B — extract: run src.extract on each downloaded PDF

Writes a manifest JSON with per-brand status + costs.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from src.scrapers.wisconsin import WisconsinScraper, latest_active

PILOT_BRANDS = [
    # Large
    "Servpro",
    "1-800-GOT-JUNK",
    "Roto-Rooter",
    "Two Men and a Truck",
    # Mid
    "The Maids International",
    "Molly Maid",
    "Merry Maids",
    "Anago",
    "Lawn Doctor",
    "Bath Fitter",
    "Ace Handyman",
    "Junk King",
    "Mr. Handyman",
    "JDog",
    # Small / regional
    "Bin Blasters",
    "Bumble Roofing",
    "Insulation Commandos",
    "Patch Boys",
    "Lightspeed Restoration",
    "Mosquito Sheriff",
]

DEST = Path("data/wi_scrape")
MANIFEST = Path("output/_pilot_wi_home_services.json")


def phase_a_scrape() -> dict:
    """Scrape all 20 brands. Returns manifest dict keyed by brand name."""
    manifest: dict[str, dict] = {}
    with WisconsinScraper(headless=True, rate_limit_sec=2.5) as scraper:
        for i, brand in enumerate(PILOT_BRANDS, start=1):
            print(f"\n[A {i}/{len(PILOT_BRANDS)}] {brand}")
            entry: dict = {"brand": brand, "phase_a": {}}
            try:
                filings = scraper.search(brand)
                active = latest_active(filings)
                if not active:
                    entry["phase_a"] = {"status": "no_active_filing", "filings_seen": len(filings)}
                    print(f"    !! no active filing ({len(filings)} total filings seen)")
                else:
                    print(f"    found id={active.portal_id} ({active.legal_name}) effective={active.effective_date}")
                    dl = scraper.download(active, DEST, dedup_against=DEST)
                    print(f"    -> {dl.path.name} ({dl.size_bytes/1024/1024:.2f} MB) sha256={dl.sha256[:16]}... dup={dl.was_duplicate}")
                    entry["phase_a"] = {
                        "status": "ok",
                        "portal_id": active.portal_id,
                        "legal_name": active.legal_name,
                        "trade_name": active.trade_name,
                        "effective_date": active.effective_date,
                        "expiration_date": active.expiration_date,
                        "filings_seen": len(filings),
                        "pdf_path": str(dl.path),
                        "sha256": dl.sha256,
                        "size_bytes": dl.size_bytes,
                        "was_duplicate": dl.was_duplicate,
                        "source_url": dl.source_url,
                    }
            except Exception as e:
                entry["phase_a"] = {"status": "error", "error": repr(e)}
                print(f"    !! error: {e}")
            manifest[brand] = entry
    return manifest


def phase_b_extract(manifest: dict) -> dict:
    """Run src.extract on each successfully-scraped PDF. Updates manifest in place."""
    for i, (brand, entry) in enumerate(manifest.items(), start=1):
        pa = entry.get("phase_a", {})
        if pa.get("status") != "ok":
            print(f"\n[B {i}/{len(manifest)}] {brand}: skip (phase A status={pa.get('status')})")
            entry["phase_b"] = {"status": "skipped", "reason": pa.get("status")}
            continue
        pdf_path = pa["pdf_path"]
        print(f"\n[B {i}/{len(manifest)}] {brand}: extracting {Path(pdf_path).name}")
        t0 = time.monotonic()
        proc = subprocess.run(
            ["C:/Users/joshs/AppData/Roaming/Python/Python312/Scripts/uv.exe",
             "run", "python", "-m", "src.extract", pdf_path],
            capture_output=True, text=True, timeout=600,
        )
        elapsed = time.monotonic() - t0
        entry["phase_b"] = {
            "status": "ok" if proc.returncode == 0 else "error",
            "elapsed_sec": round(elapsed, 1),
            "return_code": proc.returncode,
            "stdout_tail": proc.stdout[-1500:],
            "stderr_tail": proc.stderr[-500:] if proc.stderr else "",
        }
        # Parse cost from stdout (last line: "Done. Total cost: $X.XXXX")
        for line in proc.stdout.splitlines():
            if "Total cost:" in line:
                entry["phase_b"]["total_cost_usd"] = line.split("$")[-1].strip()
        # Also load each item JSON's confidence + record count for quick audit
        out_dir = Path("output") / Path(pdf_path).stem
        for j in (5, 6, 7, 19, 20):
            jf = out_dir / (
                {5: "item5_initial_fee", 6: "item6_ongoing_fees", 7: "item7_investment",
                 19: "item19_fpr", 20: "item20_outlets"}[j] + ".json")
            if jf.exists():
                try:
                    data = json.loads(jf.read_text(encoding="utf-8"))
                    info = {"confidence": data.get("confidence")}
                    if j == 19:
                        info["has_item19"] = data.get("has_item19")
                        info["records"] = len(data.get("records", []))
                    elif j == 20:
                        info["yearly_rows"] = len(data.get("yearly_summary", []))
                        info["state_rows"] = len(data.get("state_year_status", []))
                    if "_parse_error" in data:
                        info["parse_error"] = data["_parse_error"]
                    entry["phase_b"][f"item{j}"] = info
                except Exception as e:
                    entry["phase_b"][f"item{j}"] = {"load_error": repr(e)}
        # Also metadata
        meta = out_dir / "metadata.json"
        if meta.exists():
            md = json.loads(meta.read_text(encoding="utf-8"))
            entry["phase_b"]["metadata"] = {k: md.get(k) for k in
                ("legal_name", "state_of_inc", "filing_year", "issuance_date", "confidence")}
        print(f"    elapsed={elapsed:.1f}s  cost={entry['phase_b'].get('total_cost_usd', '?')}")
    return manifest


def main() -> None:
    print(f"=== PHASE A: scrape {len(PILOT_BRANDS)} franchisors from WI ===")
    manifest = phase_a_scrape()
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nPhase A manifest saved -> {MANIFEST}")

    ok_count = sum(1 for e in manifest.values() if e.get("phase_a", {}).get("status") == "ok")
    dup_count = sum(1 for e in manifest.values()
                    if e.get("phase_a", {}).get("status") == "ok" and e["phase_a"].get("was_duplicate"))
    print(f"\nPhase A summary: {ok_count}/{len(PILOT_BRANDS)} scraped, {dup_count} dedup hits")

    print(f"\n=== PHASE B: extract {ok_count} PDFs ===")
    manifest = phase_b_extract(manifest)
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nFinal manifest saved -> {MANIFEST}")


if __name__ == "__main__":
    main()
