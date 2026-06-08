#!/usr/bin/env python3
"""
Pull real search-volume buckets for the `pick-next-tool` skill.

WHY THIS EXISTS
---------------
score.py is deterministic, but it is only as honest as its inputs. The single
most-faked input is `head_bucket` -- the search-volume tier of a tool's head
keyword. This script replaces a guess with a real number from Google's Keyword
Planner (the GenerateKeywordIdeas endpoint of the Google Ads API), then maps
that number onto the SAME five bucket strings score.py consumes.

DATA QUALITY WARNING -- TREAT AS ORDINAL, NOT ABSOLUTE
------------------------------------------------------
Keyword Planner returns `avg_monthly_searches` as a BUCKETED, rounded figure,
not an exact count. On a no-spend / unfunded Google Ads account, those buckets
are coarser AND tend to be OVER-estimated (Google widens the ranges and rounds
up). So:
  * Use the OUTPUT BUCKET as an ORDINAL signal ("is this 1K-10K or 10K-100K?"),
    never as a precise traffic prediction.
  * scoring-model.md already accounts for this: it converts the bucket to a
    fixed geometric midpoint and tells you to sanity-check the head term
    against Bing Webmaster Tools + Google Trends, using the lower value if the
    Planner disagrees by >1 order of magnitude. This script gives you the
    Planner side of that comparison -- not the final word.

CURRENT API USAGE (verified 2026-06, Google Ads API v24)
--------------------------------------------------------
Confirmed against the official google-ads-python client docs and the canonical
examples/planning/generate_keyword_ideas.py:
  * client  = GoogleAdsClient.load_from_dict(config, version="v24")
  * service = client.get_service("KeywordPlanIdeaService")
  * request = client.get_type("GenerateKeywordIdeasRequest")
      request.customer_id          = <login customer id, digits only>
      request.language             = google_ads_service.language_constant_path("1000")  # English
      request.geo_target_constants = [geo_service.geo_target_constant_path("2840")]      # US
      request.keyword_plan_network = client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
      request.keyword_seed.keywords.extend(keywords)   # up to 20 seeds per request
  * response = service.generate_keyword_ideas(request=request)   # iterable of ideas
      idea.text
      idea.keyword_idea_metrics.avg_monthly_searches            (int)
      idea.keyword_idea_metrics.competition.name                (str enum name)
      idea.keyword_idea_metrics.low_top_of_page_bid_micros      (int micros, /1e6 -> USD)
      idea.keyword_idea_metrics.high_top_of_page_bid_micros     (int micros, /1e6 -> USD)

CREDENTIALS (read from env; NEVER hard-coded)
---------------------------------------------
  GOOGLE_ADS_DEVELOPER_TOKEN
  GOOGLE_ADS_CLIENT_ID
  GOOGLE_ADS_CLIENT_SECRET
  GOOGLE_ADS_REFRESH_TOKEN
  GOOGLE_ADS_LOGIN_CUSTOMER_ID
If any are missing, or the google-ads package is not installed, this script
prints a clear message pointing at SETUP.md and exits non-zero. It does NOT
raise an uncaught traceback.

OUTPUT
------
JSON array on stdout, one object per resolved keyword:
  [
    {
      "keyword": "timesheet calculator",
      "avg_monthly_searches": 40500,
      "bucket": "10K-100K",                # maps to score.py head_bucket
      "competition": "MEDIUM",
      "low_top_of_page_bid": 0.84,         # USD
      "high_top_of_page_bid": 3.12         # USD
    },
    ...
  ]
`bucket` is exactly one of score.py's head_bucket strings:
  "<100" | "100-1K" | "1K-10K" | "10K-100K" | ">=100K"
Feed the head keyword's `bucket` straight into a candidate's `head_bucket`
field, and `high_top_of_page_bid` (or the low/high midpoint) into `cpc`.

USAGE
-----
  python3 volume_buckets.py "timesheet calculator" "time card calculator" ...
  python3 volume_buckets.py kw1 kw2 ... > buckets.json
"""
from __future__ import annotations

import json
import os
import sys

