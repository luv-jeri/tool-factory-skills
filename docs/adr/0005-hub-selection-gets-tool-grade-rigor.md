# Hub selection earns tool-grade rigor — pre-flight gate-drill and a minimum depth

**Status:** accepted

The Stage-1 hub gate was four qualitative criteria applied once on judgment, while the tool gates (A–D) are measured and adversarially verified. That is backwards under ADR-0001: the hub is the *least reversible* decision in the funnel — swap a tool and you keep your domain, link-spine, and topical authority; swap a hub and you throw all of it away and rebuild authority from zero. The least-reversible decision had the least rigor, and its load-bearing criterion ("≥4–6 tools each *plausibly* clearing the gates") was a guess made *before* any tool was gate-tested.

## Decision

1. **Hub pre-flight gate-drill.** Before committing a hub, run Gates A–D *quickly* on 2–3 representative candidate tools in it. A hub is blessed only if those drills show real winnable tools — evidence, not "plausibly."
2. **Minimum hub depth ≥ 3.** A hub is rejected outright unless at least 3 independently-winnable tools clear the quick gate-drill. Depth is resilience: it is the supply of same-hub fallbacks (ADR-0001 / Stage 7) that lets a flopped opener be replaced without abandoning the authority already built.
3. **Prefer the deeper hub** when two are close — more winnable tools means more fallbacks and a longer build runway inside one authority investment.
4. **Each hub choice is its own ADR**, since it is hard to reverse and a future reader will need the "why this hub" reasoning.

## Consequences

- Stage 1 costs more upfront (a few quick gate-drills) in exchange for de-risking the most expensive-to-reverse decision.
- The chicken-and-egg in the old criterion (b) is resolved: hub viability is now established by actually drilling tools, not asserting they exist.
