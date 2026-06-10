# ADR-0002: Gaps are handled by a tiered gate plus an assumption register, with a human-gated escape hatch

## Status: Accepted

## Context

Every PRD inherits uncertainty from upstream. Some facts are `real-measured`, some
are `triangulated`, and some are only `reasoned` / `UNVERIFIED` / `HYPOTHESIS`. A
naive skill has two bad reflexes: (a) refuse to ship anything until every fact is
measured (the PRD never gets written, and the skill silently fires slow, expensive
live-data measurement on its own), or (b) ship everything regardless of evidence
(hunches get promoted to v1 requirements and the team builds on sand).

We need a policy that lets the PRD ship *complete* while making the difference
between proven and unproven impossible to hide — and that never auto-runs slow live
measurement behind the user's back.

## Decision

Gap handling is a **tiered gate** feeding an **assumption register**, with a
**human-gated escape hatch**. The behaviour is exactly:

1. **Hard-BLOCK only on a v1 must-have built on no/weak evidence.** A requirement
   with `priority == must` may NOT carry an evidence tier in
   `{reasoned, UNVERIFIED, HYPOTHESIS}` and may NOT lack a `source_ref`. This is the
   only thing that hard-blocks. (This is IRON LAW 2, enforced by
   `prd_lint.check_requirements`.)

2. **Quarantine everything else into the assumption register.** All other
   uncertainty — launch-time rechecks, unmeasured demand, anything resting on
   `v2`/nice-to-have items — is NOT a blocker. It is written into the tracked
   "Assumptions & Open Questions" register (PRD section 11 / `build-spec.open_questions`)
   with an **owner** and a **resolve-by milestone**. The PRD still ships complete; the
   uncertainty is documented, not hidden, and not silently dropped.

3. **On a hard-block, STOP and surface it to the human with two choices —
   never resolve automatically:**
   - **(a) Re-measure** by re-invoking the upstream skill
     (`projects-competitive-analysis` / `pick-next-tool`). This is a *manual*
     escalation, triggered only by the human's choice. The skill NEVER automatically
     fires slow live-data measurement.
   - **(b) Downgrade** the requirement to v2 or to a non-goal so the PRD can ship.

   The skill applies whichever the human picks, then re-runs the engine + skeptic.

## Consequences

- The PRD is allowed to ship with documented uncertainty; only a *must-have on
  weak/no evidence* stops the line. This keeps the skill productive without letting
  it lie.
- The escape hatch is strictly human-gated. Re-measurement is never automatic, so
  the skill never silently burns time/money on live data. The human stays in control
  of the only expensive operation.
- The register must be load-bearing: an `ASSUMPTION`-tagged requirement with no owner
  in `open_questions` is itself a traceability violation (IRON LAW 1). An assumption
  without an owner and a resolve-by is not a real assumption — it is a hidden gap.
- Hypotheses inherited from the brief (the upstream `hypothesis` tier) land in the
  register as open questions, never as v1 requirements — exactly the routing the
  upstream prd_seed contract intends.
