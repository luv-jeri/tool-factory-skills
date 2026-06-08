# The 9-stage process (full detail)

Read the stage you are on. Each stage has a PASS rule — do not advance until it passes. Checkpoints (in `--checkpoints` mode) are marked ⏸.

## Stage 0 — Reconcile prior research → canonical baseline
**Purpose:** start from existing research, not a blank page; resolve contradictions so the funnel rests on one agreed baseline.
**Actions:** Read all strategy/plan/ranking files with 2 parallel read-only agents (hubs, scoring model, prior recommendations, contradictions). List every contradiction (e.g. finance-first vs dev-first) and resolve via the **canonical-source rule**: README/ADR declares which plan is canonical; stale drafts are superseded IN WRITING. Flag any load-bearing premise that is uncertain or unverifiable from files alone (e.g. "do we already own domain X?") and **ASK THE USER** before relying on it. Mark every prior score ESTIMATED-until-verified; treat the inherited ranking as a hypothesis, never the verdict.
**Data:** README.md, EXEC-SUMMARY.md, 03-BULLETPROOF-PLAN.md, Money-First plan, 04-IDEA-RESCORE.md, 07-FIRST-TOOL-DECISION.md, 08-TOOL-SELECTION-RUBRIC.md, master ranking spreadsheets, + direct user confirmation on uncertain premises.
**PASS:** exactly one canonical hub/plan baseline; all contradictions resolved or escalated; no decision rests on an unverified premise.
**Out:** canonical baseline note (chosen plan, resolved contradictions + superseded drafts, premises confirmed with the user, candidate hubs to evaluate).

## Stage 1 — Hub-selection gate
**Purpose:** pick the hub/persona BEFORE sourcing tools, so every candidate shares one audience and an internal-link spine that compounds authority.
**Actions:** For each candidate hub, check the four hub criteria. Prefer the LOWEST-barrier hub for a zero-authority brand (low YMYL/E-E-A-T, embed-friendly, B2B-leaning CPC); defer high-RPM YMYL hubs (finance) to a month-12–18 graduation. Confirm the hub can host ≥4–6 tools that each plausibly clear the kill-gates and share a link spine.
**PASS (all four):** (a) one coherent persona; (b) ≥4–6 tools each plausibly clearing Gates A–D; (c) low YMYL/E-E-A-T pressure for an anonymous new brand; (d) tools share an internal-link spine. Open with the most winnable passing hub.
**Out:** chosen opening hub + ranked hub backlog + the link-spine sketch.

## Stage 2 — Standardized candidate sourcing ⏸
**Purpose:** generate ONE bounded, deduped shortlist inside the hub — the fix for the root cause of divergent winners (each agent inherited a different candidate universe).
**Actions:** Pull all tools mapped to the chosen hub from the master ranking; dedupe overlapping ideas to one canonical tool each. Top up to a fixed shortlist size (10–12) with SERP-validated net-new ideas in the same persona. For each candidate record: head term, obvious long-tail variants, intent type (interactive/transactional vs informational), rough buyer slice.
**PASS:** shortlist is a fixed size (target 10–12), fully deduped, every entry in-hub, each carries head term + variants + intent.
**Out:** deduped 10–12 candidate shortlist with per-candidate metadata. **⏸ `--checkpoints`: confirm the shortlist with the user.**

