# pick-next-tool — Improvement Brief (gaps found in the 2026-06-08 live run)

**Audience:** an agent tasked with hardening the `pick-next-tool` skill. You have **no prior conversation
context** — everything you need is here. Read this whole file before touching code.

**Skill root:** `/Users/sanjaykumar/Claude/Projects/Online Web Apps/.claude/skills/pick-next-tool/`
(Also published OSS at github.com/luv-jeri/pick-next-tool — keep changes portable; no machine-specific paths in code.)

**Key files you will edit:**
- `scripts/score.py` — the deterministic gate+score engine (SOURCE OF TRUTH for numbers).
- `scripts/research-workflow.js` — the per-candidate researcher+skeptic Workflow (feeds score.py inputs).
- `scripts/dr_wall.py` — OpenPageRank DR-wall reader (the proxy at fault below).
- `scripts/serp_aio.py` — SerpApi SERP/AI-Overview reader.
- `references/scoring-model.md` — human-readable mirror of score.py. **MUST stay in sync with score.py in the same commit.**
- `references/process.md`, `references/free-tools.md` — the 9-stage procedure + data toolchain.
- `docs/adr/` — one ADR per design decision. Add ADR-0010+ for each change below.

## Non-negotiable working rules (the skill's own philosophy — do not violate while "fixing")
1. **`python3 scripts/score.py --selftest` MUST pass after every change.** It is snapshot + structural +
   golden-bad invariants. If a change is a deliberate recalibration, update the SNAPSHOT and say why in the commit.
2. **doc↔code sync:** any rule change in `score.py` is mirrored in `references/scoring-model.md` in the SAME commit.
3. **Fail closed (ADR-0009):** ambiguous/low-tier data must produce `REFUSE`, never a confident pass OR a confident
   DROP. "REFUSE → go verify" is a first-class, correct output. Adding a new way to fail loud is good; adding a
   silent fallback is the bug.
4. **Add a golden-bad fixture for every fix** so the failure mode you're closing can never silently return.
5. **Determinism:** same inputs → same output. No `Date.now()`/`random()` in scoring. New inputs must be explicit
   fields with documented measurement methods, not vibes.

---

## What happened in the run (evidence — read this; it justifies every fix)
We ran the funnel on 12 Freelancer/Solo-Business tools, runway = 9 months, `--data=hybrid`.
- The **research-workflow ran the scripts WITHOUT the `.env` keys bound** (it executed outside the project tree,
  so `serp_aio.py`/`dr_wall.py` returned **fixture/proxy** data) — yet it still emitted **hard DROP verdicts**.
- It **falsely DROPPED "Email Signature Generator" on a "verified DR-80 wall" that does not exist.** Re-run with
  keys → no wall, winnable (Opp 85). A real committable finalist was nearly killed by untrustworthy data.
- The **OpenPageRank proxy understated true Ahrefs DR by ~50 points**: `dr_wall.py` read `calculator.net` at
  **33**; real Ahrefs DR = **84**. The winner's winnability rested on this proxy.
- Only the **Stage-6 adversarial skeptic** + **three manual Ahrefs DR reads by the user** corrected it. Verified
  real DRs: `timecardcalculatorgeek.com` = **30** (thin proof honored), `redcort.com` = **37** (beatable, not a
  wall), `invoicegenerator.com` = **11**.
- The **triangulated board ranked Invoice #1 (91)**; only real-measured Winnability + time-to-rank pulled the
  winner back to Time-Card Calculator (96). So the inputs that decide the winner were exactly the ones that were
  least trustworthy.
- **Browser automation failed:** the chrome MCP `new_page` opened a **guest profile** (Cloudflare/timeout). The
  real-data pull only worked because the **user manually screenshotted** from their logged-in Ahrefs profile.
- Several decisive inputs were never actually measured: **time-to-rank** (hand-typed, gates the runway decision),
  **demand trend** (never pulled), **CPC/Revenue** (always `reasoned`), and **volume** (a band like `>10,000`,
  not an integer).

---

## WORK ITEMS (priority order — P1/P2 are correctness; do them first)

