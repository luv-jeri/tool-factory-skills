# Scoring model — deterministic, evidence-tagged

The whole point: **the same candidate must score the same number for any agent on any run.** Subjective 1–5 "vibes" are what made three agents pick three tools. Every dimension below has a deterministic rule. Eyeballing a score is a skill failure.

> **v0 uncalibrated config (see ADR-0002).** Every cutoff and weight below — the Gate-D floor, the KD→score bands, the CPC bands, the demand-bonus condition, the dimension weights — is `v0` judgment from a single first-tool run, **not** calibrated against any shipped outcome. They live as tunable `WEIGHTS` / `THRESHOLDS` config at the top of `scripts/score.py`, tagged "v0 uncalibrated", and are revisited against the outcome ledger as real results arrive. Read `docs/adr/` for the why behind every rule on this page (ADR-0001 ruin-avoidance, 0002 uncalibrated config, 0003 selftest shape, 0004 time-to-rank, 0006 future-SERP, 0008 soft bands, 0009 input integrity).

## The formula

```
Opportunity = (0.20·Demand + 0.25·Winnability + 0.25·AI-Resistance + 0.20·Revenue + 0.10·Build) × 20
```

→ a 0–100 score. Weights are LOCKED before scoring (do not re-tune to fit a favorite). Winnability + AI-Resistance (0.25 each) outrank Demand (0.20) so a zero-authority site optimizes for "can I rank it" and "will AI eat it" over raw volume.

**`scripts/score.py` is the single source of truth for the numbers.** It takes the *measured inputs* the research workflow returns and computes each dimension deterministically — the same inputs always yield the same score, for any agent or run. The tables below explain what `score.py` does; if a table and `score.py` ever disagree, **`score.py` wins** and the table is the bug. (This doc↔code agreement is the whole anti-variance mechanism — keep them in sync.) **`score.py` also evaluates the kill-gates from the inputs and returns `status="DROP"` + the SINGLE gate that fired with `opportunity=null` for any gate-failure — so a dropped tool carries no number. NEVER quote an Opportunity total from memory or from the inherited ranking; run the candidate through `score.py` and paste its literal output. A number you did not actually run is a fabrication (this happened in testing — an agent "quoted" a 74.0 the engine never produced).**

**Two hard rules over the math:**
1. **GATE-FAIL vs VETO.** A candidate that FAILS any kill-gate (A–D) is **dropped before scoring — emit NO Opportunity number for it** ("scoring it for the record" launders a dropped tool back in). The **VETO** is the backstop for candidates that *passed* all gates: any dimension scored `1` — in practice Demand, Revenue, or Build, since Winnability=1 fails Gate B and AI-Resistance=1 fails Gate C and both are killed before this point — disqualifies it as a *first build* regardless of total. The first build is lowest-risk-on-all-axes, not highest-on-one.
2. **EVIDENCE TIER** — every score is tagged `real-measured` / `triangulated` / `reasoned`. A high score on a guess is provisional and is visibly distrusted until Stage 5 verifies it. No winner may rest its Demand on anything below `real-measured`. Data handed to you in a prompt is `triangulated` by default — treat it as `real-measured` ONLY if the prompt explicitly states it is live/measured. Never silently upgrade a tier to clear IRON LAW 1. The engine **enforces this in code** (ADR-0009): `first_build_eligible` is `True` only when Demand, Winnability, and AI-Resistance are all tagged `real-measured`; below that a tool still ranks but is not committable.

---

## Statuses — what the engine returns

