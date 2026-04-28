# amplifier-app-cost-viewer Development Context

You are working on `amplifier-app-cost-viewer`, a FastAPI + vanilla JS SPA that reads
Amplifier session event logs directly from `~/.amplifier/projects/` and renders an
interactive token cost timeline.

## Project Structure

```
token-cost/
├── bundle.md                    ← this dev bundle
├── scripts/
│   └── update_pricing.py        ← refreshes STATIC_PRICING from LiteLLM catalog
└── viewer/
    ├── pyproject.toml           ← package config (entry: amplifier-cost-viewer)
    └── amplifier_app_cost_viewer/
        ├── __init__.py
        ├── __main__.py          ← CLI entry: amplifier-cost-viewer [--host] [--port]
        ├── server.py            ← FastAPI app + REST endpoints + cache refresh loop
        ├── reader.py            ← event log parsing, span extraction, session tree
        ├── pricing.py           ← static pricing table (Anthropic, OpenAI, Google)
        └── static/
            ├── index.html
            ├── app.js           ← vanilla JS SPA (Lit custom elements, canvas renderer)
            └── style.css
```

## Data Flow

The viewer reads **directly from the Amplifier kernel's event logs** — no hook module required:

```
~/.amplifier/projects/<project>/sessions/<session_id>/
    events.jsonl      ← kernel event stream (provider:request, llm:response, tool:pre/post, etc.)
    metadata.json     ← session metadata
```

Token cost is computed locally from token counts × pricing table in `pricing.py`.
No provider returns USD cost in API responses — all three (Anthropic, OpenAI, Google)
return token counts only; cost must be calculated client-side.

## Key Token Fields (from kernel events)

The `llm:response` event's `usage` object uses these normalized field names:
- `input_tokens` / `output_tokens` — standard token counts
- `cache_read_tokens` — tokens served from prompt cache (lower cost)
- `cache_write_tokens` — tokens written to cache (higher cost)

The pricing table maps these to `cache_read_input_token_cost` and
`cache_creation_input_token_cost` per model.

## REST API

| Endpoint | Purpose |
|----------|---------|
| `GET /api/sessions` | Paginated root session list |
| `GET /api/sessions/{id}` | Full session tree with spans |
| `GET /api/sessions/{id}/spans` | Flattened spans (lazy child load) |
| `GET /api/sessions/{id}/child-spans/{child_id}` | Single child's spans |
| `POST /api/refresh` | Bust in-memory cache |

## Running the Viewer

```bash
cd viewer
uv run amplifier-cost-viewer          # default: 127.0.0.1:8181
uv run amplifier-cost-viewer --port 9000
```

## Updating Pricing

```bash
python scripts/update_pricing.py      # fetches from LiteLLM, rewrites pricing.py
```

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
- **Tests**: `cd viewer && pytest tests/`
