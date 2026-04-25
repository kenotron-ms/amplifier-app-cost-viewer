# Amplifier Cost Viewer Design

## What We're Building

`amplifier-cost-viewer` is a lightweight, zero-infrastructure web viewer for analysing Amplifier session cost and performance. It runs in-place with `uvx`, reads flat files directly from disk, and needs no Docker, no external services, and no database. It lives as a new independently-installable package inside the existing `token-cost` repo.

---

## Goal

A lightweight, zero-infra web viewer for Amplifier session cost and performance analysis that reads flat files from disk and can be launched with `uvx`.

## Background

Amplifier sessions emit detailed event logs (`events.jsonl`) and observability summaries to `~/.amplifier/`. Analysing cost and timing currently requires custom scripting. There is no visual tool that shows how a session spent its time and money across a delegation tree. This package fills that gap with a Chrome DevTools Network-tab-style Gantt view, letting engineers immediately see which delegates, models, and tools dominated cost and latency.

## Approach

A new dedicated package `amplifier-app-cost-viewer` is added inside the existing `token-cost` repo under `viewer/`. It is independently installable and has no coupling to the existing hook package. The backend is FastAPI; the frontend is vanilla JS with SVG rendering and requires no build step. The package can be extracted to its own repo later without structural changes.

## Architecture

Two independently installable packages co-exist in the repo:

```
token-cost/
├── src/amplifier_module_hook_observability/   ← existing hook (unchanged)
├── viewer/
│   ├── pyproject.toml                         ← amplifier-cost-viewer package
│   └── amplifier_app_cost_viewer/
│       ├── server.py      FastAPI app + route handlers
│       ├── reader.py      events.jsonl parser, span extractor, tree builder
│       ├── pricing.py     LiteLLM cache loader + static fallback dict
│       └── static/
│           ├── index.html
│           ├── app.js     Gantt renderer (SVG), session tree, detail panel
│           └── style.css
└── scripts/
    └── update_pricing.py  fetches LiteLLM JSON → regenerates pricing.py
```

**Launch command:**

```bash
uvx --from ./viewer amplifier-cost-viewer
```

## Components

### `server.py` — FastAPI backend

Serves the API and static assets. All data processing is triggered on demand when a session is requested; there is no background indexing.

