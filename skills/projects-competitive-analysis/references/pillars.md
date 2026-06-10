# Measurement pillars — the 11 pillars

Every analyzed competitor is scored on all 11 pillars. Fields listed here feed the scripts directly;
`references/scoring-model.md` documents how each field maps to a sub-score.

✦ = blind spot in the prior time-card-calculator brief (no data was collected here).

## Contents

1. [Pillar 1 — SERP & discoverability ✦](#pillar-1--serp--discoverability-)
2. [Pillar 2 — Domain & link authority ✦](#pillar-2--domain--link-authority-)
3. [Pillar 3 — Traffic & demand capture ✦](#pillar-3--traffic--demand-capture-)
4. [Pillar 4 — On-page SEO & content depth](#pillar-4--on-page-seo--content-depth)
5. [Pillar 4b (sub-pillar of 4) — Structured data](#pillar-4b-sub-pillar-of-4--structured-data)
6. [Pillar 5 — Product/feature completeness](#pillar-5--productfeature-completeness)
7. [Pillar 6 — UI/UX quality ✦](#pillar-6--uiux-quality-)
8. [Pillar 7 — Performance / Core Web Vitals ✦](#pillar-7--performance--core-web-vitals-)
9. [Pillar 8 — Accessibility ✦](#pillar-8--accessibility-)
10. [Pillar 9 — Monetization / ad experience](#pillar-9--monetization--ad-experience)
11. [Pillar 10 — Mobile experience ✦](#pillar-10--mobile-experience-)
12. [Pillar 11 — Voice-of-customer pain points ✦](#pillar-11--voice-of-customer-pain-points-)

---

## Pillar 1 — SERP & discoverability ✦

**Script fields fed:** `serp_rank`, `ai_overview_cited`, `serp_features_owned`

| Measured field | How to measure (free-first) | Evidence tier |
|---|---|---|
| `serp_rank` (int or null) | chrome-devtools → navigate to `google.com/search?q=<head+term>` → DOM scrape or screenshot + count position; null if not in top 10 | real-measured |
| `ai_overview_cited` (bool) | Same SERP page: check for AI Overview box; is competitor URL cited inside it? | real-measured |
| `serp_features_owned` (int) | Count of SERP features owned: featured snippet, PAA mention, calculator onebox, image pack, video pack, site-links | real-measured |

Additional fields captured (not in strength formula but in the brief): cluster-term ranks, screenshot of live SERP,
PAA box questions present.

**Measurement note:** Run the SERP capture fresh (never reuse cached results). Record `date_accessed`.
SerpApi optional as a paid escape hatch if manual capture is rate-limited.

---

## Pillar 2 — Domain & link authority ✦

**Script fields fed:** `dr`, `referring_domains`

| Measured field | How to measure (free-first) | Evidence tier |
|---|---|---|
| `dr` (0–100) | OpenPageRank free key → `domainRank` field; cross-check Ahrefs Website Authority Checker (free, manual) | triangulated |
| `referring_domains` (int) | OpenPageRank `externalBacklinks` proxy OR Ahrefs free checker "Referring domains" number | triangulated |

**Note:** OpenPageRank DR understates real Ahrefs DR (OPR proxy). Mark source explicitly.
Never assert "DR ≈ X" without a cited source URL + date — that is the exact failure mode from the prior brief.

---

## Pillar 3 — Traffic & demand capture ✦

**Script fields fed:** (not a direct strength input field, but informs `demand` in `gap_opportunity`)

| Measured field | How to measure (free-first) | Evidence tier |
|---|---|---|
| Est. monthly organic visits to ranking page | Similarweb free (site overview → top pages); Ahrefs free Keyword Explorer traffic column | triangulated |
| Keyword footprint (count) | Ahrefs free "Top keywords" count | triangulated |
| Share of cluster traffic | Compare across competitors in the triage matrix | triangulated |

Capture at measurement time; Similarweb free has a 3-month lag — note in ledger.

---

## Pillar 4 — On-page SEO & content depth

**Script fields fed:** `word_count`, `heading_count`, `paa_coverage`

| Measured field | How to measure (free-first) | Evidence tier |
|---|---|---|
| `word_count` (int) | Fetch DOM → strip nav/footer/ads → count words in `<main>` or largest text block | real-measured |
| `heading_count` (int) | Count H1+H2+H3 elements in DOM | real-measured |
| `paa_coverage` (0.0–1.0) | Collect PAA questions for head term from live SERP (Pillar 1 capture); count how many the competitor's page answers; divide by total PAA count | real-measured |

Additional fields captured for the brief (not in strength formula):
- H1 / title / meta-description text
- Internal link count
- Page freshness / last-modified date
- i18n / hreflang presence

---

## Pillar 4b (sub-pillar of 4) — Structured data

**Script fields fed:** `schema_types` (list of JSON-LD type strings)

| Measured field | How to measure (free-first) | Evidence tier |
|---|---|---|
| `schema_types` (list) | `python3 scripts/parse_jsonld.py --url <competitor-url>` — fetches page, extracts all `@type` values from JSON-LD blocks, validates against schema.org | real-measured |

**IRON LAW:** Schema presence is NOT `reasoned` from "the site looks technical". Run `parse_jsonld.py` and paste
its output. `schema_types=[]` is a valid real-measured result (it means no schema found). Never mark schema as
`UNVERIFIED` and then use it as a committed exploit.

Target types to check: `WebApplication`, `SoftwareApplication`, `FAQPage`, `HowTo`, `BreadcrumbList`, `SiteNavigationElement`.

**Rich-result freshness (IRON):** schema PRESENCE is measured here; rich-result VALUE is time-boxed.
Before any schema gap becomes an exploit, verify each type against Google's CURRENT supported
structured-data list (source ≤60 days old). FAQ rich results were removed entirely in May 2026 and
HowTo in Sept 2023 — competitor absence of these is parity data or AI-answer machine-readability at
most, never a SERP rich-result exploit. Every schema exploit must state which it targets:
(a) a currently-supported rich result, or (b) machine-readability/AI-answer parity (allowed, lower
weight). RED baseline: the 2026-06-09 invoice brief scored a FAQPage/HowTo "SERP rich-result
eligibility" exploit (gap_opp 81) a month after FAQ rich results died.

---

## Pillar 5 — Product/feature completeness

**Script fields fed:** `feature_coverage` (0.0–1.0)

| Measured field | How to measure (free-first) | Evidence tier |
|---|---|---|
| `feature_coverage` | Build a canonical feature checklist for the tool type; use the tool live; check/uncheck each item; divide covered by total | real-measured |

Feature checklist items for timesheet/time-card type tools (adapt per tool):
- OT > 8 hr/day, > 40 hr/week, CA 7th-day rule
- Break/meal deduction
- Rounding (quarter-hour, etc.)
- Timezone support
- Persistence (URL params / localStorage)
- Export (CSV / PDF / print)
- Share/permalink
- What is gated behind email capture or paywall

Record gated features separately — they affect the competitive wedge.

---

## Pillar 6 — UI/UX quality ✦

**Script fields fed:** `clicks_to_result`, `trust_signals`

| Measured field | How to measure (free-first) | Evidence tier |
|---|---|---|
| `clicks_to_result` (int ≥ 1) | Open competitor URL; count clicks from landing to seeing a result; default state counts as 0 pre-inputs | real-measured |
| `trust_signals` (int) | Count distinct trust elements present: about page, author/method attribution, contact page, privacy policy, external review/award, HTTPS lock visible | real-measured |
| `interactions_to_result` (int) | Count EVERY keystroke + tap/click + select needed to complete the canonical job once (e.g. enter one day's times; fill one invoice line); record desktop AND mobile separately | real-measured |
| `input_modality_map` (per core field) | For each core input field record the modality: typed-free-text / native picker / dropdown / preset chips / slider / auto-default. Structured data (times, dates, currency, rates) collected via free-text TYPING is a friction signal — users prefer pickers/defaults/accelerators over typing | real-measured |

**IRON LAW (same shape as CWV):** "their UX is clunky" without an `interactions_to_result` count and
an `input_modality_map` is an opinion. Count it or cut it. The lowest measured
`interactions_to_result` across competitors becomes the ergonomics baseline our build must beat
(feeds `prd_seed.input_ergonomics`).

Additional captures for the brief:
- Desktop screenshot (chrome-devtools `preview_screenshot` or equivalent)
- Mobile screenshot (after `resize_window` or `emulate` mobile viewport)
- Input friction notes: default values, placeholder helpfulness, error messages, copy-down/duplicate-row accelerators, keyboard shortcuts
- Layout quality notes

---

## Pillar 7 — Performance / Core Web Vitals ✦

**Script fields fed:** `lcp_ms`, `cls`, `inp_ms`

| Measured field | How to measure (free-first) | Evidence tier |
|---|---|---|
| `lcp_ms` (int, milliseconds) | `chrome-devtools lighthouse_audit` on mobile AND desktop; use mobile value for the script (more conservative) | real-measured |
| `cls` (float) | Same Lighthouse run | real-measured |
| `inp_ms` (int, milliseconds) | Same Lighthouse run (INP; fall back to TBT proxy if INP unavailable) | real-measured |

Additional captures for the brief: TBT, perf score, page weight (KB), request count, desktop CWV values.

**IRON LAW:** "Competitor X is fast/slow" is illegal without a measured `lcp_ms` + Lighthouse URL + date.
Never assert a CWV claim from visual impression.

---

## Pillar 8 — Accessibility ✦

**Script fields fed:** `a11y_score` (0–100)

| Measured field | How to measure (free-first) | Evidence tier |
|---|---|---|
| `a11y_score` (int 0–100) | Lighthouse `accessibility` category score from the same audit run as Pillar 7 | real-measured |

Additional captures for the brief: contrast failures, missing alt text, keyboard navigation check,
ARIA landmark coverage, tap target sizing.

**IRON LAW:** "Accessible" without a Lighthouse a11y score + date is a violation (same rule as CWV).

---

## Pillar 9 — Monetization / ad experience

**Script fields fed:** (none directly in strength formula; informs brief and PRD-SEED `monetization_notes`)

| Measured field | How to measure (free-first) | Evidence tier |
|---|---|---|
| Ad network(s) present | DOM: look for `googlesyndication`, `doubleclick`, affiliate script tags | real-measured |
| Ad count (above fold) | Count visible ad units in desktop screenshot | real-measured |
| Ad density (above fold) | Estimate % of viewport occupied by ads | real-measured |
| CLS from ads | Inspect from Lighthouse / manual observation | real-measured |
| Affiliate / premium offers | Use tool; observe any upsell, email-gate, paywall ladder | real-measured |

---

## Pillar 10 — Mobile experience ✦

**Script fields fed:** Uses same `lcp_ms`, `cls`, `inp_ms`, `a11y_score` (Lighthouse mobile run)

| Measured field | How to measure (free-first) | Evidence tier |
|---|---|---|
| Mobile render quality | chrome-devtools `emulate` mobile viewport + screenshot | real-measured |
| Mobile CWV | Lighthouse run with mobile preset (already captured in Pillar 7) | real-measured |
| Mobile SERP rank | Separate SERP capture with mobile user-agent if ranks differ | real-measured |
| Responsive correctness | Visual inspection of mobile screenshot: overflow, font size, tap targets | real-measured |

---

## Pillar 11 — Voice-of-customer pain points ✦

**Script fields fed:** (none in the strength formula — feeds the brief, gap candidates, and
`prd_seed.pain_points`; same pattern as Pillars 3 and 9)

| Measured field | How to measure (free-first) | Evidence tier |
|---|---|---|
| `pain_points[]` ({quote, url, date_accessed, source_type, frequency_signal}) | Mine Reddit/HN/forums (`site:reddit.com <tool type> annoying OR hate OR tedious OR "wish it"`), 1–3★ app-store / Chrome-store reviews of the SaaS rivals, PAA questions phrased as complaints. Copy quotes VERBATIM with URL + date_accessed into the ledger | real-measured (the quote is real; the generalization is `triangulated` only at ≥3 independent sources) |
| `input_ergonomics_complaints` (subset) | Complaints about HOW data is entered — typing times/dates on mobile keyboards, no defaults, re-entering repeated values, no copy-down, no templates. These map directly to Pillar 6 `interactions_to_result` / `input_modality_map` baselines | real-measured |
| `unmet_jtbd[]` | Jobs users describe that NO audited competitor serves (from the same mining) | triangulated |

**IRON LAW (same shape as CWV/schema):** "users hate X" without a verbatim quote + URL +
date_accessed is an opinion — it may enter the brief only as `reasoned`, never as an exploit. A pain
point becomes a committed exploit ONLY when (a) ≥3 independent sources express it AND (b) the
Pillar 5/6 audit confirms the top competitors measurably fail it.

**Why this pillar exists (RED baseline):** the 2026-06 time-card brief collected zero
input-ergonomics or voice-of-customer data; the decisive v1 requirement (R7 — low-friction time
entry: native picker + accelerators, ≤15 interactions/week) was added only by a human brainstorm
AFTER the PRD was stamped FINAL. This pillar makes that catch systematic instead of lucky.
