# Fail-closed engine — missing fields raise ContractError; "insufficient data" is a legal output

**Status:** accepted

Mirrors `pick-next-tool` ADR-0009. A scoring engine that silently passes on missing
or unverifiable input is worse than one that refuses: confident wrong output is
harder to catch than an explicit refusal. The projects-competitive-analysis skill has the same
failure mode — a missing `incumbent_weakness` measure can silently default to zero
(looks like incumbents are weak) or to a high assumed value (looks like a moat),
both wrong and both undetectable without the ContractError.

## Decision

1. **Required contract fields are required.** Every field the scoring engine reads
   is accessed by direct key indexing, not `.get()` with a default. A missing or
   mistyped key raises `ContractError` immediately — it never silently passes as a
   zero or a null.

2. **A validation pass runs before scoring.** All input fields are validated for
   type, range, and evidence-tier presence before any weight multiplication occurs.
   A malformed input stops the run at the gate, not halfway through a misleading
   partial score.

3. **`REFUSE / "insufficient data"` is a legal and correct output.** The engine
   is permitted — and required — to emit:
   ```
   REFUSE: insufficient data to score gap_opportunity.incumbent_weakness.
   Run scripts/competitor_audit.py against the full triaged set, then re-submit.
   ```
   This is not a failure of the skill; it is the skill doing its job. The caller
   (the Claude agent) must surface this refusal to the user rather than papering
   over it with a reasoned guess.

4. **Evidence-tier validation is part of the contract check.** A field tagged
   `reasoned` on a veto-path dimension (demand, incumbent_weakness) blocks the
   scoring run from emitting a `tier: build-now` verdict. The run may still produce
   a `tier: hypothesis` output — the partial data is not discarded, it is
   downgraded correctly.

5. **Broken data pulls fail loudly.** A network error, empty API response, or
   parse failure on a live-page audit is distinguishable from a genuine zero score
   and raises rather than silently defaulting. The audit must be re-run; the run
   cannot proceed on stale or missing measurement.

## Consequences

- The skill can legitimately tell the user "go measure this first" instead of
  producing a confident-looking output on incomplete evidence.
- Partial runs (some competitors measured, some not) produce a `tier: partial` block
  that clearly labels which competitors are missing and which gaps can already be
  scored.
- Downstream consumers (PRD-generation skill, handoff blocks) can trust that any
  field in a non-refused output has passed the contract check.

## Considered and rejected

- **Permissive defaults (`.get(field, 0)`) to keep the engine running on partial
  data:** rejected. A default of zero on `incumbent_weakness` says incumbents are
  weak — exactly the wrong signal for a gap with an unmeasured incumbent. There is
  no neutral default for a competitive signal.
- **Warn instead of raise on missing fields:** rejected. Warnings are easy to miss
  in long output; a ContractError forces acknowledgment. The pick-next-tool engine
  proved this — silent `.get()` on the most important gate field passed at 88.0 and
  was only caught by adversarial review.
