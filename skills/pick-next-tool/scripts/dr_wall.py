#!/usr/bin/env python3
"""
dr_wall.py -- the DR-80-WALL winnability gate for `pick-next-tool`.

WHY THIS EXISTS
---------------
Before committing build effort to a tool, you need an honest read on whether the
page-1 organic field is a "wall" of strong, authoritative incumbents (lose) or a
soft field with thin sites already ranking (winnable). The classic proxy for a
site's authority is its Domain Rating, but the real Ahrefs/Moz DR APIs are paid.
OpenPageRank (openpagerank.com, run by DomCop) exposes a FREE public PageRank
score per domain on a 0-10 decimal scale, derived from Common Crawl link data.
This script turns each page-1 domain's OpenPageRank into a 0-100 "dr_proxy"
(decimal * 10) and applies a deterministic wall/winnability rule.

It is the authority side of the live-SERP recheck: it produces `weak_count`
(the thin-site-proof signal) and a wall verdict that the human/agent folds into
score.py's winnability inputs. It does NOT itself decide build/no-build; it
hands a clean, measured signal to scoring.

DR PROXY -- READ THIS BEFORE TRUSTING A NUMBER
----------------------------------------------
OpenPageRank's `page_rank_decimal` is a 0-10 score on a roughly logarithmic
scale, NOT Ahrefs DR. We multiply by 10 to land on a familiar 0-100 axis so the
thresholds read like DR thresholds, but it is an APPROXIMATION:
  * It tracks link-graph authority well enough to separate "big authoritative
    incumbent" (proxy ~60-90) from "thin one-page affiliate / UGC thread"
    (proxy <30). That separation is all this gate needs.
  * It is NOT interchangeable with Ahrefs DR for fine distinctions; treat
    dr_proxy as ORDINAL, not a precise DR reading.
  * Brand-new domains and domains OpenPageRank has not crawled come back with a
    null or 0 PageRank. A zero here means "no data", NOT "weak site" -- a brand
    new exact-match domain can still outrank you. We therefore classify null/0
    as 'unknown, verify' and EXCLUDE it from weak_count, so a no-data domain
    never masquerades as thin-site proof.

API -- OpenPageRank getPageRank (confirmed shape, 2026-06)
----------------------------------------------------------
Confirmed via the official docs (domcop.com/openpagerank/documentation) and a
web search of the same:
    GET https://openpagerank.com/api/v1.0/getPageRank
        ?domains[]=google.com&domains[]=apple.com&...
    Header:  API-OPR: <your api key>
    Limit:   up to 100 domains per request (we chunk at 100).
    Rate:    ~10,000 calls/hour on the free tier.
Response JSON (per-domain object inside `response`):
    {
      "status_code": 200,
      "response": [
        {
          "status_code": 200,
          "error": "",
          "page_rank_integer": 9,
          "page_rank_decimal": 9.31,
          "rank": "1",
          "domain": "google.com"
        },
        { "status_code": 404, "error": "...", "page_rank_integer": 0,
          "page_rank_decimal": 0, "domain": "brand-new-domain.com" },
        ...
      ]
    }
A per-domain status_code of 200 means a real score; non-200 (e.g. 404) means
OpenPageRank has no data for that domain -> treated as null/unknown here.
(Live confirmation via WebFetch was blocked in the build sandbox; the shape
above is the documented contract. If DomCop changes it, only `_parse_response`
and the endpoint constant need touching.)

CREDENTIALS (read from env; NEVER hard-coded)
---------------------------------------------
  OPENPAGERANK_API_KEY   -- sent as the 'API-OPR' request header.
If it is missing, this script prints a one-line pointer to SETUP.md and exits
non-zero. It never dumps a traceback.

RULES (the gate)
----------------
Inputs: the page-1 organic domains (ideally the top 10), in order.
  * dr_proxy        = round(page_rank_decimal * 10, 1)   (0-100), or None if no data.
  * A domain is WEAK if it has data AND dr_proxy < 30. null/0 (no data) is NOT
    weak -- it is 'unknown, verify'.
  * weak_count      = number of WEAK domains across the supplied set. This is the
    thin-site-proof signal score.py consumes (more weak sites = more winnable).
  * Among the TOP 10 supplied domains, count those with dr_proxy >= 60 (strong).
  * wall = True  iff  >= 8 of the top-10 are strong (proxy >= 60)
                 AND  there are NO weak sites (weak_count == 0).
    i.e. a wall is an almost-uniform field of authoritative incumbents with not a
    single thin crack to slip through. Any weak site, or fewer than 8 strong
    incumbents, means the field is NOT a wall.
  * verdict (human-readable):
      "wall"           -> wall is True (avoid; field is fortified).
      "winnable"       -> not a wall AND weak_count >= 1 (thin sites already rank).
      "contested"      -> not a wall AND weak_count == 0 (no wall, but no thin
                          crack either: a mid-authority field, decide on merits).

HOW IT FEEDS score.py
---------------------
score.py scores a candidate from MEASURED fields. This script OWNS two of them
and emits the rest as null placeholders so the JSON maps onto score.py's
candidate dict with no renaming:
    weak_count       int   -- OWNED here (count of dr_proxy<30 page-1 domains)
    thin_site_proof  bool  -- OWNED here (True when weak_count >= 1; a thin/low-DR
                              site already ranks page 1). score.py also lets a
                              long-tail thin ranking flip this True downstream;
                              this gate provides the page-1 evidence.
The remaining score.py candidate fields are passed through as null so a
downstream step fills them without renaming anything:
    head_bucket, cluster_kw_count, incumbent_top3_visits, distinct_variants,
    kd_head, native_feature, artifact_type, aio_fire_pct, onebox, cpc,
    has_recurring_affiliate, buyer_slice, build_type.

CLI
---
    python3 dr_wall.py domain1.com domain2.com ...      # page-1 organic domains
    python3 dr_wall.py $(cat page1_domains.txt)

Prints JSON:
    {
      "domains": [ {domain, page_rank_decimal, dr_proxy, status}... ],
      "wall": bool,
      "weak_count": int,
      "strong_top10": int,
      "verdict": "wall" | "winnable" | "contested",
      "score_stub": { weak_count, thin_site_proof, ...null placeholders... },
      "meta": {...}
    }

STDLIB ONLY by default (urllib). If `requests` is importable it is used; if not,
urllib is the fallback -- so this keeps running for years with zero required
third-party dependencies.
"""
from __future__ import annotations

