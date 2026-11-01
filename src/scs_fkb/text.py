from __future__ import annotations

import re

_CJK_RE = re.compile(r"[\u4e00-\u9fff]+")
_ASCII_RE = re.compile(r"[A-Za-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Tokenize Chinese as bigrams (unigrams for single-character runs) and ASCII words."""
    tokens: list[str] = []
    for run in _CJK_RE.findall(text):
        if len(run) == 1:
            tokens.append(run)
        else:
            tokens.extend(run[index : index + 2] for index in range(len(run) - 1))
    tokens.extend(match.lower() for match in _ASCII_RE.findall(text))
    return tokens
