#!/usr/bin/env python3
"""ENGINE TEMPLATE — copy to scripts/<skill-name>_gate.py and adapt.

This is the house fail-closed engine skeleton. The shape is fixed; only the checks
and fixtures change. Rules that are not negotiable:

  * stdlib only — no pip installs, runs anywhere.
  * Exit codes: 0 PASS, 1 FAIL, 2 load/usage error. Nothing else.
  * Fail-closed: anything missing, unparseable, or ambiguous is a FAIL with a
    pointed, fixable message — never a warning, never a silent pass.
  * --selftest builds a golden-good fixture in a temp dir, proves it PASSes, then
    applies one mutation per bad case and proves each is REFUSED (exit 1), then
    runs one invariant (delete/alter something essential, PASS must flip to FAIL).
  * The selftest summary line format is checked by skill_gate.py — keep it EXACTLY:
        SELFTEST RESULT: PASS (<g> good, <b> bad, <i> invariant)
    with g >= 1, b >= 3, i >= 1.
  * TDD order while building: write the bad fixture FIRST, watch the selftest fail
    (the engine doesn't refuse it yet), then write the check that refuses it.

Replace everything marked ADAPT. Delete this docstring's first paragraph block and
write what YOUR engine validates.
"""

import json
import os
import sys
import tempfile

# ---------------------------------------------------------------- helpers


def fail_msgs():
    msgs = []
    return msgs, lambda m: msgs.append(m)


def load_json(path):
    """Return (data, None) or (None, error string). Fail-closed on anything odd."""
    if not os.path.isfile(path):
        return None, f"{path} does not exist"
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f), None
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return None, f"{path} does not parse: {e}"


# ---------------------------------------------------------------- checks
# ADAPT: one function per check, named check_<thing>. Each takes the loaded
# artifact(s) plus the fail() collector. Every fail message says WHAT is wrong
# and WHAT to do about it.


def check_structure(data, fail):
    """C1: required keys exist and have the right shapes."""
    for key in ("name", "items"):  # ADAPT: your required keys
        if key not in data:
            fail(f"C1: required key '{key}' missing")
    if not isinstance(data.get("items"), list) or not data.get("items"):
        fail("C1: 'items' must be a non-empty list")


def check_content(data, fail):
    """C2: ADAPT — the domain rule your skill enforces."""
    for i, item in enumerate(data.get("items", [])):
        if not isinstance(item, dict) or not item.get("evidence"):
            fail(f"C2: items[{i}] has no evidence — paste literal output, "
                 "not a claim")


# ---------------------------------------------------------------- gate


def run_gate(path):
    data, err = load_json(path)
    if err:
        print(f"LOAD ERROR: {err}")
        return 2
    msgs, fail = fail_msgs()
    check_structure(data, fail)
    check_content(data, fail)
    # ADAPT: call every check here. A check not called is a check that lies.
    if msgs:
        for m in msgs:
            print(f"FAIL {m}")
        print(f"GATE RESULT: FAIL ({len(msgs)} problems)")  # ADAPT result label
        return 1
    print("GATE RESULT: PASS")  # ADAPT result label
    return 0


# ---------------------------------------------------------------- selftest

GOOD = {  # ADAPT: the smallest artifact that legitimately passes every check
    "name": "example",
    "items": [{"evidence": "$ run thing\nthing: OK\nexit 0"}],
}


def selftest():
    # ADAPT: one mutation per check failure mode. Name = what's wrong with it.
    bad_cases = {
        "missing-name": lambda d: d.pop("name"),
        "empty-items": lambda d: d.update(items=[]),
        "item-no-evidence": lambda d: d["items"][0].pop("evidence"),
    }

    failures = []
    with tempfile.TemporaryDirectory() as root:
        good_path = os.path.join(root, "good.json")
        with open(good_path, "w", encoding="utf-8") as f:
            json.dump(GOOD, f)
        if run_gate(good_path) != 0:
            failures.append("golden-good fixture did not PASS")

        for case, mutate in bad_cases.items():
            data = json.loads(json.dumps(GOOD))
            mutate(data)
            bad_path = os.path.join(root, f"bad-{case}.json")
            with open(bad_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            if run_gate(bad_path) != 1:
                failures.append(f"bad case '{case}' was not refused")

        # invariant: removing something essential flips PASS -> FAIL.
        # ADAPT: pick the artifact's most load-bearing element.
        data = json.loads(json.dumps(GOOD))
        data["items"] = []
        inv_path = os.path.join(root, "invariant.json")
        with open(inv_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        if run_gate(inv_path) != 1:
            failures.append("invariant: gutting items did not flip to FAIL")

    print()
    if failures:
        for f in failures:
            print(f"SELFTEST FAILURE: {f}")
        print(f"SELFTEST RESULT: FAIL ({len(failures)} problems)")
        return 1
    # The printed counts MUST equal the cases actually executed — keep them
    # derived (len(bad_cases)), never hard-coded. The package gate enforces
    # only the floors (>=1 good, >=3 bad, >=1 invariant); the truth of the
    # numbers is on you, and the reviewer re-runs this line.
    print(f"SELFTEST RESULT: PASS (1 good, {len(bad_cases)} bad, 1 invariant)")
    return 0


def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        return selftest()
    if len(args) != 1:  # ADAPT if your engine takes more arguments
        print(__doc__)
        return 2
    return run_gate(args[0])


if __name__ == "__main__":
    sys.exit(main())
