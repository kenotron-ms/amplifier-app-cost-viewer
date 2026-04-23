# hook-observability

    Amplifier hook module for token cost observability. Writes a JSONL log of every
    LLM call, tool call, and session summary. Optionally ships to Langfuse.

    ## What it captures

    Every provider response fires one `provider_call` JSON record:

    ```json
    {
      "ts": "2026-04-22T17:00:00Z",
      "type": "provider_call",
      "session_id": "46508d34-...",
      "provider": "anthropic",
      "model": "claude-sonnet-4-5",
      "input_tokens": 12345,
      "output_tokens": 567,
      "cache_read_tokens": 300,
      "cache_write_tokens": 0,
      "reasoning_tokens": 0,
      "total_tokens": 12912,
      "cost_usd": 0.045678,
      "latency_ms": 2341.5
    }
    ```

    Every session end fires a `session_summary`:

    ```json
    {
      "ts": "2026-04-22T18:00:00Z",
      "type": "session_summary",
      "session_id": "46508d34-...",
      "duration_s": 3612.4,
      "total_input_tokens": 98765,
      "total_output_tokens": 12345,
      "total_cost_usd": 0.345678,
      "provider_calls": 42,
      "tool_calls": 156
    }
    ```

    Files rotate daily: `~/.amplifier/observability/YYYY-MM-DD.jsonl`

    Quick view of today's spend:

    ```bash
    jq -r 'select(.type=="session_summary") | "\(.session_id[:8]) $\(.total_cost_usd) \(.provider_calls) calls"' \
      ~/.amplifier/observability/$(date +%Y-%m-%d).jsonl
    ```

    ---

    ## Phase 1 — JSONL only (no external dependencies)

    ### Install

    ```bash
    cd /path/to/this/repo
    pip install -e .
    ```

    ### Configure in your bundle

    ```yaml
    hooks:
      - module: hook-observability
        source: git+https://github.com/kenotron-ms/token-cost@main
        config:
          output_dir: "~/.amplifier/observability"
          model: "claude-sonnet-4-5"  # fallback if model not in response metadata
    ```

    Or for local dev:

    ```yaml
    hooks:
      - module: hook-observability
        source: /Users/ken/workspace/ms/token-cost
        config:
          output_dir: "~/.amplifier/observability"
    ```

    ---

    ## Phase 2 — Langfuse

    ### Start self-hosted Langfuse

    ```bash
    git clone https://github.com/langfuse/langfuse.git
    cd langfuse
    # Edit docker-compose.yml — update the lines marked CHANGEME
    docker compose up -d
    # UI at http://localhost:3000 (~2 min startup)
    ```

    Create a project → Settings → API Keys → copy public + secret key.

    ### Install with Langfuse support

    ```bash
    pip install -e ".[langfuse]"
    ```

    ### Configure

    ```yaml
    hooks:
      - module: hook-observability
        source: /Users/ken/workspace/ms/token-cost
        config:
          output_dir: "~/.amplifier/observability"
          model: "claude-sonnet-4-5"
          langfuse_enabled: true
          langfuse_host: "http://localhost:3000"
          langfuse_public_key: "pk-lf-..."
          langfuse_secret_key: "sk-lf-..."
    ```

    Both JSONL and Langfuse run simultaneously — JSONL is always on regardless of
    Langfuse status. If Langfuse is unreachable, JSONL continues writing; errors are
    logged at WARNING level and do not interrupt the session.

    ---

    ## Pricing table

    `src/hook_observability/pricing.py` — update when rates change. Includes Anthropic
    Claude 3.x/4.x, OpenAI GPT-4o/o-series, and Google Gemini families.

    Model lookup uses longest-prefix matching: `claude-sonnet-4-5-20241022` matches
    the `claude-sonnet-4` entry. Add new models to the `PRICING` dict.

    If a model is not found, cost is logged as `0.0` (never crashes).

    ---

    ## Useful one-liners

    ```bash
    # Today's spend by session
    jq -r 'select(.type=="session_summary") | [.session_id[:8], "$"+(.total_cost_usd|tostring), .provider_calls, "calls"] | @tsv' \
      ~/.amplifier/observability/$(date +%Y-%m-%d).jsonl

    # Total spend this month
    jq -s '[.[] | select(.type=="session_summary") | .total_cost_usd] | add' \
      ~/.amplifier/observability/$(date +%Y-%m).*.jsonl 2>/dev/null || echo "0"

    # Most expensive models today
    jq -r 'select(.type=="provider_call") | [.model, .cost_usd] | @tsv' \
      ~/.amplifier/observability/$(date +%Y-%m-%d).jsonl | \
      awk '{sum[$1]+=$2} END {for (m in sum) print sum[m], m}' | sort -rn | head -10
    ```
    