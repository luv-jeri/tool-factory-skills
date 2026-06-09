# Deliverables — output templates + handoff

Stage 8 of the funnel writes these four files to the tool build folder
(`micro-tool-factory/builds/<tool>/`) and prints the handoff summary.

**Stamp rule (IRON LAW 5 + 6):** a file is `FINAL` **only** when
`prd_lint.py` PASS *and* the `prd-skeptic-workflow.js` adversarial pass both
returned clean. Otherwise every file header reads `DRAFT-INCOMPLETE` and the
controller surfaces the violation list — never silently emit FINAL.

The `build-spec.json` below is the authoritative structured source. The four
keys `prd_lint.py` reads for its data-level checks are:
`requirements[]`, `scope.{do,wont_do,skipped}`, `open_questions[]`, `budgets`.
Keep those exactly as shown or the engine fails closed.

---

## 1. `PRD.md`

The human single source of truth. Do **not** retype the section list here — copy
`references/prd-template.md` verbatim (its 14 `##` headers are what
`prd_lint.check_completeness` requires) and fill each section from the
`prd_seed` field noted in that template.

**Never silently overwrite an existing PRD.** If `PRD.md` already exists in the
build folder (e.g. a hand-written draft), write the generated PRD to
`PRD-<version>-generated.md` instead, add a `> Supersedes: PRD.md` line to its
header, and leave the rename/replace decision to the human. This mirrors how the
upstream brief lands as `COMPETITIVE-BRIEF-v2-measured.md` beside the original.

Header block to paste at the very top of `PRD.md`:

```markdown
# PRD — <tool> v<prd_version>

> Status: FINAL                <!-- FINAL only if prd_lint PASS AND skeptic PASS; else DRAFT-INCOMPLETE -->
> Generated from: COMPETITIVE-BRIEF-v2-measured.md#prd_seed
> Validated by: prd_lint.py (PASS) + prd-skeptic-workflow.js (PASS)
> Date: 2026-06-09

## Exec Summary
...
```

The Functional Requirements section must list the same requirement ids
(`R1`, `R2`, ...) that appear in `build-spec.json` — `check_agreement` fails on
any drift in either direction.

---

## 2. `build-spec.json`

The frozen machine mirror — the literal projection of the requirement records +
budgets a dev / CI / future build-skill consumes. Schema is design spec §8.
This filled example is the **time-card-calculator** dry-run target; it parses as
JSON and PASSES `prd_lint.py`.

```json
{
  "tool": "time-card-calculator",
  "prd_version": "1.0",
  "generated_from": "COMPETITIVE-BRIEF-v2-measured.md#prd_seed",
  "north_star": {
    "metric": "organic_sessions_to_calculation_rate",
    "target": ">= 60% of organic landings complete one calculation"
  },
  "requirements": [
    {
      "id": "R1",
      "priority": "must",
      "statement": "All time inputs and the results table are keyboard-operable and screen-reader labeled (WCAG 2.2 AA).",
      "source_ref": "gaps.json#accessibility",
      "evidence_tier": "real-measured",
      "acceptance_criteria": [
        { "metric": "lighthouse_a11y", "op": ">=", "value": 95, "unit": "score" },
        { "predicate": "axe-core serious+critical violations == 0 on the calculator page" }
      ]
    },
    {
      "id": "R2",
      "priority": "must",
      "statement": "User can export the computed timesheet to a CSV file client-side, no login.",
      "source_ref": "gaps.json#csv-export",
      "evidence_tier": "triangulated",
      "acceptance_criteria": [
        { "predicate": "csv_export_button downloads a valid RFC-4180 file with one row per day" },
        { "metric": "csv_export_time", "op": "<=", "value": 200, "unit": "ms" }
      ]
    },
    {
      "id": "R3",
      "priority": "should",
      "statement": "Page meets the fastest-incumbent Core Web Vitals budget (table-stakes, not a differentiator).",
      "source_ref": "audit-measured.json#lcp-baseline",
      "evidence_tier": "real-measured",
      "acceptance_criteria": [
        { "metric": "lcp", "op": "<=", "value": 1100, "unit": "ms" },
        { "metric": "cls", "op": "<=", "value": 0.0, "unit": "score" },
        { "metric": "inp", "op": "<=", "value": 60, "unit": "ms" }
      ]
    }
  ],
  "scope": {
    "do": [
      "R1 accessible time inputs + results table",
      "R2 client-side CSV export",
      "R3 match fastest-incumbent Core Web Vitals"
    ],
    "wont_do": [
      "Beat incumbents on raw page speed beyond table-stakes — diminishing returns, not the moat",
      "Emit richer schema than competitors — schema presence is table-stakes, not a differentiator",
      "Account/login or any server-side state — violates the free+static+client-side constraint"
    ],
    "skipped": [
      { "item": "Multi-worker / team timesheets", "reason": "Demand is a HYPOTHESIS; promote to v2 only if open question OQ1 resolves with measured volume." },
      { "item": "Timezone-aware shift math", "reason": "Deferred to v2; trigger = support tickets or measured search demand for timezone queries." }
    ]
  },
  "budgets": {
    "lcp_ms": 1100,
    "cls": 0.0,
    "inp_ms": 60,
    "a11y_score": 95,
    "word_count_min": 1400
  },
  "schema_targets": ["WebApplication", "FAQPage", "BreadcrumbList"],
  "monetization": {
    "ad_slots_max": 2,
    "above_fold_ads": false
  },
  "open_questions": [
    {
      "item": "Multi-worker / team timesheets",
      "owner": "Sanjay",
      "resolve_by": "v1-launch + 30 days"
    },
    {
      "item": "Per-variant keyword volume for 'timesheet' vs 'time card'",
      "owner": "Sanjay",
      "resolve_by": "pre-v2 keyword re-measure"
    }
  ]
}
```