# --------------------------------------------------------------------------- #
# Config -- US English, Search-only network. Keep this stable: changing geo or
# language changes the buckets and would silently invalidate cross-run scoring.
# --------------------------------------------------------------------------- #
GEO_TARGET_UNITED_STATES = "2840"     # geoTargetConstants/2840
LANGUAGE_ENGLISH = "1000"             # languageConstants/1000
API_VERSION = "v24"                   # current as of 2026-06; bump deliberately
MAX_SEEDS_PER_REQUEST = 20            # Keyword Planner caps keyword_seed at 20

REQUIRED_ENV = (
    "GOOGLE_ADS_DEVELOPER_TOKEN",
    "GOOGLE_ADS_CLIENT_ID",
    "GOOGLE_ADS_CLIENT_SECRET",
    "GOOGLE_ADS_REFRESH_TOKEN",
    "GOOGLE_ADS_LOGIN_CUSTOMER_ID",
)

SETUP_HINT = (
    "See SETUP.md (in the skill's references/ directory) for how to create a "
    "Google Ads API developer token, generate an OAuth refresh token, and "
    "export the five GOOGLE_ADS_* environment variables."
)


# --------------------------------------------------------------------------- #
# Bucketing -- the ONLY place that turns a raw integer into a score.py string.
# Boundaries match references/scoring-model.md exactly:
#   <100 | 100-1K | 1K-10K | 10K-100K | >=100K
# Inclusive lower bound, exclusive upper bound (e.g. exactly 1000 -> "1K-10K").
# --------------------------------------------------------------------------- #
def bucket_for(avg_monthly_searches):
    """Map a raw avg_monthly_searches integer to a score.py head_bucket string."""
    n = avg_monthly_searches or 0
    if n < 100:
        return "<100"
    if n < 1_000:
        return "100-1K"
    if n < 10_000:
        return "1K-10K"
    if n < 100_000:
        return "10K-100K"
    return ">=100K"


def micros_to_usd(micros):
    """Google Ads reports bids in micros (1e6 micros = 1 currency unit)."""
    if not micros:
        return 0.0
    return round(micros / 1_000_000, 2)


# --------------------------------------------------------------------------- #
# Preflight -- fail clearly, never crash.
# --------------------------------------------------------------------------- #
def _missing_env():
    return [var for var in REQUIRED_ENV if not os.environ.get(var)]


