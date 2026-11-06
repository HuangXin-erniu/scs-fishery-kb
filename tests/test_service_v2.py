from __future__ import annotations

from types import SimpleNamespace

import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from scs_fkb.models import Chunk, SearchHit  # noqa: E402
from scs_fkb.service_v2 import AnswerService  # noqa: E402
from scs_fkb.service_v2.api import create_app  # noqa: E402


def _hit(text: str = "南海区伏季休渔时间为5月1日12时至8月16日12时。") -> SearchHit:
    chunk = Chunk(
        chunk_id="CH-1",
        doc_id="POL-CLOS-015",
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


def _service(gate: bool = True, web_search=None) -> AnswerService:
    return AnswerService(
        retriever=FakeRetriever([_hit()], gate=gate),
        playbooks=[],
        facts=[],
        web_search=web_search,
    )


def test_answer_has_resolvable_citations() -> None:
    result = _service().query("2026年南海区伏季休渔从什么时候开始？", web="off")
    assert result.abstained is False
    assert result.mode == "kb_only"
    assert result.citations
    assert result.citations[0].doc_id == "POL-CLOS-015"
    assert "POL-CLOS-015" in result.answer


def test_weak_gate_abstains() -> None:
    result = _service(gate=False).query("某条历史规定", web="off")
    assert result.abstained is True
    assert result.mode == "abstain"
    assert result.citations == []


def test_web_evidence_is_labelled_and_never_overrides() -> None:
    evidence = SimpleNamespace(
        evidence_id="WEBV-123",
        url="https://www.moa.gov.cn/a",
        title="官方通告",
        snippet="伏季休渔时间以官方通告为准。",
        fetched_at="2026-11-06T12:00:00+00:00",
    )

    def web(question: str, **kwargs):
        return SimpleNamespace(evidences=[evidence])

    result = _service(gate=False, web_search=web).query("2026年南海伏季休渔 最新", web="auto")
    assert result.used_web is True
    assert result.mode == "web_only"
    assert "网络检索 · 未入知识库" in result.answer
    assert any(c.source_type == "web" and c.url for c in result.citations)


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
    result = service.query("伏季休渔合规自查要做什么", web="off")
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