### P1 — Workflow must not launder low-tier data into hard DROPs (fail closed at the workflow↔engine seam)
**Problem:** `research-workflow.js` emitted confident `DROP`s (and set `dr_wall_evidenced=true`) from proxy/fixture
data when the API keys weren't bound. The engine fails closed; the workflow does not.
**Fix (two layers):**
- **Workflow (`research-workflow.js`):**
  - Detect whether `SERPAPI_KEY` / `OPENPAGERANK_API_KEY` actually bound and the scripts returned LIVE data
    (`serp_aio.py` returns `ok:true` + non-empty `page1_domains`; `dr_wall.py` returns `status:"scored"`, not
    `"unknown"`). If not, **hard-fail the run with a clear message** ("data-source keys unbound / scripts returned
    fixtures — refusing to emit gate verdicts") rather than returning fixture-backed verdicts.
  - Never set `dr_wall_evidenced=true` or populate `thin_site_proof_dr` from an OPR PROXY. Leave `thin_site_proof_dr`
    **null** unless a REAL Ahrefs DR was obtained. Tag winnability evidence `triangulated` when only proxy data exists.
- **Engine (`score.py`):** a winnability hard-DROP (Gate B) must **downgrade to `REFUSE`** when the winnability
  evidence tier is below `real-measured`. Rule: only hard-DROP on winnability when `evidence["winnability"]=="real-measured"`;
  otherwise REFUSE ("winnability kill rests on non-real-measured data — verify real DR"). (Same spirit as ADR-0008's
  noise-band REFUSE, extended to evidence tier.)
**Files:** `research-workflow.js`, `score.py` (`evaluate()` Gate-B branch + a new tier check), `scoring-model.md`.
**Acceptance:** add golden-bad fixture: a candidate with `winnability==1`, `dr_wall_evidenced=true`, but
`evidence.winnability="triangulated"` → expect **REFUSE**, not DROP. Re-running the 12-candidate set must NOT
hard-drop Email Signature. `--selftest` passes.

### P2 — Enforce REAL Ahrefs DR over the OPR proxy for the decisive thin-site proof
**Problem:** the proxy is logarithmically compressed and understates DR-80 sites by ~50 points; it can both hide a
wall AND make a strong site look like thin-site proof.
**Fix:**
- `dr_wall.py`: add **anchor calibration** — accept 1–2 domains with known real Ahrefs DR (config or CLI) and emit
  a calibrated estimate + a `confidence` field; ALWAYS emit `tier:"triangulated"` for proxy-derived DR.
- `score.py`: keep the existing rule that `thin_site_proof` is honored only with `thin_site_proof_dr` ≤ 40 — but add
  that the DR must be **real-measured** to be COMMIT-honored. A thin-proof backed only by proxy DR ranks but is
  **not committable** (forces the real-DR spot-check we did manually via Ahrefs Website Authority Checker).
- `references/free-tools.md` / `process.md`: make "pull the decisive thin-ranker's REAL Ahrefs DR (Website
  Authority Checker) before commit" an explicit **blocking Stage-5/6 step**.
**Files:** `dr_wall.py`, `score.py`, `scoring-model.md`, `free-tools.md`, `process.md`.
**Acceptance:** golden-bad fixture: thin_site_proof with proxy-only DR → `first_build_eligible=false` (rankable,
not committable). `--selftest` passes.

