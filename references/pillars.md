# Measurement pillars — the 10 pillars

Every analyzed competitor is scored on all 10 pillars. Fields listed here feed the scripts directly;
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

Target types to check: `WebApplication`, `FAQPage`, `HowTo`, `BreadcrumbList`, `SiteNavigationElement`.

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

Additional captures for the brief:
- Desktop screenshot (chrome-devtools `preview_screenshot` or equivalent)
- Mobile screenshot (after `resize_window` or `emulate` mobile viewport)
- Input friction notes: default values, placeholder helpfulness, error messages
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
