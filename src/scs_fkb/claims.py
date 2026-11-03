from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml

NATURES = (
    "definition",
    "rule",
    "quantity",
    "status",
    "warning",
    "identification",
    "history",
)
DOMAINS = ("policy", "gear", "environment", "hazard", "species", "statistics", "port")
# Deterministic tie-break: a more specific, time-critical claim wins.
PRIORITY = ("warning", "identification", "status", "quantity", "rule", "definition", "history")


class ClaimError(RuntimeError):
    """Raised when the claim configuration is malformed."""


def load_claims(path: Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.is_file():
        raise ClaimError(f"claims.missing: {config_path}")
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ClaimError(f"claims.invalid: {config_path}")
    natures = data.get("natures")
    domains = data.get("domains")
    if not isinstance(natures, dict) or set(natures) != set(NATURES):
        raise ClaimError(f"claims.invalid: natures must be {sorted(NATURES)}")
    if not isinstance(domains, dict) or set(domains) != set(DOMAINS):
        raise ClaimError(f"claims.invalid: domains must be {sorted(DOMAINS)}")
    for name, nature in natures.items():
        if not isinstance(nature, dict) or not nature.get("keywords"):
            raise ClaimError(f"claims.invalid: nature {name} needs keywords")
        window = nature.get("window_days")
        if window is not None and (not isinstance(window, int) or window <= 0):
            raise ClaimError(f"claims.invalid: nature {name} window_days must be null or positive")
        primary = nature.get("primary")
        if not isinstance(primary, dict):
            raise ClaimError(f"claims.invalid: nature {name} needs primary rules")
        for key in ("trust", "classes", "kinds"):
            if not isinstance(primary.get(key), list) or not primary[key]:
                raise ClaimError(f"claims.invalid: nature {name} primary.{key} is empty")
    for name, keywords in domains.items():
        if not isinstance(keywords, list) or not keywords:
            raise ClaimError(f"claims.invalid: domain {name} needs keywords")
    return data


def _score(question: str, keywords: list[str]) -> int:
    return sum(1 for keyword in keywords if keyword and keyword in question)


def classify(question: str, config: dict[str, Any]) -> dict[str, Any]:
    """Return the claim nature and domain, with a general fallback when nothing matches."""
    nature_scores = {
        name: _score(question, nature["keywords"]) for name, nature in config["natures"].items()
    }
    best_nature = max(
        NATURES,
        key=lambda name: (nature_scores.get(name, 0), -PRIORITY.index(name)),
    )
    if nature_scores.get(best_nature, 0) == 0:
        best_nature = "general"
    domain_scores = {
        name: _score(question, keywords) for name, keywords in config["domains"].items()
    }
    best_domain = max(DOMAINS, key=lambda name: domain_scores.get(name, 0))
    if domain_scores.get(best_domain, 0) == 0:
        best_domain = "general"
    return {
        "nature": best_nature,
        "domain": best_domain,
        "nature_hits": nature_scores.get(best_nature, 0),
        "domain_hits": domain_scores.get(best_domain, 0),
        "confidence": "high" if nature_scores.get(best_nature, 0) >= 2 else "medium",
    }


def select_evidence(
    question: str,
    hits: list[Any],
    config: dict[str, Any],
    *,
    today: date | None = None,
) -> dict[str, Any]:
    """Filter hits by the claim matrix and return primary plus supporting evidence."""
    result = classify(question, config)
    nature = result["nature"]
    current = today or date.today()
    if nature == "general":
        rules: dict[str, Any] = {"kinds": ["corpus"], "classes": [], "trust": []}
        window = None
    else:
        nature_config = config["natures"][nature]
        rules = nature_config["primary"]
        window = nature_config.get("window_days")
    kept = []
    for hit in hits:
        chunk = hit.chunk
        if rules.get("kinds") and chunk.kind not in rules["kinds"]:
            continue
        if rules.get("classes") and chunk.source_class not in rules["classes"]:
            continue
        if rules.get("trust") and chunk.trust not in rules["trust"]:
            continue
        if window and nature in {"status", "quantity", "warning"} and chunk.review_due:
            try:
                if date.fromisoformat(chunk.review_due) < current:
                    continue
            except ValueError:
                pass
        kept.append(hit)
    return {
        "nature": nature,
        "domain": result["domain"],
        "primary": kept[0] if kept else None,
        "supporting": kept[1:4],
        "admissible": kept,
    }


def record_gap(
    path: Path,
    question: str,
    reason: str,
    nature: str,
    domain: str,
) -> None:
    """Append a refused question to the local knowledge-gap file."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "question": question,
        "reason": reason,
        "nature": nature,
        "domain": domain,
    }
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
