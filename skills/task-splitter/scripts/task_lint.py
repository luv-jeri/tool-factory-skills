#!/usr/bin/env python3
"""task_lint.py — fail-closed engine for tasks.json (task-splitter skill).

Validates a tasks.json against its build-spec.json:

  L1 structure — parses, required keys, unique task ids, allowed kinds
  L2 DAG — depends_on resolve, acyclic
  L3 coverage — every must AC (Rn.k, 1-based) owned by >=1 task; cited refs
     exist and are in range; should ACs owned or deferred with reason
  L4 estimates — 0 < est_hours <= 4
  L5 test-first — engine/ui/wiring require test+red_assertion; other kinds may
     opt out with a reason; empty acceptance_criteria only for scaffold/deploy
  L6 files — >=1 per task; no file shared by two dependency-independent tasks
  L7 done_when — non-empty

Fail-closed. Exit 0 PASS, 1 FAIL, 2 usage/input error.

Usage:
  python3 task_lint.py tasks.json build-spec.json
  python3 task_lint.py --selftest

stdlib only.
"""

import json
import re
import sys

ALLOWED_KINDS = ("scaffold", "engine", "ui", "content", "wiring", "qa", "deploy")
TEST_FIRST_KINDS = ("engine", "ui", "wiring")
NO_AC_KINDS = ("scaffold", "deploy")
AC_REF_RE = re.compile(r"^(R\w+)\.(\d+)$")


def spec_acs(build_spec):
    """{rid: (priority, ac_count)} from build-spec.json."""
    out = {}
    for req in build_spec.get("requirements", []):
        rid = req.get("id")
        if not rid:
            continue
        pri = str(req.get("priority", req.get("tier", ""))).strip().lower()
        out[rid] = (pri, len(req.get("acceptance_criteria", [])))
    return out


def _cycle_free(tasks_by_id):
    """Kahn topological sort; returns (ok, detail)."""
    indeg = {tid: 0 for tid in tasks_by_id}
    for t in tasks_by_id.values():
        for dep in t.get("depends_on", []):
            if dep in indeg:
                indeg[t["id"]] += 1
    queue = [tid for tid, d in indeg.items() if d == 0]
    seen = 0
    children = {tid: [] for tid in tasks_by_id}
    for t in tasks_by_id.values():
        for dep in t.get("depends_on", []):
            if dep in children:
                children[dep].append(t["id"])
    while queue:
        node = queue.pop()
        seen += 1
        for child in children[node]:
            indeg[child] -= 1
            if indeg[child] == 0:
                queue.append(child)
    if seen != len(tasks_by_id):
        stuck = sorted(tid for tid, d in indeg.items() if d > 0)
        return False, "cycle involving: %s" % ", ".join(stuck)
    return True, ""


def _ancestors(tasks_by_id):
    """{tid: set(all transitive deps)} — DAG assumed already verified."""
    memo = {}

    def walk(tid, stack):
        if tid in memo:
            return memo[tid]
        if tid in stack:          # cycle guard; cycle reported by L2 anyway
            return set()
        stack = stack | {tid}
        acc = set()
        for dep in tasks_by_id.get(tid, {}).get("depends_on", []):
            if dep in tasks_by_id:
                acc.add(dep)
                acc |= walk(dep, stack)
        memo[tid] = acc
        return acc

    for tid in tasks_by_id:
        walk(tid, frozenset())
    return memo


