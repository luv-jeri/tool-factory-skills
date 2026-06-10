# Thresholds are uncalibrated v0 judgment — treat them as tunable config, not facts

**Status:** accepted

Every cutoff in the engine — Gate D's `<1,000/mo` floor and `~5,000/mo` pass bar, the KD→score buckets (`0–5/6–10/11–15/16–20/>20`), the CPC bands (`$0.50 / $2 / $3`), the demand `+1` bonus condition (`cluster_kw_count ≥ 400` **and** `incumbent_top3_visits ≥ 1,000,000`), and the dimension weights (`0.20/0.25/0.25/0.20/0.10`) — was extracted as **judgment from the single first-tool reasoning run (07-FIRST-TOOL-DECISION), not calibrated against any shipped-tool outcome.** As of this decision the portfolio is pre-launch, so no outcome data exists to calibrate against. We will stop presenting these numbers as if they were validated.

The risk this addresses: *determinism without calibration hides error rather than removing it.* Three agents disagreeing is visible noise; one engine everyone trusts, built on eyeballed numbers, is invisible **correlated** error — every future pick wrong in the same direction with nothing to flag it. Under the ADR-0001 ruin-avoidance objective, a hidden systematic bias is worse than visible disagreement.

## Consequences

- **Honesty tagging.** Every threshold in `score.py` and `scoring-model.md` is marked `v0 uncalibrated judgment — revisit after N shipped outcomes`. A guess must never read as evidence.
- **Config, not magic numbers.** All thresholds and weights move into one `THRESHOLDS`/`WEIGHTS` config block at the top of `score.py`, tunable without touching logic. The OSS repo surfaces them as knobs.
- **Calibration loop.** The process gains an outcome ledger: for each shipped tool, log the prediction (gate verdicts + Opportunity score) against the real 6/12-month result (did it rank? draw traffic? earn?). Thresholds are revisited against that growing ledger — the skill self-corrects instead of staying frozen on the Timesheet guess.
- **Bands over points.** Because the cutoffs are guesses, each sharp threshold gains an explicit *ambiguous band* that resolves to DROP / REFUSE-TO-PICK (per ADR-0001), rather than pretending a 1-unit difference at the boundary is meaningful. **Band widths are sized from the boundary-noise sensitivity analysis (deferred until that data lands), not picked arbitrarily.**

## Considered and rejected

- **Keep the sharp deterministic cutoffs as-is** because "deterministic = reproducible": rejected. Reproducibility of a wrong number is not a virtue; it just makes the error consistent. Determinism is kept for *agreement between agents*, but the numbers themselves are explicitly provisional.
