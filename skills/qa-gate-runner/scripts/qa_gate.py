#!/usr/bin/env python3
"""qa_gate.py — fail-closed pre-launch QA report validator for static micro-tool sites.

Usage: python3 qa_gate.py <qa-report.json | dir-containing-qa-report.json>

Exit codes: 0 PASS, 1 FAIL, 2 load/usage error.

Checks:
  Q1 REPORT-COMPLETE    — report parses as JSON; non-empty pages list; each page has
                          lighthouse (all 4 numeric scores 0-100), cwv, console_errors
                          list, and schema object. A missing/null Performance score is
                          a FAIL even if the tool said it was excluded.
  Q2 LIGHTHOUSE-THRESHOLD — every page's 4 Lighthouse scores (performance, accessibility,
                          best_practices, seo) are >= 95. Any < 95 → FAIL naming page +
                          category + score.
  Q3 CWV-GREEN          — each page's cwv has lcp_ms <= 2500, cls <= 0.1, inp_ms <= 200,
                          all present as numbers. Missing or breaching → FAIL.
  Q4 ZERO-CONSOLE-ERRORS — each page's console_errors list is empty. Non-empty → FAIL
                          listing the errors.
  Q5 SCHEMA-ALLOWED-ONLY — each page's schema.types is a subset of
                          {SoftwareApplication, BreadcrumbList}; FAQPage or HowTo
                          anywhere → FAIL (dead/banned rich-result types). schema.valid
                          must be true.
  Q6 REPORT-IS-REAL     — report has tool (string) and date/timestamp fields; page set
                          has >= 1 page with a url. Refuses prose markdown, fabricated
                          stubs, or partial fixtures.
"""

import json
import os
import sys
import tempfile

# ---------------------------------------------------------------- allowed schema types

ALLOWED_SCHEMA_TYPES = {"SoftwareApplication", "BreadcrumbList"}
BANNED_SCHEMA_TYPES = {"FAQPage", "HowTo"}

# ---------------------------------------------------------------- helpers


def fail_msgs():
    msgs = []
    return msgs, lambda m: msgs.append(m)


def load_json(path):
    """Return (data, None) or (None, error string). Fail-closed on anything odd."""
    if not os.path.isfile(path):
        return None, f"{path} does not exist"
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f), None
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return None, f"{path} does not parse as JSON: {e}"


def resolve_path(arg):
    """Accept a path to qa-report.json directly, or a dir containing one."""
    if os.path.isdir(arg):
        candidate = os.path.join(arg, "qa-report.json")
        return candidate
    return arg


# ---------------------------------------------------------------- checks


def check_q1_report_complete(data, fail):
    """Q1: report has a non-empty pages list; each page has all required sections
    including all 4 lighthouse scores as numbers 0-100."""
    pages = data.get("pages")
    if not isinstance(pages, list) or len(pages) == 0:
        fail("Q1: 'pages' must be a non-empty list — a partial QA run is not a QA run")
        return

    required_lh_categories = ("performance", "accessibility", "best_practices", "seo")

    for i, page in enumerate(pages):
        if not isinstance(page, dict):
            fail(f"Q1: pages[{i}] is not an object")
            continue

        # lighthouse block
        lh = page.get("lighthouse")
        if not isinstance(lh, dict):
            fail(f"Q1: pages[{i}] missing 'lighthouse' object — "
                 "run a full Lighthouse pass including Performance")
            continue

        for cat in required_lh_categories:
            score = lh.get(cat)
            if score is None:
                fail(f"Q1: pages[{i}] lighthouse.{cat} is absent — "
                     "excluded or null categories are not acceptable; "
                     "run a Lighthouse pass that includes Performance")
            elif not isinstance(score, (int, float)) or not (0 <= score <= 100):
                fail(f"Q1: pages[{i}] lighthouse.{cat} = {score!r} is not a "
                     "number in 0-100")

        # cwv block
        if not isinstance(page.get("cwv"), dict):
            fail(f"Q1: pages[{i}] missing 'cwv' object — "
                 "Core Web Vitals must be measured and present")

        # console_errors list
        if not isinstance(page.get("console_errors"), list):
            fail(f"Q1: pages[{i}] missing 'console_errors' list")

        # schema object
        if not isinstance(page.get("schema"), dict):
            fail(f"Q1: pages[{i}] missing 'schema' object")


def check_q2_lighthouse_threshold(data, fail):
    """Q2: every page's 4 Lighthouse scores >= 95."""
    pages = data.get("pages", [])
    for i, page in enumerate(pages):
        if not isinstance(page, dict):
            continue
        lh = page.get("lighthouse")
        if not isinstance(lh, dict):
            continue
        url = page.get("url", f"pages[{i}]")
        for cat in ("performance", "accessibility", "best_practices", "seo"):
            score = lh.get(cat)
            if isinstance(score, (int, float)) and score < 95:
                fail(f"Q2: {url} lighthouse.{cat} = {score} (< 95 threshold) — "
                     "all four Lighthouse categories must score >= 95")


