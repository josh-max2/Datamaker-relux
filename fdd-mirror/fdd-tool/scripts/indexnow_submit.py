"""Submit the current sitemap URLs to IndexNow.

IndexNow is a protocol jointly supported by Bing, Yandex, Seznam.cz, and Naver.
A single submission to api.indexnow.org fans out to all participating engines.

When to run:
- After every site-content update that affects URLs you want re-crawled
- After adding new brand pages, guides, comparison pages, etc.
- Safe to re-run; engines de-duplicate

Usage:
    uv run python scripts/indexnow_submit.py                # submits everything in sitemap.xml
    uv run python scripts/indexnow_submit.py --dry-run       # prints what would be sent
    uv run python scripts/indexnow_submit.py --only-new      # diffs against last run
    uv run python scripts/indexnow_submit.py --urls URL1 URL2  # submit specific URLs only

Reads:
- docs/sitemap.xml (must be regenerated first via `python -m src.site_gen`)
- output/_indexnow_last_submit.json (tracks what we've already sent)

Writes:
- output/_indexnow_last_submit.json (timestamps + url set submitted)
- output/_indexnow_log.txt (append-only response log)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"
SITEMAP_PATH = DOCS_DIR / "sitemap.xml"
LAST_SUBMIT_PATH = OUTPUT_DIR / "_indexnow_last_submit.json"
LOG_PATH = OUTPUT_DIR / "_indexnow_log.txt"

INDEXNOW_ENDPOINT = "https://api.indexnow.org/IndexNow"
BATCH_SIZE = 10_000  # IndexNow protocol max per request

# Default key — overridable via --key / env var
DEFAULT_KEY = "108a9bb5a8ed4718a9ff03218f2899f6"


def parse_sitemap(path: Path) -> list[str]:
    """Pull <loc> URLs from sitemap.xml."""
    if not path.exists():
        print(f"ERROR: sitemap not found at {path}. Run `python -m src.site_gen` first.")
        sys.exit(1)
    xml = path.read_text(encoding="utf-8")
    return re.findall(r"<loc>([^<]+)</loc>", xml)


def load_last_submit() -> dict:
    if not LAST_SUBMIT_PATH.exists():
        return {"submitted": []}
    try:
        return json.loads(LAST_SUBMIT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"submitted": []}


def save_last_submit(urls: list[str]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LAST_SUBMIT_PATH.write_text(
        json.dumps({
            "submitted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "submitted": sorted(urls),
        }, indent=2),
        encoding="utf-8",
    )


def log(line: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {line}\n")


def submit_batch(host: str, key: str, key_location: str, urls: list[str], dry_run: bool) -> tuple[int, str]:
    """POST a batch of URLs to IndexNow. Returns (status_code, body_text)."""
    payload = {
        "host": host,
        "key": key,
        "keyLocation": key_location,
        "urlList": urls,
    }
    if dry_run:
        return 0, f"DRY RUN — would POST {len(urls)} URLs"

    data = json.dumps(payload).encode("utf-8")
    req = urllib_request.Request(
        INDEXNOW_ENDPOINT,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Host": "api.indexnow.org",
        },
    )
    try:
        with urllib_request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else str(e)
        return e.code, body
    except URLError as e:
        return -1, f"URL error: {e}"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--key", default=DEFAULT_KEY, help="IndexNow API key")
    p.add_argument("--dry-run", action="store_true", help="Print what would be sent without POSTing")
    p.add_argument("--only-new", action="store_true",
                   help="Submit only URLs that weren't in the last successful submit")
    p.add_argument("--urls", nargs="+", help="Specific URLs to submit (skips sitemap)")
    args = p.parse_args()

    key = args.key
    key_location = f"https://franchisedepth.com/{key}.txt"

    if args.urls:
        urls = list(args.urls)
        print(f"Manual mode: {len(urls)} URLs from --urls flag")
    else:
        urls = parse_sitemap(SITEMAP_PATH)
        print(f"Loaded {len(urls)} URLs from {SITEMAP_PATH}")

    if not urls:
        print("Nothing to submit.")
        return 0

    # Diff against last submit if requested
    if args.only_new and not args.urls:
        last = load_last_submit()
        prev = set(last.get("submitted", []))
        new_urls = [u for u in urls if u not in prev]
        print(f"  --only-new filter: {len(new_urls)} new (of {len(urls)} total)")
        if not new_urls:
            print("Nothing new to submit.")
            return 0
        urls = new_urls

    # Extract host from first URL (all URLs should share host)
    host_match = re.match(r"https?://([^/]+)/", urls[0])
    if not host_match:
        print(f"ERROR: could not extract host from URL: {urls[0]}")
        return 1
    host = host_match.group(1)
    print(f"Host: {host}")
    print(f"Key file: {key_location}")
    print(f"Endpoint: {INDEXNOW_ENDPOINT}")
    print()

    # Submit in batches
    all_ok = True
    for i in range(0, len(urls), BATCH_SIZE):
        batch = urls[i:i + BATCH_SIZE]
        status, body = submit_batch(host, key, key_location, batch, args.dry_run)
        msg = f"batch {i // BATCH_SIZE + 1}: {len(batch)} URLs → HTTP {status}"
        if status in (200, 202):
            print(f"  ✓ {msg}")
            log(f"OK  {msg}  body={body[:200]!r}")
        elif status == 0 and args.dry_run:
            print(f"  · {msg}")
            for u in batch[:5]:
                print(f"      {u}")
            if len(batch) > 5:
                print(f"      … +{len(batch) - 5} more")
        else:
            print(f"  ✗ {msg}  body={body[:300]!r}")
            log(f"FAIL  {msg}  body={body[:300]!r}")
            all_ok = False

    if all_ok and not args.dry_run:
        save_last_submit(urls)
        print(f"\nDone. {len(urls)} URLs submitted. Manifest: {LAST_SUBMIT_PATH}")
    elif args.dry_run:
        print(f"\nDry run complete. {len(urls)} URLs would be submitted.")
    else:
        print(f"\nDone with errors. See {LOG_PATH}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
