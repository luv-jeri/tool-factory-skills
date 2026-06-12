#!/usr/bin/env python3
"""adsense_gate.py — fail-closed AdSense monetization record validator.

Usage: python3 adsense_gate.py <monetization-record.json | dir-containing-monetization-record.json>

Exit codes: 0 PASS, 1 FAIL, 2 load/usage error.

Checks:
  M1 ELIGIBILITY-GATE     — If eligibility.hub_approved === true, skip age/users check
                            (tool joining an already-approved hub account). Otherwise:
                            eligibility.days_live >= 30 AND eligibility.daily_users >= 10
                            AND eligibility.legal_pages_present === true AND
                            eligibility.has_original_content === true. Premature application
                            (< 30 days or < 10 daily users) → FAIL.
  M2 ADS-TXT-FORMAT       — ads_txt.line must match exactly:
                            'google.com, pub-<16 digits>, DIRECT, f08c47fec0942fa0'
                            (case-insensitive on google.com/DIRECT, exact cert hash).
                            Must use pub- form (NOT ca-pub-). 16-digit pub id must be
                            real (not all-X / placeholder). ca-pub- in ads.txt → FAIL.
  M3 SCRIPT-CLIENT-MATCH  — adsense_script.client must be ca-pub-<16 digits>, real
                            (not placeholder), and its 16 digits MUST EQUAL the ads.txt
                            pub digits. Mismatch or placeholder → FAIL.
  M4 CMP-CERTIFIED        — cmp.enabled === true AND cmp.google_certified === true.
                            Missing or non-certified CMP → FAIL.
  M5 PRIVACY-DISCLOSES    — privacy.discloses_ad_cookies === true. False/missing → FAIL.
  M6 RECORD-REAL-EXECUTED — record has tool + date fields; FAIL if record declares
                            itself a plan/premature via submission_type/status of
                            plan/draft/premature, or real_setup_done: false marker.
"""

import json
import os
import re
import sys
import tempfile

# ---------------------------------------------------------------- constants

ADS_TXT_RE = re.compile(
    r"^google\.com,\s*pub-(\d{16}),\s*DIRECT,\s*f08c47fec0942fa0$",
    re.IGNORECASE,
)
CA_PUB_RE = re.compile(r"^ca-pub-(\d{16})$", re.IGNORECASE)
PLACEHOLDER_DIGITS = re.compile(r"^[Xx]{16}$")

PLAN_SUBMISSION_TYPES = {"plan", "draft", "premature", "unaided_baseline", "baseline"}
PLAN_STATUSES = {"plan", "draft", "premature", "not_executed", "pending"}

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
    """Accept a path to monetization-record.json directly, or a dir containing one."""
    if os.path.isdir(arg):
        return os.path.join(arg, "monetization-record.json")
    return arg


def _is_placeholder_id(digits):
    """Return True if the 16-digit string looks like a placeholder."""
    return bool(PLACEHOLDER_DIGITS.match(digits)) or digits == "0" * 16


# ---------------------------------------------------------------- checks


def check_m1_eligibility(data, fail):
    """M1: eligibility gate — premature application is the #1 rejection cause."""
    elig = data.get("eligibility")
    if not isinstance(elig, dict):
        fail("M1: required key 'eligibility' missing or not an object — "
             "provide eligibility object with hub_approved, days_live, daily_users, "
             "legal_pages_present, has_original_content")
        return

    hub_approved = elig.get("hub_approved")

    if hub_approved is True:
        # Tool joining an already-approved hub — skip age/users gate
        # M2-M5 still apply
        return

    # First/new application — enforce all eligibility requirements
    days_live = elig.get("days_live")
    if not isinstance(days_live, (int, float)) or days_live < 30:
        actual = days_live if days_live is not None else "missing"
        fail(f"M1: eligibility.days_live = {actual!r} — "
             "site must be live for at least 30 days before applying; "
             "a 0-day site will be rejected (the 6-month myth is false — "
             "the real threshold is ~30 days live with real traffic and content)")

    daily_users = elig.get("daily_users")
    if not isinstance(daily_users, (int, float)) or daily_users < 10:
        actual = daily_users if daily_users is not None else "missing"
        fail(f"M1: eligibility.daily_users = {actual!r} — "
             "site must have at least ~10 daily users before applying; "
             "a zero-traffic site will be rejected")

    if elig.get("legal_pages_present") is not True:
        fail("M1: eligibility.legal_pages_present must be true — "
             "AdSense requires a privacy policy and terms page before approval")

    if elig.get("has_original_content") is not True:
        fail("M1: eligibility.has_original_content must be true — "
             "AdSense requires original content; thin/duplicate content → rejection")