`score.py` returns one of four statuses, ranked **OK > VETO > REFUSE > DROP** (tie-break: higher Opportunity, then tool name — deterministic, ADR-0008/#5):

- **OK** — passed every gate, no dimension is 1. Carries an Opportunity number. Committable only if `first_build_eligible` is also true (real-measured evidence, above the finalist bar, within runway, no `sensitivity:` flag).
- **VETO** — passed every gate but a *survivable* dimension (Demand / Revenue / Build) scored 1. Not a first build. Carries an Opportunity number (it ranks below OK).
- **REFUSE** — the evidence is ambiguous/contradictory and the engine will not decide (ADR-0001/0008): a `winnability==1` in the KD noise band with no thin-site proof, or a cross-field contradiction (head bucket implies more volume than the whole cluster). A legal, first-class funnel outcome → **go verify, don't pick.** Carries **no** Opportunity number.
- **DROP** — failed a kill-gate (A/B/C/D). Carries **no** Opportunity number — a dropped tool has no number to launder back in.

REFUSE and DROP both return `opportunity=null`. Only OK and VETO carry a number.

---

## 1. Demand (weight 0.20) — cluster-based, bucket-deterministic

Measure the **cluster** (head term + every long-tail variant for the same tool intent), never a single keyword. A tool is a destination; total addressable searches across phrasings is what matters.

**Procedure:**
1. Seed the head term. Enumerate every phrasing variant that resolves to the SAME tool intent (from Keyword Planner, Ahrefs free Keyword Generator, and live Google autocomplete + People-Also-Ask + related searches).
2. Record the inputs `score.py` needs: **head_bucket** (`<100 / 100-1K / 1K-10K / 10K-100K / >=100K`), **cluster_kw_count** (keywords in the tool's cluster — Ahrefs shows "X of N keywords"), **cluster_monthly_volume** (summed monthly searches across the whole cluster — Gate D is judged on THIS), **distinct_variants** (count of distinct non-zero phrasings), and **incumbent_top3_visits** (combined monthly traffic of the top-3 ranking sites, from Similarweb). Demand is the head bucket PLUS a deep-cluster bonus — you need both real head volume AND a real long-tail, or it is a one-keyword novelty.
3. Sanity-check the head term against Bing Webmaster Tools (a real integer, free) and the Google Trends 24-month slope. If Bing disagrees with the Keyword Planner bucket by >1 order of magnitude, use the lower value and flag it.
4. **Score** — computed by `score.py` `demand_score` (the source of truth). The rule it implements:
   - **Base** from `head_bucket`: `<100`→1, `100-1K`→2, `1K-10K`→3, `10K-100K`→4, `>=100K`→5.
   - **+1** (cap 5) ONLY if `cluster_kw_count ≥ 400` **and** the **lower-bound** traffic estimate clears the line — `incumbent_top3_visits × 0.7 ≥ 1,000,000` (ADR-0008/#6). Using the conservative 0.7× estimate means ±jitter across the 1M line can't toggle a full point; a deep cluster *and* real traffic are both required.
   - **Graded −2 penalty** (floored at 1, never below) if `distinct_variants < 3` — `base = max(1, base − 2)` (#7). A thin phrasing set is a *penalty*, **not** a hard floor-to-1: the real demand floor is measured cluster volume (Gate D), not a hand-counted integer. A high-volume bucket with few variants is dinged, not zeroed.

**Gate D (the demand gate):** FAIL **only** if `cluster_monthly_volume` < 1,000/mo — the measured cluster volume, full stop (#10). `score.py` enforces this and emits `DROP — Gate D` (no Opportunity number). **Gate D no longer fires on `demand==1` or on the variant count** — those are scored as a graded demand penalty, not a hard drop, so the gate's citation never mis-blames "volume" when variants were the cause. (A negative 24-mo Trends slope is a forward-haircut input applied at measurement time per ADR-0006, not a Gate-D condition in the engine.) A Gate-D failure **drops the candidate as an anchor** (it may survive only as an internal-link fast-follow page) and is **NOT** rescued by strong Revenue/AI/Build — a tool you cannot drive traffic to monetizes nothing.

> **Cross-field REFUSE (not Gate D).** If `cluster_monthly_volume` is below the head bucket's own lower bound (`>=100K`→100000, `10K-100K`→10000, `1K-10K`→1000, `100-1K`→100, `<100`→0) — i.e. the head implies more searches than the entire cluster — the engine returns **REFUSE** ("re-measure"), not a number. The cluster cannot be smaller than its own head (#6).

---

## 2. Winnability (weight 0.25) — KD + weakCount rubric

Anchored to two **measurable** inputs:
- **KD** = Ahrefs free Keyword Difficulty of the head term (a number).
- **weakCount** = count of WEAK results in the live top-10, where WEAK = a Reddit/forum/Quora/UGC thread, a YouTube result, a DR<30 site, a thin one-pager, an exact-match-domain squatter, or an off-topic/loose-match result.

| Score | Rule | New DR<20 site outlook |
|---|---|---|
| **5** very winnable | KD 0–5, and/or weakCount ≥ 4 (at any KD ≤ 20) | top-3 in ~3–6 mo (post-sandbox) |
| **4** winnable | KD 6–10, OR KD 11–15 with weakCount ≥ 3 | top-10 in 6–9 mo |
| **3** contested | KD 11–15 with weakCount **0–2** | needs links + 9–12 mo |
| **2** hard | KD 16–20 with weakCount 0–2 | unlikely within a year without heavy links |
| **1** auto-fail | KD > 20 with weakCount ≤ 2 (a +1 weak-SERP bump can only lift it to 2), OR a Google onebox/calculator/native OS feature answers inline | not winnable as a new site |

(The +1 weak-SERP modifier — `weakCount ≥ 3` adds +1, cap 5 — applies on top of the KD base, so e.g. KD 16–20 with weakCount 3 → 3, and KD 11–15 with weakCount 0–2 stays at 3.)

**The decisive input — thin-site proof (the long-tail rule):** you buy the long-tail, never the bare head, so head-term KD is a *timeline* signal, not the gate. The strongest positive is `thin_site_proof` = a thin / low-DR / one-page site already ranking the head OR a long-tail variant — live proof a new site can win. **But the proof must be EVIDENCED to be honored** (ADR-0009/#3): the candidate must carry `thin_site_proof_url` + `thin_site_proof_dr` + `thin_site_proof_keyword` (the ranking page, its DR, and the keyword it ranks for). A bare `thin_site_proof=True` with no evidence is **ignored** — the engine falls back to the KD ladder and raises a flag ("thin_site_proof asserted WITHOUT evidence — treated as unproven"). When the proof *is* evidenced, Winnability floors at 4 (→ 5 if the SERP is also weak, `weakCount ≥ 4`) — **except it is capped at 3 when `kd_head > 80`** (a thin site beating a DR-90+ head is suspect, not proof). The KD table above applies whenever there is no evidenced thin-site proof. (This is why Timesheet scores 4 despite a KD-70 head — an evidenced one-page site, DR 15, ranks its long-tail.)

**The exact rule `score.py` `winnability_score` implements:**
1. `native_feature` true (Gate-A onebox / native OS feature) → **1** (overrides everything).
2. else `thin_site_proof` true **AND evidenced** (url + DR present) → **3** if `kd_head > 80` (cap, #3); else **5** if `weakCount ≥ 4`, else **4**. (Asserted-but-unevidenced thin_site_proof falls through to the KD ladder and is flagged.)
3. else by head KD: `0–5`→5, `6–10`→4, `11–15`→3, `16–20`→2, `>20`→1; then `weakCount ≥ 4` sets 5, or `weakCount ≥ 3` adds +1 (cap 5).

**Gate B — the margin rule (ADR-0008/#4).** A `winnability == 1` is a **confident DROP** only with margin: `native_feature`, OR (`kd_head ≥ 26` AND `weak_count ≤ 1`), OR an *evidenced* DR wall (`dr_wall_evidenced=true`). A `winnability == 1` that sits in the KD `21–25` noise band with `weak_count ≥ 2` and no thin-site proof returns **REFUSE** ("pull more SERP/thin-site evidence"), **not** DROP — a hard cutoff inside the input's own ±5 KD measurement noise is a coin-flip, not a verdict. The Gate-B *citation* branches on the real cause (#11): the "verified DR-80+ wall" wording fires **only** when `dr_wall_evidenced` is true; otherwise it cites the KD/weak-count cause.

**Mandatory modifiers (apply in this order):**
- **Native-feature gate = the Gate-A primary kill:** a Google calculator/conversion/definition onebox, or a browser/OS-native feature answering inline, is a **Gate-A HARD KILL** — stop, drop the candidate, emit no score. This is a *separate* condition from the DR-80+ wall (which is a Gate-B kill, cited as such only when `dr_wall_evidenced`). Cite whichever single condition actually fires; do not merge them into one "DR-80 wall + native feature" clause.
- **App-store-only competition:** competitors that are app-store apps (not websites) do NOT contest the open-web SERP — count them as ABSENT from the top-10. A web SERP whose only strong results are apps is a weak/empty SERP → a PASS signal, not a wall.
- **Weak-SERP override:** weakCount ≥ 3 → add exactly **+1** to the KD-derived score (apply once, cap at 5). A genuinely better *tool* outranks UGC threads on utility. (weakCount ≥ 4 already sets the base to 5, so the +1 is moot there.)
- **Sandbox cap:** a domain < 3 months old realistically caps at page 2–3 regardless — record as a *timeline* note, not a score change.

---

## 3. AI-Resistance (weight 0.25) — live check, not assumed

Run the live AI-Overview check (see `free-tools.md`) per head term; never infer it from intent alone.

Inputs `score.py` consumes: `artifact_type` (`interactive_personalized` / `live_data_tool` / `info_tool` / `static_fact` / `single_fact`), `aio_fire_pct` (% of live SERP checks showing an AI Overview, 0–100, **projected to rank-time** per ADR-0006), and `onebox` (bool).

| Score | Rule |
|---|---|
| **5** AI-proof | `interactive_personalized` (calculators, generators, randomizers, editors, scorers) with `aio_fire_pct ≤ 85`; AIO can't run your tool inline. **Drops to 2 if `aio_fire_pct > 85`** — a very high live AIO means the label is probably wrong, don't ignore it (ADR-0006). |
| **4** | `live_data_tool` (answer depends on live/changing data) with `aio_fire_pct ≤ 85`. **Drops to 2 if `aio_fire_pct > 85`.** |
| **3** | `info_tool` where AIO fires **< 40%** and organic still gets clicks. |
| **2** | `info_tool` with AIO **40 to ≤ 85**, OR `static_fact` with AIO **≤ 85**. |
| **1** dead on arrival | `onebox` present (any type) → 1; OR `info_tool`/`static_fact` with AIO **> 85** (i.e. 86–100); OR `single_fact`/unrecognized artifact type → 1. |

**The exact rule `score.py` `ai_resistance_score` implements:** `onebox` true → 1 (overrides). Then `interactive_personalized` → 5 if `aio ≤ 85` else 2; `live_data_tool` → 4 if `aio ≤ 85` else 2; `info_tool` → 3 if `aio < 40`, 2 if `aio ≤ 85`, else 1; `static_fact` → 2 if `aio ≤ 85` else 1; `single_fact`/anything else → 1.

**Hard rule:** if the live check shows a calculator/conversion/definition `onebox`, AI-Resistance is 1 (Gate C). There is **no** `comparison` artifact type — the real high-AIO cutover is `static_fact`/`info_tool` falling to 1 when `aio_fire_pct > 85`.
**Caveat to record:** AI-resistance is "true today, monitor" — AIOs creep down-funnel into commercial terms over time (2026 transactional trigger ~5–14% and rising). Score `aio_fire_pct` against the **rank-time** SERP, not today's snapshot (ADR-0006).

---

## 4. Revenue (weight 0.20) — CPC + niche RPM + buyer-slice affiliate

Signals: head/cluster CPC (free, from Keyword Planner "top of page bid" range); niche RPM band × a **~0.4 tool-page multiplier** (tools are single-pageview, low-dwell — earn 30–60% of article RPM); and whether a real affiliate program exists **for the slice of the audience that actually buys**.

The CPC base maxes at 4; the only way to reach 5 is the affiliate bonus, and that bonus fires **only when `buyer_slice == "strong"`** — a recurring affiliate program over an audience that mostly won't buy adds nothing.

| Score | Rule |
|---|---|
| **5** | CPC ≥ $3 base (4) **+1** ONLY when a recurring-commission affiliate exists **AND `buyer_slice == "strong"`**. A high CPC alone tops out at 4; without a strong buyer slice the affiliate bonus does not apply. |
| **3** | CPC ≥ $2 (base 3), OR CPC $0.50–2 (base 2) **+1** where the +1 applies ONLY when a recurring affiliate exists **AND `buyer_slice == "strong"`**. |
| **1** | CPC < $0.50 and no affiliate program (commodity utility) — forced to 1. |

**The exact rule `score.py` `revenue_score` implements:** base from CPC — `≥$3`→4, `≥$2`→3, `≥$0.50`→2, `<$0.50`→1; **+1** (cap 5) **only if** `has_recurring_affiliate` **and** `buyer_slice == "strong"`; forced to **1** if CPC `<$0.50` and no affiliate. The table above is the human-readable view of this rule.

**Buyer-slice rule (the check that turns tools display-first):** ask "who in this audience actually purchases?" and discount affiliate to that slice. Employees totalling their own hours won't buy payroll software → display-ads-first, affiliate as an upside kicker only.

2026 ad-network ladder (for context, not scoring): AdSense (no minimum, RPM ~$2–10, the only launch option) → Ezoic (~3–10k visits, ~$5–15) → Mediavine *Journey* / Newor (~10k sessions, ~$10–20) → Mediavine standard (50k sessions OR $5k+ annual ad earnings, ~$15–45) → Raptive (25k visits, ~$30–50). Apply the ~0.4 tool-page discount to all niche RPM priors.

---

## 5. Build-ease (weight 0.10) — engineering effort only

Scored from the tool's own spec, not market data.

| Score | Rule |
|---|---|
| **5** | pure client-side, deterministic, no API, no stale data, single form (percentage/date/unit/BMI calc, randomizer, text formatter) — < 1 day, ~0 maintenance |
| **4** | client-side with non-trivial UI/edge cases (multi-step, canvas/SVG output, in-browser file read) |
| **3** | one free/stable external API OR data that updates yearly (e.g. tax-year tables) |
| **2** | depends on a paid/rate-limited API, or data that goes stale monthly |
| **1** | needs a backend, accounts, or live frequently-changing data feeds |

**`score.py` `build_score` keys:** `pure_client_single_form`→5, `client_side_complex`→4, `one_stable_api_or_yearly_data`→3, `paid_or_monthly_stale`→2, `backend_or_live_feed`→1.

---

## The gates — in order, cheapest first, cite the SINGLE firing cause

`score.py` `evaluate()` runs the gates in order and returns the **one** cause that fired. (Before any gate, the contract fails closed: every `REQUIRED_FIELDS` key is read by direct indexing, so a missing/mistyped key raises `ContractError` rather than silently passing — ADR-0009/#2.)

- **Gate A — policy / native.** `adsense_restricted == true` → **DROP** ("AdSense-restricted vertical"), listed and checked **FIRST** (gambling/alcohol/adult/weapons/drugs are unmonetizable, so no other axis can rescue them — ADR-0009/#5). Then `native_feature == true` → **DROP**.
- **Gate B — winnability.** `winnability == 1` with margin (`native_feature`, OR `kd_head ≥ 26` AND `weak_count ≤ 1`, OR `dr_wall_evidenced`) → **DROP**; otherwise (the KD 21–25 noise band with `weak_count ≥ 2`, no proof) → **REFUSE**, not DROP (ADR-0008/#4). The DR-wall citation fires only when `dr_wall_evidenced` (#11).
- **Gate C — AI Overview / onebox.** `onebox == true` → **DROP**; then `ai_resistance == 1` → **DROP** ("dead on arrival — AI answers this inline", #9).
- **Cross-field contradiction — REFUSE.** `cluster_monthly_volume` below the head bucket's lower bound (`>=100K`→100000, `10K-100K`→10000, `1K-10K`→1000, `100-1K`→100, `<100`→0) → **REFUSE** ("re-measure"): the cluster cannot be below its own head (#6).
- **Gate D — measured demand floor.** `cluster_monthly_volume < 1000` → **DROP**. **Measured volume ONLY** — Gate D no longer fires on `demand==1` or on the variant count, and its citation no longer mis-blames "volume" when variants were the real cause (#10).

After the gates: a survivor is **VETO** if Demand / Revenue / Build is 1 (Winnability=1 and AI-Resistance=1 were already gated); else **OK**.

### The finalist / commit bar (reconciling #8)

The **engine hard-DROP floor is 1,000/mo** (Gate D). The **5,000/mo + 100-kw bar is the finalist / commit bar**, NOT a separate gate: a tool between 1,000 and 5,000/mo (or with < 100 cluster keywords) still passes the gates and **ranks**, but is flagged "below finalist bar" and is **not committable** — it is a fast-follow, not an opener. This bar is enforced as part of `first_build_eligible`, not as an undocumented gate.

`first_build_eligible` (committable now) requires **all** of: status `OK`; evidence `real-measured` on Demand + Winnability + AI-Resistance (ADR-0009); at/above the finalist bar (volume ≥ 5,000 AND cluster_kw_count ≥ 100, ADR-0008/#8); time-to-traffic within runway (`est_time_to_traffic_months ≤ runway_months`, ADR-0004); and no `sensitivity:` flag. Below that bar a tool **ranks** (Stage 4 on triangulated data) but only **commits** at Stage 5 (rank-on-estimates / commit-on-real-data).

---

## Worked calibration (from the real first-tool run)

These rows are illustrative OUTCOMES, computed **forward** from the rubric on each tool's measured inputs. Never match a candidate backward to a row — score it forward from its own data. Gate-dropped candidates carry **no** Opportunity number (see GATE-FAIL vs VETO above).

| Tool | D | W | AI | Rev | B | Score | Outcome |
|---|:--:|:--:|:--:|:--:|:--:|:--:|---|
| Timesheet / Time-Card Calc | 5 | 4 | 5 | 4 | 4 | **89** | ✅ BUILD FIRST — passed all gates, no dimension = 1. **Demand 5 = head bucket 10K-100K (base 4) + deep-cluster bonus** (cluster_kw_count ≥ 400 AND 0.7×top-3-visits ≥ 1M). `cluster_monthly_volume` drives **Gate D only, never Demand** — it is not the source of the 5. (W=4: evidenced thin-site proof, DR 15, over a KD-70 head.) |
| Email Signature Generator | 4 | 4 | 5 | 4 | 4 | 85 | strong #2 |
| Invoice Generator | 4 | 3 | 5 | 5 | 4 | 84 | money-anchor candidate |
| Freelance Rate Calc | — | — | — | — | — | **DROP** | Gate D FAIL — real cluster < 1,000/mo; survives only as a fast-follow internal-link page, never scored as an anchor |
| QR Generator | — | — | — | — | — | **DROP** | Gate A native-feature kill (cited as Gate A, not "DR wall" — `dr_wall_evidenced` was not set); 200k/mo is irrelevant once dropped |
| TikTok Shop Fee Calc | — | — | — | — | — | **DROP** | Gate D FAIL — measured cluster < 1,000/mo (100/mo today) |

The table's lesson: QR has the highest demand and TikTok the easiest SERP, yet each fails a gate and is dropped *before* scoring. Of the survivors, the all-rounder with no dimension = 1 wins — not the highest on any single axis.
