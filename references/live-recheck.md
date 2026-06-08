# Live Re-Check List

Runtime re-verification of every stale, load-bearing figure used by the pick-next-tool skill.

## How to use this list

**All free volume is ORDINAL, not precise.** No-spend Google Ads buckets, Bing scaling factors, range-only tools (Ahrefs free), and relative Trends scores tell you *which candidate is bigger*, never *how big*. Never carry a free-tier number into a decision as if it were exact. Bucket thresholds (`>10k` vs `<100`) are the unit of truth; anything finer is noise.

**Re-check anything load-bearing before declaring a winner.** Every figure below was captured from secondary sources, vendor blogs, or assistant approximation at brief-compile time (2026-06-08) and is the kind of number most likely to have drifted. If a figure gates a decision — a quota that determines whether a tool is usable, an accuracy claim that sets how much to trust volume, an AIO stat that pushes a candidate past the AI-Resistance gate, or an ad-network threshold that sets the Revenue score — re-verify it live FIRST. A stale quota or threshold can flip a pass/fail. When a re-check disagrees with the value here, trust the live value and note the drift.

Each item below gives: **Claimed value** / **Why it drifts** / **How to re-verify**.

---

## A. API Quotas & Limits

### Google Ads API free quota
- **Claimed:** ~1,000 keyword-idea reports/day + ~15,000 ops/day (standard access).
- **Why it drifts:** Third-party blog figures, never confirmed by Google. No-spend / test-token accounts are often throttled harder than standard, and Google revises API tiers regularly.
- **Re-verify:** Google Ads API docs — rate limits & quotas page (developers.google.com/google-ads/api/docs/best-practices/quotas). Confirm the 2026 per-day cap AND whether no-spend / Expert-Mode / test-developer-token accounts get a reduced quota.

### Bing Webmaster GetKeywordStats rate limit
- **Claimed:** No confirmed 2026 cap; one source implies low hundreds/day.
- **Why it drifts:** Undocumented limit; Microsoft has changed Webmaster API exposure before, and the keyword endpoint may be partially gated.
- **Re-verify:** Bing Webmaster Tools API docs (learn.microsoft.com/bingwebmaster). Confirm the per-day quota and that GetKeywordStats is fully exposed via a plain free API key (not OAuth-only / not deprecated).

### SerpApi free tier  ← HIGH PRIORITY (sources directly conflict)
- **Claimed:** 100 vs 250 searches/month — sources contradict each other. **Treat as 100/mo until re-checked.**
- **Why it drifts:** Pricing-page figure; SerpApi changes free-tier allowances and this is the single scarcest budget the skill spends (reserved for finalists only).
- **Re-verify:** serpapi.com/pricing. Read the exact current free monthly search count before allocating it across finalists.

### OpenPageRank limits
- **Claimed:** 100 domains/request, ~10k calls/hr, ~4.3M domains/day.
- **Why it drifts:** DomCop adjusts free-tier throughput; batch size and hourly cap set how the DR-wall gate is chunked.
- **Re-verify:** DomCop OpenPageRank API docs (domcop.com/openpagerank/documentation). Confirm per-request domain cap and daily/hourly ceilings.

### Apify free credit
- **Claimed:** ~$5/mo free credit ≈ 4,300 autocomplete queries.
- **Why it drifts:** Apify revises free-plan credit allotment and per-actor pricing, changing the effective query count.
- **Re-verify:** apify.com/pricing. Confirm monthly free credit and recompute queries against the current actor run cost.

### DataForSEO free trial / minimum top-up
- **Claimed:** $1 trial credit (confirmed), then $50 minimum top-up.
- **Why it drifts:** Trial credit and minimum deposit are promo-driven and change; the $50 floor is the reason this is a SKIP for $0 selection.
- **Re-verify:** dataforseo.com/pricing. Confirm trial credit and the minimum deposit before treating it as cheap-paid-only.

### Ubersuggest free limits
- **Claimed:** 3 searches/day (web app) vs 40/day (extension).
- **Why it drifts:** Neil Patel adjusts free caps frequently to push subscriptions.
- **Re-verify:** Run the web app and extension while logged out; observe the daily cap message. Prefer the extension per the brief.

