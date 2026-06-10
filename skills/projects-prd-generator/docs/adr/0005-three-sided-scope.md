# ADR-0005: Scope is three-sided — DO, WON'T-DO, and SKIPPED-FOR-NOW are all mandatory

## Status: Accepted

## Context

The most common silent PRD failure is an *omitted* non-goal. A PRD that lists only
what to build leaves "what we are deliberately NOT doing" to assumption, so scope
creeps and the team relitigates the boundary mid-build. Equally, a feature that is
neither committed nor explicitly excluded nor explicitly deferred is a gap hiding in
plain sight: someone will build it, or argue it should have been built, and the PRD
gave no answer.

A two-sided scope (in / out) is not enough, because it conflates two genuinely
different "nots": features we will never do, and features we are deferring on purpose
with a known trigger to revisit.

## Decision

Per **IRON LAW 4**, every PRD states scope on three sides, and every candidate feature
lands in exactly one of them, each with a one-line reason:

- **DO** — committed, in-scope, prioritized, evidence-backed v1 work.
- **WON'T-DO** — explicit non-goals. State *why not* (e.g. beating incumbents on raw
  speed is table-stakes only, not a differentiator).
- **SKIPPED-FOR-NOW** — deferred, with the reason and the trigger that would promote it
  (typically v2 / hypothesis-tier items awaiting validation).

A feature present in **none** of the three is a gap, and that is a failure. The
deterministic engine enforces this: `prd_lint.check_scope` requires
`scope.do`, `scope.wont_do`, and `scope.skipped` to each be present and non-empty in
`build-spec.json`; any empty side is a `4-scope` violation and the PRD cannot be
`FINAL`. The PRD's section 5 mirrors these three sides for the human reader.

## Consequences

- Non-goals can no longer be silently omitted; an empty `wont_do` fails the lint. The
  most common PRD drift becomes structurally impossible.
- The distinction between "never" (WON'T-DO) and "not yet" (SKIPPED-FOR-NOW) is
  preserved, so deferred work carries an explicit re-entry trigger instead of being
  lost.
- Table-stakes parity items (e.g. match-not-beat on speed/schema) are correctly placed
  in WON'T-DO with a reason, keeping the team from over-investing in non-differentiators.
- Authors are forced to make a placement decision for every candidate feature up
  front, which is more work at draft time but eliminates the most expensive class of
  mid-build scope arguments.
