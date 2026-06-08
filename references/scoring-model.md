# Scoring model — deterministic, evidence-tagged

The whole point: **the same candidate must score the same number for any agent on any run.** Subjective 1–5 "vibes" are what made three agents pick three tools. Every dimension below has a deterministic rule. Eyeballing a score is a skill failure.

## The formula

```
Opportunity = (0.20·Demand + 0.25·Winnability + 0.25·AI-Resistance + 0.20·Revenue + 0.10·Build) × 20
```

→ a 0–100 score. Weights are LOCKED before scoring (do not re-tune to fit a favorite). Winnability + AI-Resistance (0.25 each) outrank Demand (0.20) so a zero-authority site optimizes for "can I rank it" and "will AI eat it" over raw volume.

**`scripts/score.py` is the single source of truth for the numbers.** It takes the *measured inputs* the research workflow returns and computes each dimension deterministically — the same inputs always yield the same score, for any agent or run. The tables below explain what `score.py` does; if a table and `score.py` ever disagree, **`score.py` wins** and the table is the bug. (This doc↔code agreement is the whole anti-variance mechanism — keep them in sync.) **`score.py` also evaluates the kill-gates from the inputs and returns `status="DROP"` + the SINGLE gate that fired with `opportunity=null` for any gate-failure — so a dropped tool carries no number. NEVER quote an Opportunity total from memory or from the inherited ranking; run the candidate through `score.py` and paste its literal output. A number you did not actually run is a fabrication (this happened in testing — an agent "quoted" a 74.0 the engine never produced).**

**Two hard rules over the math:**
1. **GATE-FAIL vs VETO.** A candidate that FAILS any kill-gate (A–D) is **dropped before scoring — emit NO Opportunity number for it** ("scoring it for the record" launders a dropped tool back in). The **VETO** is the backstop for candidates that *passed* all gates: any dimension scored `1` — in practice Revenue, AI-Resistance, or Build, since Demand=1 already fails Gate D and Winnability=1 already fails Gate B — disqualifies it as a *first build* regardless of total. The first build is lowest-risk-on-all-axes, not highest-on-one.
2. **EVIDENCE TIER** — every score is tagged `real-measured` / `triangulated` / `reasoned`. A high score on a guess is provisional and is visibly distrusted until Stage 5 verifies it. No winner may rest its Demand on anything below `real-measured`. Data handed to you in a prompt is `triangulated` by default — treat it as `real-measured` ONLY if the prompt explicitly states it is live/measured. Never silently upgrade a tier to clear IRON LAW 1.

---

## 1. Demand (weight 0.20) — cluster-based, bucket-deterministic

Measure the **cluster** (head term + every long-tail variant for the same tool intent), never a single keyword. A tool is a destination; total addressable searches across phrasings is what matters.

