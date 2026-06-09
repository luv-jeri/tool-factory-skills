# Evidence gating — exploits require real-measured or triangulated evidence; reasoned = hypothesis only

**Status:** accepted

The prior time-card competitive brief treated unverified schema assumptions as
top-tier exploits. Specifically: "most calculators probably use FAQPage schema" was
asserted as a build-now opportunity without running a single `parse_jsonld.py` check
against actual competitor HTML. That unverified claim then propagated into gap
scoring, inflating the opportunity tier for rich-results optimization. The same
pattern appeared with performance claims ("site X is slow") stated without a
measured LCP/CLS/INP number from Lighthouse. Under the fail-closed principle, an
engine that commits on unverified observations is the most likely path to building
against a phantom gap.

## Decision

Every field that feeds `competitor_strength` or `gap_opportunity` scoring carries
an explicit evidence tier:

- **`real-measured`** — the value was obtained by running an automated tool against
  the live page (Lighthouse audit, `parse_jsonld.py` HTML parse, OpenPageRank API
  call, Lighthouse a11y audit). The tool, URL, and date are cited.
- **`triangulated`** — two or more independent proxy sources agree on the value. The
  sources are named.
- **`reasoned`** — the value was inferred or assumed. The field is tagged
  `UNVERIFIED` in the output block and **must not** be used as a committed exploit or
  a build-now justification. It may appear in the report as a *hypothesis to verify*.

The engine will not emit a `tier: build-now` gap without `real-measured` or
`triangulated` evidence on the `incumbent_weakness` sub-field for that gap. A
`reasoned` incumbent_weakness locks the gap at `tier: hypothesis`.

## Consequences

- Schema gaps, performance gaps, and a11y gaps are only promotable to build-now
  after `parse_jsonld.py`, Lighthouse, or a11y tooling has been run against the
  full triaged competitor set (not a sample).
- The output report's "exploit" section separates confirmed exploits (measured) from
  candidate exploits (reasoned / partially triangulated).
- Running the browser-driven audit pipeline is not optional for a committed output —
  it is the evidence-gating checkpoint.

## Considered and rejected

- **Allow reasoned evidence for schema/performance claims because "it's usually
  right":** rejected. The prior brief was the exact counter-example — assumed FAQPage
  schema across 9 competitors, none had been checked. Probabilistic correctness is not
  evidence; it is a prior that must be updated by measurement.
- **Gate only high-weight fields:** rejected. Partial gating creates unpredictable
  holes. All fields that flow into scoring carry tiers, or the tier system is
  untrustworthy.