## Stage 3 — Kill-gates A→B→C→D (in order, cheapest first, stop at first failure)
**Purpose:** eliminate un-buildable/un-rankable/un-monetizable candidates before scoring.
- **Gate A — Hard kill:** reject if Google answers it natively in-SERP, a browser/OS ships the feature, the output is a single static number / verbatim-chatbot text, or it is an AdSense-restricted vertical (gambling/alcohol/drugs/weapons/adult). *Escape hatch:* if it can be recast as a multi-step/stateful/file-export tool **that still carries the search demand which justified the candidate**, resurrect it — a recast that keeps the name but loses the searches does not qualify.
- **Gate B — Winnability (decisive):** pull the live SERP for the head term. FAIL on a DR-80+ wall (Canva/Adobe/Bitly/calculator.net/NerdWallet) or a native platform feature. PASS only if ≥1 thin/low-DR/one-page site already ranks the head OR the long-tail (live newcomer proof). You buy the long-tail, never the bare head. Competitors that are app-store apps (not websites) do NOT contest the open-web SERP — count them as absent (an app-only "competitive" niche is a weak/empty web SERP = a PASS signal).
- **Gate C — AI-Overview:** FAIL on informational/single-fact intent answered inline by an AI Overview/featured snippet. PASS on transactional "do-it-here" interactive-artifact intent.
- **Gate D — Real-demand (measured):** pull ACTUAL keyword volume (Stage 5 method). FAIL if head + variants cluster < ~1,000/mo. PASS at ≥ ~5,000/mo with ≥ ~100 long-tail keywords. Run the qualifier-kills-volume test: measure the BROAD commercial term, not just the persona-flavored one (the flavor word can cut volume ~100×). A Gate-D failure is a HARD drop — never rescued by strong Revenue/AI/Build (a tool you cannot drive traffic to monetizes nothing).
**PASS:** a candidate must pass A, B, C, D to be scored. Any single fail = drop (Gate A only: try the recast escape hatch). Once a gate fails, STOP — do not compute downstream gates or emit any Opportunity score for the dropped candidate. Gates B and D are the most common kills and must cite live evidence.
**Out:** per-candidate gate sheet (A/B/C/D PASS/FAIL + evidence + who-ranks-page-1) and the surviving contender set.

> **How to run Stage 3 + Stage 4 cheaply:** fan them out with `scripts/research-workflow.js` via the Workflow tool — one researcher + one skeptic per candidate. Run that workflow; do not hand-research 12 tools serially.

## Stage 4 — Weighted scoring on the standard model (verified inputs only) ⏸
**Purpose:** rank survivors objectively on the balanced model, using verified — not guessed — inputs.
**Actions:** Lock the model + weights BEFORE scoring (do not re-tune to fit a favorite): `Opportunity = (0.20·D + 0.25·W + 0.25·AI + 0.20·Rev + 0.10·Build) × 20`. Score each dimension 1–5 using the deterministic anchors in `scoring-model.md`; TAG each score's evidence tier (real-measured / triangulated / reasoned). Compute Opportunity 0–100 in a live-formula spreadsheet. Apply the veto: any single 1 disqualifies a first build.
**PASS:** ranked by Opportunity, BUT the first build must score 4–5 on EVERY dimension (no fatal weakness). Pick the all-rounder, not the highest-on-one-axis trap.
**Out:** sortable scorecard (0–100 + per-dimension 1–5 + evidence tier), provisional winner + ranked runner-ups. **⏸ `--checkpoints`: confirm the finalists before the real-data pull.**

## Stage 5 — Real-demand verification (empirical, BLOCKING gate)
**Purpose:** replace every estimated/triangulated volume on the finalists with real clickstream data — the decisive gate that has historically flipped picks.
**Actions:** Use the fixed free toolchain (`free-tools.md`): Ahrefs free Keyword Generator at `ahrefs.com/keyword-generator/?country=us` (or a paid Ahrefs/Semrush seat if available), driven in-browser. For each finalist pull banded Volume, KD (Easy/Med/Hard), and total cluster size ("X of N keywords"). **Throttle workaround:** the results component caches after ~2 lookups — RELOAD the page fresh before each new keyword (re-submitting in place returns stale rows). Re-run the qualifier test on real data (broad vs persona term); read KD as a hub-wide reality check (money heads usually "Hard" → head ≈ year-2, long-tail ≈ months 3–12).
**PASS:** a finalist survives only if real cluster volume ≥ ~5,000/mo on the broad commercial term with ≥ ~100 long-tail keywords. If real data contradicts the scored Demand, re-score and re-rank (this is where freelance-rate <100/mo dies and invoice/timecard >10k/mo wins).
**Out:** real keyword-volume table per finalist (band, KD, cluster size, source/date); the re-confirmed or re-ordered winner.

