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
the doc in the SAME commit and re-run `--selftest`.

DESIGN DECISIONS THIS ENGINE ENCODES (see docs/adr/):
  0001 Ruin-avoidance first: the false positive (greenlighting a dud) is the
       cardinal error. The score never overrides a gate; "REFUSE" is a legal,
       first-class output (insufficient/ambiguous evidence -> go verify).
  0002 Every threshold/weight below is v0 UNCALIBRATED judgment from a single
       run, NOT calibrated against shipped outcomes. They live in WEIGHTS /
       THRESHOLDS as tunable config, not facts.
  0003 The selftest is a SNAPSHOT (mutable; fails loud on recalibration so a
       human re-blesses the number) PLUS immutable structural + golden-bad
       invariants. "selftest PASS" does NOT mean "Timesheet is the right pick";
       it means the engine is wired correctly and refuses duds.
  0006 Decaying dimensions are meant to be measured against the FUTURE SERP
       (haircut applied at measurement time; the engine consumes the result).
  0008 Soft bands: a hard cutoff inside the input's own measurement noise does
       not auto-kill -- it REFUSEs. Gate-B auto-kill needs margin; the demand
       bonus uses the lower-bound traffic estimate.
  0009 Input integrity / fail-closed: required keys are required (missing key
       raises, never silently passes); thin_site_proof must carry evidence;
       AdSense-restricted verticals are expressible and killed; and
       first_build_eligible requires the high-weight dims at `real-measured`.

GATES vs SCORE:
  Gates are evaluated FIRST, in order (A->B->C->D), cheapest first. A gate
  failure returns status="DROP", the SINGLE gate that fired, and
  opportunity=None -- a dropped tool has no number to launder back in. An
  ambiguous boundary / contradictory input returns status="REFUSE" (also no
  number). Only candidates that pass every gate get an Opportunity number.

CANDIDATE INPUT (one dict per tool):
  tool                    str
  # --- Gate A policy ---
  adsense_restricted      bool  - gambling/alcohol/adult/weapons/drugs etc. (Gate A hard kill)
  # --- Demand ---
  head_bucket             str   - "<100" | "100-1K" | "1K-10K" | "10K-100K" | ">=100K"
  cluster_kw_count        int   - total keywords in the cluster
  cluster_monthly_volume  int   - summed monthly searches across the cluster (Gate D judged on THIS) [REQUIRED]
  incumbent_top3_visits   int   - combined monthly visits of top-3 incumbents (Similarweb)
  distinct_variants       int   - count of distinct non-zero phrasing variants
  # --- Winnability ---
  kd_head                 int   - Ahrefs Keyword Difficulty (0-100) of the head term
  weak_count              int   - WEAK results in the live top-10 (UGC/forum/DR<30/thin/EMD/off-topic)
  native_feature          bool  - a browser/OS/Google onebox feature answers it inline (Gate A kill)
  thin_site_proof         bool  - a thin/low-DR site already ranks the head or long-tail
  thin_site_proof_url     str   - (evidence) the ranking page; REQUIRED for thin_site_proof to be honored
  thin_site_proof_dr      int   - (evidence) that page's DR
  thin_site_proof_keyword str   - (evidence) the keyword it ranks for
  dr_wall_evidenced       bool  - (optional) a verified DR-80+ wall established from real SERP data
  # --- AI-Resistance ---
  artifact_type           str   - "interactive_personalized" | "live_data_tool" | "info_tool" | "static_fact" | "single_fact"
  aio_fire_pct            int   - % of live SERP checks showing an AI Overview (0-100), projected to rank-time (ADR-0006)
  onebox                  bool  - a live calculator/conversion/definition onebox is present (Gate C kill)
  # --- Revenue ---
  cpc                     float - top-of-page bid midpoint (USD), US-filtered
  has_recurring_affiliate bool
  buyer_slice             str   - "strong" | "weak" | "none"
  # --- Build ---
  build_type              str   - "pure_client_single_form" | "client_side_complex" |
                                  "one_stable_api_or_yearly_data" | "paid_or_monthly_stale" | "backend_or_live_feed"
  # --- Evidence + runway (optional) ---
  evidence                dict  - {dimension: "real-measured"|"triangulated"|"reasoned"}; default "reasoned"
  est_time_to_traffic_months  float - (optional) estimated months to meaningful traffic (ADR-0004)
  runway_months           float - (optional) months of runway before a build must earn (ADR-0004)

OUTPUT: {tool, status ("OK"|"VETO"|"REFUSE"|"DROP"), gate_failed (str|None),
         refuse_reasons[], scores{...}, opportunity (float|None),
         veto_dimensions[], flags[], evidence_ok (bool), first_build_eligible}.

