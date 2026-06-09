#!/usr/bin/env python3
"""prd_lint.py — fail-closed validator for projects-prd-generator PRDs.

Deep, data-level checks run against the structured build-spec.json.
PRD.md is checked only for section presence + requirement-id agreement.
Fail-closed: missing/malformed input raises ContractError (exit 2).

Usage:
    python3 prd_lint.py <prd.md> <build-spec.json>   # exit 0 PASS / 1 FAIL / 2 ContractError
    python3 prd_lint.py --selftest                    # exit 0 if all fixtures meet expectations
"""
import json
import re
import sys

REQUIRED_SECTIONS = [
    "Exec Summary", "Goal & Success Metrics", "Background & Evidence",
    "Personas & Jobs-to-be-Done", "Scope", "Functional Requirements",
    "UI/UX Spec", "Benchmarks", "Monetization & Constraints",
    "Analytics & Instrumentation", "Assumptions & Open Questions",
    "Risks & Mitigations", "Milestones / Definition of Done",
    "Traceability Appendix",
]
WEAK_TIERS = {"reasoned", "unverified", "hypothesis"}
BANNED_ADJECTIVES = {"fast", "accessible", "clean", "intuitive", "snappy",
                     "modern", "beautiful", "seamless", "blazing", "easy"}
REQ_ID_RE = re.compile(r"\bR\d+\b")
NUM_RE = re.compile(r"\d")


class ContractError(Exception):
    """Raised when input is missing/malformed — fail closed."""


def _v(law, section, item_id, message):
    return {"law": law, "section": section, "item_id": item_id, "message": message}


def _sections(prd_text):
    blocks = re.split(r"^##\s+(.*)$", prd_text, flags=re.MULTILINE)
    headers = {}
    for i in range(1, len(blocks), 2):
        name = blocks[i].strip()
        body = blocks[i + 1] if i + 1 < len(blocks) else ""
        headers[name] = body.strip()
    return headers


def check_completeness(prd_text):
    """All 14 required sections present and non-empty (supports LAW 5)."""
    violations = []
    headers = _sections(prd_text)
    for sec in REQUIRED_SECTIONS:
        match = next((h for h in headers if h.lower().startswith(sec.lower())), None)
        if match is None:
            violations.append(_v("completeness", sec, None, f"missing section: {sec}"))
        elif not headers[match]:
            violations.append(_v("completeness", sec, None, f"empty section: {sec}"))
    return violations


def check_scope(spec):
    """LAW 4: three-sided scope — do / wont_do / skipped all present and non-empty."""
    scope = spec.get("scope")
    if not isinstance(scope, dict):
        return [_v("4-scope", "scope", None, "scope missing or not an object")]
    violations = []
    for side in ("do", "wont_do", "skipped"):
        if not scope.get(side):
            violations.append(_v("4-scope", "scope", side,
                               f"scope.{side} is empty — scope must be three-sided"))
    return violations


def _is_measurable(c):
    """Measurable = numeric value + unit + metric, OR a non-empty boolean predicate."""
    if not isinstance(c, dict):
        return False
    if c.get("predicate"):
        return isinstance(c["predicate"], str)
    return (isinstance(c.get("value"), (int, float))
            and bool(c.get("unit")) and bool(c.get("metric")))