def check(tasks_doc, build_spec):
    v = []

    # L1 structure
    for key in ("tool", "tasks"):
        if key not in tasks_doc:
            v.append({"check": "L1-structure", "message": "missing top-level key '%s'" % key})
    tasks = tasks_doc.get("tasks", [])
    if not isinstance(tasks, list) or not tasks:
        v.append({"check": "L1-structure", "message": "tasks missing or empty"})
        return {"pass": False, "violations": v}
    ids = [t.get("id") for t in tasks]
    if len(ids) != len(set(ids)) or not all(ids):
        v.append({"check": "L1-structure", "message": "task ids missing or not unique"})
        return {"pass": False, "violations": v}
    tasks_by_id = {t["id"]: t for t in tasks}
    for t in tasks:
        if t.get("kind") not in ALLOWED_KINDS:
            v.append({"check": "L1-structure",
                      "message": "task %s kind '%s' not in %s" % (t["id"], t.get("kind"), list(ALLOWED_KINDS))})

    # L2 DAG
    for t in tasks:
        for dep in t.get("depends_on", []):
            if dep not in tasks_by_id:
                v.append({"check": "L2-dag", "message": "task %s depends on unknown '%s'" % (t["id"], dep)})
    ok, detail = _cycle_free(tasks_by_id)
    if not ok:
        v.append({"check": "L2-dag", "message": detail})
        return {"pass": False, "violations": v}

    # L3 coverage
    acs = spec_acs(build_spec)
    if not acs:
        v.append({"check": "L3-coverage", "message": "build-spec yields zero requirements — wrong file?"})
    owned = set()
    for t in tasks:
        refs = t.get("acceptance_criteria", [])
        if not refs and t.get("kind") not in NO_AC_KINDS:
            v.append({"check": "L3-coverage",
                      "message": "task %s (kind %s) claims zero ACs — untraced work" % (t["id"], t.get("kind"))})
        for ref in refs:
            m = AC_REF_RE.match(str(ref))
            if not m:
                v.append({"check": "L3-coverage", "message": "task %s AC ref '%s' not Rn.k form" % (t["id"], ref)})
                continue
            rid, k = m.group(1), int(m.group(2))
            if rid not in acs:
                v.append({"check": "L3-coverage", "message": "task %s cites unknown requirement %s" % (t["id"], rid)})
            elif not (1 <= k <= acs[rid][1]):
                v.append({"check": "L3-coverage",
                          "message": "task %s cites %s.%d but %s has %d ACs" % (t["id"], rid, k, rid, acs[rid][1])})
            else:
                owned.add("%s.%d" % (rid, k))
    deferred = {}
    for d in tasks_doc.get("deferred", []):
        ac, reason = d.get("ac", ""), str(d.get("reason", "")).strip()
        if not reason:
            v.append({"check": "L3-coverage", "message": "deferred entry '%s' has no reason" % ac})
        deferred[ac] = reason
    for rid, (pri, count) in acs.items():
        for k in range(1, count + 1):
            ref = "%s.%d" % (rid, k)
            if ref in owned:
                continue
            if pri == "must":
                v.append({"check": "L3-coverage", "message": "must AC %s has no owning task" % ref})
            elif ref not in deferred:
                v.append({"check": "L3-coverage",
                          "message": "%s AC %s neither owned nor deferred-with-reason" % (pri or "?", ref)})

    # L4 estimates
    for t in tasks:
        est = t.get("est_hours")
        if not (isinstance(est, (int, float)) and 0 < est <= 4):
            v.append({"check": "L4-estimate",
                      "message": "task %s est_hours %r outside (0, 4]" % (t["id"], est)})

    # L5 test-first
    for t in tasks:
        tf = t.get("test_first")
        if not isinstance(tf, dict):
            v.append({"check": "L5-testfirst", "message": "task %s missing test_first object" % t["id"]})
            continue
        if t.get("kind") in TEST_FIRST_KINDS:
            if tf.get("required") is not True or not str(tf.get("test", "")).strip() \
                    or not str(tf.get("red_assertion", "")).strip():
                v.append({"check": "L5-testfirst",
                          "message": "task %s (kind %s) needs test_first required:true + test + red_assertion"
                                     % (t["id"], t.get("kind"))})
        elif tf.get("required") is False and not str(tf.get("reason", "")).strip():
            v.append({"check": "L5-testfirst",
                      "message": "task %s opts out of test_first with no reason" % t["id"]})

    # L6 files — presence + parallel conflicts
    ancestors = _ancestors(tasks_by_id)
    for t in tasks:
        files = t.get("files", [])
        if not (isinstance(files, list) and files):
            v.append({"check": "L6-files", "message": "task %s lists no files" % t["id"]})
    tids = list(tasks_by_id)
    for i, a in enumerate(tids):
        for b in tids[i + 1:]:
            if a in ancestors.get(b, set()) or b in ancestors.get(a, set()):
                continue  # ordered — sharing files is fine
            shared = set(tasks_by_id[a].get("files", [])) & set(tasks_by_id[b].get("files", []))
            if shared:
                v.append({"check": "L6-files",
                          "message": "parallel tasks %s and %s both touch %s — add a dependency or split"
                                     % (a, b, sorted(shared))})

    # L7 done_when
    for t in tasks:
        if not str(t.get("done_when", "")).strip():
            v.append({"check": "L7-done", "message": "task %s has empty done_when" % t["id"]})

    return {"pass": not v, "violations": v}


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

