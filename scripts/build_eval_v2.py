#!/usr/bin/env python3
"""Build the deterministic 120-question v2 evaluation set."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml

from scs_fkb.facts import load_all
from scs_fkb.registry import load_registry

TOKEN_RE = re.compile(
    r"\d+(?:\.\d+)?(?:%|‰|万元|元|毫米|米|海里|节|吨|千瓦|年|月|日|天|艘|人|次|小时|分钟|度|分|秒|个|种|类)?"
    r"|[\u4e00-\u9fff]{2,8}"
)
STOP = {
    "以及",
    "或者",
    "应当",
    "可以",
    "按照",
    "规定",
    "进行",
    "有关",
    "其他",
    "不得",
    "依法",
    "我们",
    "什么",
    "哪些",
    "如何",
    "是否",
}
ABSTENTION = [
    ("某渔场的历史渔汛期与主要经济鱼种是什么？", "placeholder"),
    ("某年度南海区拖网渔船数量是多少？", "placeholder"),
    ("今年第5号台风对南海渔场的影响如何？", "no_hazard_source"),
    ("未来一周南海海温预报是多少？", "no_forecast_source"),
    ("某品种的IUCN保护等级是什么？", "placeholder"),
    ("某海域的珊瑚礁覆盖率是多少？", "placeholder"),
    ("2027年南海伏季休渔时间是否已经公布？", "future"),
    ("某渔港的泊位数量是多少？", "placeholder"),
    ("某类渔船的船员最低配员是多少？", "placeholder"),
    ("历史渔汛与中心渔场如何变化？", "no_source"),
]


def _terms(value: str, subject: str, predicate: str) -> list[str]:
    terms: list[str] = []
    for match in TOKEN_RE.findall(f"{subject} {predicate} {value}"):
        token = match.strip()
        if len(token) < 2 or token in STOP:
            continue
        if token not in terms:
            terms.append(token)
        if len(terms) >= 8:
            break
    return terms


def _question(fact: dict, draft: bool) -> str:
    subject = str(fact.get("subject") or "").strip()
    predicate = str(fact.get("predicate") or "").strip()
    if draft:
        return f"{subject}的条文要点是什么？"
    templates = {
        "time_range": f"{subject}的{predicate}是什么时间？",
        "scope": f"{subject}的{predicate}包括哪些？",
        "procedure": f"{subject}的{predicate}要求是什么？",
        "materials": f"{subject}的{predicate}需要哪些材料？",
        "penalty": f"{subject}的{predicate}是什么？",
        "definition": f"{subject}的{predicate}是什么？",
        "quantity": f"{subject}的{predicate}是多少？",
        "status": f"{subject}的{predicate}是什么？",
        "inspection": f"{subject}的{predicate}包括哪些？",
        "operation_type": f"{subject}的{predicate}包括哪些？",
    }
    return templates.get(str(fact.get("question_class")), f"{subject}的{predicate}是什么？")


def _entry(index: int, fact: dict, split: str, reviewed: bool) -> dict:
    source = fact.get("source") or {}
    draft = not reviewed
    return {
        "id": f"EV2-{index:03d}",
        "question": _question(fact, draft),
        "split": split,
        "persona": "extension" if fact.get("topic") in {"gear", "stats"} else "captain",
        "expected": {
            "answer": str(fact.get("value") or ""),
            "terms": _terms(
                str(fact.get("value") or ""),
                str(fact.get("subject") or ""),
                str(fact.get("predicate") or ""),
            ),
            "evidence": [
                {
                    "doc": str(source.get("doc") or ""),
                    **({"section": str(source.get("section"))} if source.get("section") else {}),
                }
            ],
            "abstained": False,
        },
        "source_fact": str(fact.get("id") or ""),
        "review_status": "reviewed" if reviewed else "draft",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="configs/eval-v2.yaml")
    args = parser.parse_args(argv)
    facts = load_all("configs/facts")
    approved = sorted(
        [fact for fact in facts if fact.get("status") == "approved"],
        key=lambda fact: str(fact["id"]),
    )
    drafts = sorted(
        [fact for fact in facts if fact.get("status") == "draft"],
        key=lambda fact: str(fact["id"]),
    )
    if len(approved) != 80:
        raise SystemExit(f"expected 80 approved facts, found {len(approved)}")
    if len(drafts) < 30:
        raise SystemExit(f"expected at least 30 draft facts, found {len(drafts)}")
    questions = [_entry(index, fact, "dev", True) for index, fact in enumerate(approved, 1)]
    for offset, fact in enumerate(drafts[:30], start=81):
        questions.append(_entry(offset, fact, "test", False))
    for offset, (question, reason) in enumerate(ABSTENTION, start=111):
        questions.append(
            {
                "id": f"EV2-{offset:03d}",
                "question": question,
                "split": "test",
                "persona": "captain",
                "expected": {
                    "answer": "证据不足",
                    "terms": [],
                    "evidence": [],
                    "abstained": True,
                    "reason": reason,
                },
                "source_fact": "",
                "review_status": "reviewed",
            }
        )
    registry = load_registry("configs/corpus.yaml")
    for item in questions:
        for evidence in item["expected"]["evidence"]:
            if evidence["doc"] not in registry:
                raise SystemExit(f"{item['id']}: evidence doc {evidence['doc']} not in registry")
    data = {
        "schema_version": 1,
        "updated_at": "2026-11-06",
        "description": (
            "Deterministic v2 evaluation set: 80 reviewed fact questions, "
            "30 draft provision questions and 10 abstention cases."
        ),
        "questions": questions,
    }
    Path(args.out).write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    print(
        f"wrote {len(questions)} questions: "
        f"{sum(1 for q in questions if q['split'] == 'dev')} dev, "
        f"{sum(1 for q in questions if q['split'] == 'test')} test"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
