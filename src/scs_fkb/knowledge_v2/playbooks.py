from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from ..facts import DEFAULT_FACTS_DIR, load_all
from ..registry import load_registry

PLAYBOOK_ID = re.compile(r"PLAY-[A-Z]+-\d{3}")
PERSONAS = frozenset({"captain", "owner", "enforcement", "extension"})
STATUSES = frozenset({"draft", "approved", "stale"})
DEFAULT_PLAYBOOKS = Path("configs") / "playbooks"


class PlaybookError(RuntimeError):
    """Raised when a playbook is malformed or cites an unusable fact."""


@dataclass(frozen=True)
class PlaybookCheck:
    playbooks: int
    approved: int
    steps: int
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "playbooks": self.playbooks,
            "approved": self.approved,
            "steps": self.steps,
            "errors": self.errors,
        }


def load_playbooks(path: Path | str = DEFAULT_PLAYBOOKS) -> list[dict[str, Any]]:
    source = Path(path)
    if source.is_dir():
        files = sorted(source.glob("*.yaml"))
    elif source.is_file():
        files = [source]
    else:
        raise PlaybookError(f"playbooks not found: {source}")
    playbooks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for file_path in files:
        data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        items = data.get("playbooks") if isinstance(data, dict) else None
        if not isinstance(items, list):
            raise PlaybookError(f"playbooks is not a list: {file_path}")
        for item in items:
            if not isinstance(item, dict):
                raise PlaybookError(f"playbook is not a mapping: {file_path}")
            identifier = str(item.get("id") or "")
            if identifier in seen:
                raise PlaybookError(f"duplicate playbook id: {identifier}")
            seen.add(identifier)
            playbooks.append(item)
    return playbooks


def _iso(value: Any, label: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise PlaybookError(f"{label} is not an ISO date") from exc


def validate_playbook(
    playbook: dict[str, Any],
    *,
    facts: dict[str, dict[str, Any]],
    registry: dict[str, dict[str, Any]],
) -> list[str]:
    playbook_id = str(playbook.get("id") or "<unknown>")
    errors: list[str] = []
    for key in ("id", "title", "persona", "applies_to", "steps", "sources", "status", "review_due"):
        if key not in playbook:
            errors.append(f"{playbook_id}: missing {key}")
    if not PLAYBOOK_ID.fullmatch(playbook_id):
        errors.append(f"{playbook_id}: id must match PLAY-<PERSONA>-NNN")
    if playbook.get("persona") not in PERSONAS:
        errors.append(f"{playbook_id}: persona {playbook.get('persona')!r} is invalid")
    if not str(playbook.get("title") or "").strip():
        errors.append(f"{playbook_id}: title is empty")
    if playbook.get("status") not in STATUSES:
        errors.append(f"{playbook_id}: status {playbook.get('status')!r} is invalid")
    applies = playbook.get("applies_to")
    if not isinstance(applies, dict) or not applies:
        errors.append(f"{playbook_id}: applies_to must be a non-empty mapping")
    try:
        _iso(playbook.get("review_due"), f"{playbook_id}.review_due")
    except PlaybookError as exc:
        errors.append(str(exc))
    sources = playbook.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append(f"{playbook_id}: sources must be a non-empty list")
    else:
        for source in sources:
            if str(source) not in registry:
                errors.append(f"{playbook_id}: source {source!r} is not in the registry")
    steps = playbook.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append(f"{playbook_id}: steps must be a non-empty list")
        return errors
    orders: set[int] = set()
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            errors.append(f"{playbook_id}: step #{index} is not a mapping")
            continue
        order = step.get("order")
        if not isinstance(order, int):
            errors.append(f"{playbook_id}: step #{index} order is not an integer")
        elif order in orders:
            errors.append(f"{playbook_id}: duplicate step order {order}")
        else:
            orders.add(order)
        for key in ("action", "detail"):
            if not str(step.get(key) or "").strip():
                errors.append(f"{playbook_id}: step #{index} {key} is empty")
        fact_ids = step.get("facts")
        if not isinstance(fact_ids, list) or not fact_ids:
            errors.append(f"{playbook_id}: step #{index} needs at least one fact")
            continue
        for fact_id in fact_ids:
            fact = facts.get(str(fact_id))
            if fact is None:
                errors.append(f"{playbook_id}: step #{index} fact {fact_id!r} is unknown")
            elif fact.get("status") != "approved":
                errors.append(
                    f"{playbook_id}: step #{index} fact {fact_id!r} "
                    f"is {fact.get('status')}, not approved"
                )
    return errors


def check_playbooks(
    path: Path | str = DEFAULT_PLAYBOOKS,
    *,
    facts_dir: Path | str = DEFAULT_FACTS_DIR,
    registry_path: Path | str | None = None,
) -> PlaybookCheck:
    playbooks = load_playbooks(path)
    fact_rows = load_all(facts_dir)
    facts = {str(fact["id"]): fact for fact in fact_rows}
    registry = load_registry(registry_path) if registry_path else load_registry()
    errors: list[str] = []
    steps = 0
    for playbook in playbooks:
        errors.extend(validate_playbook(playbook, facts=facts, registry=registry))
        steps += len(playbook.get("steps") or [])
    approved = sum(1 for playbook in playbooks if playbook.get("status") == "approved")
    return PlaybookCheck(
        playbooks=len(playbooks),
        approved=approved,
        steps=steps,
        errors=errors,
    )


def render_playbook(playbook: dict[str, Any], facts: dict[str, dict[str, Any]]) -> str:
    lines = [str(playbook.get("title") or playbook.get("id"))]
    for step in playbook.get("steps") or []:
        refs = []
        for fact_id in step.get("facts") or []:
            fact = facts.get(str(fact_id)) or {}
            source = fact.get("source") or {}
            refs.append(f"{fact_id} {source.get('doc')} §{source.get('section') or '全文'}")
        lines.append(f"{step.get('order')}. {step.get('action')}：{step.get('detail')}")
        if refs:
            lines.append("   依据：" + "；".join(refs))
    return "\n".join(lines)


__all__ = [
    "DEFAULT_PLAYBOOKS",
    "PERSONAS",
    "PLAYBOOK_ID",
    "PlaybookCheck",
    "PlaybookError",
    "check_playbooks",
    "load_playbooks",
    "render_playbook",
    "validate_playbook",
]
