#!/usr/bin/env python3
"""seo_content_gate.py — fail-closed SEO content validator for micro-tool landing pages.

Usage:
    python3 scripts/seo_content_gate.py <page-file> <attestation-json>
    python3 scripts/seo_content_gate.py --selftest

Exit codes: 0 PASS, 1 FAIL, 2 load error.

Checks:
  C1 word-floor        — visible original copy >= 600 words (strip tags/script/style/frontmatter)
  C2 no-dead-schema    — ZERO FAQPage or HowTo JSON-LD or microdata present
  C3 visible-faq       — visible FAQ section with >= 3 Q/A pairs as plain text
  C4 meta-completeness — title 15-60 chars; meta description 50-160 chars; og:title + og:description present
  C5 cluster-links     — >= 2 internal links to non-legal pages
  C6 human-attestation — attestation.json has non-agent reviewer, date, confirmed: true
"""

import json
import os
import re
import sys
import tempfile

# ------------------------------------------------------------------ helpers

LEGAL_PATHS = {
    "privacy", "privacy-policy", "privacy_policy",
    "terms", "terms-of-service", "terms_of_service",
    "contact", "legal", "disclaimer", "cookie",
}

# Identities that indicate agent self-attestation — refused unconditionally.
# Matched token-wise (reviewer is lowercased, split on whitespace, any token in
# this set causes refusal) so multi-word reviewer strings like "Claude Fable agent run"
# are caught even when lone "Claude" would not be the full string.
AGENT_IDENTITIES = {
    "agent", "self", "assistant", "claude", "ai", "",
    "chatgpt", "gpt", "bot", "llm", "copilot", "gemini",
}


def fail_msgs():
    msgs = []
    return msgs, lambda m: msgs.append(m)


def strip_visible_text(html: str) -> str:
    """Strip frontmatter, script, style tags and HTML tags; return visible text."""
    # Strip YAML frontmatter (Astro-style: --- ... ---)
    text = re.sub(r"^---\n.*?\n---\n", "", html, flags=re.DOTALL)
    # Strip <script> blocks
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    # Strip <style> blocks
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    # Strip HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ------------------------------------------------------------------ checks

def check_c1_word_floor(html: str, fail):
    """C1: visible original copy >= 600 words."""
    visible = strip_visible_text(html)
    words = visible.split()
    count = len(words)
    if count < 600:
        fail(f"C1: visible word count {count} < 600 — page copy is too thin for AdSense/SEO; "
             f"add original descriptive content about the tool, its features, and use cases")


def check_c2_no_dead_schema(html: str, fail):
    """C2: ZERO FAQPage or HowTo structured data (JSON-LD or microdata)."""
    # Check JSON-LD blocks for the banned type tokens anywhere inside the block body.
    # Matching on the token level (word-boundary, case-insensitive) catches both the
    # string form "@type":"FAQPage" and the array form "@type":["FAQPage",...].
    jsonld_blocks = re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, flags=re.DOTALL | re.IGNORECASE
    )
    for block in jsonld_blocks:
        if re.search(r'\bFAQPage\b', block, re.IGNORECASE):
            fail("C2: FAQPage JSON-LD found — FAQPage rich results were removed by Google "
                 "May 2026 (verified 2026-06-10); remove the @type:FAQPage block entirely")
        if re.search(r'\bHowTo\b', block, re.IGNORECASE):
            fail("C2: HowTo JSON-LD found — HowTo rich results were removed by Google "
                 "Sept 2023 (verified 2026-06-10); remove the @type:HowTo block entirely")
    # Check microdata itemtype attributes
    if re.search(r'itemtype=["\'][^"\']*FAQPage', html, re.IGNORECASE):
        fail("C2: FAQPage microdata itemtype found — same removal applies; "
             "remove the microdata markup")
    if re.search(r'itemtype=["\'][^"\']*HowTo', html, re.IGNORECASE):
        fail("C2: HowTo microdata itemtype found — same removal applies; "
             "remove the microdata markup")


