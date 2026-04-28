# Cost Observability — Work Outline & Priorities

**For**: Brian Krabach  
**From**: Ken Chau  
**Date**: 2026-04-28 (updated after alignment call w/ Brian + Salil)  
**Status**: Post-alignment — decisions captured, design doc + flat task list to follow  
**Purpose**: Living document; captures discoveries, gaps, decisions made, and prioritized work

---

## What We Talked About (Quick Recap)

Ken came in with a viewer. Brian redirected: the viewer is a great recon spike, but the primary
need is a library — one that powers the CLI status line today, and every other surface (web viewer,
assistant tool, agent hook) later. This doc captures what the spike discovered, the decisions made
in the alignment call (Ken + Brian + Salil), and the prioritized work ahead.

---

## 1. Discoveries From the Spike

### Wins / Assets

**A. The cost viewer itself** (`amplifier-app-cost-viewer`)  
121 commits of working infrastructure: event log parser, session tree builder, pricing table,
FastAPI REST API, and a full canvas Gantt timeline UI. Even in its current imperfect state, it is
already useful for analyzing our own systems — the kind of "look at that sub-loop, it costs $40
every invocation" insight Brian called out as exactly what the team needs. Brian's verdict:
**"good enough for now"** — leave it where it is, show it Thursday, make it one-line installable.

**B. Deep research doc** (`docs/research/token-cost-analysis.md`)  
Parallel research across 4 agents produced a comprehensive comparison: how Langfuse, Helicone,
LangSmith, and Braintrust track costs; how GSD/Aider/Codex CLI manage context to stay 4-8×
cheaper than Claude Code-style harnesses; and what Anthropic's new Task Budgets API (March 2026
beta) offers for capping convergence loops. This doc is a real artifact the team can use and cite.

**C. We now know what we don't know**  
The spike uncovered that we're both over-reporting and under-reporting costs today. Before we can
tell Brian "the cost of that session was X," we need to fix the measurement layer. That's not
a failure — it's the point of a spike.

**D. The 4-8× harness cost delta is confirmed**  
Published benchmarks show Claude Code-style orchestration uses 4.2× more tokens per task than
Aider, and up to 8× more than Codex CLI. The difference is architectural: GSD externalizes state
to files and resets context per plan. Amplifier's current `context_scope` policies (especially
`"full"` on sub-agent delegations) are a meaningful cost driver.

---

### Gaps Found

**G1. Cache tokens are not being tracked correctly (reader.py)**  
The event log parser looks for `cache_read_tokens` / `cache_write_tokens` but Anthropic's API
returns `cache_creation_input_tokens` / `cache_read_input_tokens`. This means sessions using
prompt caching are being billed at the full input rate — overcounting cost by up to 5× for
cache-heavy sessions. OpenAI and Google have their own different field names that are also missed.

> *Ken: need to standardize this shape in core — cache token fields should be first-class in the
> provider interface, not tacked into metadata. Brian confirmed: cache data is currently NOT part
> of the official provider interface contract; it lives in the metadata property bag. This work
> justifies making it first-class.*

**G2. Many models report $0 silently (pricing.py)**  
`claude-3-5-sonnet-*`, `claude-3-5-haiku-*`, `gemini-1.5-*`, and all Bedrock-prefixed Anthropic
model IDs are absent from the pricing table. Sessions using these models show $0.00 with no
warning. There's no instrumentation to even surface which models have no pricing entry.

**G3. No per-turn cost aggregation exists anywhere**  
Brian specifically called this out: "we don't get to see at the end of a given turn how much was
spent on that turn." The viewer can show per-span costs but nothing rolls up to the turn boundary.
This is a gap in both the viewer and the kernel's event log — there's no `turn:end` event with
an accumulated cost summary.

**G4. No real-time cost signal during a session**  
The CLI status line shows tokens, but the cost calculation is inaccurate today (see G1, G2),
and there's no per-turn or accumulated total. A user has no reliable indicator of what a task
is costing as it runs — only after the fact via the viewer.

**G5. Convergence loops have no guardrails** *(out of scope for now)*  
Browser-operator loops can grow cost quadratically because each turn re-sends full screenshot
history. No framework ships a dollar-budget kill-switch today. Anthropic's new Task Budgets API
is the right tool but is Opus 4.7-only and beta.

