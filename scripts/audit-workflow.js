export const meta = {
  name: 'competitive-audit',
  description: 'Per-competitor empirical audit: a researcher measures all 10 pillars, an adversarial skeptic re-verifies the 3 most decision-critical claims.',
  phases: [
    { title: 'Audit', detail: 'one researcher per competitor — measured fields' },
    { title: 'Verify', detail: 'one skeptic per competitor — refute weak claims' },
  ],
}

const RESEARCHER_SCHEMA = {
  type: 'object',
  required: ['name', 'url', 'fields', 'evidence'],
  properties: {
    name: { type: 'string' },
    url: { type: 'string' },
    fields: {
      type: 'object',
      description: 'Measured pillar fields. Use null + an evidence tier of "reasoned" when a value could not be measured — never invent a number.',
      required: [
        'dr', 'referring_domains', 'serp_rank', 'ai_overview_cited',
        'serp_features_owned', 'word_count', 'heading_count', 'schema_types',
        'paa_coverage', 'feature_coverage', 'lcp_ms', 'cls', 'inp_ms',
        'a11y_score', 'clicks_to_result', 'trust_signals',
      ],
      properties: {
        dr: { type: ['number', 'null'] },
        referring_domains: { type: ['number', 'null'] },
        serp_rank: { type: ['number', 'null'] },
        ai_overview_cited: { type: ['boolean', 'null'] },
        serp_features_owned: { type: ['number', 'null'] },
        word_count: { type: ['number', 'null'] },
        heading_count: { type: ['number', 'null'] },
        schema_types: { type: 'array', items: { type: 'string' } },
        paa_coverage: { type: ['number', 'null'] },
        feature_coverage: { type: ['number', 'null'] },
        lcp_ms: { type: ['number', 'null'] },
        cls: { type: ['number', 'null'] },
        inp_ms: { type: ['number', 'null'] },
        a11y_score: { type: ['number', 'null'] },
        clicks_to_result: { type: ['number', 'null'] },
        trust_signals: { type: ['number', 'null'] },
      },
    },
    screenshots: { type: 'array', items: { type: 'string' } },
    evidence: {
      type: 'array',
      description: 'One ledger row per field that mattered.',
      items: {
        type: 'object',
        required: ['field', 'value', 'method', 'evidence_tier'],
        properties: {
          field: { type: 'string' },
          value: {},
          url: { type: 'string' },
          method: { type: 'string' },
          evidence_tier: { type: 'string', enum: ['real-measured', 'triangulated', 'reasoned'] },
        },
      },
    },
  },
}

const SKEPTIC_SCHEMA = {
  type: 'object',
  required: ['name', 'verdicts'],
  properties: {
    name: { type: 'string' },
    verdicts: {
      type: 'array',
      description: 'One verdict per re-checked claim (traffic, schema presence, live ranking, AI-Overview presence).',
      items: {
        type: 'object',
        required: ['claim', 'refuted', 'corrected_value', 'evidence_tier'],
        properties: {
          claim: { type: 'string' },
          refuted: { type: 'boolean' },
          corrected_value: {},
          evidence_tier: { type: 'string', enum: ['real-measured', 'triangulated', 'reasoned'] },
          note: { type: 'string' },
        },
      },
    },
  },
}

const competitors = (args && args.competitors) || []
const cluster = (args && args.cluster) || ''
if (!competitors.length) {
  log('No competitors passed in args.competitors — nothing to audit.')
  return { audited: [] }
}

const RESEARCH = (c) => `You are auditing ONE competitor for a static, AdSense-monetized utility tool that will compete for the keyword cluster "${cluster}".

Competitor: ${c.name} — ${c.url}

Measure ALL of these pillar fields using live tools. Do NOT guess — if you cannot measure a field, set it to null and tag its evidence row "reasoned".
- SERP: capture the live Google SERP for the head term. Record serp_rank (this competitor's position, or null if not page 1), ai_overview_cited (is this domain cited in the AI Overview?), serp_features_owned (count of snippet/PAA/onebox it owns).
- Authority: dr (OpenPageRank), referring_domains (free Ahrefs checker).
- Traffic: feed into feature/trust judgement (note in evidence).
- On-page: word_count, heading_count (H1-H3), paa_coverage (fraction of the SERP People-Also-Ask this page answers, 0..1).
- Structured data: run \`python3 scripts/parse_jsonld.py --url ${c.url}\` and put its "types" into schema_types (REAL-MEASURED).
- Features: use the tool; feature_coverage = fraction of the canonical feature set it supports (0..1); note gated/paywalled features.
- Performance + a11y: run a Lighthouse audit (chrome-devtools lighthouse_audit) on mobile AND desktop; record lcp_ms, cls, inp_ms, a11y_score (0..100).
- UX: clicks_to_result (clicks from landing to a result), trust_signals (count present of: about, author, methodology, contact, brand).
- Take a desktop and a mobile screenshot; list their paths in "screenshots".

Return the RESEARCHER schema. Every non-null field needs an evidence row with method + url + evidence_tier.`

const SKEPTIC = (c, research) => `Adversarially RE-VERIFY this competitor audit. Default to skeptical. Re-check INDEPENDENTLY the 3 most decision-critical, most hallucination-prone claims: (1) traffic/authority (dr, referring_domains), (2) schema presence (schema_types), (3) live ranking + AI-Overview (serp_rank, ai_overview_cited). For each, set refuted=true if the researcher's value is not reproducible from a fresh check, give corrected_value, and set the evidence_tier you could actually achieve.

Competitor: ${c.name} — ${c.url}
Researcher fields: ${JSON.stringify(research && research.fields || {})}

Return the SKEPTIC schema.`

const audited = await pipeline(
  competitors,
  (c) => agent(RESEARCH(c), { label: `audit:${c.name}`, phase: 'Audit', schema: RESEARCHER_SCHEMA }),
  (research, c) => agent(SKEPTIC(c, research), { label: `verify:${c.name}`, phase: 'Verify', schema: SKEPTIC_SCHEMA })
    .then((verdict) => ({ ...research, skeptic: verdict })),
)

return { cluster, audited: audited.filter(Boolean) }
