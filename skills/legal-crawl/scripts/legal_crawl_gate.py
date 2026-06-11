#!/usr/bin/env python3
"""legal_crawl_gate.py — fail-closed legal + crawl file validator for static micro-tool sites.

Usage:
    python3 scripts/legal_crawl_gate.py <site-dir>
    python3 scripts/legal_crawl_gate.py --selftest

Exit codes: 0 PASS, 1 FAIL, 2 load error.

Checks:
  L1 pages-present    — site dir contains privacy, terms, about, contact HTML pages, a 404
                        page, robots.txt, and sitemap.xml
  L2 substance        — each of the 4 legal pages has >= 150 visible words, contains the
                        brand/tool name, and has NO placeholder markers
  L3 double-linked    — every content HTML page contains <a href> links to ALL FOUR legal pages
  L4 no-stale-dates   — no legal page shows a year in range 2020-(currentYear-1) adjacent to
                        "updated" or "effective"
  L5 robots-valid     — robots.txt has a Sitemap: line ending in sitemap.xml and no blanket
                        Disallow: /
  L6 sitemap-matches  — sitemap.xml is well-formed XML; every non-404 .html page has a <loc>
                        and every <loc> path resolves to a real file
  L7 contact-real     — contact page has a mailto: with a real-looking address OR a <form>
                        with a non-placeholder action
"""

import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

# ------------------------------------------------------------------ helpers


def fail_msgs():
    msgs = []
    return msgs, lambda m: msgs.append(m)


def _find_page(site_dir: str, keyword: str):
    """Return the first .html filename (basename, no path) whose name contains keyword,
    or None if not found."""
    for name in os.listdir(site_dir):
        if name.endswith(".html") and keyword.lower() in name.lower():
            return name
    return None


def _strip_visible(html: str) -> str:
    """Strip tags, script, style blocks; return visible text."""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


PLACEHOLDER_PATTERNS = [
    r"PLACEHOLDER",
    r"lorem\s+ipsum",
    r"\bTODO\b",
    r"\bFIXME\b",
    r"\{\{",
    r"\[company",
    r"\[your",
]


# ------------------------------------------------------------------ checks

def check_l1_pages_present(site_dir: str, fail):
    """L1: required pages and crawl files all exist."""
    required_keywords = ["privacy", "terms", "about", "contact"]
    for kw in required_keywords:
        if _find_page(site_dir, kw) is None:
            fail(f"L1: no HTML page found whose name contains '{kw}' — "
                 f"a {kw} page is required before launch")
    # 404 page
    has_404 = any("404" in n for n in os.listdir(site_dir) if n.endswith(".html"))
    if not has_404:
        fail("L1: no 404.html page found — a custom 404 is required")
    # robots.txt
    if not os.path.isfile(os.path.join(site_dir, "robots.txt")):
        fail("L1: robots.txt missing — required for crawl configuration")
    # sitemap.xml
    if not os.path.isfile(os.path.join(site_dir, "sitemap.xml")):
        fail("L1: sitemap.xml missing — required for search engine indexing")


def check_l2_substance(site_dir: str, brand: str, fail):
    """L2: each of the 4 legal pages has >= 150 visible words, contains brand name,
    and has no placeholder markers."""
    keywords = ["privacy", "terms", "about", "contact"]
    for kw in keywords:
        fname = _find_page(site_dir, kw)
        if fname is None:
            continue  # L1 already flagged this
        path = os.path.join(site_dir, fname)
        try:
            html = open(path, encoding="utf-8").read()
        except OSError as e:
            fail(f"L2: cannot read {fname}: {e}")
            continue
        visible = _strip_visible(html)
        words = visible.split()
        if len(words) < 150:
            fail(f"L2: {fname} has only {len(words)} visible words (< 150) — "
                 f"add substantive personalized content")
        if brand and brand.lower() not in visible.lower():
            fail(f"L2: {fname} does not contain the brand/tool name '{brand}' — "
                 f"legal pages must be personalized to the actual site")
        for pat in PLACEHOLDER_PATTERNS:
            if re.search(pat, html, re.IGNORECASE):
                fail(f"L2: {fname} contains a placeholder marker matching '{pat}' — "
                     f"replace all placeholders with real content before launch")
                break


