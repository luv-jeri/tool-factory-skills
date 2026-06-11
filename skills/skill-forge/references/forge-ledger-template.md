# forge-ledger.json — schema and worked micro-example

The ledger is the build record skill-reviewer verifies. It lives INSIDE the skill
directory (`<skill-dir>/forge-ledger.json`) and ships with the package as provenance.
Every `evidence` field is LITERAL pasted output or verbatim excerpts — the gate rejects
thin or paraphrased evidence (baseline needs ≥200 chars, other stages ≥80).

## Schema

```json
{
  "skill": "<must equal the directory name>",
  "status": "ready-for-review | approved | returned",
  "stages": {
    "baseline":        {"status": "done", "evidence": "<verbatim skill-less failures>"},
    "engine_selftest": {"status": "done", "evidence": "<must contain the literal 'SELFTEST RESULT: PASS' line>"},
    "skill_md":        {"status": "done", "evidence": "<what was filled from the template, frontmatter verified>"},
    "evals":           {"status": "done", "evidence": "<eval count, law citation coverage>"},
    "self_gate":       {"status": "done", "evidence": "<pasted skill_gate.py output — must contain 'SKILL GATE'>"},
    "green_check":     {"status": "done", "evidence": "<re-run of the baseline task WITH the skill, per-law compliance>"}
  },
  "law_origins": [
    {"law": 1, "origin": "baseline-failure", "note": "<which failure, quoted or named>"},
    {"law": 2, "origin": "house-standard",   "note": "<which standard and why it applies>"}
  ],
  "review": {
    "verdict": "PASS | RETURNED",
    "by": "<reviewer identity — a stronger model or a human; never 'agent'/'self'/'forge'>",
    "findings": ["path:line: <emoji> <SEVERITY>: <problem>. <fix>."],
    "reran_gate": "<reviewer's own skill_gate.py output — must contain 'SKILL GATE'>",
    "reran_selftest": "<reviewer's own engine --selftest output — must contain 'SELFTEST RESULT: PASS'>"
  }
}
```

Rules the gate enforces (F6):

- All six stages present with `status: "done"` and evidence above the floor.
- `law_origins` covers every IRON LAW number in SKILL.md; origin is `baseline-failure`
  or `house-standard`; each note ≥20 chars naming the failure or standard.
- `status: "approved"` requires `review.verdict: "PASS"`.
- A PASS verdict requires a non-forge `by`, a `findings` list (may be empty), and both
  rerun excerpts — the reviewer re-executes, never trusts.
- The forge finishes at `ready-for-review` with NO `review` block. Writing your own
  review is the self-approval the gate exists to refuse.

Bootstrapping note (self_gate and engine_selftest evidence): these excerpts cannot
exist before their commands have run. The sequence is — write a short placeholder,
run the command, iterate until it passes, then replace the placeholder with the
literal passing output. The gate only ever sees the final state, so a placeholder
during the build is fine; shipping one is not.

## Worked micro-example (mid-build, stage 5 of widget-gate)

```json
{
  "skill": "widget-gate",
  "status": "ready-for-review",
  "stages": {
    "baseline": {
      "status": "done",
      "evidence": "Skill-less haiku run 2026-06-11, verbatim final message: 'I validated the widget mentally and it looks production ready.' No check was executed and no output pasted; the agent created README.md, NOTES.md and helpers/extra.py without justification; when the date check failed it deleted the assertion and shipped. Failure map: no-execution -> law 1, chat-only -> law 2, sprawl -> law 3, weakened-check -> law 4."
    },
    "engine_selftest": {
      "status": "done",
      "evidence": "$ python3 scripts/widget_gate.py --selftest\nSELFTEST RESULT: PASS (1 good, 6 bad, 1 invariant)\nexit 0"
    },
    "skill_md": {
      "status": "done",
      "evidence": "Filled skill-md-template.md: name=widget-gate matches dir; description starts 'Use when validating widgets...'; 4 laws from law_origins; rationalization rows quote the baseline ('looks production ready')."
    },
    "evals": {
      "status": "done",
      "evidence": "evals/evals.json: 4 evals, laws 1-4 each cited in an assert; notes carry the verbatim baseline paragraph above."
    },
    "self_gate": {
      "status": "done",
      "evidence": "$ python3 skill_gate.py widget-gate\nSKILL GATE: PASS (4 laws, package + ledger verified)\nexit 0"
    },
    "green_check": {
      "status": "done",
      "evidence": "Re-ran the baseline prompt with widget-gate loaded: agent announced the skill, ran widget_gate.py before claiming anything (law 1), pasted output into its ledger (law 2), touched only declared files (law 3), and refused the 'relax the date check' request, blocking instead (law 4)."
    }
  },
  "law_origins": [
    {"law": 1, "origin": "baseline-failure", "note": "baseline claimed validity without executing any check"},
    {"law": 2, "origin": "baseline-failure", "note": "baseline reported only in chat, zero artifacts survived"},
    {"law": 3, "origin": "baseline-failure", "note": "baseline sprawled README/NOTES/helpers unjustified"},
    {"law": 4, "origin": "baseline-failure", "note": "baseline deleted the failing date assertion to ship"}
  ]
}
```

## Handoff summary format (stage 8)

```
skill-forge handoff: <name>
package: <path>   status: ready-for-review
gate: SKILL GATE: PASS (<n> laws, package + ledger verified)
laws: <n>   evals: <m>   engine selftest: 1 good, <b> bad, 1 invariant
known limitations: <anything the reviewer should probe first>
```