GOOD_SPEC = {"requirements": [
    {"id": "R1", "priority": "must", "acceptance_criteria": [{}, {}]},
    {"id": "R2", "priority": "should", "acceptance_criteria": [{}]},
]}

GOOD_DOC = {
    "tool": "selftest",
    "generated_from": {"build_spec": "build-spec.json", "design_md": "DESIGN.md"},
    "standing_constraints": ["no accounts"],
    "deferred": [{"ac": "R2.1", "reason": "ships at content stage"}],
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
    ],
}


def _mut(**kw):
    doc = json.loads(json.dumps(GOOD_DOC))
    for path, value in kw.items():
        keys = path.split("__")
        node = doc
        for k in keys[:-1]:
            node = node[int(k)] if k.isdigit() else node[k]
        last = keys[-1]
        if value is None:
            del node[int(last) if last.isdigit() else last]
        else:
            node[int(last) if last.isdigit() else last] = value
    return doc


def selftest():
    failures = []
    res = check(GOOD_DOC, GOOD_SPEC)
    if not res["pass"]:
        failures.append("golden-good FAILED: %s" % res["violations"])

    bads = [
        ("dup-id", _mut(tasks__0__id="T2"), "L1"),
        ("bad-kind", _mut(tasks__1__kind="misc"), "L1"),
        ("unknown-dep", _mut(tasks__1__depends_on=["TX"]), "L2"),
        ("cycle", _mut(tasks__0__depends_on=["T2"]), "L2"),
        ("uncovered-must", _mut(tasks__1__acceptance_criteria=["R1.1"]), "L3"),
        ("out-of-range-ref", _mut(tasks__1__acceptance_criteria=["R1.1", "R1.2", "R1.3"]), "L3"),
        ("deferred-no-reason", _mut(deferred=[{"ac": "R2.1", "reason": ""}]), "L3"),
        ("untraced-ui-task", _mut(tasks__1__kind="ui", tasks__1__acceptance_criteria=[]), "L3"),
        ("est-too-big", _mut(tasks__1__est_hours=6), "L4"),
        ("test-after", _mut(tasks__1__test_first={"required": False, "reason": ""}), "L5"),
        ("no-red-assertion", _mut(tasks__1__test_first={"required": True, "test": "t.ts",
                                                        "red_assertion": ""}), "L5"),
        ("no-files", _mut(tasks__1__files=[]), "L6"),
        ("parallel-file-conflict",
         _mut(tasks__1__depends_on=[], tasks__1__files=["package.json"]), "L6"),
        ("empty-done", _mut(tasks__1__done_when=" "), "L7"),
    ]
    for name, doc, want in bads:
        res = check(doc, GOOD_SPEC)
        if res["pass"]:
            failures.append("golden-bad '%s' PASSED but must FAIL" % name)
        elif not any(viol["check"].startswith(want) for viol in res["violations"]):
            failures.append("golden-bad '%s' failed on %s, expected %s*"
                            % (name, sorted({viol['check'] for viol in res['violations']}), want))

    if check({}, GOOD_SPEC)["pass"]:
        failures.append("invariant: empty doc passed")

    if failures:
        print(json.dumps({"selftest": "FAIL", "failures": failures}, indent=2))
        return 1
    print(json.dumps({"selftest": "PASS",
                      "cases": {"golden_good": 1, "golden_bad": len(bads), "invariants": 1}}))
    return 0


def main(argv):
    if len(argv) == 2 and argv[1] == "--selftest":
        return selftest()
    if len(argv) != 3:
        print("usage: task_lint.py tasks.json build-spec.json | --selftest", file=sys.stderr)
        return 2
    try:
        with open(argv[1], encoding="utf-8") as f:
            tasks_doc = json.load(f)
        with open(argv[2], encoding="utf-8") as f:
            build_spec = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"pass": False, "violations": [{"check": "L0-input", "message": str(e)}]}, indent=2))
        return 2
    result = check(tasks_doc, build_spec)
    result["verdict"] = "PASS" if result["pass"] else "FAIL"
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