Notes that keep the engine green:
- Every `must` / `should` requirement has at least one **measurable**
  acceptance criterion — either `{metric, op, value, unit}` (numeric value +
  unit + metric) or `{predicate: "..."}` (a non-empty boolean string).
  See `acceptance-criteria-guide.md`.
- No `must` requirement carries a weak `evidence_tier`
  (`reasoned` / `unverified` / `hypothesis`) — those land in `skipped` + the
  `open_questions` register instead (R-less, with an owner). That is IRON LAW 2.
- `scope.do`, `scope.wont_do`, `scope.skipped` are all non-empty (IRON LAW 4).
- Each `open_questions[]` entry has an `owner` so any future assumption-tagged
  requirement can trace to it.

---

## 3. `build-spec.yaml`

The same data as `build-spec.json`, YAML form, for humans who diff the spec in
review. The JSON is authoritative; keep this twin byte-equivalent in content.

```yaml
tool: time-card-calculator
prd_version: "1.0"
generated_from: COMPETITIVE-BRIEF-v2-measured.md#prd_seed
north_star:
  metric: organic_sessions_to_calculation_rate
  target: ">= 60% of organic landings complete one calculation"
requirements:
  - id: R1
    priority: must
    statement: All time inputs and the results table are keyboard-operable and screen-reader labeled (WCAG 2.2 AA).
    source_ref: gaps.json#accessibility
    evidence_tier: real-measured
    acceptance_criteria:
      - { metric: lighthouse_a11y, op: ">=", value: 95, unit: score }
      - { predicate: "axe-core serious+critical violations == 0 on the calculator page" }
  - id: R2
    priority: must
    statement: User can export the computed timesheet to a CSV file client-side, no login.
    source_ref: gaps.json#csv-export
    evidence_tier: triangulated
    acceptance_criteria:
      - { predicate: "csv_export_button downloads a valid RFC-4180 file with one row per day" }
      - { metric: csv_export_time, op: "<=", value: 200, unit: ms }
  - id: R3
    priority: should
    statement: Page meets the fastest-incumbent Core Web Vitals budget (table-stakes, not a differentiator).
    source_ref: audit-measured.json#lcp-baseline
    evidence_tier: real-measured
    acceptance_criteria:
      - { metric: lcp, op: "<=", value: 1100, unit: ms }
      - { metric: cls, op: "<=", value: 0.0, unit: score }
      - { metric: inp, op: "<=", value: 60, unit: ms }
scope:
  do:
    - R1 accessible time inputs + results table
    - R2 client-side CSV export
    - R3 match fastest-incumbent Core Web Vitals
  wont_do:
    - Beat incumbents on raw page speed beyond table-stakes — diminishing returns, not the moat
    - Emit richer schema than competitors — schema presence is table-stakes, not a differentiator
    - Account/login or any server-side state — violates the free+static+client-side constraint
  skipped:
    - item: Multi-worker / team timesheets
      reason: Demand is a HYPOTHESIS; promote to v2 only if open question OQ1 resolves with measured volume.
    - item: Timezone-aware shift math
      reason: Deferred to v2; trigger = support tickets or measured search demand for timezone queries.
budgets:
  lcp_ms: 1100
  cls: 0.0
  inp_ms: 60
  a11y_score: 95
  word_count_min: 1400
schema_targets:
  - WebApplication
  - FAQPage
  - BreadcrumbList
monetization:
  ad_slots_max: 2
  above_fold_ads: false
open_questions:
  - item: Multi-worker / team timesheets
    owner: Sanjay
    resolve_by: v1-launch + 30 days
  - item: Per-variant keyword volume for 'timesheet' vs 'time card'
    owner: Sanjay
    resolve_by: pre-v2 keyword re-measure
```

---

## 4. `prd-trace.md`

The traceability ledger — one row per requirement, mirroring the PRD
Traceability Appendix. `prd_lint` requires entries >= requirements; every id
here must match a `build-spec.json` requirement id.

```markdown
# Traceability — time-card-calculator v1.0

| id | source_ref | evidence_tier |
|----|------------|---------------|
| R1 | gaps.json#accessibility | real-measured |
| R2 | gaps.json#csv-export | triangulated |
| R3 | audit-measured.json#lcp-baseline | real-measured |
```

---

## 5. Handoff summary (printed at end of stage 8)

Print this block to the conversation after the files are written — it is the
PM-facing receipt, not a file.

```
PRD HANDOFF — time-card-calculator v1.0   [FINAL]

North-star: organic_sessions_to_calculation_rate >= 60% of organic landings
            complete one calculation.

Top requirements (must-have, all traceable + measurable):
  R1  Accessible inputs + results table  (lighthouse_a11y >= 95, axe 0 serious)
  R2  Client-side CSV export             (valid RFC-4180, export <= 200 ms)
  R3  Match fastest-incumbent CWV        (LCP <= 1100 ms, CLS <= 0.0, INP <= 60 ms) [should]

Scope: 3 do / 3 won't-do / 2 skipped.
Open questions: 2 quarantined, each owned (multi-worker demand; per-variant volume).

Blocker resolutions: 0 hard-blocks — no v1 must-have rested on weak evidence.
                     Multi-worker (HYPOTHESIS) downgraded to skipped + open question.

Validation: prd_lint.py PASS (0 violations) + prd-skeptic-workflow.js PASS (3/3 kept).
Files written: PRD.md, build-spec.json, build-spec.yaml, prd-trace.md
```

If either validator FAILed, the header reads `DRAFT-INCOMPLETE`, the
"Validation" line lists the violation laws + ids, and "Blocker resolutions"
states what the human must choose (re-measure upstream, or downgrade) per
funnel stage 7.
