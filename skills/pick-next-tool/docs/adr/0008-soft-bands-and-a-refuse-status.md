# Soft bands around the noisy cutoffs, and a first-class REFUSE status

**Status:** accepted (sizes the band widths ADR-0002 deferred, using the red-team sensitivity data)

The red-team measured what ADR-0002 suspected: hard cutoffs inside the inputs' own measurement noise flip the verdict ~half the time. The Gate-B KD cliff at `20→21` flips kill↔survive **~62%** of draws under the doc's stated ±5 KD noise — and the doc itself (`scoring-model.md:52`) calls head KD "a timeline signal, not the gate." The demand `+1` bonus toggles on Similarweb-estimated traffic crossing a hard `1,000,000` line under ±30% noise, swinging Opportunity up to 12 points. A point estimate on a noisy input at a cliff is a coin-flip dressed as a verdict.

## Decision

Introduce **REFUSE** as a first-class engine status (per ADR-0001: "I cannot safely decide" is a legal output), and replace bare cliffs with margins:

- **Gate-B auto-kill needs margin.** `winnability == 1` is a confident DROP only on a clear signal — `native_feature`, or `kd_head ≥ 26` with `weak_count ≤ 1`, or an *evidenced* DR wall. A `winnability == 1` that sits in the KD `21–25` noise band with no thin-site proof returns **REFUSE** ("pull more SERP/thin-site evidence"), not DROP.
- **Demand `+1` bonus uses the lower bound.** Require the conservative (`0.7×`) traffic estimate to clear `1,000,000` before granting the deep-cluster bonus, so jitter across the line can't toggle a full point.
- **Sensitivity flag.** When an input below `real-measured` tier sits within one threshold-step of a gate or score change, the candidate is flagged and cannot be `first_build_eligible` until Stage 5 verifies it; the engine reports a robust *band*, not a single confident point.
- **REFUSE carries no Opportunity number** (like DROP) and ranks below OK/VETO but above DROP.

## Consequences

- Near a boundary on estimated data, the honest output is REFUSE → go verify, rather than a false-confident OK or DROP.
- All thresholds remain v0 config (ADR-0002); the margins themselves are provisional and enter the calibration ledger.