**Procedure:**
1. Seed the head term. Enumerate every phrasing variant that resolves to the SAME tool intent (from Keyword Planner, Ahrefs free Keyword Generator, and live Google autocomplete + People-Also-Ask + related searches).
2. Record the inputs `score.py` needs: **head_bucket** (`<100 / 100-1K / 1K-10K / 10K-100K / >=100K`), **cluster_kw_count** (keywords in the tool's cluster — Ahrefs shows "X of N keywords"), **cluster_monthly_volume** (summed monthly searches across the whole cluster — Gate D is judged on THIS), **distinct_variants** (count of distinct non-zero phrasings), and **incumbent_top3_visits** (combined monthly traffic of the top-3 ranking sites, from Similarweb). Demand is the head bucket PLUS a deep-cluster bonus — you need both real head volume AND a real long-tail, or it is a one-keyword novelty.
3. Sanity-check the head term against Bing Webmaster Tools (a real integer, free) and the Google Trends 24-month slope. If Bing disagrees with the Keyword Planner bucket by >1 order of magnitude, use the lower value and flag it.
4. **Score** — computed by `score.py` `demand_score` (the source of truth). The rule it implements:
   - **Base** from `head_bucket`: `<100`→1, `100-1K`→2, `1K-10K`→3, `10K-100K`→4, `>=100K`→5.
   - **+1** (cap 5) ONLY if `cluster_kw_count ≥ 400` **and** `incumbent_top3_visits ≥ 1,000,000` — a deep cluster *and* real traffic, both required.
   - **Floor to 1** if `distinct_variants < 3` (a one-keyword novelty, not a destination).

**Gate D (the demand gate):** FAIL if `cluster_monthly_volume` < ~1,000/mo OR `distinct_variants < 3` OR a clearly negative 24-mo Trends slope. `score.py` enforces this automatically and emits `DROP — Gate D` (no Opportunity number). A Gate-D failure **drops the candidate as an anchor** (it may survive only as an internal-link fast-follow page) and is **NOT** rescued by strong Revenue/AI/Build — a tool you cannot drive traffic to monetizes nothing.

---

## 2. Winnability (weight 0.25) — KD + weakCount rubric

Anchored to two **measurable** inputs:
- **KD** = Ahrefs free Keyword Difficulty of the head term (a number).
- **weakCount** = count of WEAK results in the live top-10, where WEAK = a Reddit/forum/Quora/UGC thread, a YouTube result, a DR<30 site, a thin one-pager, an exact-match-domain squatter, or an off-topic/loose-match result.

| Score | Rule | New DR<20 site outlook |
|---|---|---|
| **5** very winnable | KD 0–5, and/or weakCount ≥ 4 | top-3 in ~3–6 mo (post-sandbox) |
| **4** winnable | KD 6–10, OR KD 11–15 with weakCount ≥ 3 | top-10 in 6–9 mo |
| **3** contested | KD 11–15 with weakCount 1–2 | needs links + 9–12 mo |
| **2** hard | KD 16–20 with no weak results | unlikely within a year without heavy links |
| **1** auto-fail | KD > 20 with zero weak results, OR a Google onebox/calculator/native OS feature answers inline | not winnable as a new site |

**The decisive input — thin-site proof (the long-tail rule):** you buy the long-tail, never the bare head, so head-term KD is a *timeline* signal, not the gate. The strongest positive is `thin_site_proof` = a thin / low-DR / one-page site already ranking the head OR a long-tail variant — live proof a new site can win. When `thin_site_proof` is true, Winnability **floors at 4** (→ 5 if the SERP is also weak, `weakCount ≥ 4`), *regardless of how Hard the head KD is*. The KD table above applies only when there is **no** thin-site proof. (This is exactly why Timesheet scores 4 despite a KD-Hard head — a one-page site ranks its long-tail; without this rule the KD table alone would wrongly score it 1, contradicting the worked calibration below.)

**The exact rule `score.py` `winnability_score` implements:**
1. `native_feature` true (Gate-A onebox / native OS feature) → **1** (overrides everything).
2. else `thin_site_proof` true → **5** if `weakCount ≥ 4`, else **4**.
3. else by head KD: `0–5`→5, `6–10`→4, `11–15`→3, `16–20`→2, `>20`→1; then `weakCount ≥ 4` sets 5, or `weakCount ≥ 3` adds +1 (cap 5).

**Mandatory modifiers (apply in this order):**
- **Native-feature gate = the Gate-A primary kill:** a Google calculator/conversion/definition onebox, or a browser/OS-native feature answering inline, is a **Gate-A HARD KILL** — stop, drop the candidate, emit no score. This is a *separate* condition from the DR-80+ wall (which is a Gate-B kill). Cite whichever single condition actually fires; do not merge them into one "DR-80 wall + native feature" clause.
- **App-store-only competition:** competitors that are app-store apps (not websites) do NOT contest the open-web SERP — count them as ABSENT from the top-10. A web SERP whose only strong results are apps is a weak/empty SERP → a PASS signal, not a wall.
- **Weak-SERP override:** weakCount ≥ 3 → add exactly **+1** to the KD-derived score (apply once, cap at 5). A genuinely better *tool* outranks UGC threads on utility. (weakCount ≥ 4 already sets the base to 5, so the +1 is moot there.)
- **Sandbox cap:** a domain < 3 months old realistically caps at page 2–3 regardless — record as a *timeline* note, not a score change.

---

## 3. AI-Resistance (weight 0.25) — live check, not assumed

Run the live AI-Overview check (see `free-tools.md`) per head term; never infer it from intent alone.

| Score | Rule |
|---|---|
| **5** AI-proof | interactive tool with user-specific input→personalized output (calculators, generators, randomizers, editors, scorers); AIO can't reproduce a personalized result |
| **4** | tool whose answer depends on live/changing data the user supplies |
| **3** | informational tool where AIO fires < 40% and organic still gets clicks |
| **2** | "what is / how many" static-fact query where AIO fires 40–85% |
| **1** dead on arrival | single-fact query with a Google onebox/calculator/conversion widget, OR comparison query where AIO fires 85–95% |

**Hard rule:** if the live check shows a calculator/conversion/definition onebox, cap AI-Resistance at 1.
**Caveat to record:** AI-resistance is "true today, monitor" — AIOs creep down-funnel into commercial terms over time (2026 transactional trigger ~5–14% and rising).

---

## 4. Revenue (weight 0.20) — CPC + niche RPM + buyer-slice affiliate

Signals: head/cluster CPC (free, from Keyword Planner "top of page bid" range); niche RPM band × a **~0.4 tool-page multiplier** (tools are single-pageview, low-dwell — earn 30–60% of article RPM); and whether a real affiliate program exists **for the slice of the audience that actually buys**.

| Score | Rule |
|---|---|
| **5** | CPC > $3 (finance/legal/SaaS) AND a recurring-commission affiliate program AND niche tool-RPM $15–30+ |
| **3** | CPC $0.50–2 AND a real affiliate program exists, OR mid-niche tool-RPM $8–15 |
| **1** | CPC < $0.50 and no affiliate program (commodity utility) |

**The exact rule `score.py` `revenue_score` implements:** base from CPC — `≥$3`→4, `$2–3`→3, `$0.50–2`→2, `<$0.50`→1; **+1** (cap 5) only if a recurring-commission affiliate exists **and** `buyer_slice == "strong"`; forced to **1** if CPC `<$0.50` and no affiliate. The table above is the human-readable view of this rule.

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

## Worked calibration (from the real first-tool run)

These rows are illustrative OUTCOMES, computed **forward** from the rubric on each tool's measured inputs. Never match a candidate backward to a row — score it forward from its own data. Gate-dropped candidates carry **no** Opportunity number (see GATE-FAIL vs VETO above).

| Tool | D | W | AI | Rev | B | Score | Outcome |
|---|:--:|:--:|:--:|:--:|:--:|:--:|---|
| Timesheet / Time-Card Calc | 5 | 4 | 5 | 4 | 4 | **89** | ✅ BUILD FIRST — passed all gates, no dimension = 1 (cluster ≥100k → Demand 5) |
| Email Signature Generator | 4 | 4 | 5 | 4 | 4 | 85 | strong #2 |
| Invoice Generator | 4 | 3 | 5 | 5 | 4 | 84 | money-anchor candidate |
| Freelance Rate Calc | — | — | — | — | — | **DROP** | Gate D FAIL — real cluster < 1,000/mo; survives only as a fast-follow internal-link page, never scored as an anchor |
| QR Generator | — | — | — | — | — | **DROP** | Gate A native-feature kill + Gate B DR-85+ wall (Winnability would be 1); 120k/mo is irrelevant once dropped |
| TikTok Shop Fee Calc | — | — | — | — | — | **DROP** | Gate D FAIL — real < 100/mo today |

The table's lesson: QR has the highest demand and TikTok the easiest SERP, yet each fails a gate and is dropped *before* scoring. Of the survivors, the all-rounder with no dimension = 1 wins — not the highest on any single axis.
