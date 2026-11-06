#!/usr/bin/env python3
"""Serve the local v2 answer service."""

from __future__ import annotations

import argparse
import os

from scs_fkb.service_v2.api import create_app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT"))
    parser.add_argument("--run-root", default=os.environ.get("SCS_FKB_RUN_ROOT"))
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args(argv)
    if not args.data_root:
        raise SystemExit("error: set SCS_FKB_DATA_ROOT or pass --data-root")
    import uvicorn

    os.environ.setdefault("SCS_FKB_DATA_ROOT", args.data_root)
    if args.run_root:
        os.environ.setdefault("SCS_FKB_RUN_ROOT", args.run_root)
    app = create_app(run_root=args.run_root)
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
