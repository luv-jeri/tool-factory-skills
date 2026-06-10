# tasks.json schema + worked micro-example

The deliverable `task_lint.py` validates. Lives NEXT TO `build-spec.json` in the tool's build
folder. AC references are positional: `R3.2` = the 2nd entry (1-based) of requirement R3's
`acceptance_criteria` array in build-spec.json — the arrays carry no ids of their own.

## 1. Schema

```jsonc
{
  "tool": "<slug>",                          // matches build-spec.json "tool"
  "generated_from": {
    "build_spec": "<path>",
    "design_md": "<path>"
  },

  // Things the splitter could not resolve alone. blocking:true stops the build
  // until a human answers; blocking:false is a recorded default.
  "assumptions": [
    { "id": "A1", "text": "...", "blocking": false, "default": "..." }
  ],

  // Restated from build-spec scope.wont_do + DESIGN.md do-not-build — the
  // executor carries these into EVERY task.
  "standing_constraints": [ "..." ],

  // should/could ACs intentionally not owned by any task, with reasons.
  "deferred": [
    { "ac": "R5.3", "reason": "ships with the Stage-13 FAQ, not this build" }
  ],

  "tasks": [
    {
      "id": "T1",                            // unique
      "title": "...",
      "kind": "scaffold",                    // scaffold|engine|ui|content|wiring|qa|deploy
      "depends_on": [],                      // task ids; acyclic
      "requirements": ["R3"],                // requirement ids this task serves
      "acceptance_criteria": ["R3.1", "R3.2"], // Rn.k refs this task DISCHARGES
      "files": ["src/lib/engine.ts"],        // >=1; no overlap with parallel tasks
      "test_first": {                        // IRON LAW 3
        "required": true,                    // true for engine|ui|wiring
        "test": "tests/engine.test.ts",
        "red_assertion": "9:00-17:00 with 30min break totals 7.5h — fails before engine exists"
      },
      "est_hours": 3,                        // 0 < est <= 4
      "done_when": "all listed ACs' predicates pass via the named test"
    }
  ]
}
```

Notes the lint enforces:

| Field | Rule |
|---|---|
| `acceptance_criteria` | every cited `Rn.k`: requirement exists, k within its AC array (1-based). Coverage: every must AC owned somewhere; should ACs owned or in `deferred[]` |
| `depends_on` | resolvable ids, acyclic |
| `files` | two tasks with NO dependency path between them must not share a file |
| `test_first` | engine/ui/wiring: `required:true` + non-empty `test` and `red_assertion`. Other kinds may use `{"required": false, "reason": "..."}` |
| `est_hours` | number, 0 < est ≤ 4 |
| `done_when` | non-empty string |

Empty `acceptance_criteria` is legal ONLY for kinds `scaffold` and `deploy` (infrastructure with
no spec ACs) — anything else claiming zero ACs is doing untraced work.

## 2. Worked micro-example (calibration)

Two-requirement tip calculator (R1 must: 2 ACs; R2 must: 1 AC):

```json
{
  "tool": "tip-calculator",
  "generated_from": { "build_spec": "build-spec.json", "design_md": "DESIGN.md" },
  "assumptions": [],
  "standing_constraints": ["no accounts", "no web fonts", "ads below fold only"],
  "deferred": [],
  "tasks": [
    {
      "id": "T1", "title": "Scaffold from template", "kind": "scaffold",
      "depends_on": [], "requirements": [], "acceptance_criteria": [],
      "files": ["package.json", "astro.config.mjs"],
      "test_first": { "required": false, "reason": "infrastructure; verified by build succeeding" },
      "est_hours": 1, "done_when": "npm run build succeeds on the copied template"
    },
    {
      "id": "T2", "title": "Tip engine (pure)", "kind": "engine",
      "depends_on": ["T1"], "requirements": ["R1"], "acceptance_criteria": ["R1.1", "R1.2"],
      "files": ["src/lib/tip.ts", "tests/tip.test.ts"],
      "test_first": { "required": true, "test": "tests/tip.test.ts",
        "red_assertion": "tip(100, 0.2) === 20 and split(120, 4) === 30 — fails before tip.ts exists" },
      "est_hours": 2, "done_when": "R1.1 and R1.2 predicates pass in vitest"
    },
    {
      "id": "T3", "title": "Calculator UI per DESIGN.md", "kind": "ui",
      "depends_on": ["T2"], "requirements": ["R2"], "acceptance_criteria": ["R2.1"],
      "files": ["src/components/TipTool.astro", "tests/ui.test.ts"],
      "test_first": { "required": true, "test": "tests/ui.test.ts",
        "red_assertion": "preset chip click renders the tip amount in the live region — fails before TipTool exists" },
      "est_hours": 3, "done_when": "R2.1 predicate passes; DESIGN.md states implemented"
    }
  ]
}
```

## 3. Handoff summary format (printed, not a file)

```
tasks: N (kinds: ...) | ACs covered: x/y must, z deferred should
critical path: T1 -> T2 -> T3 (~Nh)
parallel groups: [T4,T7] [T5,T6]
blocking assumptions: none | A2 (needs user)
lint: PASS (pasted above)
```
