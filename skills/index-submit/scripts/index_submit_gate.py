#!/usr/bin/env python3
"""index_submit_gate.py — fail-closed Google index-submission record validator.

Usage: python3 index_submit_gate.py <submission-record.json | dir-containing-submission-record.json>

Exit codes: 0 PASS, 1 FAIL, 2 load/usage error.

Checks:
  I1 RECORD-STRUCTURE    — parses as JSON; has a 'gsc' object, a 'sitemap' object, a
                           non-empty 'urls' list, and 'tool' + 'date' fields. Missing
                           any top-level key → FAIL.
  I2 GSC-VERIFIED        — gsc.property is a real https URL or domain (not placeholder/
                           TODO/empty), gsc.verified === true, and gsc.method is one of
                           {html-tag, html-file, dns-txt, google-analytics,
                           google-tag-manager}. Unverified/placeholder property → FAIL.
  I3 SITEMAP-VIA-SEARCH-CONSOLE — sitemap.url ends in sitemap.xml; sitemap.submitted
                           === true; sitemap.method is 'search-console' or
                           'sitemaps-api'. The sitemap.url host must belong to the
                           verified gsc.property host. Any deviation → FAIL.
  I4 NO-DEAD-MECHANISMS  — FAIL if the serialized record references the dead sitemap
                           ping endpoint (google.com/ping, /ping?sitemap, ping?sitemap=)
                           OR contains the substring 'indexnow' anywhere — IndexNow
                           does not belong in a Google submission record at all (it is
                           Bing/Yandex only); record any Bing submission separately.
  I5 URL-REQUESTS-RECORDED — every entry in 'urls' has a 'url' and a 'status' in the
                           done-set {indexing_requested, inspected, submitted, indexed}
                           and a 'method' field. Status 'planned'/'pending'/'todo' or
                           a missing status → FAIL. Also: urls must be non-empty. Each
                           url host must belong to the verified gsc.property host.
  I6 RECORD-IS-EXECUTED  — FAIL if the record declares itself unexecuted: a falsey
                           real_api_calls_made field, or submission_type of
                           plan/baseline/unaided_baseline/draft, or overall status of
                           planned/not_submitted.
"""

import json
import os
import sys
import tempfile

# ---------------------------------------------------------------- constants

GSC_METHODS = {"html-tag", "html-file", "dns-txt", "google-analytics", "google-tag-manager"}
URL_DONE_STATUSES = {"indexing_requested", "inspected", "submitted", "indexed"}
PLAN_SUBMISSION_TYPES = {"plan", "baseline", "unaided_baseline", "draft"}
PLAN_STATUSES = {"planned", "not_submitted"}
DEAD_PING_MARKERS = ("google.com/ping", "/ping?sitemap", "ping?sitemap=")
PLACEHOLDER_MARKERS = ("TODO", "PLACEHOLDER", "example.com", "yourdomain.com", "your-site.com")

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
    """Accept a path to submission-record.json directly, or a dir containing one."""
    if os.path.isdir(arg):
        return os.path.join(arg, "submission-record.json")
    return arg


def _property_host(gsc_property):
    """Derive the canonical host from a gsc.property value.

    sc-domain:example.com   -> "example.com"  (subdomains allowed)
    https://example.com     -> "example.com"
    https://example.com/    -> "example.com"
    Returns empty string if the property is malformed.
    """
    prop = str(gsc_property)
    if prop.startswith("sc-domain:"):
        return prop[len("sc-domain:"):].strip().rstrip("/").lower()
    # Strip scheme
    for scheme in ("https://", "http://"):
        if prop.startswith(scheme):
            host = prop[len(scheme):]
            # Drop path
            host = host.split("/")[0].lower()
            return host
    return ""


def _url_host(url):
    """Extract the host (no port, no path) from a URL string."""
    url = str(url)
    for scheme in ("https://", "http://"):
        if url.startswith(scheme):
            host = url[len(scheme):]
            host = host.split("/")[0].lower()
            # Drop port if present
            host = host.split(":")[0]
            return host
    return ""


