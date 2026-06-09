#!/usr/bin/env python3
"""parse_jsonld.py — fetch a URL (or read HTML) and extract+validate JSON-LD.

Produces REAL-MEASURED structured-data evidence for the competitive audit,
replacing the prior brief's "UNVERIFIED" schema guesses.

Usage:
    python3 parse_jsonld.py --url https://example.com/tool
    python3 parse_jsonld.py --file page.html
    python3 parse_jsonld.py --selftest
"""
from __future__ import annotations
import argparse, json, re, sys

_LD_RE = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL)


def _iter_nodes(data):
    """Yield dict nodes, descending into @graph and lists."""
    if isinstance(data, list):
        for item in data:
            yield from _iter_nodes(item)
    elif isinstance(data, dict):
        if isinstance(data.get("@graph"), list):
            for item in data["@graph"]:
                yield from _iter_nodes(item)
        yield data


def extract_jsonld(html: str) -> dict:
    blocks = _LD_RE.findall(html or "")
    types, errors, parsed = [], [], 0
    for raw in blocks:
        try:
            data = json.loads(raw.strip())
            parsed += 1
        except json.JSONDecodeError as e:
            errors.append(str(e))
            continue
        for node in _iter_nodes(data):
            t = node.get("@type")
            if isinstance(t, list):
                types.extend(str(x) for x in t)
            elif t is not None:
                types.append(str(t))
    return {
        "blocks": len(blocks), "parsed": parsed,
        "types": sorted(set(types)),
        "valid": len(blocks) > 0 and not errors,
        "errors": errors,
    }


def _fetch(url: str) -> str:
    import urllib.request
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (projects-competitive-analysis skill)"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", "replace")


_FIXTURE_OK = '''<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[
 {"@type":"WebApplication","name":"X"},
 {"@type":"FAQPage","mainEntity":[]}]}
</script></head></html>'''
_FIXTURE_BAD = '<script type="application/ld+json">{not valid json}</script>'
_FIXTURE_NONE = '<html><body>no schema here</body></html>'


def _selftest() -> int:
    failures = []
    ok = extract_jsonld(_FIXTURE_OK)
    if ok["types"] != ["FAQPage", "WebApplication"]:
        failures.append(f"OK types wrong: {ok['types']}")
    if not ok["valid"]:
        failures.append("OK fixture not marked valid")
    if ok["blocks"] != 1:
        failures.append(f"OK blocks expected 1 got {ok['blocks']}")
    bad = extract_jsonld(_FIXTURE_BAD)
    if bad["valid"]:
        failures.append("BAD json marked valid")
    if not bad["errors"]:
        failures.append("BAD json produced no error")
    none = extract_jsonld(_FIXTURE_NONE)
    if none["valid"] or none["types"]:
        failures.append("NONE fixture wrong")
    if failures:
        print("parse_jsonld selftest FAIL:")
        for f in failures:
            print("  -", f)
        return 1
    print("parse_jsonld selftest PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--url")
    ap.add_argument("--file")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    if args.url:
        print(json.dumps(extract_jsonld(_fetch(args.url)), indent=2))
        return 0
    if args.file:
        with open(args.file, encoding="utf-8", errors="replace") as fh:
            print(json.dumps(extract_jsonld(fh.read()), indent=2))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
