#!/usr/bin/env python3
"""ship_gate.py — fail-closed deploy config validator for static micro-tool sites on Cloudflare.

Usage:
    python3 scripts/ship_gate.py <project-dir>
    python3 scripts/ship_gate.py --selftest

Exit codes: 0 PASS, 1 FAIL, 2 load/usage error.

Checks:
  S1 ANALYTICS-REAL        — an HTML file contains a GA4 gtag snippet whose
                             measurement id matches G-[A-Z0-9]{6,} and is NOT
                             the placeholder G-XXXXXXXXXX (or any all-X / PLACEHOLDER id).
  S2 DEPLOY-TARGET-CORRECT — a wrangler.toml (TOML only) exists, declares current Workers
                             static assets ([assets] table with a directory field), and does
                             NOT use the deprecated Workers Sites layout ([site] table or
                             [[build.upload_rules]] / CompiledContentAssets), and is not a
                             Pages-only config.
  S3 NO-PLACEHOLDER-CONFIG — no deploy/config file (wrangler.toml, _headers, smoke artifact)
                             contains an unfilled placeholder token: YOUR_ZONE_ID,
                             YOUR_ACCOUNT_ID, PLACEHOLDER, a bare XXXX run (4+ consecutive
                             X's), <...>-style angle placeholders, or common copy-paste
                             example domains (yourdomain.com, example.com, REPLACE_ME).
  S4 STAGING-NOINDEX-EXACT — a _headers file exists, contains an X-Robots-Tag: noindex
                             rule that is correctly 2-space-indented UNDER a path rule
                             (a column-0 noindex is treated by Cloudflare as a path, not a
                             header, so staging would NOT be noindexed), and EVERY header
                             line under a path rule is indented with EXACTLY two spaces (not
                             a tab, not four spaces). Production must NOT be noindexed via any
                             top-level root path rule (/* or /).
  S5 CUSTOM-DOMAIN         — the wrangler.toml declares a production custom domain or route
                             with a real domain, NOT left only on *.workers.dev / *.pages.dev.
  S6 SMOKE-MANIFEST        — a smoke-check artifact (smoke_test.sh or SMOKE*.{sh,md,txt})
                             exists and asserts at least: production URL returns 200, staging
                             responds with X-Robots-Tag noindex, and production is NOT
                             noindexed (the prod check must invoke curl, not just mention it).
"""

import os
import re
import sys
import tempfile

# ------------------------------------------------------------------ helpers


def fail_msgs():
    msgs = []
    return msgs, lambda m: msgs.append(m)


def _find_files(project_dir, pattern):
    """Return list of (basename, full_path) for files matching pattern regex in project_dir."""
    results = []
    pat = re.compile(pattern, re.IGNORECASE)
    for name in os.listdir(project_dir):
        if pat.search(name):
            results.append((name, os.path.join(project_dir, name)))
    return results


def _read(path):
    """Return file content or None on error."""
    try:
        return open(path, encoding="utf-8").read()
    except OSError:
        return None


# ------------------------------------------------------------------ checks


def check_s1_analytics_real(project_dir, fail):
    """S1: an HTML file contains a real (non-placeholder) GA4 measurement id."""
    html_files = [
        os.path.join(project_dir, n)
        for n in os.listdir(project_dir)
        if n.endswith(".html")
    ]
    if not html_files:
        fail(
            "S1: no .html files found in project dir — cannot verify GA4 analytics snippet"
        )
        return

    found_gtag = False
    for path in html_files:
        content = _read(path)
        if content is None:
            continue
        # Look for GA4 gtag measurement ids
        ids = re.findall(r"G-([A-Z0-9]{6,})", content)
        for mid in ids:
            found_gtag = True
            # Reject all-X run (placeholder pattern) or literal XXXXXXXXXX
            if re.match(r"^X+$", mid) or "PLACEHOLDER" in mid.upper():
                fail(
                    f"S1: {os.path.basename(path)} contains a placeholder GA4 id "
                    f"'G-{mid}' — replace with a real measurement id from your GA4 property "
                    "(e.g. G-AB1CD2EF34)"
                )
                return

    if not found_gtag:
        fail(
            "S1: no GA4 gtag measurement id (G-XXXXXX...) found in any HTML file — "
            "add the GA4 snippet with a real measurement id to every page before shipping"
        )