def check_requirements(spec):
    """LAW 1 (traceability), LAW 2 (tier-gating), LAW 3 (measurability)."""
    reqs = spec.get("requirements")
    if not isinstance(reqs, list) or not reqs:
        return [_v("1-traceability", "requirements", None, "requirements missing or empty")]
    owned = {q.get("item") for q in spec.get("open_questions", []) if q.get("owner")}
    violations = []
    for r in reqs:
        rid = r.get("id", "?")
        tier = (r.get("evidence_tier") or "").lower()
        priority = (r.get("priority") or "").lower()
        if not r.get("source_ref"):
            if tier == "assumption":
                if rid not in owned and r.get("statement") not in owned:
                    violations.append(_v("1-traceability", "requirements", rid,
                        "ASSUMPTION requirement has no owner in open_questions"))
            else:
                violations.append(_v("1-traceability", "requirements", rid,
                    "requirement has no source_ref and is not tagged assumption"))
        if priority == "must" and tier in WEAK_TIERS:
            violations.append(_v("2-tier-gating", "requirements", rid,
                f"v1 must-have rests on '{tier}' evidence — only v2/open-question allowed"))
        if priority in ("must", "should"):
            crits = r.get("acceptance_criteria") or []
            if not crits:
                violations.append(_v("3-measurability", "requirements", rid,
                    "requirement has no acceptance_criteria"))
            for c in crits:
                if not _is_measurable(c):
                    violations.append(_v("3-measurability", "requirements", rid,
                        f"acceptance criterion not measurable: {c}"))
    return violations


def check_banned_adjectives(prd_text):
    """LAW 3 prose guard: banned adjective in Requirements/Benchmarks with no number on the line."""
    violations = []
    in_scope = False
    for line in prd_text.splitlines():
        m = re.match(r"^##\s+(.*)$", line)
        if m:
            name = m.group(1).strip().lower()
            in_scope = name.startswith("functional requirements") or name.startswith("benchmarks")
            continue
        if in_scope and not NUM_RE.search(line):
            low = line.lower()
            for adj in BANNED_ADJECTIVES:
                if re.search(r"\b" + adj + r"\b", low):
                    violations.append(_v("3-measurability", "prose", None,
                        f"unmeasurable adjective '{adj}' without a number: {line.strip()[:80]}"))
                    break
    return violations


def check_agreement(prd_text, spec):
    """LAW 5 structural: requirement ids in the PRD Functional Requirements section == build-spec ids."""
    spec_ids = {r.get("id") for r in spec.get("requirements", []) if r.get("id")}
    prd_ids, in_reqs = set(), False
    for line in prd_text.splitlines():
        m = re.match(r"^##\s+(.*)$", line)
        if m:
            in_reqs = m.group(1).strip().lower().startswith("functional requirements")
            continue
        if in_reqs:
            prd_ids.update(REQ_ID_RE.findall(line))
    if spec_ids != prd_ids:
        return [_v("5-agreement", "requirements", None,
            f"PRD<->build-spec id drift: missing_in_prd={sorted(spec_ids - prd_ids)} "
            f"missing_in_spec={sorted(prd_ids - spec_ids)}")]
    return []


def lint(prd_text, spec):
    """Run all checks; return (passed, violations). Fail-closed on bad spec."""
    if not isinstance(spec, dict):
        raise ContractError("build-spec is not a JSON object")
    violations = []
    violations += check_completeness(prd_text)
    violations += check_scope(spec)
    violations += check_requirements(spec)
    violations += check_banned_adjectives(prd_text)
    violations += check_agreement(prd_text, spec)
    return (len(violations) == 0, violations)


# ---------------------------------------------------------------- fixtures ---
def _good_prd():
    body = "Real content here with a number 1100ms.\n"
    return "# PRD\n\n" + "".join(f"## {s}\n\n{body}\n" for s in REQUIRED_SECTIONS) \
        + "## Functional Requirements\n\nR1 does the thing.\n"


def _good_spec():
    return {
        "tool": "demo", "prd_version": "1.0",
        "scope": {"do": ["x"], "wont_do": ["y"], "skipped": [{"item": "z", "reason": "later"}]},
        "requirements": [
            {"id": "R1", "priority": "must", "statement": "labeled inputs",
             "source_ref": "gaps.json#a11y", "evidence_tier": "real-measured",
             "acceptance_criteria": [{"metric": "lighthouse_a11y", "op": ">=", "value": 95, "unit": "score"}]},
        ],
        "open_questions": [],
    }


