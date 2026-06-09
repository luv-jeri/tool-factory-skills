# Audit procedure — pipeline stages + per-competitor recipe

**Rule:** Do not advance to the next stage until the current stage's PASS condition is met.
A stage that cannot PASS must halt with a labelled block explaining what is missing.

## Contents

- [Part A — Pipeline stages 0–8](#part-a--pipeline-stages-08)
- [Part B — Per-competitor browser-driven recipe](#part-b--per-competitor-browser-driven-recipe)

---

## Part A — Pipeline stages 0–8

---

### Stage 0 — Intake

**Purpose:** Establish the target before touching any competitor data.

**Actions:**
1. Ingest the product gist or PRD; extract the primary job-to-be-done (JTBD) in one sentence.
2. Derive the keyword cluster: head term + top variant phrasings.
3. Collect seed competitors (from user input, from `pick-next-tool` output, or both).
4. If `builds/<tool-slug>/research-raw.json` exists from a prior `pick-next-tool` run, ingest it — reuse any `volume_buckets` and `autocomplete_fanout` data rather than re-fetching.

**Data:** product gist / PRD, `research-raw.json` (optional), user-provided seeds.

**PASS:** JTBD is one clear sentence; head term is identified; keyword cluster has ≥3 phrasings.

**Out:** `{ jtbd, head_term, cluster_phrasings[], seed_competitors[], reused_pick_next_tool_data }`.

---

### Stage 1 — Discover

**Purpose:** Build a ground-truth competitor list from the live SERP — not from memory.

**Actions:**
1. Capture the live page-1 SERP for the head term (chrome-devtools → Google; screenshot + DOM).
2. Capture SERP for top 2–3 cluster variant phrasings.
3. Harvest all organic URLs from positions 1–10 per SERP. Extract root domain.
4. Merge harvested domains with seed competitors; deduplicate.
5. Classify each: `direct_tool` / `aggregator` / `saas_paywall` / `content_blog` / `off_topic`.

**Data:** Live SERP screenshots + DOM, harvested URL list.

**PASS (Gate A):** ≥3 `direct_tool` competitors found. If fewer, **REFUSE** — do not continue with a fabricated landscape.

**Out:** Classified, deduplicated competitor list with SERP position (or `null` if from seed only).

---

### Stage 2 — Triage

**Purpose:** Select the K ≈ 8–10 competitors that matter most for this cluster.

**Actions:**
1. Rank candidates by actual SERP position across the cluster (lower rank = higher priority).
2. Promote any seed competitor not found in SERP if it is a known direct competitor.
3. Drop off-topic / aggregator entries with a one-line reason.
4. Confirm final list of K competitors with the user (or proceed if running autonomously).

**Data:** Classified list from Stage 1.

**PASS:** Final list of K ≤ 10 direct competitors confirmed; each dropped candidate has a stated reason.

**Out:** `triaged_competitors[]` — the exact set the fan-out will audit.

---

### Stage 3 — Empirical audit fan-out

**Purpose:** Collect all 10-pillar measured fields for every competitor via live browser-driven audits.

**Actions:**
1. Execute `scripts/audit-workflow.js` with the triaged competitor list, keyword cluster, and pillar field schema as args.
2. Per competitor the workflow runs: Researcher agent (collects all 10-pillar fields) + Adversarial skeptic agent (re-verifies the 3 most decision-critical claims).
3. Receive schema-validated JSON per competitor with an evidence tier per field.
4. Any field that cannot be measured returns `UNVERIFIED` — never silently 0.

**Data:** Live SERP, Lighthouse audits, screenshots, `parse_jsonld.py` output, OpenPageRank, Similarweb.

**PASS (Gate B):** For each competitor, all REQUIRED_FIELDS from `competitor_strength.py` are present and typed correctly (or explicitly `UNVERIFIED` with a reason). Zero silently-zero fields.

**Out:** `per_competitor_measured_json[]`, each field tagged with evidence tier.

---

### Stage 4 — Score

**Purpose:** Produce deterministic, reproducible competitor strength scores and gap opportunity scores.

**Actions:**
1. For each competitor: `python3 scripts/competitor_strength.py --json <competitor.json>`
2. For each detected gap: `python3 scripts/gap_opportunity.py --json <gaps.json>`
3. No manual score adjustments. Numbers come from the scripts only.

**Data:** Per-competitor measured JSON from Stage 3.

**PASS:** All competitors have a `strength` score; all gaps have an `opportunity` score and tier. No `ContractError` left unresolved.

**Out:** `scored_competitors[]`, `scored_gaps[]`.

---

### Stage 5 — Gap synthesis

**Purpose:** Build the master feature matrix and articulate the wedge.

**Actions:**
1. Construct the master feature matrix: competitors × features, using Stage 3 measured data.
2. Consolidate gaps by category: UX/SEO/perf/a11y/monetization.
3. Rank gaps by `opportunity` score (descending, from scripts).
4. Draft the wedge/positioning (≤3 sentences) based on the highest-scoring build-now gaps.
5. **Check Gate C:** if the cluster SERP is dominated by an AI Overview that fully answers the JTBD → raise existential-risk flag before claiming any opportunity.

**Data:** Scored competitors, scored gaps, master feature matrix.

**PASS:** Gap table is ranked by script output; existential-risk flag evaluated; wedge is one clear statement.

**Out:** Ranked gap table, master feature matrix, wedge draft.

---

### Stage 6 — Adversarial kill pass

**Purpose:** Eliminate false opportunities before they enter the brief.

**Actions:**
1. A separate skeptic agent challenges each build-now gap: "Does the measured data actually confirm competitors fail this, or was it assumed?"
2. Challenge the AI-Overview risk: "Is the AI Overview citing a competitor? What exactly does it answer?"
3. For any gap backed by reasoned-tier evidence: demote to `hypothesis`.
4. Re-run `gap_opportunity.py` on any gap with corrected inputs.

**Data:** Ranked gap table + all evidence ledger entries.

**PASS:** Every build-now gap is backed by real-measured or triangulated evidence. No committed exploit rests on reasoned-tier or UNVERIFIED evidence.

**Out:** Final validated gap table; any demoted gaps moved to `open_questions` in the PRD-SEED.

---

### Stage 7 — Write deliverables

**Purpose:** Produce the human-readable brief and machine-readable ledger.

**Actions:**
1. Write `builds/<tool-slug>/COMPETITIVE-BRIEF.md` (see `references/deliverables.md` for template).
2. Write `builds/<tool-slug>/research-raw.json` (source ledger — every claim with `url + date_accessed + method + evidence_tier`).
3. Optionally regenerate `report.html` (tabbed dashboard).

**Data:** All prior stage outputs.

**PASS:** Brief has all 9 required sections; every claim in the brief traces to an entry in `research-raw.json`; no UNVERIFIED claim appears as a committed exploit.

**Out:** `COMPETITIVE-BRIEF.md`, `research-raw.json`, optional `report.html`.

---

### Stage 8 — Handoff

**Purpose:** Emit the machine-readable PRD-SEED block for downstream consumption.

**Actions:**
1. Populate the `prd_seed:` YAML block (full schema in `references/deliverables.md`).
2. Append it as a fenced YAML block at the end of `COMPETITIVE-BRIEF.md`.
3. Verify all required fields are present and non-empty.

**Data:** Validated gap table, wedge, PRD-SEED fields.

**PASS:** `prd_seed:` block is valid YAML; `performance_budget` values are set to beat the best-measured competitor; `ai_overview_risk` is populated.

**Out:** Final `COMPETITIVE-BRIEF.md` with appended `prd_seed:` block.

---

## Part B — Per-competitor browser-driven recipe

Executed by the Researcher agent inside `scripts/audit-workflow.js` for each competitor in the triaged list.
Steps are in dependency order — do not reorder.

---

### Step 1 — Capture live SERP + AI Overview

**Pillar fields filled:** `serp_rank`, `ai_overview_cited`, `serp_features_owned`, PAA questions list.

1. Open `https://www.google.com/search?q=<head+term>` in a fresh browser context (chrome-devtools `navigate_page`).
2. Take a full-page screenshot (`take_screenshot`).
3. Scrape DOM for organic results: position each `<a>` in `.MjjYud` (or equivalent Google result container).
4. Record competitor's position as `serp_rank` (integer 1–10, or `null`).
5. Check for AI Overview box (`#aiOverview` or `#ai-overview` selector): if present, record `ai_overview_cited=True/False` based on whether the competitor URL appears in the sources.
6. Count SERP features owned by the competitor: featured snippet, PAA mention, calculator/widget onebox, image/video pack, site-links.
7. Harvest all PAA questions shown — used for `paa_coverage` calculation in Step 4.

---

### Step 2 — Lighthouse audit (CWV + a11y)

**Pillar fields filled:** `lcp_ms`, `cls`, `inp_ms`, `a11y_score` (Pillars 7 + 8).

1. Navigate to the competitor's tool page (not homepage unless the tool IS the homepage).
2. Run `lighthouse_audit` (chrome-devtools) — mobile preset first, then desktop.
   - Mobile: record `lcp_ms`, `cls`, `inp_ms` (or TBT proxy), `a11y_score`, perf score, page weight, request count.
   - Desktop: record same set (for the brief; script uses mobile values for conservatism).
3. Attach the raw lighthouse JSON to the ledger entry as `method: "lighthouse_audit"`.
4. **IRON LAW:** Do not assert any CWV or a11y claim without this step's output. "Seems fast" is not a measurement.

---

### Step 3 — Desktop + mobile screenshots

**Pillar fields filled:** UI/UX quality notes (Pillar 6), mobile render quality (Pillar 10).

1. Desktop screenshot: `take_screenshot` at standard 1280×800 viewport.
2. Mobile screenshot: `resize_window` or `emulate` to 375×812 (iPhone 14 viewport), then `take_screenshot`.
3. Save both screenshots with filenames `<competitor-slug>-desktop.png` / `<competitor-slug>-mobile.png` to `builds/<tool-slug>/screenshots/`.
4. Note visible trust signals (about/author/method/contact/HTTPS/review badge).

---

### Step 4 — Use the tool live

**Pillar fields filled:** `clicks_to_result`, `feature_coverage`, gated-features list (Pillar 5 + 6).

1. Open the competitor tool page fresh (not from SERP page).
2. Count clicks from landing to seeing a result — record as `clicks_to_result` (minimum 1).
3. Work through the canonical feature checklist for the tool type (see `references/pillars.md` Pillar 5).
4. Record which features are present, absent, or gated (email capture / paywall).
5. Calculate `feature_coverage = present_features / total_checklist_items`.
6. Note any ad units visible above the fold; estimate ad density.

---

### Step 5 — Parse structured data

**Pillar fields filled:** `schema_types` (Pillar 4b).

```bash
python3 scripts/parse_jsonld.py --url <competitor-url>
```

1. Run `parse_jsonld.py` — it fetches the page, extracts all JSON-LD `<script>` blocks, collects `@type` values, validates against schema.org.
2. Record the output list as `schema_types`. Empty list `[]` is a valid real-measured result.
3. Do NOT infer schema presence from page structure or meta tags — `parse_jsonld.py` output only.
4. Attach the raw output to the ledger entry as `method: "parse_jsonld"`.

---

### Step 6 — Authority + traffic data

**Pillar fields filled:** `dr`, `referring_domains` (Pillar 2), traffic estimate (Pillar 3).

1. OpenPageRank API (free key): `GET https://openpagerank.com/api/v1.0/getPageRank?domains[0]=<domain>`
   - Record `domainRank` as `dr` (triangulated; note OPR understates Ahrefs DR).
   - Record `externalBacklinks` as `referring_domains` proxy.
2. Optionally cross-check with Ahrefs Website Authority Checker (manual, free, no key required).
   If both sources agree within ±10 DR points → `evidence_tier: "triangulated"`. If they disagree >10 → flag, use lower value, note discrepancy.
3. Similarweb free: navigate to `https://www.similarweb.com/website/<domain>/` → record estimated monthly visits and top-keyword count.
4. Record all values with `url`, `date_accessed`, `method`, `evidence_tier` in `research-raw.json`.

---

### Step 7 — On-page content audit

**Purpose:** Collect the on-page SEO pillar fields (`word_count`, `heading_count`, `paa_coverage`) that fill Pillar 4 (On-page SEO & content depth). These fields are required by `competitor_strength.py` and must be real-measured.

**Tool:** chrome-devtools (`get_page_text` + DOM inspection of the competitor's ranking page).

**Pillar fields filled:** `word_count`, `heading_count`, `paa_coverage` (Pillar 4).

1. Navigate to the competitor's ranking page (the URL found at their SERP position in Step 1).
2. Call `get_page_text` (chrome-devtools) to retrieve visible page text. Strip navigation, footer, sidebar, and ad regions — count words in the main content block (`<main>`, `<article>`, or the largest contiguous text block). Record as `word_count` (int).
3. Inspect the DOM (chrome-devtools `evaluate_script` or equivalent): count all `<h1>`, `<h2>`, and `<h3>` elements present on the page. Record as `heading_count` (int).
4. Using the PAA questions list harvested in Step 1, evaluate how many of those questions are answered by content on this competitor page (a question is "answered" if the page contains a direct response in text). Divide answered count by total PAA question count; record as `paa_coverage` (float 0.0–1.0). If Step 1 found zero PAA questions, record `paa_coverage = 0.0`.
5. Attach evidence as `method: "chrome_devtools_dom"`, `evidence_tier: "real-measured"` in `research-raw.json`.

**IRON LAW:** Do not assert `word_count`, `heading_count`, or `paa_coverage` without completing this step. "The page looks content-rich" is not a measurement.