**G6. No intent-based cost routing** *(out of scope for now)*  
No mechanism to say "use a cheaper model for this expensive sub-loop." The routing matrix gets
at model selection but not at cost-aware or loop-aware routing.

---

### Things That Look Like Solutions But Aren't (Quite) Right Yet

**S1. The cost viewer (app) as a data source for the CLI**  
The viewer is a separate FastAPI process reading from JSONL files retroactively. It's the right
shape for an analysis tool, but it can't be the source of truth for real-time CLI cost feedback.
The library Brian described needs to exist first; the viewer should be a thin client of that
library. Ken's insight from the alignment call: "If you're just scanning events, you don't have
to do another correlation of data exercise before you get cost data — that's the biggest win."

**S2. The Langfuse integration (early commits)**  
The repo started as a Langfuse hook (`hook-observability`, `hook-langfuse`). Langfuse is a
proxy/SDK approach — it intercepts calls and stores them in its own backend. That's a business
model for third parties, not what we want for a self-contained Amplifier experience. We moved
away from this correctly. The JSONL-first approach is right.

> *Ken: validate that the right source event is `llm:response` (Brian confirmed: it IS a
> canonical core event, defined in core, emitted by the orchestrator). The hook logging module
> reads that same event and persists it. Our cost library should subscribe to `llm:response`
> directly and stamp cost at call time.*

**S3. The Rust scanner (summaries.db)**  
A Rust-based scanner that pre-computes session summaries into SQLite was committed but never wired
into the server. The code is dead right now (`db.py` exists but `server.py` never imports it).
Good idea for performance at scale, not unblocking anything today.

---

## 2. Decisions Made in the Alignment Call

