from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from scs_fkb.models import Chunk, SearchHit
from scs_fkb.rag import LLMCache
from scs_fkb.service_v2 import AnswerService

CITATION = "[POL-CLOS-015 §三、休渔时间]"


def _hit() -> SearchHit:
    chunk = Chunk(
        chunk_id="CH-1",
        doc_id="POL-CLOS-015",
        source_id="POL-CLOS-015",
        page=3,
        section="三、休渔时间",
        text="北纬26度30分至北纬12度的东海和南海海域，休渔时间为5月1日12时至8月16日12时。",
        token_count=30,
        char_start=0,
        char_end=50,
        sensitivity="public",
        authority_tier="A",
        level="national",
        jurisdiction="national",
    )
    return SearchHit(chunk=chunk, score=1.0)


class FakeEncoder:
    def embed_query(self, text: str) -> list[float]:
        return [1.0, 0.0, 0.0]


class FakeRetriever:
    index_version = "idx-standard"

    def __init__(self) -> None:
        self.encoder = FakeEncoder()
        self.calls = 0

    def search(
        self,
        question: str,
        top_k: int = 5,
        filters=None,
        rerank: bool = True,
        depth: int | None = None,
        rerank_candidates: int | None = None,
    ) -> list[SearchHit]:
        self.calls += 1
        return [_hit()]

    def gate_ok(self, question: str, min_score: float, min_matched: int) -> bool:
        return True


class FakeClient:
    def __init__(self) -> None:
        self.calls = 0
        self.config = SimpleNamespace(model="fake-service")

    def chat(self, messages, **kwargs) -> str:
        self.calls += 1
        return json.dumps(
            {
                "answerability": "answerable",
                "conclusion": f"南海区伏季休渔时间为5月1日12时至8月16日12时。{CITATION}",
                "applicability": "南海区",
                "steps": [],
                "documents": [],
                "deadline": "",
                "basis": [CITATION],
                "caveat": "以当年通告为准。",
                "soft_gap": [],
                "missing_slots": [],
                "citations": [CITATION],
            },
            ensure_ascii=False,
        )


@pytest.fixture(autouse=True)
def _selfcheck_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCS_FKB_STANDARD_SELFCHECK", "off")


def _service(tmp_path, client: FakeClient, retriever: FakeRetriever) -> AnswerService:
    service = AnswerService(
        retriever=retriever,
        playbooks=[],
        facts=[],
        data_root=tmp_path,
        index_version="idx-standard",
        answer_mode="standard",
    )
    service._llm = (client, LLMCache(tmp_path / "llm-cache"))
    return service


def test_standard_mode_returns_evidence_and_citations(tmp_path) -> None:
    client = FakeClient()
    retriever = FakeRetriever()
    service = _service(tmp_path, client, retriever)
    result = service.query("2026年南海区伏季休渔从什么时候开始？", mode="standard", web="off")
    assert result.answer_mode == "standard"
    assert result.abstained is False
    assert result.citations
    assert result.evidence
    assert result.evidence[0].doc_id == "POL-CLOS-015"
    assert result.confidence is not None
    assert result.freshness is not None
    assert result.freshness.ttl_days is not None
    assert result.cache is None or result.cache.hit is False


def test_standard_mode_uses_cache_on_second_call(tmp_path) -> None:
    client = FakeClient()
    retriever = FakeRetriever()
    service = _service(tmp_path, client, retriever)
    first = service.query("2026年南海区伏季休渔从什么时候开始？", mode="standard", web="off")
    assert first.cache is None or first.cache.hit is False
    calls_after_first = client.calls
    second = service.query("2026年南海区伏季休渔从什么时候开始？", mode="standard", web="off")
    assert second.cache is not None
    assert second.cache.hit is True
    assert client.calls == calls_after_first
    assert second.evidence
    assert second.citations


def test_default_mode_can_still_be_dump(tmp_path) -> None:
    client = FakeClient()
    service = _service(tmp_path, client, FakeRetriever())
    service.answer_mode = "dump"
    # The dump arm needs a real retriever depth; this test only checks that the
    # explicit standard override wins over the configured default.
    result = service.query("休渔时间？", mode="standard", web="off")
    assert result.answer_mode == "standard"