def _host_matches_property(url_host, prop_host, is_sc_domain):
    """Return True if url_host belongs to the property host.

    For sc-domain: properties, subdomains are allowed (url_host ends with .prop_host
    or equals prop_host).
    For URL-prefix properties, url_host must equal prop_host exactly.
    """
    if not prop_host:
        return True  # can't check; let other checks fail it
    if is_sc_domain:
        return url_host == prop_host or url_host.endswith("." + prop_host)
    return url_host == prop_host


# ---------------------------------------------------------------- checks


def check_i1_record_structure(data, fail):
    """I1: required top-level keys present with correct shapes."""
    for key in ("gsc", "sitemap", "urls", "tool", "date"):
        if key not in data:
            fail(f"I1: required key '{key}' missing — "
                 "submission-record.json must have gsc, sitemap, urls, tool, date")
    if not isinstance(data.get("gsc"), dict):
        fail("I1: 'gsc' must be an object")
    if not isinstance(data.get("sitemap"), dict):
        fail("I1: 'sitemap' must be an object")
    if not isinstance(data.get("urls"), list) or len(data.get("urls", [])) == 0:
        fail("I1: 'urls' must be a non-empty list — "
             "per-URL indexing requests must be recorded")


def check_i2_gsc_verified(data, fail):
    """I2: GSC property is real, verified=true, method is a known verification type."""
    gsc = data.get("gsc")
    if not isinstance(gsc, dict):
        return  # I1 already caught this

    prop = gsc.get("property", "")
    if not prop:
        fail("I2: gsc.property is empty — "
             "provide the verified Search Console property URL or domain")
        return

    # Reject placeholders / TODO / empty
    prop_upper = str(prop).upper()
    if "TODO" in prop_upper or "PLACEHOLDER" in prop_upper:
        fail(f"I2: gsc.property = {prop!r} looks like a placeholder — "
             "provide the real verified property (https://... or sc-domain:...)")
        return

    # Must start with https:// or sc-domain: (domain property) or be a real URL
    if not (str(prop).startswith("https://") or str(prop).startswith("http://")
            or str(prop).startswith("sc-domain:")):
        fail(f"I2: gsc.property = {prop!r} is not a valid property URL — "
             "must start with https:// or sc-domain:")

    # verified must be true
    if gsc.get("verified") is not True:
        fail("I2: gsc.verified must be true — "
             "indexing without a verified GSC property is not a real submission")

    # method must be a known GSC verification method
    method = gsc.get("method", "")
    if method not in GSC_METHODS:
        fail(f"I2: gsc.method = {method!r} is not a known verification method — "
             f"must be one of {sorted(GSC_METHODS)}")


def check_i3_sitemap_via_search_console(data, fail):
    """I3: sitemap submitted through Search Console (not the dead ping endpoint)."""
    sitemap = data.get("sitemap")
    if not isinstance(sitemap, dict):
        return  # I1 already caught this

    url = sitemap.get("url", "")
    if not str(url).endswith("sitemap.xml"):
        fail(f"I3: sitemap.url = {url!r} does not end in 'sitemap.xml' — "
             "provide the full sitemap URL ending in sitemap.xml")

    if sitemap.get("submitted") is not True:
        fail("I3: sitemap.submitted must be true — "
             "sitemap must be submitted via Search Console, not just planned")

    method = sitemap.get("method", "")
    if method not in ("search-console", "sitemaps-api"):
        fail(f"I3: sitemap.method = {method!r} is not an accepted submission method — "
             "must be 'search-console' or 'sitemaps-api'; "
             "the ping endpoint was removed by Google")

    # Host-consistency: sitemap.url must belong to the verified gsc.property host
    gsc = data.get("gsc")
    if isinstance(gsc, dict):
        prop = gsc.get("property", "")
        is_sc_domain = str(prop).startswith("sc-domain:")
        prop_host = _property_host(prop)
        sitemap_host = _url_host(url)
        if sitemap_host and prop_host and not _host_matches_property(sitemap_host, prop_host, is_sc_domain):
            fail(f"I3: sitemap.url host '{sitemap_host}' does not belong to the "
                 f"verified property '{prop}' (expected host: '{prop_host}') — "
                 "you can only submit a sitemap for a domain you have verified in GSC")


