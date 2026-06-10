# Score decaying dimensions on a conservative rank-time projection, not the decision-time snapshot

**Status:** accepted

Three of the five dimensions are measured today but only pay off when the site ranks, 6–12 months out: **AI-Resistance** (the skill admits AIOs creep down-funnel into commercial terms), **Winnability** (a weak SERP erodes as clones launch — the original "imposter-game moat" observation), and **Demand** (a flat/declining trend means today's volume isn't tomorrow's). Scoring these on the snapshot systematically over-rates tools — the optimistic-input trap that, under ADR-0001, is how a dud gets greenlit. We commit to scoring the SERP we will actually rank *into*: the future one.

## Decision

1. **Artifact-type structural immunity over current AIO rate.** Interactive/personalized tools (calculators, generators, scorers) stay AI-Resistance=5 because Google structurally cannot run the tool inline — a moat that does not decay. Decay risk is concentrated in `info_tool`/`static_fact` types; apply a **forward haircut** to those (score against a higher *projected* AIO fire-rate than today's), and **bias the opener toward interactive/personalized artifacts**.
2. **Winnability recency check.** If page 1 shows fresh entrants (clones launched within the last few months), treat the niche as contesting and haircut winnability — a visibly eroding moat is not a moat.
3. **Demand requires a non-negative trend**, not just an absolute volume; a declining cluster fails harder.

## Consequences

- Scores will read *lower* than today's raw data suggests, by design. This is conservatism, not pessimism — it is the ADR-0001 bias applied to time.
- Each decaying dimension carries a recheck cadence on the monitor-list; the haircut assumptions are themselves part of the calibration ledger (ADR-0002).

## Related

- Same temporal-mismatch root cause as ADR-0004 (time-to-rank). Together: *both the cost (time) and the value (rank-time scores) of a build are evaluated at the future horizon, not at decision time.*
