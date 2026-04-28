# Cost Observability — Work Outline & Priorities

**For**: Brian Krabach  
**From**: Ken Chau  
**Date**: 2026-04-28  
**Purpose**: Pre-read for 30-min alignment call — discoveries, gaps, assets, and prioritized work ahead

---

## What We Talked About (Quick Recap)

Ken came in with a viewer. Brian redirected: the viewer is a great recon spike, but the primary
need is a **library** — one that powers the CLI status line today, and every other surface
(web viewer, assistant tool, agent hook) later. This doc captures what the spike discovered
and lays out the work ahead in that framing.

---

## 1. Discoveries From the Spike

### Wins / Assets

**A. The cost viewer itself** (`amplifier-app-cost-viewer`)  
121 commits of working infrastructure: event log parser, session tree builder, pricing table,
FastAPI REST API, and a full canvas Gantt timeline UI. Even in its current imperfect state, it is
already useful for analyzing our own systems — the kind of "look at that sub-loop, it costs $40
every invocation" insight Brian called out as exactly what the team needs.

**B. Deep research doc** (`docs/research/token-cost-analysis.md`)  
Parallel research across 4 agents produced a comprehensive comparison: how Langfuse, Helicone,
LangSmith, and Braintrust track costs; how GSD/Aider/Codex CLI manage context to stay 4-8× cheaper
than Claude Code-style harnesses; and what Anthropic's new Task Budgets API (March 2026 beta) offers
for capping convergence loops. This doc is a real artifact the team can use and cite.

**C. We now know what we don't know**  
The spike uncovered that we're both over-reporting and under-reporting costs today. This means
before we can tell Brian "the cost of that session was X," we need to fix the measurement layer.
That's not a failure — it's the point of a spike.

**D. The 4-8× harness cost delta is confirmed**  
Published benchmarks show Claude Code-style orchestration uses 4.2× more tokens per task than
Aider, and up to 8× more than Codex CLI. The difference is architectural: GSD externalizes state to
files and resets context per plan. Amplifier's current `context_scope` policies (especially
`"full"` on sub-agent delegations) are a meaningful cost driver.

---

### Gaps Found

**G1. Cache tokens are not being tracked correctly (reader.py)**  
The event log parser looks for `cache_read_tokens` / `cache_write_tokens` but Anthropic's API
returns `cache_creation_input_tokens` / `cache_read_input_tokens`. This means sessions using
prompt caching are being billed at the full input rate — **overcounting cost by up to 5×** for
cache-heavy sessions. OpenAI and Google have their own different field names that are also missed.

**G2. Many models report $0 silently (pricing.py)**  
`claude-3-5-sonnet-*`, `claude-3-5-haiku-*`, `gemini-1.5-*`, and all Bedrock-prefixed Anthropic
model IDs are absent from the pricing table. Sessions using these models show $0.00 with no
warning. There's no instrumentation to even surface which models have no pricing entry.

**G3. No per-turn cost aggregation exists anywhere**  
Brian specifically called this out: "we don't get to see at the end of a given turn how much was
spent on that turn." The viewer can show per-span costs but nothing rolls up to the turn boundary.
This is a gap in both the viewer **and** the kernel's event log — there's no `turn:end` event
with an accumulated cost summary.

**G4. No real-time cost signal during a session**  
The CLI status line shows tokens, but the cost calculation is inaccurate today (see G1, G2),
and there's no per-turn or accumulated total. A user has no reliable indicator of what a task
is costing as it runs — only after the fact via the viewer.

**G5. Convergence loops have no guardrails**  
Browser-operator loops (and any other convergence pattern) can grow cost quadratically because
each turn re-sends full screenshot history. No framework (including Amplifier) ships a
dollar-budget kill-switch today. LangGraph defaults to `recursion_limit=25`; Amplifier has no
equivalent. Anthropic's new Task Budgets API is the right tool but is Opus 4.7-only and beta.

**G6. No intent-based cost routing**  
There's no mechanism to say "use a cheaper model for this expensive sub-loop" or "cap browser
operator at N turns before falling back." The routing matrix gets at model selection but not
at cost-aware or loop-aware routing.

---

### Things That Look Like Solutions But Aren't (Quite) Right Yet

**S1. The cost viewer (app) as a data source for the CLI**  
The viewer is a separate FastAPI process reading from JSONL files retroactively. It's the right
shape for an analysis tool, but it can't be the source of truth for real-time CLI cost feedback.
The library Brian described needs to exist first; the viewer should be a thin client of that library.

