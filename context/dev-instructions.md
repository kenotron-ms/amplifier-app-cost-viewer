# hook-observability Development Context

You are working on `hook-observability`, an Amplifier hook module that captures every LLM
call's token costs and writes a rotating JSONL observability log. It optionally ships to
Langfuse for visualization.

## Project Structure

```
token-cost/
├── bundle.md                    ← this dev bundle
├── pyproject.toml               ← package config (entry: hook_observability:mount)
├── src/
│   └── hook_observability/
│       ├── __init__.py          ← HookObservability class + mount()
│       ├── jsonl_writer.py      ← JSONL log writer (session-scoped filenames)
│       ├── langfuse_writer.py   ← Langfuse integration (Phase 2)
│       └── pricing.py           ← token pricing table (Anthropic, OpenAI, Gemini)
└── tests/
```

## Key Data Shapes

Every provider response emits one record:
```json
{
  "ts": "2026-04-22T17:00:00Z",
  "type": "provider_call",
  "session_id": "46508d34-...",
  "provider": "anthropic",
  "model": "claude-sonnet-4-5",
  "input_tokens": 12345,
  "output_tokens": 567,
  "cost_usd": 0.045678
}
```

Every session end emits a summary:
```json
{
  "ts": "2026-04-22T18:00:00Z",
  "type": "session_summary",
  "session_id": "46508d34-...",
  "total_cost_usd": 0.345678,
  "provider_calls": 42,
  "tool_calls": 156
}
```

Files live at: `~/.amplifier/observability/<session_id>.jsonl`

## Development Workflow

Use the Superpowers methodology for all changes:

1. `/brainstorm` — Explore the design space before writing code
2. `/write-plan` — Create a TDD implementation plan with bite-sized tasks
3. `/execute-plan` — Subagent-driven implementation (implementer → spec review → quality review)
4. `/verify` — Evidence-based verification (never just claim it works)
5. `/finish` — Branch completion (merge / PR / keep)

## Code Quality

Run checks at any time via the `python_check` tool, or ask the `python-dev` agent:
- **Format**: ruff format
- **Lint**: ruff check
- **Types**: pyright
- **Tests**: `pytest tests/`

## Self-Observability Note

This dev bundle includes the hook itself — token costs from this session are captured
to `~/.amplifier/observability/`. You are watching costs while building the cost observer.
