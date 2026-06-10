#!/usr/bin/env python3
"""design_gate.py — fail-closed house gate for DESIGN.md (design-md skill).

Validates the Build Contract block in a DESIGN.md against the tool's
build-spec.json. Layer 2 of the two-engine check: Google's official linter
(`npx @google/design.md lint`) owns token validity, contrast, and section
order; THIS gate owns the pipeline's house rules:

  C1 front matter present (token layer exists)
  C2 Build Contract block present and parseable (```json under ## Build Contract)
  C3 every must-priority requirement id in build-spec.json is covered
  C4 interaction budget declared, target > 0, estimated <= target
  C5 typed/free-text input modalities carry a non-empty justification
  C6 ad slots reserved (min_height_px >= 50, above_fold false) or an
     ads_excluded_reason is given
  C7 all five states declared (default/empty/error/loading/success)

Fail-closed: a missing block, missing key, or unparseable input is a FAIL,
never a skip. Exit 0 on PASS, 1 on FAIL, 2 on contract/usage error.

Usage:
  python3 design_gate.py DESIGN.md build-spec.json
  python3 design_gate.py --selftest

stdlib only (json, re, sys).
"""

import json
import re
import sys

REQUIRED_STATES = ("default", "empty", "error", "loading", "success")
TYPED_TEXT_RE = re.compile(r"\btyped\b|\bfree[\s_-]?text\b", re.IGNORECASE)


def extract_contract(design_text):
    """Return (contract_dict, error). Finds the first ```json fence after the
    '## Build Contract' heading. Fail-closed on absence or parse error."""
    heading = re.search(r"^##\s+Build Contract\s*$", design_text, re.MULTILINE)
    if not heading:
        return None, "no '## Build Contract' section heading"
    tail = design_text[heading.end():]
    fence = re.search(r"```json\s*\n(.*?)\n```", tail, re.DOTALL)
    if not fence:
        return None, "no ```json fenced block under ## Build Contract"
    try:
        obj = json.loads(fence.group(1))
    except json.JSONDecodeError as e:
        return None, "Build Contract JSON does not parse: %s" % e
    contract = obj.get("design_contract")
    if not isinstance(contract, dict):
        return None, "top-level key 'design_contract' missing or not an object"
    return contract, None


def must_ids(build_spec):
    """Every requirement id whose priority (or tier) is 'must'."""
    ids = []
    for req in build_spec.get("requirements", []):
        pri = str(req.get("priority", req.get("tier", ""))).strip().lower()
        rid = req.get("id")
        if rid and pri == "must":
            ids.append(rid)
    return ids


def check(design_text, build_spec):
    """Run all checks. Returns dict {pass, violations:[{check,message}]}."""
    v = []

    # C1 front matter (token layer) present
    if not design_text.lstrip().startswith("---"):
        v.append({"check": "C1-frontmatter",
                  "message": "file does not start with a YAML front-matter fence (token layer missing)"})

    # C2 contract block
    contract, err = extract_contract(design_text)
    if contract is None:
        v.append({"check": "C2-contract", "message": err})
        return {"pass": False, "violations": v}

    # C3 must-requirement coverage
    coverage = contract.get("requirement_coverage")
    if not isinstance(coverage, dict):
        v.append({"check": "C3-coverage", "message": "requirement_coverage missing or not an object"})
    else:
        musts = must_ids(build_spec)
        if not musts:
            v.append({"check": "C3-coverage",
                      "message": "build-spec.json yields zero must-priority requirement ids — wrong file or wrong schema"})
        for rid in musts:
            refs = coverage.get(rid)
            if not (isinstance(refs, list) and refs and all(isinstance(r, str) and r.startswith("#") for r in refs)):
                v.append({"check": "C3-coverage",
                          "message": "must requirement %s has no non-empty list of #section refs" % rid})

    # C4 interaction budget
    budget = contract.get("interaction_budget")
    if not isinstance(budget, dict):
        v.append({"check": "C4-budget", "message": "interaction_budget missing or not an object"})
    else:
        tgt, est = budget.get("target"), budget.get("estimated")
        if not (isinstance(tgt, (int, float)) and tgt > 0):
            v.append({"check": "C4-budget", "message": "interaction_budget.target must be a number > 0"})
        if not isinstance(est, (int, float)):
            v.append({"check": "C4-budget", "message": "interaction_budget.estimated must be a number"})
        elif isinstance(tgt, (int, float)) and est > tgt:
            v.append({"check": "C4-budget",
                      "message": "estimated (%s) exceeds target (%s) — tune accelerators, not the budget" % (est, tgt)})

    # C5 input modalities — typed/free-text needs justification
    modalities = contract.get("input_modalities")
    if not isinstance(modalities, dict) or not modalities:
        v.append({"check": "C5-modality", "message": "input_modalities missing or empty"})
    else:
        for field, val in modalities.items():
            if isinstance(val, str):
                modality, justification = val, ""
            elif isinstance(val, dict):
                modality = str(val.get("modality", ""))
                justification = str(val.get("justification", "")).strip()
            else:
                v.append({"check": "C5-modality", "message": "field '%s' has invalid modality entry" % field})
                continue
            if TYPED_TEXT_RE.search(modality) and not justification:
                v.append({"check": "C5-modality",
                          "message": "field '%s' uses typed/free-text with no justification (IRON LAW 4)" % field})

    # C6 ad slots
    slots = contract.get("ad_slots")
    excluded = str(contract.get("ads_excluded_reason", "")).strip()
    if isinstance(slots, list) and slots:
        for slot in slots:
            sid = slot.get("id", "?") if isinstance(slot, dict) else "?"
            if not isinstance(slot, dict):
                v.append({"check": "C6-ads", "message": "ad slot entry is not an object"})
                continue
            mh = slot.get("min_height_px")
            if not (isinstance(mh, (int, float)) and mh >= 50):
                v.append({"check": "C6-ads", "message": "ad slot %s min_height_px missing or < 50 (CLS)" % sid})
            if slot.get("above_fold") is not False:
                v.append({"check": "C6-ads",
                          "message": "ad slot %s must declare above_fold: false (IRON LAW 5)" % sid})
    elif not excluded:
        v.append({"check": "C6-ads",
                  "message": "ad_slots missing/empty and no ads_excluded_reason given"})

    # C7 states
    states = contract.get("states")
    if not isinstance(states, dict):
        v.append({"check": "C7-states", "message": "states missing or not an object"})
    else:
        for key in REQUIRED_STATES:
            val = states.get(key)
            if not (isinstance(val, str) and val.strip()):
                v.append({"check": "C7-states", "message": "state '%s' missing or empty" % key})

    return {"pass": not v, "violations": v}


