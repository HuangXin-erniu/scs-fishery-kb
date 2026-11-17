"""Detect answer cross-contamination before accepting a batch."""

from __future__ import annotations

import re
from collections import defaultdict

REFUSAL_MARKERS = ("证据不足", "未能生成可核验", "无法回答")
TOPICS = {
    "鲎": "鲎",
    "海龟": "海龟",
    "白海豚": "海豚",
    "休渔": "休渔",
    "禁渔": "禁渔",
    "捕捞许可": "捕捞许可",
    "船网": "船网",
    "检验": "检验",
    "登记": "登记",
    "明火": "明火",
    "电鱼": "电鱼",
    "赤潮": "赤潮",
    "低氧": "缺氧",
    "热浪": "热浪",
    "保险": "保险",
    "补贴": "补贴",
    "追溯": "追溯",
    "三无": "三无",
}


def normalize(text: str) -> str:
    return re.sub(r"[\s\W]+", "", text or "")


def check(rows: list[dict]) -> list[tuple[str, str, str]]:
    problems: list[tuple[str, str, str]] = []
    seen: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        text = str(row.get("visible_answer") or "")
        if any(marker in text for marker in REFUSAL_MARKERS):
            continue
        key = normalize(text)[:80]
        if len(key) >= 40:
            seen[key].append(str(row.get("id")))
    for key, ids in seen.items():
        if len(ids) > 1:
            problems.append(("DUP_ANSWER", ",".join(ids), key[:40]))
    for row in rows:
        question = str(row.get("question") or "")
        topics = {value for name, value in TOPICS.items() if name in question}
        if not topics:
            continue
        blob = str(row.get("visible_answer") or "")
        if not any(topic in blob for topic in topics):
            problems.append(("TOPIC_MISMATCH", str(row.get("id")), f"问句主题 {sorted(topics)}"))
    return problems