## Stage 6 — Adversarial "kill the winner" ⏸
**Purpose:** red-team the chosen tool's load-bearing claims to break it or harden it before committing build effort.
**Actions:** Run a SEPARATE skeptic (a distinct agent) that independently re-checks the 2–3 most decision-critical, most-hallucination-prone claims: (1) real demand/volume, (2) AI-Overview presence on the head term, (3) the revenue-to-buyer-slice assumption. Do NOT abbreviate this into a self-review — the winner earns a full separate-skeptic pass even when it "looks obviously fine." For Revenue, force "who in this audience actually purchases?" and DISCOUNT affiliate to that slice. Adjust scores DOWN where evidence is weaker; record every honest correction. Re-check for a false tiebreaker / stale premise (how the bogus "you own contractrates.fyi" tiebreaker was caught) — cross-check load-bearing premises against the canonical plan and the user; supersede the bad draft in writing.
**PASS:** the winner STANDS only if all load-bearing claims survive (after at most documented corrections). Any claim that fails outright promotes the top same-hub runner-up and re-runs Stages 5–6 on it.
**Out:** red-team verdict (each claim survived / corrected / failed) + the honest corrections folded into final scores and monetization stance (e.g. display-first). **⏸ `--checkpoints`: confirm the winner before deliverables.**

## Stage 7 — Confidence, fallback & monitoring
**Purpose:** make the recommendation honest and robust.
**Actions:** Tag each load-bearing claim with a confidence tier (real-measured=high; triangulated=medium; reasoned=low) + dates/sources. Name an explicit SAME-HUB fallback (top runner-up) + the SWITCH TRIGGER that would promote it (real volume < ~5k/mo cluster; the red-team breaks a claim; a DR-80 entrant captures the long-tail). Add a monitor-list with cadence (AI-resistance "true today, monitor"; demand re-verify in a paid seat; ad-network thresholds). List the gating FIRST build action that closes any remaining low-confidence gap.
**PASS:** the winner has a stated confidence per load-bearing claim, a named same-hub fallback with a switch trigger, and a monitor-list. No bare single-bet recommendations.

## Stage 8 — Deliverables
**Purpose:** emit reusable, auditable artifacts so the decision is reproducible and the build can start. See `deliverables.md` for templates.
**Actions:** Write the decision brief (hub + tool + why, with the divergence-from-internal-ranking explained and the honest corrections). Ship the live-formula scored spreadsheet. Attach the real keyword-volume table and the red-team verdict. Write the starter build brief (differentiators that ARE the AI-resistance moat, one-variant-per-URL long-tail page roadmap, monetization slots, correctness/unit-test list). Log the decision + scoring model to project memory; supersede any stale draft in writing.
**PASS:** all five+ artifacts exist (brief, scorecard, real-volume table, red-team verdict, build brief) AND the decision is logged to memory with superseded drafts noted.

---

## The four hub-gate criteria (Stage 1)
A hub PASSES only if ALL hold: (a) one coherent persona; (b) ≥4–6 tools each plausibly clearing Gates A–D; (c) low YMYL/E-E-A-T pressure for an anonymous new brand; (d) tools share an internal-link spine. Open with the most winnable passing hub; graduate to higher-RPM YMYL hubs (finance) at month 12–18.

## Contradiction-reconciliation rule (Stage 0)
When sources conflict: (1) the README/ADR names which plan is canonical — it wins; (2) a load-bearing premise that can't be settled from files (domain ownership, budget, prior commitments) is escalated to the user, never assumed; (3) the stale/losing draft is superseded IN WRITING (don't leave two conflicting files). This is exactly how the false "you own contractrates.fyi" tiebreaker and the finance-first-vs-dev-first conflict were caught.
