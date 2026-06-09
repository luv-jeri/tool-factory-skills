# Scoring model — deterministic, evidence-gated

> **Contract:** `scripts/competitor_strength.py` and `scripts/gap_opportunity.py` are the single sources of
> truth. **If a table in this document and a script disagree, the script wins and this doc is the bug; change
> both in the same commit.**

## Contents

1. [Evidence tiers](#evidence-tiers)
2. [Fail-closed gates](#fail-closed-gates)
3. [`competitor_strength` — dimension rules](#competitor_strength--dimension-rules)
4. [`gap_opportunity` — gap scoring rules](#gap_opportunity--gap-scoring-rules)
5. [Worked calibration](#worked-calibration)
6. [Tuning note](#tuning-note)

---

## Evidence tiers

Every claim in the brief carries exactly one tier. Tier assignment is immutable after measurement.

| Tier | Definition | Committable? |
|---|---|---|
| **real-measured** | We ran the tool / parsed the JSON-LD / captured the live SERP / ran Lighthouse ourselves | YES |
| **triangulated** | ≥2 independent free sources agree (e.g. OpenPageRank + Ahrefs free checker) | YES |
| **reasoned** | Inference from adjacent evidence; no direct measurement | NO — hypothesis only |

**Commit an exploit only on real-measured or triangulated.** `reasoned` = a hypothesis the PRD must test.
An `UNVERIFIED` claim is reasoned by default and cannot be used as a recommendation. This rule kills the
prior "UNVERIFIED schema" failure mode.

---

## Fail-closed gates

Gates fire before scoring. A gated condition returns a labelled block (`GATE A / B / C`) — never a silent 0.

| Gate | Stage | Condition | Action |
|---|---|---|---|
| **A** | Stage 1 (Discover) | Fewer than 3 real cluster-competing URLs found on live SERP | **REFUSE** — do not fabricate a landscape |
| **B** | Stage 3 (per field) | Any required measured field absent or unverifiable | Tag claim `UNVERIFIED`; field cannot back a committed exploit |
| **C** | Stage 5/6 (Gap synthesis) | AI Overview fully answers the JTBD for the cluster | Raise **existential-risk flag** before claiming any opportunity |

The engine enforces B: `ContractError` is raised on missing or ill-typed fields (see `validate()` in both scripts).

---

## `competitor_strength` — dimension rules

### Formula

```
strength = (0.30·Authority + 0.25·SERP + 0.15·Content
            + 0.12·Feature + 0.13·UX_Perf_A11y + 0.05·Trust) × 20
```

Range: **20..100**. Each dimension is a deterministic 1..5 sub-score.

### Weight table

| Dimension | Weight |
|---|---|
| authority | 0.30 |
| serp | 0.25 |
| content | 0.15 |
| ux_perf_a11y | 0.13 |
| feature | 0.12 |
| trust | 0.05 |
| **Total** | **1.00** |

Weights are **v0 UNCALIBRATED** — see `docs/adr/0002-scoring-weights.md`.

### Required input fields

`dr` `referring_domains` `serp_rank` `ai_overview_cited` `serp_features_owned`
`word_count` `heading_count` `schema_types` `paa_coverage` `feature_coverage`
`lcp_ms` `cls` `inp_ms` `a11y_score` `clicks_to_result` `trust_signals`

All required. Missing any → `ContractError` (fail closed).

---

### authority (weight 0.30)

Blended sub-score: `round(0.6 × dr_sc + 0.4 × rd_sc)`, clamped 1..5.

| Sub-score | DR rule |
|---|---|
| 5 | dr ≥ 70 |
| 4 | dr ≥ 50 |
| 3 | dr ≥ 30 |
| 2 | dr ≥ 15 |
| 1 | dr < 15 |

| Sub-score | referring_domains rule |
|---|---|
| 5 | referring_domains ≥ 1000 |
| 4 | referring_domains ≥ 300 |
| 3 | referring_domains ≥ 50 |
| 2 | referring_domains ≥ 10 |
| 1 | referring_domains < 10 |

---

### serp (weight 0.25)

Base from `serp_rank`, then +1 bonus if `ai_overview_cited=True` OR `serp_features_owned ≥ 2`. Clamped 1..5.

| Sub-score | serp_rank rule |
|---|---|
| 5 | rank == 1 |
| 4 | rank ≤ 3 |
| 3 | rank ≤ 6 |
| 2 | rank ≤ 10 |
| 1 | rank > 10 or None |

Bonus: `+1` (cap 5) when `ai_overview_cited` is `True` OR `serp_features_owned ≥ 2`.

---

### content (weight 0.15)

Average of four sub-scores (word-count, structure, schema, PAA), rounded, clamped 1..5.

| Sub-score | word_count rule |
|---|---|
| 5 | word_count ≥ 1500 |
| 4 | word_count ≥ 1000 |
| 3 | word_count ≥ 600 |
| 2 | word_count ≥ 300 |
| 1 | word_count < 300 |

| Sub-score | heading_count rule |
|---|---|
| 5 | heading_count ≥ 8 |
| 3 | heading_count ≥ 4 |
| 1 | heading_count < 4 |

| Sub-score | schema_types rule (len of list) |
|---|---|
| 5 | len ≥ 2 |
| 3 | len == 1 |
| 1 | len == 0 (empty list) |

PAA sub-score: `clamp(round(1 + 4 × paa_coverage), 1, 5)` where `paa_coverage` ∈ [0.0, 1.0].

---

### feature (weight 0.12)

`clamp(round(1 + 4 × feature_coverage), 1, 5)` where `feature_coverage` ∈ [0.0, 1.0].

---

### ux_perf_a11y (weight 0.13)

Average of perf_sc, a11y_sc, ux_sc, rounded, clamped 1..5. `perf_sc` is itself the round-average of lcp_sc + cls_sc + inp_sc.

| Sub-score | lcp_ms rule |
|---|---|
| 5 | lcp_ms ≤ 2500 |
| 3 | lcp_ms ≤ 4000 |
| 1 | lcp_ms > 4000 |

| Sub-score | cls rule |
|---|---|
| 5 | cls ≤ 0.1 |
| 3 | cls ≤ 0.25 |
| 1 | cls > 0.25 |

| Sub-score | inp_ms rule |
|---|---|
| 5 | inp_ms ≤ 200 |
| 3 | inp_ms ≤ 500 |
| 1 | inp_ms > 500 |

a11y sub-score: `clamp(round(1 + 4 × (a11y_score / 100)), 1, 5)`.

| Sub-score | clicks_to_result rule |
|---|---|
| 5 | clicks_to_result ≤ 2 |
| 4 | clicks_to_result ≤ 4 |
| 3 | clicks_to_result ≤ 6 |
| 2 | clicks_to_result ≤ 8 |
| 1 | clicks_to_result > 8 |

---

### trust (weight 0.05)

| Sub-score | trust_signals rule |
|---|---|
| 5 | trust_signals ≥ 5 |
| 4 | trust_signals == 4 |
| 3 | trust_signals ≥ 2 |
| 2 | trust_signals == 1 |
| 1 | trust_signals == 0 |

---

## `gap_opportunity` — gap scoring rules

### Formula

```
base        = (0.35·demand + 0.30·incumbent_weakness + 0.20·ai_resistance
               + 0.15·defensibility) × 20                    # 20..100
opportunity = base × buildability_factor × weakness_gate
```

### Inputs (all int 1..5)

| Field | Meaning |
|---|---|
| demand | Cluster volume + PAA evidence (reuse pick-next-tool volume buckets) |
| incumbent_weakness | How many top competitors measurably fail the gap and how badly |
| ai_resistance | Does shipping it make us more interactive/stateful → harder to replace |
| defensibility | Durability vs trivially copied |
| buildability | Enum (see below) — static Astro feasibility |
| evidence_tier | `real-measured` / `triangulated` / `reasoned` |

### Buildability factor map

| buildability value | factor |
|---|---|
| `not_shippable` | 0.0 |
| `high` (effort) | 0.6 |
| `medium` | 0.8 |
| `trivial` | 1.0 |

### weakness_gate

`weakness_gate = 0.0 if incumbent_weakness ≤ 1 else 1.0`

A gap all competitors already solved (`incumbent_weakness ≤ 1`) is zeroed out — it is not a real gap.

### reasoned → hypothesis rule

If `evidence_tier == "reasoned"`, tier is forced to `"hypothesis"` and `committable = False`, regardless of
the numeric score. A high-scoring hypothesis is still only a hypothesis.

### Tier cutoffs

| opportunity | tier |
|---|---|
| ≥ 70 | `build-now` |
| 40–69 | `v2` |
| < 40 | `skip` |
| == 0 | `skip` (not_shippable or weakness_gate=0) |
| (reasoned) | `hypothesis` |

---

## Worked calibration

### Snapshot A — strong incumbent → **88.2**

Input (from `_selftest()` in `competitor_strength.py`):

```
dr=84, referring_domains=1500, serp_rank=1, ai_overview_cited=True,
serp_features_owned=2, word_count=490, heading_count=6,
schema_types=["WebApplication"], paa_coverage=0.3,
feature_coverage=0.6, lcp_ms=2200, cls=0.05, inp_ms=180,
a11y_score=78, clicks_to_result=2, trust_signals=4
```

Step-by-step:

| Dimension | Calculation | Score |
|---|---|---|
| authority | dr=84→5, rd=1500→5; 0.6×5+0.4×5=5.0 → **5** | 5 |
| serp | rank=1→base=5; bonus=+1 (ai_overview_cited=True); clamp(6,1,5)=**5** | 5 |
| content | wc=490→2; h=6→3; schema len=1→3; paa=round(1+4×0.3)=round(2.2)=2; avg=(2+3+3+2)/4=2.5→round=**3** | 3 |
| feature | round(1+4×0.6)=round(3.4)=**3** | 3 |
| ux_perf_a11y | lcp=2200→5; cls=0.05→5; inp=180→5; perf=round(5)=5; a11y=round(1+4×0.78)=round(4.12)=4; ux(clicks=2)=5; avg=(5+4+5)/3=4.67→round=**5** | 5 |
| trust | trust_signals=4→**4** | 4 |

`strength = (0.30×5 + 0.25×5 + 0.15×3 + 0.12×3 + 0.13×5 + 0.05×4) × 20`
`= (1.50 + 1.25 + 0.45 + 0.36 + 0.65 + 0.20) × 20`
`= 4.41 × 20 = 88.2` ✓

---

### Snapshot B — gap opportunity → **64.8 / v2**

Input (from `_selftest()` in `gap_opportunity.py`):

```
demand=4, incumbent_weakness=4, ai_resistance=5,
defensibility=3, buildability="medium", evidence_tier="real-measured"
```

`base = (0.35×4 + 0.30×4 + 0.20×5 + 0.15×3) × 20`
`= (1.40 + 1.20 + 1.00 + 0.45) × 20`
`= 4.05 × 20 = 81.0`

`weakness_gate = 1.0` (incumbent_weakness=4 > 1)
`buildability_factor = 0.8` (medium)
`opportunity = 81.0 × 0.8 × 1.0 = 64.8`
tier = `v2` (40 ≤ 64.8 < 70) ✓

---

## Tuning note

All weights are **v0 UNCALIBRATED** — set from first-principles judgment, not outcome data. They live as
tunable dicts at the top of each script and are revisited once real shipped tools produce outcome signals.
Full rationale: `docs/adr/0002-scoring-weights.md`.
