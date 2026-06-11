# build-ledger.json schema + worked micro-example

The deliverable `build_gate.py` validates alongside the app itself. Lives NEXT TO `tasks.json`
in the tool's build folder. The ledger is the build's evidence record: every task the executor
touches gets an entry, and every claim in an entry is backed by a **literal command output
excerpt** — pasted, not paraphrased. A chat report of "tests green" is not evidence; the ledger
is what survives the session and what the next pipeline stage (qa-gate-runner) reads.

## 1. Schema

```jsonc
{
  "tool": "<slug>",                      // matches tasks.json "tool"
  "generated_from": { "tasks": "<path to tasks.json>" },
  "app_root": "<path the app is built at>",
  "complete": false,                     // true ONLY when every task is done/blocked
                                         // and the completion gate passes

  // Any departure from tasks.json, build-spec, DESIGN.md, or the scaffold docs.
  // Recorded the moment it happens — a deviation that lives only in chat does not exist.
  "deviations": [
    { "task": "T1", "what": "Astro 6.4.6 instead of template-pinned 5.13",
      "why": "v6 is the current stable per the stack ADR; template hardening is pending" }
  ],

  // Human-granted waivers for ACs that cannot be discharged. "by" must be a person
  // (the engine rejects agent/self/assistant). Agents never self-waive.
  "waivers": [
    { "ac": "R4.4", "by": "sanjay", "reason": "CrUX field data only exists post-launch" }
  ],

  "entries": [
    {
      "task": "T3",                      // must exist in tasks.json; one entry per task
      "status": "done",                  // done | in_progress | blocked
      "files_touched": ["src/lib/engine.ts", "tests/engine.test.ts"],

      // Files outside the task's declared files[] need a per-file reason.
      // No entry here + not declared = gate failure.
      "extra_files": [
        { "path": "package-lock.json", "reason": "npm install artifact" }
      ],

      // REQUIRED when tasks.json test_first.required is true:
      // the literal output of running the test BEFORE the implementation existed.
      "red": {
        "test": "tests/engine.test.ts",  // must equal tasks.json test_first.test
        "command": "npx vitest run tests/engine.test.ts",
        "output_excerpt": "FAIL tests/engine.test.ts — Cannot find module '../src/lib/engine'"
      },
      // The literal passing output AFTER the implementation.
      "green": {
        "command": "npx vitest run tests/engine.test.ts",
        "output_excerpt": "Test Files 1 passed (1) | Tests 15 passed (15)"
      },

      // Literal evidence that the task's done_when clause holds (build output,
      // test totals, script output). Required for EVERY done entry.
      "done_when_evidence": "vitest: Tests 15 passed (15); engine.ts is pure (no DOM imports)",

      // Exactly the ACs this task owns in tasks.json — no more, no less.
      "acs_discharged": ["R3.1", "R3.3", "R3.5", "R3.6"]
    },
    {
      "task": "T17", "status": "blocked",
      "files_touched": [], "acs_discharged": [],
      "blocker": "A1/A2/A3 unresolved: domain, contact identity, Web3Forms key need the user"
    }
  ]
}
```

Rules the gate enforces:

| Field | Rule |
|---|---|
| `entries[].task` | exists in tasks.json; one entry per task |
| `status` | `done` requires all `depends_on` tasks done; concurrent `in_progress` entries must be dependency-independent |
| `red` / `green` | required for test-first tasks; red excerpt carries a failure signal, green a pass signal and no failure count; red ≠ green; `red.test` matches the declared test |
| `done_when_evidence` | non-empty literal output for every done entry |
| `files_touched` | every file is declared in the task's `files[]` or justified in `extra_files` |
| `acs_discharged` | exactly equals the task's `acceptance_criteria` for done entries |
| `complete: true` | every task done or blocked; every must AC discharged or human-waived |
| `deviations` / blocked entries / `waivers` | what+why / non-empty `blocker` text / human `by` + reason |

## 2. Worked micro-example (calibration)

Three-task tip calculator, mid-build — T1 done, T2 done, T3 open:

```json
{
  "tool": "tip-calculator",
  "generated_from": { "tasks": "tasks.json" },
  "app_root": "apps/tip-calculator",
  "complete": false,
  "deviations": [],
  "waivers": [],
  "entries": [
    {
      "task": "T1", "status": "done",
      "files_touched": ["package.json", "astro.config.mjs", "package-lock.json", "tsconfig.json"],
      "extra_files": [
        { "path": "package-lock.json", "reason": "npm install artifact" },
        { "path": "tsconfig.json", "reason": "emitted by create-astro; required for TS strict" }
      ],
      "done_when_evidence": "npm run build → 'Complete!' 4 pages built in 1.2s",
      "acs_discharged": []
    },
    {
      "task": "T2", "status": "done",
      "files_touched": ["src/lib/tip.ts", "tests/tip.test.ts"],
      "red": { "test": "tests/tip.test.ts", "command": "npx vitest run tests/tip.test.ts",
        "output_excerpt": "FAIL — Cannot find module '../src/lib/tip' (2 tests failed)" },
      "green": { "command": "npx vitest run tests/tip.test.ts",
        "output_excerpt": "✓ tests/tip.test.ts (2 tests) | Tests 2 passed (2)" },
      "done_when_evidence": "vitest: Tests 2 passed (2); tip(100,0.2)=20, split(120,4)=30",
      "acs_discharged": ["R1.1", "R1.2"]
    },
    {
      "task": "T3", "status": "in_progress",
      "files_touched": ["tests/ui.test.ts"],
      "red": { "test": "tests/ui.test.ts", "command": "npx vitest run tests/ui.test.ts",
        "output_excerpt": "FAIL — TipTool.astro does not exist; preset-chip assertion ✗" },
      "acs_discharged": []
    }
  ]
}
```

Note the T3 shape: the RED evidence is recorded **the moment the failing run happens**, while the
entry is still `in_progress` — not reconstructed at the end. When T3 goes green, the entry gains
`green`, `done_when_evidence`, the full `files_touched`, `acs_discharged: ["R2.1"]`, and
`status: "done"`.

## 3. Handoff summary format (printed, not a file)

```
tasks: 12/17 done, 1 blocked (T17 — A1/A2/A3), 4 not started
ACs discharged: 19/19 must, 10/10 should | waivers: none
deviations: 2 (recorded in ledger)
gate: PASS (pasted above) | full suite: Tests 64 passed (64) | build: clean
ledger: tools-mono-repo/time-card-calculator/build-ledger.json
```
