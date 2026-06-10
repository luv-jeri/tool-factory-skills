# tool-factory-skills

A single repository of Claude Code skills that together form an evidence-gated pipeline for
shipping small, single-purpose, ad-monetized web tools — from "what should we build next?" all the
way to a machine-readable build contract, with build/SEO/ship/monetize skills on the roadmap.

Structured as one plugin with many sub-skills, in the spirit of
[anthropics/skills](https://github.com/anthropics/skills) and
[obra/superpowers](https://github.com/obra/superpowers).

## The pipeline

Each stage is a separate skill with a strict input/output contract. The output of one stage is the
only legal input of the next, so nothing is built on an unmeasured assumption.

| # | Skill | Question it answers | Key outputs |
|---|-------|---------------------|-------------|
| 1 | [`pick-next-tool`](skills/pick-next-tool/) | What should we build next? | Verified winner + ordered roadmap (deterministic `score.py`, kill-gates A–D, adversarial kill pass) |
| 2 | [`projects-competitive-analysis`](skills/projects-competitive-analysis/) | Why will we win? | Measured COMPETITIVE-BRIEF + source ledger + `prd_seed` handoff (11 measurement pillars, incl. voice-of-customer pain points and input ergonomics) |
| 3 | [`projects-prd-generator`](skills/projects-prd-generator/) | What exactly do we build? | FINAL-stamped PRD.md + machine `build-spec.json` (fail-closed `prd_lint.py` + adversarial skeptic) |

Planned next stages (same hardened pattern — see [ROADMAP.md](ROADMAP.md)): `design-md`,
`task-splitter`, `build-from-spec`, `seo-content`, `legal-crawl`, `ship`, `qa-gate-runner`,
`index-submit`, `monetize-adsense`.

## What "hardened" means here

Every skill in this repo follows the same discipline:

- **IRON LAWS** — explicit, loophole-closed rules; violating the letter is violating the spirit.
- **Fail-closed engines** — deterministic Python/JS validators (`score.py`, `competitor_strength.py`,
  `gap_opportunity.py`, `prd_lint.py`) that RAISE on missing inputs; "insufficient data" and
  "REFUSE" are legal outputs.
- **Evidence tiers** — `real-measured` > `triangulated` > `reasoned`/`UNVERIFIED`; weak tiers can
  never back a committed decision or a v1 must-have.
- **Adversarial kill passes** — a separate skeptic challenges every load-bearing claim before
  anything is stamped FINAL.
- **RED-GREEN evals** — every skill ships `evals/evals.json` cases written from real, documented
  failures (the RED), so regressions are testable.
- **ADRs** — `docs/adr/` records the why behind every rule.

## Install

### Option A — copy or symlink individual skills (simplest)

```bash
git clone https://github.com/luv-jeri/tool-factory-skills
# per skill, into a project:
ln -s /path/to/tool-factory-skills/skills/pick-next-tool  your-project/.claude/skills/pick-next-tool
# (or cp -R instead of ln -s)
```

Skills then invoke by bare name: `/pick-next-tool`, `/projects-competitive-analysis`,
`/projects-prd-generator`.

### Option B — as a Claude Code plugin

The repo carries `.claude-plugin/plugin.json`, so it can be installed as a plugin (skills invoke
namespaced, e.g. `/tool-factory:pick-next-tool`). See the
[Claude Code plugin docs](https://docs.anthropic.com/en/docs/claude-code) for marketplace setup.

## Per-skill setup

`pick-next-tool` and `projects-competitive-analysis` have optional free-API integrations (Google
Ads, OpenPageRank, SerpApi, Bing) — each skill's `SETUP.md` documents the one-time keys. All skills
run in a free, browser-driven mode with zero setup.

## History

These skills started life as three standalone repos
([pick-next-tool](https://github.com/luv-jeri/pick-next-tool),
[projects-competitive-analysis](https://github.com/luv-jeri/projects-competitive-analysis),
[projects-prd-generator](https://github.com/luv-jeri/projects-prd-generator)) and were merged here
with their git histories preserved (`git subtree`). This repo is now the canonical home.

## License

MIT — see [LICENSE](LICENSE).
