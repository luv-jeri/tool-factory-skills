# projects-prd-generator

A Claude Code skill that turns a **measured competitive brief** into a **single-source-of-truth Product Requirements Document** plus a machine-readable `build-spec` for the dev team and project managers — validated by a fail-closed engine and an adversarial skeptic before it is allowed to be stamped FINAL.

It is the third stage of a three-skill pipeline:

| Stage | Skill | Answers |
|-------|-------|---------|
| 1 | [pick-next-tool](https://github.com/luv-jeri/pick-next-tool) | *What* should we build next? |
| 2 | [projects-competitive-analysis](https://github.com/luv-jeri/projects-competitive-analysis) | *Why* will we win? (measured brief + `prd_seed`) |
| 3 | **projects-prd-generator** | *What exactly* do we build? (the buildable contract) |

## Why

A hand-written PRD drifts: it omits non-goals, states unmeasurable goals ("make it fast"), and promotes unverified hunches to requirements. This skill makes those failures structurally impossible:

- **No requirement without a source** — every requirement traces to a ledger entry or is a tagged, owned assumption.
- **No unverified claim as a v1 must-have** — weak-tier evidence can only be a v2 item or a tracked open question.
- **Every acceptance criterion is measurable** — a number + unit, or it is cut.
- **Scope is three-sided** — DO / WON'T-DO / SKIPPED-FOR-NOW. A feature in none of the three is a gap.
- **Fail-closed** — a missing section, an untraceable requirement, an unmeasurable criterion, or a PRD/build-spec mismatch refuses FINAL.

## Install

```bash
git clone https://github.com/luv-jeri/projects-prd-generator .claude/skills/projects-prd-generator
```

## Usage

Invoke in Claude Code:

```
/projects-prd-generator
```

The skill runs an 8-stage gated funnel over a tool's build folder (which must already contain a `prd_seed` block from `projects-competitive-analysis`) and writes to that folder:

- `PRD.md` — the human single source of truth (14 sections; FINAL only on a clean validation).
- `build-spec.json` + `build-spec.yaml` — the frozen machine "definition of done."
- `prd-trace.md` — the requirement -> source traceability ledger.

## Verify the engine

```bash
python3 scripts/prd_lint.py --selftest
# SELFTEST PASSED — 8 fixtures, laws covered: [...]
```

`prd_lint.py` is Python 3, standard library only — no install, no paid keys.

## License

MIT © 2026 Sanjay Kumar. See [LICENSE](LICENSE).
