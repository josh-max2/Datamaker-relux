"""Download ~20 sample FDDs from MN CARDS for the WI preflight survey
(MN as proxy: modern franchisors file the same PDF across states)."""
import os
import sys
import time
from pathlib import Path

import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

SAMPLES = [
    ("all_county", "80C55299-0000-C930-8F92-124D040EC134"),
    ("happier_at_home_2025", "203AC099-0000-C811-9C6F-7DEDE2E9252E"),
    ("office_pride_2025", "20D89A99-0000-CD18-9F3E-1082C0FCCF04"),
    ("first_day_franchising", "2073549A-0000-CF52-8DCD-4602FAAD88F5"),
    ("big_blue_swim_2025", "D0033E99-0000-CF36-880A-921C550E3F77"),
    ("yasubee_ramen_v1", "40B8509A-0000-CC1C-963D-1D7187A41274"),
    ("tea_pulse", "30AAA69A-0000-CFBA-B00E-40336B9C80E2"),
    ("decimal_2025", "60FF259A-0000-C459-891E-88B76E6BAFBC"),
    ("get_a_grip_2025", "2001169A-0000-CC1B-B401-F98CEE508B47"),
    ("properties_2025", "E0E63B9A-0000-C617-BE74-F86CE68D9742"),
    ("supercuts_2025", "20C1909C-0000-CE18-8382-4D8EE2A66066"),
    ("always_best_care_2025", "3036979A-0000-C752-8F2E-19468EAAD821"),
    ("velox_valuations_2025", "209BF598-0000-CB1F-890B-5C582364F0C4"),
    ("yasubee_ramen_v2", "40B8509A-0000-C399-84E2-033ABBC2CC1A"),
    ("mb_franchise_holdings", "80A90B9A-0000-C21F-9B7E-E35521A47FBC"),
    ("unknown_e060", "E060BD9B-0000-CB1F-8FE5-7A3B236E553B"),
    ("sambazon_2026", "C071919B-0000-C156-9B40-E0EA09DD8312"),
    ("unknown_d0a2", "D0A2A69A-0000-C737-8E51-07D1F1470F7B"),
    ("unknown_1056", "1056C89B-0000-CA10-9B16-2300F08479FB"),
]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
REFERER = "https://cards.web.commerce.state.mn.us/franchise-registrations"

dest = Path("data/preflight")
dest.mkdir(parents=True, exist_ok=True)

for name, guid in SAMPLES:
    target = dest / f"{name}.pdf"
    if target.exists() and target.stat().st_size > 50_000:
        print(f"  [skip] {name} ({target.stat().st_size/1024:.0f} KB)")
        continue
    url = f"https://cards.web.commerce.state.mn.us/documents/%7B{guid}%7D/download?documentClass=FRANCHISE_REGISTRATIONS&contentSequence=0"
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/pdf,*/*",
        "Referer": REFERER,
    })
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = resp.read()
        target.write_bytes(data)
        print(f"  [ok]   {name}: {len(data)/1024/1024:.2f} MB")
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
    time.sleep(1.5)  # be polite

print(f"\nDone. {len(list(dest.glob('*.pdf')))} PDFs in {dest}")