def check_l3_double_linked(site_dir: str, fail):
    """L3: every content HTML page contains <a href> links to ALL FOUR legal pages."""
    legal_keywords = ["privacy", "terms", "about", "contact"]
    # Collect legal page filenames
    legal_files = {}
    for kw in legal_keywords:
        fname = _find_page(site_dir, kw)
        legal_files[kw] = fname  # may be None if missing; L1 covers that

    # Collect all HTML files to check
    all_html = [n for n in os.listdir(site_dir) if n.endswith(".html")]
    for html_name in all_html:
        path = os.path.join(site_dir, html_name)
        try:
            content = open(path, encoding="utf-8").read()
        except OSError:
            continue
        # Extract all href values
        hrefs = re.findall(r'<a\s[^>]*href=["\']([^"\']+)["\']', content, re.IGNORECASE)
        href_text = " ".join(hrefs).lower()
        for kw, lfname in legal_files.items():
            if lfname is None:
                continue  # L1 already flagged
            # Check if any href references this legal page (by keyword in path)
            if kw not in href_text:
                fail(f"L3: {html_name} is missing an <a href> link to the {kw} page "
                     f"({lfname}) — every page must link to all four legal pages")


def check_l4_no_stale_dates(site_dir: str, fail):
    """L4: no legal page shows a year in 2020-(currentYear-1) adjacent to
    'updated' or 'effective'."""
    current_year = datetime.now().year
    keywords = ["privacy", "terms", "about", "contact"]
    stale_range = list(range(2020, current_year))  # 2020 through currentYear-1
    pattern = re.compile(
        r"(?:updated|effective)[^.]{0,60}?(" + "|".join(str(y) for y in stale_range) + r")",
        re.IGNORECASE,
    )
    for kw in keywords:
        fname = _find_page(site_dir, kw)
        if fname is None:
            continue
        path = os.path.join(site_dir, fname)
        try:
            html = open(path, encoding="utf-8").read()
        except OSError:
            continue
        m = pattern.search(html)
        if m:
            fail(f"L4: {fname} contains a stale date year ({m.group(1)}) next to "
                 f"'updated' or 'effective' — update the date to {current_year}")


def check_l5_robots_valid(site_dir: str, fail):
    """L5: robots.txt has a Sitemap: line ending in sitemap.xml and no blanket Disallow: /."""
    robots_path = os.path.join(site_dir, "robots.txt")
    if not os.path.isfile(robots_path):
        return  # L1 already flagged
    try:
        content = open(robots_path, encoding="utf-8").read()
    except OSError as e:
        fail(f"L5: cannot read robots.txt: {e}")
        return
    # Must have Sitemap: line ending in sitemap.xml
    if not re.search(r"^Sitemap:.*sitemap\.xml\s*$", content, re.IGNORECASE | re.MULTILINE):
        fail("L5: robots.txt has no 'Sitemap: ...sitemap.xml' line — "
             "add a Sitemap directive so crawlers can discover the sitemap")
    # Must NOT have blanket Disallow: /
    if re.search(r"^Disallow:\s*/\s*$", content, re.MULTILINE):
        fail("L5: robots.txt contains 'Disallow: /' which blocks all crawlers — "
             "remove the blanket disallow directive before launch")


