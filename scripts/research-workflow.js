// pick-next-tool — runtime candidate-research workflow (Stages 3-4 evidence + a per-candidate skeptic).
// RUN THIS, do not read it to "study" it. The SKILL invokes it with the Workflow tool:
//   Workflow({ scriptPath: "<skillDir>/scripts/research-workflow.js", args: {
//     hub: "<hub name>",
//     dataMode: "manual" | "hybrid" | "auto",
//     skillDir: "<abs path to pick-next-tool>",
//     candidates: [ { tool, head_term, variants?, intent?, buyer_slice? }, ... ]   // the deduped shortlist
//   }})
//
// WHAT IT DOES: for each shortlisted candidate, a RESEARCHER agent runs Kill-Gates A-D on the live web
// and returns the MEASURED inputs score.py needs (NOT subjective 1-5 scores — that is the whole point;
// scoring stays deterministic and in the main loop). Then a separate SKEPTIC agent re-checks the two
// most-hallucinated claims (real volume + AI-Overview) plus the buyer-slice, and adjusts the inputs down.
//
// IT DOES NOT score or pick a winner, and it does NOT replace Stage 5: the MAIN LOOP runs
// `scripts/score.py` on the skeptic-corrected inputs, then independently re-verifies the top finalists'
// volume (browser Ahrefs / paid seat) before committing. Treat any volume gathered here as the tier the
// researcher labels it (measured in --data=auto; triangulated in --data=manual).

export const meta = {
  name: 'pick-next-tool-research',
  description: 'Run Kill-Gates A-D + an adversarial skeptic across a candidate shortlist, returning score.py-ready MEASURED inputs (no subjective scoring)',
  phases: [
    { title: 'Gate+Measure', detail: 'per candidate: live SERP / AI-Overview / demand gates + real measured inputs' },
    { title: 'Skeptic', detail: 'per candidate: independently re-check volume + AI-Overview + buyer-slice, adjust down' },
  ],
}

const A = args || {}
const HUB = A.hub || 'the chosen hub'
const DATA_MODE = A.dataMode || 'hybrid'
const SKILL_DIR = A.skillDir || ".claude/skills/pick-next-tool"  // pass args.skillDir (abs path); this relative default assumes cwd = project root
const CANDIDATES = Array.isArray(A.candidates) ? A.candidates : []
if (!CANDIDATES.length) {
  log('No candidates passed in args.candidates — pass { hub, dataMode, candidates:[{tool,head_term}] }.')
  return { error: 'no candidates supplied' }
}

// The score.py input contract — every researcher and skeptic returns exactly these fields.
const CONTRACT = {
  head_bucket: { type: 'string', enum: ['<100', '100-1K', '1K-10K', '10K-100K', '>=100K'] },
  cluster_kw_count: { type: 'integer' },
  cluster_monthly_volume: { type: 'integer' },
  incumbent_top3_visits: { type: 'integer' },
  distinct_variants: { type: 'integer' },
  kd_head: { type: 'integer' },
  weak_count: { type: 'integer' },
  native_feature: { type: 'boolean' },
  thin_site_proof: { type: 'boolean' },
  artifact_type: { type: 'string', enum: ['interactive_personalized', 'live_data_tool', 'info_tool', 'static_fact', 'single_fact'] },
  aio_fire_pct: { type: 'integer' },
  onebox: { type: 'boolean' },
  cpc: { type: 'number' },
  has_recurring_affiliate: { type: 'boolean' },
  buyer_slice: { type: 'string', enum: ['strong', 'weak', 'none'] },
  build_type: { type: 'string', enum: ['pure_client_single_form', 'client_side_complex', 'one_stable_api_or_yearly_data', 'paid_or_monthly_stale', 'backend_or_live_feed'] },
}
const CONTRACT_KEYS = Object.keys(CONTRACT)

const MEASURE_SCHEMA = {
  type: 'object',
  properties: Object.assign({}, CONTRACT, {
    tool: { type: 'string' },
    gateA: { type: 'string', enum: ['PASS', 'FAIL', 'RECAST'] },
    gateB: { type: 'string', enum: ['PASS', 'FAIL'] },
    gateC: { type: 'string', enum: ['PASS', 'FAIL'] },
    gateD: { type: 'string', enum: ['PASS', 'FAIL'] },
    survives_gates: { type: 'boolean' },
    who_ranks_p1: { type: 'array', items: { type: 'string' } },
    evidence: { type: 'array', items: { type: 'string' }, description: 'sources + dates; explicitly flag any field that is an estimate, not a measurement' },
  }),
  required: ['tool', 'gateA', 'gateB', 'gateC', 'gateD', 'survives_gates'].concat(CONTRACT_KEYS),
}

const SKEPTIC_SCHEMA = {
  type: 'object',
  properties: Object.assign({}, CONTRACT, {
    tool: { type: 'string' },
    corrections: { type: 'array', items: { type: 'string' }, description: 'claim -> what you actually found' },
    survived: { type: 'boolean', description: 'false if a load-bearing claim collapses (real broad-term vol < ~1k/mo, or a full-answer AIO fires)' },
    demand_confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    notes: { type: 'string' },
  }),
  required: ['tool', 'survived', 'corrections', 'demand_confidence'].concat(CONTRACT_KEYS),
}