def check_m2_ads_txt_format(data, fail):
    """M2: ads.txt line must use pub- form (NOT ca-pub-), real 16-digit id."""
    ads_txt = data.get("ads_txt")
    if not isinstance(ads_txt, dict):
        fail("M2: required key 'ads_txt' missing or not an object — "
             "provide ads_txt.line with the exact AdSense ads.txt line")
        return

    line = str(ads_txt.get("line", "")).strip()
    if not line:
        fail("M2: ads_txt.line is empty — "
             "provide the full ads.txt line: "
             "'google.com, pub-<16 digits>, DIRECT, f08c47fec0942fa0'")
        return

    # Reject ca-pub- form in ads.txt — this is the documented baseline bug
    if re.search(r"\bca-pub-", line, re.IGNORECASE):
        fail(f"M2: ads_txt.line uses 'ca-pub-' form: {line!r} — "
             "ads.txt must use the 'pub-<16 digits>' form (without 'ca-'), "
             "not the script ca-pub- form; this is the malformed-line baseline failure")
        return

    m = ADS_TXT_RE.match(line)
    if not m:
        fail(f"M2: ads_txt.line {line!r} does not match required format — "
             "must be exactly: 'google.com, pub-<16 digits>, DIRECT, f08c47fec0942fa0' "
             "(case-insensitive on google.com/DIRECT, exact cert hash)")
        return

    pub_digits = m.group(1)
    if _is_placeholder_id(pub_digits):
        fail(f"M2: ads_txt.line contains placeholder pub id '{pub_digits}' — "
             "use your real 16-digit publisher id, not a placeholder")


def check_m3_script_client_match(data, fail):
    """M3: adsense_script.client must be ca-pub-<16 digits> matching ads.txt pub digits."""
    script = data.get("adsense_script")
    if not isinstance(script, dict):
        fail("M3: required key 'adsense_script' missing or not an object — "
             "provide adsense_script.client with ca-pub-<16 digits>")
        return

    client = str(script.get("client", "")).strip()
    if not client:
        fail("M3: adsense_script.client is empty — "
             "provide the ca-pub-<16 digits> publisher id used in the AdSense script tag")
        return

    m = CA_PUB_RE.match(client)
    if not m:
        fail(f"M3: adsense_script.client = {client!r} does not match ca-pub-<16 digits> — "
             "the AdSense script loader uses the 'ca-pub-' form; "
             "ads.txt uses 'pub-' — they are the same account, different forms")
        return

    script_digits = m.group(1)
    if _is_placeholder_id(script_digits):
        fail(f"M3: adsense_script.client contains placeholder id '{script_digits}' — "
             "use your real 16-digit publisher id, not a placeholder")
        return

    # Cross-check: script digits must match ads.txt pub digits
    ads_txt = data.get("ads_txt")
    if isinstance(ads_txt, dict):
        ads_line = str(ads_txt.get("line", "")).strip()
        ads_m = ADS_TXT_RE.match(ads_line)
        if ads_m:
            ads_digits = ads_m.group(1)
            if script_digits != ads_digits:
                fail(f"M3: adsense_script.client digits '{script_digits}' do not match "
                     f"ads_txt.line pub digits '{ads_digits}' — "
                     "both must use the same 16-digit publisher id; "
                     "a mismatch means your ad code and ads.txt point to different accounts")


