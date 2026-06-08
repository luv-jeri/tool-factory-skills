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
// Fail-closed (ADR-0009): score.py reads each REQUIRED field by direct indexing — a missing key RAISES,
// it does not silently pass. Measure them all; never omit one to "let it default".
const CONTRACT = {
  // --- Gate A policy (REQUIRED, ADR-0009) ---
  adsense_restricted: { type: 'boolean', description: 'true if the vertical is AdSense-restricted (gambling/alcohol/adult/weapons/drugs/etc.) — a Gate-A hard DROP regardless of CPC' },
  // --- Demand ---
  head_bucket: { type: 'string', enum: ['<100', '100-1K', '1K-10K', '10K-100K', '>=100K'] },
  cluster_kw_count: { type: 'integer' },
  cluster_monthly_volume: { type: 'integer' },
  incumbent_top3_visits: { type: 'integer' },
  distinct_variants: { type: 'integer' },
  // --- Winnability ---
  kd_head: { type: 'integer' },
  weak_count: { type: 'integer' },
  native_feature: { type: 'boolean' },
  thin_site_proof: { type: 'boolean' },
  // thin_site_proof is HONORED only when EVIDENCED (ADR-0009): supply the ranking URL + that page's DR + the keyword.
  // A bare thin_site_proof=true with no evidence is ignored by score.py and flagged. Leave url='' / dr=null if no proof.
  thin_site_proof_url: { type: 'string', description: 'the thin/low-DR page that already ranks (evidence); REQUIRED for thin_site_proof to count' },
  thin_site_proof_dr: { type: ['integer', 'null'], description: "that ranking page's ACTUAL Domain Rating (evidence), range 0-100. Must be <= ~40 to count: a DR above that is a strong incumbent, NOT a thin site, and will NOT be honored as proof (it falls back to the KD ladder)." },
  thin_site_proof_keyword: { type: 'string', description: 'the exact keyword that page ranks for (evidence)' },
  dr_wall_evidenced: { type: 'boolean', description: 'true ONLY if you verified a DR-80+ wall from real SERP data — drives the Gate-B confident-kill citation (#11)' },
  // --- AI-Resistance ---
  artifact_type: { type: 'string', enum: ['interactive_personalized', 'live_data_tool', 'info_tool', 'static_fact', 'single_fact'] },
  aio_fire_pct: { type: 'integer', description: '% of live SERP checks showing an AI Overview, projected to RANK-TIME (ADR-0006), 0-100' },
  onebox: { type: 'boolean' },
  // --- Revenue ---
  cpc: { type: 'number' },
  has_recurring_affiliate: { type: 'boolean' },
  buyer_slice: { type: 'string', enum: ['strong', 'weak', 'none'] },
  // --- Build ---
  build_type: { type: 'string', enum: ['pure_client_single_form', 'client_side_complex', 'one_stable_api_or_yearly_data', 'paid_or_monthly_stale', 'backend_or_live_feed'] },
  // --- Evidence tiers (ADR-0009): per-dimension tier; commit (first_build_eligible) needs demand+winnability+ai_resistance at real-measured ---
  evidence: {
    type: 'object',
    description: "{dimension: 'real-measured'|'triangulated'|'reasoned'} per dimension. Label honestly — only data you actually pulled live is real-measured; default is reasoned.",
    properties: {
      demand: { type: 'string', enum: ['real-measured', 'triangulated', 'reasoned'] },
      winnability: { type: 'string', enum: ['real-measured', 'triangulated', 'reasoned'] },
      ai_resistance: { type: 'string', enum: ['real-measured', 'triangulated', 'reasoned'] },
      revenue: { type: 'string', enum: ['real-measured', 'triangulated', 'reasoned'] },
      build: { type: 'string', enum: ['real-measured', 'triangulated', 'reasoned'] },
    },
  },
}
const CONTRACT_KEYS = Object.keys(CONTRACT)