### Ahrefs free KD / Authority checker throttle
- **Claimed:** "a few per day" daily throttle.
- **Why it drifts:** Community-reported, never official; Ahrefs tunes free-tool throttles silently.
- **Re-verify:** Use ahrefs.com/keyword-difficulty and ahrefs.com/website-authority-checker until throttled; note the cap. Captcha may gate automation.

### Moz free tiers
- **Claimed:** 10 Link Explorer queries/mo (web) vs ~25 (API).
- **Why it drifts:** Moz has repeatedly changed free Link Explorer allowances.
- **Re-verify:** moz.com/link-explorer and Moz API free-tier docs. Confirm current monthly query counts for web vs API.

### Mangools post-trial free tier
- **Claimed:** ~5 lookups per 24h after trial.
- **Why it drifts:** Trial-to-free conversion behavior changes; may become trial-only with no standing free tier.
- **Re-verify:** mangools.com/pricing and observe SERPChecker behavior at signup after the trial lapses.

### Glimpse free
- **Claimed:** 10 lookups/mo free.
- **Why it drifts:** Glimpse adjusts free allowance; this caps absolute-volume reads on the 1–2 finalists.
- **Re-verify:** meetglimpse.com/pricing (or the extension's account page). Confirm the monthly free count.

---

## B. Accuracy / Methodology Claims

### GKP volume accuracy
- **Claimed:** GKP "roughly accurate" ~45% of the time; over-estimates 91% (54% dramatically); Ahrefs' own ~60%.
- **Why it drifts:** Ahrefs 2021 study, vendor-published, ~5 years old, measured against GSC on 72k keywords. AIO-era query behavior and GKP bucketing may have shifted accuracy.
- **Re-verify:** Search for a 2026 GKP-vs-GSC accuracy study (Ahrefs blog or independent). Absent a new one, keep treating no-spend GKP as bucketed and over-estimating — this is *why* free volume is ordinal.

### Bing volume → Google scaling
- **Claimed:** Bing ≈ 1/3 to 1/10 of Google volume.
- **Why it drifts:** Market-share rule of thumb, not measured for utility queries specifically; the ratio varies by niche and has moved with AI-search adoption.
- **Re-verify:** Calibrate live — pick 2–3 known-volume terms, pull both Bing GetKeywordStats and a Google bucket, derive the actual multiplier for *this* niche before scaling Bing up as a Google proxy.

### OpenPageRank → Ahrefs DR mapping  ← assistant approximation, NOT published
- **Claimed:** 6/10 ≈ DR60; 7–8/10 ≈ DR80.
- **Why it drifts:** This is an assistant approximation, never published by DomCop or Ahrefs. OpenPageRank lags Common Crawl by months and returns 0/null for brand-new domains.
- **Re-verify:** Spot-check 2–3 page-1 domains: OpenPageRank score vs true DR from Ahrefs free Website Authority Checker. Recompute the mapping per run. Treat low/zero OpenPageRank as "unknown, verify," not "weak."

### Glimpse accuracy claim
- **Claimed:** ~87% accuracy.
- **Why it drifts:** Vendor marketing claim, unaudited.
- **Re-verify:** Treat as marketing. Sanity-check a Glimpse absolute number against a known-volume term before trusting it on a finalist.

### SEO Review Tools bulk/API claim
- **Claimed:** Bulk 1,000 keywords + API key available.
- **Why it drifts:** Unverified; free bulk limits and API availability change.
- **Re-verify:** seoreviewtools.com — confirm current bulk cap and whether an API key is still offered free.

### Official Google Trends API (alpha)
- **Claimed:** Alpha access, ~1,500 requests/day, waitlisted. **pytrends is DEAD in 2026 — do not build on it.**
- **Why it drifts:** Alpha availability and quotas change; the program may open, close, or change limits.
- **Re-verify:** Check Google Trends API alpha status before designing around it. Do NOT build on pytrends. For head-to-head trend direction, the Trends web UI remains the reliable path.

### OSS repo maintenance
- **Claimed:** chukhraiartur/seo-keyword-research-tool, hassancs91/Keyword-Research-tool-python, serpapi/google-AI-overview-scraper are usable references.
- **Why it drifts:** Repos go stale; scrapers break when selectors change.
- **Re-verify:** Check last-commit date on each GitHub repo before adopting. Lift logic, don't depend. The durable part is the raw autocomplete endpoint, not any wrapper.

### AIO DOM selectors
- **Claimed:** `.Kevs9` container, `div.Y3BBE` summary.
- **Why it drifts:** Google rotates obfuscated class names frequently; hard-coded selectors break within weeks.
- **Re-verify:** Inspect a live AIO-firing SERP in a headless/real browser and read the current DOM. Never hard-code these. A raw HTML fetch misses AIO entirely (JS-rendered/lazy-loaded) — render with a browser.

---

## C. AI-Overview / Zero-Click Stats

> All figures here are DIRECTIONAL. Use them to reason about query *shape* risk, never as exact gate thresholds. The robust thesis (interactive/stateful artifacts see the lowest AIO disruption) holds; the precise percentages do not.

### AIO prevalence
- **Claimed:** ~13–16% late-2025 (Jan ~6.5% → Jul ~25% → Nov ~15.7%); cross-vendor spread 13/16/21/48%.
- **Why it drifts:** Rapidly rising and volatile; every vendor measures a different keyword set, so numbers diverge widely.
- **Re-verify:** Pull the latest from a recent vendor SERP-features study (Semrush Sensor, seoClarity, Ahrefs). Trust the trend (rising, volatile), not any single percentage.

### Zero-click rate
- **Claimed:** 58.5% US / 59.7% EU (Semrush 2025); some cite 60%+ or "93%."
- **Why it drifts:** Methodology-dependent (per-search vs per-user, branded included or not); the "93%" is an outlier definition.
- **Re-verify:** Latest Semrush / SparkToro zero-click study. Note the denominator before quoting.

### "83% of AIO queries end without a click vs 60% without"
- **Claimed:** 83% vs 60%.
- **Why it drifts:** Single-source figure, not corroborated.
- **Re-verify:** Look for a corroborating second source before using. Treat as directional only.

### CTR drops from AIO
- **Claimed:** Ahrefs 34.5% (Apr 2025) → 58% (Dec 2025) position-1 drop; Seer ~61% organic on informational.
- **Why it drifts:** Wide spread, fast-moving, methodology varies; magnitude is escalating month over month.
- **Re-verify:** Latest Ahrefs / Seer Interactive CTR-impact study. Use to justify killing question/definition queries, not as an exact multiplier.

### Ahrefs query-shape numbers
- **Claimed:** Question 57.9% trigger vs non-question 15.5%; 1-word 9.5% → 7+ word 46.4%; 99.9% Know intent; 66.5% of AIO keywords are questions; ~21% baseline.
- **Why it drifts:** One large study (146M SERPs, 86 traits), fetched via snippets; AIO behavior shifts monthly.
- **Re-verify:** Re-pull the Ahrefs AIO study for current figures. The *direction* (questions and long queries trigger AIOs far more) is the robust input to the AI-Resistance classification test — that holds even if exact %s move.

### Interactive-tool disruption
- **Claimed:** Interactive tools see `<3%` AIO disruption.
- **Why it drifts:** The thesis (calculators/converters/generators are the safest category) is robust; the exact `<3%` came from a marketing blog.
- **Re-verify:** Treat the moat thesis as load-bearing and durable; treat `<3%` as illustrative. Confirm against any newer category-disruption breakdown if quoting a number.

### Intent-mix shift
- **Claimed:** Informational 91% → 57%; transactional 2% → 14%; navigational 0.74% → 10.33% (Jan → Oct 2025).
- **Why it drifts:** Exact months and percentages from snippet-fetched data; the shift continues, so commercial/transactional AIOs keep rising.
- **Re-verify:** Re-pull the intent-shift study for current months. Practical takeaway is unchanged: the interactive-artifact test must stay STRICT — a "tool" that is really a static table is NOT AI-safe.

---

## D. Monetization / Ad-Network Thresholds

> Display-ads-first, affiliate-as-upside is hard-coded and does not drift. The *thresholds* below do, and they set the Revenue score — re-verify any that gate a candidate.

### AdSense (floor)
- **Claimed:** No official minimum traffic; ~15–20 quality pages (community consensus); ~68% market share.
- **Why it drifts:** Policy and onboarding requirements change; the page-count figure is community, not official; share splits move.
- **Re-verify:** Google AdSense eligibility / program policies pages. Confirm there is still no stated traffic minimum and current content-quality requirements.

### Ezoic (rung 2)
- **Claimed:** Pageview minimums removed for new sign-ups; <10k joins via "Access Now"; NEW sites added to an existing account after Feb 19 2026 need 250k.
- **Why it drifts:** Secondary-sourced; the dated 250k rule is exactly the kind of policy that gets revised.
- **Re-verify:** ezoic.com requirements / help docs. Confirm the new-signup path AND the post-Feb-2026 add-to-existing-account threshold for a multi-site portfolio.

### Monumetric (rung 3)  ← load-bearing static-stack disqualifier
- **Claimed:** Propel tier = 10k pageviews + $99 setup (waived at 80k), **requires WordPress/Blogger → likely DISQUALIFIED for a static Astro/Cloudflare stack.**
- **Why it drifts:** The WordPress/Blogger-only requirement is the load-bearing reason to down-weight/skip Monumetric for this stack; if it ever supports static sites the calculus changes.
- **Re-verify:** monumetric.com requirements. Confirm directly whether non-WordPress/static sites are supported before skipping or including it.

### Mediavine Journey (rung 4)
- **Claimed:** ~1,000 sessions/mo (Jan 15 2026) + Grow plugin; 70% / 75% revenue shares; auto-graduates to main network at $5,000 trailing-12-mo ad revenue; old 50k-sessions rule retired.
- **Why it drifts:** Partly primary but recently changed; exact session threshold and graduation number are the near-term Revenue-upgrade signal, so precision matters.
- **Re-verify:** mediavine.com Journey requirements page. Confirm the session minimum, revenue shares, and the $5,000 graduation figure. Flag "plausibly reaches ~1k sessions/mo?" as a Revenue-upgrade signal for sticky/repeat-use tools.

### Raptive (rung 5)
- **Claimed:** 25,000 pageviews (cut from 100k on Oct 16 2025); ≥50% tier-one (US/UK/CA/AU/NZ) for 25k–99,999, ≥40% over 100k.
- **Why it drifts:** Well-reported but recently changed; the tier-one percentage rules gate eligibility and may be tuned further.
- **Re-verify:** raptive.com requirements. Confirm the pageview floor and tier-one traffic percentages. US/EU focus is what clears the tier-one rule.

### Niche RPM / CPC bands
- **Claimed:** Insurance/legal/finance ~$15–80+ RPM; tech/B2B SaaS ~$8–18; health/wellness ~$6–14; entertainment/student/free-stuff ~$2–6. CPC $10–50+ finance vs <$0.50 entertainment.
- **Why it drifts:** Aggregated public benchmarks, directional only; RPMs move seasonally and with ad-market conditions.
- **Re-verify:** Anchor with a live Keyword Planner top-of-page-bid pull (US-filtered) for the actual candidate term, then map CPC → RPM band. The bands are the 1–5 Revenue scoring rubric; the CPC pull is the real input.

### Amazon Associates
- **Claimed:** Category rates (games ~20%, luxury beauty/handmade ~10%, grocery/health ~1%); 3-qualifying-sales-in-180-days gate; 24h cookie.
- **Why it drifts:** Amazon revises the commission rate card and program rules regularly; the 3-sales gate is the reason a non-buyer utility audience can LOSE the account.
- **Re-verify:** Amazon Associates Operating Agreement + current commission income statement. Confirm the rate card and the 3-sales/180-day rule. Score affiliate as BONUS only when the audience genuinely overlaps buyers (e.g. mortgage calculator → home-buyers).