def check_l6_sitemap_matches(site_dir: str, fail):
    """L6: sitemap.xml is well-formed XML with urlset; every non-404 .html page has a <loc>
    and every <loc> path resolves to a file that exists."""
    sitemap_path = os.path.join(site_dir, "sitemap.xml")
    if not os.path.isfile(sitemap_path):
        return  # L1 already flagged
    try:
        tree = ET.parse(sitemap_path)
    except ET.ParseError as e:
        fail(f"L6: sitemap.xml is not well-formed XML: {e}")
        return
    root = tree.getroot()
    # Strip XML namespace for tag matching
    ns_match = re.match(r"\{([^}]+)\}", root.tag)
    ns = ns_match.group(1) if ns_match else ""
    ns_prefix = f"{{{ns}}}" if ns else ""

    if "urlset" not in root.tag:
        fail("L6: sitemap.xml root element is not <urlset> — not a valid sitemap")
        return

    # Collect all <loc> values
    locs = []
    for url_el in root.findall(f"{ns_prefix}url"):
        loc_el = url_el.find(f"{ns_prefix}loc")
        if loc_el is not None and loc_el.text:
            locs.append(loc_el.text.strip())

    # Every non-404 .html page in site_dir must appear in a loc
    html_pages = [n for n in os.listdir(site_dir)
                  if n.endswith(".html") and "404" not in n]
    loc_paths = set()
    for loc in locs:
        # Extract path component (everything after the last slash for simple filenames)
        loc_path = loc.rstrip("/").split("/")[-1]
        if not loc_path:
            loc_path = "index.html"
        elif not loc_path.endswith(".html"):
            loc_path = loc_path + "/index.html" if loc_path else "index.html"
        loc_paths.add(loc_path)
        # Also add the full filename stripped of query/fragment
        raw = re.sub(r"[?#].*", "", loc).rstrip("/").split("/")[-1]
        if raw:
            loc_paths.add(raw)

    for page in html_pages:
        if page not in loc_paths:
            fail(f"L6: {page} exists in site dir but has no <loc> entry in sitemap.xml — "
                 f"add it or it will not be indexed")

    # Every <loc> path must resolve to a real file
    for loc in locs:
        # Extract filename from loc
        loc_file = re.sub(r"[?#].*", "", loc).rstrip("/").split("/")[-1]
        if not loc_file or loc_file == "":
            loc_file = "index.html"
        if loc_file and not os.path.isfile(os.path.join(site_dir, loc_file)):
            fail(f"L6: sitemap.xml <loc> references '{loc_file}' but that file does not "
                 f"exist in the site dir — remove stale loc or create the file")


def check_l7_contact_real(site_dir: str, fail):
    """L7: contact page has a real mailto: OR a <form> with a non-placeholder action."""
    fname = _find_page(site_dir, "contact")
    if fname is None:
        return  # L1 already flagged
    path = os.path.join(site_dir, fname)
    try:
        html = open(path, encoding="utf-8").read()
    except OSError as e:
        fail(f"L7: cannot read {fname}: {e}")
        return

    # Check for mailto: with a real-looking address (user@domain.tld)
    mailto_m = re.search(r'mailto:([^\s"\'<>]+)', html, re.IGNORECASE)
    if mailto_m:
        addr = mailto_m.group(1)
        addr_low = addr.lower()
        # Real-looking: contains @ and a dot in the domain; reject obvious non-addresses
        # (bare "example.com" TLD, placeholder tokens, todo markers)
        fake = (
            addr_low.endswith("@example.com")
            or "placeholder" in addr_low
            or "todo" in addr_low
            or not re.match(r'^[^@]+@[^@]+\.[^@]+$', addr)
        )
        if not fake:
            return  # passes

    # Check for a <form> with a non-empty, non-placeholder action
    form_actions = re.findall(r'<form[^>]*\baction=["\']([^"\']*)["\']', html, re.IGNORECASE)
    for action in form_actions:
        low = action.lower()
        if (action and action != "#"
                and "placeholder" not in low
                and "example" not in low
                and "todo" not in low):
            return  # passes

    fail("L7: contact page has no real contact mechanism — provide a mailto: link with a "
         "real email address OR a <form> with a non-placeholder action URL")


# ------------------------------------------------------------------ runner

