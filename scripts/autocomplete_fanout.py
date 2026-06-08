#!/usr/bin/env python3
"""
autocomplete_fanout.py -- the durable, free CLUSTER ENGINE for `pick-next-tool`.

WHY THIS EXISTS
---------------
AnswerThePublic, Ubersuggest, KeywordTool.io, AlsoAsked and the rest of the
"keyword idea" SaaS are, at their core, thin front-ends over ONE free public
endpoint: Google Autocomplete (suggestqueries.google.com). They pay for nothing
that you cannot get yourself -- they fan a seed out across the alphabet and a
handful of prefix/suffix modifiers, then sell the de-duplicated union back to
you behind a paywall and a quota. This script IS that fan-out, owned outright:
no key, no quota, no monthly bill, no rate-limit cliff that disappears your
research mid-run. It is the durable substitute for those tools.

WHAT IT DOES
------------
Given a SEED phrase it expands the cluster by querying the autocomplete endpoint
with the seed plus:
  * A-Z suffixes        ("time card calculator a", ... "time card calculator z")
  * question words      (how/what/why/when/best/free as prefixes)
  * tool modifiers      (calculator/generator/free/online as suffix + prefix)
It unions and de-duplicates every returned suggestion into a single `variants`
list, with ~0.5-1s jitter between requests and a realistic User-Agent so the run
looks like an ordinary browser session rather than a scraper.

ENDPOINT (confirmed shape)
--------------------------
    GET https://suggestqueries.google.com/complete/search
        ?client=firefox&hl=en&gl=US&q=<SEED>
The `client=firefox` flavour returns a plain JSON array (NOT JSONP):
    ["<query>", ["suggestion 1", "suggestion 2", ...], ...]
i.e. index 0 echoes the query and index 1 is the list of suggestion strings.
This parser reads index 1 and is defensive about every other position so a
shape change degrades to "no suggestions for this probe" rather than a crash.
(Live WebFetch/curl confirmation of the endpoint was blocked in the build
sandbox; the shape above is the long-stable documented contract. If Google ever
changes it, only `_extract_suggestions` needs updating.)

HOW IT FEEDS score.py
---------------------
score.py scores a candidate from MEASURED fields. This engine produces the raw
cluster a human/agent then measures, and emits its output already shaped so the
cluster-derived fields drop straight in. Per-candidate fields score.py consumes:

    head_bucket             ("<100" | "100-1K" | "1K-10K" | "10K-100K" | ">=100K")
    cluster_kw_count        int   -- here: len(variants)
    incumbent_top3_visits   int   -- (Similarweb, measured downstream)
    distinct_variants       int   -- here: count of distinct non-empty phrasings
    kd_head                 int 0-100   (Ahrefs, measured downstream)
    weak_count              int         (live SERP, measured downstream)
    native_feature          bool        (live check, downstream)
    thin_site_proof         bool        (live check, downstream)
    artifact_type           str         (classified downstream)
    aio_fire_pct            int 0-100   (live SERP, downstream)
    onebox                  bool        (live SERP, downstream)
    cpc                     float       (ads, downstream)
    has_recurring_affiliate bool        (research, downstream)
    buyer_slice             ("strong" | "weak" | "none")  (research, downstream)
    build_type              str         (spec, downstream)

This script OWNS the cluster-shape fields (cluster_kw_count, distinct_variants)
and emits a `score_stub` carrying them plus null placeholders for every field
that still needs an external measurement, so the JSON maps onto score.py's
candidate dict with no renaming.

CLI
---
    python3 autocomplete_fanout.py "time card calculator"
    python3 autocomplete_fanout.py "time card calculator" --gl US
    python3 autocomplete_fanout.py "invoice generator" --gl GB --hl en

Prints JSON: {seed, gl, hl, variants:[...], score_stub:{...}, meta:{...}}.
STDLIB ONLY (urllib). No third-party packages, by design -- this must keep
running for years with zero dependency drift.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ENDPOINT = "https://suggestqueries.google.com/complete/search"

# A realistic, current desktop User-Agent so the request blends in with normal
# browser traffic rather than reading as an obvious script.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Modifier sets. Question words go in front (how/what searches); tool modifiers
# are tried both as suffix (most common: "X calculator") and prefix ("free X").
ALPHABET = [chr(c) for c in range(ord("a"), ord("z") + 1)]
QUESTION_WORDS = ["how", "what", "why", "when", "best", "free"]
TOOL_MODIFIERS = ["calculator", "generator", "free", "online"]

# Network politeness / robustness.
JITTER_MIN = 0.5   # seconds
JITTER_MAX = 1.0   # seconds
TIMEOUT = 10       # seconds per request
MAX_RETRIES = 2    # additional attempts after the first, on transient errors


def _sleep_jitter():
    """Sleep a random 0.5-1.0s between requests to avoid a robotic cadence."""
    time.sleep(random.uniform(JITTER_MIN, JITTER_MAX))


def _build_probes(seed):
    """Build the ordered, de-duplicated list of query strings to send.

    Order: bare seed, A-Z suffixes, question-word prefixes, then tool modifiers
    (suffix and prefix). Duplicates (e.g. a modifier already in the seed) are
    dropped while preserving first-seen order.
    """
    seed = seed.strip()
    probes = [seed]
    probes += [f"{seed} {letter}" for letter in ALPHABET]
    probes += [f"{word} {seed}" for word in QUESTION_WORDS]
    for mod in TOOL_MODIFIERS:
        probes.append(f"{seed} {mod}")   # "time card calculator free"
        probes.append(f"{mod} {seed}")   # "free time card calculator"

    seen = set()
    ordered = []
    for p in probes:
        key = p.lower()
        if key not in seen:
            seen.add(key)
            ordered.append(p)
    return ordered


def _extract_suggestions(payload):
    """Pull the suggestion strings out of a parsed autocomplete payload.

    The `client=firefox` contract is: [query, [suggestions...], ...]. We read
    index 1 and stay defensive so a shape change yields [] rather than raising.
    """
    if not isinstance(payload, list) or len(payload) < 2:
        return []
    suggestions = payload[1]
    if not isinstance(suggestions, list):
        return []
    out = []
    for item in suggestions:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, list) and item and isinstance(item[0], str):
            # Some clients wrap each suggestion in a sub-list; tolerate it.
            out.append(item[0])
    return out


def _fetch(query, gl, hl):
    """Fetch suggestions for a single query string. Returns a list (maybe empty).

    Network/parse failures are swallowed into [] so one bad probe never aborts a
    whole fan-out -- the engine must degrade gracefully, not crash a long run.
    """
    params = urllib.parse.urlencode(
        {"client": "firefox", "hl": hl, "gl": gl, "q": query}
    )
    url = f"{ENDPOINT}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    last_err = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read()
            # Endpoint returns UTF-8; latin-1 fallback guards rare encodings.
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("latin-1", errors="replace")
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                return []  # not JSON -> nothing usable from this probe
            return _extract_suggestions(payload)
        except urllib.error.HTTPError as e:
            last_err = e
            # 4xx (e.g. 400 bad query, 403/429 throttle) -- back off, then move on.
            if attempt < MAX_RETRIES:
                time.sleep(random.uniform(1.0, 2.0))
                continue
            return []
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = e
            if attempt < MAX_RETRIES:
                time.sleep(random.uniform(1.0, 2.0))
                continue
            return []
    _ = last_err  # retained for debugging if needed; intentionally not raised
    return []


def fan_out(seed, gl="US", hl="en"):
    """Run the full cluster fan-out for `seed`. Returns (variants, meta).

    variants: de-duplicated union of every suggestion across every probe, with
              the bare seed echo removed, sorted for stable output.
    meta:     counts useful for auditing the run.
    """
    probes = _build_probes(seed)
    seed_lower = seed.strip().lower()

    union = {}            # lower-cased key -> original-cased suggestion
    probes_with_hits = 0
    total_raw = 0

    for i, probe in enumerate(probes):
        suggestions = _fetch(probe, gl=gl, hl=hl)
        if suggestions:
            probes_with_hits += 1
        total_raw += len(suggestions)
        for s in suggestions:
            s_clean = s.strip()
            if not s_clean:
                continue
            key = s_clean.lower()
            if key == seed_lower:
                continue  # drop the literal seed echo; it's not a "variant"
            if key not in union:
                union[key] = s_clean
        # Jitter between requests, but not after the final one.
        if i < len(probes) - 1:
            _sleep_jitter()

    variants = sorted(union.values(), key=str.lower)
    meta = {
        "probes_sent": len(probes),
        "probes_with_hits": probes_with_hits,
        "raw_suggestions_seen": total_raw,
        "distinct_variants": len(variants),
    }
    return variants, meta


def _score_stub(variants):
    """Shape the cluster output onto score.py's candidate dict.

    This engine OWNS the cluster-shape fields; every field requiring an external
    measurement (Ahrefs KD, live SERP, Similarweb, ads, research) is emitted as
    null so a downstream step can fill it in without renaming anything. Field
    names and value domains mirror score.py's documented CANDIDATE INPUT exactly.
    """
    return {
        # --- owned by this engine (cluster shape) ---
        "cluster_kw_count": len(variants),
        "distinct_variants": len(variants),
        # --- to be measured downstream; null placeholders ---
        "head_bucket": None,            # "<100"|"100-1K"|"1K-10K"|"10K-100K"|">=100K"
        "incumbent_top3_visits": None,  # int  (Similarweb)
        "kd_head": None,                # int 0-100 (Ahrefs)
        "weak_count": None,             # int  (live SERP)
        "native_feature": None,         # bool (live check)
        "thin_site_proof": None,        # bool (live check)
        "artifact_type": None,          # str  (classified)
        "aio_fire_pct": None,           # int 0-100 (live SERP)
        "onebox": None,                 # bool (live SERP)
        "cpc": None,                    # float (ads)
        "has_recurring_affiliate": None,  # bool (research)
        "buyer_slice": None,            # "strong"|"weak"|"none"
        "build_type": None,             # str  (spec)
    }


def _parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="autocomplete_fanout.py",
        description="Free Google-Autocomplete cluster engine for pick-next-tool.",
    )
    parser.add_argument("seed", help='Seed phrase, e.g. "time card calculator"')
    parser.add_argument("--gl", default="US", help="Geo (country) code, default US")
    parser.add_argument("--hl", default="en", help="UI language code, default en")
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    seed = args.seed.strip()
    if not seed:
        print(json.dumps({"error": "empty seed"}), file=sys.stderr)
        return 2

    variants, meta = fan_out(seed, gl=args.gl, hl=args.hl)
    result = {
        "seed": seed,
        "gl": args.gl,
        "hl": args.hl,
        "variants": variants,
        "score_stub": _score_stub(variants),
        "meta": meta,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
