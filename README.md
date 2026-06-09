# projects-competitive-analysis

A [Claude Code](https://docs.claude.com/en/docs/claude-code) **skill** that turns a product gist or PRD stub into a **measured, source-ledgered competitive brief** — so every gap, strength claim, and exploit recommendation rests on a number pulled from a live source, not an assertion. It is the twin of [`pick-next-tool`](https://github.com/luv-jeri/pick-next-tool), one stage downstream: where that skill picks *which* tool to build, this one tells you *what to build and why you'll win.*

> **Why this exists.** A competitor brief was once produced as a rich, readable, 9-competitor teardown — and it was wrong in the ways that matter. It listed what competitors *had* (features, monetization) but had **zero measured data**: no live SERP rankings, no verified traffic or backlinks, schema marked "UNVERIFIED" on 7 of 9 sites, no Core Web Vitals, no accessibility audit, and the #1 stated risk (AI Overview) was never actually observed on the live result page. It was a *qualitative feature inventory dressed as competitive intelligence.* This skill removes that failure mode: live SERP/AIO capture → per-competitor empirical audit → **deterministic** scoring on measured inputs → an adversarial kill pass → a brief where every claim carries a source.

## Core principle

> **Commit an exploit only on real-measured or triangulated evidence. A `reasoned`-tier guess is a hypothesis, never a recommendation.**

A brief that *reads* well but directs you to build the wrong thing is the exact failure this fixes. "Competitor X is slow" without a measured LCP, or "we'll win on schema" when schema was never parsed, is not allowed — it is cut or demoted to an open question.

## The funnel

```
0  Intake — gist/PRD + target keyword cluster + build folder; reuse pick-next-tool research
1  Discover — live SERP scrape + schema parse → identify the real page-1 competitors
2  Triage — drop irrelevants; rank survivors; select the set to audit
3  Audit fan-out — researcher + adversarial skeptic per competitor (10 pillars, MEASURED)
4  Score — competitor_strength.py per competitor on measured inputs (deterministic)
5  Gap synthesis — gap_opportunity.py on the scored matrix → ranked, gated gaps
6  Adversarial kill — a separate skeptic confirms competitors MEASURABLY fail each gap
7  Write — COMPETITIVE-BRIEF.md + research-raw.json source ledger
8  Handoff — a machine-readable PRD-SEED block the PRD-generation skill consumes
```

### The six IRON LAWS

1. **No committed exploit on `UNVERIFIED` evidence** — reasoned-tier claims are hypotheses, never recommendations.
2. **No performance or a11y claim without a measured number** — "fast"/"accessible" is illegal without a score + URL + date.
3. **Every claim carries a source** — url + date + method + evidence_tier in the ledger, or it is cut.
4. **No gap is an "opportunity" until the adversarial pass confirms competitors *measurably* fail it.**
5. **Scores come from the scripts** — quoting a number you didn't run through the engine is a skill failure.
6. **The engine fails closed** — missing field → raise, mark UNVERIFIED, REFUSE to commit; "insufficient data" is a legal output.

## The deterministic engines

The numbers are **not** hand-assigned. Two scripts are the single source of truth (`references/scoring-model.md` mirrors them; if a table and a script disagree, the script wins).

**[`scripts/competitor_strength.py`](scripts/competitor_strength.py)** — how formidable each competitor is, 0–100:
```
strength = (0.30·Authority + 0.25·SERP + 0.15·Content + 0.12·Feature + 0.13·UX/Perf/A11y + 0.05·Trust) × 20
```

**[`scripts/gap_opportunity.py`](scripts/gap_opportunity.py)** — is a gap worth building, 0–100 + tier (`build-now`/`v2`/`skip`/`hypothesis`):
```
opportunity = (0.35·Demand + 0.30·IncumbentWeakness + 0.20·AIResistance + 0.15·Defensibility) × 20
              × buildability_factor × weakness_gate
```
`weakness_gate` zeros any gap a majority of incumbents already solve (`incumbent_weakness ≤ 2`); `reasoned`-evidence gaps are demoted to `hypothesis` and never become committable. Both engines **fail closed** (missing/ill-typed/out-of-range input raises), accept `null` for genuinely unmeasured SERP/a11y fields (flagged in `unverified_dimensions`, never fabricated), and ship a `--selftest` of a mutable snapshot + structural invariants + golden-bad fixtures.

```bash
python3 scripts/competitor_strength.py --selftest
python3 scripts/gap_opportunity.py --selftest
python3 scripts/parse_jsonld.py --selftest      # verified-schema extractor
```

## Install

```bash
# project-level (this project only)
git clone https://github.com/luv-jeri/projects-competitive-analysis .claude/skills/projects-competitive-analysis

# or user-level (all projects)
git clone https://github.com/luv-jeri/projects-competitive-analysis ~/.claude/skills/projects-competitive-analysis
```

Then invoke it in Claude Code with `/projects-competitive-analysis` (give it a product gist or PRD).

## Run modes & data modes

**Free-first by default.** Core Web Vitals + accessibility + schema + on-page content need **no keys** (Lighthouse-style performance traces and the a11y tree via the chrome-devtools MCP; `parse_jsonld.py` via stdlib). **SERP rank, AI-Overview, and Domain Rating require keys** — the automation browser is CAPTCHA-blocked for live SERP and backlink tools, so set `SERPAPI_KEY` (SERP/AIO) and `OPENPAGERANK_API_KEY` (DR) per [`SETUP.md`](SETUP.md). Referring-domains needs Ahrefs/Similarweb (paid/manual); without it the authority dimension is a lower bound. If a tool's audits share one chrome-devtools browser, run them **sequentially** (parallel performance traces corrupt CWV). Reuses a sibling `pick-next-tool` `research-raw.json` when present.

## What's in here

```
SKILL.md                  entry point: IRON LAWS, 10-pillar overview, funnel, checklist, rationalization table
SETUP.md                  free-first API setup (SerpApi, OpenPageRank prerequisites)
references/
  pillars.md              the 10 measurement pillars: fields + how to measure each
  scoring-model.md        deterministic rules mirroring both engines; gates; evidence tiers
  audit-procedure.md      per-stage procedure + the per-competitor browser-driven recipe
  data-sources.md         free-first toolchain + missing-data handling + live-recheck
  deliverables.md         COMPETITIVE-BRIEF + ledger templates + the PRD-SEED contract
scripts/
  competitor_strength.py  deterministic strength engine (--selftest)
  gap_opportunity.py      deterministic gap-ranking engine (--selftest)
  parse_jsonld.py         fetch + validate JSON-LD (real-measured schema)
  audit-workflow.js       parameterized Workflow: researcher + adversarial skeptic per competitor
docs/adr/                 the "why" behind evidence-gating, weights, fail-closed, browser audits, the PRD-SEED contract
evals/evals.json          RED-GREEN evals targeting the failure modes above
```

## Credits

Built as the downstream twin of [`pick-next-tool`](https://github.com/luv-jeri/pick-next-tool), following the [superpowers](https://github.com/obra/superpowers) skill-authoring discipline (brainstorm → spec → plan → TDD build → adversarial review). Designed for a static, AdSense-monetized micro-tool portfolio, but the methodology is general.

## License

MIT — see [LICENSE](LICENSE).