def check_i4_no_dead_mechanisms(data, fail):
    """I4: no dead ping endpoint; no IndexNow anywhere in a Google submission record."""
    serialized = json.dumps(data).lower()

    # Dead ping endpoint
    for marker in DEAD_PING_MARKERS:
        if marker.lower() in serialized:
            fail(f"I4: record references the dead sitemap ping endpoint ('{marker}') — "
                 "Google removed the sitemaps ping endpoint; "
                 "submit sitemaps through Search Console only")
            break  # one message is enough; both markers would be the same root cause

    # IndexNow does not belong in a Google submission record at all.
    # It is a Bing/Yandex protocol — record any Bing submission in a separate Bing record.
    if "indexnow" in serialized:
        fail("I4: record contains 'indexnow' — IndexNow does not belong in a Google "
             "submission record (it is Bing/Yandex only); "
             "record any Bing submission in a separate Bing record")


def check_i5_url_requests_recorded(data, fail):
    """I5: every URL entry has a done-status and a method; urls non-empty; hosts match property."""
    urls = data.get("urls")
    if not isinstance(urls, list) or len(urls) == 0:
        fail("I5: 'urls' must be a non-empty list — "
             "per-URL indexing requests must be recorded")
        return

    # Derive property host once for host-consistency check
    gsc = data.get("gsc")
    prop_host = ""
    is_sc_domain = False
    if isinstance(gsc, dict):
        prop = gsc.get("property", "")
        is_sc_domain = str(prop).startswith("sc-domain:")
        prop_host = _property_host(prop)

    for i, entry in enumerate(urls):
        if not isinstance(entry, dict):
            fail(f"I5: urls[{i}] is not an object")
            continue

        url_val = entry.get("url")
        if not url_val:
            fail(f"I5: urls[{i}] missing 'url' field")
        else:
            # Host-consistency check
            url_host = _url_host(url_val)
            if url_host and prop_host and not _host_matches_property(url_host, prop_host, is_sc_domain):
                fail(f"I5: urls[{i}] url host '{url_host}' does not belong to the "
                     f"verified property (expected host: '{prop_host}') — "
                     "you can only request indexing for URLs on your verified property")

        status = entry.get("status", "")
        if not status:
            fail(f"I5: urls[{i}] missing 'status' field — "
                 "status must reflect a completed indexing request, not a plan")
        elif str(status).lower() not in URL_DONE_STATUSES:
            fail(f"I5: urls[{i}] status = {status!r} is not a completed status — "
                 f"must be one of {sorted(URL_DONE_STATUSES)}; "
                 "'planned'/'pending'/'todo' means the request was not made")

        method = entry.get("method")
        if not method:
            fail(f"I5: urls[{i}] missing 'method' field — "
                 "record how the indexing was requested (e.g. 'url-inspection')")


def check_i6_record_is_executed(data, fail):
    """I6: record must not declare itself unexecuted."""
    # real_api_calls_made must not be falsey if present
    if "real_api_calls_made" in data:
        if not data["real_api_calls_made"]:
            fail("I6: real_api_calls_made is false/null — "
                 "a plan serialized as JSON is not a submission record; "
                 "only record what was actually executed")

    # submission_type must not be a plan-tier value
    sub_type = str(data.get("submission_type", "")).lower()
    if sub_type in PLAN_SUBMISSION_TYPES:
        fail(f"I6: submission_type = {data.get('submission_type')!r} marks this as a plan — "
             "the record must reflect executed results, not intended actions; "
             "remove submission_type or set it to 'executed'")

    # overall status must not be unexecuted
    overall_status = str(data.get("status", "")).lower()
    if overall_status in PLAN_STATUSES:
        fail(f"I6: status = {data.get('status')!r} marks this record as not submitted — "
             "only write the record after the submission is complete")


# ---------------------------------------------------------------- gate


def run_gate(path):
    data, err = load_json(path)
    if err:
        print(f"LOAD ERROR: {err}")
        return 2
    msgs, fail = fail_msgs()
    check_i1_record_structure(data, fail)
    check_i2_gsc_verified(data, fail)
    check_i3_sitemap_via_search_console(data, fail)
    check_i4_no_dead_mechanisms(data, fail)
    check_i5_url_requests_recorded(data, fail)
    check_i6_record_is_executed(data, fail)
    if msgs:
        for m in msgs:
            print(f"FAIL {m}")
        print(f"INDEX SUBMIT GATE RESULT: FAIL ({len(msgs)} problems)")
        return 1
    print("INDEX SUBMIT GATE RESULT: PASS")
    return 0


