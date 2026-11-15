from __future__ import annotations

import json
import os
import re
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Form, Header, HTTPException, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from ..kb_v2 import build_numbers, build_updates, load_faq, load_terms_plain, search_faq
from ..knowledge_v2.answers import load_answers, search_answers
from ..knowledge_v2.task_cards import load_task_cards
from .answer import AnswerService, build_service
from .schemas import (
    FeedbackRequest,
    HealthResponse,
    QueryRequest,
    QueryResponse,
    SourceView,
)

EXAMPLES = [
    "2026年南海区伏季休渔从什么时候开始？",
    "捕捞许可证到期怎么换发？",
    "小型渔船拖网的最小网目尺寸是多少？",
    "渔捞日志要记哪些内容？",
]


def _feedback_path(run_root: Path | str | None) -> Path:
    if run_root:
        base = Path(run_root).expanduser().resolve()
    else:
        base = Path(tempfile.gettempdir()) / "scs-fkb-feedback"
    base.mkdir(parents=True, exist_ok=True)
    return base / "feedback.jsonl"


def _query_log_path(run_root: Path | str | None, day: str | None = None) -> Path:
    if run_root:
        base = Path(run_root).expanduser().resolve()
    else:
        base = Path(tempfile.gettempdir()) / "scs-fkb-queries"
    directory = base / "queries"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{day or datetime.now(UTC).date().isoformat()}.jsonl"


