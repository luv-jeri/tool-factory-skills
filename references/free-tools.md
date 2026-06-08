# Free Tools Reference

All-$0 tooling for picking the next AdSense micro-tool. Three operating modes
(`--data=manual`, `--data=hybrid`, `--data=auto`) trade automation against
human eyeballing. Everything below is free; the modes differ only in how much
is scripted vs. read by a person.

## Table of Contents

1. [Per-Mode FREE Tool Stack](#1-per-mode-free-tool-stack)
   - [`--data=manual`](#data-manual--zero-setup-no-api-tokens)
   - [`--data=hybrid`](#data-hybrid--automated-discovery--browser-cross-check)
   - [`--data=auto`](#data-auto--fully-scriptable-no-human-in-loop)
2. [Keyword Volume](#2-keyword-volume)
   - [Tool table](#21-tool-table)
   - [The AUTO/HYBRID procedure](#22-the-autohybrid-procedure)
   - [MANUAL: Ahrefs Free Keyword Generator + throttle workaround](#23-manual-ahrefs-free-keyword-generator--throttle-workaround)
3. [The Qualifier-Kills-Volume Test](#3-the-qualifier-kills-volume-test)
4. [SERP / Winnability](#4-serp--winnability)
   - [Tool table](#41-tool-table)
   - [Detecting the DR-80 wall (OpenPageRank batch)](#42-detecting-the-dr-80-wall-openpagerank-batch)
   - [The thin-site-proof check](#43-the-thin-site-proof-check)
5. [Live AI-Overview Check](#5-live-ai-overview-check)

---

## 1. Per-Mode FREE Tool Stack

### `--data=manual` — zero setup, no API tokens

| Tool | Role |
|------|------|
| **Ahrefs Free Keyword Generator** | Volume RANGE (`>10K` vs `100-1K` gap = qualifier test in one screen) |
| **Keyword Surfer** (extension) | Inline volume/CPC on the live Google SERP |
| **Google Trends** (web UI) | Broad-vs-qualified head-to-head |
| **Glimpse** free (10/mo) | Absolute-volume read on the 1–2 finalists |
| **Ahrefs free Website Authority Checker** | True DR, 1 domain at a time (calibration) |
| **Mangools SERPChecker** free (~5/day) | Per-result authority on the single best candidate |
| **Manual incognito Google** (`&gl=us&hl=en`) | Eyeball page-1 occupants + whether an AI Overview fires |

### `--data=hybrid` — automated discovery + browser cross-check

Keep AUTO's automated core, add human/browser cross-checks.

| Tool | Role |
|------|------|
| **Google Autocomplete** endpoint | Automated variant fan-out (same as AUTO) |
| **Google Ads API — GenerateKeywordIdeas** | Automated volume buckets (same as AUTO) |
| **OpenPageRank API** | Automated DR-wall gate (same as AUTO) |
| **Google Trends** web UI | Browser head-to-head: broad vs qualified on one normalized 0–100 chart |
| **Keyword Surfer** overlay | Inline CPC + volume + incumbent word count on the live SERP |
| **Manual / SerpApi AI-Overview read** | Confirm whether an AIO fires |
| **G-TAB** anchor bank (optional) | One pseudo-absolute volume number without an API token |

### `--data=auto` — fully scriptable, no human in loop

| # | Tool | Role |
|---|------|------|
| 1 | **Google Autocomplete** endpoint<br>`suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=US&q=SEED` | Free, no key, no account. Fans the candidate query into broad + qualified variants and the full cluster. ~10 lines; add 0.5–1s jitter. |
| 2 | **Google Ads API — GenerateKeywordIdeas** | Free no-spend Expert-Mode account + dev token. Real 12-month `avg_monthly_searches` buckets for every variant — the qualifier-kills-volume A/B in one request. |
| 3 | **Bing Webmaster GetKeywordStats API** | Free key. EXACT integer volumes to break ties inside a Google bucket. |
| 4 | **OpenPageRank API** | Free key, ~4.3M domains/day, 100 domains/request. Automatable DR proxy for the page-1 authority distribution (the DR-wall gate). |
| 5 | **SerpApi free tier** (~100–250/mo — RE-VERIFY) | Structured page-1 organic domains + `ai_overview` block. Reserve strictly for the finalist shortlist. |

> Treat ALL free volume as relative/ordinal (bucket thresholds), never precision.

---

## 2. Keyword Volume

### 2.1 Tool table

| Tool | What it gives | Free tier | Automatable | Role |
|------|---------------|-----------|-------------|------|
| **Google Ads API — GenerateKeywordIdeas** | Real `avg_monthly_searches` (12-mo) + per-month array, competition, bid range, idea fan-out | Free; ~15k ops/day, ~1k idea-reports/day (RE-VERIFY); no spend (Expert Mode) + dev token (~1-day approval) | yes-api | **PRIMARY volume source.** Relative ranking + thresholds |
| **Bing Webmaster GetKeywordStats** | EXACT integer monthly volume, country/device, related + question keywords | 100% free, free key, no spend gate | yes-api | **Tie-breaker** in one Google bucket. Scale ~3–10x for Google proxy |
| **Google Autocomplete** (`complete/search`) | Variant/qualifier fan-out (A-Z, questions, modifiers). No volume | Free, no key, no account | yes-api | **Cluster engine** for all modes |
| **Ahrefs Free Keyword Generator** | 100 ideas + 50 questions, KD, volume RANGE | Free, no account; ranges only | partial (captcha) | MANUAL gut-check |
| **Keyword Surfer** (extension) | Inline SERP volume + ideas sidebar, 70 countries | Free, unlimited | manual-only | MANUAL companion |
| **Google Keyword Planner** (UI) | Same as Ads API in a dashboard | Free, no-campaign account | manual-only | MANUAL no-code fallback |
| **Google Trends / pytrends / official API** | RELATIVE interest 0–100, seasonality, head-to-head | UI free; official API waitlisted; pytrends DEAD in 2026 | partial | **Trend direction + head-to-head only**, not volume |
| **G-TAB** (EPFL OSS) | Calibrates Trends into pseudo-absolute scale via anchor bank | Free OSS | partial | Advanced escape hatch / EU-vs-US |
| **SerpApi** | SERP JSON + autocomplete + PAA + AI Overview | ~250/mo (RE-VERIFY), no card | yes-api | DECISIVE gate (not volume) |
| **Keywords Everywhere** | Inline volume/CPC, GKP-sourced, API key | Volume needs credits (~$84/yr=100k) | yes-api | Cheap-paid upgrade |
| AnswerThePublic / Keywordtool.io / Ubersuggest / Wordtracker | Variant fan-outs; 3/day caps | Free, tiny quotas | manual-only | **SKIP** — all are autocomplete front-ends; hit the endpoint directly |

### 2.2 The AUTO/HYBRID procedure

1. **Fan out** the candidate via Google Autocomplete (seed + A-Z + question forms + "free/best/calculator/generator").
2. **Score volume**: send the exact term + harvested variants to Google Ads API GenerateKeywordIdeas in ONE request → read `avg_monthly_searches` buckets.
3. **Break ties** inside a Google bucket with Bing GetKeywordStats exact integers.
4. **Confirm trend**: one Google Trends head-to-head of broad vs qualified.
5. Treat ALL free volume as **relative/ordinal** (bucket thresholds: >10k vs <100), never precision.

> **Accuracy reality:** No-spend GKP data is bucketed (1K–10K, ~10x gaps) and groups near-synonyms → it OVER-estimates. Ahrefs ground-truth study (72k keywords vs GSC): GKP "roughly accurate" only ~45% of the time, over-estimated 91% (54% dramatically); Ahrefs' own ~60%. (RE-VERIFY — vendor study, ~5 yrs old.)

### 2.3 MANUAL: Ahrefs Free Keyword Generator + throttle workaround

Use when there are no API tokens. The free Keyword Generator returns 100 ideas
+ 50 questions with KD and a **volume RANGE** (not an integer). The range alone
runs the qualifier test: a broad term showing `>10K` next to a qualified
sibling showing `100-1K` is the gap you are looking for in one screen.

Operational steps:

1. Open the free Keyword Generator, set country (US, then UK/EU as needed).
2. Enter the broad commercial term first; record its volume range and the KD.
3. Read the ideas/questions list for qualified siblings and their ranges.
4. **Cache/throttle workaround — reload fresh before each new keyword.** The
   free tool caches the previous query and soft-throttles rapid repeat lookups.
   Before each NEW keyword, do a hard reload of the page (fresh load, not the
   in-page search box) so you get uncached data and avoid the rate cap. One
   keyword per fresh page load.
5. Cross-check the 1–2 survivors with Keyword Surfer inline on Google and a
   Google Trends comparison; use Glimpse (10/mo) only on the finalists for an
   absolute-volume read.

---

## 3. The Qualifier-Kills-Volume Test

**Rule: measure the BROAD commercial term, not the persona-qualified one.**

A qualifier (audience, niche, persona) can drop a term ~10–100x in volume. The
demand lives in the broad term; the qualifier is positioning, not a market.

Procedure:

1. Via Autocomplete, discover that a broad high-volume term (e.g. `invoice
   generator`) is the parent of a niche persona term (e.g. `freelance rate
   calculator`).
2. Fire BOTH as seeds to Google Ads API GenerateKeywordIdeas and **compare
   buckets** — or in MANUAL mode, compare their volume RANGES side by side in
   the Ahrefs Free Keyword Generator (`>10K` vs `100-1K`).
3. **Confirm visually in Google Trends:** the broad term pins the chart at 100;
   the qualified term often sits flat-near-zero.
4. Sub-measurable on the qualified term = **disqualify**. Build for the broad
   commercial demand, not the persona slice.

---

## 4. SERP / Winnability

### 4.1 Tool table

| Tool | What it gives | Free tier | Automatable | Role |
|------|---------------|-----------|-------------|------|
| **Manual Google SERP** (incognito, `&gl=&hl=`) | WHO ranks page 1, page TYPE, AIO/widget presence | Unlimited free | partial (browser only) | **DECISIVE ground-truth gate** |
| **OpenPageRank API** | DR proxy 0–10 (Common Crawl) for every page-1 domain | Free forever, key, ~4.3M domains/day, 100/request | yes-api | **BACKBONE of automatable winnability gate** |
| **Ahrefs free Website Authority Checker** | True Ahrefs DR 0–100 | Free, 1 domain/form, throttles | partial | **Calibration** of OpenPageRank→DR mapping |
| **Ahrefs free KD Checker** | KD 0–100 + backlinks-to-rank | Free, soft daily cap | partial | One difficulty input, never the gate |
| **Keyword Surfer** | Inline volume/CPC + per-result word count/traffic | Free, unlimited | manual-only | Incumbent content-depth read |
| **Detailed SEO Extension** | On-page title/H1-H6/schema/word-count/indexability of any result | Free, no cap | manual-only | Confirm "thin page-1" |
| **MozBar** | DA/PA overlay on SERP | Free w/ account, 10 Link Explorer q/mo | manual-only | Manual DA-wall glance |
| **Moz Link Explorer** | DA/PA + page-level backlinks (ghost-ranking) | 10 q/mo (web) / ~25 (API) | partial | Page-level ghost-ranking on best candidate |
| **SerpApi** | SERP JSON: organic domains + `ai_overview` | ~100/mo (RE-VERIFY) | yes-api | Automatable SERP+AIO on finalists |
| **DuckDuckGo (DDGS) / Bing HTML** | De-personalized SERP, plain-HTTP, unlimited | Free OSS | yes-browser | **Free unlimited first-pass triage** |
| **SEMScoop / SEO Review Tools / Mangools** | KD + per-result SERP authority | 2–5/day free | partial | Manual triangulation on finalists |
| **Common Crawl Web Graph** | Raw host link graph (upstream of OpenPageRank) | Free on AWS, heavy | yes-api | Skip live; fallback only |

> Google cannot be reliably batch-scraped for free in 2026 (CAPTCHA defeats headless Playwright without residential proxies). Pattern: triage long lists on DuckDuckGo/Bing HTML → spend scarce SerpApi quota or one real-browser capture only on finalists.

### 4.2 Detecting the DR-80 wall (OpenPageRank batch)

The DR-80 wall is an instant-fail gate: **8+ of the top 10 organic results are
domains with OpenPageRank ≥ ~6/10 (≈ true DR 60+) AND zero forum/UGC or thin
independent sites appear.** No crack to enter → score 0.

How to detect it:

1. Extract the ordered page-1 domains (SerpApi, or parse a real-browser capture).
2. Batch-POST all domains to OpenPageRank in ONE call (100 domains/request).
3. Threshold on count ≥ ~6/10.
4. **Calibrate** the OpenPageRank→Ahrefs-DR mapping with 2–3 spot-checks via the
   Ahrefs free Website Authority Checker (rough guide: 6/10≈DR60, 7–8/10≈DR80 —
   NOT published, calibrate it).
5. OpenPageRank lags months and returns 0/null for brand-new domains → treat
   low/zero as "unknown, verify" not "weak."

### 4.3 The thin-site-proof check

The single strongest POSITIVE winnability signal (Winnability = 5):

**At least one forum/UGC result OR a thin/low-DR (<3/10 OpenPageRank ≈ DR<30)
independent site already ranks page 1 for the long-tail query.**

This proves Google will rank a small site for the term — so a better,
purpose-built tool can take the slot. To confirm a page is genuinely thin (not
just a low-DR brand), check it with the Detailed SEO Extension / Keyword Surfer
word count: shallow content, no schema, stale = real thin-site proof.

Winnability 1–5 (after passing the hard gate):

- **5** — thin-site proof present (above).
- **4** — mixed page 1: several results under ~DR40, incumbents generic/thin.
- **3** — page 1 mid-authority (DR 40–60), no obvious weak page, no DR-80 wall.
- **2** — mostly DR 60–80 with only one weak slot.
- **1** — passed the gate but page 1 is uniformly strong purpose-built tools.

---

## 5. Live AI-Overview Check

AI Overviews are JS-rendered and lazy-loaded — a raw HTML fetch MISSES them. You
must render with a real/headless browser.

Method:

1. **Run the query in incognito** with locale pinned: `&gl=us&hl=en`.
2. Observe whether an **AI Overview block renders now**, and whether it fully
   answers the user's need on its own.
3. **Check 2–3 times** — AIO presence is volatile and varies by session, so a
   single render is not conclusive.
4. AUTO/HYBRID layer: read SerpApi's `ai_overview` field on finalists only
   (lazy ones surface via `page_token`). Do NOT hard-code DOM selectors
   (`.Kevs9`, `div.Y3BBE`) — Google changes them frequently; verify live.
5. **AI-Overview kill (instant fail):** the SERP is dominated by an AIO that
   fully answers the need AND there is no persistent tool widget worth clicking
   through for (kills the AdSense click). A stateful interactive tool
   (calculator/converter/generator) that the AIO cannot reproduce inline
   survives this gate.

---

## 6. Driving manual / hybrid mode with the browser MCP (agent-executable)

Manual and hybrid modes are agent-runnable with a connected browser MCP (Claude-in-Chrome, or Control-Chrome) — no scraper, no API key. **Don't hard-code CSS selectors** (Google rotates them); read rendered text via `get_page_text` / `read_page`.

Per candidate, the tool sequence:

1. **Who ranks page 1 + AI-Overview** — `navigate` to `https://www.google.com/search?q=<head+term>&gl=us&hl=en&pws=0`, then `get_page_text`. Record the top-10 organic domains; note whether an "AI Overview" / "AI Mode" block renders and whether it fully answers the need on its own. Repeat 2–3× (AIO presence is volatile). → fills `who_ranks_p1`, `onebox`, `aio_fire_pct`, `native_feature`.
2. **Domain authority (the DR-wall gate)** — for the top domains, `navigate` to `https://ahrefs.com/website-authority-checker/` and read DR one domain at a time (or OpenPageRank in hybrid). 8+ of 10 at DR ≥ 60 with no thin/UGC slot = wall → Winnability 1; a thin/low-DR site present → `thin_site_proof=true`. → fills `kd_head`, `weak_count`, `thin_site_proof`.
3. **Volume band + KD** — `navigate` to `https://ahrefs.com/keyword-generator/?country=us`, enter the term, read the band (`>10K` / `1K-10K` / `100-1K` / `<100`) + KD + cluster size. **Hard-`navigate` to a fresh URL before each new keyword** (don't reuse the in-page search box — it returns cached rows). → fills `head_bucket`, `cluster_kw_count`, `distinct_variants`.
4. **Qualifier test** — run step 3 on BOTH the broad commercial term and the persona-flavored term; the gap (e.g. `>10K` vs `100-1K`) is the disqualifier signal.

Feed every captured value into the `score.py` contract fields, then run `python3 scripts/score.py`. If the browser MCP isn't connected, ask the user to enable it rather than guessing the data.

---

Stale quotas/figures live in live-recheck.md — re-verify before relying on them.
