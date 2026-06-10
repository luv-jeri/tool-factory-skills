# Split the golden test into a mutable snapshot and immutable invariants

**Status:** accepted

The `score.py --selftest` was sold as a *correctness* oracle ("PASS → Timesheet=89 is the right pick"), but its fixture inputs (`thin_site_proof=True`, `kd_head=70`, `incumbent_top3_visits=2,000,000`, `cluster_monthly_volume=50000`, `cpc=3.0`, …) are the same unverified estimates IRON LAW 1 forbids deciding on. So it only ever proved the engine reproduces a *past guess* — wiring confidence masquerading as correctness confidence — and it would break the moment ADR-0002's calibration loop retunes a threshold, training agents to distrust an engine that just got *better*. We re-architect it.

## The new shape

1. **Mutable snapshot** — keep one `Timesheet == 89.0` assertion, tagged `# snapshot of v0 weights — expected to change on recalibration`. On change it **fails loudly** and a human must deliberately re-bless the new number (a feature under ADR-0001, not friction). It never auto-updates silently.
2. **Immutable structural invariants** — the real regression guarantee, encoding the *methodology* not the *numbers*, so they survive any retuning: QR drops at Gate A; Freelance/TikTok drop at Gate D; a gate-dropped tool carries no Opportunity number; any dimension `=1` vetoes; the all-rounder outranks the highest-on-one-axis tool.
3. **Golden-bad fixtures** — synthetic must-DROP / must-VETO / must-REFUSE cases that assert the engine *refuses duds*, making the ruin-avoidance behavior (ADR-0001) directly testable.
4. **Re-label** the docstring and SKILL.md so "selftest PASS" can never again be read as "Timesheet is the correct pick."

## Consequences

- A failing snapshot after recalibration is the expected, intended signal — not a regression. Reviewers re-bless deliberately.
- Structural-invariant or golden-bad failures are real engine breakage and block.