import json
import os
import sys

# Prefer requests if present (nicer), but degrade gracefully to stdlib urllib so
# the script has NO required third-party dependency.
try:  # pragma: no cover - trivial import shim
    import requests  # type: ignore
    _HAVE_REQUESTS = True
except ImportError:  # pragma: no cover
    requests = None  # type: ignore
    _HAVE_REQUESTS = False

import urllib.error
import urllib.parse
import urllib.request

# --------------------------------------------------------------------------- #
# Constants -- the gate's thresholds live here and nowhere else.
# --------------------------------------------------------------------------- #
ENDPOINT = "https://openpagerank.com/api/v1.0/getPageRank"
API_KEY_HEADER = "API-OPR"
ENV_KEY = "OPENPAGERANK_API_KEY"

MAX_DOMAINS_PER_REQUEST = 100   # OpenPageRank caps the domains[] array at 100.
TOP_N = 10                      # "top-10" window for the strong-incumbent count.

WEAK_PROXY_MAX = 30             # dr_proxy < 30  -> weak (thin-site proof signal).
STRONG_PROXY_MIN = 60           # dr_proxy >= 60 -> strong incumbent.
WALL_STRONG_MIN = 8             # >= 8 of top-10 strong (AND no weak) -> wall.

TIMEOUT = 15                    # seconds per request.

SETUP_HINT = (
    "See SETUP.md (in the skill's references/ directory) for how to get a free "
    "OpenPageRank API key (openpagerank.com / DomCop) and export it as the "
    f"{ENV_KEY} environment variable."
)


# --------------------------------------------------------------------------- #
# Domain hygiene -- callers may paste full URLs; we want bare registrable hosts.
# --------------------------------------------------------------------------- #
def normalize_domain(raw):
    """Reduce a pasted URL/host to a bare lowercase domain.

    "https://www.Example.com/path?q=1" -> "example.com"
    "Example.COM"                       -> "example.com"
    Leading "www." is stripped because OpenPageRank scores the registrable
    domain; "www." and the apex resolve to the same score and would otherwise
    double-count. Returns "" for empty/garbage input (caller drops it).
    """
    s = (raw or "").strip()
    if not s:
        return ""
    # If it looks like a URL, parse out the host; otherwise treat the whole
    # string as host[/path].
    if "://" in s:
        host = urllib.parse.urlsplit(s).netloc
    else:
        host = s.split("/", 1)[0]
    host = host.split("@")[-1]      # drop any user:pass@
    host = host.split(":", 1)[0]    # drop any :port
    host = host.strip().lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return host


def _dedupe_preserve_order(domains):
    """Lower/normalize and de-duplicate while preserving first-seen order."""
    seen = set()
    ordered = []
    for d in domains:
        nd = normalize_domain(d)
        if nd and nd not in seen:
            seen.add(nd)
            ordered.append(nd)
    return ordered


