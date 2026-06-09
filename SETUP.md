# Setup for API-backed data modes (one-time)

This guide covers the **two optional API credentials** that unlock automated data
pulls in `competitive-analysis`. Do this **once**; after that each skill run is
hands-off for the data it controls.

> **You can skip this page if you only use browser-driven mode.**
> Browser-driven mode drives Lighthouse, the chrome-devtools MCP, and stdlib
> `parse_jsonld.py` through the live browser — it needs **no keys at all** for CWV,
> a11y, and schema audits. Keys exist only to remove manual SERP and DR-lookup steps.

---

## Which keys are needed for which data modes

| Data category | Tool / source | Keys required |
|---|---|---|
| **Core Web Vitals** (LCP / CLS / INP) | Lighthouse via chrome-devtools MCP | **None** — runs live in browser |
| **Accessibility** (a11y score) | Lighthouse accessibility audit | **None** — runs live in browser |
| **Structured-data / schema** (`@type` per competitor) | `parse_jsonld.py` — stdlib JSON-LD parser against live HTML | **None** — pure HTTP + stdlib |
| **Domain Rating** (DR-wall, authority scoring) | OpenPageRank (DomCop) | `OPENPAGERANK_API_KEY` |
| **SERP layout + AI-Overview detection** (at scale / unattended) | SerpApi | `SERPAPI_KEY` (optional; manual SERP inspection works for single runs) |

**Summary:** CWV / a11y / schema need **no keys**. DR lookups need
`OPENPAGERANK_API_KEY`. Automated SERP + AI-Overview detection at scale needs
`SERPAPI_KEY`.

---

## Shared keys with `pick-next-tool`

`competitive-analysis` reuses **the same two keys** that `pick-next-tool` already
uses for its DR-wall and SERP gates. If you have already followed
[`pick-next-tool`'s SETUP.md](../../pick-next-tool/SETUP.md) you already have
`OPENPAGERANK_API_KEY` and `SERPAPI_KEY` set — **no further action needed**.

---

## Where to put the values

Add the variables to the project-root `.env` file (or your `~/.zshrc` with
`export`). The `.env` must be git-ignored so secrets are never committed.

```dotenv
# .env  (NEVER commit this file)
OPENPAGERANK_API_KEY=your-openpagerank-key-here
SERPAPI_KEY=your-serpapi-key-here          # optional for single-run use
```

---

## 1. OpenPageRank (DomCop) — competitor Domain Rating (1 variable)

OpenPageRank gives a free **Domain Rating (0–10)** for any domain. The skill uses
it to score `competitor_strength.authority` for each incumbent.

1. Go to **https://www.domcop.com/openpagerank/** and sign up (free, no card).
2. After signing in, your **API key** is shown on the OpenPageRank dashboard /
   account page.
3. Copy it → put it in **`OPENPAGERANK_API_KEY`**.

> **Free tier:** up to 10,000 API calls per hour — far more than this skill needs
> for a single competitor set (typically 5–15 domains).

> **Important note on DR scale:** OpenPageRank uses a 0–10 scale; Ahrefs uses 0–100.
> `scripts/authority_score.py` normalises the OPR value (multiply × 10) before
> applying the `competitor_strength.authority` weight. Do not compare raw OPR DR
> numbers directly to Ahrefs DR numbers.

---

## 2. SerpApi — SERP layout + AI-Overview detection (1 variable, optional)

SerpApi returns Google results as clean JSON, including whether an **AI Overview**
fired for a query (needed for the `gap_opportunity.ai_resistance` score).

- **Single runs:** you can inspect the SERP manually in the browser — the skill
  will prompt you for the AI-Overview Y/N. No key required.
- **Unattended / batch runs:** set `SERPAPI_KEY` to pull SERP data automatically.

1. Go to **https://serpapi.com/users/sign_up** and create a free account (no card
   for the free tier).
2. After signing in, open your dashboard → **"Your Account"**; copy the **Private
   API Key** (long hex string).
3. Put it in **`SERPAPI_KEY`**.

> **Free tier (verify, June 2026):** 250 searches/month on the forever-free plan —
> enough for several skill runs per month.

---

## Verify your setup

Open a **new** terminal (so it picks up your `.env` loader) and run:

```zsh
for v in OPENPAGERANK_API_KEY SERPAPI_KEY; do
  printf '%-24s %s\n' "$v" "${(P)v:+SET}"
done
```

Each variable should print `SET`. A blank line means it is not set — re-check the
name and your `.env` / profile.

---

## Quick reference

| Env var | Service | Skill data role | Where to get it |
|---|---|---|---|
| `OPENPAGERANK_API_KEY` | OpenPageRank (DomCop) | Competitor DR / authority wall | DomCop OpenPageRank dashboard |
| `SERPAPI_KEY` | SerpApi | SERP layout + AI-Overview detection | SerpApi dashboard (Private API Key) |

**CWV, a11y, and schema audits need none of the above.** Lighthouse runs live via
the chrome-devtools MCP; `parse_jsonld.py` hits the live page with no auth.