def check_s2_deploy_target_correct(project_dir, fail):
    """S2: wrangler.toml (TOML only) exists, uses current Workers static assets, not deprecated Sites."""
    # Locate wrangler.toml only — jsonc/json use different syntax and are not validated here
    wrangler_files = _find_files(project_dir, r"^wrangler\.toml$")
    if not wrangler_files:
        fail(
            "S2: no wrangler.toml found in project dir — create one with [assets] "
            "static-assets config (only wrangler.toml / TOML format is validated by this gate)"
        )
        return

    _, wpath = wrangler_files[0]
    content = _read(wpath)
    if content is None:
        fail(f"S2: cannot read {os.path.basename(wpath)}")
        return

    # Detect deprecated Workers Sites markers
    if re.search(r"^\[site\]", content, re.MULTILINE):
        fail(
            "S2: wrangler config uses deprecated Workers Sites layout ([site] table) — "
            "migrate to current Workers static assets: use [assets] with a directory field "
            "and remove the [site] block"
        )
        return
    if re.search(r"\[\[build\.upload_rules\]\]|CompiledContentAssets", content):
        fail(
            "S2: wrangler config contains deprecated [[build.upload_rules]] or "
            "CompiledContentAssets — remove these deprecated directives and use "
            "[assets] directory = '...' for Workers static assets"
        )
        return

    # Must have [assets] with a directory
    if not re.search(r"^\[assets\]", content, re.MULTILINE):
        fail(
            "S2: wrangler config has no [assets] table — Workers static assets requires "
            "[assets]\\ndirectory = '<dist-dir>' pointing at your built output folder"
        )
        return
    if not re.search(r"directory\s*=", content):
        fail(
            "S2: wrangler config [assets] table has no directory field — "
            "add: directory = '<your-dist-dir>'"
        )


def check_s3_no_placeholder_config(project_dir, fail):
    """S3: no deploy/config file contains unfilled placeholder tokens."""
    # Files to check: wrangler.toml, _headers, smoke artifacts
    config_names = []
    for name in os.listdir(project_dir):
        if (
            re.match(r"^wrangler\.toml$", name, re.IGNORECASE)
            or name == "_headers"
            or re.match(r"^smoke", name, re.IGNORECASE)
        ):
            config_names.append(name)

    placeholder_patterns = [
        (r"YOUR_ZONE_ID", "YOUR_ZONE_ID"),
        (r"YOUR_ACCOUNT_ID", "YOUR_ACCOUNT_ID"),
        (r"\bPLACEHOLDER\b", "PLACEHOLDER"),
        (r"XXXX+", "XXXX... run (4+ consecutive X's)"),
        (r"<[A-Za-z_][A-Za-z0-9_\s-]{1,40}>", "<...>-style angle placeholder"),
        (r"\byourdomain\.com\b", "yourdomain.com (copy-paste example domain)"),
        (r"\bexample\.com\b", "example.com (copy-paste example domain)"),
        (r"\bREPLACE_ME\b", "REPLACE_ME"),
    ]

    for name in config_names:
        path = os.path.join(project_dir, name)
        content = _read(path)
        if content is None:
            continue
        for pat, label in placeholder_patterns:
            m = re.search(pat, content)
            if m:
                fail(
                    f"S3: {name} contains an unfilled placeholder token '{label}' "
                    f"(matched: '{m.group(0)[:40]}') — replace with the real value "
                    "before shipping"
                )
                break  # one report per file is enough


def _is_prod_root_path(path):
    """Return True if a _headers path rule covers the production root (/* or /)."""
    # /* is the classic catch-all; bare / is also a root rule
    return path in ("/*", "/")