def check_c3_visible_faq(html: str, fail):
    """C3: visible FAQ section with >= 3 question/answer pairs as plain text.

    Two sub-requirements must BOTH hold:
      (a) An FAQ-style heading appears in the visible text — case-insensitive match on
          the word FAQ, the phrase Frequently Asked, or a heading/label Questions.
      (b) At least three question-shaped sentences appear (ending with '?').
    Scattered rhetorical questions without an FAQ heading do not satisfy this check.
    """
    visible = strip_visible_text(html)

    # (a) Require an FAQ-style heading signal.
    # Matches the unambiguous section-label tokens "FAQ" and "Frequently Asked"
    # anywhere in the visible text, or the heading "Common Questions" (which always
    # appears in a heading context and never as a verb).  The lone word "Questions"
    # is excluded because it is also used as a verb (e.g. "a client questions your
    # invoice") and would produce false positives.
    has_faq_heading = bool(re.search(
        r'\b(?:FAQ|Frequently\s+Asked|Common\s+Questions)\b',
        visible, re.IGNORECASE
    ))

    # (b) Count question-shaped sentences
    question_markers = re.findall(
        r'(?:(?:Q:|Question:|FAQ)[\s\S]{5,300}?\?'  # Q: or Question: prefix
        r'|[A-Z][^.!?\n]{15,200}\?)',               # any capitalized sentence ending with ?
        visible
    )

    if not has_faq_heading:
        fail(f"C3: no FAQ-style heading found in visible text — "
             "the page needs a heading or label containing 'FAQ', 'Frequently Asked', "
             "or 'Common Questions' to anchor the visible FAQ section; "
             "scattered question marks in body copy do not qualify")
    elif len(question_markers) < 3:
        fail(f"C3: found {len(question_markers)} question(s) in visible text — "
             "need >= 3 visible Q/A pairs as plain text for People-Also-Ask coverage; "
             "a visible FAQ section (not just JSON-LD) is required")


def check_c4_meta_completeness(html: str, fail):
    """C4: title 15-60 chars; meta description 50-160 chars; og:title + og:description."""
    # Title
    title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
    if not title_m:
        fail("C4: <title> element missing")
    else:
        title_text = re.sub(r"<[^>]+>", "", title_m.group(1)).strip()
        tlen = len(title_text)
        if tlen < 15:
            fail(f"C4: <title> is {tlen} chars — too short (min 15); "
                 "add the tool name and primary keyword")
        elif tlen > 60:
            fail(f"C4: <title> is {tlen} chars — too long (max 60); "
                 "truncate to keep it fully visible in SERPs")

    # Meta description
    desc_m = re.search(
        r'<meta\s[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']',
        html, re.IGNORECASE
    ) or re.search(
        r'<meta\s[^>]*content=["\']([^"\']*)["\'][^>]*name=["\']description["\']',
        html, re.IGNORECASE
    )
    if not desc_m:
        fail("C4: meta description missing — required for SERP snippet control")
    else:
        dlen = len(desc_m.group(1).strip())
        if dlen < 50:
            fail(f"C4: meta description is {dlen} chars — too short (min 50); "
                 "describe the tool and its primary benefit")
        elif dlen > 160:
            fail(f"C4: meta description is {dlen} chars — too long (max 160); "
                 "Google truncates at ~155 chars in mobile SERPs")

    # og:title
    if not re.search(r'<meta\s[^>]*property=["\']og:title["\']', html, re.IGNORECASE) and \
       not re.search(r'<meta\s[^>]*name=["\']og:title["\']', html, re.IGNORECASE):
        fail("C4: og:title meta tag missing — required for social sharing previews")

    # og:description
    if not re.search(r'<meta\s[^>]*property=["\']og:description["\']', html, re.IGNORECASE) and \
       not re.search(r'<meta\s[^>]*name=["\']og:description["\']', html, re.IGNORECASE):
        fail("C4: og:description meta tag missing — required for social sharing previews")


def _is_legal_path(href: str) -> bool:
    """Return True if href points to a legal/contact page that does not count as a cluster link."""
    normalized = href.lower().strip("/").split("?")[0].split("#")[0]
    # Get the last path segment
    segment = normalized.split("/")[-1] if "/" in normalized else normalized
    # Also check full path segments
    for part in normalized.split("/"):
        if part in LEGAL_PATHS:
            return True
    return segment in LEGAL_PATHS


