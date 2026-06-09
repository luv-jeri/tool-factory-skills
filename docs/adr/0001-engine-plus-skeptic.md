# ADR-0001: Verification core is a deterministic engine plus an adversarial skeptic, fail-closed

## Status: Accepted

## Context

A hand-written PRD drifts. It quietly omits non-goals, states unmeasurable goals
("make it fast"), and promotes unverified hunches to v1 requirements. The whole
point of this skill is to make those failure modes *structurally impossible*, not
merely discouraged by prose advice in a template.

`projects-prd-generator` is the third house skill in the pipeline
(`pick-next-tool` -> `projects-competitive-analysis` -> this) and is built to the
same bar as its two siblings: an IRON-LAW funnel plus a deterministic Python
engine with `--selftest`, plus an adversarial kill pass. We must decide how a PRD
earns the word "complete." Two weak options were available and rejected: trust the
author's judgement (no enforcement), or rely on a single LLM self-review (not
deterministic, and an LLM grading its own output rationalizes).

## Decision

The verification core is two independent gates, and a PRD is stamped `FINAL` only
when **both** pass:

1. **A deterministic Python validator** — `scripts/prd_lint.py` (stdlib only, with
   `--selftest`). It runs all data-level checks against the structured
   `build-spec.json` (traceability, tier-gating, measurability, three-sided scope,
   PRD<->spec agreement) and section-presence checks against `PRD.md`. It emits
   `PASS`/`FAIL` plus a structured violation list.
2. **A separate adversarial reviewer subagent** — `scripts/prd-skeptic-workflow.js`.
   It independently challenges every requirement, every acceptance criterion, and
   every non-goal, defaulting to skeptical, and returns a schema-validated verdict
   (`keep` / `demote` / `flag`).

The engine is the deterministic floor; the skeptic is the adversarial ceiling.
Neither alone is sufficient. The "complete" stamp comes from the engine + skeptic
(IRON LAW 6), never from the author asserting it.

## Consequences

- The engine fails closed (IRON LAW 5): a missing required section, an untraceable
  requirement, an unmeasurable criterion, or a PRD<->build-spec mismatch makes
  `prd_lint` raise or return FAIL; the PRD is stamped `DRAFT-INCOMPLETE` and `FINAL`
  is refused. "Insufficient input" is a legal, honest output.
- `--selftest` carries an embedded golden-GOOD fixture that must PASS and >=3
  golden-BAD fixtures (one per law) that must each FAIL with the expected law label.
  Engine regressions are caught before they reach a real PRD.
- The skeptic runs via the host Workflow tool and is never read into context to
  study; it is dispatched and its verdicts consumed. This keeps the adversarial
  pass genuinely independent of the drafting context.
- Two gates is more machinery than one, but the cost is bounded (one stdlib script +
  one workflow) and is the price of a PRD whose completeness is a fact, not a claim.