*(Brian + Ken + Salil, cont'd meeting)*

| Decision | Detail |
|---|---|
| **Library delivery = Amplifier bundle** | A new repo `amplifier-bundle-cost-management` (name TBD). Python library inside a bundle. NOT inside the app repo. NOT a standalone PyPI package. Intentionally Amplifier-ecosystem-scoped. |
| **Repo separation** | `amplifier-bundle-cost-management` (new) + `amplifier-app-cost-viewer` (stays). The bundle becomes a hard Python dependency of the app. |
| **Cost stamped at call time** | Cost must be calculated and stamped onto the `llm:response` event at the moment it fires — not retroactively. Retroactive calculation is "fake data." |
| **Provider-level cost calculation** | Salil's proposal, Brian agreed: bake cost calculation into each individual provider. Provider author is responsible for accurate cost data (especially important for subscription-based/GCSP providers where billing differs from raw token counts). |
| **Cache tokens need to become first-class** | Currently not in the provider interface contract (in metadata). This cost work is the forcing function to make it first-class. Additive change to core, not breaking. |
| **Core changes = additive only** | DTU test in core, smoke test, version bump. No breaking changes. No new deps like pytest — use the existing validation approach. |
| **Separate design doc from plan** | The outline is fine as overview. Next step: write a design doc (where each piece lives) separately from the implementation plan (ordered flat task list). |
| **Viewer: "good enough for now"** | Keep as-is. One-line installable. Show Thursday. Will be retooled to consume the bundle library later. |
| **Pre-call budget estimation** | Brian: "Don't put time on that yet." The right future direction (estimate tokens before the call, warn if over budget) but not needed for P1–P2. |

---

## 3. Work To Be Done — Outline With Priorities

Brian's architecture from the call, now with repo names:

```
amplifier-bundle-cost-management  (NEW REPO)
  ├── Python library: pricing, cost calculation, token normalization
  ├── hook module: subscribes to llm:response, stamps cost, emits per-turn total
  └── tools module: query session cost, etc.
          ↓ bundle is a Python dependency of:
amplifier-app-cost-viewer  (EXISTING REPO, keep)
  └── viewer swaps reader.py/pricing.py guts → uses bundle library
          ↓ hook is thin wrapper to:
amplifier-app-cli  (existing)
  └── status line: per-request + per-turn cost display (fixed)
          ↓ eventually also:
Resolve, web app, other surfaces
```

---

### Priority 1 — Fix the Measurement (enables everything else)

These are bugs, not features. Nothing above them is trustworthy until they're fixed.
P1 is one cohesive chunk — do all of it.

| # | Work | Why now |
|---|---|---|
| 1a | Fix cache token alias map in `reader.py` (map `cache_creation_input_tokens`, `cache_read_input_tokens`, OpenAI nested `prompt_tokens_details.cached_tokens`) | Sessions using prompt caching are overcounted by up to 5× |
| 1b | Add missing model families to `pricing.py` (`claude-3-5-sonnet/*`, `claude-3-5-haiku/*`, `gemini-1.5/*`, Bedrock prefixes) | Fixes silent $0 on large swaths of historical sessions |
| 1c | Add `logger.warning` + `/api/pricing/misses` for unknown models | Surfaces future gaps immediately |
| 1d | Add `cache_read_tokens` / `cache_write_tokens` to `SessionNode` rollup and UI summary | Makes real cost structure visible in list view |
| 1e | Verify empirically: does parent `events.jsonl` inline child `llm:response` events? | Determines if tree rollup is double-counting |
| 1f | Make viewer one-line installable (`uv tool install` from git, no clone needed) | Brian's explicit request; needed before Thursday demo |

**Exit criterion**: Pick 3 real Amplifier sessions. Viewer's reported cost within 15% of Anthropic dashboard billing. Currently we cannot make that claim.

---

### Priority 2 — The Bundle + Library (Brian's primary ask)

> *"Get all of these things into more library form... minimally wrapped around that for whenever
> we expect something to be more than just a single need."* — Brian

**Step 1: Create the new repo**
- Name: `amplifier-bundle-cost-management` (or similar, confirm with Brian/Salil)
- Structure: Python library + hook module + optional tools module

**Step 2: Migrate existing code**
- Move `pricing.py` and token-normalization logic from the viewer into the bundle library
- Extend with correct cache alias map (P1 work feeds directly here)
- Write/fix tests — no pytest as dep, use existing validation approach per core standards

**Step 3: Write the hook module**
- Subscribe to `llm:response` (canonical core event)
- Stamp cost at call time: `{model, input_tokens, cached_tokens, output_tokens, cost_usd}`
- Accumulate per-turn total; emit when turn boundary detected
- Ask core for IoC slotting / advertising hook on the status line (like error display capability)

**Step 4: Wire hook to CLI status line**
- Fix what the status line shows today (per-request cost, cache breakdown)
- Add per-turn accumulated total (doesn't exist today)
- "The status plugin is already there" — this is a shorter piece of work than it looks

**Step 5: Retool the viewer**
- Replace `reader.py` / `pricing.py` with bundle library as Python dependency
- FastAPI server and UI remain as thin wrapper

**Design questions to address in the design doc (before building):**
- Q1: Exact repo name for the bundle? *(Lean toward `amplifier-bundle-cost-management`)*
- Q2: Does the `llm:response` event currently carry all the fields we need, or do we need an
  additive change to core to normalize cache token fields into the event payload?  
  *Brian: "That's the question to get answered." Ken to investigate where hook-logging gets its
  data from and whether it's coming from the event or somewhere else.*
- Q3: LiteLLM structured data as the validation source when updating provider-baked costs?
  *(Answer: yes — LiteLLM is the "validation" when we update our own pricing table)*
- Q4: Do tokenizer APIs return cost in providers? Models endpoint, additional model details
  endpoint, raw LLM response — can we add a query param to get cost estimates? (Mauri/GHCP —
  subscription scenarios)

---

### Priority 3 — Loop Guardrails *(acknowledged, not immediately scheduled)*

> *"If you're asking a machine to do this, it might cost you 40 bucks."*

Salil's design direction (aligned): at `provider:request` time, if accumulated session cost
exceeds a threshold, warn user / offer to change model. Brian: "Don't put time on that yet —
it needs a bigger investment. But it IS high on our priority list."

Short-term stopgap (when capacity allows):
- Add `max_turns` config to browser-operator and browser-researcher agents
- Log iteration count in convergence loops so the viewer can flag "this loop ran 47 times"

Longer-term (requires design + likely additive core change):
- Budget-aware pre-call hook using `provider:request` event
- Intent-based model routing when cost threshold is approaching

---

### Priority 4 — Context Efficiency (the GSD gap) *(design-first, longer horizon)*

The 4-8× token cost delta vs. GSD/Aider comes from context accumulation, not model choice.
Real-time knowledge of budget can affect how orchestration is done — this is the "dial" Ken
described. Flag for design discussion:

- Audit `context_scope` usage across registered agents
- Pilot GSD-style fresh-context-per-plan on a defined workflow; measure token delta
- Surface per-delegation token cost in the viewer

---

### Priority 5 — Evergreen Pricing Maintenance *(ongoing, low friction)*

Brian called the foundation layer "evergreen" — new models ship weekly.

- `scripts/update_pricing.py` runs against LiteLLM catalog; becomes a scheduled/triggered update
- Track `pricing_misses`; file a tracking issue when new model appears with no pricing entry
- **Ken maintains provider pricing table and can be deputized for provider maintenance** per Brian

---

## 4. Next Concrete Actions (post-alignment)

In priority order, what to do next:

1. **Write the design doc** — separate from this outline. Cover: where each piece lives (bundle
   vs app vs core), what the `llm:response` event currently contains, whether cache fields need
   an additive core change, and how cost stamping works across providers. Brian's ask.

2. **P1 fixes** (1a–1f) — fix measurement in the existing viewer; make it one-line installable;
   demo Thursday.

3. **Investigate `llm:response` event payload** — does hook-logging pull from the event directly?
   Are cache fields present? This determines whether P2 library can be built without a core change
   or if an additive core change is needed first.

4. **Look up Amplifier masterclass** — Brian mentioned this as onboarding context for the
   ecosystem patterns.

---

## 5. Notes from Alignment Call

*(Raw notes, to be processed into design doc)*

- **DTU test in core, smoke test, version bump.** Additive changes only in core, please. Do not
  take `pytest` as a dep — use the existing validation approach when touching core.
- **Separate design from plan.** The outline is the overview. Next deliverable: (a) design doc
  showing where things live, (b) flat ordered task list for execution.
- **LiteLLM structured data = validation.** When we update our own provider "baked-in" costs,
  LiteLLM catalog is the process/validation source. Update when we want to update the model.
- **Ask core for advertising / IoC slotting on the status line.** Like how error display works
  as a capability — cost should be a first-class slot, not bolted on.
- **Look up Amplifier masterclass.** Brian referenced this as onboarding context.
- **Tokenizer API investigation.** Do provider APIs return cost estimates? Look at: models
  endpoint, models additional/details endpoint, raw LLM response. Can we add a query param to
  get token/cost estimates? Relevant for GHCP/Mauri subscription-based pricing scenarios.
- **"Resolve" context.** Brian's Resolve system uses Amplifier session and can trace context
  intelligence all the way through DTUs and reality-check sessions — cost visibility will plug
  into that chain. Cost library = base layer for all of this.
- **Viewer is "good enough for now."** Brian: "I would call that basically good enough for now
  on that." Let it sit as-is, show it Thursday, retool guts later when bundle is ready.

---

## 6. One-Page Summary (quick reference)

```
WHAT WE HAVE:
  ✓ Working cost viewer: event log parser, pricing, session tree, canvas UI
  ✓ Research doc: 4-8× harness cost delta confirmed, architectural root cause identified
  ✓ Understanding of 3 root causes: measurement bugs, context accumulation, no guardrails

WHAT'S BROKEN (measurement — P1):
  ✗ Cache tokens aliased wrong → up to 5× overcount on cache-heavy sessions
  ✗ 3-5 model families missing from pricing → silent $0 on historical sessions
  ✗ No per-turn cost anywhere
  ✗ Viewer not one-line installable

ARCHITECTURE DECIDED:
  amplifier-bundle-cost-management (NEW)
    → Python library: pricing + token normalization
    → hook module: stamp cost at llm:response, per-turn total
    → is a dependency of the app AND the CLI status line
  amplifier-app-cost-viewer (KEEP, retool guts later)
  amplifier-app-cli (status line gets fixed via hook)

PRIORITIES:
  P1: Fix measurement + one-line install (days) — demo Thursday
  P2: Build the bundle/library (weeks) — the real deliverable
  P3: Loop guardrails (capacity-dependent) — $40/invocation problem
  P4: Context efficiency (design-first, longer horizon) — the GSD gap
  P5: Evergreen pricing maintenance (ongoing, Ken owns)

NEXT: Write design doc → P1 fixes → investigate llm:response event payload
```