def check_q3_cwv_green(data, fail):
    """Q3: lcp_ms <= 2500, cls <= 0.1, inp_ms <= 200; all present as numbers."""
    pages = data.get("pages", [])
    thresholds = {
        "lcp_ms": 2500,
        "cls": 0.1,
        "inp_ms": 200,
    }
    for i, page in enumerate(pages):
        if not isinstance(page, dict):
            continue
        cwv = page.get("cwv")
        if not isinstance(cwv, dict):
            continue
        url = page.get("url", f"pages[{i}]")
        for metric, limit in thresholds.items():
            val = cwv.get(metric)
            if val is None:
                fail(f"Q3: {url} cwv.{metric} is absent — "
                     "Core Web Vitals must be measured; 'not captured' is a FAIL")
            elif not isinstance(val, (int, float)):
                fail(f"Q3: {url} cwv.{metric} = {val!r} is not a number")
            elif val > limit:
                fail(f"Q3: {url} cwv.{metric} = {val} (> {limit} green threshold) — "
                     "CWV must be in the green range before launch")


def check_q4_zero_console_errors(data, fail):
    """Q4: each page's console_errors list is empty."""
    pages = data.get("pages", [])
    for i, page in enumerate(pages):
        if not isinstance(page, dict):
            continue
        errors = page.get("console_errors")
        if not isinstance(errors, list):
            continue
        url = page.get("url", f"pages[{i}]")
        if len(errors) > 0:
            listed = "; ".join(str(e) for e in errors[:5])
            suffix = f" (and {len(errors) - 5} more)" if len(errors) > 5 else ""
            fail(f"Q4: {url} has {len(errors)} console error(s): {listed}{suffix} — "
                 "all console errors must be resolved before launch")


def check_q5_schema_allowed_only(data, fail):
    """Q5: schema.types subset of {SoftwareApplication, BreadcrumbList};
    FAQPage/HowTo anywhere → FAIL; schema.valid must be true."""
    pages = data.get("pages", [])
    for i, page in enumerate(pages):
        if not isinstance(page, dict):
            continue
        schema = page.get("schema")
        if not isinstance(schema, dict):
            continue
        url = page.get("url", f"pages[{i}]")

        types = schema.get("types", [])
        if not isinstance(types, list):
            fail(f"Q5: {url} schema.types is not a list")
            continue

        banned_found = [t for t in types if t in BANNED_SCHEMA_TYPES]
        if banned_found:
            fail(f"Q5: {url} schema.types contains banned type(s) {banned_found} — "
                 "FAQPage ended May 2026 and HowTo ended Sept 2023 as rich-result "
                 "types; remove them")

        disallowed = [t for t in types if t not in ALLOWED_SCHEMA_TYPES]
        if disallowed:
            fail(f"Q5: {url} schema.types contains disallowed type(s) {disallowed} — "
                 "only {SoftwareApplication, BreadcrumbList} are allowed")

        valid = schema.get("valid")
        if valid is not True:
            fail(f"Q5: {url} schema.valid = {valid!r} (must be true) — "
                 "fix schema validation errors before launch")


def check_q6_report_is_real(data, fail):
    """Q6: report has tool (string) and date/timestamp; at least 1 page with a url.
    Refuses prose markdown reports and fabricated stubs."""
    tool = data.get("tool")
    if not isinstance(tool, str) or not tool.strip():
        fail("Q6: report missing 'tool' field (e.g. 'lighthouse') — "
             "a prose QA_REPORT.md or fabricated stub is not a gate-able artifact")

    date = data.get("date") or data.get("timestamp")
    if not date or not isinstance(date, str) or not date.strip():
        fail("Q6: report missing 'date' or 'timestamp' field — "
             "include the ISO datetime the Lighthouse run completed")

    pages = data.get("pages", [])
    urls = [p.get("url") for p in pages if isinstance(p, dict) and p.get("url")]
    if len(urls) == 0:
        fail("Q6: no page has a 'url' field — "
             "a non-trivial QA run must report at least one page URL")


# ---------------------------------------------------------------- gate


def run_gate(path):
    data, err = load_json(path)
    if err:
        print(f"LOAD ERROR: {err}")
        return 2

    msgs, fail = fail_msgs()
    check_q1_report_complete(data, fail)
    check_q2_lighthouse_threshold(data, fail)
    check_q3_cwv_green(data, fail)
    check_q4_zero_console_errors(data, fail)
    check_q5_schema_allowed_only(data, fail)
    check_q6_report_is_real(data, fail)

    if msgs:
        for m in msgs:
            print(f"FAIL {m}")
        print(f"QA GATE RESULT: FAIL ({len(msgs)} problems)")
        return 1

    print("QA GATE RESULT: PASS")
    return 0