# ---------------------------------------------------------------------------
# Selftest — golden-good must PASS, every golden-bad must FAIL on its check.
# ---------------------------------------------------------------------------

GOOD_SPEC = {"requirements": [
    {"id": "R1", "priority": "must"},
    {"id": "R2", "priority": "must"},
    {"id": "R3", "priority": "should"},
]}

GOOD_CONTRACT = {
    "design_contract": {
        "requirement_coverage": {"R1": ["#components"], "R2": ["#layout", "#states"]},
        "interaction_budget": {"canonical_job": "enter week", "target": 15, "estimated": 9,
                               "trace": "3+3+2+1"},
        "input_modalities": {
            "time_in": "native-time-picker",
            "notes": {"modality": "typed-free-text",
                      "justification": "unstructured prose field; Pillar 11 quotes show users expect a notes box"},
        },
        "ad_slots": [{"id": "A", "position": "after-tool", "min_height_px": 280, "above_fold": False}],
        "states": {"default": "#states", "empty": "#states", "error": "#states",
                   "loading": "n/a — sync compute", "success": "#states"},
    }
}


def _design_doc(contract):
    return ("---\nname: Selftest\ncolors:\n  primary: \"#111111\"\n---\n\n"
            "## Overview\nx\n\n## Build Contract\n\n```json\n%s\n```\n"
            % json.dumps(contract, indent=2))


def _mutate(path, value):
    doc = json.loads(json.dumps(GOOD_CONTRACT))  # deep copy
    node = doc["design_contract"]
    keys = path.split(".")
    for k in keys[:-1]:
        node = node[k]
    if value is None:
        del node[keys[-1]]
    else:
        node[keys[-1]] = value
    return doc


def selftest():
    failures = []

    res = check(_design_doc(GOOD_CONTRACT), GOOD_SPEC)
    if not res["pass"]:
        failures.append("golden-good FAILED: %s" % res["violations"])

    bad_cases = [
        ("missing-contract-heading", "## Overview\nno contract here\n", GOOD_SPEC, "C2"),
        ("no-frontmatter", _design_doc(GOOD_CONTRACT).split("---\n", 2)[2], GOOD_SPEC, "C1"),
        ("uncovered-must", _design_doc(_mutate("requirement_coverage", {"R1": ["#components"]})), GOOD_SPEC, "C3"),
        ("budget-exceeded", _design_doc(_mutate("interaction_budget.estimated", 22)), GOOD_SPEC, "C4"),
        ("typed-text-no-justification",
         _design_doc(_mutate("input_modalities.notes", "typed-free-text")), GOOD_SPEC, "C5"),
        ("freetext-no-justification",
         _design_doc(_mutate("input_modalities.notes", "free_text")), GOOD_SPEC, "C5"),
        ("ad-above-fold",
         _design_doc(_mutate("ad_slots", [{"id": "A", "position": "hero", "min_height_px": 280,
                                           "above_fold": True}])), GOOD_SPEC, "C6"),
        ("missing-state", _design_doc(_mutate("states.error", None)), GOOD_SPEC, "C7"),
    ]
    for name, doc, spec, want in bad_cases:
        res = check(doc if isinstance(doc, str) else _design_doc(doc), spec)
        if res["pass"]:
            failures.append("golden-bad '%s' PASSED but must FAIL" % name)
        elif not any(viol["check"].startswith(want) for viol in res["violations"]):
            failures.append("golden-bad '%s' failed on %s, expected %s*"
                            % (name, [viol["check"] for viol in res["violations"]], want))

    # structural invariant: gate never passes an empty document
    if check("", GOOD_SPEC)["pass"]:
        failures.append("invariant: empty document passed")

    if failures:
        print(json.dumps({"selftest": "FAIL", "failures": failures}, indent=2))
        return 1
    print(json.dumps({"selftest": "PASS",
                      "cases": {"golden_good": 1, "golden_bad": len(bad_cases), "invariants": 1}}))
    return 0


def main(argv):
    if len(argv) == 2 and argv[1] == "--selftest":
        return selftest()
    if len(argv) != 3:
        print("usage: design_gate.py DESIGN.md build-spec.json | --selftest", file=sys.stderr)
        return 2
    try:
        with open(argv[1], encoding="utf-8") as f:
            design_text = f.read()
        with open(argv[2], encoding="utf-8") as f:
            build_spec = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"pass": False, "violations": [
            {"check": "C0-input", "message": str(e)}]}, indent=2))
        return 2
    result = check(design_text, build_spec)
    result["verdict"] = "PASS" if result["pass"] else "FAIL"
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
