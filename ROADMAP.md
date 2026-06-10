# Roadmap — the remaining pipeline skills

The pipeline currently covers stages 1–3 (pick → measure → PRD). The stages below complete the
path from build-spec to a live, indexed, monetized tool. Each will be built in this repo at the
same hardened level as the existing three: IRON LAWS, a fail-closed engine where real logic exists
(a checklist + verifier script for the mechanical ones), an adversarial pass where judgment is
involved, RED-GREEN evals, and ADRs.

Build order, with contracts:

| # | Skill | Input → Output | Gate |
|---|-------|----------------|------|
| 1 | `task-splitter` | `build-spec.json` (+ `design.md`) → `tasks.json` DAG of 2–4 h tasks, each carrying the acceptance criteria it must satisfy | 100% of ACs mapped to ≥1 task; no cycles (lint script) |
| 2 | `build-from-spec` | `tasks.json` + hardened template → working app, test suite green | Every AC has a passing test or an explicit human waiver; per-task TDD (red-green-refactor) |
| 3 | `design-md` | PRD + brief (incl. `prd_seed.pain_points` / `input_ergonomics`) → `design.md`: tokens, layout, component inventory, states, ad-slot placement map, a11y notes | Every must-requirement has a screen/state; input modalities favor pickers/defaults/accelerators over typing; ads never displace the tool |
| 4 | `seo-content` | PRD keywords + brief PAA data → 600+ original words, visible FAQ (no FAQPage markup — rich results dead May 2026), title/meta/OG, internal cluster links | Originality check (no template-paraphrase across variants); human originality pass mandatory |
| 5 | `legal-crawl` | brand + contact → privacy/terms/about/contact (double-linked), 404, robots.txt, sitemap check | All four legal pages live and linked |
| 6 | `ship` | built app → GA4 wired, Cloudflare Workers static-assets deploy, custom domain, staging-host noindex | Staging host returns `X-Robots-Tag: noindex`; production does not |
| 7 | `qa-gate-runner` | deployed URL → blocking gate report | Lighthouse ≥95 ×4 (mobile), CWV green, zero console errors, schema validates |
| 8 | `index-submit` | live URL set → GSC verified, sitemap submitted, URL-inspection requests filed | Key URLs requested (no IndexNow for Google; sitemap ping is dead) |
| 9 | `monetize-adsense` | gate-passing hub → AdSense script + ads.txt + EEA/UK CMP | Pre-application gate: ~1 month live, ~10 daily users, content + legal pages (hub-level, mostly one-time) |

Not skills (by design): post-launch watching is a cron job writing to the launch tracker;
promotion/outreach stays human with a checklist (spam risk); i18n is deferred until an EU-language
tool is actually picked.

Source of truth for the full plan and the evidence behind these contracts:
`micro-tool-factory/strategy/12-PIPELINE-AUDIT-AND-SKILL-ROADMAP.md` in the workspace this repo
grew out of.
