"""Standard RAG answer arm: structured JSON, citation validation and abstention.

The arm receives a bounded :class:`~scs_fkb.answer_v3.evidence.EvidencePack`,
asks the model for a structured answer, then enforces the same citation,
number and support checks as the older LLM arm.  It is the product default; the
clause-dump arm stays for the Track A instrument.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from ..llm import LLMClient, LLMError
from ..models import Answer
from ..rag import LLMCache, _citations_from_text
from .evidence import EvidencePack
from .llm_answer import (
    _cached_json,
    _number_problems,
    _resolve_citations,
    _sentence_problems,
    _verify,
)

MAX_ANSWER_CHARS = 4000
ANSWERABILITY = frozenset({"answerable", "partial", "refuse", "clarify"})
GAP_SENTENCE = (
    "证据不足",
    "未收录",
    "未规定",
    "无法从已登记语料",
    "缺口",
)

STANDARD_SYSTEM = (
    "你是南海近海渔业知识库作答器。只能使用证据清单，不得使用外部知识。"
    '只输出 JSON：{"answerability":"answerable|partial|refuse|clarify",'
    '"conclusion":"一句话结论","steps":["逐项回答"],"citations":["[DOC_ID §章节]"],'
    '"soft_gap":[],"missing_slots":[]}。'
    "先把问题拆成若干子问题，steps 每项回答一个子问题，不得遗漏；"
    "每个事实句必须带与证据标签完全一致的引用。"
    "conclusion 必须逐一回答问题的每个子问题，不得只答一部分；"
    "数字、金额、条款号、期限必须逐字从证据复制，不得改写、合并或四舍五入；"
    "来源层级必须与证据一致，国家规定不得写成省级，省级不得写成国家；"
    "不得根据印象补写“以上为省级规定”等层级判断。"
    "涉及罚则时必须写明证据中的罚款数额或幅度，原文有则摘出，不得省略。"
    "证据只覆盖部分子问题时必须用 answerability=partial，并在 soft_gap 说明未覆盖部分；"
    "只有证据清单与问题完全无关时才用 refuse，不要因为缺少细节直接拒绝回答。"
)
PROMPT_VERSION = "standard-" + hashlib.sha256(STANDARD_SYSTEM.encode()).hexdigest()[:8] + "-5"

REPAIR_SYSTEM = (
    "你在修复一份带引用的渔业答复。下面列出未被证据支持的数字或缺少引用的句子。\n"
    "只做两件事：删掉证据不支持的句子/数字，或改成证据原值；给缺引用的句子补上正确的"
    " [DOC_ID §章节] 或 [DOC_ID p.页码]。不得引入新事实。\n"
    '只输出 JSON：{"conclusion":"修复后的完整答复文本"}'
)
REPAIR_VERSION = "standard-repair-" + hashlib.sha256(REPAIR_SYSTEM.encode()).hexdigest()[:8] + "-5"


@dataclass(frozen=True)
class StandardResult:
    answer: Answer
    pack: EvidencePack
    confidence: float = 0.0
    judge_supported: bool | None = None
    judge_reason: str = ""
    answerability: str = "answerable"
    conclusion: str = ""
    conditions: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    cached: bool = False
    cache_type: str = ""
    contract_fields: dict[str, Any] = field(default_factory=dict)


def _key(kind: str, question: str, context: str, model: str) -> str:
    digest = hashlib.sha256(f"{kind}\n{question}\n{context}\n{model}".encode()).hexdigest()
    return f"standard-{digest[:24]}.json"


def _as_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _body(value: dict[str, Any]) -> str:
    lines: list[str] = []
    conclusion = str(value.get("conclusion") or "").strip()
    citations = _as_list(value.get("citations"))
    if conclusion and citations and "[" not in conclusion:
        conclusion = conclusion.rstrip("。") + " " + " ".join(citations)
    if conclusion:
        lines.append(conclusion)
    applicability = str(value.get("applicability") or "").strip()
    if applicability:
        lines.append(f"适用：{applicability}")
    documents = _as_list(value.get("documents"))
    if documents:
        lines.append("材料：" + "；".join(documents))
    deadline = str(value.get("deadline") or "").strip()
    if deadline:
        lines.append(f"时限：{deadline}")
    basis = _as_list(value.get("basis"))
    if basis:
        lines.append("依据：" + "；".join(basis))
    caveat = str(value.get("caveat") or "").strip()
    if caveat:
        lines.append(f"注意：{caveat}")
    soft_gap = _as_list(value.get("soft_gap"))
    if soft_gap:
        lines.append("缺口：" + "；".join(soft_gap))
    text = "\n".join(lines).strip()
    return text[:MAX_ANSWER_CHARS]


def _prune(text: str, by_label: dict[str, Any]) -> str:
    """Drop uncited factual sentences; keep gap declarations."""
    from .llm_answer import _sentences

    kept: list[str] = []
    for sentence in _sentences(text):
        if len(sentence) < 8:
            continue
        if "[" in sentence and "]" in sentence:
            kept.append(sentence)
            continue
        if any(marker in sentence for marker in GAP_SENTENCE):
            kept.append(sentence)
    return "\n".join(kept).strip()


def _repair(
    question: str,
    text: str,
    problems: list[str],
    client: LLMClient,
    cache: LLMCache | None,
) -> str:
    messages = [
        {"role": "system", "content": REPAIR_SYSTEM},
        {
            "role": "user",
            "content": (
                f"问题：\n{question}\n\n待修复答案：\n{text}\n\n"
                f"问题清单：{'；'.join(problems[:6])}\n\n按 JSON 输出。"
            ),
        },
    ]
    value = _cached_json(
        cache,
        _key(REPAIR_VERSION, question, text, client.config.model),
        client,
        messages,
        max_tokens=1600,
    )
    return str(value.get("conclusion") or value.get("answer") or "").strip()


def _selfcheck() -> bool:
    return os.environ.get("SCS_FKB_STANDARD_SELFCHECK", "on").strip().lower() not in {
        "off",
        "0",
        "false",
        "no",
    }


def _contract_fields(
    result: dict[str, Any],
    pack: EvidencePack,
    *,
    answerability: str,
    conclusion: str,
    missing: list[str],
) -> dict[str, Any]:
    soft_gap = _as_list(result.get("soft_gap"))
    gap = missing or soft_gap
    declared = pack.as_of or date.today().isoformat()
    return {
        "answerability": "partial" if answerability == "partial" or gap else "answerable",
        "conclusion": conclusion,
        "conditions": [str(item) for item in _as_list(result.get("applicability"))],
        "gap": gap,
        "slots": [],
        "as_of": {"declared": declared, "basis": "引用来源时效", "versions": []},
        "numbers": [],
        "channel": [],
    }


def answer_with_standard(
    question: str,
    pack: EvidencePack,
    client: LLMClient,
    cache: LLMCache | None = None,
) -> StandardResult:
    """Produce a cited structured answer from a bounded evidence pack."""
    if not pack.items:
        return StandardResult(
            answer=Answer(
                text="证据不足：未检索到可引用的已登记条款，无法支持回答。",
                abstained=True,
                reason="no_evidence",
            ),
            pack=pack,
            answerability="refuse",
            contract_fields={"answerability": "abstain", "conclusion": "", "gap": ["无可用证据"]},
        )
    messages = [
        {"role": "system", "content": STANDARD_SYSTEM},
        {
            "role": "user",
            "content": (
                f"问题（请回答所有子问题）：\n{question}\n\n"
                f"证据清单：\n{pack.text}\n\n按 JSON 输出。"
            ),
        },
    ]
    try:
        value = _cached_json(
            cache,
            _key(PROMPT_VERSION, question, pack.text, client.config.model),
            client,
            messages,
            max_tokens=2400,
        )
    except LLMError:
        # One compact retry: the remote model occasionally returns an empty
        # completion for the full schema prompt. The retry is only attempted on
        # failure, so successful calls are unchanged.
        retry_messages = [
            {
                "role": "system",
                "content": (
                    '只输出 JSON：{"answerability":"answerable|partial|refuse",'
                    '"conclusion":"一句话结论","citations":["…"]}。'
                ),
            },
            {
                "role": "user",
                "content": f"问题：{question}\n证据：\n{pack.text}\n按 JSON 输出。",
            },
        ]
        try:
            value = _cached_json(
                cache,
                _key(f"{PROMPT_VERSION}-retry", question, pack.text, client.config.model),
                client,
                retry_messages,
                max_tokens=800,
            )
        except LLMError:
            return StandardResult(
                answer=Answer(
                    text="证据不足：作答器不可用，已按缺口处理。",
                    abstained=True,
                    reason="standard_unavailable",
                ),
                pack=pack,
                answerability="refuse",
                contract_fields={
                    "answerability": "abstain",
                    "conclusion": "",
                    "gap": ["作答器不可用"],
                },
            )

    answerability = str(value.get("answerability") or "answerable").strip().lower()
    if answerability not in ANSWERABILITY:
        answerability = "answerable"
    missing = _as_list(value.get("missing_slots"))
    conclusion = str(value.get("conclusion") or "").strip()
    if answerability == "refuse":
        text = "证据不足：已登记语料未覆盖该问题。"
        if missing:
            text += "缺口：" + "；".join(missing)
        return StandardResult(
            answer=Answer(text=text, abstained=True, reason="standard_refuse"),
            pack=pack,
            answerability="refuse",
            missing=tuple(missing),
            contract_fields={
                "answerability": "abstain",
                "conclusion": "",
                "gap": missing or ["语料未覆盖"],
            },
        )
    if answerability == "clarify":
        text = "请补充关键信息后再回答："
        text += "；".join(missing) if missing else "地区、年份、船型或作业类型"
        return StandardResult(
            answer=Answer(text=text, abstained=True, reason="clarify"),
            pack=pack,
            answerability="clarify",
            missing=tuple(missing),
            contract_fields={
                "answerability": "abstain",
                "conclusion": "",
                "gap": missing or ["缺少关键槽位"],
            },
        )

    text = _body(value)
    if not text:
        return StandardResult(
            answer=Answer(
                text="证据不足：作答器未给出可用的结论。",
                abstained=True,
                reason="standard_empty",
            ),
            pack=pack,
            answerability="refuse",
            contract_fields={
                "answerability": "abstain",
                "conclusion": "",
                "gap": ["作答器未给出结论"],
            },
        )

    by_label = pack.by_label
    text = _prune(text, by_label)
    if not text or "[" not in text.splitlines()[0]:
        # The model sometimes omits inline citations from the conclusion while
        # still returning cited steps or a citations list. Recover those before
        # refusing, and fall back to an extractive evidence quote so a grounded
        # answer is never turned into an empty refusal.
        # First retry with a compact schema: this usually restores an inline
        # citation without changing the evidence.
        retry_messages = [
            {
                "role": "user",
                "content": (
                    f"问题：{question}\n证据：\n{pack.text}\n"
                    '只输出 JSON：{"answerability":"answerable|partial|refuse",'
                    '"conclusion":"逐句带 [DOC_ID §章节] 引用的回答",'
                    '"citations":["[DOC_ID §章节]"]}。只使用证据。'
                ),
            }
        ]
        try:
            compact = _cached_json(
                cache,
                _key(f"{PROMPT_VERSION}-ungrounded", question, pack.text, client.config.model),
                client,
                retry_messages,
                max_tokens=900,
            )
            compact_text = _prune(_body(compact), by_label)
            if compact_text and "[" in compact_text.splitlines()[0]:
                text = compact_text
        except LLMError:
            pass
        if not text or "[" not in text.splitlines()[0]:
            alt = "；".join(_as_list(value.get("steps")))
            if alt and "[" in alt:
                text = _prune(alt, by_label)
            # No extractive-quote fallback: a bare quote fragment reads like an
            # answer but usually does not answer the question. Prefer an honest
            # refusal over a misleading fragment.
    if not text or "[" not in text.splitlines()[0]:
        return StandardResult(
            answer=Answer(
                text="证据不足：结论没有可解析的引用，已拒绝给出结论。",
                abstained=True,
                reason="standard_ungrounded",
            ),
            pack=pack,
            answerability="refuse",
            contract_fields={
                "answerability": "abstain",
                "conclusion": "",
                "gap": ["结论没有引用"],
            },
        )
    problems = _sentence_problems(text, by_label, allow_gap=True) + _number_problems(text, by_label)
    if problems:
        try:
            repaired = _repair(question, text, problems, client, cache)
        except LLMError:
            repaired = ""
        if repaired:
            text = repaired
        problems = _sentence_problems(text, by_label, allow_gap=True) + _number_problems(
            text, by_label
        )
        if problems:
            pruned = _prune(text, by_label)
            if not pruned or not any("[" in sentence for sentence in pruned.splitlines()):
                return StandardResult(
                    answer=Answer(
                        text="证据不足：答案引用无法验证，已拒绝给出结论。",
                        abstained=True,
                        reason="standard_ungrounded",
                    ),
                    pack=pack,
                    answerability="refuse",
                    contract_fields={
                        "answerability": "abstain",
                        "conclusion": "",
                        "gap": ["答案引用无法验证"],
                    },
                )
            text = pruned

    valid, invalid = _resolve_citations(text, pack.hits, tolerant=True)
    if not valid:
        return StandardResult(
            answer=Answer(
                text="证据不足：答案引用无法解析，已拒绝给出结论。",
                abstained=True,
                reason="standard_citation_invalid",
            ),
            pack=pack,
            answerability="refuse",
            contract_fields={
                "answerability": "abstain",
                "conclusion": "",
                "gap": ["引用无法解析：" + ",".join(invalid[:2])],
            },
        )
    citations = _citations_from_text(text, pack.hits, tolerant=True)
    if not citations:
        return StandardResult(
            answer=Answer(
                text="证据不足：答案没有可解析的引用，已拒绝给出结论。",
                abstained=True,
                reason="standard_no_citation",
            ),
            pack=pack,
            answerability="refuse",
            contract_fields={"answerability": "abstain", "conclusion": "", "gap": ["答案没有引用"]},
        )

    judge_supported: bool | None = None
    judge_reason = ""
    if _selfcheck():
        judge_supported, judge_reason = _verify(question, text, by_label, client, cache)
        if not judge_supported:
            return StandardResult(
                answer=Answer(
                    text="证据不足：自检判定结论未被引用证据支持，已按缺口处理。",
                    abstained=True,
                    reason="standard_unsupported",
                ),
                pack=pack,
                answerability="refuse",
                judge_supported=False,
                judge_reason=judge_reason,
                contract_fields={
                    "answerability": "abstain",
                    "conclusion": "",
                    "gap": ["自检未通过"],
                },
            )

    gap = missing or _as_list(value.get("soft_gap"))
    confidence = 0.9 if answerability == "answerable" and not gap else 0.75
    if judge_supported is None:
        confidence -= 0.05
    if pack.truncated:
        confidence -= 0.05
    return StandardResult(
        answer=Answer(text=text, citations=citations, abstained=False, reason="standard_compose"),
        pack=pack,
        confidence=round(max(0.0, min(1.0, confidence)), 2),
        judge_supported=judge_supported,
        judge_reason=judge_reason,
        answerability=answerability,
        conclusion=conclusion,
        conditions=tuple(_as_list(value.get("applicability"))),
        missing=tuple(gap),
        contract_fields=_contract_fields(
            value,
            pack,
            answerability=answerability,
            conclusion=conclusion,
            missing=list(missing),
        ),
    )


__all__ = [
    "ANSWERABILITY",
    "PROMPT_VERSION",
    "StandardResult",
    "answer_with_standard",
]
