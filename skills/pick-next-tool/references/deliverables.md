# Deliverable templates (Stage 8)

Emit ALL SIX of these at Stage 8. Together they make the decision reproducible and let the build start the same day. File the markdown + xlsx artifacts in `micro-tool-factory/strategy/` with the **next sequence number** (e.g. `09-NEXT-TOOL-DECISION.md`, `09-NEXT-TOOL-SCORECARD.xlsx`, `09-<tool>-BUILD-BRIEF.md`). Then run the **memory log** step (artifact 6's tail) so the next run of this skill does not re-pick what was just chosen.

The decision brief carries two distinctions that ADR-0004/0007 make mandatory: (1) it names **both the opener** (the build NOW, chosen for fastest-defensible-time-to-traffic) **and the highest-ceiling tool** when they differ; and (2) it includes a **short 3–4-step ordered roadmap** (brief §7) — the next build plus its position in a sequence that compounds authority on the link-spine, not a lone pick.

**The gold-standard model to mirror** for voice, density, and the "honest correction" habit is `micro-tool-factory/strategy/07-FIRST-TOOL-DECISION.md` (the first-tool decision: timecard calculator). Match its quality — cited evidence inline, a §0 supersede note when you overturn a prior pick, a live keyword-verification section that *closes its own caveat*, and an explicit "this diverges from the inherited ranking" paragraph. Do not write thinner than that.

Each template below is a fenced block a human (or you) fills in. Replace every `<...>`. Keep the headings; they are the contract the next agent reads.

---

## 1. Decision Brief — `NN-NEXT-TOOL-DECISION.md`

The flagship artifact. Mirrors `07-FIRST-TOOL-DECISION.md` section-for-section. It must (a) carry a **§0 supersede note** if it overturns any prior draft/pick, (b) contain the **"divergence from the inherited ranking explained"** paragraph, and (c) contain the **honest corrections** subsection inside the red-team section (e.g. "display-first, not affiliate-rich"). A brief without those three is incomplete.

````markdown
# NN — NEXT TOOL DECISION: <Hub> → <Tool>

> **What this is.** The pick: which hub this belongs to, and the single next tool to build. It reconciles the prior research/rankings, validates the choice on fresh 2026 search/competition/monetization data, re-scores the in-hub candidates on the balanced deterministic model, and adversarially verifies the winner. Companion file: [`NN-NEXT-TOOL-SCORECARD.xlsx`](NN-NEXT-TOOL-SCORECARD.xlsx) · build brief: [`NN-<tool>-BUILD-BRIEF.md`](NN-<tool>-BUILD-BRIEF.md).
> **Date:** <YYYY-MM-DD>. **Status:** DECIDED (mode: <--checkpoints | --auto>). **Supersedes:** <prior draft/decision, or "none">. Builds on [07-FIRST-TOOL-DECISION](07-FIRST-TOOL-DECISION.md), [04-IDEA-RESCORE](04-IDEA-RESCORE.md).

---

## 0. Note — what this supersedes / corrects  (DELETE if nothing is overturned)

<If this overturns a prior pick or an inherited #1, say so plainly and say WHY in one paragraph: the false premise, the gate it failed, or the real-data number that demoted it. Name the specific claim that was wrong (e.g. "the prior draft scored X off the head term alone; fresh long-tail data re-rated winnability up"). Confirm any user-dependent premise was checked with the user on <date>. This is the same move §0 of 07 makes when it kills the freelance-rate pick.>

---

## 1. TL;DR — the verdict

- **Hub: <hub>.** <one-line why it passed the hub pre-flight gate-drill: one persona, ≥3 tools drilled-winnable, low YMYL/AIO pressure, embed-friendly, link-spine compounds.>
- **Opener (build NOW): `<Tool>`.** Chosen for **fastest-defensible-time-to-traffic / survival** (ADR-0004), not peak Opportunity — <one line: proven durable demand + an EVIDENCED thin-site long-tail path + AI-resistance + a real revenue floor + easy static build>. The only candidate with **no dimension scored 1** and `first_build_eligible`.
- **Highest-ceiling tool (if different from the opener): `<Tool>`.** <the bigger-Opportunity tool that is slower/competition-gated, so it becomes build #2 once revenue de-risks the wait. State this explicitly when it differs from the opener — the "first build" and "highest-opportunity tool" can legitimately diverge, ADR-0004.>
- **Runner-ups, in order:** **#2 <tool>** (<one-line why>), **#3 <tool>** (<one-line why — e.g. highest-revenue but competition-gated, so a fast-follow>).
- **One correction to the inherited thesis:** <the honest correction, e.g. build display-ads-first; affiliate is an upside kicker on the buyer slice only — most of the audience won't purchase>.
- **Avoid as the next build:** <trap tools + the ONE dimension each fails: e.g. X (high volume, unwinnable head); Y (winnable + trivial but near-zero revenue); Z (AI-vulnerable — chatbots already emit the output)>.

## 2. How this was decided

1. **Reconciled the prior research** into one canonical baseline. <which doc is canonical; which ranking was treated as a stale hypothesis, not a verdict>.
2. **Sourced 10–12 deduped in-hub candidates**, ran **Gates A→B→C→D in order** (cheapest first, stop at first failure). Dropped: <list + the gate each failed>.
3. **Scored survivors on the deterministic balanced model** (Demand 0.20, **Winnability 0.25**, **AI-Resistance 0.25**, Revenue 0.20, Build 0.10), tagging each score's evidence tier.
4. **Pulled real keyword volume** (Stage 5, BLOCKING) and **adversarially verified the winner** (Stage 6) — tried to kill it on demand, winnability, and revenue-to-buyer-slice, then kept what survived.

## 3. Hub decision — <confirmed | changed>, with fresh evidence

<2–5 bullets, each cited. Why this hub clears the hub gate vs the alternatives. Reference the macro thesis: interactive/transactional tool queries are the AI-Overview safe zone (~10–16.5% transactional AIO trigger vs ~99% informational); the AIO-resistant intents overlap the higher-CPC intents; ad-network minimums are low enough to monetize at small scale. Include the sober caveat (RPM softening / AIO down-funnel creep). Cite sources inline like 07 does.>

**Verdict:** open/continue with the <hub> hub — <one-line summary of the gate result>.

## 4. The balanced scorecard  (full evidence in the xlsx)

Scores 1–5 per dimension on the deterministic anchors, weighted into a 0–100 `Opportunity`. Winner first.

| # | Tool | Demand .20 | Winnability .25 | AI-Resist .25 | Revenue .20 | Build .10 | **Score** | Verdict |
|---|------|:--:|:--:|:--:|:--:|:--:|:--:|---|
| 1 | **<winner>** | <5> | <4> | <5> | <4> | <4> | **<89>** | **BUILD NEXT** |
| 2 | <tool> | | | | | | | <build #2/#3> |
| 3 | <tool> | | | | | | | <revenue anchor — fast-follow> |
| … | <tool> | | | | | | | <⚠ trap: fails ONE dimension — name it> |

<One sentence naming the "high score but trap" tools and the single dimension each fails — the reason a balanced (not raw-demand) model is the right lens.>

## 5. The pick — <Tool>

<One-line description of exactly what the tool does and the artifact it produces.>

**Demand — <tier>.** <proven incumbent traffic / cluster size; seasonality note; cite Similarweb/keyword tool>.

**Winnability — <tier>.** <the long-tail proof: a thin/low-DR site already ranking; the variant pages incumbents publish that map the roadmap; the honest ramp caveat (head ≈ year-2, long-tail ≈ months 3–12). Cite.>

**AI-resistance — <tier>.** <live AIO check result for the head-class query; why an interactive stateful tool sits in the resistant band; what to monitor (inline widgets, down-funnel AIO creep). Cite.>

**Revenue — <tier> (honest correction).** <measured CPCs on core terms; live affiliate programs + payouts; THEN the correction: which slice of the audience actually buys, and therefore display-first vs affiliate-rich. Cite.>

**Build — <tier>.** <static client-side scope; where the real work is (edge-case correctness + breadth of long-tail variant pages = the SEO moat)>.

**Why it's the next build:** <the all-rounder argument — scores 4–5 on every dimension, anchors the hub, proven ranking path, AI-resistant, pays from day one, variant pages give an internal-linkable roadmap that compounds topical authority>.

## 6. Why not the others

- **#2 <tool> (<score>).** <strengths; the two points it loses to the winner on; when to build it>.
- **#3 <tool> (<score>) — the revenue anchor.** <highest monetization ceiling but competition-gated; the scoped long-tail angle; how the winner feeds it>.
- **<trap tool> (<score>) — the <volume|revenue|winnability> trap.** <why it fails its one dimension; revisit-later condition>.
- <…one bullet per remaining gated candidate…>

## 7. Ordered roadmap — the next build PLUS its position in a 3–4-step sequence (ADR-0007)

The deliverable is **not a lone pick** — tools in a hub share a link-spine, so build *order* compounds topical authority. State the 3–4-step roadmap, with the opener foregrounded. It is a re-derivable sketch (data changes every run), never a frozen plan; only step 1 (the now-pick) is decided with full rigor.

1. **<opener / winner>** — the build NOW, chosen for fastest-defensible-time-to-traffic (ADR-0004); the long-tail variant pages to spin. <If the highest-ceiling tool differs, say so: "opener for speed; #<n> is the higher-ceiling build once revenue de-risks the wait.">
2. **<tool>** — the same-hub fallback (Stage 7) reframed as roadmap position #2; <role in the cluster>.
3. **<tool>** — <role; climbs the opportunity ceiling once revenue de-risks the wait>.
4. **<tool>** — <round-out spoke for internal-link gravity / preserves fallback depth>.

Internal-link spine: <axis A: tool → tool → tool> on the "<what the user is trying to do>" axis; <axis B spokes>. Every page links to ≥2 siblings.

**Next hub candidate (carried forward):** <hub + lead tool + the open question to resolve before committing>.

## 8. Divergence from the inherited ranking — explained

<MANDATORY paragraph. State which inherited top picks were demoted and the exact gate or real-data number that did it. Pattern from 07: "The balanced re-score deliberately diverges from the internal cluster ranking, which had X and Y on top (raw score NN). Fresh competition + AI data demote both: X is unwinnable for a new domain (winnability 1), and Y's head term is <100/mo. The all-rounder that wins is <winner>." If this run did NOT diverge from the inherited ranking, say so explicitly and explain why the inherited ranking survived live re-verification — do not silently omit this section.>

## 9. Confidence, fallback, switch-trigger, monitor-list

<short pointer to artifact 5 (the confidence-and-fallback block) — or inline it here. Must name: per-claim confidence tier, the same-hub fallback + its switch trigger, the monitor cadence, and the single gating first-build action.>

## 10. Live keyword-volume verification — <tool/source> (<date>)

<Closes the demand caveat with REAL data (see artifact 3 for the full table). Mirror §10 of 07: state the source + database + that it's banded/directional unless a paid seat was used; present the volume table; then a "Confirms/changes the decision" paragraph and a "KD reality check" paragraph (every money head is likely KD Hard → the path is the long-tail, never the bare head).>

## Sources (key)

<grouped by theme — macro/AIO/AdSense · the winner's niche · runner-ups · others — inline-citable, like §9 of 07. End with the method note: "Search-volume figures triangulated from incumbent traffic + keyword-tool citations; exact Google volumes sit behind paid tools. Scores are a research-grounded synthesis on the deterministic anchors, not vendor metrics.">
````

---

## 2. Scored Spreadsheet — `NN-NEXT-TOOL-SCORECARD.xlsx`

One row per **gated candidate** (only those that passed Gates A–D — dropped candidates do not get a row, but note them below the table). Build it with the `xlsx` skill so the formula is **live**, not a typed-in number.

**Columns (in order):**

| Col | Header | Contents |
|-----|--------|----------|
| A | `Tool` | candidate name; winner in row 2, sorted by Opportunity desc |
| B | `Demand` | 1–5 (deterministic anchor) |
| C | `Winnability` | 1–5 |
| D | `AI-Resistance` | 1–5 |
| E | `Revenue` | 1–5 |
| F | `Build` | 1–5 |
| G | `Opportunity` | **LIVE formula** (below) |
| H | `Demand-tier` | real-measured / triangulated / reasoned |
| I | `Winnability-tier` | real-measured / triangulated / reasoned |
| J | `AI-tier` | live-checked / reasoned |
| K | `Revenue-tier` | real-measured / triangulated / reasoned |
| L | `Veto?` | flags `VETO` if any of B:F = 1 |
| M | `Notes` | one-line evidence pointer per row (the load-bearing fact) |

**The live Opportunity formula** (note the column letters: Demand=B, Winnability=C, AI=D, Revenue=E, Build=F — so the canonical weighting `0.20·D + 0.25·W + 0.25·AI + 0.20·Rev + 0.10·B` maps to the spreadsheet as below). Put this in `G2` and fill down:

```
=(0.20*B2 + 0.25*C2 + 0.25*D2 + 0.20*E2 + 0.10*F2)*20
```

> Authoring note: the skill's prose writes the formula in *dimension* order as `=(0.20*D+0.25*W+0.25*AI+0.20*Rev+0.10*B)*20` where D=Demand, W=Winnability, B=Build. In the actual sheet, Demand sits in column B and Build in column F — so transcribe carefully. Either layout is fine as long as each weight multiplies its own dimension; verify one row by hand before trusting the column.

**Veto flag** in `L2`, fill down (any dimension = 1 disqualifies a first/next build regardless of total):

```
=IF(COUNTIF(B2:F2,1)>0,"VETO","")
```

Add a **conditional-format rule**: highlight the whole row red when `$L2="VETO"`. Tier columns (H–K) get a 3-color scale or data-validation dropdown (`real-measured` greenest → `reasoned` reddest) so a glance shows which scores rest on guessed inputs.

Below the table, a short block: **Dropped at gates** — `<candidate> — failed Gate <A|B|C|D> (<reason>)`, one line each. And the **weighting legend** so the sheet is self-documenting.

---

## 3. Real Keyword-Volume Table — (section in the brief + a tab in the xlsx)

The artifact that turns Demand from `triangulated` into `real-measured`. **One block per finalist.** Pull it browser-driven per `references/free-tools.md`; record the band, not a false-precision single number, unless a paid seat was used.

```markdown
### Real keyword volume — <Tool>  (source: <Ahrefs free Keyword Generator | Keyword Surfer | …>, <DB e.g. US>, <YYYY-MM-DD>)

| Head term | Volume band | Midpoint | KD bucket | Cluster size | Source | Date |
|-----------|-------------|:--------:|:---------:|:------------:|--------|------|
| `<head term>` | `<>10,000 | >1,000 | >100>` | <geometric midpoint of the band> | <Easy/Medium/Hard> | <N kws> | <tool> | <YYYY-MM-DD> |
| `<second in-cluster head>` | | | | | | |

**Qualifier test (the row that proves the call):**
| Term | Volume band | Midpoint | KD | Note |
|------|-------------|:--------:|:--:|------|
| `<broad commercial term>` | <band> | | | the term you'd actually rank/monetize |
| `<persona/qualifier-flavored term>` | <band> | | | proves whether the qualifier guts the volume (e.g. "freelance X" = ~100× smaller than "X") |

**Read:** <✅/⚠ one line — does the real data confirm or contradict the score? Cluster ≥ ~5k/mo to clear the Stage-5 gate? Did the qualifier kill it?>
```

Repeat for each finalist. The qualifier-test rows are not optional — they are what caught the freelance-rate trap in 07 (head `freelance rate calculator` = >100/mo, all variants <100, vs `invoice generator` = >10k/mo at the same commercial intent).

---

## 4. Adversarial Red-Team Verdict — (section in the brief)

A SEPARATE skeptic re-checks every load-bearing claim. **Always include the three mandatory rows:** real volume, AI-Overview presence, revenue-to-buyer-slice. Any outright `failed` promotes the same-hub runner-up and re-runs Stages 5–6 on it (do not paper over a failure).

```markdown
## Red-team verdict — tried to kill <Tool>

| # | Load-bearing claim | How it was re-checked | Result | Correction applied → resulting stance |
|---|--------------------|------------------------|:------:|----------------------------------------|
| 1 | **Real demand:** <the volume claim> | <re-pull in <tool>/<DB>; check broad commercial term, not the persona term> | survived / corrected / **failed** | <e.g. "head confirmed >10k/mo; kept Demand=5"> |
| 2 | **AI-Overview presence:** <"no AIO fires on the head-class query"> | <live SERP check on <date>, incognito, <region>; note any inline widget> | survived / corrected / **failed** | <e.g. "no AIO observed; monitor inline date/time widget"> |
| 3 | **Revenue-to-buyer-slice:** <the monetization claim> | <who actually buys? discount affiliate to the buyer slice; verify program payouts live> | survived / corrected / **failed** | <e.g. "much of the audience won't purchase → display-FIRST, affiliate a secondary kicker"> |
| 4 | <any other claim the score leans on, e.g. winnability proof site> | <method> | survived / corrected / failed | <stance> |

**Net verdict:** <SURVIVED — <Tool> holds | CORRECTED — holds with the honest corrections above baked into the brief | FAILED on claim <n> — promoted same-hub fallback <fallback>, re-ran Stages 5–6 (see below)>.
```

The "corrected" outcomes are the honest-corrections record — they MUST flow into the Decision Brief §5 (revenue) and the Build Brief monetization slots, not just live in this table.

---

## 5. Confidence + Fallback + Switch-Trigger + Monitor-list — (section in the brief)

Makes the bet honest and pre-commits the pivot conditions, so a later soft signal doesn't trigger an ad-hoc panic re-pick.

```markdown
## Confidence, fallback, and monitoring

### Per-claim confidence
| Claim | Confidence | Basis (source + date) |
|-------|:----------:|------------------------|
| <demand / volume> | high / med / low | <source, YYYY-MM-DD> |
| <winnability / long-tail path> | high / med / low | <proof site + date> |
| <AI-resistance> | high / med / low | <live SERP, date> |
| <revenue floor + buyer slice> | high / med / low | <CPC/affiliate source, date> |

### Named same-hub fallback
- **Fallback tool: <runner-up, SAME hub>** — <one-line why it's the safe second>.
- **Switch trigger (pre-committed):** swap to the fallback if **<measurable condition>** — e.g. "after 90 days live, the long-tail variant pages are not ranking top-20 for any target term," or "real volume re-verified in a paid seat lands <5k/mo cluster," or "an AI Overview begins firing on the head-class query."

### Monitor-list (with cadence)
| Signal | Why it matters | Re-check cadence |
|--------|----------------|------------------|
| AI-Overview creep onto the head-class / down-funnel commercial terms | erodes the AI-resistance moat | monthly |
| Real volume in a paid Ahrefs/Semrush seat | banded free data is directional only | once before build commit + at 90 days |
| Ad-network thresholds (Raptive 25k pv/mo, Mediavine Journey 1k sessions/mo, Ezoic ~none) | gates when display monetization turns on | quarterly |
| Affiliate program terms/payouts for the buyer slice | the secondary revenue kicker can change | quarterly |
| <niche-specific signal, e.g. Google inline widget for this calculator type> | direct substitution risk | monthly |

### Gating first-build action
- <the single thing that must happen before any code, e.g. "buy one brandable non-keyword .com; stand up the hub on the Astro v6 / Cloudflare stack per 05-STACK-ARCHITECTURE-ADR">.
```

---

## 6. Starter Build Brief — `NN-<tool>-BUILD-BRIEF.md`

Enough to start building immediately. The through-line: **the differentiators ARE the AI-resistance moat AND the long-tail page roadmap** — they are the same list viewed two ways.

````markdown
# NN — BUILD BRIEF: <Tool>

> Companion to [`NN-NEXT-TOOL-DECISION.md`](NN-NEXT-TOOL-DECISION.md). Scope to start; a full spec is a separate deliverable if needed.
> **Stack:** Astro v6 / Cloudflare (per [05-STACK-ARCHITECTURE-ADR](05-STACK-ARCHITECTURE-ADR.md)). **Tools live at** `/category/slug`.

## Context
- <starting state: domain bought? hub stood up? where this tool slots in the cluster sequence>.

## What it does (one paragraph)
<the tool, the inputs, the artifact it produces, the export/share affordances>.

## Differentiators — these ARE the AI-resistance moat
The specific interactive features top results lack. Each is (a) a reason a chatbot can't replace the tool inline, and (b) a long-tail page (see roadmap). Do one thing each top result doesn't:
- <feature 1 — e.g. CSV / print export>
- <feature 2 — e.g. an extra mode the incumbents split across pages>
- <feature 3 — e.g. a region/preset rule incumbents handle poorly>
- <feature 4 — save/share link (stateful, un-synthesizable)>

## Long-tail page roadmap — one variant = one URL
The internal-link spine. Each page is genuinely different in structure (not a spun template), and links to ≥2 siblings + a short genuine guide/FAQ.

```
/<tool>/                 (pillar / hub page)
  → /<variant-1>         <e.g. /biweekly>
  → /<variant-2>         <e.g. /with-lunch-breaks>
  → /<variant-3>         <e.g. /with-overtime>
  → /<variant-4>         <e.g. /california  (a state/region preset)>
  → /<variant-5>         <e.g. /weekly>
```
Sibling-link rule: every variant links to ≥2 others + the pillar. This spine is the topical-authority engine — not extra traffic for its own sake.

## Monetization slots — display-first
- **Display ad units AROUND (never inside) the tool** — header/below-results/sidebar; never interrupt the interaction.
- **ONE contextual buyer-slice affiliate CTA on the RESULTS state only** — e.g. "<running payroll for a team?>" → <affiliate>. Honest, secondary, shown only to the slice that would actually buy.
- Display is the floor and the day-one engine; affiliate is an upside kicker on the buyer slice — **unless the red-team confirmed a real buyer majority** (it usually doesn't; see Decision Brief §5).

## Correctness / unit-test list — accuracy is the product
The edge cases that MUST be right; this is the accuracy that earns the links and rankings in this niche.
- [ ] <edge case 1 — e.g. overnight / cross-midnight handling>
- [ ] <edge case 2 — e.g. rounding rules>
- [ ] <edge case 3 — e.g. daily-vs-weekly threshold interaction>
- [ ] <edge case 4 — e.g. the region/preset rule>
- [ ] <edge case 5 — empty/partial input, locale, very large values>

## Don'ts
- Don't mass-spin near-identical pages (2024–26 scaled-content / site-reputation risk).
- Don't chase the bare head term on day one (KD Hard — buy the long-tail).
- Don't lean the revenue model on affiliate (display-first; affiliate is the kicker).
````

### Memory log (the tail of Stage 8 — do not skip)

After emitting artifacts 1–6, log the decision to project memory so the next run of this skill does not re-pick what was just chosen:

1. **Append a dated entry** to `MEMORY.md` (or its referenced files): chosen hub + tool, the scoring model used, the Opportunity score, and **what was superseded** (the prior draft/pick this overturns, in writing).
2. **Update the MEMORY index** with a one-line pointer to the new dated entry.
3. Use the `consolidate-memory` / memory-management skill if available to merge duplicates and prune stale entries.

The supersede note must exist in BOTH the Decision Brief §0 and the memory entry — the brief is the durable record, the memory entry is what the next agent reads before sourcing candidates.
