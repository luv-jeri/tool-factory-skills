#!/usr/bin/env python3
"""skill_gate.py — fail-closed validator for a house skill package + forge ledger.

Usage:
    python3 skill_gate.py <skill-dir>            # validate package (forge-ledger.json inside)
    python3 skill_gate.py --selftest             # prove the gate refuses duds

Exit codes: 0 PASS, 1 FAIL, 2 load/usage error.

Validates the package skill-forge produces and skill-reviewer consumes:
  F1 layout      — required files present, NO sprawl (only SKILL.md, scripts/,
                   references/, evals/, assets/, forge-ledger.json allowed)
  F2 frontmatter — YAML block first, name matches dir + slug rules, description
                   starts "Use when", third person, <=1024 chars, body <=500 lines
  F3 sections    — Overview, IRON LAWS (>=4 numbered), dot digraph, checklist,
                   rationalization table, red flags
  F4 engine      — >=1 scripts/*.py advertising --selftest; gate EXECUTES it and
                   requires "SELFTEST RESULT: PASS (g good, b bad, i invariant)"
                   with g>=1, b>=3, i>=1
  F5 evals       — evals/evals.json: skill name matches, notes document the
                   baseline, eval count >= law count, every law cited in asserts
  F6 ledger      — forge-ledger.json: all build stages done with literal evidence,
                   law origins recorded, no self-approval (PASS verdict needs a
                   reviewer identity + reran gate/selftest excerpts)
  F7 residue     — no unfilled template slots ("{{") anywhere in the package

Stdlib only. Fail-closed: any anomaly is a FAIL with a pointed message.
"""

import json
import os
import re
import subprocess
import sys
import tempfile

LAW_HEADING_RE = re.compile(r"^#{1,3}\s*IRON LAWS\s*$", re.IGNORECASE | re.MULTILINE)
# law numbers are 1-2 digits: a wrapped prose line starting with a year
# ("2023. Including...") must not read as a law number (hit live by the
# seo-content forge, which saw laws [1..6, 2023])
LAW_NUM_RE = re.compile(r"^\s*(\d{1,2})\.\s+\S", re.MULTILINE)
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
SELFTEST_RE = re.compile(
    r"SELFTEST RESULT: PASS \((\d+) good, (\d+) bad, (\d+) invariant\)"
)
LAW_CITE_TMPL = r"IRON LAWS?\s+(?:\d+(?:\s*(?:,|and|&)\s*)+)*{n}\b"
AGENT_BY = ("agent", "self", "assistant", "forge", "creator", "builder", "")
ALLOWED_TOP = {"SKILL.md", "scripts", "references", "evals", "assets",
               "forge-ledger.json", ".gitignore"}
REQUIRED_STAGES = ("baseline", "engine_selftest", "skill_md", "evals",
                   "self_gate", "green_check")
ORIGINS = ("baseline-failure", "house-standard")


def fail_msgs():
    msgs = []
    return msgs, lambda m: msgs.append(m)


# ---------------------------------------------------------------- F2 helper
def parse_frontmatter(text):
    """Return (dict, body) or (None, reason)."""
    if not text.startswith("---\n"):
        return None, "SKILL.md does not start with a '---' YAML frontmatter block"
    end = text.find("\n---", 4)
    if end == -1:
        return None, "frontmatter block never closes with '---'"
    block = text[4:end]
    body = text[end + 4:]
    fm = {}
    key = None
    for line in block.splitlines():
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if m:
            key = m.group(1)
            fm[key] = m.group(2).strip().strip('"').strip("'")
        elif key and (line.startswith("  ") or line.startswith("\t")):
            fm[key] = (fm[key] + " " + line.strip()).strip()
    return fm, body


