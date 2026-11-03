from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml


def species_card_id(scientific: str) -> str:
    slug = re.sub(r"[^A-Z0-9]+", "-", scientific.upper()).strip("-")
    return f"WEB-WORMS-{slug}"


def species_note(card: dict[str, Any], text: str, index: int) -> dict[str, Any] | None:
    try:
        records = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(records, list) or not records:
        return None
    record = records[0]
    scientific = str(record.get("scientificname") or "").strip()
    if not scientific:
        return None
    classification = " > ".join(
        str(record.get(field) or "?") for field in ("phylum", "class", "order", "family")
    )
    facts = [
        {"label": "学名", "value": scientific},
        {"label": "命名人", "value": str(record.get("authority") or "未记录")},
        {"label": "分类", "value": classification},
        {
            "label": "海洋/淡水",
            "value": (
                f"海洋={record.get('isMarine')} 半咸水={record.get('isBrackish')} "
                f"淡水={record.get('isFreshwater')}"
            ),
        },
        {"label": "WoRMS ID", "value": str(record.get("AphiaID") or "")},
    ]
    remark = "分布与保护等级尚未核实，仅提供分类事实。"
    return {
        "id": f"KNO-SPECIES-{index:03d}",
        "title": f"{card.get('title', scientific)}",
        "summary": f"{scientific} 在 WoRMS 的分类记录；{remark}",
        "facts": facts,
        "sea_area": "南海",
        "species": [scientific],
        "as_of": "2026-11-03",
        "review_due": "2027-02-01",
        "status": "approved",
        "confidence": "high",
        "sources": [
            {
                "card": card["id"],
                "sha256": card["sha256"],
                "url": card["url"],
                "publisher": "WoRMS",
                "fetched_at": card["fetched_at"],
            }
        ],
        "tags": ["species", "taxonomy"],
    }


def build_species_notes(
    cards_path: Path,
    cache_root: Path,
    knowledge_path: Path,
    seed_path: Path,
) -> dict[str, Any]:
    cards = {
        str(card["id"]): card
        for card in yaml.safe_load(Path(cards_path).read_text(encoding="utf-8"))["cards"]
    }
    seed = yaml.safe_load(Path(seed_path).read_text(encoding="utf-8"))["species"]
    data = yaml.safe_load(Path(knowledge_path).read_text(encoding="utf-8"))
    notes = list(data.get("notes") or [])
    known = {note.get("species", [""])[0] for note in notes}
    next_index = (
        max(
            [int(note["id"].rsplit("-", 1)[1]) for note in notes if note["id"].count("-") == 2]
            or [0]
        )
        + 1
    )
    added: list[str] = []
    skipped: list[dict[str, str]] = []
    for entry in seed:
        scientific = str(entry.get("scientific") or "").strip()
        zh = str(entry.get("zh") or scientific)
        if scientific in known:
            continue
        card_id = species_card_id(scientific)
        card = cards.get(card_id)
        if card is None or card.get("status") != "ok":
            skipped.append({"scientific": scientific, "reason": "card missing or not ok"})
            continue
        text_path = Path(cache_root) / str(card["file"])
        if not text_path.is_file():
            skipped.append({"scientific": scientific, "reason": "cache missing"})
            continue
        text = text_path.read_text(encoding="utf-8")
        card = {**card, "title": f"{zh} {scientific}"}
        note = species_note(card, text, next_index)
        if note is None:
            skipped.append({"scientific": scientific, "reason": "empty WoRMS record"})
            continue
        notes.append(note)
        known.add(scientific)
        added.append(note["id"])
        next_index += 1
    if added:
        data["notes"] = notes
        Path(knowledge_path).write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
    return {"added": added, "skipped": skipped, "total": len(notes)}
