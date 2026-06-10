# Optimize for ruin-avoidance first, opportunity-maximization second

**Status:** accepted

The `pick-next-tool` skill chooses the next tool to build for a solo founder on limited runway, where the stated failure mode is "if we choose wrong we are dead." We therefore treat the **false positive — greenlighting a tool that never ranks, draws no traffic, or never earns, and so burns months of runway — as the cardinal error**, strictly worse than the false negative of skipping a tool that would have been fine. The skill's job is first to *avoid the dud*, and only second to find the highest-opportunity tool among the safe survivors.

## Consequences

- The kill-gates and the evidence-tier rules are the primary product; the 0–100 Opportunity score is only a tie-breaker among candidates that have already cleared the gates. A high score never overrides a gate failure or a low evidence tier.
- When data is genuinely ambiguous (e.g. real volume straddles a gate threshold, or the kill pass is inconclusive), the bias is to **DROP / refuse to pick**, not to rank optimistically. "REFUSE TO PICK — insufficient evidence; get better data or widen the hub" must be a legal, first-class output of the funnel, not an error state.
- Threshold calibration (see later ADRs) is tuned to minimize false positives, accepting more false negatives as the price.

## Considered and rejected

- **Pure opportunity-maximizer** (rank everything by score, pick the top): rejected — it reaches for the highest number, which is exactly the optimistic-input trap that kills runway. Under a fatal-downside constraint, maximizing expected upside is the wrong objective.

## Open

- Whether **time-to-rank** is itself a fatal axis (a winnable-but-slow tool starving the runway before it ranks) — i.e. whether time-to-rank becomes a *gate* rather than a footnote — is deferred to its own decision.
