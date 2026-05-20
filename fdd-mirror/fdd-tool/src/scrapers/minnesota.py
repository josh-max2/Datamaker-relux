"""Minnesota CARDS franchise scraper.

The MN Commerce Department's CARDS portal exposes franchise filings via a
public search at https://cards.web.commerce.state.mn.us/franchise-registrations
Unlike WI's stateful ASP.NET portal, MN serves:
  - A simple GET search with year + documentType (no session needed)
  - 500 results per page; htmx "Load more" for additional pages
  - Direct PDF downloads at /documents/{GUID}/download?documentClass=FRANCHISE_REGISTRATIONS

The result table includes:
  Document ID | Franchisor | Franchise names | Document types | Year |
  File number | Received date | Added on | (download link in row)

For recency-first scraping, sort by `added_on` desc — that's when the document
was published to CARDS, which catches both new filings and back-dated uploads.

Usage:
    from src.scrapers.minnesota import MinnesotaScraper

    with MinnesotaScraper() as s:
        filings = s.search(year=2026, document_type="Clean FDD")
        for f in filings[:5]:
            result = s.download(f, dest=Path("data/mn_scrape"))
            print(result.path, result.sha256)
"""
from __future__ import annotations

import hashlib
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

BASE_URL = "https://cards.web.commerce.state.mn.us"
SEARCH_URL = f"{BASE_URL}/franchise-registrations"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
DEFAULT_RATE_LIMIT_SEC = 1.5  # MN is more permissive than WI; still polite


@dataclass
class MinnesotaFiling:
    document_id: str          # e.g. "36648-202605-03"
    franchisor: str           # "CruiseOne, LLC"
    franchise_name: str       # "CruiseOne"
    document_type: str        # "Clean FDD" | "Revised FDD - Clean" | etc.
    year: int                 # 2026
    file_number: str          # "10705"
    received_date: str        # "05/15/2026" (raw MM/DD/YYYY)
    added_on: str             # "05/18/2026" (raw MM/DD/YYYY)
    download_url: str         # full URL including GUID
    guid: str                 # the {...} GUID inside the URL

    @property
    def added_on_iso(self) -> str | None:
        """Parse added_on into YYYY-MM-DD for sorting."""
        try:
            return datetime.strptime(self.added_on, "%m/%d/%Y").strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            return None

    @property
    def received_date_iso(self) -> str | None:
        try:
            return datetime.strptime(self.received_date, "%m/%d/%Y").strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            return None


@dataclass
class MinnesotaDownloadResult:
    path: Path
    sha256: str
    size_bytes: int
    source_url: str
    document_id: str
    was_duplicate: bool


_RE_DOC_LINK = re.compile(
    r'href="(/documents/(\{[0-9A-F-]+\})/download\?documentClass=FRANCHISE_REGISTRATIONS[^"]*)"',
    re.IGNORECASE,
)
_RE_TABLE_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL | re.IGNORECASE)
_RE_TD = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL | re.IGNORECASE)
_RE_TAG = re.compile(r"<[^>]+>")
_RE_WS = re.compile(r"\s+")


def _clean(html_fragment: str) -> str:
    """Strip tags, collapse whitespace, decode common entities."""
    if not html_fragment:
        return ""
    s = _RE_TAG.sub(" ", html_fragment)
    s = (s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
           .replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " "))
    return _RE_WS.sub(" ", s).strip()


