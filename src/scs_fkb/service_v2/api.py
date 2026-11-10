from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Form, Header, HTTPException, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

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
        return app.state.service.query(
            payload.question,
            persona=payload.persona,
            region=payload.region,
            year=payload.year,
            web=payload.web,
        )

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
        return templates.TemplateResponse(
            request=request,
            name="result.html",
            context={"result": result.model_dump(), "examples": EXAMPLES},
        )

    return app


__all__ = ["EXAMPLES", "create_app"]
