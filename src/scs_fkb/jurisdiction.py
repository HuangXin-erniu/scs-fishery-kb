from __future__ import annotations

# Province names used by the corpus, mapped to the jurisdiction codes recorded in
# the reference collections. The order matters when a question names more than one.
PROVINCES: dict[str, str] = {
    "海南": "hainan",
    "广西": "guangxi",
    "广东": "guangdong",
    "汕头": "guangdong",
    "湛江": "guangdong",
    "阳江": "guangdong",
    "福建": "fujian",
}


def question_jurisdiction(text: str) -> str | None:
    """Return the jurisdiction named in the question, or None."""
    for name, code in PROVINCES.items():
        if name in text:
            return code
    return None