class MinnesotaScraper:
    """Plain HTTP scraper — no browser, no session. MN CARDS is stateless."""

    def __init__(self, *, rate_limit_sec: float = DEFAULT_RATE_LIMIT_SEC):
        self._rate_limit = rate_limit_sec
        self._last_request_at = 0.0

    def __enter__(self) -> "MinnesotaScraper":
        return self

    def __exit__(self, *args):
        return False

    def _throttle(self) -> None:
        elapsed = time.time() - self._last_request_at
        if elapsed < self._rate_limit:
            time.sleep(self._rate_limit - elapsed)
        self._last_request_at = time.time()

    def _get(self, url: str) -> str:
        self._throttle()
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": SEARCH_URL,
        })
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read().decode("utf-8", errors="replace")

    def _get_bytes(self, url: str) -> bytes:
        """Fetch raw bytes with retry-on-429 (exponential backoff: 30s, 60s, 120s)."""
        backoffs = [30, 60, 120]
        last_err = None
        for attempt in range(len(backoffs) + 1):
            self._throttle()
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept": "application/pdf,*/*",
                "Referer": SEARCH_URL,
            })
            try:
                with urllib.request.urlopen(req, timeout=180) as resp:
                    return resp.read()
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < len(backoffs):
                    wait = backoffs[attempt]
                    print(f"      429 throttle — sleeping {wait}s (attempt {attempt+1})")
                    time.sleep(wait)
                    last_err = e
                    continue
                raise
        raise last_err if last_err else RuntimeError("download failed")

    def search(self, *, year: int | None = None,
               document_type: str = "Clean FDD",
               franchisor: str | None = None) -> list[MinnesotaFiling]:
        """Run a single search. Returns parsed filings (up to ~500 per call;
        further results require "Load more" pagination which we'll add when needed).

        Default document_type='Clean FDD' is the canonical full-FDD document.
        Other useful values: 'Revised FDD - Clean' (amendment), 'Final FDD'
        (deprecated — returns 0 today).
        """
        params = {"doSearch": "true", "documentType": document_type}
        if year is not None:
            params["year"] = str(year)
        if franchisor:
            params["franchisor"] = franchisor
        url = f"{SEARCH_URL}?{urllib.parse.urlencode(params)}"
        html = self._get(url)
        return self._parse_results_table(html)

    def _parse_results_table(self, html: str) -> list[MinnesotaFiling]:
        """Extract filing rows from the search results table.

        The table has a header row + data rows. Each data row's last cell
        contains the download link; the row's cells contain the metadata.
        """
        # Isolate the results table (first <table> on the page)
        m = re.search(r"<table[^>]*>(.*?)</table>", html, re.DOTALL | re.IGNORECASE)
        if not m:
            return []
        table_html = m.group(1)
        rows = _RE_TABLE_ROW.findall(table_html)
        out: list[MinnesotaFiling] = []
        for row in rows:
            tds = _RE_TD.findall(row)
            if len(tds) < 9:  # header rows / "Load more" rows have <td> count off
                continue
            # Find the download link inside the row
            dl_match = _RE_DOC_LINK.search(row)
            if not dl_match:
                continue
            rel_path = dl_match.group(1).replace("&amp;", "&")
            guid = dl_match.group(2)
            # MN's server requires {} URL-encoded as %7B...%7D in the path.
            encoded_guid = "%7B" + guid.strip("{}") + "%7D"
            encoded_rel_path = rel_path.replace(guid, encoded_guid)
            download_url = f"{BASE_URL}{encoded_rel_path}"
            try:
                # Column layout (verified against actual rendered HTML 2026-05-19):
                #   tds[0] = Document ID  (e.g. "36648-202605-03")
                #   tds[1] = Franchisor   (e.g. "CruiseOne, LLC")
                #   tds[2] = Franchise names
                #   tds[3] = Document types
                #   tds[4] = Year
                #   tds[5] = File number
                #   tds[6] = Notes (often empty)
                #   tds[7] = Received date
                #   tds[8] = Added on
                doc_id = _clean(tds[0])
                franchisor = _clean(tds[1])
                franchise_name = _clean(tds[2])
                doc_type = _clean(tds[3])
                year_str = _clean(tds[4])
                file_num = _clean(tds[5])
                received = _clean(tds[7])
                added = _clean(tds[8])
                out.append(MinnesotaFiling(
                    document_id=doc_id,
                    franchisor=franchisor,
                    franchise_name=franchise_name,
                    document_type=doc_type,
                    year=int(year_str) if year_str.isdigit() else 0,
                    file_number=file_num,
                    received_date=received,
                    added_on=added,
                    download_url=download_url,
                    guid=guid,
                ))
            except (ValueError, IndexError):
                continue
        return out

    def download(self, filing: MinnesotaFiling, dest: Path,
                 existing_shas: set[str] | None = None) -> MinnesotaDownloadResult:
        """Download a filing's PDF. Computes SHA-256 and (if existing_shas given)
        marks duplicates without rewriting the file.

        Filename pattern: data/mn_scrape/{slug-of-franchisor}_{year}_mn_{doc_id}.pdf
        """
        dest.mkdir(parents=True, exist_ok=True)
        # Build a stable filename from franchisor slug + year + document_id
        slug = re.sub(r"[^a-z0-9]+", "_", filing.franchisor.lower()).strip("_")[:60]
        safe_doc_id = re.sub(r"[^A-Za-z0-9-]", "", filing.document_id)
        path = dest / f"{slug}_{filing.year}_mn_{safe_doc_id}.pdf"

        if path.exists() and path.stat().st_size > 50_000:
            # Already downloaded; recompute sha for return
            data = path.read_bytes()
            sha = hashlib.sha256(data).hexdigest()
            return MinnesotaDownloadResult(
                path=path, sha256=sha, size_bytes=len(data),
                source_url=filing.download_url, document_id=filing.document_id,
                was_duplicate=(existing_shas is not None and sha in existing_shas),
            )

        data = self._get_bytes(filing.download_url)
        sha = hashlib.sha256(data).hexdigest()
        was_dup = existing_shas is not None and sha in existing_shas
        if not was_dup:
            path.write_bytes(data)
        return MinnesotaDownloadResult(
            path=path, sha256=sha, size_bytes=len(data),
            source_url=filing.download_url, document_id=filing.document_id,
            was_duplicate=was_dup,
        )