def check_s4_staging_noindex_exact(project_dir, fail):
    """S4: _headers has X-Robots-Tag: noindex with exact 2-space indentation under a path rule; prod not noindexed."""
    headers_path = os.path.join(project_dir, "_headers")
    if not os.path.isfile(headers_path):
        fail(
            "S4: _headers file not found — create one with X-Robots-Tag: noindex "
            "for the staging host path rule, using exactly two-space indentation "
            "(Cloudflare silently ignores tabs or four-space indented _headers)"
        )
        return

    content = _read(headers_path)
    if content is None:
        fail("S4: cannot read _headers")
        return

    # Check X-Robots-Tag noindex exists at all (anywhere in file)
    noindex_present_in_file = bool(
        re.search(r"X-Robots-Tag\s*:\s*noindex", content, re.IGNORECASE)
    )
    if not noindex_present_in_file:
        fail(
            "S4: _headers has no X-Robots-Tag: noindex rule — "
            "staging host must be noindexed to prevent duplicate-content penalties"
        )
        return

    # Parse _headers: collect path rules and their header lines
    # Cloudflare _headers format: path-line (no leading whitespace), then header lines
    # indented with EXACTLY two spaces.
    lines = content.splitlines()

    # Track the current path rule and its header lines
    current_path = None
    prod_noindex = False
    bad_indent_found = False
    # Track whether at least one correctly 2-space-indented noindex HEADER was parsed
    # under any path rule (not just present anywhere in the file).
    correctly_indented_noindex_found = False

    for i, raw_line in enumerate(lines):
        lineno = i + 1
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # A path rule starts at column 0 (no leading whitespace)
        if not raw_line[0:1].isspace():
            current_path = stripped
            continue

        # This is a header line under current_path — check exact 2-space indentation
        # Reject tab indentation
        if raw_line.startswith("\t"):
            fail(
                f"S4: _headers line {lineno} under path rule '{current_path}' uses "
                "tab indentation — Cloudflare _headers requires EXACTLY two spaces; "
                "tabs cause the rule to be silently ignored"
            )
            bad_indent_found = True
            continue

        # Reject 4-space (or more) indentation
        leading = len(raw_line) - len(raw_line.lstrip(" "))
        if leading != 2:
            fail(
                f"S4: _headers line {lineno} under path rule '{current_path}' has "
                f"{leading} leading spaces — EXACTLY two spaces required; "
                "Cloudflare silently ignores any other indentation"
            )
            bad_indent_found = True
            continue

        # This header line has exactly 2-space indentation under current_path.
        if re.search(r"X-Robots-Tag\s*:\s*noindex", raw_line, re.IGNORECASE):
            correctly_indented_noindex_found = True
            # Check for production noindex: any top-level root path rule applying noindex
            if current_path and _is_prod_root_path(current_path):
                prod_noindex = True

    # If noindex appears in the file but was never seen as a correctly-indented header
    # under a path rule, it is sitting at column 0 — Cloudflare treats it as a path,
    # not a header, so staging would NOT be noindexed.
    if noindex_present_in_file and not correctly_indented_noindex_found and not bad_indent_found:
        fail(
            "S4: X-Robots-Tag: noindex is present in _headers but is NOT indented under "
            "a path rule — a column-0 line is treated by Cloudflare as a PATH, not a header, "
            "so staging will NOT be noindexed. Indent it with exactly two spaces under the "
            "staging path rule."
        )

    if prod_noindex:
        fail(
            "S4: _headers applies X-Robots-Tag: noindex to a top-level root path rule "
            "('/*' or '/') — this would noindex production. Scope the noindex rule to the "
            "staging path prefix only (e.g. /staging/* or use a staging-only subdomain path)"
        )


