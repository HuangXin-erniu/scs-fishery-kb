from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from scs_fkb.models import Chunk, SearchHit  # noqa: E402
from scs_fkb.service_v2 import AnswerService  # noqa: E402
from scs_fkb.service_v2.api import create_app  # noqa: E402


def _hit(
    text: str = "南海区伏季休渔时间为5月1日12时至8月16日12时。",
    doc_id: str = "POL-CLOS-015",
) -> SearchHit:
    chunk = Chunk(
        chunk_id="CH-1",
        doc_id=doc_id,
        source_id="POL-CLOS-015",
        page=1,
        section="三、休渔时间",
        text=text,
        token_count=20,
        char_start=0,
        char_end=len(text),
        sensitivity="public",
        kind="corpus",
        authority_tier="A",
        level="national",
        jurisdiction="national",
    )
    return SearchHit(chunk=chunk, score=1.0)


class FakeRetriever:
    index_version = "v2-test"

    def __init__(self, hits: list[SearchHit], gate: bool = True) -> None:
        self.hits = hits
        self.gate = gate
        self.calls = 0

    def search(self, question: str, top_k: int = 5, filters=None, rerank: bool = True):
        self.calls += 1
        return self.hits

    def gate_ok(self, question: str, min_score: float, min_matched: int) -> bool:
        return self.gate


def _service(gate: bool = True) -> AnswerService:
    return AnswerService(
        retriever=FakeRetriever([_hit()], gate=gate),
        playbooks=[],
        facts=[],
    )


def test_answer_has_resolvable_citations() -> None:
    result = _service().query("2026年南海区伏季休渔从什么时候开始？")
    assert result.abstained is False
    assert result.mode == "kb_only"
    assert result.citations
    assert result.citations[0].doc_id == "POL-CLOS-015"
    assert "POL-CLOS-015" in result.answer


def test_weak_gate_abstains() -> None:
    result = _service(gate=False).query("某条历史规定")
    assert result.abstained is True
    assert result.mode == "abstain"
    assert result.citations == []


def test_playbook_block_has_steps_and_sources() -> None:
    playbook = {
        "id": "PLAY-CAPTAIN-001",
        "title": "伏季休渔合规自查",
        "persona": "captain",
        "status": "approved",
        "steps": [
            {
                "order": 1,
                "action": "核对休渔时间",
                "detail": "按通告执行。",
                "facts": ["FACT-POLICY-001"],
            }
        ],
    }
    fact = {
        "id": "FACT-POLICY-001",
        "status": "approved",
        "source": {"doc": "POL-CLOS-015", "section": "三、休渔时间"},
    }
    service = AnswerService(
        retriever=FakeRetriever([_hit()]),
        playbooks=[playbook],
        facts=[fact],
    )
    result = service.query("伏季休渔合规自查要做什么")
    assert result.playbook is not None
    assert result.playbook.steps[0].facts == ["FACT-POLICY-001"]
    assert result.playbook.steps[0].sources == ["POL-CLOS-015"]


