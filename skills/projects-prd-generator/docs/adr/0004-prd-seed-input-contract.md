# ADR-0004: The input contract is the competitive brief's frozen prd_seed block; absent it, fail closed

## Status: Accepted

## Context

This skill is the third stage of a pipeline. It is not a green-field PRD writer — it
exists to convert a *measured* competitive brief into a buildable contract. If it
accepted a vague product gist as its primary input, it would be inventing demand and
market data, which is exactly what IRON LAW 1 (no requirement without a source) and
the skill's non-goals forbid. The upstream `projects-competitive-analysis` skill
already emits a frozen, machine-readable handoff for precisely this consumer: the
`prd_seed:` YAML block embedded in `COMPETITIVE-BRIEF.md`, whose field names are a
frozen API surface (see that skill's ADR-0005).

The decision is what this skill reads, what is required versus optional, and what
happens when the spine is missing.

## Decision

The skill reads the tool's build folder
(`micro-tool-factory/builds/<tool>/`) with this resolution order:

| Source | Role | Required |
|---|---|---|
| `COMPETITIVE-BRIEF*.md` -> `prd_seed:` YAML block | Spine: positioning, JTBD, must-have / v2 / out-of-scope, budgets, targets, open questions | YES |
| Full brief + source ledger (`research-raw*.json`, `audit-measured.json`, `gaps.json`) | Evidence + tiers for traceability; competitor baselines to beat | YES |
| `pick-next-tool` `research-raw.json` | Demand / keyword cluster / volume | optional (else `demand` flagged inherited-unverified) |
| Product gist / prior qualitative brief | Background, framing | optional |

Every fact pulled in carries its **upstream evidence tier**
(`real-measured` > `triangulated` > `reasoned` / `UNVERIFIED` / `HYPOTHESIS`). That
tier governs IRON LAW 2 (tier-gating) downstream.

If the `prd_seed` block is absent, the skill **fails closed**: it refuses to run and
emits "No prd_seed found — run projects-competitive-analysis first." It does not
fabricate a spine from a gist.

## Consequences

- The skill cannot manufacture market data; every requirement traces to a brief-ledger
  entry, a `pick-next-tool` datum, or an owned assumption (IRON LAW 1).
- The frozen `prd_seed` field names are the integration boundary between the two
  skills. A rename upstream is a breaking change to this contract.
- The fail-closed refusal mirrors how `projects-competitive-analysis` can import
  `pick-next-tool` research: a missing upstream artifact is a hard stop, not a silent
  best-effort guess.
- Optional sources degrade gracefully: absent `pick-next-tool` demand data, the demand
  fact is flagged `inherited-unverified` rather than blocking the run — consistent with
  the tiered gate in ADR-0002.
