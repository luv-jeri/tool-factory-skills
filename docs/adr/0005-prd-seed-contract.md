# PRD seed contract — the handoff is a machine-readable block; field names are frozen

**Status:** accepted

The competitive-analysis skill's primary deliverable is not a prose report — it is
a structured data block that seeds the next stage of the pipeline: PRD generation.
If the field names drift between runs (e.g. `incumbent_weakness` becomes
`competitor_weakness` in one output, `gap_weakness` in another), the downstream
PRD-generation skill cannot parse the handoff without bespoke mapping logic.
Field names are an API surface. They must be frozen now, before any downstream
consumer is written, and treated as a breaking-change boundary thereafter.

## Decision

The competitive-analysis skill always emits a `<!-- PRD_SEED -->` block at the
end of its output. The block is valid JSON. The following field names are **frozen**
(semver-style: changes require a new major version tag and migration note):

```json
{
  "tool_slug": "string — kebab-case, e.g. time-card-calculator",
  "analysis_date": "YYYY-MM-DD",
  "evidence_tier": "real-measured | triangulated | reasoned",
  "top_competitors": [
    {
      "url": "string",
      "dr": "number (0–100, normalised)",
      "performance_score": "number (0–100, Lighthouse)",
      "lcp_ms": "number",
      "a11y_score": "number (0–100, Lighthouse)",
      "schema_types": ["string"],
      "serp_features_owned": ["string"]
    }
  ],
  "competitor_strength_score": "number (0–100)",
  "competitor_strength_breakdown": {
    "authority": "number",
    "serp_presence": "number",
    "content_depth": "number",
    "ux_perf_a11y": "number",
    "feature_completeness": "number",
    "trust_signals": "number"
  },
  "gaps": [
    {
      "id": "string — kebab-case",
      "label": "string — human-readable",
      "gap_opportunity_score": "number (0–100)",
      "tier": "build-now | consider | hypothesis",
      "evidence_tier": "real-measured | triangulated | reasoned",
      "demand_score": "number",
      "incumbent_weakness_score": "number",
      "ai_resistance_score": "number",
      "defensibility_score": "number"
    }
  ],
  "build_now_exploits": ["string — gap ids only"],
  "hypothesis_exploits": ["string — gap ids only, reasoned tier, unverified"]
}
```

The PRD-generation skill (when built) will `json.loads()` the `PRD_SEED` block
directly. It is a hard failure if the block is absent or not valid JSON.

## Consequences

- Field names are treated as a breaking-change surface. Renaming a field bumps the
  contract version in `SKILL.md` and requires a migration note.
- The prose report is still produced for human consumption, but it is secondary to
  the JSON block. The JSON block is the ground truth.
- Adding new optional fields is non-breaking (the PRD skill ignores unknown keys).
  Removing or renaming existing fields is breaking and requires a version bump.
- All automated tests (`evals/evals.json`) validate that the PRD_SEED block is
  present and parses as valid JSON with the required top-level keys.

## Considered and rejected

- **Emit only prose; let the PRD skill parse natural language:** rejected. Natural
  language parsing of competitive briefs is fragile and non-deterministic. A
  machine-readable contract is the correct boundary between pipeline stages.
- **Use a different serialisation format (YAML, TOML) for readability:** rejected.
  JSON is the lingua franca for structured inter-agent handoffs; it is unambiguous,
  stdlib-parseable in every target language, and already used by `evals/evals.json`.
  YAML's implicit type coercions are a footgun at API boundaries.