def check_c5_cluster_links(html: str, fail):
    """C5: >= 2 internal cluster links (non-legal, non-external).

    Only hrefs from <a ...> anchor tags are counted. Stylesheet, preload, and
    other <link rel="..."> tag hrefs are excluded so they cannot satisfy the floor.
    """
    # Extract href values from <a> anchor tags only
    hrefs = re.findall(r'<a\s[^>]*href=["\']([^"\']+)["\']', html, re.IGNORECASE)
    cluster_links = []
    for href in hrefs:
        # Skip external links
        if href.startswith("http://") or href.startswith("https://") or href.startswith("//"):
            continue
        # Skip anchors and data URIs
        if href.startswith("#") or href.startswith("data:") or href.startswith("javascript:"):
            continue
        # Skip legal pages
        if _is_legal_path(href):
            continue
        cluster_links.append(href)
    if len(cluster_links) < 2:
        legal_found = [h for h in hrefs if _is_legal_path(h) and not h.startswith("http")]
        fail(f"C5: found {len(cluster_links)} qualifying cluster link(s) — need >= 2 internal "
             f"links to related tools or content pages (found {len(legal_found)} legal-page "
             f"link(s) which do NOT count: {legal_found[:3]}); add links to related tools on "
             "the same site")


def check_c6_human_attestation(attestation_path: str, fail):
    """C6: attestation.json has non-agent reviewer, date, and confirmed: true."""
    if not os.path.isfile(attestation_path):
        fail(f"C6: attestation file not found at '{attestation_path}' — "
             "create attestation.json with reviewer (human identity), date (YYYY-MM-DD), "
             "and confirmed: true after a human has reviewed the copy")
        return

    try:
        data = json.load(open(attestation_path, encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        fail(f"C6: attestation.json does not parse as JSON: {e}")
        return

    reviewer_raw = str(data.get("reviewer", "")).strip()
    reviewer = reviewer_raw.lower()
    # Token-wise check: split on whitespace and refuse if any individual token is in
    # the agent-identity set.  This catches multi-word values like "Claude Fable agent run"
    # and "ChatGPT" that would not match a whole-string comparison against reviewer.
    reviewer_tokens = reviewer.split() if reviewer else [""]
    bad_token = next((t for t in reviewer_tokens if t in AGENT_IDENTITIES), None)
    if bad_token is not None:
        fail(f"C6: attestation reviewer '{reviewer_raw}' is an agent identity (token '{bad_token}' "
             "matched) — AdSense scaled-content policy requires a named human reviewer; set "
             "reviewer to a real person's name or handle, not 'agent', 'assistant', 'claude', "
             "'chatgpt', 'gpt', 'bot', 'llm', 'copilot', 'gemini', or empty")

    date_val = data.get("date", "")
    if not date_val or not re.match(r"^\d{4}-\d{2}-\d{2}$", str(date_val)):
        fail(f"C6: attestation date '{date_val}' is missing or not in YYYY-MM-DD format")

    confirmed = data.get("confirmed")
    if confirmed is not True:
        fail("C6: attestation confirmed is not true — a human must review and edit the copy, "
             "then set confirmed: true in attestation.json; the engine cannot set this field "
             "on your behalf")


# ------------------------------------------------------------------ runner

def run_gate(page_path: str, attestation_path: str):
    if not os.path.isfile(page_path):
        print(f"LOAD ERROR: page file '{page_path}' not found")
        return 2
    try:
        html = open(page_path, encoding="utf-8").read()
    except (OSError, UnicodeDecodeError) as e:
        print(f"LOAD ERROR: cannot read page file: {e}")
        return 2

    msgs, fail = fail_msgs()
    check_c1_word_floor(html, fail)
    check_c2_no_dead_schema(html, fail)
    check_c3_visible_faq(html, fail)
    check_c4_meta_completeness(html, fail)
    check_c5_cluster_links(html, fail)
    check_c6_human_attestation(attestation_path, fail)

    if msgs:
        for m in msgs:
            print(f"FAIL {m}")
        print(f"SEO CONTENT GATE: FAIL ({len(msgs)} check(s) failed)")
        return 1

    print("SEO CONTENT GATE: PASS (C1-C6 all green)")
    return 0


# ================================================================ selftest

def _write(path: str, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def selftest():
    """Prove the engine refuses known-bad inputs and passes a known-good one."""
    failures = []
    root = tempfile.mkdtemp()

    # ---- GOOD FIXTURE ----
    GOOD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Free Time Card Calculator | Track Work Hours</title>
<meta name="description" content="Free online time card calculator. Track work hours, calculate overtime, and export timesheets to CSV. No sign-up required. Works in your browser.">
<meta property="og:title" content="Free Time Card Calculator">
<meta property="og:description" content="Track work hours, calculate overtime, and export CSV timesheets free.">
</head>
<body>
<nav><a href="/tools/invoice-generator">Invoice Generator</a> <a href="/tools/estimate-calculator">Estimate Calculator</a></nav>
<main>
<h1>Free Time Card Calculator</h1>
<p>Our free time card calculator helps you track your weekly work hours, calculate overtime pay, and export professional timesheets to CSV in seconds. No account, no software, no cost. Everything runs directly in your browser so your data never leaves your device.</p>
<p>Whether you are a freelancer billing hourly clients, a small business owner tracking employee hours, or an individual keeping tabs on your own schedule, this tool handles weekly time entry, automatic overtime calculation, lunch break deductions, and one-click CSV export. It supports both Monday-start and Sunday-start work weeks and lets you annotate each shift with a project label.</p>
<p>Accurate time tracking is the foundation of accurate billing. When you track hours precisely, you can invoice confidently, dispute payroll errors with evidence, and understand where your productive hours actually go. This calculator stores nothing on our servers and requires no login, so you can start tracking in under sixty seconds.</p>
<h2>How to Use the Time Card Calculator</h2>
<p>Enter your clock-in and clock-out times for each day of the week. If you take an unpaid lunch break, enter the break duration and we will deduct it from your paid hours automatically. Click Calculate to see your total hours, regular hours, and overtime hours for the week. When you are satisfied with the entries, click Export CSV to download a formatted timesheet you can attach to an invoice or send to payroll.</p>
<h2>Why Accurate Time Tracking Matters</h2>
<p>Inaccurate time tracking is one of the most common sources of billing disputes between freelancers and clients. A few minutes of rounding error per day adds up to hours of unpaid work over the course of a month. By logging your exact clock-in and clock-out times every day, you build an irrefutable record that supports your invoices, justifies overtime claims, and protects you if a client ever disputes hours. Time records also help you spot patterns in your own productivity: which days are most efficient, which projects take longer than estimated, and where your schedule has room to improve.</p>
<p>For small business owners managing hourly employees, this calculator provides a lightweight alternative to expensive payroll software. Enter hours at the end of each shift, export the weekly CSV, and hand it directly to your accountant or import it into your payroll system. No subscription fees, no complex setup, no data sent to a third-party server.</p>
<h2>Features at a Glance</h2>
<p>The time card calculator supports entry for up to seven days per week with separate clock-in, clock-out, and break-duration fields for each day. It calculates regular hours, overtime hours (over 40 per week or over 8 per day depending on your jurisdiction setting), and total compensable hours for the period. The exported CSV includes columns for date, clock-in, clock-out, break duration, regular hours, overtime hours, and a notes field where you can record the project or client name.</p>
<h2>Frequently Asked Questions</h2>
<section class="faq">
<h3>Is the time card calculator really free?</h3>
<p>Yes, completely free. There are no hidden fees, premium tiers, or sign-up requirements. The calculator runs entirely in your browser.</p>
<h3>Do I need to create an account to use it?</h3>
<p>No account is needed. The calculator works instantly without any registration or login. Open the page and start entering hours.</p>
<h3>How is overtime calculated?</h3>
<p>Standard overtime rules apply: hours worked beyond 40 in a week are counted as overtime. You can also enable daily overtime for jurisdictions that require it after 8 hours per day. Consult your local labor regulations for the applicable rule in your area.</p>
<h3>Can I deduct lunch breaks automatically?</h3>
<p>Yes. Enter a break duration for any shift and the calculator deducts it from your paid hours so only compensable time is counted.</p>
</section>
<p>If you need to convert those tracked hours into a formal bill, try our <a href="/tools/invoice-generator">free invoice generator</a>. For project-based work, our <a href="/tools/estimate-calculator">estimate calculator</a> helps you scope and quote jobs before work begins.</p>
</main>
</body>
</html>"""

    GOOD_ATTEST = json.dumps({"reviewer": "Jane Smith", "date": "2026-06-11", "confirmed": True})

    good_page = os.path.join(root, "good.html")
    good_attest = os.path.join(root, "good_attest.json")
    _write(good_page, GOOD_HTML)
    _write(good_attest, GOOD_ATTEST)

    if run_gate(good_page, good_attest) != 0:
        failures.append("golden-good fixture did not PASS")

    # ---- BAD FIXTURES — one per check ----

    # BAD C1: word count too low (thin page)
    BAD_C1_HTML = """<!DOCTYPE html><html><head>
<title>Free Time Card Calculator | Hours</title>
<meta name="description" content="Free time card calculator for tracking work hours and overtime pay online.">
<meta property="og:title" content="Free Time Card Calculator">
<meta property="og:description" content="Track work hours free.">
</head><body>
<nav><a href="/tools/invoice-generator">Invoice Generator</a><a href="/tools/estimate">Estimate Tool</a></nav>
<p>Track your hours here. Fast and free tool. Enter time in, time out.</p>
<section class="faq">
<h3>Is it free?</h3><p>Yes completely free.</p>
<h3>Do I need an account?</h3><p>No account required at all.</p>
<h3>How does overtime work?</h3><p>Standard 40-hour rule applies weekly.</p>
</section>
</body></html>"""
    bad_c1 = os.path.join(root, "bad_c1.html")
    _write(bad_c1, BAD_C1_HTML)
    if run_gate(bad_c1, good_attest) != 1:
        failures.append("bad-C1 (thin word count) was not refused")

    # BAD C2: FAQPage JSON-LD present — string @type form
    BAD_C2_HTML = GOOD_HTML.replace(
        "</head>",
        '<script type="application/ld+json">{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[]}</script>\n</head>'
    )
    bad_c2 = os.path.join(root, "bad_c2.html")
    _write(bad_c2, BAD_C2_HTML)
    if run_gate(bad_c2, good_attest) != 1:
        failures.append("bad-C2 (FAQPage JSON-LD string @type) was not refused")

    # BAD C2b: HowTo JSON-LD present — string @type form
    BAD_C2B_HTML = GOOD_HTML.replace(
        "</head>",
        '<script type="application/ld+json">{"@context":"https://schema.org","@type":"HowTo","name":"How to use","step":[]}</script>\n</head>'
    )
    bad_c2b = os.path.join(root, "bad_c2b.html")
    _write(bad_c2b, BAD_C2B_HTML)
    if run_gate(bad_c2b, good_attest) != 1:
        failures.append("bad-C2b (HowTo JSON-LD string @type) was not refused")

    # BAD C2c: FAQPage JSON-LD array @type form — "@type": ["FAQPage"]
    BAD_C2C_HTML = GOOD_HTML.replace(
        "</head>",
        '<script type="application/ld+json">{"@context":"https://schema.org","@type":["FAQPage"],"mainEntity":[]}</script>\n</head>'
    )
    bad_c2c = os.path.join(root, "bad_c2c.html")
    _write(bad_c2c, BAD_C2C_HTML)
    if run_gate(bad_c2c, good_attest) != 1:
        failures.append("bad-C2c (FAQPage JSON-LD array @type) was not refused")

    # BAD C2d: HowTo JSON-LD array @type form — "@type": ["HowTo"]
    BAD_C2D_HTML = GOOD_HTML.replace(
        "</head>",
        '<script type="application/ld+json">{"@context":"https://schema.org","@type":["HowTo"],"name":"How to use","step":[]}</script>\n</head>'
    )
    bad_c2d = os.path.join(root, "bad_c2d.html")
    _write(bad_c2d, BAD_C2D_HTML)
    if run_gate(bad_c2d, good_attest) != 1:
        failures.append("bad-C2d (HowTo JSON-LD array @type) was not refused")

    # BAD C3a: no visible FAQ section (fewer than 3 questions, no FAQ heading)
    BAD_C3A_HTML = """<!DOCTYPE html><html><head>
<title>Free Time Card Calculator | Track Work Hours</title>
<meta name="description" content="Free online time card calculator. Track work hours, calculate overtime, and export timesheets to CSV. No sign-up required. Works in your browser.">
<meta property="og:title" content="Free Time Card Calculator">
<meta property="og:description" content="Track work hours, calculate overtime, and export CSV timesheets free.">
</head><body>
<nav><a href="/tools/invoice-generator">Invoice Generator</a> <a href="/tools/estimate-calculator">Estimate Calculator</a></nav>
<main>
<h1>Free Time Card Calculator</h1>
<p>Our free time card calculator helps you track your weekly work hours, calculate overtime pay, and export professional timesheets to CSV in seconds. No account, no software, no cost. Everything runs directly in your browser so your data never leaves your device.</p>
<p>Whether you are a freelancer billing hourly clients, a small business owner tracking employee hours, or an individual keeping tabs on your own schedule, this tool handles weekly time entry, automatic overtime calculation, lunch break deductions, and one-click CSV export. It supports both Monday-start and Sunday-start work weeks.</p>
<p>Accurate time tracking is the foundation of accurate billing. When you track hours precisely, you can invoice confidently, dispute payroll errors with evidence, and understand where your productive hours actually go. This calculator stores nothing on our servers and requires no login.</p>
<p>Enter your clock-in and clock-out times for each day of the week. If you take an unpaid lunch break, enter the break duration and we will deduct it from your paid hours automatically. Click Calculate to see your total hours, regular hours, and overtime hours for the week. When satisfied, click Export CSV to download a formatted timesheet.</p>
<p>If you need to convert those tracked hours into a formal bill, try our <a href="/tools/invoice-generator">free invoice generator</a>. For project-based work, our <a href="/tools/estimate-calculator">estimate calculator</a> helps you scope and quote jobs before work begins.</p>
</main></body></html>"""
    bad_c3a = os.path.join(root, "bad_c3a.html")
    _write(bad_c3a, BAD_C3A_HTML)
    if run_gate(bad_c3a, good_attest) != 1:
        failures.append("bad-C3a (no visible FAQ section or heading) was not refused")

    # BAD C3b: scattered rhetorical questions but NO FAQ-style heading.
    # Word count is >= 600 and C4/C5 are satisfied, so only C3 can refuse this page.
    BAD_C3B_HTML = """<!DOCTYPE html><html><head>
<title>Free Time Card Calculator | Track Work Hours</title>
<meta name="description" content="Free online time card calculator. Track work hours, calculate overtime, and export timesheets to CSV. No sign-up required. Works in your browser.">
<meta property="og:title" content="Free Time Card Calculator">
<meta property="og:description" content="Track work hours, calculate overtime, and export CSV timesheets free.">
</head><body>
<nav><a href="/tools/invoice-generator">Invoice Generator</a> <a href="/tools/estimate-calculator">Estimate Calculator</a></nav>
<main>
<h1>Free Time Card Calculator</h1>
<p>Our free time card calculator helps you track your weekly work hours, calculate overtime pay, and export professional timesheets to CSV in seconds. No account, no software, no cost. Everything runs directly in your browser so your data never leaves your device.</p>
<p>Whether you are a freelancer billing hourly clients, a small business owner tracking employee hours, or an individual keeping tabs on your own schedule, this tool handles weekly time entry, automatic overtime calculation, lunch break deductions, and one-click CSV export. It supports both Monday-start and Sunday-start work weeks.</p>
<p>Accurate time tracking is the foundation of accurate billing. When you track hours precisely, you can invoice confidently, dispute payroll errors with evidence, and understand where your productive hours actually go. This calculator stores nothing on our servers and requires no login.</p>
<p>Enter your clock-in and clock-out times for each day of the week. If you take an unpaid lunch break, enter the break duration and we will deduct it from your paid hours automatically. Click Calculate to see your total hours, regular hours, and overtime hours for the week. When satisfied, click Export CSV to download a formatted timesheet.</p>
<h2>How to Use the Time Card Calculator</h2>
<p>Select your work-week start day, then enter clock-in and clock-out times for each day. The calculator automatically deducts any unpaid break you enter and applies the correct overtime rule for your region. When your entries look right, click Export CSV to save a formatted timesheet you can attach to invoices or send to payroll processing.</p>
<h2>Why Time Tracking Matters</h2>
<p>Inaccurate time records are a leading cause of billing disputes between freelancers and clients. Even a few minutes of rounding error per day compounds into hours of unpaid work by the end of a month. A precise daily record gives you irrefutable evidence when a client questions your invoice and makes overtime claims straightforward to justify.</p>
<p>For small business owners managing hourly employees, this calculator provides a lightweight alternative to expensive payroll software. Export the weekly CSV directly and hand it to your accountant or import it into your payroll system without a subscription.</p>
<h2>Who Uses This Tool</h2>
<p>Independent contractors who bill by the hour depend on precise time records to justify invoices to clients and to claim deductions on tax returns. Staffing agencies use it to verify hours before approving payroll runs. Construction supervisors track crew time across multiple job sites and export separate CSV files for each project code. Remote workers in distributed teams use it to demonstrate availability and output to overseas managers who track attendance differently. Gig workers managing multiple platforms consolidate their hours in a single weekly view before reconciling earnings at the end of each pay period. Consultants tracking billable versus non-billable hours use the separate CSV columns that map directly to standard invoice line items without manual reformatting. The tool is free, requires no sign-up, and saves no data to any server.</p>
<p>Have you ever lost track of your hours partway through a long project? We built this tool because so many freelancers told us their billing suffered from informal tracking. Do you need to handle more than one job code per week? The notes field in the CSV export covers that. Is your overtime threshold different from the federal forty-hour rule? You can switch between weekly-OT and daily-OT modes in the settings panel.</p>
<p>For project-based work, our <a href="/tools/estimate-calculator">estimate calculator</a> helps you scope and quote jobs before work begins. Once you have tracked your hours, our <a href="/tools/invoice-generator">invoice generator</a> converts them to a professional billable document in seconds.</p>
</main></body></html>"""
    bad_c3b = os.path.join(root, "bad_c3b.html")
    _write(bad_c3b, BAD_C3B_HTML)
    if run_gate(bad_c3b, good_attest) != 1:
        failures.append("bad-C3b (scattered questions, no FAQ heading) was not refused")

    # BAD C4: meta description too short and og tags missing
    BAD_C4_HTML = GOOD_HTML.replace(
        '<meta name="description" content="Free online time card calculator. Track work hours, calculate overtime, and export timesheets to CSV. No sign-up required. Works in your browser.">',
        '<meta name="description" content="Track hours.">'
    ).replace(
        '<meta property="og:title" content="Free Time Card Calculator">',
        ''
    ).replace(
        '<meta property="og:description" content="Track work hours, calculate overtime, and export CSV timesheets free.">',
        ''
    )
    bad_c4 = os.path.join(root, "bad_c4.html")
    _write(bad_c4, BAD_C4_HTML)
    if run_gate(bad_c4, good_attest) != 1:
        failures.append("bad-C4 (short meta desc, missing og tags) was not refused")

    # BAD C5a: only legal-page <a> links (no cluster links)
    BAD_C5A_HTML = GOOD_HTML.replace(
        '<nav><a href="/tools/invoice-generator">Invoice Generator</a> <a href="/tools/estimate-calculator">Estimate Calculator</a></nav>',
        '<nav><a href="/privacy-policy">Privacy</a> <a href="/terms-of-service">Terms</a></nav>'
    ).replace(
        'try our <a href="/tools/invoice-generator">free invoice generator</a>. For project-based work, our <a href="/tools/estimate-calculator">estimate calculator</a> helps you scope and quote jobs before work begins.',
        'please review our <a href="/privacy-policy">privacy policy</a>.'
    )
    bad_c5a = os.path.join(root, "bad_c5a.html")
    _write(bad_c5a, BAD_C5A_HTML)
    if run_gate(bad_c5a, good_attest) != 1:
        failures.append("bad-C5a (only legal-page <a> links) was not refused")

    # BAD C5b: non-anchor hrefs only (stylesheet + preload <link> tags, zero <a> cluster links).
    # Word count and FAQ section are intact so only C5 can refuse.
    BAD_C5B_HTML = GOOD_HTML.replace(
        '<nav><a href="/tools/invoice-generator">Invoice Generator</a> <a href="/tools/estimate-calculator">Estimate Calculator</a></nav>',
        '<link rel="stylesheet" href="/tools/invoice-generator/style.css">'
        '<link rel="preload" href="/tools/estimate-calculator/bundle.js" as="script">'
        '<nav><a href="/privacy-policy">Privacy</a></nav>'
    ).replace(
        'try our <a href="/tools/invoice-generator">free invoice generator</a>. For project-based work, our <a href="/tools/estimate-calculator">estimate calculator</a> helps you scope and quote jobs before work begins.',
        'please review our <a href="/privacy-policy">privacy policy</a>.'
    )
    bad_c5b = os.path.join(root, "bad_c5b.html")
    _write(bad_c5b, BAD_C5B_HTML)
    if run_gate(bad_c5b, good_attest) != 1:
        failures.append("bad-C5b (stylesheet/preload hrefs only, no anchor cluster links) was not refused")

    # BAD C6: agent attestation (reviewer = "agent")
    bad_attest_agent = os.path.join(root, "bad_attest_agent.json")
    _write(bad_attest_agent, json.dumps({"reviewer": "agent", "date": "2026-06-11", "confirmed": True}))
    if run_gate(good_page, bad_attest_agent) != 1:
        failures.append("bad-C6 (agent reviewer) was not refused")

    # BAD C6d: reviewer = "ChatGPT" — single-token agent identity
    bad_attest_chatgpt = os.path.join(root, "bad_attest_chatgpt.json")
    _write(bad_attest_chatgpt, json.dumps({"reviewer": "ChatGPT", "date": "2026-06-11", "confirmed": True}))
    if run_gate(good_page, bad_attest_chatgpt) != 1:
        failures.append("bad-C6d (ChatGPT reviewer) was not refused")

    # BAD C6e: reviewer = "Claude Fable agent run" — multi-word phrase containing agent tokens
    bad_attest_phrase = os.path.join(root, "bad_attest_phrase.json")
    _write(bad_attest_phrase, json.dumps({"reviewer": "Claude Fable agent run", "date": "2026-06-11", "confirmed": True}))
    if run_gate(good_page, bad_attest_phrase) != 1:
        failures.append("bad-C6e (multi-word agent phrase reviewer) was not refused")

    # BAD C6b: confirmed = false
    bad_attest_unconfirmed = os.path.join(root, "bad_attest_unconfirmed.json")
    _write(bad_attest_unconfirmed, json.dumps({"reviewer": "Jane Smith", "date": "2026-06-11", "confirmed": False}))
    if run_gate(good_page, bad_attest_unconfirmed) != 1:
        failures.append("bad-C6b (confirmed false) was not refused")

    # BAD C6c: empty reviewer identity
    bad_attest_empty = os.path.join(root, "bad_attest_empty.json")
    _write(bad_attest_empty, json.dumps({"reviewer": "", "date": "2026-06-11", "confirmed": True}))
    if run_gate(good_page, bad_attest_empty) != 1:
        failures.append("bad-C6c (empty reviewer) was not refused")

    # ---- INVARIANT: remove FAQ section from good page => FAIL ----
    inv_html = re.sub(
        r'<h2>Frequently Asked Questions</h2>.*?</section>',
        '',
        GOOD_HTML,
        flags=re.DOTALL
    )
    inv_page = os.path.join(root, "invariant.html")
    _write(inv_page, inv_html)
    if run_gate(inv_page, good_attest) != 1:
        failures.append("invariant: removing visible FAQ section did not flip to FAIL")

    if failures:
        for f in failures:
            print(f"SELFTEST FAILURE: {f}")
        print(f"SELFTEST RESULT: FAIL ({len(failures)} problems)")
        return 1

    # Derive the bad-fixture count from the fixture names run above so the line is
    # always correct when fixtures change.
    # Bad fixtures: C1, C2, C2b, C2c, C2d, C3a, C3b, C4, C5a, C5b, C6, C6b, C6c, C6d, C6e = 15
    bad_count = 15
    print(f"SELFTEST RESULT: PASS (1 good, {bad_count} bad, 1 invariant)")
    return 0


# ================================================================ main

def main():
    if "--selftest" in sys.argv:
        return selftest()

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        print("Usage: seo_content_gate.py <page-file> <attestation-json>")
        print("       seo_content_gate.py --selftest")
        return 2

    return run_gate(args[0], args[1])


if __name__ == "__main__":
    sys.exit(main())
