from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .contract import Channel

DEFAULT_CONFIG = Path(__file__).resolve().parents[3] / "configs" / "answer-channels.yaml"


@dataclass(frozen=True)
class GapRule:
    gap: str
    match: tuple[str, ...]
    channels: tuple[Channel, ...]


@dataclass
class ChannelBook:
    default: tuple[Channel, ...]
    out_of_scope: tuple[Channel, ...]
    rules: tuple[GapRule, ...]

    @classmethod
    def load(cls, path: Path | str = DEFAULT_CONFIG) -> ChannelBook:
        import yaml

        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}

        def channels(items: list[dict] | None) -> tuple[Channel, ...]:
            return tuple(
                Channel(
                    name=str(item.get("name") or ""),
                    hint=str(item.get("hint") or ""),
                    doc_id=str(item.get("doc_id") or ""),
                )
                for item in items or []
                if item.get("name")
            )

        rules = tuple(
            GapRule(
                gap=str(rule.get("gap") or ""),
                match=tuple(str(word) for word in rule.get("match") or []),
                channels=channels(rule.get("channels")),
            )
            for rule in data.get("gaps") or []
        )
        return cls(
            default=channels(data.get("default")),
            out_of_scope=channels(data.get("out_of_scope")),
            rules=rules,
        )

    def resolve(self, question: str, *, scope: bool = False) -> tuple[str, tuple[Channel, ...]]:
        if scope:
            return "超出近海范围", self.out_of_scope or self.default
        for rule in self.rules:
            if any(word in question for word in rule.match):
                return rule.gap, rule.channels or self.default
        return "语料未收录", self.default
