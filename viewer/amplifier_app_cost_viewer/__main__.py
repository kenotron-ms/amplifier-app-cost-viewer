"""Entry point for the amplifier-cost-viewer CLI."""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Amplifier session cost and performance viewer"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=8181, help="Port to bind (default: 8181)"
    )
    args = parser.parse_args()

    import uvicorn

    uvicorn.run(
        "amplifier_app_cost_viewer.server:app",
        host=args.host,
        port=args.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