### P3 — Deterministic time-to-rank estimator (it gates the runway decision; today it's hand-typed)
**Problem:** `est_time_to_traffic_months` is a free input that decides opener-vs-fast-follow against `runway_months`,
yet there's no method. It swung 5→10 between me and the skeptic.
**Fix:** add `estimate_time_to_traffic(kd_head, weak_count, thin_proof_evidenced, dr_wall_strong_count,
domain_age_months)` to `score.py` returning months, with a documented formula (e.g. base from KD band, minus
credit for evidenced thin-proof / high weak_count, plus a new-domain sandbox floor of ~3–6 mo). When the candidate
omits `est_time_to_traffic_months`, derive it; when provided, keep it but flag large divergence from the estimate.
Document the formula in `scoring-model.md` and add ADR-0010.
**Files:** `score.py`, `scoring-model.md`, `docs/adr/0010-*.md`.
**Acceptance:** fixtures pinning a few (inputs→months) pairs; the runway time-block path still fires when
derived months > runway. `--selftest` passes (update SNAPSHOT if a golden's derived value changes a result).

### P4 — Demand trend is a required input (declining-demand trap)
**Problem:** Demand is scored on a static snapshot; a >10k/mo term declining 30%/yr scores identically to a rising one.
ADR-0006 says "project forward" but there's no trend field.
**Fix:** add `trend_slope_24mo` (or `trend_direction ∈ {rising,flat,declining}`) to the contract. Apply: declining →
Demand haircut (−1, floored) + a `sensitivity:` flag; strongly declining → REFUSE. Source = Google Trends 24-mo
(document in `free-tools.md`; it's a browser/manual read in hybrid mode). Make it part of Stage-5 real-demand.
**Files:** `score.py` (new REQUIRED or default field + `demand_score`/flags), `scoring-model.md`, `process.md`,
`free-tools.md`, ADR-0011. **Acceptance:** golden-bad: declining trend on an otherwise-strong tool → haircut/REFUSE.

### P5 — Measure Revenue, don't reason it
**Problem:** CPC was `reasoned` every run; `first_build_eligible` only requires D/W/AI at real-measured, so a money
decision commits on an unmeasured CPC/buyer-slice.
**Fix:** document the CPC pull (Google Ads Keyword Planner "top of page bid" — keys may exist in `.env`) in
`free-tools.md`; OPTIONALLY add `revenue` to `COMMIT_TIER_REQUIRED` (decide via ADR — it raises the commit bar).
At minimum, surface a flag when `evidence.revenue != real-measured` on the provisional winner.
**Files:** `score.py` (flag), `scoring-model.md`, `free-tools.md`, ADR-0012.

### P6 — Stop over-labeling banded volume as "real-measured"
**Problem:** Ahrefs free returns a BAND (`>10,000`), not an integer, yet we tag demand `real-measured` and let
`first_build_eligible` flip on a banded estimate near the 5,000 finalist bar.
**Fix:** introduce a `band` vs `integer` distinction for volume. Banded volume → demand tier capped at
`triangulated` UNLESS the band is unambiguously clear of the bar (e.g. band floor ≥ 2× finalist bar). Integer
(paid seat / Bing exact) → `real-measured`. Update `scoring-model.md`; ADR-0013.
**Files:** `score.py` (validate/score), `scoring-model.md`.

### P7 — Make human-in-the-loop data capture the DESIGNED hybrid path
**Problem:** `free-tools.md` §6 assumes an agent drives a browser MCP to scrape Ahrefs. Reality: `new_page` opens a
**guest** profile → Cloudflare/timeout. The run only worked because the user manually screenshotted from their
authenticated profile.
**Fix:** rewrite `free-tools.md` §6 + the hybrid description in `process.md` so the **primary** hybrid path is:
(a) API scripts for SERP/AIO/DR (serp_aio/dr_wall, keys required); (b) **user-driven capture** of Ahrefs
volume/KD/cluster + Website-Authority-Checker DR from their **logged-in profile** (agent reads screenshots /
`evaluate_script` on already-open tabs); headless automation is explicitly NOT relied on. Add the operational
gotchas: don't `new_page` (guest); scripts auto-load `.env` only when run from inside the project tree; zsh
needs `${=var}` to word-split domain lists.
**Files:** `free-tools.md`, `process.md`, optionally `SETUP.md`.

### P8 — Define `incumbent_top3_visits` precisely + tighten the Demand +1 bonus
**Problem:** the Demand +1 deep-cluster bonus uses `incumbent_top3_visits × 0.7 ≥ 1M`, but the field is undefined
(site-wide 70M for calculator.net makes it fire trivially; I had to estimate it).
**Fix:** define it as the **combined estimated monthly organic traffic to the top-3 RANKING PAGES for the cluster**
(not site-wide domain traffic), measured via Similarweb/Ahrefs; require it measured (tier) for the bonus to count.
Document in `scoring-model.md`; ADR-0014.
**Files:** `score.py` (doc/validate), `scoring-model.md`.

### P9 — Anti-prior-laundering guard (optional but recommended)
**Problem:** the funnel converged back to the inherited pick. It genuinely could have flipped (Invoice led the
triangulated board), but there's no guard proving the funnel isn't rationalizing the prior.
**Fix:** add a `--blind` mode that strips the inherited ranking/winner from the Stage-0 baseline passed downstream,
so Stages 2–6 source and score without knowing the prior answer; compare the blind winner to the prior as a
consistency check. Document in `process.md`; ADR-0015.

---

## Final acceptance (run before declaring done)
1. `python3 scripts/score.py --selftest` → **PASS** (snapshot + structural + all golden-bad, including the NEW
   fixtures from P1–P4/P6).
2. `references/scoring-model.md` matches `score.py` (no rule documented that the code doesn't implement, and vice versa).
3. Re-run the 12-candidate Freelancer/Solo-Business set through `research-workflow.js` with keys bound and confirm:
   Email Signature is **NOT hard-dropped** (REFUSE or PROVISIONAL when DR is proxy-only); the run **hard-fails
   loudly** if keys are unbound instead of emitting fixture verdicts.
4. One ADR added per behavioral change (ADR-0010+), each stating the problem, the rule, and the evidence above.
5. No machine-specific absolute paths committed into scripts (keep OSS-portable).

## Out of scope / do not break
- Don't weaken the existing gates, the veto rule, or the OK>VETO>REFUSE>DROP ordering.
- Don't turn REFUSE into a silent pass to "make the pipeline smoother" — REFUSE is the point.
- Don't remove the deterministic snapshot; recalibrate it explicitly if a fix legitimately changes a golden number.