def check_m4_cmp_certified(data, fail):
    """M4: Google-certified CMP required for EEA/UK consent (since 2024-01-16)."""
    cmp = data.get("cmp")
    if not isinstance(cmp, dict):
        fail("M4: required key 'cmp' missing or not an object — "
             "Google requires a certified CMP to serve ads to EEA/UK users "
             "(required since 2024-01-16); provide cmp.enabled and cmp.google_certified")
        return

    if cmp.get("enabled") is not True:
        fail("M4: cmp.enabled must be true — "
             "a CMP must be actively deployed on the site; "
             "AdSense without a CMP cannot serve personalized ads in EEA/UK (post-2024)")

    if cmp.get("google_certified") is not True:
        fail("M4: cmp.google_certified must be true — "
             "only a Google-certified CMP (from the official certified list) satisfies "
             "the GDPR consent requirement for AdSense; "
             "the baseline set up no CMP at all and the agent admitted 'I did not consider CMP compliance'")


def check_m5_privacy_discloses(data, fail):
    """M5: privacy policy must disclose third-party advertising cookies."""
    privacy = data.get("privacy")
    if not isinstance(privacy, dict):
        fail("M5: required key 'privacy' missing or not an object — "
             "provide privacy.discloses_ad_cookies = true; "
             "AdSense program policy requires the privacy policy to disclose "
             "third-party advertising cookies")
        return

    if privacy.get("discloses_ad_cookies") is not True:
        fail("M5: privacy.discloses_ad_cookies must be true — "
             "AdSense program policy requires the privacy policy to disclose "
             "that third-party ad cookies are used (e.g. by Google AdSense)")


def check_m6_record_real_executed(data, fail):
    """M6: record must have tool + date and must not declare itself a plan."""
    if not data.get("tool"):
        fail("M6: required key 'tool' missing — "
             "record what tool/step produced this monetization record")

    if not data.get("date"):
        fail("M6: required key 'date' missing — "
             "record the ISO 8601 date this was executed")

    # Reject real_setup_done: false
    if "real_setup_done" in data and not data["real_setup_done"]:
        fail("M6: real_setup_done is false — "
             "a plan serialized as JSON is not an executed monetization record; "
             "only write the record after the setup is complete")

    # Reject plan-tier submission_type
    sub_type = str(data.get("submission_type", "")).lower()
    if sub_type in PLAN_SUBMISSION_TYPES:
        fail(f"M6: submission_type = {data.get('submission_type')!r} marks this as a plan — "
             "remove submission_type or set it to 'executed'; "
             "the baseline wrote a plan-as-record with status 'premature'")

    # Reject plan-tier status
    overall_status = str(data.get("status", "")).lower()
    if overall_status in PLAN_STATUSES:
        fail(f"M6: status = {data.get('status')!r} marks this record as not executed — "
             "only write the record after monetization setup is complete")


# ---------------------------------------------------------------- gate


def run_gate(path):
    data, err = load_json(path)
    if err:
        print(f"LOAD ERROR: {err}")
        return 2
    msgs, fail = fail_msgs()
    check_m1_eligibility(data, fail)
    check_m2_ads_txt_format(data, fail)
    check_m3_script_client_match(data, fail)
    check_m4_cmp_certified(data, fail)
    check_m5_privacy_discloses(data, fail)
    check_m6_record_real_executed(data, fail)
    if msgs:
        for m in msgs:
            print(f"FAIL {m}")
        print(f"ADSENSE GATE RESULT: FAIL ({len(msgs)} problems)")
        return 1
    print("ADSENSE GATE RESULT: PASS")
    return 0


# ---------------------------------------------------------------- selftest

GOOD = {
    "tool": "adsense-setup",
    "date": "2026-06-12T12:00:00Z",
    "eligibility": {
        "hub_approved": False,
        "days_live": 45,
        "daily_users": 30,
        "legal_pages_present": True,
        "has_original_content": True
    },
    "ads_txt": {
        "line": "google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0"
    },
    "adsense_script": {
        "client": "ca-pub-1234567890123456"
    },
    "cmp": {
        "enabled": True,
        "google_certified": True
    },
    "privacy": {
        "discloses_ad_cookies": True
    }
}

