from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

import yaml

NOTE_ID = re.compile(r"KNO-[A-Z]+-\d{3}")
TOPICS = frozenset({"species", "policy", "gear", "environment", "hazard", "stats"})
STATUSES = frozenset({"draft", "approved", "stale", "retired"})
CONFIDENCE = frozenset({"high", "medium", "low"})
REQUIRED = (
    "id",
    "title",
    "summary",
    "facts",
    "as_of",
    "review_due",
    "status",
    "confidence",
    "sources",
)


class KnowledgeError(RuntimeError):
    """Raised when a knowledge file or note is malformed."""


def _iso(value: Any, field: str, note_id: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise KnowledgeError(f"{note_id}: {field} is not an ISO date") from exc


def validate_note(note: Any, topic: str | None = None) -> list[str]:
    if not isinstance(note, dict):
        return ["note is not a mapping"]
    note_id = str(note.get("id") or "<unknown>")
    errors: list[str] = []
    for key in REQUIRED:
        if key not in note:
            errors.append(f"{note_id}: missing {key}")
    if not NOTE_ID.fullmatch(note_id):
        errors.append(f"{note_id}: id must match KNO-<TOPIC>-<NNN>")
    if topic and note.get("topic") not in (None, topic):
        errors.append(f"{note_id}: topic {note.get('topic')!r} does not match file topic {topic!r}")
    if note.get("status") not in STATUSES:
        errors.append(f"{note_id}: status {note.get('status')!r} not in {sorted(STATUSES)}")
    if note.get("confidence") not in CONFIDENCE:
        errors.append(
            f"{note_id}: confidence {note.get('confidence')!r} not in {sorted(CONFIDENCE)}"
        )
    facts = note.get("facts")
    if not isinstance(facts, list) or not facts:
        errors.append(f"{note_id}: facts must be a non-empty list")
    else:
        for fact in facts:
            if not isinstance(fact, dict) or not fact.get("label") or not fact.get("value"):
                errors.append(f"{note_id}: each fact needs label and value")
    sources = note.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append(f"{note_id}: sources must be a non-empty list")
    else:
        for source in sources:
            if not isinstance(source, dict) or not (source.get("card") or source.get("doc")):
                errors.append(f"{note_id}: source needs card or doc")
            elif source.get("card") and not source.get("sha256"):
                errors.append(f"{note_id}: card source needs sha256")
    try:
        as_of = _iso(note.get("as_of"), "as_of", note_id)
        review_due = _iso(note.get("review_due"), "review_due", note_id)
        if review_due < as_of:
            errors.append(f"{note_id}: review_due is before as_of")
        if note.get("expires_at"):
            _iso(note["expires_at"], "expires_at", note_id)
    except KnowledgeError as exc:
        errors.append(str(exc))
    return errors


def load_knowledge(path: Path) -> dict[str, Any]:
    source = Path(path)
    if not source.is_file():
        raise KnowledgeError(f"knowledge.missing: {source}")
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise KnowledgeError(f"knowledge.invalid: {source}")
    topic = data.get("topic")
    if topic not in TOPICS:
        raise KnowledgeError(f"knowledge.invalid: topic {topic!r} in {source}")
    notes = data.get("notes")
    if not isinstance(notes, list):
        raise KnowledgeError(f"knowledge.invalid: notes is not a list in {source}")
    seen: set[str] = set()
    for note in notes:
        errors = validate_note(note, str(topic))
        if errors:
            raise KnowledgeError("; ".join(errors))
        if note["id"] in seen:
            raise KnowledgeError(f"knowledge.invalid: duplicate id {note['id']}")
        seen.add(note["id"])
    return data


def load_all(directory: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(Path(directory).glob("*.yaml")):
        data = load_knowledge(path)
        for note in data["notes"]:
            rows.append({**note, "_path": path, "_topic": data["topic"]})
    return rows


def _card_hashes(cards_path: Path) -> dict[str, str]:
    if not Path(cards_path).is_file():
        return {}
    data = yaml.safe_load(Path(cards_path).read_text(encoding="utf-8")) or {}
    return {
        str(card["id"]): str(card.get("sha256") or "")
        for card in data.get("cards") or []
        if isinstance(card, dict) and card.get("id")
    }


def stale_reasons(note: dict[str, Any], cards: dict[str, str], today: date) -> list[str]:
    reasons: list[str] = []
    for source in note.get("sources") or []:
        card = source.get("card")
        if not card:
            continue
        if card not in cards:
            reasons.append(f"source card {card} is missing from the card registry")
        elif cards[card] != source.get("sha256"):
            reasons.append(f"source card {card} changed since the note was written")
    if note.get("topic") == "hazard" and note.get("expires_at"):
        if _iso(note["expires_at"], "expires_at", str(note["id"])) < today:
            reasons.append("hazard note expired")
    return reasons


def check(
    directory: Path,
    cards_path: Path,
    *,
    today: date | None = None,
    write: bool = False,
) -> dict[str, Any]:
    current = today or date.today()
    cards = _card_hashes(cards_path)
    rows: list[dict[str, Any]] = []
    changed: list[Path] = []
    for path in sorted(Path(directory).glob("*.yaml")):
        data = load_knowledge(path)
        mutated = False
        for note in data["notes"]:
            reasons = stale_reasons(note, cards, current)
            due = _iso(note["review_due"], "review_due", str(note["id"])) <= current
            if reasons and note["status"] in {"draft", "approved"}:
                note["status"] = "stale"
                mutated = True
            rows.append(
                {
                    "id": note["id"],
                    "topic": data["topic"],
                    "status": note["status"],
                    "due": due,
                    "reasons": reasons,
                }
            )
        if mutated and write:
            changed.append(path)
            path.write_text(
                yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
            )
    return {
        "notes": rows,
        "stale": sum(1 for row in rows if row["status"] == "stale"),
        "due": sum(1 for row in rows if row["due"]),
        "written": [str(path) for path in changed],
    }


def approve(directory: Path, note_id: str, *, today: date | None = None) -> dict[str, Any]:
    current = today or date.today()
    cards = _card_hashes(Path(directory).parent / "web-cards.yaml")
    for path in sorted(Path(directory).glob("*.yaml")):
        data = load_knowledge(path)
        for note in data["notes"]:
            if note["id"] != note_id:
                continue
            reasons = stale_reasons(note, cards, current)
            if reasons:
                raise KnowledgeError(f"{note_id}: cannot approve: {'; '.join(reasons)}")
            if note["status"] != "draft":
                raise KnowledgeError(f"{note_id}: status is {note['status']}, not draft")
            note["status"] = "approved"
            path.write_text(
                yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
            )
            return {"id": note_id, "status": "approved", "path": str(path)}
    raise KnowledgeError(f"{note_id}: note not found")


def list_notes(directory: Path) -> list[dict[str, Any]]:
    return [
        {
            "id": note["id"],
            "topic": note["_topic"],
            "title": note["title"],
            "status": note["status"],
            "review_due": note["review_due"],
        }
        for note in load_all(directory)
    ]
