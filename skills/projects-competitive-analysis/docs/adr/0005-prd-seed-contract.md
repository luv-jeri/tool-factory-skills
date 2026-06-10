# PRD-SEED contract — the handoff is a YAML `prd_seed:` block; field names are frozen

**Status:** accepted

## Context

The projects-competitive-analysis skill's primary deliverable is not a prose report — it is
a structured data block that seeds the next stage of the pipeline: PRD generation.
If field names drift between runs the downstream PRD-generation skill cannot parse
the handoff without bespoke mapping logic. Field names are an API surface. They must
be frozen now, before any downstream consumer is written, and treated as a
breaking-change boundary thereafter.

The gap tier vocabulary is defined by `scripts/gap_opportunity.py` and must be used
verbatim in the block: `build-now`, `v2`, `skip`, `hypothesis`.
`must_have_features` entries map to `build-now` gaps; `v2_features` entries map to
`v2` gaps.

## Decision

The projects-competitive-analysis skill appends a fenced YAML block to `COMPETITIVE-BRIEF.md`
(Section 8 of the brief). The block is led by the key `prd_seed:`. The future
PRD-generation skill reads this block directly by parsing the fenced YAML in-file —
it is a hard failure if the block is absent or its YAML is malformed.

The following 14 field names are **frozen** (semver-style: renaming or removing a
field requires a new major version tag and a migration note in `SKILL.md`):

```yaml
prd_seed:
  positioning: "<one-line winning insight — why our build wins on measured gaps>"

  target_cluster:
    head_term: "<e.g. timesheet calculator>"
    monthly_volume_bucket: "<10K-100K>"
    kw_count: 0

  jobs_to_be_done:
    - "<primary JTBD>"
    - "<secondary JTBD>"

  must_have_features:
    - feature: "<feature name>"
      gap_opportunity_score: 0.0
      evidence: "<claim_id(s) from research-raw.json>"
    # one entry per build-now gap (tier = build-now in gap_opportunity.py)

  v2_features:
    - feature: "<feature name>"
      gap_opportunity_score: 0.0
      evidence: "<claim_id(s)>"
    # one entry per v2 gap (tier = v2 in gap_opportunity.py)

  out_of_scope:
    - "<feature or scope item explicitly excluded>"

  differentiation_moat: "<what makes the positioning durable>"

  ai_overview_risk:
    level: low   # low | med | high | existential
    what_aio_covers: "<what the AI Overview currently answers for this cluster>"
    mitigation: "<how we remain necessary despite AIO>"

  seo_content_spec:
    word_count_target: 0
    headings:
      - "<H2 topic>"
    schema_types:
      - WebApplication
    paa_to_answer:
      - "<PAA question from live SERP>"

  performance_budget:
    lcp_ms: 0
    cls: 0.0
    inp_ms: 0

  a11y_target: "WCAG 2.2 AA + Lighthouse a11y ≥ <best measured competitor score>"

  monetization_notes:
    ad_density_ceiling: "<e.g. max 2 units above fold>"
    ladder_step: "<e.g. email capture for CSV export>"

  open_questions:
    - "<reasoned-tier hypothesis to validate post-launch>"

  source_ledger_ref: research-raw.json
```

**Frozen field names (14):**
`positioning`, `target_cluster`, `jobs_to_be_done`, `must_have_features`,
`v2_features`, `out_of_scope`, `differentiation_moat`, `ai_overview_risk`,
`seo_content_spec`, `performance_budget`, `a11y_target`, `monetization_notes`,
`open_questions`, `source_ledger_ref`.

**Gap tier vocabulary** (from `scripts/gap_opportunity.py`):
`build-now` | `v2` | `skip` | `hypothesis`

The four valid tiers are exhaustive — no other tier name is permitted. Gaps scoring into the `build-now` tier populate
`must_have_features`; gaps scoring into the `v2` tier populate `v2_features`.
`hypothesis` gaps are unverified (reasoned-tier evidence only) and are NOT listed in
either feature field — they surface only in `open_questions`.

## Consequences

- Field names are a breaking-change surface. Renaming or removing a field bumps the
  contract version in `SKILL.md` and requires a migration note.
- The prose brief is still produced for human consumption, but it is secondary to the
  `prd_seed:` block. The YAML block is the ground truth for downstream automation.
- Adding new optional fields is non-breaking (the PRD skill ignores unknown keys).
- All automated tests (`evals/evals.json`) validate that the `prd_seed:` block is
  present, parses as valid YAML, and contains all 14 required top-level keys.
- The block is embedded directly in `COMPETITIVE-BRIEF.md` (not a separate file),
  making the brief self-contained and the handoff human-inspectable.

## Considered and rejected

- **Emit only prose; let the PRD skill parse natural language:** rejected. Natural
  language parsing of competitive briefs is fragile and non-deterministic. A
  machine-readable contract is the correct boundary between pipeline stages.
- **A separate JSON block with a `<!-- PRD_SEED -->` HTML comment marker:** rejected.
  A separate JSON artefact duplicates information already in the brief, forces
  consumers to locate a second file, and is less human-readable than inline YAML.
  The single in-brief `prd_seed:` YAML block is simpler, human-readable, and keeps
  one source of truth.
- **TOML or other formats:** rejected. YAML is readable, stdlib-parseable in Python
  (`yaml.safe_load`), and already the natural format for structured front-matter in
  Markdown documents. The brief is written in Markdown, so inline YAML is idiomatic.
