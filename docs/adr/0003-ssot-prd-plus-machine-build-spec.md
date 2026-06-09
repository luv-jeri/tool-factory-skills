# ADR-0003: Output is one human SSOT PRD.md plus a frozen machine-readable build-spec

## Status: Accepted

## Context

The deliverable must serve two readers with one truth: a human (PM / dev lead) who
needs prose, an exec summary, and rationale; and a machine (CI, a future build-skill,
a dev parsing the contract) that needs structured, unambiguous records. The failure
mode to avoid is *drift* — two documents that claim to describe the same product but
disagree, so nobody knows which is authoritative.

We also need the deterministic engine (ADR-0001) to do its deep checks somewhere
unambiguous. Running traceability, tier-gating, and measurability checks against
markdown prose means brittle regex against free text; that is fragile and
non-deterministic.

## Decision

The output is exactly two artifacts that mirror each other, plus a trace ledger:

1. **`PRD.md`** — the single human source of truth. It contains all 14 required
   sections (including a PM-facing exec-summary / TL;DR section) in prose + tables.
   Its header reads `FINAL` only when the engine and the skeptic both PASS; otherwise
   `DRAFT-INCOMPLETE`.
2. **`build-spec.json`** (with a `.yaml` twin) — the frozen machine mirror. It is a
   *literal projection* of the requirement records + budgets, with the schema fixed in
   the design spec and `deliverables.md`:
   `tool`, `prd_version`, `generated_from`, `north_star`, `requirements[]`
   (`id`, `priority`, `statement`, `source_ref`, `evidence_tier`,
   `acceptance_criteria[]`), `scope` (`do`, `wont_do`, `skipped`), `budgets`,
   `schema_targets`, `monetization`, `open_questions[]`.
3. **`prd-trace.md`** — the traceability ledger, one entry per requirement
   (`id -> source_ref -> evidence_tier`).

The two primary artifacts must agree, and `prd_lint` enforces it: every section-6
requirement id and every section-8 budget number must appear in `build-spec.json`,
and vice versa. The structured JSON is the authoritative source for all deep,
data-level checks; `PRD.md` is checked only for section presence and for agreement
with the spec. This is one human source of truth, one machine mirror, no drift —
not three competing documents and not a single artifact trying to be both.

## Consequences

- The engine's deep checks run against `build-spec.json`, which is deterministic and
  unambiguous. No brittle prose regex governs a hard gate.
- PRD<->build-spec agreement is a lintable invariant (IRON LAW 5 structural check).
  Drift between the human doc and the machine doc fails the build rather than slipping
  through.
- A downstream build-skill or CI consumes `build-spec.json` directly without parsing
  prose. The PRD stays human-first; the spec stays machine-first; neither has to
  compromise.
- The author must keep the two in sync as they iterate, but that is exactly what the
  agreement check forces — and it is cheaper than reconciling two prose documents by
  hand later.
