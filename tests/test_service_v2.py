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
