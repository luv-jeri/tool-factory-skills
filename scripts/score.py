#!/usr/bin/env python3
"""
Deterministic scoring + gate engine for the `pick-next-tool` skill.

WHY THIS EXISTS
---------------
Three different agents once scored the same tool portfolio and picked three
different winners. The cause was never the data -- it was subjective 1-5
"vibes" that drifted from run to run. This module makes both the GATES and the
SCORES mechanical: given the same measured inputs, every agent gets the same
verdict. Eyeballing a score, or quoting an Opportunity number you did not
actually run through this engine, is a skill failure -- call this and paste its
literal output.

It implements references/scoring-model.md. If you change a rule here, change
the doc in the SAME commit and re-run `--selftest`. The selftest IS the golden
regression test: it replays the real first-tool decision (07-FIRST-TOOL-DECISION)
and MUST reproduce "Timesheet = 89, build first", with QR / Freelance / TikTok
DROPPED at their gate (no Opportunity number). If it fails, the engine is
broken -- do not trust its output.

GATES vs SCORE (the key design point):
  This engine evaluates the kill-gates FIRST, from the inputs it can see, and
  for any gate failure returns status="DROP", the SINGLE gate that fired, and
  opportunity=None. It computes an Opportunity number ONLY for candidates that
  pass every gate -- so a dropped tool has no number to launder back in, and
  the agent cites exactly one gate (never a merged "native + wall" clause).

CANDIDATE INPUT (one dict per tool; all fields required):
  tool                    str
  # --- Demand ---
  head_bucket             str   - "<100" | "100-1K" | "1K-10K" | "10K-100K" | ">=100K"
  cluster_kw_count        int   - total keywords in the cluster
  cluster_monthly_volume  int   - summed monthly searches across the whole cluster (Gate D is judged on THIS)
  incumbent_top3_visits   int   - combined monthly visits of top-3 incumbents (Similarweb)
  distinct_variants       int   - count of distinct non-zero phrasing variants
  # --- Winnability ---
  kd_head                 int   - Ahrefs Keyword Difficulty (0-100) of the head term
  weak_count              int   - WEAK results in the live top-10 (UGC/forum/DR<30/thin/EMD/off-topic)
  native_feature          bool  - a browser/OS/Google onebox feature answers it inline (Gate A kill)
  thin_site_proof         bool  - a thin/low-DR/one-page site already ranks the head or long-tail
  # --- AI-Resistance ---
  artifact_type           str   - "interactive_personalized" | "live_data_tool" | "info_tool" | "static_fact" | "single_fact"
  aio_fire_pct            int   - % of live SERP checks showing an AI Overview (0-100)
  onebox                  bool  - a live calculator/conversion/definition onebox is present (Gate C kill)
  # --- Revenue ---
  cpc                     float - top-of-page bid midpoint (USD), US-filtered
  has_recurring_affiliate bool
  buyer_slice             str   - "strong" | "weak" | "none"
  # --- Build ---
  build_type              str   - "pure_client_single_form" | "client_side_complex" |
                                  "one_stable_api_or_yearly_data" | "paid_or_monthly_stale" | "backend_or_live_feed"

OUTPUT: {tool, status ("OK"|"VETO"|"DROP"), gate_failed (str|None), scores{...},
         opportunity (float|None), veto_dimensions[], first_build_eligible}.

Usage:
  python3 score.py candidate.json     # score one candidate or a JSON list
  python3 score.py --selftest         # run the golden regression test
"""
from __future__ import annotations
import json
import sys

WEIGHTS = {"demand": 0.20, "winnability": 0.25, "ai_resistance": 0.25,
           "revenue": 0.20, "build": 0.10}

# --------------------------------------------------------------------------- #
# Dimension rules (each deterministic — same inputs, same score).
# --------------------------------------------------------------------------- #
HEAD_BUCKET_BASE = {"<100": 1, "100-1K": 2, "1K-10K": 3, "10K-100K": 4, ">=100K": 5}


def demand_score(head_bucket, cluster_kw_count, incumbent_top3_visits, distinct_variants):
    base = HEAD_BUCKET_BASE[head_bucket]
    if cluster_kw_count >= 400 and incumbent_top3_visits >= 1_000_000:
        base = min(5, base + 1)          # deep cluster AND real traffic = a destination
    if distinct_variants < 3:
        base = min(base, 1)              # not a real cluster
    return base


def winnability_score(kd_head, weak_count, native_feature, thin_site_proof):
    if native_feature:
        return 1
    if thin_site_proof:                  # you buy the long-tail; a thin site ranking proves it
        return 5 if weak_count >= 4 else 4
    if kd_head <= 5:
        base = 5
    elif kd_head <= 10:
        base = 4
    elif kd_head <= 15:
        base = 3
    elif kd_head <= 20:
        base = 2
    else:
        base = 1
    if weak_count >= 4:
        base = 5
    elif weak_count >= 3:
        base = min(5, base + 1)
    return base


