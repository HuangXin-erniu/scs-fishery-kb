from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from scs_fkb.models import Chunk, SearchHit  # noqa: E402
from scs_fkb.service_v2 import AnswerService  # noqa: E402
from scs_fkb.service_v2.api import create_app  # noqa: E402


class _Retriever:
    index_version = "kb-test"

    def search(self, question: str, top_k: int = 5, filters=None, rerank: bool = True):
        chunk = Chunk(
            chunk_id="CH-KB",
            doc_id="POL-CLOS-015",
            source_id="POL-CLOS-015",
            page=1,
            section="三、休渔时间",
            text="南海区休渔时间为5月1日12时至8月16日12时。",
            token_count=10,
            char_start=0,
            char_end=20,
            sensitivity="public",
            kind="corpus",
        )
        return [SearchHit(chunk=chunk, score=1.0)]

    def gate_ok(self, question: str, min_score: float, min_matched: int) -> bool:
        return True


PLAYBOOK = {
    "id": "PLAY-CAPTAIN-999",
    "title": "休渔自查",
    "persona": "captain",
    "status": "approved",
    "applies_to": {"region": ["national"]},
    "steps": [{"order": 1, "action": "核对休渔时间", "detail": "按通告执行。", "facts": []}],
    "documents": ["捕捞许可证"],
    "deadlines": ["5月1日前"],
    "penalties": ["罚款"],
    "sources": ["POL-CLOS-015"],
    "review_due": "2027-02-02",
}

FACT = {
    "id": "FACT-KB-1",
    "status": "approved",
    "topic": "policy",
    "subject": "休渔",
    "predicate": "开始时间",
    "value": "5月1日12时",
    "unit": "None",
    "source": {"doc": "POL-CLOS-015", "section": "三、休渔时间"},
    "review_due": "2026-12-03",
}


def _app(tmp_path):
    service = AnswerService(
        retriever=_Retriever(),
        playbooks=[PLAYBOOK],
        facts=[FACT],
        data_root=tmp_path,
    )
    return create_app(service, run_root=tmp_path)


def test_kb_page_has_all_sections(tmp_path) -> None:
    client = TestClient(_app(tmp_path))
    response = client.get("/kb")
    assert response.status_code == 200
    for heading in (
        "任务卡（速查）",
        "标准问答",
        "办事流程（详解）",
        "常见问答",
        "术语白话",
        "数值速查",
        "更新提醒",
    ):
        assert heading in response.text
    assert "休渔自查" in response.text
    assert "/kb/manifest.webmanifest" in response.text


def test_kb_task_detail_and_feedback(tmp_path) -> None:
    client = TestClient(_app(tmp_path))
    detail = client.get("/kb/tasks/TASK-CAPTAIN-001")
    assert detail.status_code == 200
    assert "步骤" in detail.text
    assert client.get("/kb/tasks/TASK-NONE-000").status_code == 404
    posted = client.post(
        "/kb/feedback",
        data={
            "item_id": "TASK-CAPTAIN-001",
            "kind": "task",
            "helpful": "1",
            "comment": "clear",
            "next_path": "/kb#taskcards",
        },
        follow_redirects=False,
    )
    assert posted.status_code == 303
    feedback = (tmp_path / "feedback.jsonl").read_text(encoding="utf-8")
    assert '"kind": "task"' in feedback


def test_kb_pwa_routes(tmp_path) -> None:
    client = TestClient(_app(tmp_path))
    manifest = client.get("/kb/manifest.webmanifest")
    assert manifest.status_code == 200
    assert manifest.headers["content-type"].startswith("application/manifest+json")
    assert manifest.json()["start_url"] == "/kb"
    sw = client.get("/kb/sw.js")
    assert sw.status_code == 200
    assert "serviceWorker" not in sw.text  # the worker itself, registered by the page
    icon = client.get("/kb/icon.svg")
    assert icon.status_code == 200
    assert icon.headers["content-type"].startswith("image/svg+xml")


def test_kb_persona_filter_and_playbook_detail(tmp_path) -> None:
    client = TestClient(_app(tmp_path))
    assert client.get("/kb?persona=owner").status_code == 200
    detail = client.get("/kb/playbooks/PLAY-CAPTAIN-999")
    assert detail.status_code == 200
    assert "核对休渔时间" in detail.text
    assert client.get("/kb/playbooks/PLAY-NONE-000").status_code == 404


def test_kb_search_filters_faq(tmp_path) -> None:
    client = TestClient(_app(tmp_path))
    hit = client.get("/kb", params={"q": "休渔"})
    assert hit.status_code == 200
    miss = client.get("/kb", params={"q": "完全不存在的词"})
    assert miss.status_code == 200
