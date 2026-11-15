from __future__ import annotations

from dataclasses import dataclass

ANSWERABILITY = ("answerable", "partial", "abstain")


@dataclass(frozen=True)
class VersionNote:
    doc_id: str
    document_no: str = ""
    effective: str = ""
    title: str = ""


@dataclass(frozen=True)
class AsOf:
    declared: str
    basis: str
    versions: tuple[VersionNote, ...] = ()


@dataclass(frozen=True)
class NumericAnchor:
    value: str
    unit: str = ""
    basis: str = ""
    location: str = ""


@dataclass(frozen=True)
class SlotView:
    """One answered part of a multi-part question, as shown in the summary."""

    text: str
    doc_id: str = ""
    section: str = ""
    kind: str = ""
    score: float = 0.0

    def label(self) -> str:
        where = f"§{self.section}" if self.section else ""
        return f"[{self.doc_id}{(' ' + where) if where else ''}]"


@dataclass(frozen=True)
class Channel:
    name: str
    hint: str
    doc_id: str = ""


@dataclass(frozen=True)
class AnswerContract:
    answerability: str
    conclusion: str
    conditions: tuple[str, ...] = ()
    gap: tuple[str, ...] = ()
    channel: tuple[Channel, ...] = ()
    as_of: AsOf | None = None
    numbers: tuple[NumericAnchor, ...] = ()
    slots: tuple[SlotView, ...] = ()
    body: str = ""
    # Where the user-facing summary came from: ``model`` (a verified model
    # draft), ``fallback`` (the model was asked and its draft was dropped) or
    # ``deterministic`` (no model attempt). The spot check records this per row
    # so a silent fallback cannot be mistaken for a model-written answer.
    summary_source: str = ""

    def to_dict(self) -> dict:
        return {
            "answerability": self.answerability,
            "summary_source": self.summary_source,
            "conclusion": self.conclusion,
            "conditions": list(self.conditions),
            "gap": list(self.gap),
            "channel": [
                {"name": item.name, "hint": item.hint, "doc_id": item.doc_id}
                for item in self.channel
            ],
            "as_of": (
                {
                    "declared": self.as_of.declared,
                    "basis": self.as_of.basis,
                    "versions": [
                        {
                            "doc_id": version.doc_id,
                            "document_no": version.document_no,
                            "effective": version.effective,
                            "title": version.title,
                        }
                        for version in self.as_of.versions
                    ],
                }
                if self.as_of
                else None
            ),
            "numbers": [
                {
                    "value": item.value,
                    "unit": item.unit,
                    "basis": item.basis,
                    "location": item.location,
                }
                for item in self.numbers
            ],
            "slots": [
                {
                    "text": item.text,
                    "doc_id": item.doc_id,
                    "section": item.section,
                    "kind": item.kind,
                    "score": round(item.score, 4),
                }
                for item in self.slots
            ],
        }