def ai_resistance_score(artifact_type, aio_fire_pct, onebox):
    if onebox:
        return 1
    if artifact_type == "interactive_personalized":
        return 5
    if artifact_type == "live_data_tool":
        return 4
    if artifact_type == "info_tool":
        if aio_fire_pct < 40:
            return 3
        return 2 if aio_fire_pct <= 85 else 1
    if artifact_type == "static_fact":
        return 2 if aio_fire_pct <= 85 else 1
    return 1


def revenue_score(cpc, has_recurring_affiliate, buyer_slice):
    if cpc >= 3:
        base = 4
    elif cpc >= 2:
        base = 3
    elif cpc >= 0.5:
        base = 2
    else:
        base = 1
    if has_recurring_affiliate and buyer_slice == "strong":
        base = min(5, base + 1)
    if cpc < 0.5 and not has_recurring_affiliate:
        base = 1
    return base


BUILD_BASE = {
    "pure_client_single_form": 5,
    "client_side_complex": 4,
    "one_stable_api_or_yearly_data": 3,
    "paid_or_monthly_stale": 2,
    "backend_or_live_feed": 1,
}


def build_score(build_type):
    return BUILD_BASE[build_type]


def opportunity(scores):
    return round(sum(WEIGHTS[k] * scores[k] for k in WEIGHTS) * 20, 1)


# --------------------------------------------------------------------------- #
# Gates — evaluated IN ORDER, cheapest first, cite the SINGLE gate that fires.
# A drop returns no Opportunity number (you cannot launder a dropped tool back).
# --------------------------------------------------------------------------- #
def evaluate_gates(c, scores):
    if c["native_feature"]:
        return "A — a browser/OS/Google native feature answers it inline"
    if scores["winnability"] == 1:
        return "B — unwinnable: DR-80+ wall with no thin-site proof"
    if c["onebox"]:
        return "C — a live AI Overview / onebox answers it inline"
    cluster = c.get("cluster_monthly_volume")
    if (cluster is not None and cluster < 1000) or scores["demand"] == 1:
        return "D — demand below the ~1,000/mo cluster floor"
    return None


def score_candidate(c):
    scores = {
        "demand": demand_score(c["head_bucket"], c["cluster_kw_count"],
                               c["incumbent_top3_visits"], c["distinct_variants"]),
        "winnability": winnability_score(c["kd_head"], c["weak_count"],
                                         c["native_feature"], c["thin_site_proof"]),
        "ai_resistance": ai_resistance_score(c["artifact_type"], c["aio_fire_pct"],
                                             c["onebox"]),
        "revenue": revenue_score(c["cpc"], c["has_recurring_affiliate"],
                                 c["buyer_slice"]),
        "build": build_score(c["build_type"]),
    }
    gate = evaluate_gates(c, scores)
    if gate is not None:
        return {
            "tool": c.get("tool", "?"),
            "status": "DROP",
            "gate_failed": "Gate " + gate,
            "scores": scores,              # shown as evidence; NOT a selectable result
            "opportunity": None,           # dropped tools carry NO number
            "veto_dimensions": [],
            "first_build_eligible": False,
        }
    # Passed all gates. Among survivors only Revenue/Build can still be 1 (a VETO).
    vetoes = [k for k, v in scores.items() if v == 1]
    return {
        "tool": c.get("tool", "?"),
        "status": "VETO" if vetoes else "OK",
        "gate_failed": None,
        "scores": scores,
        "opportunity": opportunity(scores),
        "veto_dimensions": vetoes,
        "first_build_eligible": not vetoes,
    }


RANK_ORDER = {"OK": 2, "VETO": 1, "DROP": 0}


def rank(cands):
    """OK (first-build-eligible) ranks above VETO above DROP; then by Opportunity."""
    scored = [score_candidate(c) for c in cands]
    scored.sort(key=lambda r: (RANK_ORDER[r["status"]],
                               r["opportunity"] if r["opportunity"] is not None else -1),
                reverse=True)
    return scored