def test_api_auth_query_and_feedback(tmp_path) -> None:
    service = _service()
    app = create_app(service, api_key="secret", run_root=tmp_path)
    client = TestClient(app)
    assert client.get("/healthz").status_code == 200
    assert client.post("/v1/query", json={"question": "休渔时间"}).status_code == 401
    response = client.post(
        "/v1/query",
        headers={"X-API-Key": "secret"},
        json={"question": "2026年南海区伏季休渔从什么时候开始？", "web": "off"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["request_id"].startswith("REQ-")
    assert body["citations"]
    feedback = client.post(
        "/v1/feedback",
        headers={"X-API-Key": "secret"},
        json={"request_id": body["request_id"], "helpful": True, "comment": "清楚"},
    )
    assert feedback.status_code == 200
    assert (tmp_path / "feedback.jsonl").is_file()


def test_ui_pages(tmp_path) -> None:
    app = create_app(_service(), run_root=tmp_path)
    client = TestClient(app)
    index = client.get("/")
    assert index.status_code == 200
    assert "南海近岸渔业知识库" in index.text
    result = client.post(
        "/",
        data={
            "question": "2026年南海区伏季休渔从什么时候开始？",
            "persona": "captain",
            "region": "",
            "year": "2026",
            "web": "off",
        },
    )
    assert result.status_code == 200
    assert "引用来源" in result.text


def test_answer_contract_fields() -> None:
    result = _service().query("2026年南海区伏季休渔从什么时候开始？")
    assert result.answerability == "answerable"
    assert result.conclusion
    assert result.answer.startswith("结论：")
    assert result.as_of is not None
    assert "依据摘录：" in result.answer


def test_v1_contract_remains_available() -> None:
    service = AnswerService(
        retriever=FakeRetriever([_hit()]),
        playbooks=[],
        facts=[],
        answer_contract="v1",
    )
    result = service.query("2026年南海区伏季休渔从什么时候开始？")
    assert result.conclusion == ""
    assert not result.answer.startswith("结论：")


def test_llm_mode_falls_back_without_configuration(monkeypatch) -> None:
    import scs_fkb.llm as llm_module

    for name in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(llm_module, "load_dotenv", lambda: None)
    monkeypatch.setenv("SCS_FKB_ANSWER_MODE", "llm")
    service = _service()
    result = service.query("2026年南海区伏季休渔从什么时候开始？")
    assert result.abstained is False
    assert result.reason != "llm_compose"


def test_summary_is_short_and_contract_shaped() -> None:
    result = _service().query("2026年南海区伏季休渔从什么时候开始？")
    assert result.summary
    assert len(result.summary) <= 2000
    assert "结论：" in result.summary
    assert result.citations_total == 1


def test_displayed_citations_are_unique_by_document_and_capped() -> None:
    from scs_fkb.service_v2.answer import _display_citations
    from scs_fkb.service_v2.schemas import CitationModel

    citations = [
        CitationModel(doc_id=f"POL-{index:03d}", title="t", section="s", page=1, snippet="x")
        for index in range(25)
    ]
    citations.append(CitationModel(doc_id="POL-000", title="t", section="s", page=1, snippet="x"))
    displayed, total = _display_citations(citations, 20)
    assert len(displayed) == 20
    assert len({item.doc_id for item in displayed}) == 20
    assert total == 25


def test_abstain_and_clarify_have_summaries() -> None:
    weak = _service(gate=False).query("某条历史规定")
    assert weak.abstained is True
    assert weak.summary
    clarify = _service().query("某渔场今年休渔时间？")
    assert clarify.mode == "clarify"
    assert clarify.summary


def test_api_compresses_large_responses(tmp_path) -> None:
    app = create_app(_service(), run_root=tmp_path)
    client = TestClient(app)
    response = client.get("/", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert response.headers.get("content-encoding") == "gzip"


def test_demo_page_renders_summary_and_evidence(tmp_path) -> None:
    app = create_app(_service(), run_root=tmp_path)
    client = TestClient(app)
    page = client.get("/demo")
    assert page.status_code == 200
    assert "测试页" in page.text
    assert "2026年南海区伏季休渔" in page.text
    result = client.post(
        "/demo",
        data={"question": "2026年南海区伏季休渔从什么时候开始？", "persona": "captain"},
    )
    assert result.status_code == 200
    assert "结论：" in result.text
    assert "完整依据摘录" in result.text
    assert "POL-CLOS-015" in result.text
    assert "份文档" in result.text


def test_metrics_report_requests_and_latency(tmp_path) -> None:
    app = create_app(_service(), run_root=tmp_path)
    client = TestClient(app)
    client.get("/healthz")
    metrics = client.get("/metrics").json()
    assert metrics["requests_total"] >= 1
    assert metrics["errors_total"] == 0
    assert metrics["latency_ms"]["p50"] is not None
    assert metrics["index_version"] == "v2"


def test_unhandled_errors_return_json(tmp_path) -> None:
    app = create_app(_service(), run_root=tmp_path)

    def boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    app.state.service.query = boom
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/v1/query", json={"question": "休渔时间"})
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"


def _web_evidence(url: str = "https://www.moa.gov.cn/a") -> object:
    from scs_fkb.web_v2 import WebEvidence

    return WebEvidence(
        evidence_id="WEBV-abc123",
        url=url,
        canonical_url=url,
        title="2026年南海区伏季休渔通告",
        publisher="农业农村部",
        domain="www.moa.gov.cn",
        authority_tier="A",
        source_class="reference",
        fetched_at="2026-11-10T03:00:00+00:00",
        content_hash="b" * 64,
        snippet="南海区休渔时间为5月1日12时至8月16日12时。",
        text_path="web-cache/WEBV-abc123.txt",
        search_query="2026年南海区伏季休渔",
        rank=1,
        ttl_days=30,
    )


def _web_result(evidences: list) -> object:
    from scs_fkb.web_v2 import WebSearchResult

    return WebSearchResult(
        triggered=True,
        reason="explicit",
        query="2026年南海区伏季休渔",
        provider="fake",
        mode="on",
        evidences=evidences,
    )


def test_web_off_does_not_touch_the_layer(monkeypatch, tmp_path) -> None:
    import scs_fkb.web_v2 as web_module

    calls: list[int] = []
    monkeypatch.setattr(web_module, "search_web", lambda *args, **kwargs: calls.append(1))
    service = AnswerService(
        retriever=FakeRetriever([_hit()]), playbooks=[], facts=[], data_root=tmp_path
    )
    result = service.query("2026年南海区伏季休渔从什么时候开始？", web="off")
    assert calls == []
    assert result.used_web is False
    assert result.web_leads == []
    assert result.mode == "kb_only"


def test_web_leads_stay_out_of_the_answer_and_citations(monkeypatch, tmp_path) -> None:
    import scs_fkb.web_v2 as web_module

    monkeypatch.setattr(
        web_module, "search_web", lambda *args, **kwargs: _web_result([_web_evidence()])
    )
    service = AnswerService(
        retriever=FakeRetriever([_hit()]), playbooks=[], facts=[], data_root=tmp_path
    )
    baseline = service.query("2026年南海区伏季休渔从什么时候开始？", web="off")
    result = service.query("2026年南海区伏季休渔从什么时候开始？", web="on")
    assert result.used_web is True
    assert result.mode == "kb_plus_web"
    assert len(result.web_leads) == 1
    assert result.web_leads[0].label == "网络检索 · 未入知识库"
    assert result.web_leads[0].tier == "A"
    assert result.answer == baseline.answer
    assert result.citations_total == baseline.citations_total
    assert all(item.source_type == "corpus" for item in result.citations)
    assert "网络补充" in result.summary


def test_web_never_flips_an_abstention(monkeypatch, tmp_path) -> None:
    import scs_fkb.web_v2 as web_module

    monkeypatch.setattr(
        web_module, "search_web", lambda *args, **kwargs: _web_result([_web_evidence()])
    )
    service = AnswerService(
        retriever=FakeRetriever([_hit()], gate=False),
        playbooks=[],
        facts=[],
        data_root=tmp_path,
    )
    result = service.query("某条历史规定", web="on")
    assert result.abstained is True
    assert result.used_web is False
    assert result.mode == "abstain"
    assert result.web_leads
    assert "网络线索" in result.summary


def test_web_auto_without_leads_keeps_the_answer_plain(monkeypatch, tmp_path) -> None:
    import scs_fkb.web_v2 as web_module

    monkeypatch.setattr(web_module, "search_web", lambda *args, **kwargs: _web_result([]))
    service = AnswerService(
        retriever=FakeRetriever([_hit()]), playbooks=[], facts=[], data_root=tmp_path
    )
    result = service.query("2026年南海区伏季休渔从什么时候开始？", web="auto")
    assert result.used_web is False
    assert result.web_leads == []
    assert result.mode == "kb_only"


def test_query_log_is_opt_in(monkeypatch, tmp_path) -> None:
    import json

    monkeypatch.setenv("SCS_FKB_LOG_QUERIES", "on")
    client = TestClient(create_app(_service(), run_root=tmp_path))
    response = client.post(
        "/v1/query",
        json={"question": "2026年南海区伏季休渔从什么时候开始？", "web": "off"},
    )
    assert response.status_code == 200
    files = list((tmp_path / "queries").glob("*.jsonl"))
    assert files
    row = json.loads(files[0].read_text(encoding="utf-8").splitlines()[0])
    assert row["question"].startswith("2026年")
    assert row["abstained"] is False


def test_query_log_is_off_by_default(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("SCS_FKB_LOG_QUERIES", raising=False)
    client = TestClient(create_app(_service(), run_root=tmp_path))
    client.post(
        "/v1/query",
        json={"question": "2026年南海区伏季休渔从什么时候开始？", "web": "off"},
    )
    assert not (tmp_path / "queries").exists()


def test_short_flag_falls_back_without_llm(monkeypatch) -> None:
    service = _service()
    monkeypatch.setattr(service, "_llm_pair", lambda: None)
    result = service.query("2026年南海区伏季休渔从什么时候开始？", short=True)
    assert result.abstained is False
    assert result.citations


def test_query_request_accepts_short_and_rerank() -> None:
    from scs_fkb.service_v2.schemas import QueryRequest

    payload = QueryRequest(question="休渔时间", short=True, rerank=True)
    assert payload.short is True
    assert payload.rerank is True


def test_kb_feedback_is_stored_locally(tmp_path) -> None:
    import json

    client = TestClient(create_app(_service(), run_root=tmp_path))
    response = client.post(
        "/kb/feedback",
        data={
            "item_id": "PLAY-CAPTAIN-001",
            "kind": "playbook",
            "helpful": "0",
            "comment": "期限不清楚",
            "next_path": "/kb#tasks",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/kb")
    rows = (tmp_path / "feedback.jsonl").read_text(encoding="utf-8").splitlines()
    row = json.loads(rows[0])
    assert row["source"] == "kb"
    assert row["item_id"] == "PLAY-CAPTAIN-001"
    assert row["helpful"] is False
    assert row["comment"] == "期限不清楚"


def test_kb_feedback_rejects_an_unknown_item(tmp_path) -> None:
    client = TestClient(create_app(_service(), run_root=tmp_path))
    response = client.post(
        "/kb/feedback",
        data={"item_id": "bad id!", "kind": "playbook", "helpful": "1"},
    )
    assert response.status_code == 400
    assert not (tmp_path / "feedback.jsonl").exists()


def test_short_failure_diagnostic_is_opt_in(tmp_path, monkeypatch) -> None:
    from scs_fkb.service_v2.answer import _record_short_failure

    log = tmp_path / "diag.jsonl"
    monkeypatch.delenv("SCS_FKB_SHORT_DIAG", raising=False)
    _record_short_failure("short_invalid:uncited")
    assert not log.exists()

    monkeypatch.setenv("SCS_FKB_SHORT_DIAG", str(log))
    _record_short_failure("short_invalid:uncited")
    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert "uncited" in lines[0]
    assert "question" not in lines[0]


def test_dump_mode_never_requests_a_model_summary() -> None:
    service = AnswerService(
        retriever=FakeRetriever([_hit()], gate=True),
        playbooks=[],
        facts=[],
        answer_mode="dump",
    )
    assert service._summary_mode() == "off"
