# Time-to-rank is a fatal axis — the opener optimizes for speed-to-traffic, not peak opportunity

**Status:** accepted

Winnability answers *can a thin site rank this*, never *how long until it does*. The KD buckets imply a timeline (3–6mo / 6–9mo / 9–12mo) but the engine never enforces it against runway. Under ADR-0001 (ruin-avoidance), a winnable-but-slow tool that matures past the runway is not opportunity cost — it is the fatal outcome itself ("ranked into bankruptcy"). Notably the enshrined Timesheet pick is exactly such a tool: it scored 89 because `thin_site_proof` floored its winnability despite a KD-70 Hard head, i.e. a slow long-tail play. So time-to-rank must become a first-class, runway-relative axis.

## Decision

1. **Runway is an explicit per-invocation input** — "N months before a build must be earning." Not hardcoded; supplied each run.
2. **Time-to-first-traffic is estimated per candidate** from already-measured signals (head KD + `thin_site_proof` long-tail speed + domain sandbox age), turning the buried KD timeline into an explicit number.
3. **The opener is biased toward fastest-defensible-time-to-traffic, not highest Opportunity.** The first build's job is survival — start earning / prove the hub before runway ends. A higher-ceiling-but-slower tool becomes build #2, once revenue de-risks the wait.
4. **Soft gate:** time-to-traffic clearly beyond runway → drop as opener (keep as a fast-follow); merely slower than a same-hub alternative → demote. Hard kill only when a tool cannot plausibly rank inside the runway at all.

## Consequences

- The "first build" and "highest-opportunity tool" can legitimately differ; the brief must state both and explain the speed-over-ceiling choice for the opener.
- Adds runway as a required input to the funnel and a time-to-traffic field to each candidate's scorecard.
