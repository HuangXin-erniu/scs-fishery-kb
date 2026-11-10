"""Command line for the SCS-FKB pipeline: ask, serve and check."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _data_root(value: str | None) -> str:
    root = value or os.environ.get("SCS_FKB_DATA_ROOT", "")
    if not root:
        raise SystemExit("error: set SCS_FKB_DATA_ROOT or pass --data-root")
    return root


def _service(args: argparse.Namespace):
    from .service_v2.answer import build_service

    return build_service(data_root=_data_root(args.data_root), run_root=args.run_root)


def _ask(args: argparse.Namespace) -> int:
    result = _service(args).query(args.question, web=getattr(args, "web", None))
    if args.json:
        payload = {
            "summary": result.summary,
            "answer": result.answer,
            "abstained": result.abstained,
            "mode": result.mode,
            "citations_total": result.citations_total,
            "used_web": result.used_web,
            "web_leads": [
                {
                    "url": item.url,
                    "title": item.title,
                    "domain": item.domain,
                    "publisher": item.publisher,
                    "fetched_at": item.fetched_at,
                    "citation": item.citation,
                }
                for item in result.web_leads
            ],
            "citations": [
                {
                    "doc_id": item.doc_id,
                    "section": item.section,
                    "page": item.page,
                    "title": item.title,
                }
                for item in result.citations
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if args.full:
        print(result.answer)
    else:
        print(result.summary)
    if result.citations:
        if args.full:
            print(f"\n引用（前 {len(result.citations)} 条，共 {result.citations_total} 份文档）：")
        else:
            print(f"\n主要依据（共 {result.citations_total} 份文档）：")
        for item in result.citations:
            where = f"§{item.section}" if item.section else f"p.{item.page}"
            print(f"- [{item.doc_id} {where}] {item.title}")
    if not args.full:
        print("\n（完整证据请加 --full）")
    return 0


def _serve(args: argparse.Namespace) -> int:
    import uvicorn

    from .service_v2.api import create_app

    os.environ.setdefault("SCS_FKB_DATA_ROOT", _data_root(args.data_root))
    if args.run_root:
        os.environ.setdefault("SCS_FKB_RUN_ROOT", args.run_root)
    app = create_app(run_root=args.run_root)
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)
    return 0


def _check(_args: argparse.Namespace) -> int:
    script = ROOT / "scripts" / "check_public_tree.py"
    return subprocess.call([sys.executable, str(script)], cwd=ROOT)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scs-fkb", description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT"))
    parser.add_argument("--run-root", default=os.environ.get("SCS_FKB_RUN_ROOT"))
    sub = parser.add_subparsers(dest="command", required=True)

    ask = sub.add_parser("ask", help="answer one question with cited evidence")
    ask.add_argument("question")
    ask.add_argument("--json", action="store_true", help="print a JSON payload")
    ask.add_argument("--full", action="store_true", help="print the full evidence text")
    ask.add_argument(
        "--web",
        choices=["off", "auto", "on"],
        default=None,
        help="web evidence mode; default from SCS_FKB_WEB or off",
    )
    ask.set_defaults(func=_ask)

    serve = sub.add_parser("serve", help="run the local HTTP service")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--reload", action="store_true")
    serve.set_defaults(func=_serve)

    check = sub.add_parser("check", help="validate the public tree")
    check.set_defaults(func=_check)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


__all__ = ["build_parser", "main"]
