# Acceptance-criteria guide — measurable or it is not a criterion

> **Contract:** `scripts/prd_lint._is_measurable` and `scripts/prd_lint.check_banned_adjectives` are the
> single source of truth. **If this document and the engine disagree, the engine wins and this doc is the bug;
> change both in the same commit.** This guide enforces IRON LAW 3 (every acceptance criterion is measurable).

## Contents

1. [The two accepted shapes](#the-two-accepted-shapes)
2. [What the engine accepts](#what-the-engine-accepts)
3. [The prose guard — banned adjectives](#the-prose-guard--banned-adjectives)
4. [The banned-adjective set, with a measured rewrite for each](#the-banned-adjective-set-with-a-measured-rewrite-for-each)
5. [Worked example — the time-card must-haves](#worked-example--the-time-card-must-haves)

---

## The two accepted shapes

An acceptance criterion in `build-spec.json.requirements[].acceptance_criteria[]` is measurable in exactly one
of two shapes:

1. **Structured metric** — `{ "metric": "...", "op": "...", "value": <number>, "unit": "..." }`. The `value`
   must be a number (int or float), and both `unit` and `metric` must be non-empty.
   Example: `{ "metric": "lighthouse_a11y", "op": ">=", "value": 95, "unit": "score" }`.
2. **Boolean predicate** — `{ "predicate": "<verifiable string>" }` for things that are present or absent.
   Example: `{ "predicate": "csv_export == true" }`.

Anything else is not a criterion. "It feels right," "users like it," "good UX" — none are measurable, none pass.

---

## What the engine accepts

`_is_measurable(c)` returns true only when:

- `c` is a dict, **and**
- it has a non-empty string `predicate` (boolean shape), **or**
- `value` is an `int`/`float` **and** `unit` is non-empty **and** `metric` is non-empty (structured shape).

So `{ "metric": "ux", "op": "is", "value": "good", "unit": "" }` fails twice: `value` is a string and `unit`
is empty. The engine emits `3-measurability … acceptance criterion not measurable`. Every `must`/`should`
requirement must carry at least one criterion that passes this test, or it fails with
`3-measurability … requirement has no acceptance_criteria`.

---

## The prose guard — banned adjectives

`_is_measurable` guards the structured `build-spec.json`. But unmeasurable language also creeps into the
`PRD.md` prose. `check_banned_adjectives` is the second line of defense: inside the **Functional Requirements**
and **Benchmarks** sections, any line that contains a banned adjective **and has no number on it** is a
violation (`3-measurability`, section `prose`). The fix is always the same: replace the adjective with the
measured target it is gesturing at.

---

## The banned-adjective set, with a measured rewrite for each

The set is defined verbatim in `scripts/prd_lint.py`:

```python
BANNED_ADJECTIVES = {"fast", "accessible", "clean", "intuitive", "snappy",
                     "modern", "beautiful", "seamless", "blazing", "easy"}
```

Each is illegal in Requirements/Benchmarks prose unless the same line carries a number. Rewrite to the measured
target (baselines below are the time-card brief's, so each rewrite also names what it beats/matches):

| Banned adjective | Unmeasurable phrasing (illegal) | Measured rewrite (legal) |
|---|---|---|
| `fast` | "the tool is fast" | `LCP <= 1100 ms (beat Redcort 1165 ms; match TimeClockWizard 800 ms)` |
| `accessible` | "an accessible form" | `Lighthouse a11y score >= 95 (all 10 incumbents 12-70)` |
| `clean` | "a clean ad layout" | `<= 2 ad slots, 0 above the fold (vs TimeClockWizard 35)` |
| `intuitive` | "intuitive time entry" | `task completion (enter shift -> total) in <= 3 inputs, 0 errors in usability test` |
| `snappy` | "snappy interaction" | `INP <= 60 ms at p75` |
| `modern` | "a modern UI" | `responsive at 360 / 768 / 1280 px breakpoints; CLS <= 0.0` |
| `beautiful` | "a beautiful results panel" | `AA contrast ratio >= 4.5:1 on all text; WCAG 2.2 AA pass` |
| `seamless` | "seamless CSV export" | `CSV export downloads a valid RFC-4180 file in 1 click (predicate: csv_export == true)` |
| `blazing` | "blazing performance" | `LCP <= 1100 ms AND INP <= 60 ms AND CLS <= 0.0 (Core Web Vitals all green)` |
| `easy` | "easy keyboard use" | `100% of inputs reachable and operable by keyboard (Tab/Enter); 0 keyboard traps` |

Rule of thumb: if you cannot attach a number or a verifiable boolean to the adjective, it does not belong in a
requirement or a benchmark — move it to UI/UX Spec as a design principle, where it is not gated.

---

## Worked example — the time-card must-haves

The two committed exploits, expressed as measurable criteria the engine accepts:

```json
{ "id": "R1", "priority": "must",
  "statement": "Form inputs are programmatically labeled, keyboard-navigable, AA-contrast",
  "source_ref": "gaps.json#accessibility", "evidence_tier": "real-measured",
  "acceptance_criteria": [
    { "metric": "lighthouse_a11y", "op": ">=", "value": 95, "unit": "score" },
    { "metric": "contrast_ratio", "op": ">=", "value": 4.5, "unit": "ratio" },
    { "predicate": "all_inputs_keyboard_operable == true" }
  ] }
```

```json
{ "id": "R2", "priority": "must",
  "statement": "Export the computed timesheet as machine-readable CSV",
  "source_ref": "gaps.json#csv", "evidence_tier": "triangulated",
  "acceptance_criteria": [
    { "predicate": "csv_export == true" },
    { "metric": "csv_export_clicks", "op": "<=", "value": 1, "unit": "clicks" }
  ] }
```

Compare the illegal version that the prose guard catches — a Requirements-section line reading
`R1 must be accessible and the export should feel seamless.` Two banned adjectives (`accessible`, `seamless`),
no number → `3-measurability … unmeasurable adjective 'accessible' without a number`. The rewrite above carries
`>= 95 score`, `>= 4.5 ratio`, and `csv_export == true` instead.