API routes:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/sessions` | Recent root sessions sorted by recency, with total cost + duration |
| `GET` | `/api/sessions/{id}` | Full delegation tree + aggregated costs for one root session |
| `GET` | `/api/sessions/{id}/spans` | All spans for Gantt rendering (events + computed costs) |
| `GET` | `/static/*` | Serve `index.html`, `app.js`, `style.css` |

Results are cached in memory per session. No persistence layer.

### `reader.py` — Event log parser

Reads `events.jsonl` files and produces structured span data:

- Pairs `provider:request` → `llm:response` into **LLM spans**
- Pairs `tool:pre` → `tool:post` (matched by `tool_call_id`) into **tool spans**
- Pairs first `thinking:delta` → `thinking:final` into **thinking spans**
- Gaps between spans are surfaced as orchestrator overhead (dark space in the Gantt — no bar rendered)

Also reads `metadata.json` per session to extract `parent_session_id` and `created` timestamp for tree construction.

### `pricing.py` — Cost computation

Loads the LiteLLM `model_prices_and_context_window.json` pricing table. For each LLM span computes:

```
cost_usd = input_cost + output_cost + cache_read_cost + cache_write_cost
```

Model lookup uses longest-prefix matching on model name strings consistent with the existing hook's approach. Unknown models are flagged visually in the UI with `$?`.

Pricing is cached at `~/.amplifier/pricing-cache.json`. A `"pricing last updated"` timestamp is shown in the viewer.

### `update_pricing.py` — Pricing refresh script

Located at `scripts/update_pricing.py`. Fetches the LiteLLM JSON from GitHub and regenerates `pricing.py`. Can be run manually or scheduled via cron. Falls back to the static dict bundled in `pricing.py` when the network is unavailable.

Attribution to LiteLLM is included in the `pricing.py` header and the README.

### `static/app.js` — Frontend (vanilla JS, no build step)

Implements the full three-pane UI:

- **Session tree** — expandable/collapsible delegation tree with per-node subtotal cost
- **Gantt** — SVG-rendered timeline, time relative to root `session:start`
- **Detail panel** — slides up on span click

No framework, no bundler, no compile step.

## Data Sources

### Primary — `events.jsonl`

Path: `~/.amplifier/projects/<slug>/sessions/<id>/events.jsonl`

Provides:
- Full wall-time visibility (every kernel event with timestamps)
- Token counts (from `llm:response` event usage data)
- Tool I/O (from `tool:pre` / `tool:post` event data, when `log_io=true`)

Cost is computed by applying `pricing.py` to each LLM span. Used for the Gantt view.

### Secondary — observability JSONL

Path: `~/.amplifier/observability/<session_id>.jsonl`

Provides:
- Pre-computed cost totals from `session_summary` events (fast, no full `events.jsonl` scan)
- `parent_session_id` links for tree building

Used **only** for the session list sidebar. Not used for Gantt rendering.

## Data Flow

Five stages run server-side on demand when a session is selected:

### 1. DISCOVER

Scan `~/.amplifier/projects/*/sessions/*/` for `events.jsonl` + `metadata.json`. Read `parent_session_id` and `created` timestamp. Build the delegation tree. Sort root sessions by recency.

### 2. PARSE

For each session in the tree, read `events.jsonl` and pair start/end events into spans:

| Span type | Start event | End event | Match key |
|-----------|-------------|-----------|-----------|
| LLM | `provider:request` | `llm:response` | sequence |
| Tool | `tool:pre` | `tool:post` | `tool_call_id` |
| Thinking | first `thinking:delta` | `thinking:final` | sequence |

Gaps between spans are retained as orchestrator overhead.

### 3. COST

For each LLM span, look up the model in the pricing table and compute:

```
cost_usd = input_cost + output_cost + cache_read_cost + cache_write_cost
```

### 4. AGGREGATE

Walk the delegation tree bottom-up. Sum `cost_usd` to each parent. The root node carries the total cost of the entire job including all delegates.

### 5. NORMALIZE

Convert all timestamps to milliseconds offset from the root session's `session:start` event. Child session timelines are aligned to the moment their `session:start` fired within the parent timeline.

### Output JSON structure

```json
{
  "session_id": "4fd2cf85",
  "duration_ms": 2700000,
  "cost_usd": 3.24,
  "spans": [
    {
      "type": "llm",
      "start_ms": 0,
      "end_ms": 8700,
      "provider": "anthropic",
      "model": "claude-sonnet-4-6",
      "cost_usd": 0.034,
      "input_tokens": 512,
      "output_tokens": 128,
      "input": ["..."],
      "output": "..."
    },
    {
      "type": "tool",
      "start_ms": 8900,
      "end_ms": 9242,
      "tool_name": "bash",
      "success": true,
      "input": {},
      "output": "..."
    }
  ],
  "children": [
    { "session_id": "...", "spans": ["..."], "children": ["..."] }
  ]
}
```

## UI Layout

Three-pane layout styled after the Chrome DevTools Network tab:

```
┌─────────────────────────────────────────────────────────────────┐
│ [-Users-ken ▾] [4fd2cf85 — Today 11:45 ▾]  $3.24 total  [↺]   │
├──────────────────┬──────────────────────────────────────────────┤
│ SESSION TREE     │ 0s      10s      30s      1m       ... 45m   │
│                  │ ──────────────────────────────────────────── │
│ ▼ 4fd2cf85       │ [llm▓▓▓][t][llm▓▓▓▓▓▓][··delegate··▒▒▒▒▒] │
│   ▼ explorer     │                         [llm▓▓▓▓▓▓▓▓▓▓▓▓▓] │
│       (child)    │                              [t][llm▓▓▓▓▓▓] │
│   ─ git-ops #1   │          [llm▓▓][t][llm▓]                   │
│   ─ git-ops #2   │                                      [llm▓] │
│   ─ web-research │                                        [llm] │
├──────────────────┴──────────────────────────────────────────────┤
│ anthropic / claude-sonnet-4-6          +2.1s → +10.8s  (8.7s)  │
│ in: 512  out: 128  cache_read: 52,495   $0.034                  │
│ INPUT  [{"role":"user","content":"..."}]                         │
│ OUTPUT "The short answer: not exactly..."                        │
└─────────────────────────────────────────────────────────────────┘
```

**Top bar** — project dropdown + session dropdown (recency sorted), tree total cost, refresh button. No project-filter dropdown in the initial release.

**Left column (~220px)** — delegation tree, expandable/collapsible. Each row shows the session name and its subtotal cost. Clicking a row scrolls the Gantt to that session's lane.

**Gantt (right, flex)** — time axis relative to root session start. Dark background between spans = visible orchestrator overhead (the emptiness is the signal). LLM spans are coloured by provider, tool spans are slate gray, delegate spans render as a range bar that expands into the child session row below. Rendered in SVG.

**Bottom detail panel** — slides up when a span is clicked.

## Color Coding

Provider maps to a hue; model tier maps to saturation:

```
anthropic    →  purple        #7B2FBE
  claude-opus              100% saturation
  claude-sonnet             70% saturation
  claude-haiku              50% saturation

openai       →  teal          #10A37F
  gpt-4.5 / gpt-4o         100% saturation
  gpt-4o-mini               55% saturation

google       →  blue          #4285F4
  gemini-pro / 2.0          100% saturation
  gemini-flash               55% saturation

azure        →  blue-violet   #3B82F6
unknown      →  amber         #F59E0B

tool calls       →  slate gray    #64748B  (all tools the same)
thinking spans   →  indigo        #6366F1
orchestrator     →  (dark gap, no bar rendered)
```

Color lookup uses the same model-name prefix strings as `pricing.py`, resolved with longest-match-first.

## Session List

The sidebar shows only root sessions (those without a `parent_session_id`). Each row:

```
4fd2cf85  token-cost  Today 11:45   $3.24   45m
48b20414  token-cost  Yesterday     $0.21    8m
```

Cost and duration are read from the observability JSONL `session_summary` record — a fast lookup that avoids scanning full event logs. Sessions still in progress show a live `⬤` indicator alongside partial cost. The project name is derived from the terminal folder name embedded in the project slug (leading `-`-encoded path separators are stripped).

## Detail Panel

Slides up when any span is clicked. Three variants depending on span type:

**LLM call:**
```
anthropic / claude-sonnet-4-6          +2.1s → +10.8s  (8.7s)
in: 512  out: 128  cache_read: 52,495  cache_write: 3,598   $0.034
INPUT   [{"role": "user", "content": "..."}]
OUTPUT  "The short answer: not exactly..."
```

**Tool call:**
```
bash  ✓                                +10.9s → +11.2s  (342ms)
INPUT   {"command": "ls -la ~/.amplifier/observability/"}
OUTPUT  "total 208\n-rw-r--r-- 1 ken staff 16141..."
```

**Orchestrator gap** (click dark space between spans):
```
orchestrator overhead                  +11.2s → +14.6s  (3.4s)
(between bash and next LLM call)
```

Input/output is only shown when `log_io=true` was set during the session. Long values are truncated at ~2000 characters with a "show more" toggle.

## Error Handling

- **Missing pricing data** — unknown models are flagged in the UI with `$?` rather than a hard error.
- **Missing observability JSONL** — session list falls back to computing cost from `events.jsonl` directly (slower, but functional).
- **Incomplete/truncated event logs** — sessions still running are detected and shown with the `⬤` live indicator; partial data is rendered as-is.
- **Network unavailable for pricing update** — `update_pricing.py` fails gracefully and the static dict bundled in `pricing.py` is used as fallback.
- **Unpaired events** — spans missing a matching end event are silently dropped from the Gantt (not surfaced as errors to the user).

## Testing Strategy

- **Unit tests for `reader.py`** — test span pairing logic against synthetic `events.jsonl` fixtures covering: paired spans, unpaired starts, unpaired ends, out-of-order events, and in-progress sessions.
- **Unit tests for `pricing.py`** — test cost computation against known token counts for a small set of models; test longest-prefix matching; test fallback behaviour when the cache file is absent.
- **Unit tests for tree building** — test DISCOVER + AGGREGATE stages against a fixture directory of sessions with known parent/child relationships.
- **API integration tests** — use FastAPI's `TestClient` to exercise all four routes against fixture data.
- **Manual browser testing** — no automated frontend tests in the initial release; the SVG Gantt and detail panel are verified manually.

## Open Questions

None — design fully validated.
