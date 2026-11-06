from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import yaml

from scs_fkb.eval_v2 import (
    aggregate,
    answer_correctness,
    citation_resolution,
    gate_ok,
    load_questions,
    run_eval,
    score_row,
)
from scs_fkb.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]


def _row(**overrides) -> dict:
    row = {
        "id": "EV2-001",
        "question": "南海区伏季休渔的起止时间是什么？",
        "split": "dev",
        "review_status": "reviewed",
        "answer": "5月1日12时至8月16日12时 [POL-CLOS-015 §三、休渔时间]",
        "abstained": False,
        "latency_ms": 10,
        "citations": [{"doc_id": "POL-CLOS-015", "section": "三、休渔时间"}],
        "expected": {
            "answer": "5月1日12时至8月16日12时",
            "terms": ["5月1日", "8月16日"],
            "evidence": [{"doc": "POL-CLOS-015", "section": "三、休渔时间"}],
            "abstained": False,
        },
    }
    row.update(overrides)
    return row


def test_live_eval_set_counts_and_evidence() -> None:
    questions = load_questions(ROOT / "configs" / "eval-v2.yaml")
    assert len(questions) == 120
    assert sum(1 for item in questions if item["split"] == "dev") == 80
    assert sum(1 for item in questions if item["split"] == "test") == 40
    assert len({item["id"] for item in questions}) == 120
    registry = load_registry(ROOT / "configs" / "corpus.yaml")
    for item in questions:
        if not item["expected"]["abstained"]:
            assert item["expected"]["terms"]
            assert item["expected"]["evidence"]
        for evidence in item["expected"]["evidence"]:
            assert evidence["doc"] in registry


def test_metrics_reward_correct_cited_answer() -> None:
    scored = score_row(_row())
    assert scored["answer_correctness"] == 1.0
    assert scored["citation_resolution"] == 1.0
    assert scored["context_recall"] == 1.0
    assert scored["faithfulness"] == 1.0


def test_metrics_penalise_wrong_or_uncited_answer() -> None:
    scored = score_row(
        _row(
            answer="没有引用。",
            citations=[],
        )
    )
    assert scored["answer_correctness"] == 0.0
    assert scored["citation_resolution"] == 0.0
    assert answer_correctness(_row(answer="5月1日")) == 0.5
    assert citation_resolution(_row(citations=[])) == 0.0


def test_abstention_is_scored_separately() -> None:
    row = _row(
        answer="证据不足：请补充具体渔场。",
        abstained=True,
        citations=[],
        expected={"answer": "证据不足", "terms": [], "evidence": [], "abstained": True},
        review_status="reviewed",
    )
    scored = score_row(row)
    assert scored["answer_correctness"] == 1.0
    assert scored["citation_resolution"] == 1.0
    assert scored["abstention_accuracy"] == 1.0
    summary = aggregate([{**row, **scored}])
    assert summary["abstention_accuracy"] == 1.0


def test_gate_pass_and_fail() -> None:
    good = {
        "answer_correctness": 0.9,
        "citation_resolution": 1.0,
        "context_recall": 0.9,
        "abstention_accuracy": 1.0,
    }
    assert gate_ok(good, good)[0] is True
    bad = dict(good, answer_correctness=0.5)
    passed, failures = gate_ok(bad, good)
    assert passed is False
    assert any("answer_correctness" in item for item in failures)


def test_runner_with_fake_service(tmp_path: Path) -> None:
    config = tmp_path / "eval.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "questions": [
                    {
                        "id": "EV2-901",
                        "question": "南海区伏季休渔的起止时间是什么？",
                        "split": "dev",
                        "persona": "captain",
                        "review_status": "reviewed",
                        "expected": {
                            "answer": "5月1日12时至8月16日12时",
                            "terms": ["5月1日", "8月16日"],
                            "evidence": [{"doc": "POL-CLOS-015", "section": "三、休渔时间"}],
                            "abstained": False,
                        },
                    },
                    {
                        "id": "EV2-902",
                        "question": "某渔场的历史渔汛是什么？",
                        "split": "test",
                        "persona": "captain",
                        "review_status": "reviewed",
                        "expected": {
                            "answer": "证据不足",
                            "terms": [],
                            "evidence": [],
                            "abstained": True,
                        },
                    },
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    class FakeService:
        def query(self, question: str, web: str = "auto"):
            if "某渔场" in question:
                return SimpleNamespace(
                    answer="请补充具体渔场。",
                    abstained=True,
                    reason="clarify",
                    mode="clarify",
                    citations=[],
                    latency_ms=1,
                )
            citation = SimpleNamespace(
                doc_id="POL-CLOS-015",
                section="三、休渔时间",
                page=1,
                url="",
                model_dump=lambda: {
                    "doc_id": "POL-CLOS-015",
                    "section": "三、休渔时间",
                    "page": 1,
                    "url": "",
                },
            )
            return SimpleNamespace(
                answer="5月1日12时至8月16日12时 [POL-CLOS-015 §三、休渔时间]",
                abstained=False,
                reason="ok",
                mode="kb_only",
                citations=[citation],
                latency_ms=2,
            )

    result = run_eval(FakeService(), questions_path=config)
    assert result["questions"] == 2
    assert result["groups"]["dev"]["answer_correctness"] == 1.0
    assert result["groups"]["overall"]["abstention_accuracy"] == 1.0
