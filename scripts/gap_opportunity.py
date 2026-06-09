#!/usr/bin/env python3
"""gap_opportunity.py — deterministic gap-opportunity engine.

Ranks a candidate gap (a weakness shared by the top competitors) by how worth
building it is. SINGLE SOURCE OF TRUTH; references/scoring-model.md mirrors it.

    base = (0.35*Demand + 0.30*IncumbentWeakness + 0.20*AIResistance
            + 0.15*Defensibility) * 20                              # 20..100
    opportunity = base * buildability_factor * weakness_gate
        buildability_factor: not_shippable=0.0 high=0.6 medium=0.8 trivial=1.0
        weakness_gate: 0.0 if incumbent_weakness <= 2 else 1.0   (not a consensus gap unless a strict majority of incumbents fail)
    tier: reasoned evidence -> 'hypothesis' (never committable)
          opportunity == 0   -> 'skip'
          >= 70 -> 'build-now'   40..69 -> 'v2'   < 40 -> 'skip'

Fails closed on missing / ill-typed / out-of-range input.

Usage:
    python3 gap_opportunity.py --selftest
    from gap_opportunity import score_gap, rank_gaps
"""
from __future__ import annotations
import argparse, json, sys


class ContractError(ValueError):
    """Raised when a gap record violates the input contract."""


WEIGHTS = {  # v0 UNCALIBRATED — see docs/adr/0002-scoring-weights.md
    "demand": 0.35, "incumbent_weakness": 0.30,
    "ai_resistance": 0.20, "defensibility": 0.15,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9

BUILDABILITY = {"not_shippable": 0.0, "high": 0.6, "medium": 0.8, "trivial": 1.0}
EVIDENCE_TIERS = {"real-measured", "triangulated", "reasoned"}
SCORE_FIELDS = ["demand", "incumbent_weakness", "ai_resistance", "defensibility"]


def validate(gap: dict) -> None:
    if not isinstance(gap, dict):
        raise ContractError("gap must be a dict")
    for f in SCORE_FIELDS:
        if f not in gap:
            raise ContractError(f"missing required field: {f}")
        v = gap[f]
        if isinstance(v, bool) or not isinstance(v, int) or not (1 <= v <= 5):
            raise ContractError(f"{f} must be an int in 1..5, got {v!r}")
    if gap.get("buildability") not in BUILDABILITY:
        raise ContractError(f"buildability must be one of {sorted(BUILDABILITY)}")
    if gap.get("evidence_tier") not in EVIDENCE_TIERS:
        raise ContractError(f"evidence_tier must be one of {sorted(EVIDENCE_TIERS)}")


def score_gap(gap: dict) -> dict:
    validate(gap)
    base = sum(WEIGHTS[k] * gap[k] for k in WEIGHTS) * 20
    bf = BUILDABILITY[gap["buildability"]]
    weakness_gate = 0.0 if gap["incumbent_weakness"] <= 2 else 1.0
    opportunity = round(base * bf * weakness_gate, 1)
    et = gap["evidence_tier"]
    committable = et in {"real-measured", "triangulated"}
    if not committable:
        tier = "hypothesis"
    elif opportunity == 0.0:
        tier = "skip"
    elif opportunity >= 70:
        tier = "build-now"
    elif opportunity >= 40:
        tier = "v2"
    else:
        tier = "skip"
    return {
        "opportunity": opportunity, "tier": tier, "base": round(base, 1),
        "buildability_factor": bf, "committable": committable,
        "evidence_tier": et,
    }


def rank_gaps(gaps: list) -> list:
    scored = [{**g, **score_gap(g)} for g in gaps]
    return sorted(scored, key=lambda g: g["opportunity"], reverse=True)


def _selftest() -> int:
    failures = []
    snap = dict(demand=4, incumbent_weakness=4, ai_resistance=5,
                defensibility=3, buildability="medium",
                evidence_tier="real-measured")
    r = score_gap(snap)
    if r["opportunity"] != 64.8:
        failures.append(f"SNAPSHOT opportunity expected 64.8 got {r['opportunity']}")
    if r["tier"] != "v2":
        failures.append(f"SNAPSHOT tier expected v2 got {r['tier']}")

    # GOLDEN: high demand but not shippable -> 0 -> skip
    g = dict(demand=5, incumbent_weakness=5, ai_resistance=5, defensibility=5,
             buildability="not_shippable", evidence_tier="real-measured")
    if score_gap(g)["tier"] != "skip" or score_gap(g)["opportunity"] != 0.0:
        failures.append("not_shippable gap not forced to skip/0")

    # GOLDEN: all competitors already solved it (incumbent_weakness=1) -> 0
    g = dict(demand=5, incumbent_weakness=1, ai_resistance=5, defensibility=5,
             buildability="trivial", evidence_tier="real-measured")
    if score_gap(g)["opportunity"] != 0.0 or score_gap(g)["tier"] == "build-now":
        failures.append("solved gap (weakness=1) not gated to 0")

    # GOLDEN: a gap a majority of incumbents already solve (iw=2) -> gated to 0
    g = dict(demand=5, incumbent_weakness=2, ai_resistance=5, defensibility=5,
             buildability="trivial", evidence_tier="real-measured")
    if score_gap(g)["opportunity"] != 0.0 or score_gap(g)["tier"] == "build-now":
        failures.append("iw=2 gap not gated to 0 (weakness_gate too loose)")

    # GOLDEN: reasoned evidence -> hypothesis, never committable
    g = dict(demand=5, incumbent_weakness=5, ai_resistance=5, defensibility=5,
             buildability="trivial", evidence_tier="reasoned")
    rr = score_gap(g)
    if rr["tier"] != "hypothesis" or rr["committable"]:
        failures.append("reasoned-tier gap not demoted to hypothesis")

    # fail-closed
    for bad in [
        dict(snap, demand=6),                       # out of 1..5
        dict(snap, buildability="someday"),          # bad enum
        dict(snap, evidence_tier="vibes"),           # bad enum
        {k: v for k, v in snap.items() if k != "demand"},  # missing field
    ]:
        try:
            score_gap(bad); failures.append(f"did not raise for {bad}")
        except ContractError:
            pass

    if failures:
        print("gap_opportunity selftest FAIL:")
        for f in failures:
            print("  -", f)
        return 1
    print("gap_opportunity selftest PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json", help="path to a JSON list of gap records")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    if args.json:
        with open(args.json) as fh:
            print(json.dumps(rank_gaps(json.load(fh)), indent=2))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