**S2. The Langfuse integration (early commits)**  
The repo started as a Langfuse hook (`hook-observability`, `hook-langfuse`). Langfuse is a
proxy/SDK approach — it intercepts calls and stores them in its own backend. That's a business
model for third parties, not what we want for a self-contained Amplifier experience. We moved
away from this correctly. The JSONL-first approach is right.

**S3. The Rust scanner (summaries.db)**  
A Rust-based scanner that pre-computes session summaries into SQLite was committed but never wired
into the server. The code is dead right now (`db.py` exists but `server.py` never imports it).
This is a good idea for performance at scale but it's not unblocking anything today.

---

## 2. Work To Be Done — Outline With Priorities

Brian's architecture from the call:

```
Layer 0 (foundation):  cost-tracking LIBRARY
                          ↓ thin wrapper
Layer 1 (CLI):         status line hook  ←  fixes what's broken today
                          ↓ also powered by
Layer 2 (analysis):    cost viewer app   ←  keep, fix guts, use library
                          ↓ also powered by
Layer 3 (future):      assistant tool, agent bundle, other surfaces
```

---

### Priority 1 — Fix the Measurement (enables everything else)

These are bugs, not features. Nothing above them is trustworthy until they're fixed.

| # | Work | Why now |
|---|---|---|
| 1a | Fix cache token alias map in `reader.py` | Sessions using prompt caching are overcounted by up to 5×; fixing this may immediately show costs are much lower than feared |
| 1b | Add missing model families to `pricing.py` (`claude-3-5-sonnet/*`, `gemini-1.5/*`, Bedrock prefixes) | Fixes silent $0 reporting for large swaths of historical sessions |
| 1c | Add `logger.warning` + `/api/pricing/misses` for unknown models | Surfaces future pricing gaps immediately instead of letting them hide |
| 1d | Add `cache_read_tokens` / `cache_write_tokens` to `SessionNode` rollup and UI summary | Makes the real cost structure (fresh tokens vs cache hits) visible in the list view |
| 1e | Verify empirically: does parent `events.jsonl` inline child `llm:response` events? | Determines whether tree rollup is double-counting; if yes, everything looks 2× too expensive |

**Exit criterion**: Pick any 3 real Amplifier sessions. The viewer's reported cost should be within
15% of what the Anthropic dashboard bills. Currently we cannot make that claim.

---

### Priority 2 — The Library (Brian's primary ask)

> "What I need is something closer to a library that's going to be able to be leveraged more in
> real time... done in a library first, and then thinly wrapped in hooks."

This is the core deliverable. Design questions to align on before building:

**Q1: Where does it live?**  
A new `amplifier-module-cost` repo (a kernel hook module) vs. expanding
`amplifier-app-cost-viewer`'s reader/pricing into a published package vs. inside `amplifier-core`.
Brian's framing — "it's got to fit inside that payload, not as 'also run this other app'" — suggests
it should be a hook module, not a separate app.

**Q2: What does it expose?**  
At minimum, three levels Brian named:
- Per-LLM-request: `{model, input_tokens, cached_tokens, output_tokens, cost_usd}` — fixes what
  the CLI status line shows today
- Per-turn: accumulated cost across all LLM calls in one orchestrator turn — **doesn't exist today**
- Per-session: running total — exists in the viewer, needs to move to the library

**Q3: What does "real-time" mean for the CLI?**  
The current status line is emitted by the orchestrator after each LLM call. Fixing it to show
accurate cost is a hook call, not an app. The library computes cost from the `llm:response` event's
`usage` fields; the hook formats and emits to the status line.

**Q4: How does the viewer relationship change?**  
The viewer's `reader.py` / `pricing.py` becomes the library or is replaced by it. The FastAPI
server and UI remain as a thin wrapper around the library's data model.

**Proposed sequence**:
1. Extract `pricing.py` as a standalone, well-tested Python package (`amplifier-cost-lib` or similar)
2. Extend it with the correct cache alias map and missing models (Priority 1 work feeds this)
3. Write a hook module that subscribes to `llm:response` and emits per-request + per-turn cost
4. Wire that hook into the CLI status line
5. Retool the viewer's `reader.py` to use the library for cost calculation
6. Library is now the single source of truth for all surfaces

---

### Priority 3 — Loop Guardrails (the $40-per-invocation problem)

