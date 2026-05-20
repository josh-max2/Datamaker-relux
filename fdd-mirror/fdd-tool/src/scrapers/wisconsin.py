"""Wisconsin DFI franchise scraper.

The WI portal (apps.dfi.wi.gov/apps/FranchiseSearch) is a stateful ASP.NET app.
The flow is: search → results table → click Details for a filing → click Download
to get the PDF. Requires a real browser (Playwright + chromium); the download URL
is not a static GET — it's a server-side POST.

Usage:
    from src.scrapers.wisconsin import WisconsinScraper

    with WisconsinScraper() as scraper:
        filings = scraper.search("Mr. Rooter")
        active = [f for f in filings if f.status == "Registered"]
        for f in active:
            result = scraper.download(f, dest=Path("data/wi_scrape"))
            print(result.path, result.sha256, "duplicate!" if result.was_duplicate else "")
"""
from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

SEARCH_URL = "https://apps.dfi.wi.gov/apps/FranchiseSearch/MainSearch.aspx"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
DEFAULT_RATE_LIMIT_SEC = 2.5  # per WI portal politeness norms; aligns with spec §2


@dataclass
class FilingRow:
    portal_id: str          # e.g., "640790"
    legal_name: str         # e.g., "Mr. Rooter SPV LLC"
    trade_name: str         # e.g., "Mr. Rooter"
    effective_date: str     # "4/2/2026"
    expiration_date: str    # "4/2/2027"
    status: str             # "Registered" or "Expired" (or other)
    details_url: str | None


@dataclass
class DownloadResult:
    path: Path
    sha256: str
    size_bytes: int
    source_url: str
    portal_id: str
    was_duplicate: bool


# Parses one tab-separated results row:
# "640790  Mr. Rooter SPV LLC  Mr. Rooter  4/2/2026  4/2/2027  Registered  Details"
_ROW_FIELD_SEP = re.compile(r"\s{2,}|\t")
_ID_RE = re.compile(r"^\d{6}$")
_HREF_ID_RE = re.compile(r"id=(\d+)")


class WisconsinScraper:
    """Context-managed scraper that reuses a single Chromium context across calls."""

    def __init__(self, *, headless: bool = True, rate_limit_sec: float = DEFAULT_RATE_LIMIT_SEC):
        self._headless = headless
        self._rate_limit = rate_limit_sec
        self._last_request_at = 0.0
        self._pw = None
        self._browser: Browser | None = None
        self._ctx: BrowserContext | None = None

    def __enter__(self) -> "WisconsinScraper":
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self._headless)
        self._ctx = self._browser.new_context(user_agent=UA, accept_downloads=True)
        return self

    def __exit__(self, *exc) -> None:
        if self._ctx:
            self._ctx.close()
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self._rate_limit:
            time.sleep(self._rate_limit - elapsed)
        self._last_request_at = time.monotonic()

    def _open_page(self) -> Page:
        self._throttle()
        assert self._ctx is not None, "Use WisconsinScraper as a context manager"
        return self._ctx.new_page()

    def search(self, query: str) -> list[FilingRow]:
        """Search the WI portal. Returns every matching filing (all years, all statuses)."""
        page = self._open_page()
        try:
            page.goto(SEARCH_URL, wait_until="networkidle")
            page.fill("input[name='txtName']", query)
            page.click("#btnSearch")
            page.wait_for_load_state("networkidle")

            body = page.inner_text("body")
            link_data = page.eval_on_selector_all(
                "a",
                "els => els.filter(a => a.href && a.href.includes('details.aspx'))"
                "      .map(a => ({id: (a.href.match(/id=(\\d+)/)||[])[1], href: a.href}))",
            )
            id_to_url = {l["id"]: l["href"] for l in link_data if l.get("id")}

            rows: list[FilingRow] = []
            for line in body.split("\n"):
                s = line.strip()
                parts = _ROW_FIELD_SEP.split(s)
                if len(parts) >= 6 and _ID_RE.match(parts[0]):
                    rows.append(FilingRow(
                        portal_id=parts[0],
                        legal_name=parts[1],
                        trade_name=parts[2],
                        effective_date=parts[3],
                        expiration_date=parts[4],
                        status=parts[5],
                        details_url=id_to_url.get(parts[0]),
                    ))
            return rows
        finally:
            page.close()

    def download(
        self,
        filing: FilingRow,
        dest: Path,
        *,
        dedup_against: Path | None = None,
    ) -> DownloadResult:
        """Download the FDD PDF for `filing` into `dest`. SHA-256 hashed.

        If `dedup_against` is set, scans that directory for an existing PDF with the
        same SHA-256 and (if found) returns the existing path with `was_duplicate=True`.
        """
        if not filing.details_url:
            raise ValueError(f"FilingRow has no details_url; can't download id={filing.portal_id}")

        dest.mkdir(parents=True, exist_ok=True)
        page = self._open_page()
        try:
            page.goto(filing.details_url, wait_until="networkidle")
            with page.expect_download(timeout=60_000) as dl_info:
                page.click("#upload_downloadFile")
            download = dl_info.value

            tmp = dest / f"_tmp_{filing.portal_id}.pdf"
            download.save_as(str(tmp))
            data = tmp.read_bytes()
            digest = hashlib.sha256(data).hexdigest()

            if dedup_against and dedup_against.exists():
                for existing in dedup_against.glob("*.pdf"):
                    if existing.name.startswith("_tmp_") or existing == tmp:
                        continue
                    if hashlib.sha256(existing.read_bytes()).hexdigest() == digest:
                        tmp.unlink()
                        return DownloadResult(
                            path=existing, sha256=digest,
                            size_bytes=existing.stat().st_size,
                            source_url=filing.details_url,
                            portal_id=filing.portal_id,
                            was_duplicate=True,
                        )

            slug = re.sub(r"[^A-Za-z0-9]+", "_", filing.trade_name).strip("_").lower()[:40]
            final = dest / f"{slug}_id{filing.portal_id}.pdf"
            tmp.rename(final)
            return DownloadResult(
                path=final, sha256=digest, size_bytes=len(data),
                source_url=filing.details_url,
                portal_id=filing.portal_id,
                was_duplicate=False,
            )
        finally:
            page.close()


def latest_active(filings: list[FilingRow]) -> FilingRow | None:
    """Pick the currently-Registered filing from a result set; None if all expired."""
    active = [f for f in filings if f.status.strip().lower() == "registered"]
    if not active:
        return None
    # If multiple Registered (rare), prefer the most recent effective_date string-sorted desc
    # (M/D/YYYY format — fine for same-decade comparisons)
    return sorted(active, key=lambda f: f.effective_date, reverse=True)[0]
