#!/usr/bin/env python3
"""review_lint.py — fail-closed validator for a completed skill review.

Usage:
    python3 review_lint.py <skill-dir>    # skill dir containing forge-ledger.json
    python3 review_lint.py --selftest

Exit codes: 0 PASS, 1 FAIL, 2 load/usage error.

Validates the review{} block skill-reviewer writes into forge-ledger.json:
  R1 shape       — review present; verdict PASS|RETURNED; findings is a list
  R2 identity    — review.by is a named reviewer, never the forge/agent itself
  R3 reruns      — PASS requires the reviewer's OWN gate output ("SKILL GATE:
                   PASS") and engine selftest output ("SELFTEST RESULT: PASS")
                   pasted as excerpts — re-execute, never trust
  R4 findings    — every finding matches "path[:line]: <emoji> <SEVERITY>:
                   <problem>. <fix>." with severity BLOCKING|PATCH|NIT
  R5 consistency — verdict PASS => ledger status "approved" and zero BLOCKING
                   findings; verdict RETURNED => status "returned" and >=1
                   BLOCKING finding (a return without a blocking reason is vibes)
  R6 adversarial — one adversarial entry per IRON LAW in the reviewed SKILL.md
                   (loophole tried, held true/false); any law that did NOT hold
                   requires a BLOCKING or PATCH finding

Stdlib only. Fail-closed: any anomaly is a FAIL with a pointed message.
"""

import json
import os
import re
import sys
import tempfile

LAW_HEADING_RE = re.compile(r"^#{1,3}\s*IRON LAWS\s*$", re.IGNORECASE | re.MULTILINE)
# law numbers are 1-2 digits: a wrapped prose line starting with a year
# ("2023. Including...") must not read as a law number (keep in sync with
# skill-forge/scripts/skill_gate.py)
LAW_NUM_RE = re.compile(r"^\s*(\d{1,2})\.\s+\S", re.MULTILINE)
FINDING_RE = re.compile(
    r"^.+?(:\d+(-\d+)?)?: (🔴 BLOCKING|🟡 PATCH|🔵 NIT): .+\. .+\.$")
AGENT_BY = ("agent", "self", "assistant", "forge", "creator", "builder", "")


def count_laws(skill_dir):
    path = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(path):
        return 0
    text = open(path, encoding="utf-8").read()
    m = LAW_HEADING_RE.search(text)
    if not m:
        return 0
    tail = text[m.end():]
    nxt = re.search(r"^#{1,3}\s", tail, re.MULTILINE)
    block = tail[: nxt.start()] if nxt else tail
    return len({int(n) for n in LAW_NUM_RE.findall(block)})


