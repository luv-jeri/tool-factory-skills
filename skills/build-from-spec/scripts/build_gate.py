#!/usr/bin/env python3
"""build_gate.py — fail-closed evidence gate for build-ledger.json (build-from-spec skill).

Usage:
    python3 build_gate.py build-ledger.json tasks.json build-spec.json [--complete]
    python3 build_gate.py --selftest

Validates the build ledger an executor maintains while building from tasks.json:

    G1 structure   — JSON parses; required keys; every entry names a real task; no duplicates
    G2 order       — done entries have all dependencies done; concurrent in_progress entries
                     are dependency-independent and have all dependencies done
    G3 evidence    — test-first tasks carry literal RED (failing) and GREEN (passing) output
                     excerpts; red.test matches tasks.json; every done entry carries literal
                     done_when evidence
    G4 file scope  — files_touched is covered by the task's declared files[] plus per-file
                     justified extras
    G5 AC parity   — a done entry discharges exactly the ACs its task owns (no more, no less)
    G6 completion  — (--complete or "complete": true) every task done or blocked; every
                     must-priority AC discharged by a done task or carried by a human waiver
    G7 honesty     — deviations have what+why; blocked entries have a blocker; waivers have
                     a non-agent "by" and a reason

Exit codes: 0 PASS, 1 FAIL (violations printed), 2 usage/load error.
Stdlib only. Fail-closed: anything unparseable or unprovable is a violation.
"""

import json
import re
import sys

ALLOWED_STATUS = ("done", "in_progress", "blocked")
ENTRY_REQUIRED = ("task", "status", "files_touched", "acs_discharged")
LEDGER_REQUIRED = ("tool", "generated_from", "entries")
TEST_FIRST_KINDS = ("engine", "ui", "wiring")

# A red excerpt must look like a failure; a green excerpt must look like a pass
# and must not report a non-zero failure count.
RED_SIGNAL_RE = re.compile(
    r"fail|error|✗|×|missing|cannot find|not (?:found|defined)|assert", re.IGNORECASE)
GREEN_PASS_RE = re.compile(r"pass(?:ed|ing)?\b|✓|\bok\b|complete", re.IGNORECASE)
GREEN_FAILCOUNT_RE = re.compile(r"[1-9]\d*\s*(?:tests?\s+)?fail", re.IGNORECASE)
AGENT_WAIVER_BY = ("agent", "self", "assistant", "claude", "model", "ai")


