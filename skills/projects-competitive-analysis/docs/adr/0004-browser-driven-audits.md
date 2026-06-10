# Browser-driven audits — live Lighthouse/screenshots/SERP over reasoned claims

**Status:** accepted

The prior "not great" competitive research (time-card brief, June 2026) produced
performance and UX assessments by visual inspection and inference: "the site looks
old, probably slow"; "it's likely mobile-unfriendly." No Lighthouse audit was run.
No screenshot was taken and measured. No structured-data parse was executed. The
result was a brief that read confidently but contained zero measured competitor
data for any of the technical dimensions (CWV, a11y, schema). Under ADR-0001,
every one of those assessments was `reasoned` and should have been marked
`UNVERIFIED` rather than presented as findings.

The chrome-devtools MCP server is available in this environment and provides
`lighthouse_audit`, `take_screenshot`, `navigate_page`, and `get_page_content`
with no additional setup. There is no excuse for reasoned performance claims when
a real Lighthouse run takes under 30 seconds per URL.

## Decision

**Browser-driven audits are the default, not an enhancement.** For every competitor
URL in the triaged set:

1. **Core Web Vitals** — `chrome-devtools: lighthouse_audit` is run and the
   `lcp`, `cls`, `inp`, and `performance_score` fields are read directly from the
   JSON output. The URL, audit date, and raw scores are cited in the output block.
   No performance claim is made without these numbers.

2. **Accessibility** — `lighthouse_audit` a11y category score is read from the same
   run. The score + top failing audits are cited.

3. **Structured data / schema** — `get_page_content` fetches the live HTML; then
   `parse_jsonld.py` (stdlib `json`; no keys) extracts all `@type` values.
   Schema presence is verified per competitor, not assumed across the set.

4. **SERP layout** — `navigate_page` loads the live SERP for the target query;
   `take_screenshot` captures AI Overview presence, featured snippet, and PAA box.
   Manual inspection of the screenshot is the fallback for single runs; `SERPAPI_KEY`
   enables automated parsing at scale (see SETUP.md).

5. **Visual UX** — `take_screenshot` of the competitor's above-the-fold layout is
   captured and attached to the output block as evidence for UX assessments.

The output always includes: tool used, URL audited, date of audit. A claim without
these three fields is `reasoned` and must be labelled as such.

## Consequences

- Each full competitor audit takes longer than a reasoned summary (30–120 seconds
  per URL for Lighthouse + schema parse). This is the correct trade-off: measured
  data is worth the wait.
- The skill's `scripts/competitor_audit.py` orchestrates the browser calls in
  sequence, writes results to `data/audit_YYYY-MM-DD/`, and feeds the scored fields
  into `score_config.py`. Raw audit output is preserved for reproducibility.
- A competitor set of 9 URLs takes roughly 5–15 minutes for a full browser-driven
  audit pass. This is disclosed to the user at the start of the run.

## Considered and rejected

- **Reasoned/visual-inspection claims tagged as triangulated if two agents agree:**
  rejected. Two agents reading the same visually-inspected page converge on the same
  visual inference, not independent evidence. Agreement between reasoned claims is
  still reasoned.
- **Run Lighthouse only for the top 3 competitors to save time:** rejected.
  Partial audits are how the time-card brief ended up with a "CSV export gap"
  asserted from 3 of 9 competitors — the unmeasured 6 contained the actual gap
  picture. The full set must be audited before gap scoring runs.
