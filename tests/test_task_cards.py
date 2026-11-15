from __future__ import annotations

from scs_fkb.knowledge_v2.task_cards import (
    build_from_playbooks,
    load_task_cards,
    validate_task_cards,
)

FACT = {"id": "FACT-TEST-001", "status": "approved", "subject": "休渔", "predicate": "时间"}
PLAYBOOK = {
    "id": "PLAY-CAPTAIN-001",
    "title": "休渔合规自查",
    "persona": "captain",
    "status": "approved",
    "applies_to": {"region": ["national"], "year": 2026},
    "steps": [
        {
            "order": 1,
            "action": "核对休渔时间",
            "detail": "5月1日至8月16日",
            "facts": ["FACT-TEST-001"],
        }
    ],
    "documents": ["捕捞许可证"],
    "deadlines": ["5月1日12时前"],
    "review_due": "2027-02-02",
}


def test_build_from_playbook_creates_draft_card() -> None:
    cards = build_from_playbooks([PLAYBOOK], facts=[FACT])
    assert len(cards) == 1
    card = cards[0]
    assert card["id"] == "TASK-CAPTAIN-001"
    assert card["status"] == "draft"
    assert card["steps"][0]["facts"] == ["FACT-TEST-001"]
    assert card["source"] == {"kind": "playbook", "id": "PLAY-CAPTAIN-001"}
    assert validate_task_cards(cards, facts=[FACT], playbooks=[PLAYBOOK]) == []


def test_task_card_with_unknown_fact_is_rejected() -> None:
    cards = build_from_playbooks([PLAYBOOK], facts=[FACT])
    cards[0]["steps"][0]["facts"] = ["FACT-MISSING-999"]
    errors = validate_task_cards(cards, facts=[FACT], playbooks=[PLAYBOOK])
    assert any("unknown fact" in error for error in errors)


def test_task_card_with_no_steps_is_rejected() -> None:
    cards = build_from_playbooks([PLAYBOOK], facts=[FACT])
    cards[0]["steps"] = []
    errors = validate_task_cards(cards, facts=[FACT], playbooks=[PLAYBOOK])
    assert any("steps must be a non-empty list" in error for error in errors)


def test_live_task_cards_validate() -> None:
    cards = load_task_cards()
    from scs_fkb.facts import load_all
    from scs_fkb.knowledge_v2.playbooks import load_playbooks

    assert cards
    assert validate_task_cards(cards, facts=load_all(), playbooks=load_playbooks()) == []
    assert all(card["status"] in {"draft", "approved", "retired"} for card in cards)