def create_app(
    service: AnswerService | None = None,
    *,
    api_key: str | None = None,
    run_root: Path | str | None = None,
) -> FastAPI:
    app = FastAPI(
        title="SCS-FKB answer service",
        version="v2",
        description="Local knowledge-base answer service with cited corpus evidence.",
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.state.service = service or build_service(run_root=run_root)
    app.state.stats = {"started": time.time(), "requests": 0, "errors": 0, "latencies": []}

    @app.middleware("http")
    async def record_request(request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            app.state.stats["errors"] += 1
            raise
        elapsed = (time.perf_counter() - started) * 1000
        stats = app.state.stats
        stats["requests"] += 1
        stats["latencies"].append(elapsed)
        if len(stats["latencies"]) > 1000:
            stats["latencies"] = stats["latencies"][-1000:]
        return response

    @app.exception_handler(Exception)
    async def unhandled_error(_request: Request, _exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "internal server error"}},
        )

    app.state.run_root = run_root
    log_queries = os.environ.get("SCS_FKB_LOG_QUERIES", "").strip().lower() in {
        "on",
        "1",
        "true",
        "yes",
    }

    def log_query(result: QueryResponse, question: str) -> None:
        if not log_queries:
            return
        row = {
            "request_id": result.request_id,
            "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "question": question,
            "mode": result.mode,
            "reason": result.reason,
            "abstained": result.abstained,
            "answerability": result.answerability,
            "latency_ms": result.latency_ms,
        }
        try:
            with _query_log_path(app.state.run_root).open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        except OSError:
            pass

    templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
    required_key = api_key if api_key is not None else os.environ.get("SCS_FKB_API_KEY", "")

    def require_key(x_api_key: str | None = Header(default=None)) -> None:
        if required_key and x_api_key != required_key:
            raise HTTPException(status_code=401, detail="invalid or missing X-API-Key")

    @app.get("/healthz", response_model=HealthResponse)
    def healthz() -> HealthResponse:
        return HealthResponse(status="ok", index_version=app.state.service.index_version)

    @app.get("/readyz", response_model=HealthResponse)
    def readyz() -> HealthResponse:
        return HealthResponse(status="ready", index_version=app.state.service.index_version)

    @app.post(
        "/v1/query",
        response_model=QueryResponse,
        dependencies=[Depends(require_key)],
        openapi_extra={
            "requestBody": {
                "content": {
                    "application/json": {
                        "example": {
                            "question": EXAMPLES[0],
                            "persona": "captain",
                            "web": "auto",
                        }
                    }
                }
            }
        },
    )
    def query(payload: QueryRequest) -> QueryResponse:
        result = app.state.service.query(
            payload.question,
            persona=payload.persona,
            region=payload.region,
            year=payload.year,
            web=payload.web,
            short=payload.short,
            rerank=payload.rerank,
            mode=payload.mode,
            max_chars=payload.max_chars,
        )
        log_query(result, payload.question)
        return result

    @app.get("/v1/sources", response_model=list[SourceView], dependencies=[Depends(require_key)])
    def sources() -> list[SourceView]:
        return [SourceView(**row) for row in app.state.service.sources()]

    @app.get(
        "/v1/playbooks",
        response_model=list[dict],
        dependencies=[Depends(require_key)],
    )
    def playbooks() -> list[dict]:
        return app.state.service.playbook_list()

    @app.post("/v1/feedback", dependencies=[Depends(require_key)])
    def feedback(payload: FeedbackRequest) -> dict[str, str]:
        row = {
            "request_id": payload.request_id,
            "helpful": payload.helpful,
            "comment": payload.comment,
            "question": payload.question,
            "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        }
        path = _feedback_path(app.state.run_root)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        return {"status": "recorded", "request_id": payload.request_id}

    @app.get("/metrics")
    def metrics() -> dict:
        stats = app.state.stats
        latencies = sorted(stats["latencies"])
        if latencies:
            p50 = latencies[len(latencies) // 2]
            p95 = latencies[min(len(latencies) - 1, int(round(0.95 * (len(latencies) - 1))))]
        else:
            p50 = p95 = None
        return {
            "uptime_seconds": round(time.time() - stats["started"], 1),
            "requests_total": stats["requests"],
            "errors_total": stats["errors"],
            "latency_ms": {
                "p50": round(p50, 1) if p50 is not None else None,
                "p95": round(p95, 1) if p95 is not None else None,
            },
            "index_version": app.state.service.index_version,
        }

    @app.get("/demo", response_class=HTMLResponse)
    def demo(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="demo.html",
            context={"examples": EXAMPLES, "result": None, "question": "", "web": "off"},
        )

    @app.post("/demo", response_class=HTMLResponse)
    def demo_query(
        request: Request,
        question: str = Form(...),
        persona: str = Form("general"),
        region: str = Form(""),
        year: str = Form(""),
        web: str = Form("off"),
    ) -> HTMLResponse:
        year_value = int(year) if year.strip().isdigit() else None
        result = app.state.service.query(
            question,
            persona=persona,
            region=region.strip() or None,
            year=year_value,
            web=web,
        )
        log_query(result, question)
        return templates.TemplateResponse(
            request=request,
            name="demo.html",
            context={
                "examples": EXAMPLES,
                "result": result.model_dump(),
                "question": question,
                "web": web,
            },
        )

    @app.get("/kb", response_class=HTMLResponse)
    def kb(request: Request, persona: str = "general", q: str = "") -> HTMLResponse:
        service = app.state.service
        registry = getattr(service, "_registry", {})
        facts = list(getattr(service, "facts", []) or [])
        playbooks = [
            item
            for item in getattr(service, "playbooks", []) or []
            if item.get("status") == "approved"
        ]
        selected = (
            persona if persona in {"captain", "owner", "enforcement", "extension"} else "general"
        )
        if selected != "general":
            playbooks = [item for item in playbooks if item.get("persona") == selected]
        task_cards = [
            item
            for item in load_task_cards()
            if item.get("status") in {"approved", "draft"}
            and (selected == "general" or item.get("persona") == selected)
        ]
        answer_bank = [item for item in load_answers() if item.get("status") == "approved"]
        if q.strip():
            answer_bank = [item for item in answer_bank if search_answers([item], q) is not None]
        terms = load_terms_plain()
        needle = q.strip().lower()
        if needle:
            terms = [
                item
                for item in terms
                if needle
                in " ".join(
                    [str(item.get("official") or ""), str(item.get("plain") or "")]
                    + [str(value) for value in item.get("variants") or []]
                ).lower()
            ]
        return templates.TemplateResponse(
            request=request,
            name="kb.html",
            context={
                "persona": selected,
                "query": q,
                "playbooks": playbooks,
                "task_cards": task_cards,
                "answers": answer_bank,
                "faq": search_faq(load_faq(), q),
                "terms": terms,
                "numbers": build_numbers(facts),
                "updates": build_updates(registry),
            },
        )

    @app.get("/kb/playbooks/{playbook_id}", response_class=HTMLResponse)
    def kb_playbook(request: Request, playbook_id: str) -> HTMLResponse:
        service = app.state.service
        playbooks = [
            item
            for item in getattr(service, "playbooks", []) or []
            if item.get("status") == "approved"
        ]
        playbook = next((item for item in playbooks if item.get("id") == playbook_id), None)
        if playbook is None:
            raise HTTPException(status_code=404, detail="playbook not found")
        return templates.TemplateResponse(
            request=request,
            name="kb_playbook.html",
            context={"playbook": playbook, "persona": playbook.get("persona") or "general"},
        )

    @app.get("/kb/tasks/{task_id}", response_class=HTMLResponse)
    def kb_task(request: Request, task_id: str) -> HTMLResponse:
        service = app.state.service
        task = next((item for item in load_task_cards() if item.get("id") == task_id), None)
        if task is None:
            raise HTTPException(status_code=404, detail="task card not found")
        facts = {str(item.get("id")): item for item in getattr(service, "facts", []) or []}
        playbook = next(
            (
                item
                for item in getattr(service, "playbooks", []) or []
                if item.get("id") == (task.get("source") or {}).get("id")
            ),
            None,
        )
        return templates.TemplateResponse(
            request=request,
            name="kb_task.html",
            context={
                "task": task,
                "facts": facts,
                "playbook": playbook,
                "persona": task.get("persona") or "general",
            },
        )

    @app.get("/kb/manifest.webmanifest")
    def kb_manifest() -> Response:
        return JSONResponse(
            {
                "name": "南海近岸渔业知识站",
                "short_name": "渔业知识站",
                "start_url": "/kb",
                "scope": "/kb",
                "display": "standalone",
                "background_color": "#f4f7f4",
                "theme_color": "#0f6b73",
                "lang": "zh-CN",
                "icons": [
                    {
                        "src": "/kb/icon.svg",
                        "sizes": "any",
                        "type": "image/svg+xml",
                        "purpose": "any",
                    }
                ],
            },
            media_type="application/manifest+json",
        )

    @app.get("/kb/icon.svg")
    def kb_icon() -> Response:
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            '<rect width="64" height="64" rx="12" fill="#0f6b73"/>'
            '<path d="M12 40c8-10 16-14 24-12 6 1 10 5 16 10-8 8-18 12-30 8-4-1-7-3-10-6z" '
            'fill="#e8f0ef"/>'
            '<circle cx="40" cy="30" r="3" fill="#0f6b73"/>'
            "</svg>"
        )
        return Response(content=svg, media_type="image/svg+xml")

    @app.get("/kb/sw.js")
    def kb_service_worker() -> Response:
        script = """
const CACHE = 'scs-kb-v1';
const SHELL = ['/kb', '/kb/icon.svg', '/kb/manifest.webmanifest'];
self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(SHELL)));
  self.skipWaiting();
});
self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys().then((keys) =>
    Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)))
  ));
  self.clients.claim();
});
self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE).then((cache) => cache.put(event.request, copy));
        return response;
      })
      .catch(() => caches.match(event.request).then((hit) => hit || caches.match('/kb')))
  );
});
"""
        return Response(content=script.strip() + "\n", media_type="application/javascript")

    @app.post("/kb/feedback")
    def kb_feedback(
        item_id: str = Form(...),
        kind: str = Form(...),
        helpful: str = Form(...),
        comment: str = Form(""),
        next_path: str = Form("/kb"),
    ) -> RedirectResponse:
        if not re.fullmatch(r"[A-Za-z0-9-]{3,40}", item_id) or kind not in {
            "playbook",
            "faq",
            "task",
            "answer",
        }:
            raise HTTPException(status_code=400, detail="invalid feedback item")
        target = next_path if next_path.startswith("/kb") else "/kb"
        flag = helpful.strip().lower() in {"1", "true", "yes", "on"}
        row = {
            "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "source": "kb",
            "item_id": item_id,
            "kind": kind,
            "helpful": flag,
            "comment": comment.strip()[:200],
        }
        with _feedback_path(app.state.run_root).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        return RedirectResponse(url=f"{target}?feedback=ok", status_code=303)

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"examples": EXAMPLES},
        )

    @app.post("/", response_class=HTMLResponse)
    def ui_query(
        request: Request,
        question: str = Form(...),
        persona: str = Form("general"),
        region: str = Form(""),
        year: str = Form(""),
    ) -> HTMLResponse:
        year_value = int(year) if year.strip().isdigit() else None
        result = app.state.service.query(
            question,
            persona=persona,
            region=region.strip() or None,
            year=year_value,
        )
        log_query(result, question)
        return templates.TemplateResponse(
            request=request,
            name="result.html",
            context={"result": result.model_dump(), "examples": EXAMPLES},
        )

    return app


__all__ = ["EXAMPLES", "create_app"]