# ---------------------------------------------------------------- selftest

GOOD = {
    "tool": "google-search-console",
    "date": "2026-06-12T14:00:00Z",
    "gsc": {
        "property": "https://timecard.quicktools.app",
        "verified": True,
        "method": "html-tag"
    },
    "sitemap": {
        "url": "https://timecard.quicktools.app/sitemap.xml",
        "submitted": True,
        "method": "search-console"
    },
    "urls": [
        {
            "url": "https://timecard.quicktools.app/",
            "status": "indexing_requested",
            "method": "url-inspection"
        },
        {
            "url": "https://timecard.quicktools.app/calculator",
            "status": "indexing_requested",
            "method": "url-inspection"
        }
    ]
}


def selftest():
    bad_cases = {
        # I1 failures
        "missing-gsc": lambda d: d.pop("gsc"),
        "missing-sitemap": lambda d: d.pop("sitemap"),
        "missing-urls": lambda d: d.pop("urls"),
        "missing-tool": lambda d: d.pop("tool"),
        # I2 failures
        "gsc-not-verified": lambda d: d["gsc"].update({"verified": False}),
        "gsc-placeholder-property": lambda d: d["gsc"].update({"property": "TODO"}),
        "gsc-bad-method": lambda d: d["gsc"].update({"method": "unknown-method"}),
        # I3 failures
        "sitemap-not-submitted": lambda d: d["sitemap"].update({"submitted": False}),
        "sitemap-via-ping-method": lambda d: d["sitemap"].update({"method": "ping-endpoint"}),
        "sitemap-url-wrong": lambda d: d["sitemap"].update({"url": "https://example.com/feed.xml"}),
        # I4 failures — dead ping endpoint
        "dead-ping-endpoint": lambda d: d.update(
            {"submission_notes": "curl https://www.google.com/ping?sitemap=https://timecard.quicktools.app/sitemap.xml"}
        ),
        # I4 failures — IndexNow as Google channel
        "indexnow-as-google-channel": lambda d: d.update(
            {"google_submission_steps": ["POST to api.indexnow.org for Google indexing"]}
        ),
        # I4 failures — IndexNow nested under a "notes" key (must still fail)
        "indexnow-under-notes-key": lambda d: d.update(
            {"notes": {"method": "indexnow", "endpoint": "api.indexnow.org"}}
        ),
        # I3 failures — host consistency
        "sitemap-wrong-domain": lambda d: d["sitemap"].update(
            {"url": "https://other-domain.com/sitemap.xml"}
        ),
        # I5 failures
        "url-status-planned": lambda d: d["urls"][0].update({"status": "planned"}),
        "url-missing-status": lambda d: d["urls"][0].pop("status"),
        "url-missing-method": lambda d: d["urls"][0].pop("method"),
        # I5 failures — host consistency
        "url-wrong-domain": lambda d: d["urls"][0].update(
            {"url": "https://other-domain.com/"}
        ),
        # I6 failures
        "real-api-calls-false": lambda d: d.update({"real_api_calls_made": False}),
        "submission-type-plan": lambda d: d.update({"submission_type": "unaided_baseline"}),
        "status-not-submitted": lambda d: d.update({"status": "not_submitted"}),
    }

    failures = []
    with tempfile.TemporaryDirectory() as root:
        # Good fixture must PASS
        good_path = os.path.join(root, "good.json")
        with open(good_path, "w", encoding="utf-8") as f:
            json.dump(GOOD, f)
        if run_gate(good_path) != 0:
            failures.append("golden-good fixture did not PASS")

        # Each bad case must be REFUSED (exit 1)
        for case, mutate in bad_cases.items():
            data = json.loads(json.dumps(GOOD))
            mutate(data)
            bad_path = os.path.join(root, f"bad-{case}.json")
            with open(bad_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            if run_gate(bad_path) != 1:
                failures.append(f"bad case '{case}' was not refused")

        # Invariant: gutting urls flips PASS -> FAIL
        data = json.loads(json.dumps(GOOD))
        data["urls"] = []
        inv_path = os.path.join(root, "invariant.json")
        with open(inv_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        if run_gate(inv_path) != 1:
            failures.append("invariant: gutting urls did not flip to FAIL")

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