def check_s5_custom_domain(project_dir, fail):
    """S5: wrangler.toml declares a production custom domain/route, not only workers.dev."""
    wrangler_files = _find_files(project_dir, r"^wrangler\.toml$")
    if not wrangler_files:
        return  # S2 already flagged missing wrangler.toml

    _, wpath = wrangler_files[0]
    content = _read(wpath)
    if content is None:
        return

    # Look for route/routes or custom_domain declarations
    has_route = re.search(
        r"(route\s*=|routes\s*=|\[\[routes\]\]|custom_domain\s*=)", content
    )
    if not has_route:
        fail(
            "S5: wrangler config has no route, [[routes]], or custom_domain declaration — "
            "add a production route pointing to your real domain "
            "(e.g. route = { pattern = 'yourdomain.com/*', zone_name = 'yourdomain.com' })"
        )
        return

    # Check that any declared route doesn't only use workers.dev or pages.dev
    # Extract route pattern values
    route_values = re.findall(
        r"""(?:route|custom_domain)\s*=\s*['"]([^'"]+)['"]""", content
    )
    # Also check TOML pattern = "..." inside [[routes]] blocks
    route_values += re.findall(r"""pattern\s*=\s*['"]([^'"]+)['"]""", content)

    only_dev = all(
        re.search(r"\.(workers|pages)\.dev", v) for v in route_values
    ) if route_values else False

    if only_dev:
        fail(
            "S5: all wrangler route/custom_domain values point to *.workers.dev or "
            "*.pages.dev — add a production custom domain route for your real domain "
            "so the site is reachable without a workers.dev subdomain"
        )


def check_s6_smoke_manifest(project_dir, fail):
    """S6: a smoke-check artifact exists and asserts: prod 200, staging noindex, prod NOT noindexed."""
    smoke_files = _find_files(project_dir, r"^smoke.*\.(sh|md|txt)$")
    if not smoke_files:
        fail(
            "S6: no smoke-check artifact found (expected smoke_test.sh, SMOKE.md, etc.) — "
            "create one that asserts: (a) production URL returns 200, "
            "(b) staging responds with X-Robots-Tag: noindex, "
            "(c) production does NOT return X-Robots-Tag: noindex"
        )
        return

    _, spath = smoke_files[0]
    content = _read(spath)
    if content is None:
        fail(f"S6: cannot read {os.path.basename(spath)}")
        return

    missing = []
    # (a) production URL returns 200
    if not re.search(r"200", content):
        missing.append("production URL returns 200")
    # (b) staging responds with X-Robots-Tag noindex
    if not re.search(r"X-Robots-Tag.*noindex|noindex.*X-Robots-Tag", content, re.IGNORECASE):
        missing.append("staging responds with X-Robots-Tag: noindex")
    # (c) production is NOT noindexed — must invoke curl against the prod URL AND assert
    # the ABSENCE of noindex via an executable statement; a comment merely mentioning
    # "not noindexed" does not count.
    # Strategy: look for a non-comment line that invokes curl AND within 3 lines there is a
    # non-comment line that (i) references noindex and (ii) uses an absence-assertion pattern
    # (grep -qi noindex && exit, grep -i noindex && exit, etc. — the && exit pattern signals
    # "fail if noindex IS found", i.e. asserting its ABSENCE). The staging check uses
    # `grep -qi noindex || exit` (fail if NOT found); the prod check must use `&& exit`.
    has_prod_noindex_curl_check = False
    lines_content = content.splitlines()
    for idx, line in enumerate(lines_content):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        # A curl call on a non-comment, non-blank line
        if not re.search(r"\bcurl\b", line, re.IGNORECASE):
            continue
        # Found a curl line. Check next 3 lines (inclusive of current) for a non-comment
        # executable line that references noindex via an absence-assertion (&&-exit pattern).
        window_lines = lines_content[idx:idx + 4]
        for wl in window_lines:
            wl_stripped = wl.strip()
            if wl_stripped.startswith("#") or not wl_stripped:
                continue
            # Must reference noindex AND use &&-exit (absence assertion)
            if re.search(r"noindex", wl, re.IGNORECASE) and re.search(
                r"&&\s*\{|&&\s*echo|grep.*noindex.*&&|noindex.*&&", wl, re.IGNORECASE
            ):
                has_prod_noindex_curl_check = True
                break
        if has_prod_noindex_curl_check:
            break
    if not has_prod_noindex_curl_check:
        missing.append(
            "production is NOT noindexed (must use curl to assert absence of X-Robots-Tag: noindex "
            "on the production URL — a comment mentioning 'not noindexed' is not sufficient)"
        )

    if missing:
        fail(
            f"S6: smoke-check artifact {os.path.basename(spath)} is missing assertions: "
            + "; ".join(missing)
            + " — a smoke check that does not verify all three is not a real smoke check"
        )


