---
bundle:
  name: token-cost
  version: 0.1.0
  description: |
    Development bundle for amplifier-app-cost-viewer — a FastAPI + SPA app that
    reads Amplifier session event logs and renders an interactive token cost
    timeline. Includes Python quality tooling and TDD methodology.

includes:
  - bundle: git+https://github.com/microsoft/amplifier-bundle-python-dev@main
  - bundle: git+https://github.com/microsoft/amplifier-bundle-superpowers@main
---

# amplifier-app-cost-viewer Development

You are working on `amplifier-app-cost-viewer`, a FastAPI + vanilla JS SPA that reads
Amplifier session event logs and visualizes token costs as an interactive timeline.

@token-cost:context/dev-instructions.md

---

@foundation:context/shared/common-system-base.md
