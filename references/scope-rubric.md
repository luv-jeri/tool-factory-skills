# Scope rubric — three-sided classification

> **Contract:** `scripts/prd_lint.check_scope` is the single source of truth. **If this document and the
> engine disagree, the engine wins and this doc is the bug; change both in the same commit.** This rubric
> enforces IRON LAW 4 (scope is three-sided).

## Contents

1. [Why three-sided](#why-three-sided)
2. [The three buckets](#the-three-buckets)
3. [Decision flow](#decision-flow)
4. [Worked example — the time-card brief](#worked-example--the-time-card-brief)
5. [What the engine checks](#what-the-engine-checks)

---

## Why three-sided

A hand-written PRD silently drops the non-goals. Six months later a "while we're at it" feature lands because
nobody wrote down that it was deliberately excluded. IRON LAW 4 makes that impossible: **every candidate
feature must land in exactly one of three buckets, each with a one-line reason.** A feature present in none of
the three is an unclassified gap and the engine fails.

`build-spec.json.scope` has exactly three keys: `do`, `wont_do`, `skipped`. All three must be non-empty.

---

## The three buckets

| Bucket | `build-spec` key | Meaning | Required reason |
|---|---|---|---|
| **Do** | `do[]` | Committed v1 work. Evidence-backed (real-measured or triangulated), traceable, with measurable acceptance criteria. | What we win on / why it is in v1 |
| **Won't-Do** | `wont_do[]` | Explicit, permanent non-goal. We are deliberately **not** building this — state *why not*. | The reason it is excluded (e.g. "table-stakes only — match, do not differentiate"; "outside the free+static+no-login model") |
| **Skipped-For-Now** | `skipped[]` | Deferred to a later version. Not rejected — parked, with the **trigger** that would promote it. | `reason` field = the condition under which it becomes a Do |

The distinction that matters most: **Won't-Do is a closed door; Skipped-For-Now is a door left ajar.** Speed
parity is Won't-Do because we will never differentiate on it — we just match the leaders. Multi-worker is
Skipped because measured demand would promote it to a future Do.

---

## Decision flow

For each candidate feature:

1. **Is it evidence-backed (real-measured/triangulated) AND something we win on?** → **Do** (becomes a `must`/`should` requirement).
2. **Is it a deliberate exclusion — a thing competitors do that we will match-not-beat, or a thing outside our model (login/paid/server)?** → **Won't-Do**, with the reason.
3. **Is it a plausible future feature whose evidence is weak today (`reasoned`/`hypothesis`/unmeasured demand)?** → **Skipped-For-Now**, with the promotion trigger.
4. **None of the above / unclassified?** → STOP. The engine fails. Classify it.

Anything on a weak evidence tier that you were tempted to commit (LAW 2) lands here as Skipped, paired with an
owned open question — never as a v1 Do.

---

## Worked example — the time-card brief

From `COMPETITIVE-BRIEF-v2-measured.md#prd_seed` and `gaps.json`:

**Do (committed v1, evidence-backed):**

- **Fully accessible form** — labeled inputs, ARIA, keyboard nav, AA contrast. Tier `real-measured`; gap Opp 65.0; 10/10 incumbents fail (a11y 12–70, best 70). This is the moat.
- **True CSV export** — machine-readable, not print/PDF. Tier `triangulated`; gap Opp 62.0; 0/10 ship it.
- **Core calc** — in/out, breaks/lunch, overtime, rounding, decimal + HH:MM, running total. The functional baseline of the tool.

**Won't-Do (explicit non-goals, with *why not*):**

- **Beating incumbents on raw speed** — *why not:* table-stakes only. The leaders are already green (TimeClockWizard LCP 800 ms, Redcort 1165). We **match** the budget (LCP ≤ 1100 ms), we do not differentiate on it.
- **Beating incumbents on schema presence** — *why not:* refuted exploit. 4/10 ship schema incl. #1 Redcort (`FAQPage`) and #3 Harvest. We ship valid `WebApplication` + `FAQPage` to match, not to win.
- **Paid / login features** — *why not:* outside the free + static + client-side + AdSense model.

**Skipped-For-Now (deferred + promotion trigger):**

- **Multi-worker / team timesheets** — tier `hypothesis` (Opp 57.6, demand unmeasured). *Trigger:* promote to a Do once multi-worker demand is measured. Paired open question owned by the analyst.
- **Timezone / DST-aware entry** — tier `reasoned` (Opp 49.6, niche, demand unmeasured). *Trigger:* promote if a measured cluster shows timezone intent.

Note the symmetry with the requirement rubric: schema/speed are Won't-Do because the brief **refuted** them as
exploits (table-stakes); multi-worker/timezone are Skipped because the brief tagged them **HYPOTHESIS**
(unmeasured) — exactly the items LAW 2 forbids as v1 must-haves.

The matching `build-spec.json.scope`:

```json
"scope": {
  "do": [
    "Fully accessible form: labeled inputs, ARIA, keyboard nav, AA contrast",
    "True CSV export (machine-readable)",
    "Core calc: in/out, breaks, overtime, rounding, decimal + HH:MM, running total"
  ],
  "wont_do": [
    "Differentiate on raw speed (table-stakes — match LCP <= 1100ms, do not beat)",
    "Differentiate on schema presence (table-stakes — ship WebApplication + FAQPage to match)",
    "Paid / login features (outside free + static + AdSense model)"
  ],
  "skipped": [
    { "item": "Multi-worker / team timesheets", "reason": "HYPOTHESIS — promote when demand is measured" },
    { "item": "Timezone / DST-aware entry", "reason": "reasoned/niche — promote on a measured timezone cluster" }
  ]
}
```

---

## What the engine checks

`check_scope` reads `build-spec.json.scope`:

- `scope` must be an object → else `4-scope … scope missing or not an object`.
- `do`, `wont_do`, and `skipped` must each be present and non-empty → an empty bucket emits
  `4-scope … scope.<side> is empty — scope must be three-sided`.

An empty Won't-Do is the most common failure: it means someone forgot to write down the non-goals. The engine
treats that as a hard fail, not a warning.
