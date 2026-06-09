#!/usr/bin/env python3
"""competitor_strength.py — deterministic competitor-strength engine.

Part of the `competitive-analysis` skill. SINGLE SOURCE OF TRUTH for the
strength score. references/scoring-model.md mirrors this file; if they ever
disagree, THIS FILE WINS and the doc is the bug.

    strength = (0.30*Authority + 0.25*SERP + 0.15*Content
                + 0.12*Feature + 0.13*UX/Perf/A11y + 0.05*Trust) * 20   # 20..100

Each dimension is a deterministic 1..5 sub-score derived from MEASURED fields.
Fails closed: a missing/ill-typed/out-of-range required field raises ContractError.

Usage:
    python3 competitor_strength.py --selftest
    from competitor_strength import score_competitor
"""
from __future__ import annotations
import argparse, json, math, sys


class ContractError(ValueError):
    """Raised when a competitor record violates the input contract."""


WEIGHTS = {  # v0 UNCALIBRATED — see docs/adr/0002-scoring-weights.md
    "authority": 0.30, "serp": 0.25, "content": 0.15,
    "feature": 0.12, "ux_perf_a11y": 0.13, "trust": 0.05,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9

REQUIRED_FIELDS = [
    "dr", "referring_domains", "serp_rank", "ai_overview_cited",
    "serp_features_owned", "word_count", "heading_count", "schema_types",
    "paa_coverage", "feature_coverage", "lcp_ms", "cls", "inp_ms",
    "a11y_score", "clicks_to_result", "trust_signals",
]


def _r(x: float) -> int:
    """Round half-up (avoids Python banker's-rounding surprises)."""
    return int(math.floor(x + 0.5))


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def _require_number(rec, name, lo=None, hi=None, allow_none=False):
    v = rec[name]
    if allow_none and v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ContractError(f"{name} must be a number, got {v!r}")
    if math.isnan(v) or math.isinf(v):
        raise ContractError(f"{name} must be finite, got {v!r}")
    if lo is not None and v < lo:
        raise ContractError(f"{name}={v} below minimum {lo}")
    if hi is not None and v > hi:
        raise ContractError(f"{name}={v} above maximum {hi}")
    return v


def validate(rec: dict) -> None:
    if not isinstance(rec, dict):
        raise ContractError("record must be a dict")
    for f in REQUIRED_FIELDS:
        if f not in rec:
            raise ContractError(f"missing required field: {f}")
    _require_number(rec, "dr", 0, 100)
    _require_number(rec, "referring_domains", 0)
    _require_number(rec, "serp_rank", 1, allow_none=True)
    _require_number(rec, "serp_features_owned", 0, allow_none=True)
    _require_number(rec, "word_count", 0)
    _require_number(rec, "heading_count", 0)
    _require_number(rec, "paa_coverage", 0.0, 1.0)
    _require_number(rec, "feature_coverage", 0.0, 1.0)
    _require_number(rec, "lcp_ms", 0)
    _require_number(rec, "cls", 0)
    _require_number(rec, "inp_ms", 0)
    _require_number(rec, "a11y_score", 0, 100, allow_none=True)
    _require_number(rec, "clicks_to_result", 0)
    _require_number(rec, "trust_signals", 0)
    if rec["ai_overview_cited"] is not None and not isinstance(rec["ai_overview_cited"], bool):
        raise ContractError("ai_overview_cited must be bool or None")
    if not isinstance(rec["schema_types"], list):
        raise ContractError("schema_types must be a list")


def _authority(rec):
    dr, rd = rec["dr"], rec["referring_domains"]
    dr_sc = 5 if dr >= 70 else 4 if dr >= 50 else 3 if dr >= 30 else 2 if dr >= 15 else 1
    rd_sc = 5 if rd >= 1000 else 4 if rd >= 300 else 3 if rd >= 50 else 2 if rd >= 10 else 1
    return _clamp(_r(0.6 * dr_sc + 0.4 * rd_sc), 1, 5)


def _serp(rec):
    rank = rec["serp_rank"]
    if rank is None:
        base = 1
    else:
        base = 5 if rank == 1 else 4 if rank <= 3 else 3 if rank <= 6 else 2 if rank <= 10 else 1
    aio = rec["ai_overview_cited"] is True
    feats = rec["serp_features_owned"] or 0
    bonus = 1 if (aio or feats >= 2) else 0
    return _clamp(base + bonus, 1, 5)


def _content(rec):
    wc = rec["word_count"]
    wc_sc = 5 if wc >= 1500 else 4 if wc >= 1000 else 3 if wc >= 600 else 2 if wc >= 300 else 1
    h = rec["heading_count"]
    struct_sc = 5 if h >= 8 else 3 if h >= 4 else 1
    n = len(rec["schema_types"])
    schema_sc = 5 if n >= 2 else 3 if n == 1 else 1
    paa_sc = _clamp(_r(1 + 4 * rec["paa_coverage"]), 1, 5)
    return _clamp(_r((wc_sc + struct_sc + schema_sc + paa_sc) / 4), 1, 5)


def _feature(rec):
    return _clamp(_r(1 + 4 * rec["feature_coverage"]), 1, 5)


def _ux_perf_a11y(rec):
    lcp, cls, inp = rec["lcp_ms"], rec["cls"], rec["inp_ms"]
    lcp_sc = 5 if lcp <= 2500 else 3 if lcp <= 4000 else 1
    cls_sc = 5 if cls <= 0.1 else 3 if cls <= 0.25 else 1
    inp_sc = 5 if inp <= 200 else 3 if inp <= 500 else 1
    perf_sc = _r((lcp_sc + cls_sc + inp_sc) / 3)
    c = rec["clicks_to_result"]
    ux_sc = 5 if c <= 2 else 4 if c <= 4 else 3 if c <= 6 else 2 if c <= 8 else 1
    parts = [perf_sc, ux_sc]
    if rec["a11y_score"] is not None:
        parts.append(_clamp(_r(1 + 4 * (rec["a11y_score"] / 100)), 1, 5))
    return _clamp(_r(sum(parts) / len(parts)), 1, 5)


def _trust(rec):
    t = rec["trust_signals"]
    return 5 if t >= 5 else 4 if t == 4 else 3 if t >= 2 else 2 if t == 1 else 1


def score_competitor(rec: dict) -> dict:
    validate(rec)
    scores = {
        "authority": _authority(rec),
        "serp": _serp(rec),
        "content": _content(rec),
        "feature": _feature(rec),
        "ux_perf_a11y": _ux_perf_a11y(rec),
        "trust": _trust(rec),
    }
    strength = round(sum(WEIGHTS[k] * scores[k] for k in WEIGHTS) * 20, 1)
    ordered = sorted(scores.items(), key=lambda kv: kv[1])
    lo, hi = ordered[0][1], ordered[-1][1]
    unverified = []
    if rec["serp_rank"] is None or rec["ai_overview_cited"] is None or rec["serp_features_owned"] is None:
        unverified.append("serp")
    if rec["a11y_score"] is None:
        unverified.append("ux_perf_a11y")
    return {
        "strength": strength,
        "scores": scores,
        "weakest_dimensions": [k for k, v in ordered if v == lo],
        "strongest_dimensions": [k for k, v in ordered if v == hi],
        "unverified_dimensions": unverified,
    }


def _selftest() -> int:
    failures = []
    strong = dict(dr=84, referring_domains=1500, serp_rank=1,
        ai_overview_cited=True, serp_features_owned=2, word_count=490,
        heading_count=6, schema_types=["WebApplication"], paa_coverage=0.3,
        feature_coverage=0.6, lcp_ms=2200, cls=0.05, inp_ms=180,
        a11y_score=78, clicks_to_result=2, trust_signals=4)
    weak = dict(dr=8, referring_domains=2, serp_rank=None,
        ai_overview_cited=False, serp_features_owned=0, word_count=120,
        heading_count=1, schema_types=[], paa_coverage=0.0,
        feature_coverage=0.1, lcp_ms=6000, cls=0.4, inp_ms=800,
        a11y_score=40, clicks_to_result=9, trust_signals=0)

    # SNAPSHOT (mutable; fails loud if the engine is recalibrated)
    got = score_competitor(strong)["strength"]
    if got != 88.2:
        failures.append(f"SNAPSHOT strong strength expected 88.2 got {got}")

    # STRUCTURAL invariants
    r = score_competitor(strong)
    if not (20.0 <= r["strength"] <= 100.0):
        failures.append("strength out of [20,100]")
    if r["scores"][r["weakest_dimensions"][0]] != min(r["scores"].values()):
        failures.append("weakest_dimensions is not the minimum")
    if r["scores"][r["strongest_dimensions"][0]] != max(r["scores"].values()):
        failures.append("strongest_dimensions is not the maximum")

    # GOLDEN-BAD / ruin avoidance
    if score_competitor(weak)["strength"] > 45.0:
        failures.append("weak thin site scored too high")
    if score_competitor(strong)["strength"] < 80.0:
        failures.append("strong incumbent scored too low")

    # fail-closed
    try:
        bad = dict(strong); del bad["dr"]; score_competitor(bad)
        failures.append("missing dr did not raise")
    except ContractError:
        pass
    try:
        bad = dict(strong); bad["dr"] = 150; score_competitor(bad)
        failures.append("dr=150 did not raise")
    except ContractError:
        pass

    # NULL handling: unmeasured SERP + a11y + 0-click auto-compute must score, not raise
    nulls = dict(strong, serp_rank=None, ai_overview_cited=None,
                 serp_features_owned=None, a11y_score=None, clicks_to_result=0)
    rn = score_competitor(nulls)
    if "serp" not in rn["unverified_dimensions"] or "ux_perf_a11y" not in rn["unverified_dimensions"]:
        failures.append("null inputs not flagged in unverified_dimensions")
    if not (20.0 <= rn["strength"] <= 100.0):
        failures.append("null-input record did not score in range")

    if failures:
        print("competitor_strength selftest FAIL:")
        for f in failures:
            print("  -", f)
        return 1
    print("competitor_strength selftest PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json", help="path to a competitor record JSON file")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    if args.json:
        with open(args.json) as fh:
            print(json.dumps(score_competitor(json.load(fh)), indent=2))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