def _load(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as exc:
        print("LOAD ERROR: %s: %s" % (path, exc))
        sys.exit(2)


def _spec_priorities(build_spec):
    """rid -> (priority, ac_count) — mirrors task_lint.py's spec parsing."""
    out = {}
    for req in build_spec.get("requirements", []):
        rid = req.get("id")
        if not rid:
            continue
        pri = str(req.get("priority", req.get("tier", ""))).strip().lower()
        out[rid] = (pri, len(req.get("acceptance_criteria", [])))
    return out


def _task_index(tasks_doc):
    return {t.get("id"): t for t in tasks_doc.get("tasks", []) if t.get("id")}


def _ancestors(task_ids, deps):
    """Transitive dependency closure per task id."""
    memo = {}

    def walk(tid, seen):
        if tid in memo:
            return memo[tid]
        if tid in seen:
            return set()  # cycle — task_lint's problem, not ours
        seen = seen | {tid}
        acc = set()
        for d in deps.get(tid, []):
            if d in task_ids:
                acc.add(d)
                acc |= walk(d, seen)
        memo[tid] = acc
        return acc

    for t in task_ids:
        walk(t, set())
    return memo


def check(ledger, tasks_doc, build_spec, complete_flag=False):
    v = []
    tasks = _task_index(tasks_doc)
    deps = {tid: t.get("depends_on", []) for tid, t in tasks.items()}
    anc = _ancestors(set(tasks), deps)

    # ---------------- G1 structure ----------------
    for key in LEDGER_REQUIRED:
        if key not in ledger:
            v.append(("G1", "ledger missing required key '%s'" % key))
    entries = ledger.get("entries", [])
    if not isinstance(entries, list):
        v.append(("G1", "'entries' is not a list"))
        entries = []
    seen_tasks = set()
    by_task = {}
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            v.append(("G1", "entry %d is not an object" % i))
            continue
        for key in ENTRY_REQUIRED:
            if key not in e:
                v.append(("G1", "entry %d (%s) missing '%s'" % (i, e.get("task", "?"), key)))
        tid = e.get("task")
        if tid not in tasks:
            v.append(("G1", "entry %d names unknown task '%s'" % (i, tid)))
            continue
        if tid in seen_tasks:
            v.append(("G1", "duplicate entry for task %s" % tid))
            continue
        seen_tasks.add(tid)
        by_task[tid] = e
        if e.get("status") not in ALLOWED_STATUS:
            v.append(("G1", "%s: status '%s' not in %s" % (tid, e.get("status"), list(ALLOWED_STATUS))))

    def status(tid):
        return by_task.get(tid, {}).get("status")

    # ---------------- G2 order ----------------
    for tid, e in by_task.items():
        if e.get("status") in ("done", "in_progress"):
            for d in deps.get(tid, []):
                if status(d) != "done":
                    v.append(("G2", "%s is %s but dependency %s is %s — DAG order violated"
                              % (tid, e["status"], d, status(d) or "absent")))
    open_tasks = [tid for tid, e in by_task.items() if e.get("status") == "in_progress"]
    for i, a in enumerate(open_tasks):
        for b in open_tasks[i + 1:]:
            if a in anc.get(b, set()) or b in anc.get(a, set()):
                v.append(("G2", "%s and %s are both in_progress but dependency-related" % (a, b)))

    # ---------------- G3 evidence ----------------
    for tid, e in by_task.items():
        if e.get("status") != "done":
            continue
        task = tasks[tid]
        tf = task.get("test_first", {})
        if tf.get("required") is True:
            red = e.get("red") or {}
            green = e.get("green") or {}
            red_out = str(red.get("output_excerpt", "")).strip()
            green_out = str(green.get("output_excerpt", "")).strip()
            if not red_out:
                v.append(("G3", "%s: test-first task has no literal RED output_excerpt" % tid))
            elif not RED_SIGNAL_RE.search(red_out):
                v.append(("G3", "%s: RED excerpt carries no failure signal: %r" % (tid, red_out[:80])))
            if not green_out:
                v.append(("G3", "%s: test-first task has no literal GREEN output_excerpt" % tid))
            else:
                if not GREEN_PASS_RE.search(green_out):
                    v.append(("G3", "%s: GREEN excerpt carries no pass signal: %r" % (tid, green_out[:80])))
                if GREEN_FAILCOUNT_RE.search(green_out):
                    v.append(("G3", "%s: GREEN excerpt reports failures: %r" % (tid, green_out[:80])))
            if red_out and red_out == green_out:
                v.append(("G3", "%s: RED and GREEN excerpts are identical — evidence not credible" % tid))
            declared_test = tf.get("test", "")
            if declared_test and red.get("test") != declared_test:
                v.append(("G3", "%s: red.test %r != tasks.json test_first.test %r"
                          % (tid, red.get("test"), declared_test)))
        if not str(e.get("done_when_evidence", "")).strip():
            v.append(("G3", "%s: done entry has no literal done_when_evidence" % tid))

    # ---------------- G4 file scope ----------------
    for tid, e in by_task.items():
        declared = set(tasks[tid].get("files", []))
        extras = {}
        for x in e.get("extra_files", []) or []:
            if isinstance(x, dict) and x.get("path"):
                extras[x["path"]] = str(x.get("reason", "")).strip()
        touched = e.get("files_touched", []) or []
        for f in touched:
            if f in declared:
                continue
            if f in extras:
                if not extras[f]:
                    v.append(("G4", "%s: extra file %s has an empty reason" % (tid, f)))
            else:
                v.append(("G4", "%s: touched undeclared file %s with no justified extra_files entry"
                          % (tid, f)))

    # ---------------- G5 AC parity ----------------
    for tid, e in by_task.items():
        if e.get("status") != "done":
            continue
        owned = set(tasks[tid].get("acceptance_criteria", []))
        claimed = set(e.get("acs_discharged", []) or [])
        missing = owned - claimed
        extra = claimed - owned
        if missing:
            v.append(("G5", "%s: done but does not discharge owned ACs %s" % (tid, sorted(missing))))
        if extra:
            v.append(("G5", "%s: discharges ACs it does not own %s" % (tid, sorted(extra))))

    # ---------------- G6 completion ----------------
    claiming_complete = complete_flag or ledger.get("complete") is True
    if complete_flag and ledger.get("complete") is not True:
        v.append(("G6", "--complete passed but ledger does not declare \"complete\": true"))
    if claiming_complete:
        pri = _spec_priorities(build_spec)
        if not pri:
            v.append(("G6", "build-spec yields zero requirements — wrong file?"))
        for tid in tasks:
            if status(tid) is None:
                v.append(("G6", "complete claimed but task %s has no ledger entry" % tid))
            elif status(tid) == "in_progress":
                v.append(("G6", "complete claimed but task %s is still in_progress" % tid))
        waivers = {}
        for w in ledger.get("waivers", []) or []:
            if isinstance(w, dict) and w.get("ac"):
                waivers[w["ac"]] = w
        discharged = set()
        for tid, e in by_task.items():
            if e.get("status") == "done":
                discharged |= set(e.get("acs_discharged", []) or [])
        for rid, (p, count) in pri.items():
            if p != "must":
                continue
            for k in range(1, count + 1):
                ac = "%s.%d" % (rid, k)
                owners = [t["id"] for t in tasks_doc.get("tasks", [])
                          if ac in t.get("acceptance_criteria", [])]
                if not owners:
                    continue  # coverage is task_lint's gate; we gate execution
                if ac not in discharged and ac not in waivers:
                    v.append(("G6", "must AC %s is neither discharged by a done task nor waived" % ac))

    # ---------------- G7 honesty ----------------
    for d in ledger.get("deviations", []) or []:
        if not isinstance(d, dict) or not str(d.get("what", "")).strip() \
                or not str(d.get("why", "")).strip():
            v.append(("G7", "deviation entry missing what/why: %r" % (d,)))
    for tid, e in by_task.items():
        if e.get("status") == "blocked" and not str(e.get("blocker", "")).strip():
            v.append(("G7", "%s: blocked with no blocker text" % tid))
    for w in ledger.get("waivers", []) or []:
        by = str(w.get("by", "")).strip()
        if not by or by.lower() in AGENT_WAIVER_BY:
            v.append(("G7", "waiver for %s lacks a human 'by' (got %r) — agents cannot self-waive"
                      % (w.get("ac", "?"), by)))
        if not str(w.get("reason", "")).strip():
            v.append(("G7", "waiver for %s has no reason" % w.get("ac", "?")))

    return v


def main(argv):
    if "--selftest" in argv:
        return selftest()
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 3:
        print(__doc__)
        return 2
    ledger = _load(args[0])
    tasks_doc = _load(args[1])
    build_spec = _load(args[2])
    violations = check(ledger, tasks_doc, build_spec, complete_flag="--complete" in argv)
    if violations:
        for code, msg in violations:
            print("%s FAIL: %s" % (code, msg))
        print("RESULT: FAIL (%d violation%s)" % (len(violations), "s" if len(violations) != 1 else ""))
        return 1
    done = sum(1 for _ in ledger.get("entries", []) if _.get("status") == "done")
    print("RESULT: PASS (%d entries, %d done)" % (len(ledger.get("entries", [])), done))
    return 0


# ------------------------------------------------------------------
# Selftest — golden-good ledger must PASS; each golden-bad must FAIL
# on the expected gate; mutating the good ledger must flip the result.
# ------------------------------------------------------------------

GOOD_SPEC = {"requirements": [
    {"id": "R1", "priority": "must", "acceptance_criteria": [{}, {}]},
    {"id": "R2", "priority": "must", "acceptance_criteria": [{}]},
    {"id": "R3", "priority": "should", "acceptance_criteria": [{}]},
]}

GOOD_TASKS = {
    "tool": "selftest",
    "tasks": [
        {"id": "T1", "title": "scaffold", "kind": "scaffold", "depends_on": [],
         "requirements": [], "acceptance_criteria": [], "files": ["package.json"],
         "test_first": {"required": False, "reason": "infrastructure"},
         "est_hours": 1, "done_when": "build passes"},
        {"id": "T2", "title": "engine", "kind": "engine", "depends_on": ["T1"],
         "requirements": ["R1"], "acceptance_criteria": ["R1.1", "R1.2"],
         "files": ["src/lib/x.ts", "tests/x.test.ts"],
         "test_first": {"required": True, "test": "tests/x.test.ts",
                        "red_assertion": "fails before x.ts exists"},
         "est_hours": 3, "done_when": "R1 ACs pass"},
        {"id": "T3", "title": "ui", "kind": "ui", "depends_on": ["T2"],
         "requirements": ["R2"], "acceptance_criteria": ["R2.1"],
         "files": ["src/components/Y.astro", "tests/y.test.ts"],
         "test_first": {"required": True, "test": "tests/y.test.ts",
                        "red_assertion": "fails before Y exists"},
         "est_hours": 2, "done_when": "R2.1 passes"},
    ],
}

GOOD_LEDGER = {
    "tool": "selftest",
    "generated_from": {"tasks": "tasks.json"},
    "complete": True,
    "deviations": [
        {"task": "T1", "what": "pinned vitest 3.x not latest", "why": "template parity"}
    ],
    "waivers": [],
    "entries": [
        {"task": "T1", "status": "done", "files_touched": ["package.json", "package-lock.json"],
         "extra_files": [{"path": "package-lock.json", "reason": "npm install artifact"}],
         "acs_discharged": [],
         "done_when_evidence": "npm run build -> 'Complete!' 6 pages built"},
        {"task": "T2", "status": "done",
         "files_touched": ["src/lib/x.ts", "tests/x.test.ts"], "acs_discharged": ["R1.1", "R1.2"],
         "red": {"test": "tests/x.test.ts", "command": "npx vitest run tests/x.test.ts",
                 "output_excerpt": "FAIL tests/x.test.ts — Cannot find module '../src/lib/x'"},
         "green": {"command": "npx vitest run tests/x.test.ts",
                   "output_excerpt": "Test Files 1 passed | Tests 12 passed"},
         "done_when_evidence": "vitest: Tests 12 passed (12)"},
        {"task": "T3", "status": "done",
         "files_touched": ["src/components/Y.astro", "tests/y.test.ts"],
         "acs_discharged": ["R2.1"],
         "red": {"test": "tests/y.test.ts", "command": "npx vitest run tests/y.test.ts",
                 "output_excerpt": "AssertionError: expected <button> to exist — ✗ 3 tests failed"},
         "green": {"command": "npx vitest run tests/y.test.ts",
                   "output_excerpt": "✓ tests/y.test.ts (3 tests) — all passed"},
         "done_when_evidence": "vitest green; component renders per DESIGN.md"},
    ],
}


def _clone(obj):
    return json.loads(json.dumps(obj))


def selftest():
    failures = []

    def expect(name, ledger, want_codes, complete=True):
        got = check(ledger, GOOD_TASKS, GOOD_SPEC, complete_flag=complete)
        codes = {c for c, _ in got}
        if want_codes is None:
            if got:
                failures.append("%s: expected PASS, got %s" % (name, got))
        else:
            if not codes & set(want_codes):
                failures.append("%s: expected a violation in %s, got %s" % (name, want_codes, got))

    expect("good-ledger", GOOD_LEDGER, None)

    b = _clone(GOOD_LEDGER); b["entries"][1].pop("red")
    expect("bad-missing-red", b, {"G3"})

    b = _clone(GOOD_LEDGER)
    b["entries"][1]["red"]["output_excerpt"] = b["entries"][1]["green"]["output_excerpt"]
    expect("bad-red-equals-green", b, {"G3"})

    b = _clone(GOOD_LEDGER); b["entries"][1]["red"]["output_excerpt"] = "everything looks good"
    expect("bad-red-no-fail-signal", b, {"G3"})

    b = _clone(GOOD_LEDGER); b["entries"][1]["green"]["output_excerpt"] = "Tests 11 passed | 1 failed"
    expect("bad-green-reports-failures", b, {"G3"})

    b = _clone(GOOD_LEDGER); b["entries"][1]["red"]["test"] = "tests/other.test.ts"
    expect("bad-wrong-red-test-path", b, {"G3"})

    b = _clone(GOOD_LEDGER); b["entries"][0]["done_when_evidence"] = ""
    expect("bad-no-done-when-evidence", b, {"G3"})

    b = _clone(GOOD_LEDGER); b["entries"][1]["files_touched"].append("src/sneaky.ts")
    expect("bad-undeclared-file", b, {"G4"})

    b = _clone(GOOD_LEDGER); b["entries"][0]["extra_files"][0]["reason"] = ""
    expect("bad-extra-file-empty-reason", b, {"G4"})

    b = _clone(GOOD_LEDGER); b["entries"][1]["status"] = "in_progress"
    expect("bad-dep-not-done", b, {"G2"}, complete=False)

    b = _clone(GOOD_LEDGER)
    b["entries"][1]["status"] = "in_progress"; b["entries"][2]["status"] = "in_progress"
    expect("bad-dependent-both-open", b, {"G2"}, complete=False)

    b = _clone(GOOD_LEDGER); b["entries"][1]["acs_discharged"] = ["R1.1"]
    expect("bad-acs-subset", b, {"G5"})

    b = _clone(GOOD_LEDGER); b["entries"][1]["acs_discharged"] = ["R1.1", "R1.2", "R2.1"]
    expect("bad-acs-superset", b, {"G5"})

    b = _clone(GOOD_LEDGER); b["entries"].append(_clone(b["entries"][1]))
    expect("bad-duplicate-entry", b, {"G1"})

    b = _clone(GOOD_LEDGER); b["entries"][2]["task"] = "T9"
    expect("bad-unknown-task", b, {"G1"})

    b = _clone(GOOD_LEDGER); b["entries"].pop(2)
    expect("bad-complete-missing-task", b, {"G6"})

    b = _clone(GOOD_LEDGER)
    b["entries"][2] = {"task": "T3", "status": "blocked", "files_touched": [],
                       "acs_discharged": [], "blocker": ""}
    expect("bad-blocked-no-blocker", b, {"G7"})

    b = _clone(GOOD_LEDGER)
    b["entries"][2] = {"task": "T3", "status": "blocked", "files_touched": [],
                       "acs_discharged": [], "blocker": "needs user decision on Y"}
    expect("bad-complete-must-ac-unwaived", b, {"G6"})

    b = _clone(GOOD_LEDGER)
    b["entries"][2] = {"task": "T3", "status": "blocked", "files_touched": [],
                       "acs_discharged": [], "blocker": "needs user decision on Y"}
    b["waivers"] = [{"ac": "R2.1", "by": "agent", "reason": "could not fix"}]
    expect("bad-agent-self-waiver", b, {"G7"})

    # invariant: mutating the good ledger flips PASS -> FAIL
    b = _clone(GOOD_LEDGER); b["entries"][2].pop("green")
    got = check(b, GOOD_TASKS, GOOD_SPEC, complete_flag=True)
    if not got:
        failures.append("invariant: dropping GREEN evidence did not flip the result")

    if failures:
        for f in failures:
            print("SELFTEST FAIL: %s" % f)
        print("SELFTEST RESULT: FAIL (%d)" % len(failures))
        return 1
    print("SELFTEST RESULT: PASS (1 good, 18 bad, 1 invariant)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