def run_gate(site_dir: str) -> int:
    """Run all checks. Return exit code 0 (PASS) or 1 (FAIL)."""
    if not os.path.isdir(site_dir):
        print(f"ERROR: '{site_dir}' is not a directory", file=sys.stderr)
        return 2

    # Detect brand: look for an index.html title tag, take only the part before
    # the first separator ( — | - | : | | ) so "ToolName — Tagline" → "ToolName"
    brand = os.path.basename(os.path.abspath(site_dir))
    index_path = os.path.join(site_dir, "index.html")
    if os.path.isfile(index_path):
        try:
            idx_html = open(index_path, encoding="utf-8").read()
            m = re.search(r"<title[^>]*>([^<]+)</title>", idx_html, re.IGNORECASE)
            if m:
                full_title = m.group(1).strip()
                # Strip tagline: take text before first em-dash, pipe, colon, or hyphen
                brand_m = re.split(r"\s*[—\|\-:]\s*", full_title, maxsplit=1)
                brand = brand_m[0].strip() if brand_m else full_title
        except OSError:
            pass

    msgs, fail = fail_msgs()

    check_l1_pages_present(site_dir, fail)
    check_l2_substance(site_dir, brand, fail)
    check_l3_double_linked(site_dir, fail)
    check_l4_no_stale_dates(site_dir, fail)
    check_l5_robots_valid(site_dir, fail)
    check_l6_sitemap_matches(site_dir, fail)
    check_l7_contact_real(site_dir, fail)

    if msgs:
        for m in msgs:
            print(f"FAIL  {m}")
        print(f"\nlegal_crawl_gate: FAIL ({len(msgs)} issue(s))")
        return 1
    else:
        print("legal_crawl_gate: PASS — all L1-L7 checks green")
        return 0


# ------------------------------------------------------------------ selftest