# Hub-approved variant: days_live=0 should PASS because hub_approved=true skips M1 age gate
GOOD_HUB_APPROVED = {
    "tool": "adsense-setup",
    "date": "2026-06-12T12:00:00Z",
    "eligibility": {
        "hub_approved": True,
        "days_live": 0,
        "daily_users": 0,
        "legal_pages_present": True,
        "has_original_content": True
    },
    "ads_txt": {
        "line": "google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0"
    },
    "adsense_script": {
        "client": "ca-pub-1234567890123456"
    },
    "cmp": {
        "enabled": True,
        "google_certified": True
    },
    "privacy": {
        "discloses_ad_cookies": True
    }
}


def selftest():
    bad_cases = {
        # M1 failures
        "premature-application": lambda d: d["eligibility"].update(
            {"days_live": 0, "daily_users": 0, "hub_approved": False}
        ),
        "days-live-too-low": lambda d: d["eligibility"].update({"days_live": 5}),
        "daily-users-too-low": lambda d: d["eligibility"].update({"daily_users": 2}),
        "no-legal-pages": lambda d: d["eligibility"].update({"legal_pages_present": False}),
        "no-original-content": lambda d: d["eligibility"].update(
            {"has_original_content": False}
        ),
        # M2 failures
        "ads-txt-ca-pub-form": lambda d: d["ads_txt"].update(
            {"line": "google.com, ca-pub-1234567890123456, DIRECT, f08c47fec0942fa0"}
        ),
        "ads-txt-placeholder-id": lambda d: d["ads_txt"].update(
            {"line": "google.com, pub-XXXXXXXXXXXXXXXX, DIRECT, f08c47fec0942fa0"}
        ),
        "ads-txt-wrong-cert-hash": lambda d: d["ads_txt"].update(
            {"line": "google.com, pub-1234567890123456, DIRECT, 0000000000000000"}
        ),
        # M3 failures
        "script-client-placeholder": lambda d: d["adsense_script"].update(
            {"client": "ca-pub-XXXXXXXXXXXXXXXX"}
        ),
        "script-client-mismatch": lambda d: d["adsense_script"].update(
            {"client": "ca-pub-9999999999999999"}
        ),
        "script-client-wrong-form": lambda d: d["adsense_script"].update(
            {"client": "pub-1234567890123456"}
        ),
        # M4 failures
        "no-cmp": lambda d: d.pop("cmp"),
        "cmp-not-enabled": lambda d: d["cmp"].update({"enabled": False}),
        "cmp-not-google-certified": lambda d: d["cmp"].update(
            {"google_certified": False}
        ),
        # M5 failures
        "privacy-no-disclosure": lambda d: d["privacy"].update(
            {"discloses_ad_cookies": False}
        ),
        # M6 failures
        "plan-as-record": lambda d: d.update(
            {"submission_type": "premature", "real_setup_done": False}
        ),
        "status-draft": lambda d: d.update({"status": "draft"}),
    }

    failures = []
    with tempfile.TemporaryDirectory() as root:
        # Good fixture must PASS
        good_path = os.path.join(root, "good.json")
        with open(good_path, "w", encoding="utf-8") as f:
            json.dump(GOOD, f)
        if run_gate(good_path) != 0:
            failures.append("golden-good fixture did not PASS")

        # Hub-approved variant must PASS (days_live=0 skipped when hub_approved=true)
        hub_path = os.path.join(root, "good-hub-approved.json")
        with open(hub_path, "w", encoding="utf-8") as f:
            json.dump(GOOD_HUB_APPROVED, f)
        if run_gate(hub_path) != 0:
            failures.append("hub-approved good fixture did not PASS (age gate should be skipped)")

        # Each bad case must be REFUSED (exit 1)
        for case, mutate in bad_cases.items():
            data = json.loads(json.dumps(GOOD))
            mutate(data)
            bad_path = os.path.join(root, f"bad-{case}.json")
            with open(bad_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            if run_gate(bad_path) != 1:
                failures.append(f"bad case '{case}' was not refused")

        # Invariant: gutting eligibility flips PASS -> FAIL
        data = json.loads(json.dumps(GOOD))
        data.pop("eligibility")
        inv_path = os.path.join(root, "invariant.json")
        with open(inv_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        if run_gate(inv_path) != 1:
            failures.append("invariant: removing eligibility did not flip to FAIL")

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