# --------------------------------------------------------------------------- #
# Golden regression test — replays the real 07-FIRST-TOOL-DECISION run.
# --------------------------------------------------------------------------- #
GOLDEN = [
    {"tool": "Timesheet / Time-Card Calculator",
     "head_bucket": "10K-100K", "cluster_kw_count": 424, "cluster_monthly_volume": 50000,
     "incumbent_top3_visits": 2_000_000, "distinct_variants": 40,
     "kd_head": 70, "weak_count": 1, "native_feature": False, "thin_site_proof": True,
     "artifact_type": "interactive_personalized", "aio_fire_pct": 5, "onebox": False,
     "cpc": 3.0, "has_recurring_affiliate": True, "buyer_slice": "weak",
     "build_type": "client_side_complex"},
    {"tool": "Email Signature Generator",
     "head_bucket": "10K-100K", "cluster_kw_count": 542, "cluster_monthly_volume": 30000,
     "incumbent_top3_visits": 168_000, "distinct_variants": 30,
     "kd_head": 60, "weak_count": 1, "native_feature": False, "thin_site_proof": True,
     "artifact_type": "interactive_personalized", "aio_fire_pct": 5, "onebox": False,
     "cpc": 3.0, "has_recurring_affiliate": True, "buyer_slice": "weak",
     "build_type": "client_side_complex"},
    {"tool": "Freelance Rate Calculator",
     "head_bucket": "100-1K", "cluster_kw_count": 13, "cluster_monthly_volume": 400,
     "incumbent_top3_visits": 500_000, "distinct_variants": 13,
     "kd_head": 14, "weak_count": 2, "native_feature": False, "thin_site_proof": False,
     "artifact_type": "interactive_personalized", "aio_fire_pct": 5, "onebox": False,
     "cpc": 4.0, "has_recurring_affiliate": True, "buyer_slice": "strong",
     "build_type": "pure_client_single_form"},
    {"tool": "QR Code Generator",
     "head_bucket": ">=100K", "cluster_kw_count": 10334, "cluster_monthly_volume": 200000,
     "incumbent_top3_visits": 9_400_000, "distinct_variants": 200,
     "kd_head": 75, "weak_count": 0, "native_feature": True, "thin_site_proof": False,
     "artifact_type": "interactive_personalized", "aio_fire_pct": 5, "onebox": False,
     "cpc": 2.0, "has_recurring_affiliate": False, "buyer_slice": "none",
     "build_type": "pure_client_single_form"},
    {"tool": "TikTok Shop Fee Calculator",
     "head_bucket": "<100", "cluster_kw_count": 4, "cluster_monthly_volume": 100,
     "incumbent_top3_visits": 50_000, "distinct_variants": 4,
     "kd_head": 3, "weak_count": 5, "native_feature": False, "thin_site_proof": True,
     "artifact_type": "live_data_tool", "aio_fire_pct": 5, "onebox": False,
     "cpc": 3.0, "has_recurring_affiliate": False, "buyer_slice": "weak",
     "build_type": "pure_client_single_form"},
]

GOLDEN_EXPECT = {
    "Timesheet / Time-Card Calculator": {"status": "OK", "opportunity": 89.0},
    "Email Signature Generator":        {"status": "OK", "opportunity": 85.0},
    "Freelance Rate Calculator":        {"status": "DROP", "gate": "Gate D"},
    "QR Code Generator":                {"status": "DROP", "gate": "Gate A"},
    "TikTok Shop Fee Calculator":       {"status": "DROP", "gate": "Gate D"},
}


def _selftest():
    results = {r["tool"]: r for r in (score_candidate(c) for c in GOLDEN)}
    ranked = rank(GOLDEN)
    failures = []

    for tool, exp in GOLDEN_EXPECT.items():
        got = results[tool]
        if got["status"] != exp["status"]:
            failures.append(f"{tool}: status {got['status']} != expected {exp['status']}")
        if "opportunity" in exp and got["opportunity"] != exp["opportunity"]:
            failures.append(f"{tool}: opportunity {got['opportunity']} != expected {exp['opportunity']}")
        if exp.get("gate") and (got["gate_failed"] is None or not got["gate_failed"].startswith(exp["gate"])):
            failures.append(f"{tool}: expected {exp['gate']} drop, got {got['gate_failed']}")

    winner = ranked[0]
    if winner["tool"] != "Timesheet / Time-Card Calculator" or winner["status"] != "OK":
        failures.append(f"winner is {winner['tool']!r} ({winner['status']}), expected Timesheet (OK)")
    # A dropped tool must never carry a number to launder back in.
    for r in ranked:
        if r["status"] == "DROP" and r["opportunity"] is not None:
            failures.append(f"{r['tool']}: DROP but has opportunity {r['opportunity']} (should be None)")

    print("=== pick-next-tool golden regression test ===")
    for r in ranked:
        opp = "  —  " if r["opportunity"] is None else f"{r['opportunity']:>5}"
        tag = f"  DROP({r['gate_failed']})" if r["status"] == "DROP" else (
            f"  VETO({','.join(r['veto_dimensions'])})" if r["status"] == "VETO" else "")
        print(f"  {opp}  {r['tool']:<36} {r['scores']}{tag}")
    print()
    if failures:
        print("FAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("PASS: engine reproduces the canonical 07-FIRST-TOOL-DECISION outcome "
          "(Timesheet=89 build-first; QR/Freelance/TikTok dropped at their gate, no number).")
    return 0


def _main(argv):
    if len(argv) == 2 and argv[1] == "--selftest":
        return _selftest()
    if len(argv) == 2:
        with open(argv[1]) as fh:
            data = json.load(fh)
        cands = data if isinstance(data, list) else [data]
        print(json.dumps(rank(cands), indent=2))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