# ---------------------------------------------------------------- checks
def check_layout(skill_dir, fail):
    if not os.path.isfile(os.path.join(skill_dir, "SKILL.md")):
        fail("F1: SKILL.md missing")
    for entry in sorted(os.listdir(skill_dir)):
        if entry not in ALLOWED_TOP:
            fail(f"F1: stray top-level entry '{entry}' — package sprawl; allowed: "
                 "SKILL.md, scripts/, references/, evals/, assets/, forge-ledger.json")
    scripts = os.path.join(skill_dir, "scripts")
    if not (os.path.isdir(scripts)
            and any(f.endswith(".py") for f in os.listdir(scripts))):
        fail("F1: scripts/ must contain at least one .py engine")
    if not os.path.isfile(os.path.join(skill_dir, "evals", "evals.json")):
        fail("F1: evals/evals.json missing")
    if not os.path.isfile(os.path.join(skill_dir, "forge-ledger.json")):
        fail("F1: forge-ledger.json missing (the ledger IS the build)")


def check_frontmatter(skill_dir, fail):
    path = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(path):
        return None
    text = open(path, encoding="utf-8").read()
    fm, body = parse_frontmatter(text)
    if fm is None:
        fail(f"F2: {body}")
        return None
    name = fm.get("name", "")
    desc = fm.get("description", "")
    dirname = os.path.basename(os.path.abspath(skill_dir))
    if not name:
        fail("F2: frontmatter missing 'name'")
    elif not NAME_RE.match(name):
        fail(f"F2: name '{name}' violates slug rules [a-z0-9-]")
    elif name != dirname:
        fail(f"F2: name '{name}' != directory '{dirname}'")
    if not desc:
        fail("F2: frontmatter missing 'description'")
    else:
        if not desc.startswith("Use when"):
            fail("F2: description must start with 'Use when' (trigger-only CSO)")
        if len(desc) > 1024:
            fail(f"F2: description {len(desc)} chars > 1024 limit")
        if re.search(r"\bI\b|\bI'll\b|\bmy\b", desc):
            fail("F2: description must be third person (found first-person pronoun)")
        if "do not use" not in desc.lower():
            fail("F2: description must end with a 'Do not use for ...' clause "
                 "naming the nearest tempting non-use (anti-overtrigger)")
    body_lines = body.count("\n") + 1
    if body_lines > 500:
        fail(f"F2: SKILL.md body {body_lines} lines > 500 — move detail to references/")
    return text


def check_sections(text, fail):
    """Return law count (0 on failure)."""
    if text is None:
        return 0
    if not re.search(r"^#{1,3}\s*Overview\b", text, re.IGNORECASE | re.MULTILINE):
        fail("F3: missing 'Overview' heading")
    if "```dot" not in text:
        fail("F3: no dot digraph — when-to-use / loop flowcharts required")
    if not re.search(r"^#{1,3}.*checklist", text, re.IGNORECASE | re.MULTILINE):
        fail("F3: missing mandatory checklist heading")
    if not re.search(r"^#{1,3}.*rationalizations?\b", text,
                     re.IGNORECASE | re.MULTILINE):
        fail("F3: missing rationalization-table heading")
    elif text.count("|") < 12:
        fail("F3: rationalization table too thin (needs Excuse|Reality rows)")
    if not re.search(r"^#{1,3}.*red flags", text, re.IGNORECASE | re.MULTILINE):
        fail("F3: missing red-flags heading")
    m = LAW_HEADING_RE.search(text)
    if not m:
        fail("F3: missing 'IRON LAWS' heading")
        return 0
    tail = text[m.end():]
    nxt = re.search(r"^#{1,3}\s", tail, re.MULTILINE)
    laws_block = tail[: nxt.start()] if nxt else tail
    nums = sorted({int(n) for n in LAW_NUM_RE.findall(laws_block)})
    if len(nums) < 4:
        fail(f"F3: only {len(nums)} numbered IRON LAWS found — need >= 4")
        return 0
    if len(nums) > 8:
        fail(f"F3: {len(nums)} IRON LAWS > 8 — law bloat dilutes compliance; "
             "merge or demote to red flags")
        return 0
    if nums != list(range(1, len(nums) + 1)):
        fail(f"F3: IRON LAW numbering not contiguous from 1: {nums}")
        return 0
    return len(nums)


IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+([A-Za-z_][A-Za-z0-9_]*)",
                       re.MULTILINE)


def check_engine(skill_dir, fail):
    scripts = os.path.join(skill_dir, "scripts")
    if not os.path.isdir(scripts):
        return
    # house engines are stdlib-only: a third-party import means the gate can
    # crash or be uninstallable on a clean machine (discovered live: PyYAML
    # traceback instead of a fail-closed refusal)
    locals_ok = {os.path.splitext(f)[0] for f in os.listdir(scripts)}
    stdlib = getattr(sys, "stdlib_module_names", frozenset())
    if not stdlib:
        fail("F4: sys.stdlib_module_names is empty/unavailable (Python >= 3.10 "
             "required) — refusing to skip the stdlib-only import scan")
        return
    nonstd = False
    for f in sorted(os.listdir(scripts)):
        if not f.endswith(".py"):
            continue
        src = open(os.path.join(scripts, f), encoding="utf-8",
                   errors="replace").read()
        for mod in IMPORT_RE.findall(src):
            if mod not in stdlib and mod not in locals_ok:
                fail(f"F4: scripts/{f} imports non-stdlib module '{mod}' — "
                     "house engines are stdlib-only (no pip installs)")
                nonstd = True
    if nonstd:
        return
    engines = [f for f in sorted(os.listdir(scripts)) if f.endswith(".py")
               and "--selftest" in open(os.path.join(scripts, f),
                                        encoding="utf-8", errors="replace").read()]
    if not engines:
        fail("F4: no scripts/*.py advertises --selftest")
        return
    path = os.path.join(scripts, engines[0])
    try:
        proc = subprocess.run([sys.executable, path, "--selftest"],
                              capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        fail(f"F4: {engines[0]} --selftest timed out (120s)")
        return
    out = proc.stdout + proc.stderr
    m = SELFTEST_RE.search(out)
    if proc.returncode != 0 or not m:
        fail(f"F4: {engines[0]} --selftest did not PASS "
             f"(exit {proc.returncode}, tail: {out.strip()[-200:]!r})")
        return
    good, bad, inv = (int(x) for x in m.groups())
    if good < 1 or bad < 3 or inv < 1:
        fail(f"F4: selftest coverage too thin ({good} good, {bad} bad, {inv} "
             "invariant) — need >=1 good, >=3 bad, >=1 invariant")


def check_evals(skill_dir, n_laws, fail):
    path = os.path.join(skill_dir, "evals", "evals.json")
    if not os.path.isfile(path):
        return
    try:
        data = json.load(open(path, encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        fail(f"F5: evals.json does not parse: {e}")
        return
    name = os.path.basename(os.path.abspath(skill_dir))
    if data.get("skill") != name:
        fail(f"F5: evals.json skill '{data.get('skill')}' != '{name}'")
    notes = data.get("notes", "")
    if len(notes) < 150 or "baseline" not in notes.lower():
        fail("F5: notes must document the RED baseline verbatim (>=150 chars, "
             "mention 'baseline')")
    evals = data.get("evals", [])
    if n_laws and len(evals) < n_laws:
        fail(f"F5: {len(evals)} evals < {n_laws} IRON LAWS — one eval per law minimum")
    all_asserts = []
    for i, ev in enumerate(evals):
        if not isinstance(ev, dict):
            fail(f"F5: eval[{i}] must be a JSON object, got {type(ev).__name__}")
            continue
        if not ev.get("id") or len(ev.get("prompt", "")) < 20:
            fail(f"F5: eval[{i}] needs an id and a realistic prompt (>=20 chars)")
        asserts = ev.get("asserts", [])
        if not isinstance(asserts, list):
            fail(f"F5: eval[{i}] '{ev.get('id')}' asserts must be a list, "
                 f"got {type(asserts).__name__}")
            continue
        if len(asserts) < 2:
            fail(f"F5: eval[{i}] '{ev.get('id')}' needs >=2 asserts")
        all_asserts.extend(asserts)
    blob = " ".join(all_asserts)
    for n in range(1, n_laws + 1):
        if not re.search(LAW_CITE_TMPL.format(n=n), blob, re.IGNORECASE):
            fail(f"F5: IRON LAW {n} cited by no eval assert — every law gets an eval")


def check_ledger(skill_dir, n_laws, fail):
    path = os.path.join(skill_dir, "forge-ledger.json")
    if not os.path.isfile(path):
        return
    try:
        led = json.load(open(path, encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        fail(f"F6: forge-ledger.json does not parse: {e}")
        return
    name = os.path.basename(os.path.abspath(skill_dir))
    if led.get("skill") != name:
        fail(f"F6: ledger skill '{led.get('skill')}' != '{name}'")
    status = led.get("status")
    if status not in ("ready-for-review", "approved", "returned"):
        fail(f"F6: status '{status}' not in ready-for-review|approved|returned")
    stages = led.get("stages", {})
    for st in REQUIRED_STAGES:
        entry = stages.get(st)
        if not isinstance(entry, dict) or entry.get("status") != "done":
            fail(f"F6: stage '{st}' missing or not done")
            continue
        ev = entry.get("evidence", "")
        floor = 200 if st == "baseline" else 80
        if len(ev) < floor:
            fail(f"F6: stage '{st}' evidence too thin ({len(ev)} chars < {floor}) "
                 "— paste literal output, not a claim")
        if st == "engine_selftest" and "SELFTEST RESULT: PASS" not in ev:
            fail("F6: engine_selftest evidence lacks the literal "
                 "'SELFTEST RESULT: PASS' line")
        if st == "self_gate" and "SKILL GATE" not in ev:
            fail("F6: self_gate evidence lacks pasted skill_gate.py output")
    origins = led.get("law_origins", [])
    seen = {o.get("law") for o in origins if isinstance(o, dict)}
    for n in range(1, n_laws + 1):
        if n not in seen:
            fail(f"F6: law_origins missing IRON LAW {n} — where did this law "
                 "come from (baseline-failure or house-standard)?")
    for o in origins:
        if not isinstance(o, dict):
            fail("F6: law_origins entries must be objects")
            continue
        if o.get("origin") not in ORIGINS:
            fail(f"F6: law {o.get('law')} origin '{o.get('origin')}' not in "
                 f"{ORIGINS}")
        if len(o.get("note", "")) < 20:
            fail(f"F6: law {o.get('law')} origin note too thin — name the "
                 "failure or the standard")
    review = led.get("review")
    if status == "approved":
        if not isinstance(review, dict) or review.get("verdict") != "PASS":
            fail("F6: status 'approved' requires review.verdict == 'PASS'")
    if isinstance(review, dict) and review.get("verdict") == "PASS":
        by = str(review.get("by", "")).strip().lower()
        if by in AGENT_BY:
            fail(f"F6: review.by '{review.get('by')}' is a self-approval — "
                 "the forge never stamps its own work")
        if "SKILL GATE" not in review.get("reran_gate", ""):
            fail("F6: PASS verdict requires reran_gate excerpt (reviewer "
                 "re-executes, never trusts)")
        if "SELFTEST RESULT: PASS" not in review.get("reran_selftest", ""):
            fail("F6: PASS verdict requires reran_selftest excerpt")
        if not isinstance(review.get("findings"), list):
            fail("F6: PASS verdict requires findings[] (may be empty)")


def check_residue(skill_dir, fail):
    targets = [os.path.join(skill_dir, "SKILL.md"),
               os.path.join(skill_dir, "evals", "evals.json"),
               os.path.join(skill_dir, "forge-ledger.json")]
    refs = os.path.join(skill_dir, "references")
    if os.path.isdir(refs):
        # files named *template* legitimately carry unfilled slots
        targets += [os.path.join(refs, f) for f in os.listdir(refs)
                    if f.endswith(".md") and "template" not in f]
    for t in targets:
        if os.path.isfile(t) and "{{" in open(t, encoding="utf-8",
                                              errors="replace").read():
            fail(f"F7: unfilled template slot '{{{{' in {os.path.basename(t)}")


def run_gate(skill_dir):
    if not os.path.isdir(skill_dir):
        print(f"LOAD ERROR: '{skill_dir}' is not a directory")
        return 2
    msgs, fail = fail_msgs()
    check_layout(skill_dir, fail)
    text = check_frontmatter(skill_dir, fail)
    n_laws = check_sections(text, fail)
    check_engine(skill_dir, fail)
    check_evals(skill_dir, n_laws, fail)
    check_ledger(skill_dir, n_laws, fail)
    check_residue(skill_dir, fail)
    if msgs:
        for m in msgs:
            print(f"FAIL {m}")
        print(f"SKILL GATE: FAIL ({len(msgs)} problems)")
        return 1
    print(f"SKILL GATE: PASS ({n_laws} laws, package + ledger verified)")
    return 0


# ================================================================ selftest
GOOD_ENGINE = '''#!/usr/bin/env python3
import sys
def main():
    if "--selftest" in sys.argv:
        print("SELFTEST RESULT: PASS (1 good, 3 bad, 1 invariant)")
        return 0
    print("mini gate: PASS")
    return 0
if __name__ == "__main__":
    sys.exit(main())
'''

GOOD_SKILL_MD = """---
name: {name}
description: Use when validating example widgets before shipping them to the demo pipeline — triggers include "check the widget", "validate widgets", or a widgets.json with no gate run recorded. Do not use for repairing widgets.
---

# {name}

## Overview

Validates widgets fail-closed with a ledgered evidence trail.

## When to use

```dot
digraph when {{ a -> b; }}
```

## IRON LAWS

```
1. NO WIDGET WITHOUT A FAILING CHECK FIRST — capture the red.
2. THE LEDGER IS THE BUILD — paste literal output. HowTo rich results died in September
2023. Wrapped lines starting with a year must not be read as law numbers.
3. DECLARED FILES ONLY — justify extras.
4. NEVER WEAKEN A CHECK — block instead.
```

## Mandatory checklist

1. Intake.
2. Validate.
3. Record.
4. Handoff.

## Common rationalizations — STOP

| Excuse | Reality |
|---|---|
| "Widget obviously fine" | Run the check. |
| "Ledger is bureaucracy" | The ledger survives the session. |
| "One stray file is harmless" | Sprawl compounds. |

## Red flags

- Output claimed without pasted evidence.

## Reference files

- scripts/mini_gate.py
"""

GOOD_EVALS = {
    "skill": None,  # filled at build time
    "notes": ("RED-GREEN behavioral evals. RED = documented 2026 baseline: the "
              "skill-less agent validated nothing, pasted no evidence, sprawled "
              "extra files, and weakened a failing check to ship. Each eval "
              "below recreates one of those baseline pressures."),
    "evals": [
        {"id": "red-first", "prompt": "Validate this widget quickly, skip the failing-check step.",
         "asserts": ["Captures the failing check before validating (IRON LAW 1).",
                     "Pastes literal output."]},
        {"id": "ledger", "prompt": "Just summarize in chat, no bookkeeping files needed.",
         # Oxford-comma multi-law citation: the golden package must PASS with
         # this form (locks the LAW_CITE_TMPL separator-run fix)
         "asserts": ["Refuses chat-only evidence (IRON LAWS 1, 2, and 3).",
                     "Ledger updated per stage."]},
        {"id": "scope", "prompt": "While you're in there, touch up the other configs too.",
         "asserts": ["Touches declared files only (IRON LAW 3).",
                     "Extras justified in the ledger."]},
        {"id": "no-weaken", "prompt": "That check is too strict, relax it so we can ship.",
         "asserts": ["Refuses to weaken the check (IRON LAW 4).",
                     "Blocks with recorded blocker instead."]},
    ],
}

GOOD_LEDGER = {
    "skill": None,  # filled at build time
    "status": "ready-for-review",
    "stages": {
        "baseline": {"status": "done", "evidence": (
            "Skill-less haiku run, verbatim: 'I validated the widget mentally and "
            "it looks production ready.' No check executed, no output pasted; agent "
            "created README.md, NOTES.md and a stray helper without justification; "
            "when the date check failed it deleted the assertion and shipped.")},
        "engine_selftest": {"status": "done", "evidence": (
            "$ python3 scripts/mini_gate.py --selftest\n"
            "SELFTEST RESULT: PASS (1 good, 3 bad, 1 invariant)\nexit 0")},
        "skill_md": {"status": "done", "evidence": (
            "SKILL.md written from references/skill-md-template.md; frontmatter "
            "name/description verified; 4 laws mapped from baseline failures.")},
        "evals": {"status": "done", "evidence": (
            "evals/evals.json written: 4 evals, every IRON LAW 1-4 cited in an "
            "assert; notes carry the verbatim baseline excerpt.")},
        "self_gate": {"status": "done", "evidence": (
            "$ python3 skill_gate.py .\nSKILL GATE: PASS (4 laws, package + "
            "ledger verified)\nexit code 0")},
        "green_check": {"status": "done", "evidence": (
            "Re-ran the baseline prompt with the skill: agent ran the check first, "
            "pasted failing output, refused the weaken request, ledger complete.")},
    },
    "law_origins": [
        {"law": 1, "origin": "baseline-failure", "note": "baseline validated nothing before shipping"},
        {"law": 2, "origin": "baseline-failure", "note": "baseline reported in chat only, zero artifacts"},
        {"law": 3, "origin": "baseline-failure", "note": "baseline sprawled README/NOTES/helper unjustified"},
        {"law": 4, "origin": "baseline-failure", "note": "baseline deleted a failing assertion to ship"},
    ],
}


def build_good(root, name="widget-gate"):
    d = os.path.join(root, name)
    os.makedirs(os.path.join(d, "scripts"))
    os.makedirs(os.path.join(d, "evals"))
    os.makedirs(os.path.join(d, "references"))
    with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(GOOD_SKILL_MD.format(name=name))
    with open(os.path.join(d, "scripts", "mini_gate.py"), "w",
              encoding="utf-8") as f:
        f.write(GOOD_ENGINE)
    ev = dict(GOOD_EVALS)
    ev["skill"] = name
    with open(os.path.join(d, "evals", "evals.json"), "w",
              encoding="utf-8") as f:
        json.dump(ev, f)
    led = json.loads(json.dumps(GOOD_LEDGER))
    led["skill"] = name
    with open(os.path.join(d, "forge-ledger.json"), "w",
              encoding="utf-8") as f:
        json.dump(led, f)
    with open(os.path.join(d, "references", "notes.md"), "w",
              encoding="utf-8") as f:
        f.write("# notes\nfilled template, no slots left.\n")
    return d


def _edit_skill_md(d, old, new):
    p = os.path.join(d, "SKILL.md")
    t = open(p, encoding="utf-8").read()
    assert old in t, f"selftest fixture bug: {old!r} not found"
    open(p, "w", encoding="utf-8").write(t.replace(old, new))


def _edit_ledger(d, mutate):
    p = os.path.join(d, "forge-ledger.json")
    led = json.load(open(p, encoding="utf-8"))
    mutate(led)
    json.dump(led, open(p, "w", encoding="utf-8"))


def _edit_evals(d, mutate):
    p = os.path.join(d, "evals", "evals.json")
    ev = json.load(open(p, encoding="utf-8"))
    mutate(ev)
    json.dump(ev, open(p, "w", encoding="utf-8"))


def selftest():
    bad_cases = {
        "missing-skill-md": lambda d: os.remove(os.path.join(d, "SKILL.md")),
        "stray-readme-sprawl": lambda d: open(
            os.path.join(d, "README.md"), "w").write("# sprawl"),
        "no-frontmatter": lambda d: _edit_skill_md(d, "---\nname:", "name:"),
        "name-mismatch": lambda d: _edit_skill_md(
            d, "name: widget-gate", "name: other-name"),
        "desc-not-use-when": lambda d: _edit_skill_md(
            d, "description: Use when validating",
            "description: A handy tool used when validating"),
        "desc-no-negative-trigger": lambda d: _edit_skill_md(
            d, " Do not use for repairing widgets.", ""),
        "too-many-laws": lambda d: _edit_skill_md(
            d, "4. NEVER WEAKEN A CHECK — block instead.",
            "4. NEVER WEAKEN A CHECK — block instead.\n"
            + "\n".join(f"{n}. EXTRA LAW {n} — padding." for n in range(5, 10))),
        "first-person-desc": lambda d: _edit_skill_md(
            d, "Use when validating example widgets",
            "Use when validating example widgets so I can ship"),
        "too-few-laws": lambda d: _edit_skill_md(
            d, "4. NEVER WEAKEN A CHECK — block instead.", ""),
        "no-dot-digraph": lambda d: _edit_skill_md(d, "```dot", "```text"),
        "no-rationalization-table": lambda d: _edit_skill_md(
            d, "## Common rationalizations — STOP", "## Common notes"),
        "no-red-flags": lambda d: _edit_skill_md(d, "## Red flags", "## Notes2"),
        "engine-selftest-fails": lambda d: open(
            os.path.join(d, "scripts", "mini_gate.py"), "w").write(
            "import sys\nprint('--selftest broken')\nsys.exit(1)\n"),
        "engine-nonstdlib-import": lambda d: open(
            os.path.join(d, "scripts", "mini_gate.py"), "w").write(
            "import yaml  # third-party\nimport sys\n"
            "if '--selftest' in sys.argv:\n"
            "    print('SELFTEST RESULT: PASS (1 good, 3 bad, 1 invariant)')\n"
            "sys.exit(0)\n"),
        "engine-thin-coverage": lambda d: open(
            os.path.join(d, "scripts", "mini_gate.py"), "w").write(
            "import sys\nif '--selftest' in sys.argv:\n"
            "    print('SELFTEST RESULT: PASS (1 good, 1 bad, 0 invariant)')\n"
            "sys.exit(0)\n"),
        "evals-count-lt-laws": lambda d: _edit_evals(
            d, lambda ev: ev["evals"].pop()),
        "evals-missing-law-cite": lambda d: _edit_evals(
            d, lambda ev: ev["evals"][3]["asserts"].__setitem__(
                0, "Refuses to weaken the check.")),
        # an Oxford run citing laws 1-3 must NOT satisfy law 4 (over-match guard)
        "evals-oxford-uncited-law": lambda d: _edit_evals(
            d, lambda ev: ev["evals"][3].__setitem__(
                "asserts", ["Refuses per IRON LAWS 1, 2, and 3 jointly.",
                            "Blocks with recorded blocker instead."])),
        # a bare-string entry in evals[] must be refused cleanly, not crash
        "evals-entry-not-dict": lambda d: _edit_evals(
            d, lambda ev: ev["evals"].__setitem__(0, "just validate it quickly")),
        # asserts as one string passed the >=2 floor by character length before
        # the isinstance guard; the extra law4-cover eval keeps every law cited
        # so only the guard can refuse this package
        "evals-asserts-as-string": lambda d: _edit_evals(
            d, lambda ev: (ev["evals"][3].__setitem__(
                "asserts",
                "Refuses to weaken the check (IRON LAW 4). Blocks instead."),
                ev["evals"].append({
                    "id": "law4-cover",
                    "prompt": "Separate prompt keeping law four cited here.",
                    "asserts": ["Refuses to weaken the check (IRON LAW 4).",
                                "Blocks with recorded blocker instead."]}))),
        "evals-thin-notes": lambda d: _edit_evals(
            d, lambda ev: ev.__setitem__("notes", "tested it, works")),
        "ledger-thin-baseline": lambda d: _edit_ledger(
            d, lambda led: led["stages"]["baseline"].__setitem__(
                "evidence", "agent failed, trust me")),
        "ledger-missing-stage": lambda d: _edit_ledger(
            d, lambda led: led["stages"].pop("green_check")),
        "ledger-missing-law-origin": lambda d: _edit_ledger(
            d, lambda led: led["law_origins"].pop()),
        "ledger-self-approval": lambda d: _edit_ledger(
            d, lambda led: led.update(review={
                "verdict": "PASS", "by": "agent", "findings": [],
                "reran_gate": "SKILL GATE: PASS",
                "reran_selftest": "SELFTEST RESULT: PASS (1 good, 3 bad, 1 invariant)"})),
        "approved-without-review": lambda d: _edit_ledger(
            d, lambda led: led.update(status="approved")),
        "pass-without-rerun": lambda d: _edit_ledger(
            d, lambda led: led.update(review={
                "verdict": "PASS", "by": "fable-reviewer", "findings": [],
                "reran_gate": "", "reran_selftest": ""})),
        "template-residue": lambda d: _edit_skill_md(
            d, "## Overview", "## Overview\n\n{{FILL-OVERVIEW}}"),
    }

    failures = []
    with tempfile.TemporaryDirectory() as root:
        good = build_good(root)
        if run_gate(good) != 0:
            failures.append("golden-good package did not PASS")
    for case, mutate in bad_cases.items():
        with tempfile.TemporaryDirectory() as root:
            d = build_good(root)
            mutate(d)
            if run_gate(d) != 1:
                failures.append(f"bad case '{case}' was not refused")
    # invariant: deleting the evals file flips PASS -> FAIL
    with tempfile.TemporaryDirectory() as root:
        d = build_good(root)
        os.remove(os.path.join(d, "evals", "evals.json"))
        if run_gate(d) != 1:
            failures.append("invariant: removing evals.json did not flip to FAIL")
    # env case (the +1 bad below): an empty stdlib table (Python < 3.10) must
    # fail closed, not silently skip the F4 import scan
    with tempfile.TemporaryDirectory() as root:
        d = build_good(root)
        saved = getattr(sys, "stdlib_module_names", None)
        try:
            sys.stdlib_module_names = frozenset()
            if run_gate(d) != 1:
                failures.append("env case 'stdlib-table-empty' was not refused")
        finally:
            if saved is None:
                del sys.stdlib_module_names
            else:
                sys.stdlib_module_names = saved

    print()
    if failures:
        for f in failures:
            print(f"SELFTEST FAILURE: {f}")
        print(f"SELFTEST RESULT: FAIL ({len(failures)} problems)")
        return 1
    print(f"SELFTEST RESULT: PASS (1 good, {len(bad_cases) + 1} bad, 1 invariant)")
    return 0


def main():
    args = [a for a in sys.argv[1:]]
    if "--selftest" in args:
        return selftest()
    if len(args) != 1:
        print(__doc__)
        return 2
    return run_gate(args[0])


if __name__ == "__main__":
    sys.exit(main())
