---
bundle:
  name: token-cost
  version: 0.1.0
  description: |
    Development bundle for hook-observability — Amplifier hook module for token
    cost observability. Includes Python quality tooling, TDD methodology, and
    the hook module itself for self-observability while developing.

includes:
  - bundle: git+https://github.com/microsoft/amplifier-bundle-python-dev@main
  - bundle: git+https://github.com/microsoft/amplifier-bundle-superpowers@main

hooks:
  - module: hook-observability
    source: ./src
    config:
      output_dir: "~/.amplifier/observability"
      langfuse_enabled: true
      langfuse_host: ${LANGFUSE_HOST}
      langfuse_public_key: ${LANGFUSE_PUBLIC_KEY}
      langfuse_secret_key: ${LANGFUSE_SECRET_KEY}
---

# hook-observability Development

You are working on the `hook-observability` project — an Amplifier hook module that captures
every LLM call's token costs and writes a rotating JSONL observability log.

@token-cost:context/dev-instructions.md

---

@foundation:context/shared/common-system-base.md
