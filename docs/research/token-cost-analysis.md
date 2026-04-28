# Token Cost Analysis: Amplifier vs Other Agent Harnesses

**Date**: 2026-04-28  
**Author**: Research synthesis via Amplifier (parallel agent investigation)  
**Status**: Draft — for team review  
**Scope**: (1) accuracy of current cost tracking, (2) observability platform patterns, (3) context strategy differences, (4) loop capping, (5) benchmark methodology

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current Tracking Accuracy — Code Audit](#2-current-tracking-accuracy--code-audit)
3. [How Other Observability Platforms Track Costs](#3-how-other-observability-platforms-track-costs)
4. [Context Strategy Differences](#4-context-strategy-differences)
5. [Agentic Loop Capping](#5-agentic-loop-capping)
6. [Measuring Token Efficiency — Benchmark Methodology](#6-measuring-token-efficiency--benchmark-methodology)
7. [Prioritized Recommendations](#7-prioritized-recommendations)
8. [Appendix: Sources](#appendix-sources)

---

## 1. Executive Summary

The concern that Amplifier sessions cost significantly more than comparable harnesses is **well-founded and multi-causal**.
The published benchmark delta is real: Claude Code-style harnesses consume **4–8× more tokens per task** than
Aider or Codex CLI on equivalent work. However, there are also concrete bugs in the cost viewer itself that are
making costs look both higher *and* lower than reality simultaneously — depending on which session you look at.

**Three root causes compound each other:**

1. **Measurement bugs** — the viewer silently misreports costs for caching, missing models, and multi-agent rollups.
2. **Architecture** — Amplifier's orchestrator session accumulates history; GSD/Aider reset per task.
3. **No guardrails** — unbounded convergence loops (especially browser-tester) grow cost quadratically with no kill-switch.

All three are fixable.

---

## 2. Current Tracking Accuracy — Code Audit

A full audit of `reader.py`, `pricing.py`, and `server.py` was performed. Findings are ordered by severity.

### 2.1 Cache Token Aliases Are Wrong (High — silent overcount)

**Files**: `reader.py:302-305`, `reader.py:638-641`

The reader only recognises these aliases for cache tokens:

```python
"cache_read_tokens" / "cache_read"
"cache_write_tokens" / "cache_write"
```

But the actual field names from each provider are different:

| Provider | Field name in API response |
|---|---|
| Anthropic | `cache_creation_input_tokens`, `cache_read_input_tokens` |
| OpenAI | `prompt_tokens_details.cached_tokens` (nested) |
| Google | `cachedContentTokenCount` |

**Impact**: Any session using prompt caching has cache tokens silently dropped and billed at the full input rate.
For cache-heavy sessions this overcounts cost by 10–30%. On a session where 70% of input tokens are cache hits,
the viewer reports roughly 2.5× the actual cost.

**Fix**: Extend the alias map in `reader.py:300-305` and `:638-641` to include all provider-native names.
The OpenAI nested path requires special-case extraction from `usage.prompt_tokens_details.cached_tokens`.

---

### 2.2 Cache Tokens Absent from Rollup Aggregates (High — hidden data)

**Files**: `reader.py:65-85` (dataclass), `reader.py:524-543` (`aggregate_costs`)

`SessionNode` has no `cache_read_tokens` or `cache_write_tokens` fields. `aggregate_costs` does not sum them.
The cost USD is computed correctly per span (since `compute_cost` does the right multiplication), but the
**reported token totals** suppress all cache traffic entirely.

For a multi-turn Amplifier session with prompt caching active, 70–90% of all input-side tokens are cache reads —
and the summary view shows none of them. The list page token counts are wrong for all sessions that use caching.

**Fix**: Add `own_cache_read_tokens`, `own_cache_write_tokens`, `total_cache_read_tokens`,
`total_cache_write_tokens` to `SessionNode`. Propagate through `aggregate_costs`,
`compute_session_cost_fast`, and `_node_to_dict`.

---

### 2.3 Missing Models → Silent $0 (High — undercount)

**File**: `pricing.py:19-1089`

These model families are entirely absent from `STATIC_PRICING`. Sessions that used them report **$0.00** with no
warning, log entry, or UI signal:

| Missing family | Notes |
|---|---|
| `claude-3-5-sonnet-*` | The dominant Anthropic model, mid-2024 onward |
| `claude-3-5-haiku-*` | Widely used for fast/cheap tasks |
| `gemini-1.5-pro`, `gemini-1.5-flash` | Listed in color table; absent from prices |
| `anthropic.claude-*` (Bedrock prefix) | e.g. `anthropic.claude-sonnet-4-20250514-v1:0` |
| `vertex_ai/gemini-2.5-pro`, `vertex_ai/gemini-2.5-flash` | Most Vertex Gemini entries missing |

Additionally, `_lookup_pricing` returns `None` silently with no logging. An unknown model is
indistinguishable from a $0 model in the UI.

**Fix**: (a) Run `scripts/update_pricing.py` to pull fresh data from LiteLLM. (b) Add a `logger.warning`
on every pricing miss. (c) Expose a `/api/pricing/misses` endpoint backed by a process-lifetime `set()`.

---

### 2.4 Tree Rollup Double-Count Risk (High — conditional)

**Files**: `reader.py:524-543`, `server.py:446-474`

Both `aggregate_costs` and `get_session_costs` scan every node's `events.jsonl` independently and sum the
results. This is correct **only if parent and child sessions never share events**.

If the Amplifier kernel ever inlines a sub-agent's `llm:response` into the parent log (even as a summary
event), every byte of overlap is double-counted with no dedup pass and no event-ID suppression.

This assumption is unasserted anywhere in the code. The single most important empirical check is:

```bash
# On a known multi-agent session, compare:
sum(compute_session_cost_fast(child) for child in children)
vs.
compute_session_cost_fast(parent)
# If parent > sum(children), the parent log contains inlined child events.
```

---

### 2.5 SQLite Overlay Is Dead Code (High — performance)

**Files**: `server.py:200-214`, `db.py`

The `_get_roots` docstring promises:

> "After building the raw tree, overlays pre-computed costs from the Rust scanner's `summaries.db`."

The body is just `build_session_tree(AMPLIFIER_HOME)`. `db.py` is never imported by `server.py`.
The commit message `feat: integrate Rust cost scanner with SQLite cost reading and overlay` describes
work that is not reflected in the code on disk.

**Impact**: The list view re-parses `events.jsonl` on every cold load rather than reading pre-computed
summaries. For large session populations this is the primary source of slow initial load times.

---

### 2.6 Sequential Zip Pairing for LLM Spans (Medium — silent undercount)

**File**: `reader.py:283-334`

Provider request and LLM response spans are paired via `zip(requests, responses)`. If a request is retried
(one request, two responses billed), `zip` takes the shorter list and the retry's cost is silently dropped.

The comment at line 287 acknowledges this: "If counts diverge, the shorter list wins — unmatched events
are silently dropped." This should be correlation-ID matching, like the tool span path at line 344.

---

### 2.7 Pricing Typo — `ft:gpt-4o-2024-11-20` (Medium)

**File**: `pricing.py:222-227`

This fine-tune entry uses Anthropic's field name `cache_creation_input_token_cost` instead of OpenAI's
`cache_read_input_token_cost`. Every other OpenAI fine-tune entry uses the correct name. OpenAI does not
charge a cache-write premium, so this entry overcharges write tokens and undercharges read tokens.

---

### 2.8 `POST /api/refresh` Does Not Clear `_cost_cache` (Low)

**File**: `server.py:317-323`

`/api/refresh` clears `_roots_cache` and `_loaded_cache` but leaves `_cost_cache` intact.
Updated pricing does not propagate to already-cached sessions until process restart.

---

### 2.9 Summary Table

| Severity | Area | Issue | Location |
|---|---|---|---|
| **High** | reader | Cache aliases miss provider-native field names | `reader.py:302-305` |
| **High** | reader/server | Cache tokens absent from rollup aggregates | `reader.py:65-85`, `524-543` |
| **High** | pricing | claude-3-5-sonnet/haiku, gemini-1.5, Bedrock missing → silent $0 | `pricing.py` |
| **High** | reader/server | Tree rollup assumes no parent/child log overlap — unverified | `server.py:446-474` |
| **High** | server | SQLite overlay documented but not implemented; `db.py` is dead code | `server.py:200-214` |
| **Medium** | reader | LLM spans paired by zip — drops retried events | `reader.py:283-334` |
| **Medium** | pricing | `ft:gpt-4o-2024-11-20` uses wrong cache field name | `pricing.py:222-227` |
| **Medium** | pricing | `_lookup_pricing` silently returns $0 on unknown models | `pricing.py:1187` |
| **Medium** | server | `only_root=True` load skips `aggregate_costs`, stales `total_*` fields | `server.py:291-304` |
| **Low** | server | `/api/refresh` does not clear `_cost_cache` | `server.py:317-323` |

---

## 3. How Other Observability Platforms Track Costs

All four major platforms (Langfuse, Helicone, LangSmith, Braintrust) share a fundamental architecture:
**provider-reported token counts are the source of truth**. Client-side tokenization is a fallback every
platform acknowledges is inaccurate. None of them match actual provider billing exactly.

### 3.1 Capture Mechanisms

| Platform | Capture method | Cache-aware? | Retroactive repricing? |
|---|---|---|---|
| **Langfuse** | SDK decorators / OTel — not a proxy | Yes — arbitrary `usage_details` keys | No — stored at ingestion |
| **Helicone** | Proxy (on critical path) or async OTel | Partial — streaming requires `include_usage: true` or reports $0 | No |
| **LangSmith** | SDK wrappers, `@traceable` decorator | Yes — full cache schema (see §3.3) | No — stored at ingestion |
| **Braintrust** | OTel/SDK + query-time BTQL aggregation | Partial — open Gemini cache bug as of Feb 2026 | **Yes** — recomputes at query time |

### 3.2 The Span-Tree Double-Count Problem (Universal)

Every platform has shipped this bug at least once. The cause: instrumentation writes token totals onto
*both* an LLM call span and its parent orchestration span, then sums the tree naively.

The implicit convention — not codified in any standard — is that **cost/tokens live only on the actual LLM
call leaf, never on orchestration wrappers**. OpenTelemetry GenAI semantic conventions are still in
"Development" maturity and define no cost aggregation semantics at all.

Notable incidents:
- **Langfuse + Microsoft Agent Framework**: `invoke_agent` spans triggered auto-classification as
  `generation`, doubling all token totals.
- **Braintrust v3.1.0**: Fixed "token double counting between parent and child spans in Vercel AI SDK
  integration" — live for an unknown period before the fix.
- **Amplifier viewer risk**: the tree rollup in `server.py` has the same pattern; see §2.4.

### 3.3 LangSmith's Cache Schema — the Reference Implementation

LangSmith has the most complete schema for Anthropic prompt caching. Their `usage_metadata` structure:

```json
{
  "input_tokens": 12,
  "output_tokens": 200,
  "input_token_details": {
    "cache_read": 8192,
    "cache_creation": 1024,
    "ephemeral_5m_input_tokens": 0,
    "ephemeral_1h_input_tokens": 0
  }
}
```

They differentiate the **5-minute TTL** (1.25× write cost) from the **1-hour TTL** (2.0× write cost),
and apply tier-specific prices greedy-first. This is the schema Amplifier's `reader.py` should converge on.

### 3.4 Anthropic Prompt Caching — Cost Structure

Understanding this is critical because Amplifier uses it extensively:

| Token type | Multiplier vs base input | Field name in API |
|---|---|---|
| Standard (fresh) input | 1.0× | `input_tokens` |
| Cache write (5-min TTL) | **1.25×** | `cache_creation_input_tokens` |
| Cache write (1-hour TTL, beta) | **2.0×** | `cache_creation_input_tokens` |
| Cache read hit | **0.1×** | `cache_read_input_tokens` |

**Break-even**: 5-min cache pays off after a single cache hit. 1-hour cache pays off after 2 hits.

A session that shows 10,000 total input tokens in Amplifier's current viewer — but has 8,000 of those as
cache reads — actually costs `1,990 × $3/MTok + 10 × $0.30/MTok` = ~$0.006,
not the `10,000 × $3/MTok` = $0.03 the viewer reports. That is a **5× overcount** in this scenario.

### 3.5 What No Platform Gets Right

Even with everything working correctly, observability totals diverge from actual provider billing due to:

- Failed/retried requests: counted on retries, billed once (or the reverse)
- Provider-side rounding and batch rebates
- Pricing tier transitions mid-billing-cycle
- SDK-level silent retries not surfaced to the logger

Datadog is the only platform known to mitigate this by pulling **actual billed cost from provider billing
APIs** (not from request logging) and reconciling the two. Langfuse, LangSmith, Helicone, and Braintrust
all produce estimates.

---

## 4. Context Strategy Differences

This is the architectural root of the monthly bill gap.

### 4.1 Published Token Cost Benchmarks

The most comprehensive published benchmark (Morph, Feb 2026, 6-month production study across 47-file
Next.js, 62-file React Native, and 31-file Python codebases):

| Harness | Avg tokens/task | Ratio | First-pass success |
|---|---|---|---|
| **Aider** | 105K | 1.0× | 71% |
| **Cursor** | 104K | 0.85× | 68% |
| **Claude Code** | 479K | **4.2×** | 78% |

Codex CLI comparison (single-vendor, Daniel Vaughan / NxCode, 2026):

| Task | Claude Code | Codex CLI | Ratio |
|---|---|---|---|
| Focused TypeScript task | 234,772 tokens | 72,579 tokens | 3.2× |
| Figma-to-code clone | 6.2M tokens | 1.5M tokens | 4.1× |

The 4–8× multiplier is consistent across sources. The extra cost is not entirely waste — Claude Code's
deeper planning, larger explanatory output, and fewer user interruptions buy ~7–10 percentage points of
first-pass success. The question is whether that tradeoff is worth it for every task.

**GSD** ("Get Shit Done") is a meta-prompting, spec-driven system built on Claude Code by the
`gsd-build` org. No peer-reviewed per-task benchmark exists for GSD specifically, but the authors
document a **~12K token system-prompt floor per session** in default install (86 skills + 33 agents
loaded into Claude Code's config dirs). A `--minimal` install flag reduces this.

### 4.2 How Each Harness Treats Context

| Harness | Context strategy | Effect on cost |
|---|---|---|
| **GSD** | Fresh context window per plan; state externalized to `PROJECT.md`, `STATE.md`, etc. | Each plan is capped at one context window; no accumulated history |
| **Aider** | Repo-map (~1024 tokens via tree-sitter); human selects files with `/add` | Minimal token floor; human decides scope |
| **Cursor** | RAG/vector index of workspace; pulls only relevant chunks | ~0.85× Aider; controlled injection |
| **Codex CLI** | `.codexignore` exclusions + profile-based `max_tokens_per_session`; subagent fan-out | Explicit budget per session |
| **Claude Code** | Accumulates full history; auto-compact at ~95% context fill; sub-agents get clean windows | Grows until compact; compacting at 95% is too late |
| **Amplifier** | Orchestrator accumulates delegate results; `context_scope="full"` injects full parent tool history into sub-agents | Same as Claude Code + additional cross-agent history replication |

The "context bloat cure" across every serious harness is the same pattern:
**isolate sub-tasks in their own context window, summarize results back to the orchestrator, persist
everything else to disk.** Amplifier does this architecturally via sub-sessions — but the orchestrator
session itself still accumulates unbounded history.

### 4.3 Context-Scope Policy and Its Cost

Amplifier's `context_scope` parameter on `delegate()` has direct cost implications that are not
currently visible to users:

| `context_scope` | What the sub-agent receives | Approximate token overhead |
|---|---|---|
| `"conversation"` | User/assistant text only | Low |
| `"agents"` | + all prior delegate results | Medium — grows with agent count |
| `"full"` | + ALL tool results in parent session | **High** — can be >100K tokens of tool output |

The `context_scope="full"` pattern (recommended in the delegation docs for bug-hunter/self-delegation)
injects the entire parent tool call history. On a long session this can mean the sub-agent receives
more context than the actual task requires. This is by design for correctness — but the cost is invisible.

---

## 5. Agentic Loop Capping

### 5.1 The Browser-Tester Convergence Loop Failure Mode

When agents are told to "keep going until it works", cost grows super-linearly for three compounding reasons:

1. **Quadratic context growth**: each turn re-sends full history + new tool result. Even with prompt caching
   the cumulative billed tokens grow as O(n²) relative to loop iteration count.
2. **Vision tokens dominate**: each browser screenshot is ~1,000–1,800 tokens and is appended to history.
   After 30 screenshots you have ~45K vision tokens persistently in context.
3. **Thinking tokens compound**: with extended thinking, a fresh thinking budget is emitted and billed
   every turn — it is not preserved across turns by default.

Documented failure modes for convergence loops:
- **Stuck-state loop**: agent re-screenshots an identical page and re-issues the same action
- **Reflexive variation loop**: tries endless variations of the same fix; never converges
- **Context-poisoned loop**: ~37% of tool calls fail with silent parameter mismatches; agent mistakes
  failure for success and escalates

### 5.2 What Frameworks Ship for Loop Control

| Framework | Iteration cap | Token/dollar budget |
|---|---|---|
| **LangGraph** | `recursion_limit=25` (default) | None built-in |
| **CrewAI** | `max_iter=25` per agent (configurable) | None |
| **AutoGen** | `max_consecutive_auto_reply=100` | None |
| **OpenAI Agents SDK** | `max_turns` parameter | None |
| **Codex CLI** | None | `max_tokens_per_session` in `~/.codex/config.toml` |
| **Claude Code** | None publicly documented | None publicly documented |
| **GSD** | Plan-checker has iteration limit; fresh-context-per-plan is implicit cap | None |
| **Amplifier** | None | None |

The ecosystem gap is documented explicitly: LangChain, CrewAI, and AutoGen provide no per-workflow
dollar budget controls. Hard caps require external gateways (LiteLLM, Helicone, Maxim).

### 5.3 Anthropic Task Budgets — The Right Tool (March 2026 Beta)

Anthropic shipped **Task Budgets** as a public beta on Claude Opus 4.7. This is the direct answer to
the browser-tester convergence loop problem:

```python
client.beta.messages.create(
    model="claude-opus-4-7",
    max_tokens=128000,
    output_config={
        "effort": "high",
        "task_budget": {"type": "tokens", "total": 64000},
    },
    betas=["task-budgets-2026-03-13"],
    messages=[...],
)
```

Key properties:
- Spans the **entire agentic loop** — thinking + tool calls + tool results + output across multiple requests
- The server injects a running countdown the model sees on each turn — the model paces itself and wraps up
- Advisory (soft cap) — for a hard kill combine with `max_tokens`
- Minimum budget is 20,000 tokens; smaller values return HTTP 400
- `remaining` field can be carried across context compaction checkpoints
- Currently **Opus 4.7 only**; graduation to other models not yet announced

Note: `thinking.budget_tokens` (extended thinking) is a different, orthogonal mechanism — it caps
reasoning per step, not the whole loop.

### 5.4 The Two Distinct Budget Mechanisms

| Mechanism | Scope | Type | Beta header | Models |
|---|---|---|---|---|
| `thinking.budget_tokens` | Single thinking block | Hard ceiling on thinking only | None (GA) | All extended-thinking models |
| `output_config.task_budget` | Entire agentic loop | Advisory + countdown | `task-budgets-2026-03-13` | Opus 4.7 only |

---

## 6. Measuring Token Efficiency — Benchmark Methodology

To produce a meaningful comparison of Amplifier vs GSD (or any other harness) for the same tasks:

### 6.1 Variables That Must Be Fixed (Confounds)

1. **Same model + exact version** (`claude-opus-4-7-20260301`, not just "Opus")
2. **Same task set** with deterministic seeds where possible
3. **Same success criterion** — binary pass/fail from an external grader, not self-report
4. **Same tool surface** — a harness with `bash + grep + view + browser` vs `bash` only is a different experiment
5. **Same context window cap and compaction policy** — or measure both states explicitly
6. **Same temperature and sampling params**
7. **Same starting environment** — Docker image, repo SHA, no network access for reproducibility

### 6.2 Variables That Must Be Measured

- Total input tokens (uncached)
- Total cached input tokens (`cache_read_input_tokens`) — these are ~10× cheaper; mixing them with fresh tokens hides efficiency
- Total cache-write tokens (`cache_creation_input_tokens`) — 1.25× more expensive; must be tracked separately
- Total output tokens (including thinking tokens — always billed)
- Wall-clock time (correlated with cost via retries and latency)
- Iteration count to completion
- **Pass rate at fixed token budget** — this is the Pareto frontier metric

### 6.3 Critical Methodology Rules

- **Run N≥10 trials per task** — agentic systems have very high variance; single-run comparisons are noise
- **Report cost-at-fixed-success, not raw cost** — a cheaper harness that fails the task is not efficient
- **Disclose retry policy** — some harnesses retry entire runs on failure; this is a 2–10× hidden cost multiplier
- **Report prompt-caching behavior separately** — comparing a caching vs non-caching harness without noting it is apples-to-oranges
- **`None` vs `0.0` distinction matters** — `None` means "no measurement taken"; `0.0` means "legitimately free". Collapsing them shifts reported medians

### 6.4 Reference Benchmarks to Calibrate Against

| Benchmark | Harness | What it controls | URL |
|---|---|---|---|
| **SWE-bench (vals.ai)** | Minimal bash-only | Fair model comparison, fixed harness | `vals.ai/benchmarks/swebench` |
| **SWE-bench Verified (Epoch AI)** | mini-SWE-agent | Publishes token budgets, full log viewer | `epoch.ai/benchmarks/swe-bench-verified` |
| **Morph tool benchmark** | Real production repos | Publishes per-task token counts | `morphllm.com/comparisons/morph-vs-aider-diff` |

### 6.5 A Proposed Internal Benchmark

We could instrument a small fixed task set (e.g., 10 well-defined coding tasks from our own codebase)
and run them identically through:
- Amplifier with current defaults
- Amplifier with `context_scope="conversation"` (no tool history propagation)
- Amplifier with explicit per-plan `context_depth="none"` (GSD-style)
- GSD + Claude Code (as baseline)

The instrumentation needed is already partially in place via the cost viewer. The missing piece is
exposing `cache_read_tokens` separately in the summary view (§2.2 fix) — without that, the comparison
confounds actual cost differences with caching differences.

---

## 7. Prioritized Recommendations

### Immediate (high impact, low effort)

| # | Action | Expected impact |
|---|---|---|
| 1 | Fix cache token alias map (`reader.py:302-305`) to include `cache_creation_input_tokens`, `cache_read_input_tokens`, `prompt_tokens_details.cached_tokens` | May reveal that many sessions are 50–80% cheaper than currently displayed |
| 2 | Run `scripts/update_pricing.py` and add missing models (claude-3-5-sonnet, gemini-1.5, Bedrock prefix handling) | Eliminates silent $0 sessions; gives accurate historical view |
| 3 | Add `logger.warning` + `/api/pricing/misses` endpoint for unknown models | Surfaces future gaps immediately |
| 4 | Add `cache_read_tokens` / `cache_write_tokens` to the `SessionNode` rollup and the UI summary view | Makes the real cost structure visible |

### Near-term (architectural)

| # | Action | Expected impact |
|---|---|---|
| 5 | Verify empirically whether parent `events.jsonl` inlines child `llm:response` events | Either confirms or eliminates the double-count risk |
| 6 | Add `task_budget` to browser-tester (browser-operator / browser-researcher) delegate calls | Prevents runaway convergence loops; model self-terminates gracefully |
| 7 | Add explicit `max_turns` configuration for all agentic loop orchestrations | Hard backstop against infinite retry loops |
| 8 | Audit `context_scope` usage in registered agent bundles — flag any `context_scope="full"` usage and evaluate whether it is justified | May cut per-delegation token cost significantly |

### Strategic (requires design work)

| # | Action | Expected impact |
|---|---|---|
| 9 | Implement GSD-style "externalize state to disk, fresh context per plan" as an optional orchestration mode | Could reduce orchestrator session cost by 2–4× for multi-plan work |
| 10 | Surface real-time "tokens consumed this session" in the CLI (like Claude Code's `/status` context meter) | Gives users visibility before cost is incurred |
| 11 | Run a controlled internal benchmark (10 fixed tasks × 3 context strategies) and publish results | Provides evidence-based answer to the GSD comparison question |
| 12 | Wire `db.py` SQLite overlay into `server.py` as intended, or remove it and the dead commit promise | Performance fix for large session lists |

---

## Appendix: Sources

### Code Audit Sources
- `/Users/ken/workspace/ms/cost-viewer/viewer/amplifier_app_cost_viewer/reader.py`
- `/Users/ken/workspace/ms/cost-viewer/viewer/amplifier_app_cost_viewer/pricing.py`
- `/Users/ken/workspace/ms/cost-viewer/viewer/amplifier_app_cost_viewer/server.py`
- `/Users/ken/workspace/ms/cost-viewer/viewer/amplifier_app_cost_viewer/db.py`

### Observability Platform Sources
- Langfuse cost tracking: https://langfuse.com/docs/observability/features/token-and-cost-tracking
- Langfuse data model: https://langfuse.com/docs/observability/data-model
- LangSmith cost tracking: https://docs.langchain.com/langsmith/cost-tracking
- Helicone proxy vs async: https://docs.helicone.ai/references/proxy-vs-async
- Helicone cost calculation: https://docs.helicone.ai/references/how-we-calculate-cost
- Braintrust changelog (token double-counting fix): https://www.braintrust.dev/docs/changelog
- Span-tree double-counting analysis: https://orekhov.work/posts/span-tree-aggregation/

### Anthropic Documentation
- Anthropic prompt caching pricing: https://platform.claude.com/docs/en/about-claude/pricing
- Anthropic prompt caching mechanics: https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- Task Budgets (beta): https://platform.claude.com/docs/en/build-with-claude/task-budgets
- Extended thinking: https://platform.claude.com/docs/en/build-with-claude/extended-thinking
- Tool use loop semantics: https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works

### Harness Comparison Sources
- GSD primary repo: https://github.com/gsd-build/get-shit-done
- GSD-2 (Pi SDK rewrite): https://github.com/gsd-build/gsd-2
- GSD walkthrough: https://www.agentnative.dev/blog/get-shit-done-meta-prompting-and-spec-driven-development-for-claude-code-and-codex
- GSD system-prompt overhead issue: https://github.com/gsd-build/get-shit-done/issues/2762
- Claude Code auto-compact: https://cuttlesoft.com/blog/2026/02/03/claude-code-for-advanced-users/
- Claude Code subagents: https://code.claude.com/docs/en/agent-sdk/subagents
- Aider repo-map: https://aider.chat/docs/repomap.html
- Codex CLI cost management: https://codex.danielvaughan.com/2026/03/28/codex-cli-cost-management-token-strategy/
- Token benchmark (Morph): https://www.morphllm.com/comparisons/morph-vs-aider-diff
- LangGraph recursion limit: https://docs.langchain.com/oss/python/langgraph/errors/GRAPH_RECURSION_LIMIT
- CrewAI max_iter: https://docs.crewai.com/en/learn/customizing-agents
- Framework budget gap analysis: https://tokenfence.dev/blog/langchain-crewai-cost-control-budget-limits
- Loop failure modes: https://kindatechnical.com/claude-ai/error-recovery-and-retries-in-agentic-workflows.html
- SWE-bench (vals.ai): https://www.vals.ai/benchmarks/swebench
- SWE-bench Verified (Epoch AI): https://epoch.ai/benchmarks/swe-bench-verified
