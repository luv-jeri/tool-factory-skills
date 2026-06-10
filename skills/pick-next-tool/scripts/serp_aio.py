#!/usr/bin/env python3
"""
SERP + AI-Overview reader for `pick-next-tool` `--data=auto` (via SerpApi).

WHAT IT DOES
------------
Given a head/variant keyword, pulls the live US Google SERP through SerpApi and
returns the score.py-relevant signals that were previously gathered by hand in a
browser: whether an AI Overview fired (the core AI-Resistance input), whether a
calculator/answer-box "onebox" answers the query inline (the Gate-C / AI=1 kill),
and the page-1 domains (feed these to `dr_wall.py` for the DR-wall + weak_count).

It returns RAW MEASURED signals for ONE keyword — it does NOT score. The skill
aggregates across the cluster's head + variants:
  aio_fire_pct = round(100 * (#keywords where ai_overview_present) / (#checked))
and sets score.py's `onebox=True` if any checked head term shows a calc/answer
onebox. Pass the page-1 domains to dr_wall.py to derive kd-wall / weak_count.

Uses only the Python stdlib (urllib). Reads SERPAPI_KEY from the environment or a
project .env (same loader as the other auto-mode scripts). The free SerpApi plan
is ~250 searches/month, so each call counts — check a handful of head terms, not
every long-tail variant.

Usage:
  python3 serp_aio.py "time card calculator"
  python3 serp_aio.py "loan calculator" --country us --hl en
  python3 serp_aio.py --selftest        # offline parser test (no API call, no search used)
"""
from __future__ import annotations
import json
import os
import sys
import urllib.parse
import urllib.request
import urllib.error

ENV_KEY = "SERPAPI_KEY"
ENDPOINT = "https://serpapi.com/search.json"

# Answer-box types that mean "Google answered it inline" -> the Gate-C / AI=1 onebox kill.
ONEBOX_ANSWER_TYPES = {
    "calculator_result", "calculator", "unit_converter", "currency_converter",
    "conversion", "translation_result", "dictionary_results", "definition",
    "finance_results", "weather_result", "time", "date",
}


def _load_dotenv():
    """Populate os.environ from the nearest .env (walking up from CWD, then this file's dir),
    WITHOUT overriding already-set vars. Stdlib only — mirrors the other auto-mode scripts."""
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
                            k, _, v = line.partition("=")
                            k, v = k.strip(), v.strip().strip('"').strip("'")
                            if k and k not in os.environ:
                                os.environ[k] = v
                except OSError:
                    pass
                return
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent


def _domain(url_or_link):
    if not url_or_link:
        return ""
    s = str(url_or_link)
    if "://" in s:
        s = s.split("://", 1)[1]
    s = s.split("/", 1)[0].strip().lower()
    return s[4:] if s.startswith("www.") else s


def analyze(data):
    """Turn a raw SerpApi google response into score.py-relevant signals (pure; no I/O)."""
    if "error" in data:
        return {"ok": False, "error": data["error"]}

    answer_box = data.get("answer_box") or {}
    ab_type = (answer_box.get("type") or "").lower() if isinstance(answer_box, dict) else ""
    onebox = bool(answer_box) and (ab_type in ONEBOX_ANSWER_TYPES or not ab_type)
    # A bare answer_box with no recognised type is still an inline answer -> treat as onebox.

    ai_overview_present = "ai_overview" in data and bool(data.get("ai_overview"))
    organic = data.get("organic_results") or []
    domains = []
    for r in organic[:10]:
        dom = _domain(r.get("link") or r.get("displayed_link"))
        if dom and dom not in domains:
            domains.append(dom)

    return {
        "ok": True,
        "query": (data.get("search_parameters") or {}).get("q"),
        # --- score.py-relevant signals (for ONE keyword) ---
        "ai_overview_present": ai_overview_present,   # contributes to aio_fire_pct
        "onebox": onebox,                              # -> score.py `onebox` (Gate C / AI=1) if any head term shows it
        "onebox_type": ab_type or None,
        "page1_domains": domains,                      # -> feed dr_wall.py for DR-wall + weak_count
        # --- supporting context ---
        "knowledge_graph_present": "knowledge_graph" in data,
        "people_also_ask_present": bool(data.get("related_questions")),
        "related_searches_count": len(data.get("related_searches") or []),
        "organic_count": len(organic),
        "notes": "ai_overview presence is the AIO signal; onebox=calc/answer box = the Gate-C inline kill; "
                 "pass page1_domains to dr_wall.py for the winnability DR-wall.",
    }


def fetch(query, country="us", hl="en", num=10):
    _load_dotenv()
    key = os.environ.get(ENV_KEY, "")
    if not key:
        return {"ok": False, "error": f"{ENV_KEY} not set (env or project .env). See SETUP.md."}
    params = {"engine": "google", "q": query, "gl": country, "hl": hl,
              "num": str(num), "api_key": key}
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "pick-next-tool/serp_aio"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300]
        return {"ok": False, "error": f"HTTP {e.code}: {body}"}
    except Exception as e:  # noqa: BLE001 - report any transport failure as a clean signal
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    return analyze(data)


# --------------------------------------------------------------------------- #
# Offline parser selftest (no API call, no search consumed).
# --------------------------------------------------------------------------- #
def _selftest():
    cases = [
        ("calc onebox", {"search_parameters": {"q": "loan calculator"},
                         "answer_box": {"type": "calculator_result"},
                         "organic_results": [{"link": "https://www.calculator.net/x"}]},
         {"onebox": True, "ai_overview_present": False}),
        ("ai overview", {"search_parameters": {"q": "best wyr questions"},
                         "ai_overview": {"page_token": "abc"},
                         "organic_results": [{"link": "https://reddit.com/r/x"}]},
         {"onebox": False, "ai_overview_present": True}),
        ("clean transactional", {"search_parameters": {"q": "time card calculator"},
                                 "organic_results": [{"link": "https://clockify.me/t"},
                                                     {"displayed_link": "redcort.com"}]},
         {"onebox": False, "ai_overview_present": False}),
        ("api error", {"error": "Invalid API key"}, None),
    ]
    fails = []
    for name, raw, want in cases:
        got = analyze(raw)
        if want is None:
            if got.get("ok") is not False:
                fails.append(f"{name}: expected ok=False on error")
            continue
        for k, v in want.items():
            if got.get(k) != v:
                fails.append(f"{name}: {k}={got.get(k)} != {v}")
    print("=== serp_aio parser selftest ===")
    print("domains parsed:", analyze(cases[0][1])["page1_domains"])
    if fails:
        print("FAIL:"); [print("  -", f) for f in fails]; return 1
    print("PASS: onebox / ai-overview / domain parsing behave as documented (no API call made).")
    return 0


def _main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    if "--selftest" in argv:
        return _selftest()
    if not args:
        print(__doc__); return 2
    country = "us"
    hl = "en"
    for i, a in enumerate(argv):
        if a == "--country" and i + 1 < len(argv):
            country = argv[i + 1]
        if a == "--hl" and i + 1 < len(argv):
            hl = argv[i + 1]
    print(json.dumps(fetch(args[0], country=country, hl=hl), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