Usage:
  python3 score.py candidate.json     # score one candidate or a JSON list
  python3 score.py --selftest         # snapshot + structural + golden-bad invariants
"""
from __future__ import annotations
import json
import math
import sys

# =========================================================================== #
# v0 UNCALIBRATED CONFIG (ADR-0002). These numbers are JUDGMENT from a single
# first-tool run, NOT calibrated against any shipped outcome. Tune them against
# the outcome ledger as real results arrive; do not mistake them for evidence.
# =========================================================================== #
WEIGHTS = {"demand": 0.20, "winnability": 0.25, "ai_resistance": 0.25,
           "revenue": 0.20, "build": 0.10}  # v0 uncalibrated

THRESHOLDS = {
    # Demand
    "cluster_floor_drop": 1000,         # < this  -> Gate D hard DROP
    "finalist_volume_bar": 5000,        # >=floor but < this -> below finalist bar (rankable, not committable)
    "finalist_kw_bar": 100,             # cluster_kw_count below this at commit -> below finalist bar
    "deep_cluster_kw": 400,             # demand +1 bonus: keyword-count threshold
    "deep_cluster_visits": 1_000_000,   # demand +1 bonus: incumbent-traffic threshold
    "deep_cluster_visits_lb": 0.7,      # ADR-0008: require lower-bound (0.7x) estimate to clear the line
    "min_distinct_variants": 3,         # below -> graded demand penalty (NOT a hard floor-to-1; #7)
    "variant_penalty": 2,               # demand points subtracted when below min_distinct_variants
    # Winnability KD bands
    "kd_easy": 5, "kd_good": 10, "kd_contested": 15, "kd_hard": 20,
    "kd_autokill_margin": 26,           # ADR-0008: winnability==1 is a CONFIDENT kill only at KD>=this w/ weak<=1
    "kd_thin_proof_cap": 80,            # #3: cap thin-site winnability floor to 3 when kd_head > this
    "thin_proof_dr_ceiling": 40,        # a "thin-site proof" page above this DR is NOT thin -> not proof (verify-critical)
    "weak_strong": 4, "weak_mod": 3,
    # AI-Resistance
    "aio_info_low": 40, "aio_dead": 85,
    # Revenue CPC bands
    "cpc_high": 3.0, "cpc_mid": 2.0, "cpc_low": 0.5,
    # Sensitivity band (ADR-0008): flag estimated inputs within this fraction of a cutoff
    "sensitivity_margin": 0.20,
}

EVIDENCE_TIERS = ("real-measured", "triangulated", "reasoned")
# first_build_eligible requires these dimensions at real-measured (IRON LAW 1 in code; ADR-0009)
COMMIT_TIER_REQUIRED = ("demand", "winnability", "ai_resistance")

HEAD_BUCKET_BASE = {"<100": 1, "100-1K": 2, "1K-10K": 3, "10K-100K": 4, ">=100K": 5}
HEAD_BUCKET_LB = {"<100": 0, "100-1K": 100, "1K-10K": 1000, "10K-100K": 10000, ">=100K": 100000}

# Fields that MUST be present (read by direct indexing; a missing key raises -- ADR-0009 / #2).
REQUIRED_FIELDS = (
    "tool", "adsense_restricted",
    "head_bucket", "cluster_kw_count", "cluster_monthly_volume",
    "incumbent_top3_visits", "distinct_variants",
    "kd_head", "weak_count", "native_feature", "thin_site_proof",
    "artifact_type", "aio_fire_pct", "onebox",
    "cpc", "has_recurring_affiliate", "buyer_slice", "build_type",
)


class ContractError(ValueError):
    """A candidate is missing a required field or has an out-of-range value."""


def validate(c):
    """Fail closed: a missing/mistyped required key raises instead of silently passing (ADR-0009)."""
    missing = [f for f in REQUIRED_FIELDS if f not in c]
    if missing:
        raise ContractError(f"{c.get('tool', '?')}: missing required field(s): {', '.join(missing)}")
    if c["head_bucket"] not in HEAD_BUCKET_BASE:
        raise ContractError(f"{c['tool']}: bad head_bucket {c['head_bucket']!r}")
    if c["build_type"] not in BUILD_BASE:
        raise ContractError(f"{c['tool']}: bad build_type {c['build_type']!r}")
    ev = c.get("evidence", {})
    for dim, tier in ev.items():
        if tier not in EVIDENCE_TIERS:
            raise ContractError(f"{c['tool']}: bad evidence tier {tier!r} for {dim}")
    # Fail closed on non-finite / wrong-type numerics (ADR-0009): NaN/Inf would slip past every
    # `<` gate comparison (NaN<x is always False; Inf clears every floor) and silently greenlight.
    for f in ("cluster_kw_count", "cluster_monthly_volume", "incumbent_top3_visits",
              "distinct_variants", "kd_head", "weak_count", "aio_fire_pct", "cpc"):
        v = c[f]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ContractError(f"{c['tool']}: {f} must be a finite number, got {v!r}")
    for f in ("thin_site_proof_dr", "est_time_to_traffic_months", "runway_months"):
        v = c.get(f)
        if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)):
            raise ContractError(f"{c['tool']}: {f} must be a finite number or omitted, got {v!r}")
    dr = c.get("thin_site_proof_dr")
    if dr is not None and not (0 <= dr <= 100):
        raise ContractError(f"{c['tool']}: thin_site_proof_dr must be 0..100, got {dr}")


# --------------------------------------------------------------------------- #
# Dimension rules (each deterministic -- same inputs, same score).
# --------------------------------------------------------------------------- #
def demand_score(head_bucket, cluster_kw_count, incumbent_top3_visits, distinct_variants):
    base = HEAD_BUCKET_BASE[head_bucket]
    # Deep-cluster bonus: deep cluster AND real traffic, using the LOWER-BOUND traffic
    # estimate so ±jitter across the 1M line can't toggle a full point (ADR-0008 / #6).
    if (cluster_kw_count >= THRESHOLDS["deep_cluster_kw"] and
            incumbent_top3_visits * THRESHOLDS["deep_cluster_visits_lb"] >= THRESHOLDS["deep_cluster_visits"]):
        base = min(5, base + 1)
    # Thin phrasing set is a graded PENALTY, not a hard floor-to-1 -- the real demand
    # floor is measured cluster volume (Gate D), not a hand-counted integer (#7).
    if distinct_variants < THRESHOLDS["min_distinct_variants"]:
        base = max(1, base - THRESHOLDS["variant_penalty"])
    return base


def winnability_score(kd_head, weak_count, native_feature, thin_site_proof, thin_proof_evidenced):
    if native_feature:
        return 1
    # Thin-site proof floors winnability -- but only when EVIDENCED (URL+DR+keyword; ADR-0009),
    # and capped at 3 when the head is brutally hard (a thin site beating a DR-90+ head is
    # suspect, not proof; #3).
    if thin_site_proof and thin_proof_evidenced:
        if kd_head > THRESHOLDS["kd_thin_proof_cap"]:
            return 3
        return 5 if weak_count >= THRESHOLDS["weak_strong"] else 4
    if kd_head <= THRESHOLDS["kd_easy"]:
        base = 5
    elif kd_head <= THRESHOLDS["kd_good"]:
        base = 4
    elif kd_head <= THRESHOLDS["kd_contested"]:
        base = 3
    elif kd_head <= THRESHOLDS["kd_hard"]:
        base = 2
    else:
        base = 1
    if weak_count >= THRESHOLDS["weak_strong"]:
        base = 5
    elif weak_count >= THRESHOLDS["weak_mod"]:
        base = min(5, base + 1)
    return base


def ai_resistance_score(artifact_type, aio_fire_pct, onebox):
    if onebox:
        return 1
    if artifact_type == "interactive_personalized":
        # Structurally AI-immune (Google can't run your tool inline) -- BUT a very high
        # live AIO means the label is probably wrong; don't ignore it (#3 / ADR-0006).
        return 5 if aio_fire_pct <= THRESHOLDS["aio_dead"] else 2
    if artifact_type == "live_data_tool":
        return 4 if aio_fire_pct <= THRESHOLDS["aio_dead"] else 2
    if artifact_type == "info_tool":
        if aio_fire_pct < THRESHOLDS["aio_info_low"]:
            return 3
        return 2 if aio_fire_pct <= THRESHOLDS["aio_dead"] else 1
    if artifact_type == "static_fact":
        return 2 if aio_fire_pct <= THRESHOLDS["aio_dead"] else 1
    return 1  # single_fact / unrecognized -> dead on arrival


def revenue_score(cpc, has_recurring_affiliate, buyer_slice):
    if cpc >= THRESHOLDS["cpc_high"]:
        base = 4
    elif cpc >= THRESHOLDS["cpc_mid"]:
        base = 3
    elif cpc >= THRESHOLDS["cpc_low"]:
        base = 2
    else:
        base = 1
    if has_recurring_affiliate and buyer_slice == "strong":
        base = min(5, base + 1)
    if cpc < THRESHOLDS["cpc_low"] and not has_recurring_affiliate:
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
# Helpers for gate confidence / evidence / flags.
# --------------------------------------------------------------------------- #
def _thin_proof_evidenced(c):
    """Thin-site proof is honored only when it carries a genuinely THIN (low-DR) ranking page.
    A proof page whose DR is above the thinness ceiling is not a thin site — it is just a strong
    incumbent — so it is NOT proof a new thin site can win (the whole point of the rule). validate()
    has already range-checked thin_site_proof_dr to a finite 0..100, so the only question here is
    'present, and actually thin?' (closes the verify-pass critical where a DR-91 proof greenlit a wall)."""
    if not c["thin_site_proof"] or not c.get("thin_site_proof_url"):
        return False
    dr = c.get("thin_site_proof_dr")
    if dr is None:
        return False
    return dr <= THRESHOLDS["thin_proof_dr_ceiling"]


def _winnability_confident_kill(c, win_score):
    """A winnability==1 is a CONFIDENT Gate-B kill only with margin (ADR-0008 / #4)."""
    if win_score != 1:
        return False
    if c["native_feature"]:
        return True
    if c["kd_head"] >= THRESHOLDS["kd_autokill_margin"] and c["weak_count"] <= 1:
        return True
    if c.get("dr_wall_evidenced"):
        return True
    return False


def _tier(c, dim):
    return c.get("evidence", {}).get(dim, "reasoned")


def _sensitivity_flags(c):
    """Flag estimated inputs sitting within one threshold-step of a verdict change (ADR-0008)."""
    flags = []
    m = THRESHOLDS["sensitivity_margin"]
    # Demand floor proximity, on estimated volume.
    if _tier(c, "demand") != "real-measured":
        floor = THRESHOLDS["cluster_floor_drop"]
        if floor <= c["cluster_monthly_volume"] < floor * (1 + m):
            flags.append("sensitivity: cluster volume hugs the Gate-D floor on estimated data -- verify")
        v = THRESHOLDS["deep_cluster_visits"]
        if v * (1 - m) <= c["incumbent_top3_visits"] <= v * (1 + m):
            flags.append("sensitivity: incumbent traffic straddles the demand-bonus line on an estimate -- verify")
    # KD noise band near the contested/hard boundary, on estimated winnability.
    if _tier(c, "winnability") != "real-measured":
        if THRESHOLDS["kd_contested"] <= c["kd_head"] < THRESHOLDS["kd_autokill_margin"] \
                and not (c["thin_site_proof"] and _thin_proof_evidenced(c)):
            flags.append("sensitivity: head KD in the noise band -- pull more SERP/thin-site evidence")
    return flags


# --------------------------------------------------------------------------- #
# Gate / refuse evaluation -- in order, cheapest first. Cite the SINGLE cause.
# --------------------------------------------------------------------------- #
def evaluate(c, scores):
    """Return (status, gate_failed, refuse_reasons). status in DROP/REFUSE/None(pass)."""
    # GATE A -- policy / native-feature hard kills.
    if c["adsense_restricted"]:
        return "DROP", "Gate A — AdSense-restricted vertical (gambling/alcohol/adult/etc.): unmonetizable", []
    if c["native_feature"]:
        return "DROP", "Gate A — a browser/OS/Google native feature answers it inline", []
    # GATE B -- winnability (confident kill vs ambiguous band).
    if scores["winnability"] == 1:
        if _winnability_confident_kill(c, scores["winnability"]):
            if c.get("dr_wall_evidenced"):
                return "DROP", "Gate B — unwinnable: verified DR-80+ wall, no thin-site proof", []
            return "DROP", (f"Gate B — unwinnable: head KD {c['kd_head']} (>= {THRESHOLDS['kd_autokill_margin']}) "
                            "with <=1 weak result and no thin-site proof"), []
        return "REFUSE", None, [
            f"winnability ambiguous: head KD {c['kd_head']} with weak_count {c['weak_count']} is past "
            f"the kill line but lacks auto-kill margin (need KD >= {THRESHOLDS['kd_autokill_margin']} "
            "with <=1 weak result, or an evidenced DR wall) and has no evidenced thin-site proof — "
            "pull more SERP/thin-site evidence before deciding"]
    # GATE C -- AI Overview / onebox / dead-on-arrival AI.
    if c["onebox"]:
        return "DROP", "Gate C — a live calculator/conversion/definition onebox answers it inline", []
    if scores["ai_resistance"] == 1:
        return "DROP", "Gate C — dead on arrival: AI answers this query inline (AIO/single-fact)", []
    # Cross-field contradiction -- head bucket implies more volume than the whole cluster (#6).
    lb = HEAD_BUCKET_LB[c["head_bucket"]]
    if c["cluster_monthly_volume"] < lb:
        return "REFUSE", None, [
            f"input contradiction: head_bucket {c['head_bucket']!r} implies >= {lb}/mo but cluster is "
            f"{c['cluster_monthly_volume']}/mo (cluster cannot be below the head) — re-measure"]
    # GATE D -- real demand floor (measured volume only; NOT the variant count, NOT demand==1).
    if c["cluster_monthly_volume"] < THRESHOLDS["cluster_floor_drop"]:
        return "DROP", f"Gate D — cluster below the ~{THRESHOLDS['cluster_floor_drop']}/mo demand floor", []
    return None, None, []


def score_candidate(c):
    validate(c)
    thin_ev = _thin_proof_evidenced(c)
    scores = {
        "demand": demand_score(c["head_bucket"], c["cluster_kw_count"],
                               c["incumbent_top3_visits"], c["distinct_variants"]),
        "winnability": winnability_score(c["kd_head"], c["weak_count"],
                                         c["native_feature"], c["thin_site_proof"], thin_ev),
        "ai_resistance": ai_resistance_score(c["artifact_type"], c["aio_fire_pct"], c["onebox"]),
        "revenue": revenue_score(c["cpc"], c["has_recurring_affiliate"], c["buyer_slice"]),
        "build": build_score(c["build_type"]),
    }
    status, gate, refuse = evaluate(c, scores)

    flags = []
    if c["thin_site_proof"] and not thin_ev:
        flags.append("thin_site_proof asserted WITHOUT evidence (url+DR+keyword) — treated as unproven")

    if status in ("DROP", "REFUSE"):
        return {
            "tool": c["tool"], "status": status,
            "gate_failed": gate, "refuse_reasons": refuse,
            "scores": scores, "opportunity": None,   # dropped/refused tools carry NO number
            "veto_dimensions": [], "flags": flags,
            "evidence_ok": False, "first_build_eligible": False,
        }

    # Passed all gates. Among survivors only Demand/Revenue/Build can still be 1 (a VETO);
    # winnability==1 and ai_resistance==1 were gated above.
    vetoes = [k for k, v in scores.items() if v == 1]

    # Evidence sufficiency for COMMIT (ADR-0009): high-weight dims must be real-measured.
    weak_tiers = [d for d in COMMIT_TIER_REQUIRED if _tier(c, d) != "real-measured"]
    evidence_ok = not weak_tiers
    if weak_tiers:
        flags.append("evidence below real-measured on: " + ", ".join(weak_tiers)
                     + " — rankable but NOT committable until Stage 5 verifies")

    # Finalist bar (ADR-0008 / #8): rankable, but not committable below the bar.
    below_finalist = (c["cluster_monthly_volume"] < THRESHOLDS["finalist_volume_bar"]
                      or c["cluster_kw_count"] < THRESHOLDS["finalist_kw_bar"])
    if below_finalist:
        flags.append(f"below finalist bar (< {THRESHOLDS['finalist_volume_bar']}/mo or "
                     f"< {THRESHOLDS['finalist_kw_bar']} kw) — fast-follow, not an opener")

    flags.extend(_sensitivity_flags(c))

    # Time-to-rank vs runway (ADR-0004): a winnable-but-slow tool starves the runway.
    time_block = False
    ett = c.get("est_time_to_traffic_months")
    run = c.get("runway_months")
    if ett is not None and run is not None and ett > run:
        time_block = True
        flags.append(f"time-to-traffic ~{ett}mo exceeds runway {run}mo — fast-follow, not the opener")

    status = "VETO" if vetoes else "OK"
    first_build_eligible = (status == "OK" and evidence_ok and not below_finalist
                            and not time_block and not any(f.startswith("sensitivity:") for f in flags))
    return {
        "tool": c["tool"], "status": status,
        "gate_failed": None, "refuse_reasons": [],
        "scores": scores, "opportunity": opportunity(scores),
        "veto_dimensions": vetoes, "flags": flags,
        "evidence_ok": evidence_ok, "first_build_eligible": first_build_eligible,
    }


RANK_ORDER = {"OK": 3, "VETO": 2, "REFUSE": 1, "DROP": 0}


def rank(cands):
    """OK > VETO > REFUSE > DROP; then higher Opportunity; then tool name (deterministic tie-break, #5)."""
    scored = [score_candidate(c) for c in cands]
    scored.sort(key=lambda r: (-RANK_ORDER[r["status"]],
                               -(r["opportunity"] if r["opportunity"] is not None else -1.0),
                               r["tool"]))
    return scored


# =========================================================================== #
# Golden regression test (ADR-0003): SNAPSHOT (mutable, fails loud) +
# immutable STRUCTURAL invariants + GOLDEN-BAD ruin-avoidance fixtures.
# A failing SNAPSHOT after a deliberate recalibration is EXPECTED -- re-bless the
# number. A failing INVARIANT or GOLDEN-BAD case means the engine is broken.
# =========================================================================== #
def _real(*dims):
    return {d: "real-measured" for d in dims}


GOLDEN = [
    {"tool": "Timesheet / Time-Card Calculator", "adsense_restricted": False,
     "head_bucket": "10K-100K", "cluster_kw_count": 424, "cluster_monthly_volume": 50000,
     "incumbent_top3_visits": 2_000_000, "distinct_variants": 40,
     "kd_head": 70, "weak_count": 1, "native_feature": False, "thin_site_proof": True,
     "thin_site_proof_url": "timecardcalculatorgeek.com", "thin_site_proof_dr": 15,
     "thin_site_proof_keyword": "time card calculator",
     "artifact_type": "interactive_personalized", "aio_fire_pct": 5, "onebox": False,
     "cpc": 3.0, "has_recurring_affiliate": True, "buyer_slice": "weak",
     "build_type": "client_side_complex",
     "evidence": _real("demand", "winnability", "ai_resistance")},
    {"tool": "Email Signature Generator", "adsense_restricted": False,
     "head_bucket": "10K-100K", "cluster_kw_count": 542, "cluster_monthly_volume": 30000,
     "incumbent_top3_visits": 168_000, "distinct_variants": 30,
     "kd_head": 60, "weak_count": 1, "native_feature": False, "thin_site_proof": True,
     "thin_site_proof_url": "emailsignaturerescue.com", "thin_site_proof_dr": 22,
     "thin_site_proof_keyword": "email signature generator",
     "artifact_type": "interactive_personalized", "aio_fire_pct": 5, "onebox": False,
     "cpc": 3.0, "has_recurring_affiliate": True, "buyer_slice": "weak",
     "build_type": "client_side_complex",
     "evidence": _real("demand", "winnability", "ai_resistance")},
    {"tool": "Freelance Rate Calculator", "adsense_restricted": False,
     "head_bucket": "100-1K", "cluster_kw_count": 13, "cluster_monthly_volume": 400,
     "incumbent_top3_visits": 500_000, "distinct_variants": 13,
     "kd_head": 14, "weak_count": 2, "native_feature": False, "thin_site_proof": False,
     "artifact_type": "interactive_personalized", "aio_fire_pct": 5, "onebox": False,
     "cpc": 4.0, "has_recurring_affiliate": True, "buyer_slice": "strong",
     "build_type": "pure_client_single_form",
     "evidence": _real("demand", "winnability", "ai_resistance")},
    {"tool": "QR Code Generator", "adsense_restricted": False,
     "head_bucket": ">=100K", "cluster_kw_count": 10334, "cluster_monthly_volume": 200000,
     "incumbent_top3_visits": 9_400_000, "distinct_variants": 200,
     "kd_head": 75, "weak_count": 0, "native_feature": True, "thin_site_proof": False,
     "artifact_type": "interactive_personalized", "aio_fire_pct": 5, "onebox": False,
     "cpc": 2.0, "has_recurring_affiliate": False, "buyer_slice": "none",
     "build_type": "pure_client_single_form",
     "evidence": _real("demand", "winnability", "ai_resistance")},
    {"tool": "TikTok Shop Fee Calculator", "adsense_restricted": False,
     "head_bucket": "<100", "cluster_kw_count": 4, "cluster_monthly_volume": 100,
     "incumbent_top3_visits": 50_000, "distinct_variants": 4,
     "kd_head": 3, "weak_count": 5, "native_feature": False, "thin_site_proof": True,
     "thin_site_proof_url": "tiktokfeecalc.example", "thin_site_proof_dr": 8,
     "thin_site_proof_keyword": "tiktok shop fee calculator",
     "artifact_type": "live_data_tool", "aio_fire_pct": 5, "onebox": False,
     "cpc": 3.0, "has_recurring_affiliate": False, "buyer_slice": "weak",
     "build_type": "pure_client_single_form",
     "evidence": _real("demand", "winnability", "ai_resistance")},
]

# SNAPSHOT (mutable; ADR-0003): the v0-weights numbers. A change here after a
# deliberate recalibration is EXPECTED -- update the number and note why.
SNAPSHOT = {
    "Timesheet / Time-Card Calculator": 89.0,
    "Email Signature Generator": 85.0,
}

# Each golden-bad case asserts the engine REFUSES a dud. These are IMMUTABLE.
GOLDEN_BAD = [
    {"name": "restricted-vertical greenlight (CRITICAL)", "expect": ("DROP", "Gate A"),
     "cand": {"tool": "Gambling Odds Calculator", "adsense_restricted": True,
              "head_bucket": "10K-100K", "cluster_kw_count": 500, "cluster_monthly_volume": 40000,
              "incumbent_top3_visits": 2_000_000, "distinct_variants": 30,
              "kd_head": 8, "weak_count": 4, "native_feature": False, "thin_site_proof": False,
              "artifact_type": "interactive_personalized", "aio_fire_pct": 5, "onebox": False,
              "cpc": 6.0, "has_recurring_affiliate": True, "buyer_slice": "strong",
              "build_type": "pure_client_single_form"}},
    {"name": "thin_site_proof gamed (bare bool over a DR-90 wall)", "expect": ("DROP", "Gate B"),
     "cand": {"tool": "Vanity Wall Tool", "adsense_restricted": False,
              "head_bucket": "1K-10K", "cluster_kw_count": 120, "cluster_monthly_volume": 8000,
              "incumbent_top3_visits": 3_000_000, "distinct_variants": 10,
              "kd_head": 88, "weak_count": 0, "native_feature": False, "thin_site_proof": True,
              "artifact_type": "interactive_personalized", "aio_fire_pct": 5, "onebox": False,
              "cpc": 3.0, "has_recurring_affiliate": False, "buyer_slice": "weak",
              "build_type": "pure_client_single_form"}},
    {"name": "evidenced thin-proof that is NOT thin (DR-91 page over a KD-82 head)", "expect": ("DROP", "Gate B"),
     "cand": {"tool": "Strong-Site-Mislabeled-As-Thin", "adsense_restricted": False,
              "head_bucket": "1K-10K", "cluster_kw_count": 150, "cluster_monthly_volume": 8000,
              "incumbent_top3_visits": 3_000_000, "distinct_variants": 12,
              "kd_head": 82, "weak_count": 0, "native_feature": False, "thin_site_proof": True,
              "thin_site_proof_url": "bigbrand.com/tool", "thin_site_proof_dr": 91,
              "thin_site_proof_keyword": "the keyword",
              "artifact_type": "interactive_personalized", "aio_fire_pct": 5, "onebox": False,
              "cpc": 3.0, "has_recurring_affiliate": False, "buyer_slice": "weak",
              "build_type": "pure_client_single_form"}},
    {"name": "KD noise band -> REFUSE, not auto-kill", "expect": ("REFUSE", None),
     "cand": {"tool": "Mid-Difficulty Tool", "adsense_restricted": False,
              "head_bucket": "1K-10K", "cluster_kw_count": 150, "cluster_monthly_volume": 8000,
              "incumbent_top3_visits": 400_000, "distinct_variants": 12,
              "kd_head": 22, "weak_count": 2, "native_feature": False, "thin_site_proof": False,
              "artifact_type": "interactive_personalized", "aio_fire_pct": 5, "onebox": False,
              "cpc": 3.0, "has_recurring_affiliate": False, "buyer_slice": "weak",
              "build_type": "pure_client_single_form"}},
    {"name": "AI dead-on-arrival -> Gate C drop", "expect": ("DROP", "Gate C"),
     "cand": {"tool": "Capital Of France Lookup", "adsense_restricted": False,
              "head_bucket": "10K-100K", "cluster_kw_count": 200, "cluster_monthly_volume": 9000,
              "incumbent_top3_visits": 500_000, "distinct_variants": 8,
              "kd_head": 10, "weak_count": 4, "native_feature": False, "thin_site_proof": False,
              "artifact_type": "single_fact", "aio_fire_pct": 95, "onebox": False,
              "cpc": 1.0, "has_recurring_affiliate": False, "buyer_slice": "none",
              "build_type": "pure_client_single_form"}},
    {"name": "impossible cross-field (>=100K head, 1k cluster) -> REFUSE", "expect": ("REFUSE", None),
     "cand": {"tool": "Contradictory Tool", "adsense_restricted": False,
              "head_bucket": ">=100K", "cluster_kw_count": 300, "cluster_monthly_volume": 1000,
              "incumbent_top3_visits": 2_000_000, "distinct_variants": 20,
              "kd_head": 8, "weak_count": 4, "native_feature": False, "thin_site_proof": False,
              "artifact_type": "interactive_personalized", "aio_fire_pct": 5, "onebox": False,
              "cpc": 3.0, "has_recurring_affiliate": False, "buyer_slice": "weak",
              "build_type": "pure_client_single_form"}},
]


def _selftest():
    failures = []
    results = {r["tool"]: r for r in (score_candidate(c) for c in GOLDEN)}
    ranked = rank(GOLDEN)

    # --- SNAPSHOT (mutable) ---
    for tool, want in SNAPSHOT.items():
        got = results[tool]["opportunity"]
        if got != want:
            failures.append(f"[snapshot] {tool}: opportunity {got} != {want} "
                            "(EXPECTED to change on recalibration -- if deliberate, update SNAPSHOT)")

    # --- STRUCTURAL invariants (immutable) ---
    def drop_at(tool, gate):
        r = results[tool]
        if r["status"] != "DROP" or not (r["gate_failed"] or "").startswith(gate):
            failures.append(f"[invariant] {tool}: expected DROP at {gate}, got {r['status']} / {r['gate_failed']}")
        if r["opportunity"] is not None:
            failures.append(f"[invariant] {tool}: DROP must carry no Opportunity number, got {r['opportunity']}")
    drop_at("QR Code Generator", "Gate A")
    drop_at("Freelance Rate Calculator", "Gate D")
    drop_at("TikTok Shop Fee Calculator", "Gate D")

    win = ranked[0]
    if win["tool"] != "Timesheet / Time-Card Calculator" or win["status"] != "OK":
        failures.append(f"[invariant] winner is {win['tool']!r} ({win['status']}), expected Timesheet (OK)")
    if not win["first_build_eligible"]:
        failures.append("[invariant] Timesheet should be first_build_eligible (real-measured evidence, no flags)")
    # The all-rounder outranks the highest-on-one-axis tool.
    if results["Timesheet / Time-Card Calculator"]["opportunity"] <= results["Email Signature Generator"]["opportunity"]:
        failures.append("[invariant] all-rounder Timesheet should outrank Email Signature")
    # Deterministic ranking: re-rank a shuffled copy, order must be identical (#5).
    if [r["tool"] for r in rank(list(reversed(GOLDEN)))] != [r["tool"] for r in ranked]:
        failures.append("[invariant] ranking is not order-independent (deterministic tie-break missing)")

    # --- GOLDEN-BAD ruin-avoidance fixtures (immutable) ---
    for case in GOLDEN_BAD:
        r = score_candidate(case["cand"])
        exp_status, exp_gate = case["expect"]
        ok = r["status"] == exp_status and (exp_gate is None or (r["gate_failed"] or "").startswith(exp_gate))
        if not ok:
            failures.append(f"[golden-bad] {case['name']}: expected {exp_status}/{exp_gate}, "
                            f"got {r['status']}/{r['gate_failed']}")
        if r["opportunity"] is not None:
            failures.append(f"[golden-bad] {case['name']}: must carry no Opportunity number")

    # --- FAIL-CLOSED: a missing required key must RAISE, not silently pass (#2) ---
    bad = dict(GOLDEN[0]); bad.pop("cluster_monthly_volume")
    try:
        score_candidate(bad)
        failures.append("[fail-closed] missing cluster_monthly_volume did NOT raise (silent pass)")
    except ContractError:
        pass
    # thin_site_proof_dr is range-validated, and a non-thin DR is not honored as proof.
    for badval, why in ((-5, "negative DR"), (150, "DR>100")):
        b = dict(GOLDEN[0]); b["thin_site_proof_dr"] = badval
        try:
            score_candidate(b)
            failures.append(f"[fail-closed] thin_site_proof_dr={badval} ({why}) did NOT raise")
        except ContractError:
            pass
    # NaN/Inf volume must not bypass the gates (NaN<x and Inf<floor would silently pass).
    for badval in (float("nan"), float("inf")):
        b = dict(GOLDEN[0]); b["cluster_monthly_volume"] = badval
        try:
            score_candidate(b)
            failures.append(f"[fail-closed] cluster_monthly_volume={badval} did NOT raise")
        except ContractError:
            pass

    # --- Print report ---
    print("=== pick-next-tool selftest (snapshot + invariants + golden-bad) ===")
    for r in ranked:
        opp = "  —  " if r["opportunity"] is None else f"{r['opportunity']:>5}"
        tag = (f"  DROP({r['gate_failed']})" if r["status"] == "DROP" else
               f"  REFUSE" if r["status"] == "REFUSE" else
               f"  VETO({','.join(r['veto_dimensions'])})" if r["status"] == "VETO" else
               ("  [committable]" if r["first_build_eligible"] else "  [rankable]"))
        print(f"  {opp}  {r['tool']:<36} {r['scores']}{tag}")
    print()
    if failures:
        print("FAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("PASS: snapshot holds (Timesheet=89), structural invariants hold (QR/Freelance/TikTok drop at "
          "their gate, no number; deterministic order), the golden-bad duds are all refused, and the "
          "contract fails closed on a missing key.")
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
