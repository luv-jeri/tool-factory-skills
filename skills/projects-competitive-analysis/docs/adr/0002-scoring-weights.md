# Scoring weights — competitor_strength and gap_opportunity weight assignments (v0 UNCALIBRATED)

**Status:** accepted — tagged v0 UNCALIBRATED; recalibrate from shipped-tool outcomes

Every weight below was derived from first-principles judgment on a single
competitive brief (time-card tool, June 2026). No shipped-tool outcome data exists
yet. Following the principle established in `pick-next-tool` ADR-0002, we stop
presenting these numbers as validated facts and mark them explicitly provisional.

## Decision

### `competitor_strength` sub-weights (sum = 1.00)

| Dimension | Weight | Rationale |
|---|---|---|
| `authority` | 0.30 | Domain rating is the single most predictive proxy for how hard it is to outrank an incumbent organically. Highest single weight. |
| `serp_presence` | 0.25 | Owning featured snippets, PAA boxes, and AI-Overview citations is increasingly the real estate that matters — organic position 1 alone understates a strong incumbent. |
| `content_depth` | 0.15 | Content quality matters but is more improvable than authority; a thin-content incumbent is a real gap even at high DR. |
| `ux_perf_a11y` | 0.13 | CWV + a11y + mobile UX; measurable and actionable, but incumbents vary widely — weighted modestly so a single bad LCP doesn't dominate. |
| `feature_completeness` | 0.12 | Feature parity matters less than authority/SERP for rank; relevant for conversion once traffic arrives. Weighted below content. |
| `trust_signals` | 0.05 | HTTPS, reviews, privacy policy — table-stakes for most niches. Low weight because absence is disqualifying but presence is expected. |

### `gap_opportunity` sub-weights (sum = 1.00)

| Dimension | Weight | Rationale |
|---|---|---|
| `demand` | 0.35 | A gap with no search demand is not an opportunity. Demand dominates. |
| `incumbent_weakness` | 0.30 | Real measured weakness across the top incumbents is what makes a gap exploitable, not just theoretical. |
| `ai_resistance` | 0.20 | An opportunity that will be absorbed by AI Overviews in 12 months is worth less. Weighted meaningfully as the SERP landscape shifts. |
| `defensibility` | 0.15 | Can the gap be copied by incumbents in a sprint? Low defensibility lowers long-term value. |

All weights live in `scripts/score_config.py` as named constants — tunable without
touching engine logic.

Every weight in the above tables is tagged **`# v0 uncalibrated judgment — revisit
after N shipped outcomes`** in the code.

## Consequences

- The calibration loop: for each shipped tool, log the gap predictions against
  real 6/12-month outcomes (did the gap produce ranking uplift? conversion rate
  improvement?). Weights are revisited against that ledger — the skill self-corrects.
- Sharp weight boundaries carry an ambiguous band. A gap scoring 0.49 vs 0.51 on
  `incumbent_weakness` does not cleanly resolve to tier-2 vs tier-1; the band
  resolves to REFUSE-TO-TIER pending more data.

## Considered and rejected

- **Equal weights (1/6 each for competitor_strength, 1/4 each for gap_opportunity)**
  as a "neutral" default: rejected. Equal weighting is itself a strong claim (that
  all dimensions matter equally) and is harder to defend than documented asymmetric
  judgment. Explicit asymmetry is more honest about what we believe.
- **Borrow weights directly from pick-next-tool's scoring model:** rejected. The
  pick-next-tool model scores *tool opportunities* (demand + winnability + AI risk);
  this model scores *competitor gaps* (incumbent weakness + demand + defensibility).
  The axes overlap but the decision context differs.