def _build_config():
    """Assemble the load_from_dict config from env vars (login id digits-only)."""
    login_id = "".join(ch for ch in os.environ["GOOGLE_ADS_LOGIN_CUSTOMER_ID"] if ch.isdigit())
    return {
        "developer_token": os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
        "client_id": os.environ["GOOGLE_ADS_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_ADS_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
        "login_customer_id": login_id,
        "use_proto_plus": True,
    }, login_id


# --------------------------------------------------------------------------- #
# The one network call.
# --------------------------------------------------------------------------- #
def fetch_buckets(keywords):
    """
    Return a list of result dicts for `keywords`. Only keywords actually
    returned by the Planner are included; the Planner may add related ideas,
    which we drop so the output maps 1:1 onto the seeds you asked about
    (matched case-insensitively).
    """
    # Imported here so a missing package is reported by _main as a clean
    # message, not an ImportError traceback at module load.
    from google.ads.googleads.client import GoogleAdsClient

    config, login_id = _build_config()
    client = GoogleAdsClient.load_from_dict(config, version=API_VERSION)

    idea_service = client.get_service("KeywordPlanIdeaService")
    google_ads_service = client.get_service("GoogleAdsService")
    geo_service = client.get_service("GeoTargetConstantService")

    language_rn = google_ads_service.language_constant_path(LANGUAGE_ENGLISH)
    geo_rns = [geo_service.geo_target_constant_path(GEO_TARGET_UNITED_STATES)]

    # Case-insensitive lookup of which seeds we want to keep, preserving the
    # caller's original spelling/order in the output.
    wanted = {kw.strip().lower(): kw for kw in keywords if kw.strip()}
    collected = {}

    # Keyword Planner caps keyword_seed at 20 entries; chunk the seeds.
    seeds = list(wanted.values())
    for start in range(0, len(seeds), MAX_SEEDS_PER_REQUEST):
        chunk = seeds[start:start + MAX_SEEDS_PER_REQUEST]

        request = client.get_type("GenerateKeywordIdeasRequest")
        request.customer_id = login_id
        request.language = language_rn
        request.geo_target_constants = geo_rns
        request.include_adult_keywords = False
        request.keyword_plan_network = (
            client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
        )
        request.keyword_seed.keywords.extend(chunk)

        response = idea_service.generate_keyword_ideas(request=request)

        for idea in response:
            key = idea.text.strip().lower()
            if key not in wanted or key in collected:
                continue  # related idea (not a seed) or already captured
            m = idea.keyword_idea_metrics
            avg = int(m.avg_monthly_searches or 0)
            collected[key] = {
                "keyword": wanted[key],          # caller's original spelling
                "avg_monthly_searches": avg,
                "bucket": bucket_for(avg),
                "competition": (m.competition.name if m.competition else "UNSPECIFIED"),
                "low_top_of_page_bid": micros_to_usd(m.low_top_of_page_bid_micros),
                "high_top_of_page_bid": micros_to_usd(m.high_top_of_page_bid_micros),
            }

    # Any seed the Planner returned no data for -> explicit zero/<100 row, so
    # the caller never silently loses a keyword.
    results = []
    for key, original in wanted.items():
        if key in collected:
            results.append(collected[key])
        else:
            results.append({
                "keyword": original,
                "avg_monthly_searches": 0,
                "bucket": bucket_for(0),
                "competition": "UNSPECIFIED",
                "low_top_of_page_bid": 0.0,
                "high_top_of_page_bid": 0.0,
            })
    return results


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _main(argv):
    keywords = [a for a in argv[1:] if a.strip()]
    if not keywords:
        print("usage: python3 volume_buckets.py <keyword> [<keyword> ...]",
              file=sys.stderr)
        print("       prints JSON [{keyword, avg_monthly_searches, bucket, "
              "competition, low_top_of_page_bid, high_top_of_page_bid}]",
              file=sys.stderr)
        return 2

    missing = _missing_env()
    if missing:
        print("ERROR: missing required environment variable(s): "
              + ", ".join(missing), file=sys.stderr)
        print(SETUP_HINT, file=sys.stderr)
        return 1

    try:
        from google.ads.googleads.client import GoogleAdsClient  # noqa: F401
    except ImportError:
        print("ERROR: the 'google-ads' package is not installed. "
              "Install it with:  pip install google-ads", file=sys.stderr)
        print(SETUP_HINT, file=sys.stderr)
        return 1

    try:
        results = fetch_buckets(keywords)
    except Exception as exc:  # noqa: BLE001 -- never dump a raw traceback at the CLI
        # GoogleAdsException and auth/credential errors all land here. Surface a
        # one-line message plus the pointer, and exit non-zero (do NOT crash).
        msg = str(exc).strip().splitlines()[0] if str(exc).strip() else exc.__class__.__name__
        print(f"ERROR: Google Ads API call failed: {msg}", file=sys.stderr)
        print(SETUP_HINT, file=sys.stderr)
        return 1

    print(json.dumps(results, indent=2))
    return 0


def _load_dotenv():
    """Populate os.environ from the nearest .env (walking up from CWD, then this file's
    directory), WITHOUT overriding vars already set in the real environment. Stdlib only —
    no python-dotenv dependency. Lets `--data=auto` read keys from a project .env per
    SETUP.md Option A; real exported env vars still win."""
    for start in (os.getcwd(), os.path.dirname(os.path.abspath(__file__))):
        d = start
        while True:
            path = os.path.join(d, ".env")
            if os.path.isfile(path):
                try:
                    with open(path) as fh:
                        for raw in fh:
                            line = raw.strip()
                            if not line or line.startswith("#") or "=" not in line:
                                continue
                            key, _, val = line.partition("=")
                            key, val = key.strip(), val.strip().strip('"').strip("'")
                            if key and key not in os.environ:
                                os.environ[key] = val
                except OSError:
                    pass
                return
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent


if __name__ == "__main__":
    _load_dotenv()
    sys.exit(_main(sys.argv))