const MEASURE_SCHEMA = {
  type: 'object',
  properties: Object.assign({}, CONTRACT, {
    tool: { type: 'string' },
    gateA: { type: 'string', enum: ['PASS', 'FAIL', 'RECAST'], description: 'FAIL covers BOTH adsense_restricted and native_feature — note which in evidence_sources' },
    gateB: { type: 'string', enum: ['PASS', 'FAIL', 'REFUSE'], description: 'REFUSE = winnability==1 in the KD 21-25 noise band with no evidenced proof (ADR-0008)' },
    gateC: { type: 'string', enum: ['PASS', 'FAIL'] },
    gateD: { type: 'string', enum: ['PASS', 'FAIL'] },
    survives_gates: { type: 'boolean' },
    who_ranks_p1: { type: 'array', items: { type: 'string' } },
    // NOTE: per-dimension evidence TIERS live in the contract field `evidence` (an object).
    // This array is the human-readable source/date trail — kept under a distinct key to avoid collision.
    evidence_sources: { type: 'array', items: { type: 'string' }, description: 'sources + dates; explicitly flag any field that is an estimate, not a measurement' },
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
  hybrid: `DATA MODE = hybrid: automate discovery + volume with the skill scripts via Bash (${'`'}python3 ${SKILL_DIR}/scripts/autocomplete_fanout.py${'`'} for the cluster; ${'`'}volume_buckets.py${'`'} for Google Ads buckets if creds are set), but cross-check the page-1 SERP and the AI-Overview in the browser OR via ${'`'}python3 ${SKILL_DIR}/scripts/serp_aio.py "<head term>"${'`'} (SerpApi) when a SERPAPI_KEY is set. Where a script lacks credentials, fall back to the free site/browser for that input.`,
  auto: `DATA MODE = auto: drive the skill scripts via Bash — autocomplete_fanout.py (cluster), volume_buckets.py (Google Ads buckets), dr_wall.py (OpenPageRank page-1 DR wall + weak_count), and ${'`'}python3 ${SKILL_DIR}/scripts/serp_aio.py "<head term>"${'`'} (SerpApi live SERP: ai_overview presence -> aio_fire_pct, onebox/answer-box -> the Gate-C inline kill, and page-1 domains -> feed those into dr_wall.py). The free SerpApi plan is ~250 searches/mo, so check a handful of head terms, not every variant. If a script prints a missing-credential error, note it and fall back to a browser/free check for that input rather than failing the candidate. Label volume 'measured'.`,
})[DATA_MODE] || `DATA MODE = hybrid (default).`

function researchPrompt(c) {
  return [
    `You assess ONE candidate micro-tool for a BRAND-NEW, zero-authority website (DR < 20) targeting US/Western-Europe AdSense + affiliate revenue in 2026. Hub: ${HUB}.`,
    `CANDIDATE: ${JSON.stringify(c)}`,
    `Skill scripts: ${SKILL_DIR}/scripts  ·  Procedure: read ${SKILL_DIR}/references/process.md (Stage 3) + free-tools.md as needed.`,
    DATA,
    '',
    'Run the four KILL-GATES IN ORDER, note the first firing cause, and gather the REAL measured inputs score.py needs:',
    '- Gate A (hard kill): FIRST, is this an AdSense-restricted vertical (gambling/alcohol/adult/weapons/drugs/etc.)? -> set adsense_restricted=true (a hard DROP regardless of CPC). Then: a browser/OS/Google onebox feature answers it inline? output is a single static number / verbatim-chatbot text? (-> native_feature). If it can be RECAST as a stateful/multi-step/file-export tool, mark RECAST and continue.',
    '- Gate B (winnability, decisive): WHO ranks page 1 of the head term? Any thin/low-DR/one-page site ranking the head OR long-tail? If so set thin_site_proof=true AND supply the EVIDENCE — thin_site_proof_url, thin_site_proof_dr, thin_site_proof_keyword — because score.py IGNORES a bare thin_site_proof with no evidence. If instead a verified DR-80+ wall dominates page 1, set dr_wall_evidenced=true (drives the confident-kill citation). You buy the long-tail, never the bare head.',
    '- Gate C (AI-Overview): check the LIVE SERP. Does an AIO answer it inline (-> onebox / high aio_fire_pct)? Project aio_fire_pct to RANK-TIME (6-12mo out), not today (ADR-0006). Is the intent an interactive do-it-here artifact?',
    '- Gate D (real demand): measure the BROAD commercial term AND the persona-flavored term (the qualifier test — the flavor word can cut volume ~100x). Record head_bucket, cluster_kw_count, cluster_monthly_volume (summed across the cluster — Gate D is judged on THIS measured volume only), distinct_variants, and top-3 incumbent monthly visits (Similarweb).',
    '',
    'Also set per-dimension evidence TIERS in the `evidence` object (demand/winnability/ai_resistance/revenue/build -> real-measured | triangulated | reasoned). Be honest: only data you pulled LIVE is real-measured; default to reasoned. Commit-eligibility requires demand+winnability+ai_resistance at real-measured.',
    'Return the score.py contract fields with your best MEASURED values, each gate PASS/FAIL/REFUSE/RECAST, survives_gates, who_ranks_p1, and evidence_sources (sources + dates). For any field you could only estimate, SAY SO in evidence_sources and tier it triangulated/reasoned — never pass a guess off as a measurement.',
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
    '(2) AI-OVERVIEW on the head term — verify on the LIVE SERP yourself; never infer from intent. A full-answer AIO collapses AI-resistance. Project aio_fire_pct to rank-time, not today.',
    '(3) BUYER SLICE for revenue — who actually purchases? If most users are non-buyers (e.g. employees totalling their own hours), set buyer_slice="weak"/"none" (display-first, affiliate is upside only). NB: the affiliate +1 only applies at buyer_slice="strong".',
    '(4) RESTRICTED VERTICAL — confirm adsense_restricted: a high CPC in gambling/CBD/adult/etc. is a $0 monetizable Gate-A DROP, not Revenue=5. Set adsense_restricted=true if so.',
    '(5) THIN-SITE PROOF — if thin_site_proof=true, verify the EVIDENCE is real (thin_site_proof_url + _dr + _keyword); a thin site allegedly beating a DR-90+ head is suspect. Strip thin_site_proof to false (and clear the evidence) if you cannot confirm the ranking page. Conversely confirm dr_wall_evidenced only on a real DR-80+ wall.',
    'Also re-check for any false tiebreaker / stale premise (a domain "already owned", a prior commitment) — these have been wrong before; do not let one carry the decision.',
    'Return the CORRECTED contract fields (including adsense_restricted, the thin_site_proof_* evidence, dr_wall_evidenced, and the per-dimension `evidence` tiers — downgrade any tier you could not independently confirm to real-measured), a corrections list, demand_confidence (keep <= medium unless you pulled real keyword-tool data), and survived.',
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