def _write(path: str, content: str):
    """Write content to path, creating parent dirs as needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def selftest():
    """Run 1 good fixture, >=7 bad fixtures, and 1 invariant mutation."""
    import tempfile
    import shutil

    current_year = datetime.now().year

    # ---------------------------------------------------------------- helpers
    def make_good_site(root: str):
        """Scaffold a minimal but fully compliant site."""
        brand = "QuickCalc"
        legal_link_block = (
            '<footer>'
            '<a href="privacy.html">Privacy</a> '
            '<a href="terms.html">Terms</a> '
            '<a href="about.html">About</a> '
            '<a href="contact.html">Contact</a>'
            '</footer>'
        )
        boilerplate = (
            "This tool is provided as-is without warranty of any kind. "
            "QuickCalc is a free online calculator. We respect your privacy. "
            "Use of this service constitutes acceptance of our terms. "
        ) * 6  # ~150+ words

        def page(title_tag, body_extra=""):
            return (
                f"<!DOCTYPE html><html><head>"
                f"<title>{title_tag}</title>"
                f"</head><body>"
                f"{boilerplate}{body_extra}"
                f"{legal_link_block}"
                f"</body></html>"
            )

        # index.html
        _write(os.path.join(root, "index.html"),
               page("QuickCalc — Free Calculator",
                    '<a href="calculator.html">Calculator</a>'))
        # calculator.html
        _write(os.path.join(root, "calculator.html"),
               page("QuickCalc Calculator", ""))
        # 404.html
        _write(os.path.join(root, "404.html"),
               f"<html><body><h1>404 Not Found</h1>{legal_link_block}</body></html>")
        # privacy.html
        _write(os.path.join(root, "privacy.html"),
               page(f"QuickCalc Privacy Policy",
                    f"Last Updated: January {current_year}. QuickCalc collects no personal data. " * 10))
        # terms.html
        _write(os.path.join(root, "terms.html"),
               page(f"QuickCalc Terms of Service",
                    f"Effective {current_year}. By using QuickCalc you agree to these terms. " * 10))
        # about.html
        _write(os.path.join(root, "about.html"),
               page("About QuickCalc",
                    "QuickCalc was built to help people calculate quickly and accurately. " * 10))
        # contact.html — real mailto
        _write(os.path.join(root, "contact.html"),
               page("Contact QuickCalc",
                    '<p>Email us: <a href="mailto:hello@quickcalc.example.com">hello@quickcalc.example.com</a></p>'
                    "QuickCalc welcomes your feedback. " * 8))
        # robots.txt
        _write(os.path.join(root, "robots.txt"),
               "User-agent: *\nAllow: /\nSitemap: https://quickcalc.example.com/sitemap.xml\n")
        # sitemap.xml — lists all non-404 pages
        _write(os.path.join(root, "sitemap.xml"), (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f'<url><loc>https://quickcalc.example.com/index.html</loc></url>'
            f'<url><loc>https://quickcalc.example.com/calculator.html</loc></url>'
            f'<url><loc>https://quickcalc.example.com/privacy.html</loc></url>'
            f'<url><loc>https://quickcalc.example.com/terms.html</loc></url>'
            f'<url><loc>https://quickcalc.example.com/about.html</loc></url>'
            f'<url><loc>https://quickcalc.example.com/contact.html</loc></url>'
            '</urlset>'
        ))

    # ---------------------------------------------------------------- run case
    def run_case(label: str, site_dir: str) -> list:
        """Return list of FAIL lines."""
        msgs, fail = fail_msgs()
        brand = "QuickCalc"
        check_l1_pages_present(site_dir, fail)
        check_l2_substance(site_dir, brand, fail)
        check_l3_double_linked(site_dir, fail)
        check_l4_no_stale_dates(site_dir, fail)
        check_l5_robots_valid(site_dir, fail)
        check_l6_sitemap_matches(site_dir, fail)
        check_l7_contact_real(site_dir, fail)
        return msgs

    errors = []

    # ---------------------------------------------------------- GOOD fixture
    tmp = tempfile.mkdtemp()
    try:
        make_good_site(tmp)
        msgs = run_case("good", tmp)
        if msgs:
            errors.append(f"GOOD fixture unexpectedly FAILED: {msgs}")
    finally:
        shutil.rmtree(tmp)

    # ---------------------------------------------------------- BAD fixtures

    bad_cases = []  # list of (label, description) pairs for passed bad cases

    # bad-L1: missing about page
    tmp = tempfile.mkdtemp()
    try:
        make_good_site(tmp)
        os.remove(os.path.join(tmp, "about.html"))
        msgs = run_case("bad-L1-missing-about", tmp)
        if not any("about" in m for m in msgs):
            errors.append("bad-L1: should have failed on missing about page")
        else:
            bad_cases.append(("bad-L1", "missing about page → L1 FAIL"))
    finally:
        shutil.rmtree(tmp)

    # bad-L2: placeholder in privacy.html
    tmp = tempfile.mkdtemp()
    try:
        make_good_site(tmp)
        priv = os.path.join(tmp, "privacy.html")
        content = open(priv).read()
        open(priv, "w").write(content.replace("QuickCalc collects no personal data.", "[company] collects no personal data."))
        msgs = run_case("bad-L2-placeholder", tmp)
        if not any("L2" in m and "placeholder" in m.lower() for m in msgs):
            errors.append("bad-L2: should have failed on placeholder marker")
        else:
            bad_cases.append(("bad-L2", "placeholder '[company]' in privacy → L2 FAIL"))
    finally:
        shutil.rmtree(tmp)

    # bad-L3: index.html missing link to about page
    tmp = tempfile.mkdtemp()
    try:
        make_good_site(tmp)
        idx = os.path.join(tmp, "index.html")
        content = open(idx).read()
        # Remove the about link
        open(idx, "w").write(content.replace('<a href="about.html">About</a> ', ''))
        msgs = run_case("bad-L3-missing-about-link", tmp)
        if not any("L3" in m and "about" in m.lower() for m in msgs):
            errors.append("bad-L3: should have failed on missing about link in index.html")
        else:
            bad_cases.append(("bad-L3", "index.html missing about link → L3 FAIL"))
    finally:
        shutil.rmtree(tmp)

    # bad-L4: stale date in terms.html
    tmp = tempfile.mkdtemp()
    try:
        make_good_site(tmp)
        terms = os.path.join(tmp, "terms.html")
        content = open(terms).read()
        # inject a stale year (current_year - 2) next to "Effective"
        stale_year = current_year - 2
        open(terms, "w").write(content.replace(f"Effective {current_year}",
                                               f"Effective {stale_year}"))
        msgs = run_case("bad-L4-stale-date", tmp)
        if not any("L4" in m for m in msgs):
            errors.append(f"bad-L4: should have failed on stale year {stale_year} in terms.html")
        else:
            bad_cases.append(("bad-L4", f"stale year {stale_year} in terms → L4 FAIL"))
    finally:
        shutil.rmtree(tmp)

    # bad-L5: robots.txt has blanket Disallow: /
    tmp = tempfile.mkdtemp()
    try:
        make_good_site(tmp)
        _write(os.path.join(tmp, "robots.txt"),
               "User-agent: *\nDisallow: /\nSitemap: https://quickcalc.example.com/sitemap.xml\n")
        msgs = run_case("bad-L5-disallow-all", tmp)
        if not any("L5" in m and "Disallow" in m for m in msgs):
            errors.append("bad-L5: should have failed on blanket Disallow: /")
        else:
            bad_cases.append(("bad-L5", "blanket Disallow: / in robots.txt → L5 FAIL"))
    finally:
        shutil.rmtree(tmp)

    # bad-L6: sitemap.xml references a file that does not exist
    tmp = tempfile.mkdtemp()
    try:
        make_good_site(tmp)
        _write(os.path.join(tmp, "sitemap.xml"), (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>https://quickcalc.example.com/ghost-page.html</loc></url>'
            '</urlset>'
        ))
        msgs = run_case("bad-L6-stale-loc", tmp)
        if not any("L6" in m for m in msgs):
            errors.append("bad-L6: should have failed on sitemap loc / page mismatch")
        else:
            bad_cases.append(("bad-L6", "sitemap loc/file mismatch → L6 FAIL"))
    finally:
        shutil.rmtree(tmp)

    # bad-L7: contact page has only a placeholder form action
    tmp = tempfile.mkdtemp()
    try:
        make_good_site(tmp)
        contact = os.path.join(tmp, "contact.html")
        content = open(contact).read()
        # Replace the mailto with a placeholder form
        new_content = content.replace(
            '<p>Email us: <a href="mailto:hello@quickcalc.example.com">hello@quickcalc.example.com</a></p>',
            '<form action="https://formspree.io/f/PLACEHOLDER"><input type="email"><button>Send</button></form>'
        )
        open(contact, "w").write(new_content)
        msgs = run_case("bad-L7-placeholder-form", tmp)
        if not any("L7" in m for m in msgs):
            errors.append("bad-L7: should have failed on placeholder form action")
        else:
            bad_cases.append(("bad-L7", "placeholder form action in contact → L7 FAIL"))
    finally:
        shutil.rmtree(tmp)

    # ---------------------------------------------------------- INVARIANT
    # Gut robots.txt entirely → a PASS site must flip to FAIL
    tmp = tempfile.mkdtemp()
    try:
        make_good_site(tmp)
        os.remove(os.path.join(tmp, "robots.txt"))
        msgs = run_case("invariant-no-robots", tmp)
        if not msgs:
            errors.append("INVARIANT: removing robots.txt should cause FAIL but got PASS")
    finally:
        shutil.rmtree(tmp)

    # ---------------------------------------------------------- Report
    b = len(bad_cases)
    if errors:
        for e in errors:
            print(f"SELFTEST ERROR: {e}")
        print(f"SELFTEST RESULT: FAIL")
        sys.exit(1)
    else:
        print(f"SELFTEST RESULT: PASS (1 good, {b} bad, 1 invariant)")
        sys.exit(0)


# ------------------------------------------------------------------ main

def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        selftest()
        return
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/legal_crawl_gate.py <site-dir>", file=sys.stderr)
        print("       python3 scripts/legal_crawl_gate.py --selftest", file=sys.stderr)
        sys.exit(2)
    site_dir = sys.argv[1]
    sys.exit(run_gate(site_dir))


if __name__ == "__main__":
    main()
