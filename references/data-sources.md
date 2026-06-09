# Data sources — free-first tooling + missing-data handling

## Contents

1. [Free-first tooling map](#free-first-tooling-map)
2. [Missing-data handling](#missing-data-handling)
3. [live-recheck — stale quotas and thresholds](#live-recheck--stale-quotas-and-thresholds)
4. [Reuse from pick-next-tool](#reuse-from-pick-next-tool)

---

## Free-first tooling map

Every field is collected free-first. Paid escape hatches exist for scale or coverage gaps — use them only
when the free path is exhausted or returns no data.

| Need | Free tool | Evidence tier | Paid escape hatch |
|---|---|---|---|
| CWV (LCP/CLS/INP) | chrome-devtools: `performance_start_trace` (reload=true) → `performance_stop_trace` → `performance_analyze_insight` | real-measured | — |
| a11y score | chrome-devtools heuristic: `take_snapshot` + `evaluate_script` (form-label, ARIA, alt, heading, lang) → `triangulated`/`reasoned`; `null` if not assessed | triangulated / null | — |
| Structured data (JSON-LD) | `scripts/parse_jsonld.py --url <url>` — fetch + extract + validate | real-measured | — |
| **SERP positions (1–10)** ⚠ REQUIRED | **SerpApi** (`SERPAPI_KEY`) — browser SERP is CAPTCHA-blocked; key lives in project-root `.env` | real-measured | DataForSEO |
| **AI-Overview presence + citations** ⚠ REQUIRED | **SerpApi** `ai_overview` parameter (same key) | real-measured | — |
| **SERP features (featured snippet, PAA, onebox)** ⚠ REQUIRED | **SerpApi** (same key) | real-measured | — |
| **Domain authority (DR)** ⚠ REQUIRED | **OpenPageRank** (`OPENPAGERANK_API_KEY`): `page_rank_decimal` (0–10) × 10 → `dr` (0–100); understates true Ahrefs DR — ordinal use only; key lives in project-root `.env` | triangulated | Ahrefs paid (true DR) |
| Referring domains count | **NOT available from OpenPageRank or chrome-devtools.** Requires Ahrefs or Similarweb (paid/manual). Without it, `authority` dimension is a LOWER BOUND — mark `referring_domains` `UNVERIFIED`. | — | Ahrefs paid / Similarweb paid |
| Traffic estimate | Similarweb free site overview (`similarweb.com/website/<domain>/`) | triangulated | Similarweb paid / Ahrefs paid |
| Keyword footprint | Ahrefs free Keyword Explorer "Top keywords" tab (manual, no key) | triangulated | Ahrefs paid |
| Demand / volume buckets | Reuse `pick-next-tool` `volume_buckets.py` / `autocomplete_fanout.py` outputs | real-measured (if already run) | Google Ads API (paid seat) |
| Page content (word count, headings, DOM) | `fetch` + DOM parse (chrome-devtools `get_page_content` or `parse_jsonld.py` pattern) | real-measured | — |
| Mobile screenshots / render | chrome-devtools `emulate` + `take_screenshot` | real-measured | — |

---

## Missing-data handling

These are defining features of the pipeline, not afterthoughts. Every rule below is enforced by the scripts.

**Fail closed at the engine.**
`competitor_strength.py` and `gap_opportunity.py` raise `ContractError` on any missing or ill-typed required
field. The engine will not produce a score from incomplete data. A `ContractError` must be resolved by going
back and measuring the missing field — not by guessing a plausible value.

**REFUSE over guess.**
If a required field cannot be measured (e.g. Similarweb shows no data for a small site), tag the field
`UNVERIFIED` with a reason in the ledger. A competitor with UNVERIFIED required fields gets no committed
score. "Insufficient data" is a first-class, legal output. Do NOT fill missing fields with industry averages
or adjacent-site proxies unless the source is explicitly cited and tiered `triangulated`.

**Empty scrape ≠ 0.**
If `parse_jsonld.py` returns an empty list, that is a real-measured `schema_types=[]` result (no structured
data found). It is NOT a measurement failure. But if the fetch itself fails (network error, 403, timeout),
that is a hard failure — log it loudly, mark the field `UNVERIFIED`, do not silently record `[]`.
Same principle for all DOM scrapes: a failed fetch must be reported, not silently zero-ed.

**UNVERIFIED claims are hypotheses only.**
Any field tagged `UNVERIFIED` must not back a committed exploit or a `build-now` gap. It may appear in
`open_questions` in the PRD-SEED. Gate B (Stage 3) enforces this.

---

## live-recheck — stale quotas and thresholds

Data sources and platform behaviors change. The items below have known staleness risk.
Re-verify each before a production run if more than 90 days have passed since the skill was last validated.

| Item | Current assumption | How to re-verify |
|---|---|---|
| **SerpApi free cap** | 100 searches/month on free plan | Check `serpapi.com/pricing` — free tier cap may change; update `SETUP.md` if so |
| **OpenPageRank → DR mapping** | OPR `domainRank` 0–10 scale; proxy for Ahrefs DR (0–100) but systematically understates by ~15–20 DR points | Compare OPR output vs Ahrefs Website Authority Checker on 5 known domains; recalibrate the note in `pillars.md` Pillar 2 |
| **CWV "Good" thresholds** | LCP ≤ 2500ms, CLS ≤ 0.1, INP ≤ 200ms (per web.dev/vitals as of 2025) | Check `web.dev/vitals` for any updated thresholds; update the scoring-model.md tables and `competitor_strength.py` `_ux_perf_a11y()` if changed |
| **AI-Overview prevalence** | AI Overview appears on a large share of informational queries; tool/calculator queries show lower prevalence | Run a fresh SERP sample of 10 tool-type queries; note AIO prevalence %; update Gate C trigger guidance in `audit-procedure.md` if prevalence has shifted significantly |
| **Similarweb free data lag** | Free tier shows ~3-month lag; covers sites with ≥10K monthly visits | Verify by comparing a known site's Similarweb free vs paid data; update the lag note in the tooling map above |
| **Lighthouse scoring model** | Lighthouse v12 weights (perf score formula may change across major versions) | Check `github.com/GoogleChrome/lighthouse/releases` for scoring-model changes; note Lighthouse version in each audit's ledger entry |

---

## Reuse from pick-next-tool

If `pick-next-tool` has already been run for this tool slug, ingest its outputs rather than re-fetching:

- **`builds/<tool-slug>/research-raw.json`** — check for `volume_buckets` and `autocomplete_fanout` keys;
  use the `cluster_monthly_volume` and `head_bucket` values directly for `gap_opportunity` `demand` scoring.
- **`builds/<tool-slug>/RESEARCH-BRIEF.md`** — may contain competitor mentions from Stage 1 to use as seeds.

When reusing, tag the reused values as `evidence_tier: "real-measured"` only if the pick-next-tool run itself
measured them live. If the source JSON shows `evidence_tier: "triangulated"` or `"reasoned"`, carry that tier
forward unchanged — never silently upgrade.

Do not re-fetch data that is still fresh (< 7 days old for SERP; < 30 days for authority/traffic estimates).
Record the original `date_accessed` from the prior run in the ledger entry, not today's date.
