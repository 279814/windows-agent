from __future__ import annotations

import argparse
import asyncio
from os import environ


def _configure_windows_event_loop() -> None:
    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def main() -> int:
    _configure_windows_event_loop()
    from .mcp_server import create_server

    parser = argparse.ArgumentParser(prog="desktop-agent-dev")
    parser.add_argument("--windows-mcp-root", default=environ.get("WINDOWS_MCP_ROOT") or environ.get("WINDOWS_MCP_WORKSPACE"))
    parser.add_argument("--export-manifest", action="store_true", help="Print the generated manifest JSON and exit")
    parser.add_argument("--export-tools", action="store_true", help="Print the generated tool catalog JSON and exit")
    args = parser.parse_args()
    server = create_server(args.windows_mcp_root)
    if args.export_manifest:
        import json

        print(json.dumps(server.manifest, ensure_ascii=False, indent=2))
        return 0
    if args.export_tools:
        import json

        print(json.dumps(server.catalog, ensure_ascii=False, indent=2))
        return 0
    server.mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