> "If you're asking a machine to do this, it might cost you 40 bucks. Are you willing to pay
> for that cost? I don't have any good indicator before I ask for a task exactly how much it
> would cost."

This is the most visible pain point. Short-term and longer-term options:

**Short-term (ship in days)**:
- Add `max_turns` / `max_iterations` config to browser-operator and browser-researcher agents
- Expose Anthropic's `task_budget` parameter (Opus 4.7 beta) on browser-tester delegations;
  set a conservative default (e.g., 32K tokens per convergence attempt)
- Log iteration count in convergence loops so the viewer can flag "this loop ran 47 times"

**Longer-term (requires design)**:
- Intent-based cost routing: before entering an expensive sub-loop, emit an event; the hook can
  inspect the route and substitute a cheaper model or local alternative
- Budget-aware orchestrator: if accumulated cost this session exceeds a threshold, change behavior
  (warn, ask, abort) — this is what Brian described as the value of the real-time library

---

### Priority 4 — Context Efficiency (the GSD gap)

> "It might be intent-based routing... it's more than the routing matrix thing we've got."

The 4-8× token cost delta vs. GSD/Aider comes from context accumulation, not model choice.
The work here is more architectural and slower to deliver. Flag these for design discussion
rather than near-term execution:

- Audit `context_scope` usage across all registered agents — identify which ones use
  `"full"` or `"agents"` and whether that's justified vs. defaulted
- Pilot GSD-style "fresh context per plan" pattern on a defined workflow (e.g., execute-plan
  recipe) and measure token delta
- Surface per-delegation token cost in the viewer so the team can see which agents are the
  most expensive to call and with which context settings

---

### Priority 5 — Evergreen Maintenance (ongoing, low friction)

Brian called the foundation layer "evergreen" — new models ship weekly.

- `scripts/update_pricing.py` runs against LiteLLM catalog and rewrites `pricing.py`; this
  should become a scheduled CI job (weekly) or a PR-triggered update
- Track `pricing_misses` in the viewer and file a tracking issue when a new model appears
  that has no pricing entry

---

## 3. Open Alignment Questions for the 30-Min Call

These are the things where Ken's direction depends on Brian's answer:

1. **Library location**: hook module in `amplifier-core` ecosystem, or extracted package from the
   viewer repo, or something else? (This determines where the code lives and who touches it.)

2. **Viewer disposition**: Keep `amplifier-app-cost-viewer` as the analysis tool and have it
   consume the library, or fold it into a different repo/surface?

3. **Per-turn event**: Is there appetite to add a `turn:end` event to the kernel's event log?
   That one change would make per-turn cost aggregation trivial for all downstream consumers —
   viewer, library, status line, everything.

4. **Team ownership**: Brian mentioned Ken + Paul + Salil working closely on this layer. Which
   of these priorities should Ken drive solo vs. need early design alignment with Paul/Salil?

5. **Cloud Pilot opportunity**: Ken mentioned the Cloud Pilot team needs a better harness. Does
   that change the priority or shape of the library/viewer work? (Brian said "we'll figure that
   out within the bigger plan.")

---

## 4. One-Page Summary (for quick reference during the call)

```
WHAT WE HAVE:
  ✓ Working cost viewer with event log parser, pricing table, session tree, canvas UI
  ✓ Research doc confirming the 4-8× harness cost delta is real and architectural
  ✓ Understanding of the 3 root causes: measurement bugs, context accumulation, no guardrails

WHAT'S BROKEN (measurement):
  ✗ Cache tokens aliased wrong → up to 5× overcount on cache-heavy sessions
  ✗ 3-5 model families missing from pricing → silent $0 on historical sessions
  ✗ No per-turn cost anywhere

WHAT BRIAN ACTUALLY NEEDS (the reframe):
  → Library (compute + emit cost at per-request / per-turn / per-session)
     → thin hook wrapper → CLI status line (fixes what's broken today)
     → thin app wrapper → cost viewer (keep, swap guts)
     → thin future wrappers → assistant tool, agent bundle, etc.

PRIORITIES:
  P1: Fix measurement (days) — enables trust in everything else
  P2: Build the library (weeks) — the real deliverable
  P3: Loop guardrails (days for short-term, weeks for full) — $40/invocation problem
  P4: Context efficiency (design-first, longer horizon) — the GSD gap
  P5: Evergreen pricing maintenance (ongoing, low friction)
```