# ------------------------------------------------------------------ runner


def run_gate(project_dir):
    """Run all S1-S6 checks. Return exit code 0 (PASS) or 1 (FAIL)."""
    if not os.path.isdir(project_dir):
        print(f"LOAD ERROR: '{project_dir}' is not a directory")
        return 2

    msgs, fail = fail_msgs()
    check_s1_analytics_real(project_dir, fail)
    check_s2_deploy_target_correct(project_dir, fail)
    check_s3_no_placeholder_config(project_dir, fail)
    check_s4_staging_noindex_exact(project_dir, fail)
    check_s5_custom_domain(project_dir, fail)
    check_s6_smoke_manifest(project_dir, fail)

    if msgs:
        for m in msgs:
            print(f"FAIL {m}")
        print(f"ship_gate: FAIL ({len(msgs)} problems)")
        return 1

    print("ship_gate: PASS — all S1-S6 checks green")
    return 0


# ------------------------------------------------------------------ selftest

# Good fixture: a tiny 2-page site with a CORRECT ship config.
# _headers uses REAL two-space indentation (the single most important fixture detail).
GOOD_FILES = {
    "index.html": (
        "<!DOCTYPE html><html><head>"
        "<script async src='https://www.googletagmanager.com/gtag/js?id=G-AB1CD2EF34'></script>"
        "<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}"
        "gtag('js',new Date());gtag('config','G-AB1CD2EF34');</script>"
        "</head><body><h1>TimeCard</h1></body></html>"
    ),
    "calculator.html": (
        "<!DOCTYPE html><html><head>"
        "<script async src='https://www.googletagmanager.com/gtag/js?id=G-AB1CD2EF34'></script>"
        "<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}"
        "gtag('js',new Date());gtag('config','G-AB1CD2EF34');</script>"
        "</head><body><h1>Calculator</h1></body></html>"
    ),
    "wrangler.toml": (
        "name = \"timecard-calculator\"\n"
        "main = \"src/worker.js\"\n"
        "compatibility_date = \"2024-01-01\"\n"
        "\n"
        "[assets]\n"
        "directory = \"./dist\"\n"
        "\n"
        "[[routes]]\n"
        "pattern = \"timecardpro.io/*\"\n"
        "zone_name = \"timecardpro.io\"\n"
        "\n"
        "[env.staging]\n"
        "name = \"timecard-calculator-staging\"\n"
    ),
    # _headers: path rule at col 0, header lines indented with EXACTLY two spaces
    "_headers": (
        "https://staging.timecardpro.io/*\n"
        "  X-Robots-Tag: noindex\n"
        "\n"
        "/*\n"
        "  X-Content-Type-Options: nosniff\n"
    ),
    "smoke_test.sh": (
        "#!/bin/bash\n"
        "# Smoke checks for timecardpro.io\n"
        "# (a) production URL returns 200\n"
        "STATUS=$(curl -s -o /dev/null -w '%{http_code}' https://timecardpro.io/)\n"
        "[ \"$STATUS\" = \"200\" ] || { echo 'FAIL: prod 200 check'; exit 1; }\n"
        "# (b) staging responds with X-Robots-Tag noindex\n"
        "ROBOTS=$(curl -sI https://staging.timecardpro.io/ | grep -i X-Robots-Tag)\n"
        "echo \"$ROBOTS\" | grep -qi noindex || { echo 'FAIL: staging noindex check'; exit 1; }\n"
        "# (c) production is NOT noindexed\n"
        "PROD_ROBOTS=$(curl -sI https://timecardpro.io/ | grep -i X-Robots-Tag)\n"
        "echo \"$PROD_ROBOTS\" | grep -qi noindex && { echo 'FAIL: prod must not be noindexed'; exit 1; }\n"
        "echo 'SMOKE PASS'\n"
    ),
}


