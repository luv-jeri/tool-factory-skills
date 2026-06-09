# PRD Template (14 sections)

Copy this file to `PRD.md` in the tool build folder and fill every section. The
`##` headers below are the canonical section headers — they match
`REQUIRED_SECTIONS` in `scripts/prd_lint.py` verbatim and in order, so a PRD
built from this template passes `check_completeness`. Do NOT rename, reorder, or
delete a header. Every section must be non-empty (the engine fails on an empty
section).

The italic `Source:` line under each header records which `prd_seed` / ledger
field fills that section. These are plain italic notes, not HTML comments, so the
file stays lint-clean. Keep them; replace the instructional prose and the worked
`Example:` line with real content.

The PRD title line carries the status stamp. Use `DRAFT-INCOMPLETE` until both
`prd_lint.py` PASSes and the skeptic PASSes; only then promote to `FINAL`.

```
# PRD — <tool-name> — DRAFT-INCOMPLETE
```

---

## Exec Summary

*Source: prd_seed.positioning + differentiation_moat.*

PM-facing TL;DR, 200 words or fewer: what the product is, the north-star goal,
the target we must hit, and the one-line "why we win."

Example: Time-Card Calculator is a free, static, client-side timesheet tool that
turns punch in/out rows into paid hours and gross pay; we win on a measured
Lighthouse a11y score of 100 versus a competitor baseline of 78.

## Goal & Success Metrics

*Source: prd_seed.target_cluster + analyst-defined.*

The single north-star metric, the measurable target we must hit, and supporting
KPIs. State each as a number with a unit.

Example: North-star = task-completion rate >= 90 percent; supporting KPI =
calculation error rate <= 0 incidents per 1000 sessions.

## Background & Evidence

*Source: brief executive summary + refuted_prior_assumptions.*

The market wedge, the shape of the field, and prior assumptions the competitive
brief refuted, distilled from the measured brief.

Example: Top 3 ranking tools share a 78 median Lighthouse a11y score; the prior
assumption that "users want a multi-week grid" was refuted by 0 of 5 top tools
shipping one.

## Personas & Jobs-to-be-Done

*Source: prd_seed.jobs_to_be_done.*

Who uses this and the job they hire it to do. One line per persona + JTBD.

Example: Hourly worker — "When my shift ends, I want to total my paid hours so I
can check my paycheck is correct."

## Scope

*Source: prd_seed.must_have / v2 / out_of_scope, classified per scope-rubric.md.*

Three-sided scope. Every candidate feature lands in exactly one subsection. See
`references/scope-rubric.md`. The engine (IRON LAW 4 / `check_scope`) fails if any
side is empty.

### Do

Committed v1, evidence-backed in-scope features.

Example: Labeled form inputs meeting WCAG 2.2 AA; CSV export of the computed
timesheet.

### Won't-Do

Explicit non-goals — state *why not*.

Example: Beating incumbents on raw render speed beyond table-stakes — raw speed is
table-stakes, not a differentiator.

### Skipped-For-Now

Deferred to v2 — state the trigger that would promote each item.

Example: Multi-worker batch entry (HYPOTHESIS) — promote if post-launch analytics
show >= 20 percent of sessions adding more than one worker.

## Functional Requirements

*Source: stage-1 requirement records; mirrored by build-spec.json `requirements[]`.*

One row per requirement. The `id` column uses `R1`, `R2`, … and MUST match the
ids in `build-spec.json` (IRON LAW 5 / `check_agreement`). Every `must`/`should`
row needs a measurable `acceptance_criteria` (IRON LAW 3). See
`references/requirement-rubric.md`.

| id | priority | statement | source_ref | evidence_tier | acceptance_criteria |
|----|----------|-----------|------------|---------------|---------------------|
| R1 | must | Labeled inputs meet WCAG 2.2 AA | gaps.json#a11y | real-measured | lighthouse_a11y >= 95 score |
| R2 | should | Export computed timesheet as CSV | prd_seed.must_have#csv | triangulated | csv_export == true |

## UI/UX Spec

*Source: analyst + brief UX teardown.*

How it should look: page layout, key screens and states, primary interaction
flow, responsive breakpoints, and the empty / loading / error states.

Example: Single-page layout; input table with one row per punch; live total
panel pinned right on >= 768 px viewports and stacked below on narrower ones;
empty state shows one blank row with placeholder times.

## Benchmarks

*Source: prd_seed.performance_budget / a11y_target / seo_content_spec + audit-measured.json baselines.*

Non-functional targets, each with the **competitor baseline** to beat or match.
Numbers required (IRON LAW 3). Cover performance (LCP / CLS / INP), a11y, SEO /
schema, content length, and browser / device support.

| metric | our_target | competitor_baseline | source |
|--------|-----------|---------------------|--------|
| lcp_ms | 1100 | 2400 | audit-measured.json#lcp |
| cls | 0.0 | 0.18 | audit-measured.json#cls |
| lighthouse_a11y | 100 | 78 | audit-measured.json#a11y |
| word_count | 700 | 350 | audit-measured.json#content |

## Monetization & Constraints

*Source: prd_seed.monetization_notes.*

Ad-density ceiling and the hard constraints: free, static, client-side only, no
login.

Example: Max 1 ad unit above the fold; 100 percent client-side compute; no
server, no account, no PII stored.

## Analytics & Instrumentation

*Source: analyst-defined from the Goal & Success Metrics section.*

What to measure post-launch to confirm the north-star and KPIs are met.

Example: Fire a `calc_completed` event on each total; track CSV-export click rate;
sample Core Web Vitals via the field RUM endpoint.

## Assumptions & Open Questions

*Source: prd_seed.open_questions + every inherited UNVERIFIED / HYPOTHESIS tier.*

Each unverified belief and open question with an owner and a resolve-by date. Any
must-have resting on weak evidence is demoted to v2 and registered here (IRON LAW
2). An assumption-tier requirement with no `source_ref` is only allowed if its
`item` or `id` is owned here.

| item | risk | owner | resolve_by |
|------|------|-------|------------|
| Users want multi-worker entry | Builds a feature nobody uses | analyst | 2026-07-01 |

## Risks & Mitigations

*Source: brief Risks + analyst.*

Top risks to the launch and how each is mitigated.

Example: Risk — an AI Overview answers the calculation inline, cutting clicks;
Mitigation — add an interactive CSV export and saved-state value the SERP cannot
replicate.

## Milestones / Definition of Done

*Source: analyst — the launch gate.*

The launch gate: which requirements and which benchmark numbers must be green to
ship v1.

Example: v1 ships when R1 and R2 pass, lighthouse_a11y >= 95, and lcp_ms <= 1100
on the audit harness.

## Traceability Appendix

*Source: full requirement-id map; mirrored by prd-trace.md.*

The full map of requirement id to source_ref to evidence_tier.

| id | source_ref | evidence_tier |
|----|------------|---------------|
| R1 | gaps.json#a11y | real-measured |
| R2 | prd_seed.must_have#csv | triangulated |