# --------------------------------------------------------------------------- #
# Network -- one chunked GET against getPageRank. Two backends, same return.
# --------------------------------------------------------------------------- #
def _request_chunk(chunk, api_key):
    """Fetch one <=100-domain chunk. Returns the parsed `response` list.

    Raises RuntimeError with a one-line message on any transport/HTTP/parse
    failure so the CLI can surface it cleanly and exit non-zero.
    """
    # domains[]=a.com&domains[]=b.com ... (doseq expands the list correctly).
    query = urllib.parse.urlencode({"domains[]": chunk}, doseq=True)
    url = f"{ENDPOINT}?{query}"
    headers = {API_KEY_HEADER: api_key}

    if _HAVE_REQUESTS:
        try:
            resp = requests.get(url, headers=headers, timeout=TIMEOUT)
        except requests.RequestException as exc:  # type: ignore[union-attr]
            raise RuntimeError(f"request failed: {exc}") from exc
        if resp.status_code != 200:
            raise RuntimeError(
                f"HTTP {resp.status_code} from OpenPageRank "
                f"({_short(resp.text)})"
            )
        try:
            payload = resp.json()
        except ValueError as exc:
            raise RuntimeError("OpenPageRank returned non-JSON body") from exc
    else:
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                raw = r.read()
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", "replace")
            except Exception:  # noqa: BLE001
                pass
            raise RuntimeError(
                f"HTTP {exc.code} from OpenPageRank ({_short(body)})"
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"request failed: {exc}") from exc
        try:
            payload = json.loads(raw.decode("utf-8", "replace"))
        except json.JSONDecodeError as exc:
            raise RuntimeError("OpenPageRank returned non-JSON body") from exc

    return _extract_response_list(payload)


def _short(text, n=180):
    """Trim an error body to one short line for a clean CLI message."""
    if not text:
        return ""
    one = " ".join(str(text).split())
    return one[:n] + ("..." if len(one) > n else "")


def _extract_response_list(payload):
    """Pull the per-domain list out of a getPageRank payload, defensively.

    Expected: {"status_code":200, "response":[ {...per domain...}, ... ]}.
    A top-level non-200 with an error string is surfaced as a RuntimeError
    (e.g. invalid/expired key). Anything unexpected -> [] for that chunk rather
    than a crash.
    """
    if not isinstance(payload, dict):
        return []
    top = payload.get("status_code")
    if top is not None and top != 200:
        # Surface auth / quota failures clearly (e.g. 401/403).
        err = payload.get("error") or payload.get("message") or f"status {top}"
        raise RuntimeError(f"OpenPageRank error: {_short(err)}")
    resp = payload.get("response")
    if isinstance(resp, list):
        return resp
    return []


def _parse_response(resp_list):
    """Turn a getPageRank `response` list into our per-domain records.

    A per-domain record:
        {domain, page_rank_decimal (float|None), dr_proxy (float|None), status}
    where status is "scored" (real data) or "unknown" (null/0/no data ->
    'unknown, verify', NOT weak).
    """
    out = {}
    for item in resp_list:
        if not isinstance(item, dict):
            continue
        domain = normalize_domain(item.get("domain", ""))
        if not domain:
            continue
        per_status = item.get("status_code")
        raw_dec = item.get("page_rank_decimal")
        dec = _coerce_float(raw_dec)
        # A domain is "scored" only when OpenPageRank returned 200 for it AND a
        # positive decimal. Otherwise it is a brand-new / uncrawled domain:
        # unknown, NOT weak.
        if per_status == 200 and dec is not None and dec > 0:
            out[domain] = {
                "domain": domain,
                "page_rank_decimal": dec,
                "dr_proxy": round(dec * 10, 1),
                "status": "scored",
            }
        else:
            out[domain] = {
                "domain": domain,
                "page_rank_decimal": dec if dec is not None else None,
                "dr_proxy": None,
                "status": "unknown",   # null/0 PageRank -> 'unknown, verify'
            }
    return out


def _coerce_float(v):
    """Best-effort float coercion; None/blank/garbage -> None."""
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def fetch_page_rank(domains, api_key):
    """Fetch records for `domains` (already normalized), chunking at 100.

    Returns a list of per-domain records in the SAME order as `domains`. A
    domain OpenPageRank omits entirely is emitted as an "unknown" record so the
    caller never silently loses a row.
    """
    merged = {}
    for start in range(0, len(domains), MAX_DOMAINS_PER_REQUEST):
        chunk = domains[start:start + MAX_DOMAINS_PER_REQUEST]
        resp_list = _request_chunk(chunk, api_key)
        merged.update(_parse_response(resp_list))

    records = []
    for d in domains:
        if d in merged:
            records.append(merged[d])
        else:
            # Domain not returned at all -> unknown, verify.
            records.append({
                "domain": d,
                "page_rank_decimal": None,
                "dr_proxy": None,
                "status": "unknown",
            })
    return records