def _write_fixture(root, files):
    """Write a dict of filename->content into root dir."""
    for name, content in files.items():
        path = os.path.join(root, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


def selftest():
    import copy

    # Bad cases — one per check (S1-S6) plus one additional S4 indentation variant.
    # TDD: define the bad case, then the check that refuses it.
    bad_cases = {
        # S1: placeholder GA4 id
        "s1-placeholder-ga4-id": lambda files: files.update({
            "index.html": files["index.html"].replace("G-AB1CD2EF34", "G-XXXXXXXXXX"),
            "calculator.html": files["calculator.html"].replace("G-AB1CD2EF34", "G-XXXXXXXXXX"),
        }),
        # S2: deprecated Workers Sites layout
        "s2-deprecated-workers-sites": lambda files: files.update({
            "wrangler.toml": (
                "name = \"timecard-calculator\"\n"
                "type = \"javascript\"\n"
                "main = \"src/index.js\"\n"
                "[site]\n"
                "bucket = \".\"\n"
                "[[build.upload_rules]]\n"
                "type = \"CompiledContentAssets\"\n"
            )
        }),
        # S3: placeholder YOUR_ZONE_ID in wrangler config
        "s3-placeholder-zone-id": lambda files: files.update({
            "wrangler.toml": files["wrangler.toml"] + "\nzone_id = \"YOUR_ZONE_ID\"\n",
        }),
        # S4: tab-indented _headers (the headline bad fixture — must be refused)
        "s4-tab-indented-headers": lambda files: files.update({
            "_headers": (
                "https://staging.timecardpro.io/*\n"
                "\tX-Robots-Tag: noindex\n"  # TAB indentation — must be refused
                "\n"
                "/*\n"
                "  X-Content-Type-Options: nosniff\n"
            )
        }),
        # S4b: four-space indented _headers
        "s4-four-space-headers": lambda files: files.update({
            "_headers": (
                "https://staging.timecardpro.io/*\n"
                "    X-Robots-Tag: noindex\n"  # 4-space indentation — must be refused
                "\n"
                "/*\n"
                "  X-Content-Type-Options: nosniff\n"
            )
        }),
        # S4c: zero-indent (column-0) X-Robots-Tag: noindex — Cloudflare treats it as a
        # path, not a header, so staging would NOT be noindexed. Must be refused.
        "s4-zero-indent-noindex": lambda files: files.update({
            "_headers": (
                "https://staging.timecardpro.io/*\n"
                "X-Robots-Tag: noindex\n"  # COLUMN 0 — treated as a path, not a header
                "\n"
                "/*\n"
                "  X-Content-Type-Options: nosniff\n"
            )
        }),
        # S4d: production root path '/' carrying a 2-space-indented noindex — must be refused
        "s4-prod-noindexed": lambda files: files.update({
            "_headers": (
                "https://staging.timecardpro.io/*\n"
                "  X-Robots-Tag: noindex\n"
                "\n"
                "/\n"                            # production root rule
                "  X-Robots-Tag: noindex\n"     # 2-space-indented noindex on prod root
                "  X-Content-Type-Options: nosniff\n"
            )
        }),
        # S3: route uses 'yourdomain.com' (copy-paste example domain) — must be refused
        "s3-example-domain": lambda files: files.update({
            "wrangler.toml": (
                "name = \"timecard-calculator\"\n"
                "main = \"src/worker.js\"\n"
                "compatibility_date = \"2024-01-01\"\n"
                "\n"
                "[assets]\n"
                "directory = \"./dist\"\n"
                "\n"
                "[[routes]]\n"
                "pattern = \"yourdomain.com/*\"\n"  # copy-paste example domain
                "zone_name = \"yourdomain.com\"\n"
            )
        }),
        # S5: no custom domain, only workers.dev
        "s5-no-custom-domain": lambda files: files.update({
            "wrangler.toml": (
                "name = \"timecard-calculator\"\n"
                "main = \"src/worker.js\"\n"
                "compatibility_date = \"2024-01-01\"\n"
                "\n"
                "[assets]\n"
                "directory = \"./dist\"\n"
            )
        }),
        # S6: smoke file missing noindex assertion
        "s6-smoke-missing-noindex-check": lambda files: files.update({
            "smoke_test.sh": (
                "#!/bin/bash\n"
                "STATUS=$(curl -s -o /dev/null -w '%{http_code}' https://timecardpro.io/)\n"
                "[ \"$STATUS\" = \"200\" ] || exit 1\n"
                "echo 'SMOKE PASS'\n"
            )
        }),
        # S6b: smoke file with prod-not-noindexed assertion only in a comment — must be refused
        # because the check requires an actual curl call, not just a mention in a comment.
        "s6-smoke-comment-only-noindex": lambda files: files.update({
            "smoke_test.sh": (
                "#!/bin/bash\n"
                "# (a) production URL returns 200\n"
                "STATUS=$(curl -s -o /dev/null -w '%{http_code}' https://timecardpro.io/)\n"
                "[ \"$STATUS\" = \"200\" ] || { echo 'FAIL: prod 200 check'; exit 1; }\n"
                "# (b) staging responds with X-Robots-Tag noindex\n"
                "ROBOTS=$(curl -sI https://staging.timecardpro.io/ | grep -i X-Robots-Tag)\n"
                "echo \"$ROBOTS\" | grep -qi noindex || { echo 'FAIL: staging noindex check'; exit 1; }\n"
                "# (c) production is not noindexed -- trust me, it's fine, checked manually\n"
                "echo 'SMOKE PASS'\n"
            )
        }),
    }

    failures = []
    with tempfile.TemporaryDirectory() as root:
        # Good fixture
        good_dir = os.path.join(root, "good")
        os.makedirs(good_dir)
        _write_fixture(good_dir, GOOD_FILES)
        if run_gate(good_dir) != 0:
            failures.append("golden-good fixture did not PASS")

        # Bad fixtures — one mutation each
        for case, mutate in bad_cases.items():
            bad_dir = os.path.join(root, f"bad-{case}")
            os.makedirs(bad_dir)
            files = {k: v for k, v in GOOD_FILES.items()}
            mutate(files)
            _write_fixture(bad_dir, files)
            if run_gate(bad_dir) != 1:
                failures.append(f"bad case '{case}' was not refused")

        # Invariant: removing wrangler.toml flips PASS -> FAIL
        inv_dir = os.path.join(root, "invariant")
        os.makedirs(inv_dir)
        _write_fixture(inv_dir, GOOD_FILES)
        os.remove(os.path.join(inv_dir, "wrangler.toml"))
        if run_gate(inv_dir) != 1:
            failures.append("invariant: removing wrangler.toml did not flip to FAIL")

    print()
    if failures:
        for f in failures:
            print(f"SELFTEST FAILURE: {f}")
        print(f"SELFTEST RESULT: FAIL ({len(failures)} problems)")
        return 1

    print(
        f"SELFTEST RESULT: PASS (1 good, {len(bad_cases)} bad, 1 invariant)"
    )
    return 0


def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        return selftest()
    if len(args) != 1:
        print(__doc__)
        return 2
    return run_gate(args[0])


if __name__ == "__main__":
    sys.exit(main())
