# Input integrity — the engine fails closed and refuses to commit on unverified inputs

**Status:** accepted

The red-team proved the engine trusts whatever it is handed: `cluster_monthly_volume` was read with `.get()`, so omitting/mistyping the single most important gate's input **silently passed** it at OK `88.0`; and three *self-asserted* fields (`thin_site_proof`, `artifact_type`, affiliate+`buyer_slice`) move ~70% of the weight — `thin_site_proof=True` alone flipped a DR-95 wall from DROP to `93`. The evidence-tier discipline `scoring-model.md:17` mandates was **never enforced in code**. Under ADR-0001, an engine that fails *open* on missing/optimistic input is the most likely real-world path to a greenlit dud.

## Decision

The scoring engine fails **closed** and will not emit a build-first verdict on inputs it cannot stand behind:

1. **Required keys are required.** Every contract field is read by direct indexing; a missing/mistyped key raises, never silently passes. A validation pass runs before scoring.
2. **The blocking gate fails closed.** No `real-measured` demand → no commit. The engine never downgrades an evidence tier to clear IRON LAW 1.
3. **Evidence tiers are code-enforced.** `first_build_eligible = True` requires the high-weight, veto-relevant dimensions (demand, winnability, AI-resistance) to be tagged `real-measured`. Below that, the candidate still *ranks* (Stage 4 runs on triangulated data) but is **not committable** until Stage 5 upgrades the evidence — operationalizing the rank-on-estimates / commit-on-real-data funnel.
4. **`thin_site_proof` must carry evidence.** It is honored only when accompanied by the ranking URL + that page's DR + the keyword it ranks for; a bare asserted boolean is treated as unproven (and flagged). The thin-site winnability floor is also capped at 3 when `kd_head > 80` (a thin site beating a DR-90+ head is suspect, not proof).
5. **Restricted verticals are expressible and killed.** A required `adsense_restricted` flag is the first Gate-A DROP — closing the critical gap where an unmonetizable gambling/adult vertical scored 88–98 and outranked the real winner.
6. **Operational fail-closed:** a broken/empty data pull is distinguishable from genuine low volume and hard-fails loudly; finalists triangulate ≥2 free sources; a paid seat is recommended to *commit* (not to rank).

## Consequences

- The engine can now legitimately answer "REFUSE — get real data / a paid seat" instead of a confident pick on shaky inputs.
- Stage 4 ranking still works on triangulated data; only the *commit* (first_build_eligible) is gated on real-measured evidence — matching the funnel, not breaking it.