# --------------------------------------------------------------------------- #
# The gate -- pure function over records, no I/O. This is the testable core.
# --------------------------------------------------------------------------- #
def evaluate(records):
    """Apply the wall / winnability rule to per-domain records.

    Returns (wall, weak_count, strong_top10, verdict).
      weak_count   : domains (any position) with dr_proxy < 30 (scored only).
      strong_top10 : domains among the first TOP_N with dr_proxy >= 60.
      wall         : strong_top10 >= 8 AND weak_count == 0.
      verdict      : "wall" | "winnable" | "contested".
    """
    weak_count = 0
    for r in records:
        proxy = r.get("dr_proxy")
        # null/0 (status "unknown") is excluded by construction: dr_proxy is None
        # there, so it can never be < WEAK_PROXY_MAX.
        if proxy is not None and proxy < WEAK_PROXY_MAX:
            weak_count += 1

    top10 = records[:TOP_N]
    strong_top10 = sum(
        1 for r in top10
        if r.get("dr_proxy") is not None and r["dr_proxy"] >= STRONG_PROXY_MIN
    )

    wall = strong_top10 >= WALL_STRONG_MIN and weak_count == 0

    if wall:
        verdict = "wall"
    elif weak_count >= 1:
        verdict = "winnable"
    else:
        verdict = "contested"

    return wall, weak_count, strong_top10, verdict


def _score_stub(weak_count):
    """Shape the gate's output onto score.py's candidate dict.

    OWNS weak_count and thin_site_proof; every field requiring a separate
    measurement is null so a downstream step fills it in without renaming. Field
    names and value domains mirror score.py's documented CANDIDATE INPUT exactly.
    """
    return {
        # --- owned by this gate ---
        "weak_count": weak_count,
        "thin_site_proof": weak_count >= 1,
        # --- to be measured downstream; null placeholders ---
        "head_bucket": None,            # "<100"|"100-1K"|"1K-10K"|"10K-100K"|">=100K"
        "cluster_kw_count": None,       # int  (autocomplete_fanout)
        "incumbent_top3_visits": None,  # int  (Similarweb)
        "distinct_variants": None,      # int  (autocomplete_fanout)
        "kd_head": None,                # int 0-100 (Ahrefs)
        "native_feature": None,         # bool (live check)
        "artifact_type": None,          # str  (classified)
        "aio_fire_pct": None,           # int 0-100 (live SERP)
        "onebox": None,                 # bool (live SERP)
        "cpc": None,                    # float (ads)
        "has_recurring_affiliate": None,  # bool (research)
        "buyer_slice": None,            # "strong"|"weak"|"none"
        "build_type": None,             # str  (spec)
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _main(argv):
    domains_in = [a for a in argv[1:] if a.strip()]
    if not domains_in:
        print("usage: python3 dr_wall.py <domain> [<domain> ...]",
              file=sys.stderr)
        print("       (the page-1 organic domains, ideally the top 10)",
              file=sys.stderr)
        print("       prints JSON {domains, wall, weak_count, strong_top10, "
              "verdict, score_stub, meta}", file=sys.stderr)
        return 2

    api_key = os.environ.get(ENV_KEY, "").strip()
    if not api_key:
        print(f"ERROR: missing required environment variable: {ENV_KEY}",
              file=sys.stderr)
        print(SETUP_HINT, file=sys.stderr)
        return 1

    domains = _dedupe_preserve_order(domains_in)
    if not domains:
        print("ERROR: no valid domains after normalization.", file=sys.stderr)
        return 1

    try:
        records = fetch_page_rank(domains, api_key)
    except RuntimeError as exc:
        print(f"ERROR: OpenPageRank request failed: {exc}", file=sys.stderr)
        print(SETUP_HINT, file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - never dump a raw traceback at the CLI
        msg = str(exc).strip().splitlines()[0] if str(exc).strip() else exc.__class__.__name__
        print(f"ERROR: OpenPageRank request failed: {msg}", file=sys.stderr)
        print(SETUP_HINT, file=sys.stderr)
        return 1

    wall, weak_count, strong_top10, verdict = evaluate(records)

    unknown_count = sum(1 for r in records if r["status"] == "unknown")
    result = {
        "domains": records,
        "wall": wall,
        "weak_count": weak_count,
        "strong_top10": strong_top10,
        "verdict": verdict,
        "score_stub": _score_stub(weak_count),
        "meta": {
            "domains_evaluated": len(records),
            "top_n_window": TOP_N,
            "scored_count": sum(1 for r in records if r["status"] == "scored"),
            "unknown_count": unknown_count,   # null/0 PageRank -> verify these
            "weak_proxy_max": WEAK_PROXY_MAX,
            "strong_proxy_min": STRONG_PROXY_MIN,
            "wall_strong_min": WALL_STRONG_MIN,
            "backend": "requests" if _HAVE_REQUESTS else "urllib",
        },
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
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
