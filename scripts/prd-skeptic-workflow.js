export const meta = {
  name: 'prd-skeptic',
  description: 'Adversarially challenge every PRD requirement, acceptance criterion, and non-goal',
  phases: [{ title: 'Challenge', detail: 'one skeptic per requirement' }],
}

const VERDICT_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['item_id', 'traceable', 'measurable', 'scope_correct',
             'contradiction_found', 'missing_edge_case', 'verdict', 'reason'],
  properties: {
    item_id: { type: 'string' },
    traceable: { type: 'boolean' },
    measurable: { type: 'boolean' },
    scope_correct: { type: 'boolean' },
    contradiction_found: { type: 'boolean' },
    missing_edge_case: { type: 'string' },
    verdict: { type: 'string', enum: ['keep', 'demote', 'flag'] },
    reason: { type: 'string' },
  },
}

const _args = typeof args === 'string' ? JSON.parse(args) : args
const spec = _args && _args.build_spec
if (!spec || !Array.isArray(spec.requirements)) {
  throw new Error('prd-skeptic: args.build_spec with requirements[] is required')
}

phase('Challenge')
const verdicts = await parallel(spec.requirements.map(r => () =>
  agent(
    `You are an adversarial PRD reviewer. Default to skeptical.\n` +
    `Challenge this requirement from the PRD for "${spec.tool}":\n` +
    JSON.stringify(r, null, 2) + `\n\n` +
    `Scope (do/wont_do/skipped): ${JSON.stringify(spec.scope)}\n\n` +
    `Decide: TRACEABLE (real source_ref or an owned assumption)? ` +
    `Every acceptance criterion MEASURABLE (number+unit or boolean predicate)? ` +
    `Scope placement correct? Any CONTRADICTION with scope or another requirement? ` +
    `Any MISSING EDGE CASE (empty string if none)? ` +
    `verdict=keep ONLY if it survives every check; otherwise demote or flag.`,
    { label: `skeptic:${r.id}`, phase: 'Challenge', schema: VERDICT_SCHEMA }
  )
))

const clean = verdicts.filter(Boolean)
// A verdict BLOCKS FINAL only on an OBJECTIVE defect: a hard gate fails
// (traceability, measurability, scope) or the deliverable contradicts itself.
// A demote/flag raised solely for a missing edge case — hard gates green, no
// contradiction — is ADVISORY: fold it into the PRD as a refinement. Blocking on
// every conceivable edge case never converges (the skeptic always finds one more);
// blocking on objective defects does. The verdict label alone does not block.
const isBlocking = v =>
  !v.traceable || !v.measurable || !v.scope_correct || v.contradiction_found
const blocking = clean.filter(isBlocking)
const advisory = clean.filter(v => v.verdict !== 'keep' && !isBlocking(v))
return {
  total: spec.requirements.length,
  kept: clean.filter(v => v.verdict === 'keep').length,
  blocking,
  advisory,
  pass: blocking.length === 0,
}