# ---------------------------------------------------------------- selftest

GOOD = {
    "tool": "lighthouse",
    "date": "2026-06-12T10:00:00Z",
    "pages": [
        {
            "url": "https://example.com/",
            "lighthouse": {
                "performance": 97,
                "accessibility": 100,
                "best_practices": 100,
                "seo": 98,
            },
            "cwv": {"lcp_ms": 1200, "cls": 0.02, "inp_ms": 80},
            "console_errors": [],
            "schema": {"types": ["SoftwareApplication"], "valid": True},
        },
        {
            "url": "https://example.com/calculator",
            "lighthouse": {
                "performance": 96,
                "accessibility": 99,
                "best_practices": 100,
                "seo": 100,
            },
            "cwv": {"lcp_ms": 900, "cls": 0.0, "inp_ms": 120},
            "console_errors": [],
            "schema": {"types": ["SoftwareApplication", "BreadcrumbList"], "valid": True},
        },
    ],
}


def _mutate(source, mutate_fn):
    """Deep-copy GOOD and apply mutate_fn."""
    import copy
    d = copy.deepcopy(source)
    mutate_fn(d)
    return d


def selftest():
    bad_cases = {
        # Q1: performance score absent (the headline baseline failure)
        "q1-performance-absent": lambda d: d["pages"][0]["lighthouse"].pop("performance"),
        # Q1: pages list is empty
        "q1-empty-pages": lambda d: d.update(pages=[]),
        # Q1: cwv object missing
        "q1-cwv-missing": lambda d: d["pages"][0].pop("cwv"),
        # Q1: console_errors list missing
        "q1-console-errors-missing": lambda d: d["pages"][0].pop("console_errors"),
        # Q2: accessibility score below threshold (91 — exactly what the baseline got)
        "q2-accessibility-below-threshold": lambda d: d["pages"][0]["lighthouse"].update(
            accessibility=91
        ),
        # Q3: lcp_ms over threshold (CWV not captured in baseline)
        "q3-lcp-over-threshold": lambda d: d["pages"][0]["cwv"].update(lcp_ms=3000),
        # Q3: inp_ms absent
        "q3-inp-absent": lambda d: d["pages"][0]["cwv"].pop("inp_ms"),
        # Q4: console errors present
        "q4-console-errors-present": lambda d: d["pages"][0].update(
            console_errors=["Uncaught ReferenceError: foo is not defined"]
        ),
        # Q5: FAQPage in schema types (banned since May 2026)
        "q5-faqpage-banned": lambda d: d["pages"][0]["schema"].update(
            types=["SoftwareApplication", "FAQPage"]
        ),
        # Q5: HowTo in schema types (banned since Sept 2023)
        "q5-howto-banned": lambda d: d["pages"][0]["schema"].update(
            types=["HowTo"]
        ),
        # Q6: tool field absent (prose report or fabricated stub)
        "q6-tool-missing": lambda d: d.pop("tool"),
        # Q6: date field absent
        "q6-date-missing": lambda d: d.pop("date"),
    }

    failures = []
    with tempfile.TemporaryDirectory() as root:
        # 1 good fixture
        good_path = os.path.join(root, "good.json")
        with open(good_path, "w", encoding="utf-8") as f:
            json.dump(GOOD, f)
        if run_gate(good_path) != 0:
            failures.append("golden-good fixture did not PASS")

        # bad fixtures — one mutation per check failure mode
        for case, mutate_fn in bad_cases.items():
            data = _mutate(GOOD, mutate_fn)
            bad_path = os.path.join(root, f"bad-{case}.json")
            with open(bad_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            if run_gate(bad_path) != 1:
                failures.append(f"bad case '{case}' was not refused")

        # invariant: remove all pages — PASS must flip to FAIL
        data = _mutate(GOOD, lambda d: d.update(pages=[]))
        inv_path = os.path.join(root, "invariant.json")
        with open(inv_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        if run_gate(inv_path) != 1:
            failures.append("invariant: empty pages did not flip to FAIL")

    print()
    if failures:
        for f in failures:
            print(f"SELFTEST FAILURE: {f}")
        print(f"SELFTEST RESULT: FAIL ({len(failures)} problems)")
        return 1

    print(f"SELFTEST RESULT: PASS (1 good, {len(bad_cases)} bad, 1 invariant)")
    return 0


def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        return selftest()
    if len(args) != 1:
        print(__doc__)
        return 2
    path = resolve_path(args[0])
    return run_gate(path)


if __name__ == "__main__":
    sys.exit(main())
