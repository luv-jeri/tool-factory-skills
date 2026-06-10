# pick-next-tool

A [Claude Code](https://docs.claude.com/en/docs/claude-code) **skill** that decides which micro-tool (and which content hub it lives in) to build next for an SEO / AdSense tool portfolio — using one reproducible, data-backed funnel, so the **same inputs always produce the same winner**.

> **Why this exists.** Three different agents were once asked to pick the first tool to build for the same portfolio. They returned three different tools. The cause was never the data — it was that each used a *different shortlist*, a *different volume source*, and *subjective 1–5 "vibe" scores* that drifted from run to run. This skill removes that variance: fixed candidate sourcing → ordered kill-gates → **deterministic** scoring on real data → an adversarial kill pass.

## Core principle

> **For a brand-new, zero-authority domain, _winnability_ — not demand — is the binding constraint.**

A keyword with 1,000,000 searches is worth zero to you if DR-90 incumbents own page 1. The whole method finds tools where a thin new site can actually rank, and that AI Overviews can't answer inline, *then* ranks the survivors on money and durability.

## The funnel

```
0  Reconcile prior research → one canonical baseline
1  Hub-selection gate (one persona, ≥4–6 tools, low YMYL, shared link spine)
2  Source 10–12 deduped in-hub candidates
3  Kill-gates A→B→C→D, in order, cheapest first — STOP at first failure
       A  native-feature / restricted-vertical hard kill
       B  winnability (DR-80 wall vs. thin-site long-tail proof)
       C  AI-Overview / onebox eats the click
       D  real demand below the cluster floor
4  Deterministic weighted score (evidence-tier every input)
5  Real keyword-volume verification  ← BLOCKING gate
6  Adversarial "kill the winner" (a separate skeptic re-checks load-bearing claims)
7  Confidence + named same-hub fallback + monitor-list
8  Deliverables + decision log
```

### The four IRON LAWS

1. **No tool is chosen on estimated volume.** Real keyword data (Stage 5) is a blocking gate. Triangulated / SERP-density numbers *rank* candidates; they never *select* the winner.
2. **No scoring before all four kill-gates pass.** Run A→B→C→D in order. Stop at the first failure and emit **no** Opportunity number for a dropped candidate. A gate failure is never rescued by strong scores elsewhere.
3. **No winner without a survived adversarial kill pass.** A separate skeptic re-checks the load-bearing claims (real volume, AI-Overview presence, revenue-to-buyer-slice). Any outright failure promotes the same-hub runner-up.
4. **The first build has no dimension scored 1.** Any single `1` is an automatic veto. Pick the all-rounder with no fatal weakness, never the highest-on-one-axis trap.

## The deterministic scoring engine

The numbers are **not** hand-assigned. [`scripts/score.py`](scripts/score.py) is the single source of truth:

```
Opportunity = (0.20·Demand + 0.25·Winnability + 0.25·AI-Resistance + 0.20·Revenue + 0.10·Build) × 20   → 0–100
```

Winnability + AI-Resistance (0.25 each) deliberately outrank Demand (0.20). Each dimension is computed mechanically from *measured inputs* (head-volume bucket, KD + weak-SERP count, live AI-Overview fire-rate, CPC + buyer slice, build effort) — so any agent, on any run, gets the same verdict. The engine also evaluates the kill-gates and returns `DROP` + the single gate that fired (no launderable number) for any failure.

The engine **fails closed** and is built for a fatal-downside decision: the cardinal error is the *false positive* — greenlighting a dud that burns runway ([ADR-0001](docs/adr/0001-ruin-avoidance-over-opportunity-maximization.md)). So it returns four statuses — **OK > VETO > REFUSE > DROP** — where **REFUSE** ("the evidence is ambiguous/contradictory — go verify, don't pick") is a first-class outcome, not an error. Required inputs are read by direct indexing (a missing key *raises*, never silently passes); AdSense-restricted verticals are dropped at Gate A; `thin_site_proof` is honored only when it carries evidence (ranking URL + DR + keyword); and `first_build_eligible` requires the high-weight dimensions to be tagged `real-measured` ([ADR-0009](docs/adr/0009-input-integrity-the-engine-refuses-to-trust-what-it-cannot-verify.md)).

The built-in `--selftest` is a **mutable snapshot** (the `Timesheet = 89` number, which *fails loud* on recalibration so a human re-blesses it) **plus immutable invariants** — structural (QR drops at Gate A, gate-dropped tools carry no number, ranking is deterministic) and **golden-bad** ruin-avoidance cases (a restricted vertical, a gamed thin-proof wall, an AI-answerable lookup, and a contradictory input are all refused). A PASS means the engine is wired correctly **and refuses duds** — *not* that Timesheet is the universally "correct" pick ([ADR-0003](docs/adr/0003-golden-test-snapshot-plus-invariants.md)).

```bash
python3 scripts/score.py --selftest
# Score one or more candidates:
python3 scripts/score.py candidates.json
```

```
=== pick-next-tool selftest (snapshot + invariants + golden-bad) ===
   89.0  Timesheet / Time-Card Calculator   {demand:5, winnability:4, ai_resistance:5, revenue:4, build:4}  [committable]
   85.0  Email Signature Generator          {demand:4, winnability:4, ai_resistance:5, revenue:4, build:4}  [committable]
    —    Freelance Rate Calculator          DROP(Gate D — cluster below the ~1000/mo demand floor)
    —    QR Code Generator                  DROP(Gate A — a browser/OS/Google native feature answers it inline)
    —    TikTok Shop Fee Calculator         DROP(Gate D — cluster below the ~1000/mo demand floor)
PASS
```

Note how QR has the highest demand and TikTok the easiest SERP — yet each fails a gate and is dropped *before* scoring. The all-rounder with no fatal weakness wins. Every threshold is `v0` uncalibrated judgment in a tunable config block, revisited against an outcome ledger as real builds ship ([ADR-0002](docs/adr/0002-thresholds-are-uncalibrated-v0-config.md)). The full design rationale lives in [`docs/adr/`](docs/adr/).

## Install

This is a Claude Code skill. Drop it into your skills directory:

```bash
# project-level
git clone https://github.com/luv-jeri/pick-next-tool .claude/skills/pick-next-tool
# or user-level
git clone https://github.com/luv-jeri/pick-next-tool ~/.claude/skills/pick-next-tool
```

Then invoke it by intent — *"pick the next tool to build"*, *"what should we build next"*, *"validate this tool idea"* — or by name. Claude reads [`SKILL.md`](SKILL.md) and works the funnel stage by stage.

## Run modes & data modes

| Flag | Effect |
|---|---|
| `--checkpoints` *(default)* | Human-in-the-loop: pauses at the shortlist, the finalists, and the winner. |
| `--auto` | Runs end-to-end; stops only when the data is genuinely ambiguous. |
| `--data=manual` | Zero setup. Browser + free sites only (incognito Google for SERP/AIO; Ahrefs free Keyword Generator for volume bands). |
| `--data=hybrid` *(default)* | Automate discovery + volume via scripts where credentials exist; cross-check SERP/AIO in the browser. |
| `--data=auto` | Fully scripted via free APIs (one-time keys — see [`SETUP.md`](SETUP.md)); browser fallback if a credential is missing. |

The mode changes only *where it pauses* and *how inputs are measured* — never the gates or the scoring.

## What's in here

```
SKILL.md                      entry point — laws, funnel, checklist, rationalization table
SETUP.md                      one-time free-API keys (only for --data=auto)
references/
  process.md                  the full 9-stage procedure (actions, pass/fail, outputs)
  scoring-model.md            the deterministic dimension rules (mirrors score.py)
  free-tools.md               the verified free + open-source keyword/SERP toolchain
  live-recheck.md             stale quotas/thresholds to re-verify at runtime
  deliverables.md             copy-paste templates for the 6 output artifacts
scripts/
  score.py                    deterministic scoring + gate engine (source of truth; --selftest)
  research-workflow.js        per-candidate researcher + adversarial skeptic (Workflow tool)
  autocomplete_fanout.py      cluster discovery from autocomplete + PAA
  volume_buckets.py           Google Ads / Keyword Planner volume bands
  dr_wall.py                  SERP DR-wall + weak-result analysis
  serp_aio.py                 SerpApi live SERP — AI-Overview / onebox / page-1 domains (--data=auto)
docs/adr/                     architecture decision records — the why behind every rule
evals/evals.json              RED-GREEN evals targeting the three real divergence failure modes
```

## Credits

- Skill structure and discipline patterns inspired by [obra/superpowers](https://github.com/obra/superpowers).
- The funnel synthesizes the strongest move from three independent agent runs on the same portfolio: live-SERP re-checking and the AI-Overview tiebreaker; lock-the-criteria-before-the-answers and the false-tiebreaker catch; and winnability-is-the-binding-constraint with the qualifier-kills-volume and thin-site-long-tail-proof rules. Each contributed something; the variance between them is exactly what the determinism removes.

## License

[MIT](LICENSE) © 2026 Sanjay Kumar