def _selftest():
    cases = []
    # GOOD must pass
    cases.append(("good", _good_prd(), _good_spec(), True, None))
    # BAD: missing a section
    bad_prd = _good_prd().replace("## Risks & Mitigations\n\nReal content here with a number 1100ms.\n\n", "")
    cases.append(("missing_section", bad_prd, _good_spec(), False, "completeness"))
    # BAD: scope missing wont_do
    bad_spec = json.loads(json.dumps(_good_spec()))
    bad_spec["scope"]["wont_do"] = []
    cases.append(("scope_no_wontdo", _good_prd(), bad_spec, False, "4-scope"))
    # BAD: must-have on hypothesis tier (LAW 2)
    s2 = json.loads(json.dumps(_good_spec()))
    s2["requirements"][0]["evidence_tier"] = "hypothesis"
    cases.append(("musthave_hypothesis", _good_prd(), s2, False, "2-tier-gating"))
    # BAD: unmeasurable acceptance criterion (LAW 3)
    s3 = json.loads(json.dumps(_good_spec()))
    s3["requirements"][0]["acceptance_criteria"] = [{"metric": "ux", "op": "is", "value": "good", "unit": ""}]
    cases.append(("unmeasurable", _good_prd(), s3, False, "3-measurability"))
    # BAD: requirement with no source_ref and not an assumption (LAW 1)
    s4 = json.loads(json.dumps(_good_spec()))
    s4["requirements"][0]["source_ref"] = ""
    cases.append(("untraceable", _good_prd(), s4, False, "1-traceability"))
    # BAD: banned adjective without a number (LAW 3 prose guard)
    bad_prose = _good_prd().replace("R1 does the thing.", "It must be blazing and beautiful.")
    cases.append(("banned_adjective", bad_prose, _good_spec(), False, "3-measurability"))
    # BAD: PRD<->spec requirement-id drift (LAW 5)
    s5 = json.loads(json.dumps(_good_spec()))
    s5["requirements"].append({"id": "R2", "priority": "must", "statement": "csv export",
        "source_ref": "gaps.json#csv", "evidence_tier": "triangulated",
        "acceptance_criteria": [{"metric": "csv_export", "op": "==", "value": 1, "unit": "bool"}]})
    cases.append(("id_drift", _good_prd(), s5, False, "5-agreement"))

    failed = []
    laws_seen = set()
    for name, prd, spec, want_pass, want_law in cases:
        passed, violations = lint(prd, spec)
        if passed != want_pass:
            failed.append(f"{name}: expected pass={want_pass}, got {passed} ({violations})")
        if want_law:
            laws_seen.add(want_law)
            if not any(want_law in v["law"] for v in violations):
                failed.append(f"{name}: expected a '{want_law}' violation, got {violations}")

    expected_laws = {"completeness", "4-scope", "1-traceability", "2-tier-gating",
                     "3-measurability", "5-agreement"}
    if not expected_laws.issubset(laws_seen):
        failed.append(f"structural: missing bad-fixture coverage for {sorted(expected_laws - laws_seen)}")

    if failed:
        print("SELFTEST FAILED:")
        for f in failed:
            print("  -", f)
        return 1
    print(f"SELFTEST PASSED — {len(cases)} fixtures, laws covered: {sorted(laws_seen)}")
    return 0


def _main(argv):
    if len(argv) == 1 and argv[0] == "--selftest":
        return _selftest()
    if len(argv) != 2:
        print(__doc__)
        return 2
    try:
        with open(argv[0], encoding="utf-8") as fh:
            prd_text = fh.read()
        with open(argv[1], encoding="utf-8") as fh:
            spec = json.load(fh)
        passed, violations = lint(prd_text, spec)
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(str(exc))
    result = {"passed": passed, "violations": violations}
    print(json.dumps(result, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    try:
        sys.exit(_main(sys.argv[1:]))
    except ContractError as exc:
        print(f"ContractError: {exc}", file=sys.stderr)
        sys.exit(2)