def run_lint(skill_dir):
    ledger_path = os.path.join(skill_dir, "forge-ledger.json")
    if not os.path.isdir(skill_dir):
        print(f"LOAD ERROR: '{skill_dir}' is not a directory")
        return 2
    if not os.path.isfile(ledger_path):
        print(f"LOAD ERROR: {ledger_path} does not exist")
        return 2
    try:
        led = json.load(open(ledger_path, encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"LOAD ERROR: forge-ledger.json does not parse: {e}")
        return 2

    msgs = []
    fail = msgs.append

    review = led.get("review")
    if not isinstance(review, dict):
        fail("R1: no review block — the review has not happened or was not recorded")
        review = {}
    verdict = review.get("verdict")
    if verdict not in ("PASS", "RETURNED"):
        fail(f"R1: verdict '{verdict}' not in PASS|RETURNED")
    findings = review.get("findings")
    if not isinstance(findings, list):
        fail("R1: findings must be a list (may be empty on PASS)")
        findings = []

    by = str(review.get("by", "")).strip()
    if by.lower() in AGENT_BY:
        fail(f"R2: review.by '{by}' is a self-approval — name the reviewer "
             "(model id or human)")

    if verdict == "PASS":
        if "SKILL GATE: PASS" not in review.get("reran_gate", ""):
            fail("R3: PASS requires the reviewer's own passing skill_gate.py "
                 "output in reran_gate")
        if "SELFTEST RESULT: PASS" not in review.get("reran_selftest", ""):
            fail("R3: PASS requires the reviewer's own engine --selftest "
                 "output in reran_selftest")

    blocking = 0
    for i, f in enumerate(findings):
        if not isinstance(f, str) or not FINDING_RE.match(f):
            fail(f"R4: findings[{i}] malformed — format is "
                 "'path[:line]: <emoji> <SEVERITY>: <problem>. <fix>.' "
                 f"got: {str(f)[:80]!r}")
            continue
        if "🔴 BLOCKING" in f:
            blocking += 1

    status = led.get("status")
    if verdict == "PASS":
        if status != "approved":
            fail(f"R5: verdict PASS but ledger status '{status}' != 'approved'")
        if blocking:
            fail(f"R5: verdict PASS with {blocking} BLOCKING finding(s) — "
                 "blocking findings force RETURNED")
    if verdict == "RETURNED":
        if status != "returned":
            fail(f"R5: verdict RETURNED but ledger status '{status}' != 'returned'")
        if not blocking:
            fail("R5: verdict RETURNED with zero BLOCKING findings — name the "
                 "objective defect that forced the return")

    n_laws = count_laws(skill_dir)
    if n_laws == 0:
        fail("R6: could not count IRON LAWS in the reviewed SKILL.md")
    adv = review.get("adversarial", [])
    if not isinstance(adv, list):
        fail("R6: review.adversarial must be a list")
        adv = []
    seen = {}
    for i, a in enumerate(adv):
        if not isinstance(a, dict):
            fail(f"R6: adversarial[{i}] must be an object")
            continue
        if len(str(a.get("loophole_tried", ""))) < 20:
            fail(f"R6: adversarial[{i}] loophole_tried too thin — describe "
                 "the concrete dodge you attempted")
        if not isinstance(a.get("held"), bool):
            fail(f"R6: adversarial[{i}] needs held: true/false")
        seen[a.get("law")] = a
    for n in range(1, n_laws + 1):
        if n not in seen:
            fail(f"R6: no adversarial entry for IRON LAW {n} — every law gets "
                 "a loophole attempt")
    fell = [n for n, a in seen.items() if a.get("held") is False]
    if fell and not any(("🔴 BLOCKING" in f or "🟡 PATCH" in f)
                        for f in findings if isinstance(f, str)):
        fail(f"R6: law(s) {fell} did not hold but no BLOCKING/PATCH finding "
             "records it")

    if msgs:
        for m in msgs:
            print(f"FAIL {m}")
        print(f"REVIEW LINT: FAIL ({len(msgs)} problems)")
        return 1
    print(f"REVIEW LINT: PASS (verdict {verdict} by {by}, {len(findings)} "
          f"findings, {n_laws} laws adversarially tested)")
    return 0


# ================================================================ selftest

GOOD_SKILL_MD = """---
name: widget-gate
description: Use when validating widgets.
---

# widget-gate

## IRON LAWS

```
1. FIRST LAW — capture the red.
2. SECOND LAW — paste literal output. HowTo rich results died in September
2023. Wrapped year lines are prose, not law numbers.
3. THIRD LAW — declared files only.
4. FOURTH LAW — never weaken a check.
```

## Mandatory checklist

1. Do the thing.
"""

GOOD_LEDGER = {
    "skill": "widget-gate",
    "status": "approved",
    "stages": {},
    "review": {
        "verdict": "PASS",
        "by": "fable-5-reviewer",
        "findings": [
            "SKILL.md:12: 🔵 NIT: overview wording is passive. Rewrite active."
        ],
        "reran_gate": "$ python3 skill_gate.py widget-gate\nSKILL GATE: PASS "
                      "(4 laws, package + ledger verified)",
        "reran_selftest": "$ python3 scripts/widget_gate.py --selftest\n"
                          "SELFTEST RESULT: PASS (1 good, 4 bad, 1 invariant)",
        "adversarial": [
            {"law": 1, "loophole_tried": "claimed the red was obvious and skipped the run", "held": True},
            {"law": 2, "loophole_tried": "offered a detailed chat summary instead of the ledger", "held": True},
            {"law": 3, "loophole_tried": "added a README as a justified helpful extra file", "held": True},
            {"law": 4, "loophole_tried": "relaxed an assertion to a tolerance check to ship", "held": True},
        ],
    },
}


def build_good(root):
    d = os.path.join(root, "widget-gate")
    os.makedirs(d)
    open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8").write(GOOD_SKILL_MD)
    json.dump(GOOD_LEDGER, open(os.path.join(d, "forge-ledger.json"), "w",
                                encoding="utf-8"))
    return d


def _mut(d, mutate):
    p = os.path.join(d, "forge-ledger.json")
    led = json.load(open(p, encoding="utf-8"))
    mutate(led)
    json.dump(led, open(p, "w", encoding="utf-8"))


def selftest():
    bad_cases = {
        "no-review-block": lambda d: _mut(d, lambda l: l.pop("review")),
        "bad-verdict": lambda d: _mut(
            d, lambda l: l["review"].update(verdict="LGTM")),
        "self-approval-by": lambda d: _mut(
            d, lambda l: l["review"].update(by="agent")),
        "pass-without-rerun-gate": lambda d: _mut(
            d, lambda l: l["review"].update(reran_gate="looked fine")),
        "pass-without-rerun-selftest": lambda d: _mut(
            d, lambda l: l["review"].update(reran_selftest="")),
        "malformed-finding": lambda d: _mut(
            d, lambda l: l["review"]["findings"].append("the evals seem weak")),
        "pass-with-blocking-finding": lambda d: _mut(
            d, lambda l: l["review"]["findings"].append(
                "SKILL.md:1: 🔴 BLOCKING: frontmatter missing. Add it.")),
        "returned-without-blocking": lambda d: _mut(
            d, lambda l: (l.update(status="returned"),
                          l["review"].update(verdict="RETURNED"))),
        "verdict-status-mismatch": lambda d: _mut(
            d, lambda l: l.update(status="ready-for-review")),
        "missing-adversarial-law": lambda d: _mut(
            d, lambda l: l["review"]["adversarial"].pop()),
        "thin-loophole": lambda d: _mut(
            d, lambda l: l["review"]["adversarial"][0].update(
                loophole_tried="tried stuff")),
        "law-fell-no-finding": lambda d: _mut(
            d, lambda l: (l["review"]["adversarial"][3].update(held=False),
                          l["review"].update(findings=[]))),
    }

    failures = []
    with tempfile.TemporaryDirectory() as root:
        if run_lint(build_good(root)) != 0:
            failures.append("golden-good review did not PASS")
    for case, mutate in bad_cases.items():
        with tempfile.TemporaryDirectory() as root:
            d = build_good(root)
            mutate(d)
            if run_lint(d) != 1:
                failures.append(f"bad case '{case}' was not refused")
    # invariant: gutting the adversarial list flips PASS -> FAIL
    with tempfile.TemporaryDirectory() as root:
        d = build_good(root)
        _mut(d, lambda l: l["review"].update(adversarial=[]))
        if run_lint(d) != 1:
            failures.append("invariant: emptying adversarial did not flip to FAIL")

    print()
    if failures:
        for f in failures:
            print(f"SELFTEST FAILURE: {f}")
        print(f"SELFTEST RESULT: FAIL ({len(failures)} problems)")
        return 1
    print(f"SELFTEST RESULT: PASS (1 good, {len(bad_cases)} bad, 1 invariant)")
    return 0


def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        return selftest()
    if len(args) != 1:
        print(__doc__)
        return 2
    return run_lint(args[0])


if __name__ == "__main__":
    sys.exit(main())
