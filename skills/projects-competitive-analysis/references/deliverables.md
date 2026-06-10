# Deliverables — report template + PRD-SEED contract

Three artifacts are written to `builds/<tool-slug>/` at Stage 7–8.

## Contents

1. [COMPETITIVE-BRIEF.md — section skeleton](#competitive-briefmd--section-skeleton)
2. [research-raw.json — source ledger shape](#research-rawjson--source-ledger-shape)
3. [PRD-SEED YAML block](#prd-seed-yaml-block)

---

## COMPETITIVE-BRIEF.md — section skeleton

Every section is required. A brief missing any section fails Stage 7 PASS.

```markdown
# Competitive Brief — <Tool Name>

- **Date:** YYYY-MM-DD
- **Methodology:** staged + gated pipeline (see references/audit-procedure.md)
- **Source ledger:** research-raw.json (every claim is traceable)
- **Tool slug:** <tool-slug>
- **Skill version:** projects-competitive-analysis v<x>

---

## 1. Executive summary

<One-paragraph wedge/positioning — the single insight that drives the build.>

**Top 5 ranked opportunities** (from gap_opportunity.py output):

| Rank | Gap | Opportunity score | Tier | Evidence tier |
|---|---|---|---|---|
| 1 | ... | ... | build-now | real-measured |
| ... | | | | |

---

## 2. Per-competitor profiles

### <Competitor Name> — strength: <score>/100

**Strongest dimensions:** <list>
**Weakest dimensions:** <list> ← exploit targets

#### 10-pillar scorecard

| Pillar | Score (1–5) | Key measured values |
|---|---|---|
| Authority | x/5 | DR=nn, referring_domains=nnn |
| SERP | x/5 | rank=n, ai_overview_cited=T/F, features=n |
| Content depth | x/5 | word_count=nnn, headings=n, schema=[...] |
| Feature | x/5 | feature_coverage=0.xx |
| UX/Perf/A11y | x/5 | LCP=nnnn ms, CLS=0.xx, INP=nnn ms, a11y=nn |
| Trust | x/5 | trust_signals=n |

**Screenshots:** ![desktop](<slug>-desktop.png) ![mobile](<slug>-mobile.png)

**Weaknesses to exploit:** <numbered list — real-measured or triangulated evidence only>

---

[Repeat per competitor]

---

## 3. Master feature matrix

| Feature | <Comp A> | <Comp B> | ... | Our target |
|---|---|---|---|---|
| OT > 8hr/day | ✓ | ✗ | ... | ✓ |
| ... | | | | |

Gated features (behind email/paywall) are marked ⊙.

---

## 4. Empirical dashboards

### CWV table

| Competitor | LCP (ms) | CLS | INP (ms) | Perf score | Measured |
|---|---|---|---|---|---|
| ... | | | | | YYYY-MM-DD |

### A11y table

| Competitor | Lighthouse a11y score | Critical issues | Measured |
|---|---|---|---|
| ... | | | YYYY-MM-DD |

### Ad-density table

| Competitor | Ad network | Above-fold units | Est. density | Layout shift from ads |
|---|---|---|---|---|
| ... | | | | |

### SERP / AI-Overview table

| Competitor | Head-term rank | AI-Overview cited | SERP features owned | PAA coverage |
|---|---|---|---|---|
| ... | | T/F | n | 0.xx |

---

## 5. Ranked gap-opportunity table

(Produced by gap_opportunity.py — do not edit numbers manually.)

| Rank | Gap description | Opportunity | Tier | Demand | Inc. weakness | AI resistance | Defensibility | Buildability | Evidence tier |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ... | 0.0 | build-now | 5 | 4 | 4 | 3 | trivial | real-measured |
| ... | | | | | | | | | |

---

## 6. Wedge & differentiation moat

<3–5 sentences. What we build, why it wins, why it is durable. Grounded in measured gaps.>

---

## 7. Risks

- **AI-Overview risk:** <level + what the AIO covers + mitigation>
- **Authority wall:** <DR gap to top competitors + what we can realistically achieve>
- **Other risks:** <mobile parity, ad UX, schema arms race, etc.>

---

## 8. PRD-SEED block

(See Section 3 of this document for the full YAML schema.)

\`\`\`yaml
prd_seed:
  ...
\`\`\`
```

---

## research-raw.json — source ledger shape

Every claim in the brief traces to an entry here. The file is the audit trail.

```jsonc
{
  "tool_slug": "time-card-calculator",
  "generated_at": "YYYY-MM-DDTHH:MM:SSZ",
  "skill_version": "projects-competitive-analysis v1",

  // Top-level claim ledger: each entry backs one fact in the brief.
  "claims": [
    {
      "claim_id": "c001",
      "value": "DR 84",
      "url": "https://openpagerank.com/api/v1.0/getPageRank?domains[0]=example.com",
      "date_accessed": "2026-06-09",
      "method": "OpenPageRank API",
      "evidence_tier": "triangulated",
      "competitor": "example.com",
      "field": "dr"
    }
    // ... one entry per measured value
  ],

  // Per-competitor raw measured records (schema-validated output from audit-workflow.js).
  "competitors": {
    "example.com": {
      // All REQUIRED_FIELDS from competitor_strength.py:
      "dr": 84,
      "referring_domains": 1500,
      "serp_rank": 1,
      "ai_overview_cited": true,
      "serp_features_owned": 2,
      "word_count": 490,
      "heading_count": 6,
      "schema_types": ["WebApplication"],
      "paa_coverage": 0.3,
      "feature_coverage": 0.6,
      "lcp_ms": 2200,
      "cls": 0.05,
      "inp_ms": 180,
      "a11y_score": 78,
      "clicks_to_result": 2,
      "trust_signals": 4,
      // Evidence tier per field:
      "_evidence_tiers": {
        "dr": "triangulated",
        "referring_domains": "triangulated",
        "serp_rank": "real-measured",
        "ai_overview_cited": "real-measured",
        "serp_features_owned": "real-measured",
        "word_count": "real-measured",
        "heading_count": "real-measured",
        "schema_types": "real-measured",
        "paa_coverage": "real-measured",
        "feature_coverage": "real-measured",
        "lcp_ms": "real-measured",
        "cls": "real-measured",
        "inp_ms": "real-measured",
        "a11y_score": "real-measured",
        "clicks_to_result": "real-measured",
        "trust_signals": "real-measured"
      },
      // Computed scores (from competitor_strength.py):
      "_strength": {
        "strength": 88.2,
        "scores": { "authority": 5, "serp": 5, "content": 3, "feature": 3, "ux_perf_a11y": 5, "trust": 4 },
        "strongest_dimensions": ["authority", "serp", "ux_perf_a11y"],
        "weakest_dimensions": ["content", "feature"]
      },
      // Additional brief fields (not in strength formula):
      "screenshots": {
        "desktop": "screenshots/example-desktop.png",
        "mobile": "screenshots/example-mobile.png"
      },
      "traffic_estimate_monthly": 45000,
      "ad_units_above_fold": 2,
      "gated_features": ["export_csv"]
    }
  },

  // Gap records (input to gap_opportunity.py):
  "gaps": [
    {
      "gap_id": "g001",
      "description": "No real timezone-aware overtime calculation",
      "demand": 4,
      "incumbent_weakness": 4,
      "ai_resistance": 5,
      "defensibility": 3,
      "buildability": "medium",
      "evidence_tier": "real-measured",
      "supporting_claims": ["c012", "c015", "c021"],
      // Computed (from gap_opportunity.py):
      "opportunity": 64.8,
      "tier": "v2",
      "base": 81.0,
      "buildability_factor": 0.8
    }
  ]
}
```

---

## PRD-SEED YAML block

The machine-readable handoff contract. Appended verbatim at the end of `COMPETITIVE-BRIEF.md` inside a
fenced YAML block. The future PRD-generation skill reads this directly — field names are EXACT and must
not be renamed.

```yaml
prd_seed:
  positioning: "<one-line winning insight — why our build wins on measured gaps>"

  target_cluster:
    head_term: "<e.g. timesheet calculator>"
    monthly_volume_bucket: "<10K-100K>"   # from pick-next-tool volume_buckets or measured
    kw_count: 0                            # cluster keyword count

  jobs_to_be_done:
    - "<primary JTBD>"
    - "<secondary JTBD>"

  must_have_features:
    - feature: "<feature name>"
      gap_opportunity_score: 0.0
      evidence: "<claim_id(s) from research-raw.json>"
    # one entry per build-now gap

  v2_features:
    - feature: "<feature name>"
      gap_opportunity_score: 0.0
      evidence: "<claim_id(s)>"
    # one entry per v2 gap

  out_of_scope:
    - "<feature or scope item explicitly excluded>"

  differentiation_moat: "<what makes the positioning durable — e.g. interactive state, UX depth, schema coverage>"

  ai_overview_risk:
    level: low   # low | med | high | existential
    what_aio_covers: "<what the AI Overview currently answers for this cluster>"
    mitigation: "<how we remain necessary despite AIO>"

  pain_points:                       # Pillar 11 — voice-of-customer (verbatim quotes live in the ledger)
    - pain: "<one-line pain statement>"
      evidence: "<claim_id(s) — quote + url + date_accessed in research-raw.json>"
      sources_count: 0               # independent sources expressing it (>=3 required for exploit-grade)
      competitors_failing: []        # who measurably fails it (Pillar 5/6 audit)
      maps_to: "<must_have_feature | v2_feature | open_question>"

  input_ergonomics:                  # Pillar 6 measured baselines for the canonical job
    canonical_job: "<e.g. enter one week of times and get the weekly total>"
    best_competitor_interactions: 0  # lowest measured interactions_to_result across audited rivals
    typed_free_text_fields: []       # structured fields rivals collect by free-text typing (friction to beat)
    target: "<our budget, e.g. <=15 interactions/week, zero typed time fields, native pickers + copy-down>"

  seo_content_spec:
    word_count_target: 0      # set to beat best measured competitor + PAA coverage
    headings:
      - "<H2 topic>"
    schema_types:
      - WebApplication
      # add all types to implement; each rich-result claim must be verified against
      # Google's CURRENT supported structured-data list (<=60 days) or marked parity-only
    paa_to_answer:
      - "<PAA question from live SERP>"

  performance_budget:
    lcp_ms: 0     # set to beat best measured competitor LCP (e.g. best_lcp - 200)
    cls: 0.0      # set to beat best measured competitor CLS
    inp_ms: 0     # set to beat best measured competitor INP

  a11y_target: "WCAG 2.2 AA + Lighthouse a11y ≥ <best measured competitor score>"

  monetization_notes:
    ad_density_ceiling: "<e.g. max 2 units above fold>"
    ladder_step: "<e.g. email capture for CSV export>"

  open_questions:
    - "<reasoned-tier hypothesis to validate post-launch>"

  source_ledger_ref: research-raw.json
```
