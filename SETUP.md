# Setup

`projects-prd-generator` is intentionally dependency-light. It consumes artifacts that already exist in a tool's build folder and validates them — it does not call any paid API.

## Prerequisites

| Requirement | Why | Cost |
|-------------|-----|------|
| Python 3 (3.8+) | Runs `scripts/prd_lint.py` (standard library only — no `pip install`). | free |
| The host's Workflow tool | Runs `scripts/prd-skeptic-workflow.js`, the adversarial review pass. | free |
| A `prd_seed` block in the build folder | The skill's **required input** — the spine of the PRD. | free |

There are **no API keys** to configure. All measurement was already done upstream by `projects-competitive-analysis`; this skill reads its outputs.

## Upstream dependency (required)

This skill is stage 3 of the pipeline. Before running it, the tool's build folder (`micro-tool-factory/builds/<tool>/`) must contain a measured competitive brief with a `prd_seed:` YAML block, produced by:

```
/projects-competitive-analysis
```

If no `prd_seed` is found, the skill **fails closed** with: *"No prd_seed found — run projects-competitive-analysis first."* This is by design (IRON LAW 5).

## What it reads

- `COMPETITIVE-BRIEF*.md` -> the `prd_seed:` block (spine, required).
- `research-raw*.json`, `audit-measured.json`, `gaps.json` -> the source ledger + competitor baselines.
- `pick-next-tool` `research-raw.json` -> demand / keyword data (optional).
- the product gist (optional, for background).

## Verify the install

```bash
python3 scripts/prd_lint.py --selftest
```

Expected:

```
SELFTEST PASSED — 8 fixtures, laws covered: ['1-traceability', '2-tier-gating', '3-measurability', '4-scope', '5-agreement', 'completeness']
```
