# Requirement rubric — well-formed and traceable

> **Contract:** `scripts/prd_lint.check_requirements` is the single source of truth. **If this document and
> the engine disagree, the engine wins and this doc is the bug; change both in the same commit.** This rubric
> enforces IRON LAW 1 (traceability) and IRON LAW 2 (tier-gating).

## Contents

1. [The shape of a requirement](#the-shape-of-a-requirement)
2. [IRON LAW 1 — no requirement without a source](#iron-law-1--no-requirement-without-a-source)
3. [IRON LAW 2 — no unverified claim as a v1 must-have](#iron-law-2--no-unverified-claim-as-a-v1-must-have)
4. [The assumption escape hatch](#the-assumption-escape-hatch)
5. [Checklist](#checklist)

---

## The shape of a requirement

Every functional requirement is one record in `build-spec.json.requirements[]`. A well-formed requirement is:

| Field | Rule | Example |
|---|---|---|
| `id` | `R1`, `R2`, … — unique; mirrored in the PRD Functional Requirements table | `R1` |
| `statement` | **one** verifiable behavior, not a bundle. "Export to CSV" not "export and email and print" | `"Form inputs are programmatically labeled, keyboard-navigable, AA-contrast"` |
| `priority` | one of `must` (v1 commit), `should` (v1 if budget), `v2` (deferred) | `must` |
| `source_ref` | a ledger/brief/pick-next-tool anchor, OR empty only if `evidence_tier == assumption` and owned (see below) | `gaps.json#accessibility` |
| `evidence_tier` | the inherited upstream tier: `real-measured` > `triangulated` > `reasoned`/`unverified`/`hypothesis`/`assumption` | `real-measured` |
| `acceptance_criteria` | a non-empty list of measurable criteria (see `acceptance-criteria-guide.md`) — required for `must`/`should` | `[{metric: lighthouse_a11y, op: ">=", value: 95, unit: score}]` |

One behavior per record. If you cannot write a single measurable acceptance criterion for it, it is not yet a
requirement — it is a feature idea that belongs in scope triage or the open-questions register.

---

## IRON LAW 1 — no requirement without a source

Every requirement traces to a real upstream artifact (a `gaps.json` row, an `audit-measured.json` baseline,
a `prd_seed` field, or a `pick-next-tool` datum) **or** is explicitly tagged an assumption with a named owner.
An untraceable requirement is cut. The engine fails on any requirement that has an empty `source_ref` and is
not tagged `assumption`.

**PASS — traceable to the measured gap:**

```json
{ "id": "R1", "priority": "must",
  "statement": "Form inputs are programmatically labeled, keyboard-navigable, AA-contrast",
  "source_ref": "gaps.json#accessibility", "evidence_tier": "real-measured",
  "acceptance_criteria": [ { "metric": "lighthouse_a11y", "op": ">=", "value": 95, "unit": "score" } ] }
```

`source_ref` points at the `gaps.json` row that measured a11y 12–70 across all 10 incumbents. Anyone can open
that file and confirm the requirement is earned, not invented.

**FAIL — no source, not an assumption:**

```json
{ "id": "R7", "priority": "should",
  "statement": "Add a Pomodoro timer mode",
  "source_ref": "", "evidence_tier": "reasoned",
  "acceptance_criteria": [ { "predicate": "pomodoro_mode_present == true" } ] }
```

Engine emits: `1-traceability … requirement has no source_ref and is not tagged assumption`. A Pomodoro mode
appears in no `gaps.json` row, no brief, no `prd_seed` — it is a hunch. Cut it, or move it to the
open-questions register with an owner.

---

## IRON LAW 2 — no unverified claim as a v1 must-have

A `must` requirement may not rest on weak evidence. The engine blocks any requirement where
`priority == must` and `evidence_tier in {reasoned, unverified, hypothesis}` (`WEAK_TIERS` in the engine).
Weak-tier ideas are legal only as `v2` items or as tracked open questions — never as a v1 commit.

**FAIL — must-have on a HYPOTHESIS gap (the time-card multi-worker trap):**

```json
{ "id": "R5", "priority": "must",
  "statement": "Multi-worker / team timesheet entry",
  "source_ref": "gaps.json#multi-worker", "evidence_tier": "hypothesis",
  "acceptance_criteria": [ { "predicate": "team_mode_present == true" } ] }
```

Engine emits: `2-tier-gating … v1 must-have rests on 'hypothesis' evidence — only v2/open-question allowed`.
The time-card brief scored multi-worker at Opp 57.6 but tagged it `demand unmeasured`. It cannot be a v1
must-have on that evidence.

**PASS — same idea, correctly demoted to v2 with an owned open question:**

```json
{ "id": "R5", "priority": "v2",
  "statement": "Multi-worker / team timesheet entry",
  "source_ref": "gaps.json#multi-worker", "evidence_tier": "hypothesis" }
```

…paired with an `open_questions[]` entry owning the unknown:
`{ "item": "Multi-worker demand", "owner": "analyst", "resolve_by": "pre-v2" }`.

Priority `v2` is outside `must`/`should`, so the engine does not require acceptance criteria on it, and the
tier gate does not fire. The hypothesis is documented, not hidden, and the PRD still ships complete.

---

## The assumption escape hatch

When a requirement genuinely has no upstream source but the team chooses to commit to it anyway, it must be
tagged `evidence_tier: assumption` AND appear in `open_questions[]` with an `owner` (matched by `item` or by
`statement`). This makes the assumption a tracked debt with a name on it rather than a silent guess. A
requirement tagged `assumption` with no owner still fails LAW 1.

---

## Checklist

- [ ] One verifiable behavior per requirement — no bundles.
- [ ] `source_ref` resolves to a real ledger/brief/pick-next-tool anchor, or `evidence_tier == assumption` + owner.
- [ ] No `must` on `reasoned`/`unverified`/`hypothesis` — demote to `v2` or quarantine as an open question.
- [ ] Every `must`/`should` carries ≥1 measurable acceptance criterion.
- [ ] Requirement ids in the PRD Functional Requirements table match `build-spec.json.requirements[].id` exactly.
