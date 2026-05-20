"""Audit the generated site for HTML/JSON-LD issues, broken links, content gaps.

Runs without external deps beyond what's already installed.
Output: a structured report of findings per page + summary.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from html.parser import HTMLParser

sys.stdout.reconfigure(encoding="utf-8")

DOCS = Path("../docs")
SITE_PREFIX = "/Parser"


class HTMLValidator(HTMLParser):
    """Minimal HTML validator — flags unclosed tags + unbalanced structure."""
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "source", "track", "wbr"}

    def __init__(self):
        super().__init__()
        self.stack: list[str] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return  # XHTML-style <input /> triggers spurious endtag; void elements have no real close
        if not self.stack:
            self.errors.append(f"closing </{tag}> with no matching open")
            return
        if self.stack[-1] != tag:
            self.errors.append(f"closing </{tag}> but expected </{self.stack[-1]}>")
            try:
                self.stack.remove(tag)
            except ValueError:
                pass
        else:
            self.stack.pop()


def collect_all_pages(docs: Path) -> list[Path]:
    return list(docs.rglob("*.html"))


def collect_internal_links(docs: Path) -> dict[str, set[str]]:
    """Returns {source_page: set of /Parser/... hrefs found}. Strips out hrefs inside <script> blocks."""
    result: dict[str, set[str]] = defaultdict(set)
    for page in collect_all_pages(docs):
        html = page.read_text(encoding="utf-8")
        # Strip script + style tag contents to avoid false positives from JS template literals
        clean = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.S)
        clean = re.sub(r"<style[^>]*>.*?</style>", "", clean, flags=re.S)
        for m in re.finditer(r'href="([^"]+)"', clean):
            href = m.group(1)
            # Skip unresolved JS template variables
            if "${" in href:
                continue
            if href.startswith(SITE_PREFIX + "/") or href.startswith(SITE_PREFIX):
                result[str(page)].add(href)
            elif href.startswith("#"):
                continue  # in-page anchor
            elif "://" not in href and not href.startswith("mailto:"):
                result[str(page)].add(href)
    return result


def href_to_docs_path(href: str) -> Path | None:
    """Resolve a /Parser/... href to a docs/ file path."""
    if "#" in href:
        href = href.split("#", 1)[0]
    if "?" in href:
        href = href.split("?", 1)[0]
    if not href:
        return DOCS / "index.html"
    if href.startswith(SITE_PREFIX):
        href = href[len(SITE_PREFIX):]
    href = href.lstrip("/")
    if not href:
        return DOCS / "index.html"
    if href.endswith("/"):
        return DOCS / href / "index.html"
    return DOCS / href


def audit_html_validity():
    print("\n=== AUDIT 1: HTML validity ===")
    issues = 0
    for page in collect_all_pages(DOCS):
        html = page.read_text(encoding="utf-8")
        v = HTMLValidator()
        try:
            v.feed(html)
        except Exception as e:
            print(f"  PARSE ERROR {page.relative_to(DOCS.parent)}: {e}")
            issues += 1
            continue
        if v.errors:
            issues += len(v.errors)
            print(f"  {page.relative_to(DOCS.parent)}: {len(v.errors)} unbalanced tag(s)")
            for e in v.errors[:3]:
                print(f"      - {e}")
        if v.stack:
            issues += 1
            print(f"  {page.relative_to(DOCS.parent)}: unclosed at EOF: {v.stack}")
    if issues == 0:
        print(f"  OK: {len(collect_all_pages(DOCS))} pages, no HTML structure issues")
    return issues


def audit_json_ld():
    print("\n=== AUDIT 2: JSON-LD validity ===")
    issues = 0
    schema_types_seen: Counter = Counter()
    for page in collect_all_pages(DOCS):
        html = page.read_text(encoding="utf-8")
        blocks = re.findall(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', html, re.S)
        for i, block in enumerate(blocks):
            try:
                data = json.loads(block)
                # Traverse @graph documents so we count every entity, not just the top-level
                for node in (data.get("@graph") or [data]):
                    if isinstance(node, dict):
                        schema_types_seen[node.get("@type", "?")] += 1
            except json.JSONDecodeError as e:
                issues += 1
                print(f"  INVALID JSON {page.relative_to(DOCS.parent)} block {i+1}: {e}")
                print(f"      first 200 chars: {block[:200]!r}")
            else:
                # Walk @graph entries (or just the top-level if no graph)
                nodes = data.get("@graph") or [data]
                for node in nodes:
                    if not isinstance(node, dict):
                        continue
                    # FAQPage-specific validation
                    if node.get("@type") == "FAQPage":
                        entries = node.get("mainEntity", [])
                        for j, e in enumerate(entries):
                            if e.get("@type") != "Question":
                                issues += 1; print(f"  {page.relative_to(DOCS.parent)} FAQ entry {j}: missing @type=Question")
                            if not e.get("name"):
                                issues += 1; print(f"  {page.relative_to(DOCS.parent)} FAQ entry {j}: missing name")
                            ans = e.get("acceptedAnswer", {})
                            if ans.get("@type") != "Answer":
                                issues += 1; print(f"  {page.relative_to(DOCS.parent)} FAQ entry {j}: bad acceptedAnswer")
                            if not ans.get("text"):
                                issues += 1; print(f"  {page.relative_to(DOCS.parent)} FAQ entry {j}: empty answer text")
                    # Article schema check
                    if node.get("@type") == "Article":
                        needed = ("headline", "author", "publisher", "dateModified")
                        missing = [k for k in needed if not node.get(k)]
                        if missing:
                            issues += 1
                            print(f"  {page.relative_to(DOCS.parent)}: Article schema missing {missing}")
    print(f"\n  Schema @types seen across site: {dict(schema_types_seen)}")
    if issues == 0:
        print(f"  OK: all JSON-LD blocks parse + validate")
    return issues


def audit_internal_links():
    print("\n=== AUDIT 3: internal link resolution ===")
    issues = 0
    broken: list[tuple[str, str]] = []
    links_by_page = collect_internal_links(DOCS)
    for src, hrefs in links_by_page.items():
        for h in hrefs:
            target = href_to_docs_path(h)
            if target and not target.exists():
                broken.append((src, h, str(target)))
                issues += 1
    if broken:
        print(f"  {len(broken)} broken internal links:")
        for src, h, t in broken[:15]:
            print(f"    {Path(src).relative_to(DOCS.parent)} -> {h}  (expected at {t})")
        if len(broken) > 15:
            print(f"    ... and {len(broken)-15} more")
    else:
        total_hrefs = sum(len(s) for s in links_by_page.values())
        print(f"  OK: {total_hrefs} internal links across {len(links_by_page)} pages, none broken")
    return issues


def audit_compliance_coverage():
    print("\n=== AUDIT 5: compliance fix coverage ===")
    issues = 0
    brand_pages = sorted((DOCS / "franchise").glob("*/index.html"))
    print(f"  Checking {len(brand_pages)} brand pages...")

    # Breakeven section must use scenario language
    no_arithmetic_heading = []
    no_not_a_projection = []
    no_ftc_link = []
    # Risk badge must use Closure rate label
    risk_old_label = []
    # FTC footer disclosure
    no_footer_ftc = []
    # Inline affiliate disclosure
    no_inline_disclosure = []

    for p in brand_pages:
        html = p.read_text(encoding="utf-8")
        if "<h2>Arithmetic breakeven scenario</h2>" not in html:
            # Some brands may not have breakeven (no Item 19) — only flag if breakeven section is present
            if "breakeven-section" in html and "Cannot be estimated" not in html:
                no_arithmetic_heading.append(p.name)
        if "breakeven-section" in html and "Cannot be estimated" not in html:
            if "This is not a projection" not in html:
                no_not_a_projection.append(p.name)
            if "436.5(s)" not in html:
                no_ftc_link.append(p.name)
        if "System health" in html and "Closure rate" not in html:
            risk_old_label.append(p.name)
        if "16 CFR Part 255" not in html:
            no_footer_ftc.append(p.name)
        if "affiliate-inline-disclosure" not in html:
            no_inline_disclosure.append(p.name)

    if no_arithmetic_heading:
        issues += len(no_arithmetic_heading)
        print(f"  {len(no_arithmetic_heading)} pages missing 'Arithmetic breakeven scenario' heading (where breakeven exists): {no_arithmetic_heading[:3]}")
    if no_not_a_projection:
        issues += len(no_not_a_projection)
        print(f"  {len(no_not_a_projection)} pages missing 'This is not a projection' language: {no_not_a_projection[:3]}")
    if no_ftc_link:
        issues += len(no_ftc_link)
        print(f"  {len(no_ftc_link)} pages missing FTC §436.5(s) link: {no_ftc_link[:3]}")
    if risk_old_label:
        issues += len(risk_old_label)
        print(f"  {len(risk_old_label)} pages still using old 'System health' label: {risk_old_label[:3]}")
    if no_footer_ftc:
        issues += len(no_footer_ftc)
        print(f"  {len(no_footer_ftc)} pages missing FTC footer disclosure: {no_footer_ftc[:3]}")
    if no_inline_disclosure:
        issues += len(no_inline_disclosure)
        print(f"  {len(no_inline_disclosure)} pages missing inline affiliate disclosure: {no_inline_disclosure[:3]}")

    if issues == 0:
        print(f"  OK: compliance fixes present on all brand pages")
    return issues


def audit_faq_content_match():
    print("\n=== AUDIT 4: FAQ schema content matches visible content ===")
    """Google penalizes when FAQPage schema text differs materially from visible HTML."""
    issues = 0
    brand_pages = sorted((DOCS / "franchise").glob("*/index.html"))
    for p in brand_pages:
        html = p.read_text(encoding="utf-8")
        # Pull visible FAQ Q/A pairs
        visible_items = re.findall(
            r'<details class="faq-item">\s*<summary>(.*?)</summary>\s*<div class="faq-answer"><p>(.*?)</p></div>\s*</details>',
            html, re.S)
        # Pull schema entries
        schema_match = re.search(r'<script type="application/ld\+json">\s*(\{[^<]*?"@type":\s*"FAQPage".*?\})\s*</script>', html, re.S)
        if not schema_match:
            continue
        try:
            schema = json.loads(schema_match.group(1))
        except json.JSONDecodeError:
            continue
        schema_items = [(e.get("name", ""), e.get("acceptedAnswer", {}).get("text", ""))
                        for e in schema.get("mainEntity", [])]
        if len(visible_items) != len(schema_items):
            issues += 1
            print(f"  {p.parent.name}: count mismatch — {len(visible_items)} visible vs {len(schema_items)} in schema")
            continue
        # HTML-decode visible text so &amp; etc. compare equal to schema's raw &
        import html as _html
        for i, ((vq, va), (sq, sa)) in enumerate(zip(visible_items, schema_items)):
            vq_norm = _html.unescape(vq.strip())
            if vq_norm != sq.strip():
                issues += 1
                print(f"  {p.parent.name} FAQ {i+1}: question mismatch")
                print(f"      visible:  {vq_norm[:80]!r}")
                print(f"      schema:   {sq[:80]!r}")
            va_text = _html.unescape(re.sub(r"<[^>]+>", "", va)).strip()
            sa_text = sa.strip()
            if va_text != sa_text:
                if re.sub(r"\s+", " ", va_text) != re.sub(r"\s+", " ", sa_text):
                    issues += 1
                    print(f"  {p.parent.name} FAQ {i+1}: answer mismatch")
                    print(f"      visible:  {va_text[:120]!r}")
                    print(f"      schema:   {sa_text[:120]!r}")
    if issues == 0:
        print(f"  OK: all FAQ schema content matches visible content")
    return issues


def audit_accessibility():
    """Spot-check accessibility — alt text on imgs, label-for-input pairs,
    skip-to-content link presence."""
    print("\n=== AUDIT 6: accessibility (F8.1-F8.4) ===")
    issues = 0
    pages_missing_skip = []
    pages_with_unlabeled_inputs = []
    images_missing_alt = []
    for page in collect_all_pages(DOCS):
        html = page.read_text(encoding="utf-8")
        # F8.2 — skip-to-content link
        if 'class="skip-to-content"' not in html and '/Parser/' in html:  # only check real pages
            pages_missing_skip.append(str(page.relative_to(DOCS.parent)))
        # F8.1 — img alt
        for m in re.finditer(r"<img\b([^>]*)>", html):
            attrs = m.group(1)
            if 'alt=' not in attrs:
                images_missing_alt.append(f"{page.relative_to(DOCS.parent)}: <img{attrs[:60]}...>")
        # F8.4 — every visible input has a label (or aria-label / aria-labelledby)
        for m in re.finditer(r'<input\b([^>]*?)>', html):
            attrs = m.group(1)
            # Skip hidden / submit / button / honeypot inputs
            type_m = re.search(r'type="(\w+)"', attrs)
            input_type = type_m.group(1) if type_m else "text"
            if input_type in ("hidden", "submit", "button"):
                continue
            if "aria-hidden" in attrs:  # honeypot
                continue
            if "aria-label" in attrs or "aria-labelledby" in attrs:
                continue
            id_m = re.search(r'id="([^"]+)"', attrs)
            if not id_m:
                pages_with_unlabeled_inputs.append(f"{page.relative_to(DOCS.parent)}: input no id, no aria-label")
                continue
            input_id = id_m.group(1)
            # Look for matching <label for="...">
            if f'for="{input_id}"' not in html:
                pages_with_unlabeled_inputs.append(f"{page.relative_to(DOCS.parent)}: input#{input_id} has no <label for>")

    if pages_missing_skip:
        issues += len(pages_missing_skip)
        print(f"  {len(pages_missing_skip)} pages missing skip-to-content link")
        for p in pages_missing_skip[:3]: print(f"    - {p}")
    if images_missing_alt:
        issues += len(images_missing_alt)
        print(f"  {len(images_missing_alt)} <img> without alt attribute")
        for s in images_missing_alt[:3]: print(f"    - {s}")
    if pages_with_unlabeled_inputs:
        issues += len(pages_with_unlabeled_inputs)
        print(f"  {len(pages_with_unlabeled_inputs)} inputs without associated label")
        for s in pages_with_unlabeled_inputs[:3]: print(f"    - {s}")

    if issues == 0:
        print(f"  OK: skip-link present, all imgs have alt, all inputs labeled")
    return issues


def main():
    print("AUDIT: full site")
    print(f"  docs root: {DOCS.resolve()}")
    print(f"  pages: {len(collect_all_pages(DOCS))}")
    total = 0
    total += audit_html_validity()
    total += audit_json_ld()
    total += audit_internal_links()
    total += audit_faq_content_match()
    total += audit_compliance_coverage()
    total += audit_accessibility()
    print(f"\n=== SUMMARY: {total} total issues found ===")


if __name__ == "__main__":
    main()
