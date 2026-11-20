#!/usr/bin/env python3
"""Pre-flight a pool before packaging: section binding, penalty clause, subquestions.

Checks, per answered row:
  1. every number in the visible answer appears in at least one cited chunk;
  2. a monetary/confiscation conclusion cites a chunk that actually carries a
     penalty (罚款/没收/吊销), not only a prohibition;
  3. a multi-part question gets a conclusion sentence (结论/应/不得/处) rather
     than a bare quotation.

Usage: check_pool_binding.py questions.csv answers.jsonl chunks.jsonl
"""

import csv
import json
import re
import sys
from collections import defaultdict

PENALTY = re.compile(r"罚款|没收|吊销|拘留")
CONCLUSION = re.compile(r"结论|应当|必须|不得|禁止|处[一二三四五六七八九十百千万\d]|可以")


def main(qpath, apath, cpath) -> int:
    qs = {r["id"]: r for r in csv.DictReader(open(qpath, encoding="utf-8-sig"))}
    chunks = defaultdict(list)
    for line in open(cpath, encoding="utf-8"):
        if line.strip():
            row = json.loads(line)
            chunks[row["doc_id"]].append(row)
    answers = [json.loads(l) for l in open(apath, encoding="utf-8") if l.strip()]
    binding, penalty, subq = [], [], []
    for row in answers:
        qid = row.get("id", "")
        raw = str(row.get("visible_answer", ""))
        text = re.sub(r"\[[^\]]+\]", "", raw)
        text = "\n".join(
            line
            for line in text.splitlines()
            if not line.strip().startswith(("时效：", "渠道：", "口径："))
        )
        cites = row.get("citations") or []
        bodies = []
        for c in cites:
            for ch in chunks.get(str(c.get("doc_id")), []):
                if str(c.get("section", ""))[:20] in str(ch.get("section", "")):
                    bodies.append(str(ch.get("text", "")))
        blob = "\n".join(bodies)
        nums = re.findall(r"\d+(?:\.\d+)?", text)
        missing = [n for n in nums if n not in blob]
        if missing:
            binding.append((qid, missing[:4]))
        if (
            PENALTY.search(text)
            and row.get("reason") == "clause_fallback"
            and not PENALTY.search(blob)
        ):
            penalty.append(qid)
        question = str(qs.get(qid, {}).get("question", ""))
        parts = question.count("？") + len(re.findall(r"哪些|哪几种|怎么|如何", question))
        if parts >= 2 and not CONCLUSION.search(text):
            subq.append(qid)
    print(
        f"answers={len(answers)} section_binding={len(binding)} penalty={len(penalty)} subquestion={len(subq)}"
    )
    for qid, miss in binding:
        print("BIND", qid, miss)
    for qid in penalty:
        print("PEN", qid)
    for qid in subq:
        print("SUBQ", qid)
    return 1 if (binding or penalty or subq) else 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:4]))
