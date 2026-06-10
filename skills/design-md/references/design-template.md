# DESIGN.md skeleton + Build Contract schema

Copy this skeleton, replace every placeholder, delete instructional comments. The front matter and
the eight canonical sections follow Google's DESIGN.md spec (`npx @google/design.md spec` for the
live version — the format is alpha). House sections come AFTER the canonical ones, in the order
shown. Unknown sections are spec-legal ("preserve; do not error"), which is what makes the house
extensions safe.

---

## 1. The skeleton

```md
---
version: alpha
name: <Tool display name>
description: <one line — what UI this file governs>
colors:
  primary: "<css color>"        # core text / headlines
  secondary: "<css color>"      # borders, captions, metadata
  tertiary: "<css color>"       # THE interaction color (CTAs, focus)
  neutral: "<css color>"        # page background
  on-tertiary: "<css color>"    # text on tertiary — pair must clear WCAG AA 4.5:1
  error: "<css color>"
  warning: "<css color>"
typography:
  h1: { fontFamily: <stack>, fontSize: <rem>, fontWeight: <n> }
  h2: { fontFamily: <stack>, fontSize: <rem>, fontWeight: <n> }
  body-md: { fontFamily: <stack>, fontSize: 1rem }
  label: { fontFamily: <stack>, fontSize: 0.875rem, fontWeight: 500 }
  numeric: { fontFamily: <stack>, fontSize: <rem>, fontFeature: "tnum" }  # totals never jitter
rounded:
  sm: 4px
  md: 8px
  lg: 16px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
components:
  button-primary:
    backgroundColor: "{colors.tertiary}"
    textColor: "{colors.on-tertiary}"
    rounded: "{rounded.sm}"
    padding: 12px
  button-secondary:
    backgroundColor: "{colors.neutral}"
    textColor: "{colors.primary}"
    rounded: "{rounded.sm}"
  input-field:
    backgroundColor: "{colors.neutral}"
    textColor: "{colors.primary}"
    rounded: "{rounded.sm}"
    height: 44px            # mobile tap target floor
  ad-slot:
    backgroundColor: "{colors.neutral}"
    height: 280px           # reserved — CLS protection
---

## Overview

<2-4 sentences: the aesthetic in plain words, the device reality (mobile-first?), and the one-line
job the UI must make effortless. Name the tool's emotional register (calm utility, not dashboard).>

## Colors

<Why each token exists and where it may be used. One bullet per token. State the AA-checked pairs.>

## Typography

<Scale rationale; which token each surface uses; tabular numerals rule for any recomputing value.>

## Layout

<Page composition top-to-bottom (hero -> tool -> ad slot -> guidance -> ad slot -> FAQ), grid/
column behavior, the mobile breakpoint and what reflows, tap-target floor, spacing rhythm.>

## Elevation & Depth

<Shadow/border strategy. Static tools usually: borders over shadows, one card level. Omit if empty.>

## Shapes

<Radius usage per component family. Omit if rounded tokens tell the whole story.>

## Components

<One block per component the build needs: anatomy, token bindings, variants (hover/focus/disabled
as separate component entries in front matter), behavior notes. EVERY component cites the
requirement id(s) it serves, e.g. "(R1, R7)".>

## Do's and Don'ts

<5-10 bullets each. Don'ts must include the do-not-build list — anything adjacent the agent might
be tempted to add (mirrors the PRD's WON'T-DO).>

## States

<House section. For each interactive surface: default / empty / error / loading / success.
Errors: inline, field-level, aria-described, never color-only, never modal. State which states are
n/a and why (e.g. loading n/a — static client-side compute).>

## Ad Slots

<House section. Each slot: id, position in the page composition, reserved min-height (px),
above-fold = NO. Restate the law: ads never displace or precede the tool.>

## Build Contract

<House section. The machine block design_gate.py validates. Fenced as ```json — exact schema below.>
```

---

## 2. Build Contract schema (the fenced JSON block)

```json
{
  "design_contract": {
    "requirement_coverage": {
      "R1": ["#components", "#states"],
      "R2": ["#layout"]
    },
    "interaction_budget": {
      "canonical_job": "<the prd_seed.input_ergonomics canonical job>",
      "target": 15,
      "estimated": 9,
      "trace": "<one line: how the estimate was counted>"
    },
    "input_modalities": {
      "<field-name>": "native-time-picker",
      "<field-name-2>": { "modality": "typed-free-text", "justification": "<evidence-backed reason or it fails the gate>" }
    },
    "ad_slots": [
      { "id": "A", "position": "after-tool", "min_height_px": 280, "above_fold": false }
    ],
    "states": {
      "default": "#states",
      "empty": "#states",
      "error": "#states",
      "loading": "n/a — static client-side compute",
      "success": "#states"
    }
  }
}
```

Rules the gate enforces (fail-closed):

| Field | Rule |
|---|---|
| `requirement_coverage` | EVERY `priority: must` id in build-spec.json present, each with a non-empty list of `#section-anchor` refs |
| `interaction_budget` | `target` > 0, `estimated` ≤ `target`; pull target from `prd_seed.input_ergonomics.target` when present |
| `input_modalities` | every entry whose modality matches typed/free-text REQUIRES a non-empty `justification` |
| `ad_slots` | ≥1 entry, each with `min_height_px` ≥ 50 and `above_fold: false` — OR an `ads_excluded_reason` string instead of slots |
| `states` | all five keys present, each a non-empty string (`#anchor` or `n/a — reason`) |
| front matter | file must start with a `---` YAML fence (token layer present; token VALIDITY is the Google linter's job) |

## 3. Worked micro-example (calibration)

A passing contract for a one-field tip calculator with R1 (a11y) and R2 (instant result) as musts:

```json
{
  "design_contract": {
    "requirement_coverage": { "R1": ["#components", "#states"], "R2": ["#components"] },
    "interaction_budget": { "canonical_job": "enter bill, see tip", "target": 4, "estimated": 2, "trace": "1 amount entry + 1 preset chip" },
    "input_modalities": { "bill_amount": "numeric-keypad-input", "tip_percent": "preset-chips" },
    "ad_slots": [ { "id": "A", "position": "after-tool", "min_height_px": 280, "above_fold": false } ],
    "states": { "default": "#states", "empty": "#states", "error": "#states", "loading": "n/a — sync compute", "success": "#states" }
  }
}
```
