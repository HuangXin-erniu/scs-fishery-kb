from __future__ import annotations

import json
from pathlib import Path

from scripts.merge_audit_artifacts import main


def test_merge_dedupes_and_adds_inline_citations(tmp_path: Path) -> None:
    questions = tmp_path / "q.jsonl"
    questions.write_text(
        json.dumps({"id": "Q1"}, ensure_ascii=False)
        + "\n"
        + json.dumps({"id": "Q2"}, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    first = tmp_path / "a.jsonl"
    first.write_text(
        json.dumps(
            {
                "id": "Q1",
                "visible_answer": "答案一 [POL-A-001 §第一条]。",
                "citations": [],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    second = tmp_path / "b.jsonl"
    second.write_text(
        json.dumps(
            {
                "id": "Q1",
                "visible_answer": "答案二 [POL-A-001 §第一条][POL-B-002 §第二条]。",
                "citations": [{"doc_id": "POL-A-001", "section": "第一条"}],
            },
            ensure_ascii=False,
        )
        + "\n"
        + json.dumps({"id": "Q2", "visible_answer": "答案三。", "citations": []})
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.jsonl"
    assert (
        main(
            ["--questions", str(questions), "--answers", str(first), str(second), "--out", str(out)]
        )
        == 0
    )
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert [row["id"] for row in rows] == ["Q1", "Q2"]
    assert rows[0]["visible_answer"].startswith("答案二")
    assert {(c["doc_id"], c["section"]) for c in rows[0]["citations"]} == {
        ("POL-A-001", "第一条"),
        ("POL-B-002", "第二条"),
    }