const DATA = ({
  manual: `DATA MODE = manual (NO API keys): use the browser MCP (Claude-in-Chrome). Run the head term in incognito Google (append &gl=us&hl=en) to read who ranks page 1 and whether an AI Overview fires. Use the Ahrefs free Keyword Generator (ahrefs.com/keyword-generator/?country=us) for the volume band + KD + cluster size — RELOAD the page fresh before each new keyword (results cache after ~2 lookups). Label volume as 'triangulated'.`,
  hybrid: `DATA MODE = hybrid: automate discovery + volume with the skill scripts via Bash (${'`'}python3 ${SKILL_DIR}/scripts/autocomplete_fanout.py${'`'} for the cluster; ${'`'}volume_buckets.py${'`'} for Google Ads buckets if creds are set), but cross-check the page-1 SERP and the AI-Overview in the browser. Where a script lacks credentials, fall back to the free site for that input.`,
  auto: `DATA MODE = auto: drive the skill scripts via Bash — autocomplete_fanout.py (cluster), volume_buckets.py (Google Ads buckets), dr_wall.py (OpenPageRank page-1 DR wall + weak_count) — plus SerpApi for the SERP + ai_overview. If a script prints a missing-credential error, note it and fall back to a browser/free check for that input rather than failing the candidate. Label volume 'measured'.`,
})[DATA_MODE] || `DATA MODE = hybrid (default).`

function researchPrompt(c) {
  return [
    `You assess ONE candidate micro-tool for a BRAND-NEW, zero-authority website (DR < 20) targeting US/Western-Europe AdSense + affiliate revenue in 2026. Hub: ${HUB}.`,
    `CANDIDATE: ${JSON.stringify(c)}`,
    `Skill scripts: ${SKILL_DIR}/scripts  ·  Procedure: read ${SKILL_DIR}/references/process.md (Stage 3) + free-tools.md as needed.`,
    DATA,
    '',
    'Run the four KILL-GATES IN ORDER, note the first failure, and gather the REAL measured inputs score.py needs:',
    '- Gate A (hard kill): a browser/OS/Google onebox feature answers it inline? output is a single static number / verbatim-chatbot text? AdSense-restricted vertical? If it can be RECAST as a stateful/multi-step/file-export tool, mark RECAST and continue.',
    '- Gate B (winnability, decisive): WHO ranks page 1 of the head term? Any thin/low-DR/one-page site ranking the head OR long-tail (-> thin_site_proof=true)? Or a DR-80+ wall (-> native_feature stays false but weak_count low)? You buy the long-tail, never the bare head.',
    '- Gate C (AI-Overview): check the LIVE SERP. Does an AIO answer it inline (-> onebox/high aio_fire_pct)? Is the intent an interactive do-it-here artifact?',
    '- Gate D (real demand): measure the BROAD commercial term AND the persona-flavored term (the qualifier test — the flavor word can cut volume ~100x). Record head_bucket, cluster_kw_count, cluster_monthly_volume (summed across the cluster — Gate D is judged on this), distinct_variants, and top-3 incumbent monthly visits (Similarweb).',
    '',
    'Return the score.py contract fields with your best MEASURED values, each gate PASS/FAIL/RECAST, survives_gates, who_ranks_p1, and evidence (sources + dates). For any field you could only estimate, SAY SO in evidence — never pass a guess off as a measurement.',
  ].filter(Boolean).join('\n')
}

function skepticPrompt(measured, c) {
  return [
    `You are an adversarial SKEPTIC. Default to disbelief and try to BREAK the case for "${c.tool || measured.tool}", not confirm it.`,
    'RESEARCHER INPUTS (JSON):',
    JSON.stringify(measured, null, 2),
    DATA,
    '',
    'Independently re-check, with fresh data, the most decision-critical, most-hallucinated claims and adjust the contract fields DOWN where evidence is weaker:',
    '(1) REAL volume of the BROAD commercial term — re-pull it. The qualifier often guts volume 10-100x (e.g. "freelance rate calculator" <100/mo vs "invoice generator" >10k/mo). If the real broad cluster is < ~1,000/mo, survived=false.',
    '(2) AI-OVERVIEW on the head term — verify on the LIVE SERP yourself; never infer from intent. A full-answer AIO collapses AI-resistance.',
    '(3) BUYER SLICE for revenue — who actually purchases? If most users are non-buyers (e.g. employees totalling their own hours), set buyer_slice="weak"/"none" (display-first, affiliate is upside only).',
    'Also re-check for any false tiebreaker / stale premise (a domain "already owned", a prior commitment) — these have been wrong before; do not let one carry the decision.',
    'Return the CORRECTED contract fields, a corrections list, demand_confidence (keep <= medium unless you pulled real keyword-tool data), and survived.',
  ].join('\n')
}

phase('Gate+Measure')
log(`Gating + measuring ${CANDIDATES.length} candidates in "${HUB}" (data mode: ${DATA_MODE}).`)

const results = await pipeline(
  CANDIDATES,
  (c) => agent(researchPrompt(c), { label: `gate:${c.tool || c.head_term}`, phase: 'Gate+Measure', schema: MEASURE_SCHEMA }),
  (measured, c) => {
    if (!measured) return null
    return agent(skepticPrompt(measured, c), { label: `skeptic:${c.tool || c.head_term}`, phase: 'Skeptic', schema: SKEPTIC_SCHEMA })
      .then((skeptic) => ({
        tool: measured.tool,
        gates: { A: measured.gateA, B: measured.gateB, C: measured.gateC, D: measured.gateD, survives: measured.survives_gates },
        who_ranks_p1: measured.who_ranks_p1 || [],
        research_inputs: measured,
        skeptic_inputs: skeptic,        // <- feed THESE corrected fields to score.py
      }))
  }
)

return {
  hub: HUB,
  dataMode: DATA_MODE,
  results: results.filter(Boolean),
  next: 'Main loop: write each surviving candidate\'s skeptic_inputs to candidates.json and run `python3 scripts/score.py candidates.json` to rank + apply the veto. Then Stage 5 re-verifies the top finalists\' volume before committing.',
}
