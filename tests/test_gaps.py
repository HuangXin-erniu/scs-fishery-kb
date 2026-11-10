from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from scs_fkb.gaps import collect_gaps


def test_collect_gaps_reads_feedback_and_query_logs(tmp_path: Path) -> None:
    day = datetime.now(UTC).date().isoformat()
    (tmp_path / "queries").mkdir()
    rows = [
        {
            "request_id": "REQ-1",
            "created_at": datetime.now(UTC).isoformat(),
            "question": "某渔场历史渔汛？",
            "mode": "abstain",
            "reason": "weak_evidence",
            "abstained": True,
            "latency_ms": 12,
        },
        {
            "request_id": "REQ-2",
            "created_at": datetime.now(UTC).isoformat(),
            "question": "某渔场历史渔汛？",
            "mode": "abstain",
            "reason": "weak_evidence",
            "abstained": True,
            "latency_ms": 10,
        },
        {
            "request_id": "REQ-3",
            "created_at": datetime.now(UTC).isoformat(),
            "question": "休渔时间",
            "mode": "kb_only",
            "reason": "ok",
            "abstained": False,
            "latency_ms": 9,
        },
    ]
    (tmp_path / "queries" / f"{day}.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "feedback.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"question": "休渔时间", "helpful": False}, ensure_ascii=False),
                json.dumps(
                    {
                        "source": "kb",
                        "item_id": "FAQ-001",
                        "kind": "faq",
                        "helpful": False,
                        "comment": "太短",
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {"source": "kb", "item_id": "FAQ-001", "kind": "faq", "helpful": True},
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    gaps = collect_gaps(tmp_path)
    assert gaps["queries"]["total"] == 3
    assert gaps["queries"]["abstained"] == 2
    assert gaps["reasons"]["weak_evidence"] == 2
    assert gaps["feedback"] == {"total": 3, "unhelpful": 2}
    assert gaps["kb"]["total"] == 2
    assert gaps["kb"]["unhelpful"] == 1
    assert gaps["kb"]["top_items"] == [{"item_id": "FAQ-001", "count": 1}]
    assert gaps["top_questions"][0] == {"question": "某渔场历史渔汛？", "count": 2}


def test_collect_gaps_without_a_run_root() -> None:
    gaps = collect_gaps(None)
    assert gaps["queries"]["total"] == 0
    assert gaps["note"] == "run root is unset"
