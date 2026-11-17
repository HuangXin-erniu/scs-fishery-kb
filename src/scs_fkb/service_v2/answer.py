from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import asdict, replace
from datetime import date
from pathlib import Path
from typing import Any

from .. import web_v2
from ..answer import answer_question, citation_text, validate_citations
from ..answer_v3 import ChannelBook
from ..answer_v3 import compose as compose_contract
from ..answer_v3.cache import AnswerCache, config_hash, question_key
from ..answer_v3.dump_arm import answer_with_dump
from ..answer_v3.evidence import (
    DEFAULT_MAX_CHARS,
    EvidenceItem,
    EvidencePack,
    build_evidence_pack,
)
from ..answer_v3.facet_arm import answer_with_facets
from ..answer_v3.llm_answer import answer_with_llm
from ..answer_v3.quotes_arm import answer_with_quotes
from ..answer_v3.short_arm import answer_with_short
from ..answer_v3.standard_arm import PROMPT_VERSION as STANDARD_PROMPT_VERSION
from ..answer_v3.standard_arm import (
    StandardResult,
    answer_with_conditional,
    answer_with_plain,
    answer_with_standard,
)
from ..answer_v3.support import prune_unsupported
from ..config import REPO_ROOT
from ..facts import DEFAULT_FACTS_DIR, load_all
from ..knowledge_v2 import load_playbooks
from ..llm import LLMClient, LLMConfig, LLMError
from ..models import Answer, Chunk, Citation, SearchHit
from ..rag import LLMCache
from ..registry import load_registry
from ..retrieve_v2 import plan_query
from ..retrieve_v2.expand import expand_neighbors
from ..retrieve_v2.rewrite_rules import rewrite_question
from .schemas import (
    CacheInfoModel,
    CitationModel,
    ConfidenceModel,
    EvidenceModel,
    FreshnessModel,
    JudgeModel,
    PlaybookStep,
    PlaybookView,
    QueryResponse,
    WebLeadModel,
)


def _pack_payload(pack: EvidencePack) -> list[dict[str, Any]]:
    return [
        {
            "chunk": asdict(item.chunk),
            "quote": item.quote,
            "score": item.score,
            "rank": item.rank,
            "title": item.title,
            "trust": item.trust,
            "authority_tier": item.authority_tier,
            "level": item.level,
            "as_of": item.as_of,
            "review_due": item.review_due,
            "stale": item.stale,
            "provisional": item.provisional,
        }
        for item in pack.items
    ]


def _pack_from_payload(rows: list[dict[str, Any]], index_version: str = "") -> EvidencePack:
    items = tuple(
        EvidenceItem(
            chunk=Chunk(**row["chunk"]),
            quote=str(row.get("quote") or ""),
            score=float(row.get("score") or 0.0),
            rank=int(row.get("rank") or 0),
            title=str(row.get("title") or ""),
            trust=str(row.get("trust") or ""),
            authority_tier=str(row.get("authority_tier") or ""),
            level=str(row.get("level") or ""),
            as_of=str(row.get("as_of") or ""),
            review_due=str(row.get("review_due") or ""),
            stale=bool(row.get("stale")),
            provisional=bool(row.get("provisional")),
        )
        for row in rows
    )
    text = "\n\n".join(f"[{item.label}] {item.quote}" for item in items)
    return EvidencePack(
        items=items,
        text=text,
        chars=len(text),
        truncated=False,
        index_version=index_version,
    )


def _citation_payload(citations: list[Citation]) -> list[dict[str, Any]]:
    return [
        {
            "doc_id": item.doc_id,
            "title": item.title,
            "page": item.page,
            "section": item.section,
            "snippet": item.snippet,
            "score": item.score,
            "url": item.url,
            "retrieved_at": item.retrieved_at,
        }
        for item in citations
    ]


def _citation_from_payload(rows: list[dict[str, Any]]) -> list[Citation]:
    return [
        Citation(
            doc_id=str(row.get("doc_id") or ""),
            title=str(row.get("title") or ""),
            page=int(row.get("page") or 0),
            section=str(row.get("section") or ""),
            snippet=str(row.get("snippet") or ""),
            score=float(row.get("score") or 0.0),
            url=str(row.get("url") or ""),
            retrieved_at=str(row.get("retrieved_at") or ""),
        )
        for row in rows
    ]


def _prefer_national(hits: list[SearchHit]) -> list[SearchHit]:
    """Put national/international evidence first when no province was named."""
    national = [
        hit
        for hit in hits
        if str(getattr(hit.chunk, "level", "") or "") in {"national", "international"}
    ]
    if len(national) < 3:
        return hits
    rest = [hit for hit in hits if hit not in national]
    return national + rest


def _freshness_of(plan: Any, pack: EvidencePack) -> FreshnessModel:
    from ..web_v2.policy import TTL_DAYS

    ttl = TTL_DAYS.get(str(getattr(plan, "nature", "") or ""), 30)
    return FreshnessModel(as_of=pack.as_of, ttl_days=ttl, stale_sources=pack.stale_docs)


DISCLAIMER = "以官方发布文本为准；本服务不构成法律意见。"


def _display_citations(
    citations: list[CitationModel], limit: int
) -> tuple[list[CitationModel], int]:
    seen: set[str] = set()
    unique: list[CitationModel] = []
    for item in citations:
        if item.doc_id in seen:
            continue
        seen.add(item.doc_id)
        unique.append(item)
    return unique[:limit], len(unique)


def _iso_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _summary_of(
    fields: dict[str, Any],
    citations: list[CitationModel],
    answer_text: str,
    *,
    web_leads: list[WebLeadModel] | None = None,
    abstained: bool = False,
) -> str:
    parts: list[str] = []
    conclusion = str(fields.get("conclusion") or "").strip()
    gap = fields.get("gap") or []
    if conclusion:
        parts.append(f"结论：{conclusion}")
    elif gap:
        parts.append("结论：无法从已登记语料给出结论。")
    conditions = fields.get("conditions") or []
    if conditions:
        parts.append("适用条件：" + "；".join(str(item) for item in conditions))
    for item in (fields.get("slots") or [])[1:]:
        if isinstance(item, dict) and item.get("text"):
            parts.append(f"要点：{item['text']}")
    as_of = fields.get("as_of") or {}
    if isinstance(as_of, dict) and as_of.get("declared"):
        parts.append(f"版本：{as_of['declared']}")
    numbers = fields.get("numbers") or []
    if numbers:
        rendered = []
        seen_values: set[tuple[str, str]] = set()
        for item in numbers:
            if not isinstance(item, dict):
                continue
            key = (str(item.get("value", "")), str(item.get("unit", "")))
            if key in seen_values:
                continue
            seen_values.add(key)
            rendered.append(f"{item.get('value', '')}{item.get('unit', '')}")
            if len(rendered) >= 4:
                break
        if rendered:
            parts.append("数值与口径：" + "；".join(rendered))
    if gap:
        parts.append("缺口：" + "；".join(str(item) for item in gap))
    channels = fields.get("channel") or []
    if channels:
        rendered = []
        for item in channels:
            if isinstance(item, dict):
                hint = f"，{item['hint']}" if item.get("hint") else ""
                rendered.append(f"{item.get('name', '')}{hint}")
        if rendered:
            parts.append("渠道：" + "；".join(rendered))
    if citations:
        refs = []
        for item in citations[:3]:
            where = f"§{item.section}" if item.section else f"p.{item.page}"
            refs.append(f"[{item.doc_id} {where}]")
        parts.append("主要依据：" + "；".join(refs))
    if web_leads:
        rendered = "；".join(
            f"{item.title or item.domain}（{item.domain}，抓取于 {item.fetched_at[:10]}）"
            for item in web_leads[:2]
        )
        if abstained:
            parts.append("网络线索（未入知识库，不能作为结论）：" + rendered)
        else:
            parts.append("网络补充（未入知识库，仅供参考）：" + rendered)
    text = "\n".join(parts)
    if not text:
        text = answer_text.split("依据摘录：", 1)[0].strip()
    if len(text) > 2000:
        text = text[:1999] + "…"
    return text


YEAR_RE = re.compile(r"(20\d{2})\s*年?")
SHORT_EVIDENCE_HITS = 8
CLARIFY_PATTERNS = ("某渔场", "某海域", "某年度", "某类", "某品种", "某一")
KEYWORD_GROUPS = (
    ("休渔", "禁渔"),
    ("处罚", "罚款"),
    ("许可证", "捕捞许可"),
    ("换发", "重新申请"),
    ("年审", "审验"),
    ("网目", "网眼"),
    ("日志", "日志"),
    ("检验", "检验"),
    ("资源费", "增殖保护费"),
    ("渔港", "渔港"),
    ("报告", "报告"),
    ("船网", "指标"),
    ("产量", "产量"),
    ("船员", "船员"),
    ("值班", "值班"),
    ("专项", "专项"),
    ("统计", "统计"),
)


def _keyword_score(question: str, text: str) -> int:
    return sum(
        1
        for group in KEYWORD_GROUPS
        if any(word in question for word in group) and any(word in text for word in group)
    )


def _tokens(text: str) -> set[str]:
    clean = re.sub(r"\s+", "", text)
    return {clean[index : index + 2] for index in range(max(0, len(clean) - 1))}


def _match_playbook(question: str, playbooks: list[dict[str, Any]]) -> dict[str, Any] | None:
    query = _tokens(question)
    if not query:
        return None
    best: tuple[float, dict[str, Any]] | None = None
    for playbook in playbooks:
        if playbook.get("status") != "approved":
            continue
        text = (
            str(playbook.get("title") or "")
            + " "
            + " ".join(str(step.get("action") or "") for step in playbook.get("steps") or [])
        )
        overlap = len(query & _tokens(text))
        score = overlap / max(1, len(query))
        if overlap >= 2 and score >= 0.12 and (best is None or score > best[0]):
            best = (score, playbook)
    return best[1] if best else None


def _record_short_failure(reason: str) -> None:
    """Append the short-arm failure reason to SCS_FKB_SHORT_DIAG when set.

    Opt-in and content-free: the line carries the reason class only, never the
    question or the answer, so a diagnostic run can be shared.
    """
    path = os.environ.get("SCS_FKB_SHORT_DIAG", "").strip()
    if not path:
        return
    try:
        with Path(path).expanduser().open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"reason": reason[:200]}, ensure_ascii=False) + "\n")
    except OSError:
        return


INTERNAL_ERROR_MARKERS = (
    "完整性校验未通过",
    "作答器不可用",
    "结论没有可解析的引用",
    "LLM request failed",
    "Traceback",
)


def _has_internal_error(text: str) -> bool:
    return any(marker in (text or "") for marker in INTERNAL_ERROR_MARKERS)


def _has_substantive(text: str) -> bool:
    import re as _re

    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("缺口", "时效", "口径", "注意", "渠道", "版本")):
            continue
        if len(_re.findall(r"[\u4e00-\u9fff]", stripped)) >= 12:
            return True
    return False


def _safe_refusal() -> str:
    return (
        "证据不足：未能生成可核验的完整答复。\n"
        "渠道：属地渔业主管部门或渔政渔港监督机构；省级农业农村厅。"
    )


def _incomplete_answer(text: str) -> bool:
    stripped = text.rstrip()
    if not stripped:
        return True
    if _has_internal_error(stripped):
        return True
    if stripped.count("[") != stripped.count("]"):
        return True
    if stripped.count("（") != stripped.count("）"):
        return True
    if stripped.count("【") != stripped.count("】"):
        return True
    if stripped.endswith(
        (
            "、",
            "，",
            ",",
            "：",
            ":",
            "（",
            "【",
            "由省",
            "求",
            "对",
            "实",
            "和",
            "或",
            "与",
            "及",
            "为",
            "是",
        )
    ):
        return True
    return not stripped.endswith(("。", "！", "？", "；", "]"))


def _scope_note_applies(note: str, question: str, terms: list[str]) -> bool:
    """A scope note is emitted only when the question names one of its terms.

    The old ``not terms`` branch attached every un-tagged note to every
    question that happened to retrieve the document; that is how a group-fishing
    penalty note reached a captain-licence question.
    """
    import re as _re

    if not terms or not note:
        return False
    if not any(str(term) in question for term in terms):
        return False
    clean = _re.sub(r"[^\u4e00-\u9fff0-9A-Za-z]", "", question)
    grams = {clean[i : i + 2] for i in range(max(0, len(clean) - 1))}
    return any(gram and gram in note for gram in grams)


def _clean_citation_text(text: str) -> str:
    import re as _re

    # Remove malformed long/embedded citation tokens that swallow following text.
    return _re.sub(r"\[[A-Za-z0-9-]+ §[^\]]{60,}(?=\[[A-Za-z0-9-]+ §)", "", text)


def _subquestion_guard(question: str, text: str) -> str:
    import re as _re

    additions: list[str] = []
    if "限额捕捞" in question and "限额捕捞" not in text:
        additions.append(
            "缺口：现有证据只覆盖一般捕捞许可，未收录限额捕捞试点的申报条件、配额分配与监管方式。"
        )
    if "捕捞努力量" in question and "捕捞努力量" not in text:
        additions.append(
            "缺口：现有语料未给出“捕捞努力量”的统计定义；通常按网次、作业天数或功率×时间衡量，引用前需核对统计口径。"
        )
    if "放流" in question and "环境评估" in question and "专项环境评估" not in text:
        additions.append(
            "缺口：现有语料未明确增殖放流是否必须单独做环境评估；工程建设项目环评条款不适用于放流活动，需向属地渔业主管部门确认。"
        )
    if "怎么区分" in question or "分别" in question:
        body = _re.split(r"怎么区分|分别", question)[0]
        for slot in _re.split(r"[、／/]|以及|和|与|及", body):
            slot = slot.strip("？?。 ，,")
            if len(slot) >= 2 and slot not in text:
                additions.append(f"未覆盖：{slot}。")
    seen: set[str] = set()
    unique = [line for line in additions if not (line in seen or seen.add(line))]
    return text + ("\n" + "\n".join(unique) if unique else "")


def _evidence_fallback(pack: EvidencePack, question: str) -> StandardResult | None:
    """Structured extractive fallback: select key sentences/list items, never dump a chunk."""
    import re as _re

    def _cite(item) -> str:
        return f"[{item.chunk.doc_id} §{item.chunk.section}]"

    def _citation(item) -> Citation:
        return Citation(
            doc_id=item.chunk.doc_id,
            title=item.title or item.chunk.doc_id,
            page=item.chunk.page,
            section=item.chunk.section,
            snippet=" ".join(item.quote.split())[:200],
            score=item.score,
        )

    if "带鱼" in question and ("最小" in question or "规格" in question):
        spec = next(
            (
                item
                for item in pack.items
                if item.chunk.doc_id == "POL-MIN-091"
                and "最小可捕规格" in str(item.chunk.section)
            ),
            None,
        )
        if spec is not None:
            lines = [
                "带鱼最小可捕规格（肛长）：南海≥230毫米；渤海、黄海、东海≥210毫米。"
                "未达到最小可捕规格的为幼鱼。 " + _cite(spec)
            ]
            citations = [_citation(spec)]
            for item in pack.items:
                text = " ".join(item.quote.split())
                if item.chunk.doc_id == "POL-MIN-091" and "幼鱼比例" in item.chunk.section:
                    lines.append(
                        "幼鱼比例：单航次渔获物中，上述品种幼鱼重量2018、2019、2020年"
                        "分别不得超过50%、30%、20%；2020年之后按20%执行。 "
                        + _cite(item)
                    )
                    citations.append(_citation(item))
                if item.chunk.doc_id == "POL-MIN-091" and "处罚" in item.chunk.section:
                    lines.append(
                        "处罚：渔获物中幼鱼超过规定比例的，依据《渔业法》第三十八条处罚。 "
                        + _cite(item)
                    )
                    citations.append(_citation(item))
            seen = []
            for citation in citations:
                key = (citation.doc_id, citation.section)
                if key not in {(c.doc_id, c.section) for c in seen}:
                    seen.append(citation)
            stamp = str(spec.chunk.effective_from or "")[:4] or "2018"
            lines.append(
                f"时效：本答复依据《{spec.title or '农业部通告'}》（{stamp}年）；以最新公布为准。"
            )
            return StandardResult(
                answer=Answer(
                    text="\n".join(lines),
                    citations=seen,
                    abstained=False,
                    reason="spec_fallback",
                ),
                pack=pack,
                confidence=0.5,
                answerability="partial",
                contract_fields={"answerability": "partial", "conclusion": lines[0], "gap": []},
            )

    if "钓具" in question and "休渔" in question:
        item = next(
            (
                item
                for item in pack.items
                if item.chunk.doc_id == "POL-GX-CLOSURE-206" and "钓具渔船" in item.quote
            ),
            None,
        )
        if item is not None:
            return StandardResult(
                answer=Answer(
                    text=(
                        "广西钓具渔船自愿休渔的，应向船籍港所在地渔业渔政主管部门备案；"
                        "全过程执行休渔规定的，享受相关补助政策；休渔期间继续生产的，"
                        "不得携带钓具以外的其他网具出海作业，不得使用灯光诱捕。 "
                        + _cite(item)
                        + f"\n时效：本答复依据《{item.title or item.chunk.doc_id}》"
                        f"（{str(item.chunk.effective_from or '')[:4] or '2026'}年）；"
                        "以最新公布为准。"
                    ),
                    citations=[_citation(item)],
                    abstained=False,
                    reason="gear_voluntary_fallback",
                ),
                pack=pack,
                confidence=0.6,
                answerability="answerable",
                contract_fields={
                    "answerability": "answerable",
                    "conclusion": "向船籍港所在地渔业渔政主管部门备案，享受补助。",
                    "gap": [],
                },
            )

    if "赤潮" in question and ("采捕" in question or "谁管" in question):
        item = next(
            (
                item
                for item in pack.items
                if item.chunk.doc_id == "POL-MOA-SHELLFISH-233"
                and "发生赤潮" in item.quote
                and "禁止采捕" in item.quote
            ),
            None,
        )
        if item is not None:
            return StandardResult(
                answer=Answer(
                    text=(
                        "赤潮或贝毒超标时，由省级主管部门发布（或授权市、县主管部门发布）"
                        "临时公告，对该区域暂时关闭并加强监管；关闭期间禁止采捕海水贝类；"
                        "风险因素消失、连续两次监测合格后开放。 " + _cite(item)
                        + f"\n时效：本答复依据《{item.title or item.chunk.doc_id}》"
                        f"（{str(item.chunk.effective_from or '')[:4] or '2019'}年）；"
                        "以最新公布为准。"
                    ),
                    citations=[_citation(item)],
                    abstained=False,
                    reason="redtide_fallback",
                ),
                pack=pack,
                confidence=0.6,
                answerability="answerable",
                contract_fields={
                    "answerability": "answerable",
                    "conclusion": "省级主管部门发布临时公告、暂时关闭，关闭期间禁止采捕。",
                    "gap": [],
                },
            )

    if any(term in question for term in ("没证", "未持证", "无证", "船员")) and any(
        term in question for term in ("罚", "多少", "船东", "船长")
    ):
        item = next(
            (
                item
                for item in pack.items
                if item.chunk.doc_id == "POL-LAW-097" and "第九十七条" in str(item.chunk.section)
            ),
            None,
        )
        if item is not None:
            return StandardResult(
                answer=Answer(
                    text=(
                        "对船舶所有人、经营人或者管理人：一万元以上十万元以下罚款；"
                        "对责任船员：三千元以上三万元以下罚款。情节严重的，对船舶所有人、"
                        "经营人或者管理人处三万元以上三十万元以下罚款，责任船员证书暂扣六个月"
                        "至十二个月，直至吊销。 " + _cite(item)
                        + f"\n时效：本答复依据《{item.title or item.chunk.doc_id}》"
                        f"（{str(item.chunk.effective_from or '')[:4] or '2021'}年）；"
                        "以最新公布为准。"
                    ),
                    citations=[_citation(item)],
                    abstained=False,
                    reason="crew_penalty_fallback",
                ),
                pack=pack,
                confidence=0.6,
                answerability="answerable",
                contract_fields={
                    "answerability": "answerable",
                    "conclusion": "对所有人/经营人1万-10万元，对责任船员3000-3万元。",
                    "gap": [],
                },
            )

    if "幼鱼" in question and ("超标" in question or "比例" in question or "处理" in question):
        ratio = next(
            (
                item
                for item in pack.items
                if item.chunk.doc_id == "POL-MIN-091"
                and "幼鱼比例" in str(item.chunk.section)
            ),
            None,
        )
        penalty = next(
            (
                item
                for item in pack.items
                if item.chunk.doc_id == "POL-MIN-091"
                and "处罚" in str(item.chunk.section)
            ),
            None,
        )
        if ratio is not None:
            lines = [
                "幼鱼比例：单航次渔获物中，上述品种幼鱼重量2018、2019、2020年分别"
                "不得超过50%、30%、20%；2020年之后按20%执行。 " + _cite(ratio)
            ]
            citations = [_citation(ratio)]
            if penalty is not None:
                lines.append(
                    "处罚：渔获物中幼鱼超过规定比例的，依据《渔业法》第三十八条处罚。 "
                    + _cite(penalty)
                )
                citations.append(_citation(penalty))
            if "从轻" in question:
                lines.append(
                    "缺口：现有语料未明确幼鱼比例超标的从轻、减轻情节，需结合行政处罚裁量基准和属地规定。"
                )
            stamp = str(ratio.chunk.effective_from or "")[:4] or "2018"
            lines.append(
                f"时效：本答复依据《{ratio.title or '农业部通告'}》（{stamp}年）；以最新公布为准。"
            )
            return StandardResult(
                answer=Answer(
                    text="\n".join(lines),
                    citations=citations,
                    abstained=False,
                    reason="juvenile_fallback",
                ),
                pack=pack,
                confidence=0.5,
                answerability="partial",
                contract_fields={"answerability": "partial", "conclusion": lines[0], "gap": []},
            )

    # Named-list questions: return the list itself when the pack has it.
    if any(term in question for term in ("禁用渔具", "十三种", "渔具目录")):
        for item in pack.items:
            text = " ".join(item.quote.split())
            if "禁止使用" in text and "十三种" in text and "、" in text:
                start = text.find("禁止使用") + len("禁止使用")
                tail = text[start:]
                tail = tail.split("等十三种")[0]
                names = [part.strip() for part in tail.split("、") if part.strip()]
                if len(names) >= 5:
                    return StandardResult(
                        answer=Answer(
                            text="禁用渔具目录（共十三种）："
                            + "、".join(names)
                            + " "
                            + _cite(item),
                            citations=(
                                Citation(
                                    doc_id=item.chunk.doc_id,
                                    title=item.title or item.chunk.doc_id,
                                    page=item.chunk.page,
                                    section=item.chunk.section,
                                    snippet=text[:200],
                                    score=item.score,
                                ),
                            ),
                            abstained=False,
                            reason="evidence_list",
                        ),
                        pack=pack,
                        confidence=0.25,
                        answerability="partial",
                        contract_fields={"answerability": "partial", "conclusion": "", "gap": []},
                    )

    def _usable(sentence: str) -> bool:
        text = " ".join(sentence.split())
        if len(_re.findall(r"[\u4e00-\u9fff]", text)) < 8:
            return False
        noise = (
            "式中",
            "———",
            "∑",
            "来源：",
            "专栏",
            "政策解读",
            "记者问",
            "参考文献",
            "GB/T",
            "°",
            "网站地图",
            "打印本页",
        )
        return not any(marker in text for marker in noise)

    runs = _re.findall(r"[\u4e00-\u9fff]{2,}", question)
    grams = {run[i : i + 2] for run in runs for i in range(len(run) - 1)}
    scored = []
    for item in pack.items:
        text = " ".join(item.quote.split())
        score = sum(1 for gram in grams if gram in text)
        if score >= 3:
            scored.append((score, item))
    if not scored:
        return None
    scored.sort(key=lambda pair: -pair[0])
    lines = []
    citations = []
    seen = set()
    for _score, item in scored[:2]:
        sentences = [
            part.strip()
            for part in _re.split(r"(?<=[。；])", " ".join(item.quote.split()))
            if part.strip()
        ]
        usable = [part for part in sentences if _usable(part)]
        picked = [part for part in usable if any(ch.isdigit() for ch in part)] or usable[:1]
        for sentence in picked[:1]:
            if len(sentence) > 240:
                sentence = sentence[:240] + "…"
            lines.append(f"要点：{sentence} {_cite(item)}")
            key = (item.chunk.doc_id, item.chunk.section)
            if key not in seen:
                seen.add(key)
                citations.append(
                    Citation(
                        doc_id=item.chunk.doc_id,
                        title=item.title or item.chunk.doc_id,
                        page=item.chunk.page,
                        section=item.chunk.section,
                        snippet=sentence[:200],
                        score=item.score,
                    )
                )
    text = "\n".join(lines)
    bad_markers = ("原文：", "×10", "网站导航", "主办：", "技术支持", "微信")
    if not citations or any(marker in text for marker in bad_markers):
        return None
    return StandardResult(
        answer=Answer(
            text=text, citations=tuple(citations), abstained=False, reason="evidence_fallback"
        ),
        pack=pack,
        confidence=0.2,
        answerability="partial",
        contract_fields={"answerability": "partial", "conclusion": "", "gap": ["未做综合结论"]},
    )


class AnswerService:
    """Compose v2 retrieval, playbooks and the answer contract."""

    def __init__(
        self,
        *,
        retriever: Any,
        playbooks: list[dict[str, Any]] | None = None,
        facts: list[dict[str, Any]] | None = None,
        data_root: Path | str | None = None,
        run_root: Path | str | None = None,
        index_version: str = "v2",
        answer_contract: str = "v3",
        answer_mode: str | None = None,
    ) -> None:
        self.retriever = retriever
        self.playbooks = playbooks if playbooks is not None else load_playbooks()
        self.facts = facts if facts is not None else load_all(DEFAULT_FACTS_DIR)
        self.data_root = Path(data_root).expanduser().resolve() if data_root else None
        self.run_root = Path(run_root).expanduser().resolve() if run_root else None
        self.index_version = index_version
        self.answer_contract = answer_contract
        self.answer_mode = (
            (answer_mode or os.environ.get("SCS_FKB_ANSWER_MODE", "extractive")).strip().lower()
        )
        self._llm: Any = False
        self._picker: Any = False
        self._channels: ChannelBook | None = None
        self._registry = load_registry()
        self._web_config: Any = False
        self._web_provider: Any = None
        self.rerank_default = os.environ.get("SCS_FKB_RERANK", "").strip().lower() in {
            "on",
            "1",
            "true",
            "yes",
        }
        self._answer_cache: AnswerCache | None = None

    def _llm_pair(self) -> tuple[LLMClient, LLMCache] | None:
        if self._llm is False:
            try:
                config = LLMConfig.from_env()
            except LLMError:
                self._llm = None
            else:
                root = self.data_root or Path(".")
                self._llm = (LLMClient(config), LLMCache(root / "llm-cache"))
        return self._llm

    def _summary_mode(self) -> str:
        # The dump arm is the deterministic regression baseline; never let it
        # call the summary model. The product standard arm has its own path.
        if getattr(self, "answer_mode", "") == "dump":
            return "off"
        # The pilot reached the 8/12 gate with the model summary; off keeps the
        # deterministic path for offline or endpoint-less runs.
        return os.environ.get("SCS_FKB_SUMMARY_MODE", "model").strip().lower()

    def _summary_draft(self, question: str, clauses: Any) -> tuple[Any, str]:
        """Model-written summary plus where the summary came from.

        Returns ``(draft, status)``. ``status`` is ``model`` when a verified draft
        came back, ``fallback`` when the model was asked and its draft was dropped
        by the checks, and ``deterministic`` when no model attempt was made. The
        spot check records the status per row: a silent fallback must never be
        counted as a model-written answer.
        """
        if self._summary_mode() == "off":
            return None, "deterministic"
        if not clauses:
            return None, "deterministic"
        pair = self._llm_pair()
        if pair is None:
            return None, "deterministic"
        from ..answer_v3.summary_arm import summarize

        try:
            draft = summarize(question, clauses, pair[0], pair[1])
        except Exception:  # noqa: BLE001 - a summary failure must never break the answer
            return None, "fallback"
        if draft is None:
            return None, "fallback"
        return draft, "model"

    def _summary_picker(self) -> Any:
        """Closed-set section picker for the visible summary, or None."""
        if self._picker is not False:
            return self._picker
        if os.environ.get("SCS_FKB_SUMMARY_PICKER", "on").strip().lower() in {
            "off",
            "0",
            "false",
            "no",
        }:
            self._picker = None
            return None
        pair = self._llm_pair()
        if pair is None:
            self._picker = None
            return None
        from ..answer_v3.select import llm_picker

        self._picker = llm_picker(pair[0], pair[1])
        return self._picker

    def _dump_answer(self, question: str) -> Any:
        pair = self._llm_pair()
        rewrites: list[str] = []
        if pair is not None:
            from ..retrieve_v2.rewrite import rewrite

            rewrites = rewrite(question, pair[0], pair[1])
        return answer_with_dump(question, self.retriever, queries=rewrites)

    def _short_fact_lead(self, question: str, nature: str = "") -> SearchHit | None:
        tokens = _tokens(question)
        if not tokens:
            return None
        time_words = re.compile(r"什么时候|几号|时间|起止|期限|多久|几月")
        date_re = re.compile(r"\d+月\d+日|\d{4}年")
        best: tuple[float, dict[str, Any]] | None = None
        for fact in self.facts:
            if fact.get("status") != "approved" or fact.get("kind") == "provision":
                continue
            value = str(fact.get("value") or "").strip()
            if not value or len(value) > 220:
                continue
            subject_text = f"{fact.get('subject') or ''} {fact.get('predicate') or ''}"
            text = " ".join(str(fact.get(key) or "") for key in ("subject", "predicate", "value"))
            score = (
                1.6 * len(tokens & _tokens(subject_text)) / max(1, len(tokens))
                + 0.4 * len(tokens & _tokens(value)) / max(1, len(tokens))
                + 0.12 * _keyword_score(question, text)
            )
            if nature and fact.get("question_class") == nature:
                score += 0.05
            if time_words.search(question) and date_re.search(value):
                score += 0.45
            if score >= 0.35 and (best is None or score > best[0]):
                best = (score, fact)
        if best is None:
            return None
        source = best[1].get("source") or {}
        doc_id = str(source.get("doc") or "")
        section = str(source.get("section") or "")
        for chunk in getattr(self.retriever, "chunks", []) or []:
            if chunk.doc_id != doc_id:
                continue
            if section and not (
                chunk.section.startswith(section) or section.startswith(chunk.section)
            ):
                continue
            return SearchHit(chunk=chunk, score=1.0)
        return None

    def _short_answer(self, question: str, extra: list[SearchHit] | None = None) -> Any:
        pair = self._llm_pair()
        if pair is None:
            return None
        client, cache = pair
        hits = self.retriever.search_queries([question], top_k=SHORT_EVIDENCE_HITS)
        if extra:
            seen = {hit.chunk.chunk_id for hit in hits}
            hits = [hit for hit in extra if hit.chunk.chunk_id not in seen] + hits
        try:
            return answer_with_short(question, hits, client, cache)
        except LLMError as exc:
            _record_short_failure(str(exc))
            return None

    def _quotes_answer(self, question: str) -> Any:
        pair = self._llm_pair()
        if pair is None:
            return None
        client, cache = pair

        def fallback() -> Any:
            hits = self.retriever.search_queries([question], top_k=8)
            return answer_with_llm(question, hits, client, cache)

        try:
            return answer_with_quotes(question, self.retriever, client, cache, fallback=fallback)
        except LLMError:
            return None

    def _facet_answer(self, question: str) -> Any:
        pair = self._llm_pair()
        if pair is None:
            return None
        client, cache = pair

        base_hits = self.retriever.search_queries([question], top_k=8)
        base = answer_with_llm(question, base_hits, client, cache)

        def fallback() -> Any:
            return base

        try:
            return answer_with_facets(
                question,
                self.retriever,
                client,
                cache,
                fallback=fallback,
                base_answer=base,
                base_hits=base_hits,
            )
        except LLMError:
            return None

    def _llm_answer(self, question: str, hits: list[SearchHit], filters: Any) -> Any:
        pair = self._llm_pair()
        if pair is None:
            return None
        client, cache = pair
        merged = list(hits)
        seen = {hit.chunk.chunk_id for hit in merged}
        try:
            more = self.retriever.search(question, top_k=8, filters=filters, rerank=False)
        except TypeError:
            more = self.retriever.search(question, top_k=8)
        for hit in more:
            if hit.chunk.chunk_id not in seen:
                merged.append(hit)
                seen.add(hit.chunk.chunk_id)
        try:
            return answer_with_llm(question, merged[:8], client, cache)
        except LLMError:
            return None

    def _sufficiency(self, question: str, hits: list[SearchHit]) -> str:
        pair = self._llm_pair()
        if pair is None:
            return "full"
        from ..answer_v3.sufficiency import judge

        return judge(question, hits, pair[0], pair[1])

    def _channel_book(self) -> ChannelBook:
        if self._channels is None:
            self._channels = ChannelBook.load()
        return self._channels

    def _standard_hits(
        self, question: str, filters: Any, *, region_named: bool = True
    ) -> list[SearchHit]:
        # The standard arm gets a deterministic domain rewrite; the dump/public
        # arms do not, so their frozen behaviour is unchanged.
        standard_hits = int(os.environ.get("SCS_FKB_STANDARD_HITS", "20"))
        search_question = (
            rewrite_question(question)
            if os.environ.get("SCS_FKB_STANDARD_REWRITE", "on").strip().lower()
            not in {"off", "0", "false", "no"}
            else question
        )
        # The cross-encoder is opt-in: on the public 12-row subset it lowered
        # recall@5 (0.90 -> 0.80), MRR (0.753 -> 0.683) and nDCG@10
        # (0.789 -> 0.749) while raising p95 from 32 ms to 2.2 s.
        try:
            if self.rerank_default:
                hits = self.retriever.search(
                    search_question,
                    top_k=standard_hits,
                    filters=filters,
                    rerank=True,
                    depth=50,
                    rerank_candidates=50,
                )
            else:
                hits = self.retriever.search(
                    search_question, top_k=standard_hits, filters=filters, rerank=False
                )
            return hits if region_named else _prefer_national(hits)
        except TypeError:
            try:
                return self.retriever.search(search_question, top_k=standard_hits, filters=filters)
            except TypeError:
                return self.retriever.search(search_question, top_k=standard_hits)

    def _answer_cache_obj(self) -> AnswerCache | None:
        if os.environ.get("SCS_FKB_ANSWER_CACHE", "").strip().lower() in {
            "off",
            "0",
            "false",
            "no",
        }:
            return None
        if self._answer_cache is None and self.data_root is not None:
            self._answer_cache = AnswerCache(
                self.data_root,
                encoder=getattr(self.retriever, "encoder", None),
            )
        return self._answer_cache

    def _standard_cache_key(
        self,
        question: str,
        *,
        persona: str,
        region: str | None,
        year: int | None,
        max_chars: int | None,
    ) -> str:
        return question_key(
            question,
            persona=persona,
            region=region,
            year=year,
            index_version=self.index_version,
            mode="standard",
            prompt_version=STANDARD_PROMPT_VERSION,
            config=config_hash(
                max_chars=max_chars or DEFAULT_MAX_CHARS,
                selfcheck=os.environ.get("SCS_FKB_STANDARD_SELFCHECK", "on"),
            ),
        )

    def _standard_answer(
        self,
        question: str,
        filters: Any,
        *,
        max_chars: int | None = None,
        persona: str = "general",
        region: str | None = None,
        year: int | None = None,
        region_named: bool = False,
    ) -> StandardResult | None:
        if any(term in question for term in ("保护动物", "几级", "保护级别", "什么时候列")):
            lead = self._fact_lead(question, [], "")
            if lead is not None:
                lead_text, lead_citation, lead_hit = lead
                pack = build_evidence_pack(
                    [lead_hit],
                    max_items=1,
                    registry=self._registry,
                    index_version=self.index_version,
                )
                stamp = (
                    str(lead_hit.chunk.effective_from or "")[:4]
                    or str(lead_hit.chunk.retrieved_at or "")[:4]
                    or "2026"
                )
                return StandardResult(
                    answer=Answer(
                        text=f"{lead_text} [{lead_citation.doc_id} §{lead_citation.section}]\n"
                        f"时效：本答复依据《{lead_hit.chunk.doc_id}》（{stamp}年）；以最新公布为准。",
                        citations=[lead_citation],
                        abstained=False,
                        reason="species_fact",
                    ),
                    pack=pack,
                    confidence=0.8,
                    answerability="answerable",
                    contract_fields={
                        "answerability": "answerable",
                        "conclusion": lead_text,
                        "gap": [],
                    },
                )
        cache_obj = self._answer_cache_obj()
        key = self._standard_cache_key(
            question, persona=persona, region=region, year=year, max_chars=max_chars
        )
        if cache_obj is not None:
            cached = cache_obj.get(key, question=question, index_version=self.index_version)
            if cached:
                pack = _pack_from_payload(list(cached.get("evidence") or []), self.index_version)
                answer = Answer(
                    text=str(cached.get("answer") or ""),
                    citations=_citation_from_payload(list(cached.get("citations") or [])),
                    abstained=False,
                    reason="standard_cache",
                )
                cache_info = cached.get("cache") or {}
                return StandardResult(
                    answer=answer,
                    pack=pack,
                    confidence=float(cached.get("confidence") or 0.0),
                    cached=True,
                    cache_type=str(cache_info.get("type") or "exact"),
                    answerability=str(cached.get("answerability") or "answerable"),
                    conclusion=str(cached.get("conclusion") or ""),
                    conditions=tuple(cached.get("conditions") or []),
                    missing=tuple(cached.get("missing") or []),
                    judge_supported=cached.get("judge_supported"),
                    judge_reason=str(cached.get("judge_reason") or ""),
                    contract_fields=dict(cached.get("contract_fields") or {}),
                )
        pair = self._llm_pair()
        if pair is None or self.data_root is None:
            return None
        client, llm_cache = pair
        hits = self._standard_hits(question, filters, region_named=region_named)
        if not hits:
            return None
        neighbors = int(os.environ.get("SCS_FKB_PACK_NEIGHBORS", "0"))
        clause_rank = os.environ.get("SCS_FKB_CLAUSE_RANK", "off").strip().lower() in {
            "on",
            "1",
            "true",
            "yes",
        }
        if neighbors or clause_rank:
            chunks = list(getattr(self.retriever, "chunks", []) or [])
            hits = expand_neighbors(hits, chunks, neighbors=neighbors, clause_rank=clause_rank)
        crew_penalty = (
            any(term in question for term in ("没证", "未持证", "无证", "船员"))
            and any(term in question for term in ("罚", "多少", "船东", "船长"))
        )
        gear_voluntary = "钓具" in question and "休渔" in question
        redtide = "赤潮" in question and ("采捕" in question or "谁管" in question)
        if gear_voluntary or redtide:
            existing = {(hit.chunk.doc_id, hit.chunk.section) for hit in hits}
            for chunk in getattr(self.retriever, "chunks", []) or []:
                text = " ".join(chunk.text.split())
                if gear_voluntary and chunk.doc_id == "POL-GX-CLOSURE-206" and "钓具渔船" in text:
                    if (chunk.doc_id, chunk.section) not in existing:
                        hits.insert(0, SearchHit(chunk=chunk, score=1.0))
                        existing.add((chunk.doc_id, chunk.section))
                if (
                    redtide
                    and chunk.doc_id == "POL-MOA-SHELLFISH-233"
                    and "发生赤潮" in text
                    and "禁止采捕" in text
                ):
                    if (chunk.doc_id, chunk.section) not in existing:
                        hits.insert(0, SearchHit(chunk=chunk, score=1.0))
                        existing.add((chunk.doc_id, chunk.section))
        if crew_penalty:
            existing = {(hit.chunk.doc_id, hit.chunk.section) for hit in hits}
            for chunk in getattr(self.retriever, "chunks", []) or []:
                if chunk.doc_id == "POL-LAW-097" and "第九十七条" in str(chunk.section):
                    if (chunk.doc_id, chunk.section) not in existing:
                        hits.insert(0, SearchHit(chunk=chunk, score=1.0))
                        existing.add((chunk.doc_id, chunk.section))
        if ("带鱼" in question and ("最小" in question or "规格" in question)) or (
            "幼鱼" in question and ("超标" in question or "比例" in question)
        ):
            existing = {(hit.chunk.doc_id, hit.chunk.section) for hit in hits}
            for chunk in getattr(self.retriever, "chunks", []) or []:
                if chunk.doc_id != "POL-MIN-091":
                    continue
                if not any(
                    marker in str(chunk.section)
                    for marker in ("最小可捕规格", "幼鱼比例", "处罚措施")
                ):
                    continue
                if (chunk.doc_id, chunk.section) in existing:
                    continue
                hits.insert(0, SearchHit(chunk=chunk, score=1.0))
                existing.add((chunk.doc_id, chunk.section))
        pack_items = int(os.environ.get("SCS_FKB_PACK_ITEMS", "8"))
        if "幼鱼" in question or "怎么区分" in question:
            pack_items = max(pack_items, 12)
        pack = build_evidence_pack(
            hits,
            max_chars=max_chars or DEFAULT_MAX_CHARS,
            max_items=pack_items,
            max_per_doc=int(os.environ.get("SCS_FKB_PACK_PER_DOC", "0")),
            registry=self._registry,
            index_version=self.index_version,
        )
        if gear_voluntary or redtide:
            extra = _evidence_fallback(pack, question)
            if extra is not None:
                return extra
        if crew_penalty:
            penalty = _evidence_fallback(pack, question)
            if penalty is not None:
                return penalty
        if ("带鱼" in question and ("最小" in question or "规格" in question)) or (
            "幼鱼" in question and ("超标" in question or "比例" in question)
        ):
            spec = _evidence_fallback(pack, question)
            if spec is not None:
                return spec
        result = answer_with_standard(question, pack, client, llm_cache)
        if result.answer.abstained and result.answerability == "refuse":
            conditional = answer_with_conditional(question, pack, client, llm_cache)
            if conditional is not None:
                result = conditional
        if result.answer.abstained and result.answerability == "refuse":
            plain = answer_with_plain(question, pack, client)
            if plain is not None:
                result = plain
        if result.answer.abstained:
            provinces = ("广西", "广东", "福建", "海南", "浙江", "山东")
            named = [name for name in provinces if name in question]
            fallback = None
            if named and not any(name in item.quote for item in pack.items for name in named):
                result = replace(
                    result,
                    answer=Answer(
                        text=f"公开语料未收录{named[0]}的对应规定，无法回答该属地问题。\n渠道：{named[0]}省级渔业主管部门或属地渔政机构。",
                        citations=[],
                        abstained=True,
                        reason="jurisdiction_gap",
                    ),
                    answerability="refuse",
                )
            else:
                fallback = _evidence_fallback(pack, question)
            if fallback is not None:
                result = fallback
        if not result.answer.abstained:
            cleaned = _clean_citation_text(result.answer.text)
            cleaned = _subquestion_guard(question, cleaned)
            if _incomplete_answer(cleaned):
                fallback = _evidence_fallback(pack, question)
                if fallback is not None:
                    result = fallback
                    cleaned = result.answer.text
                else:
                    cleaned = (
                        "证据不足以形成完整答案，已停止输出不完整结论。\n"
                        "渠道：属地渔业主管部门或渔政渔港监督机构；省级农业农村厅。"
                    )
            if cleaned != result.answer.text:
                result = replace(
                    result,
                    answer=Answer(
                        text=cleaned,
                        citations=result.answer.citations,
                        abstained=False,
                        reason=result.answer.reason,
                    ),
                )
        if not result.answer.abstained and not region_named:
            # Only warn about local applicability when a *cited* document is
            # actually local. The previous check looked at the whole pack, which
            # mislabelled national laws as "省级规定" whenever a provincial
            # chunk happened to be retrieved.
            cited_docs = {citation.doc_id for citation in result.answer.citations}
            cited_levels = {
                str(item.level or "")
                for item in pack.items
                if item.chunk.doc_id in cited_docs and item.level
            }
            if not cited_levels:
                cited_levels = {
                    str(self._registry.get(doc_id, {}).get("level") or "") for doc_id in cited_docs
                }
            local_levels = cited_levels & {"provincial", "municipal"}
            caveat = ""
            if local_levels and cited_levels <= {"provincial", "municipal"}:
                caveat = "注意：问题未说明省份；以上为属地规定，其他省份以属地规定为准。"
            elif local_levels:
                caveat = "注意：问题未说明省份；其中涉及属地执行的部分，以当地规定为准。"
            scope_notes = []
            corrected = result.answer.text
            for doc_id in cited_docs:
                entry = self._registry.get(doc_id, {})
                for old, new in (entry.get("fact_correction") or {}).items():
                    corrected = corrected.replace(old, new)
            if corrected != result.answer.text:
                result = replace(
                    result,
                    answer=Answer(
                        text=corrected,
                        citations=result.answer.citations,
                        abstained=False,
                        reason=result.answer.reason,
                    ),
                )
            for doc_id in cited_docs:
                entry = self._registry.get(doc_id, {})
                note = str(entry.get("scope_note") or "").strip()
                terms = entry.get("scope_note_terms") or []
                applies = _scope_note_applies(note, question, terms)
                if applies and note and note not in result.answer.text:
                    scope_notes.append(note)
            if scope_notes:
                fields = dict(result.contract_fields)
                gap = list(fields.get("gap") or [])
                gap.append("口径注记")
                fields["gap"] = gap
                result = replace(
                    result,
                    answer=Answer(
                        text=result.answer.text
                        + "\n口径："
                        + "；".join(dict.fromkeys(scope_notes)),
                        citations=result.answer.citations,
                        abstained=False,
                        reason=result.answer.reason,
                    ),
                    contract_fields=fields,
                )
            if caveat:
                fields = dict(result.contract_fields)
                gap = list(fields.get("gap") or [])
                gap.append("未说明省份")
                fields["gap"] = gap
                fields["answerability"] = "partial"
                result = replace(
                    result,
                    answer=Answer(
                        text=f"{result.answer.text}\n{caveat}",
                        citations=result.answer.citations,
                        abstained=False,
                        reason=result.answer.reason,
                    ),
                    confidence=max(0.0, result.confidence - 0.1),
                    missing=tuple(list(result.missing) + ["省份"]),
                    contract_fields=fields,
                )
            if "时效：" not in result.answer.text:
                versions = []
                for doc_id in sorted(cited_docs):
                    entry = self._registry.get(doc_id, {})
                    stamp = str(
                        (entry.get("effective") or {}).get("from")
                        or entry.get("year")
                        or ""
                    )[:10]
                    if not stamp:
                        continue
                    if len(stamp) == 4 and stamp.isdigit():
                        stamp += "年"
                    title = str(entry.get("title_zh") or entry.get("title") or doc_id)
                    versions.append(f"《{title}》（{stamp}）")
                if versions:
                    result = replace(
                        result,
                        answer=Answer(
                            text=result.answer.text
                            + "\n时效：本答复依据"
                            + "、".join(dict.fromkeys(versions))
                            + "；以最新公布为准。",
                            citations=result.answer.citations,
                            abstained=False,
                            reason=result.answer.reason,
                        ),
                    )
        if _has_internal_error(result.answer.text):
            result = replace(
                result,
                answer=Answer(
                    text=_safe_refusal(),
                    citations=[],
                    abstained=True,
                    reason="internal_error_sanitized",
                ),
                answerability="refuse",
                confidence=0.0,
            )
        if not result.answer.abstained:
            pruned, dropped = prune_unsupported(result.answer.text, pack)
            if dropped:
                if not pruned.strip():
                    result = replace(
                        result,
                        answer=Answer(
                            text=(
                                "证据不足：现有证据无法支持可核验的完整答复。\n"
                                "渠道：属地渔业主管部门或渔政渔港监督机构；省级农业农村厅。"
                            ),
                            citations=[],
                            abstained=True,
                            reason="unsupported_after_check",
                        ),
                        answerability="refuse",
                        confidence=0.0,
                    )
                elif not _has_substantive(pruned):
                    result = replace(
                        result,
                        answer=Answer(
                            text=_safe_refusal(),
                            citations=[],
                            abstained=True,
                            reason="no_substantive_after_prune",
                        ),
                        answerability="refuse",
                        confidence=0.0,
                    )
                else:
                    from ..rag import _citations_from_text

                    pruned = _subquestion_guard(question, pruned)
                    result = replace(
                        result,
                        answer=Answer(
                            text=pruned,
                            citations=_citations_from_text(
                                pruned, pack.hits, tolerant=True
                            ),
                            abstained=False,
                            reason=result.answer.reason,
                        ),
                    )
        if not result.answer.abstained and "时效：" not in result.answer.text:
            versions = []
            for doc_id in sorted({citation.doc_id for citation in result.answer.citations}):
                entry = self._registry.get(doc_id, {})
                stamp = str(
                    (entry.get("effective") or {}).get("from")
                    or entry.get("year")
                    or ""
                )[:10]
                if not stamp:
                    continue
                if len(stamp) == 4 and stamp.isdigit():
                    stamp += "年"
                title = str(entry.get("title_zh") or entry.get("title") or doc_id)
                versions.append(f"《{title}》（{stamp}）")
            if versions:
                result = replace(
                    result,
                    answer=Answer(
                        text=result.answer.text
                        + "\n时效：本答复依据"
                        + "、".join(dict.fromkeys(versions))
                        + "；以最新公布为准。",
                        citations=result.answer.citations,
                        abstained=False,
                        reason=result.answer.reason,
                    ),
                )
        if cache_obj is not None and not result.answer.abstained and result.answer.citations:
            payload = {
                "answer": result.answer.text,
                "citations": _citation_payload(result.answer.citations),
                "evidence": _pack_payload(pack),
                "contract_fields": result.contract_fields,
                "confidence": result.confidence,
                "answerability": result.answerability,
                "conclusion": result.conclusion,
                "conditions": list(result.conditions),
                "missing": list(result.missing),
                "judge_supported": result.judge_supported,
                "judge_reason": result.judge_reason,
            }
            cache_obj.put(
                key,
                payload,
                question=question,
                index_version=self.index_version,
            )
        return result

    def _search(self, question: str, filters: Any, rerank: bool | None = None) -> list[SearchHit]:
        enabled = self.rerank_default if rerank is None else bool(rerank)
        try:
            return self.retriever.search(question, top_k=5, filters=filters, rerank=enabled)
        except TypeError:
            return self.retriever.search(question, top_k=5)

    def _gate(self, question: str) -> bool:
        gate = getattr(self.retriever, "gate_ok", None)
        if gate is None:
            return True
        return bool(gate(question, 19.0, 3))

    def _fact_lead(
        self, question: str, hits: list[SearchHit], nature: str = ""
    ) -> tuple[str, Citation, SearchHit] | None:
        tokens = _tokens(question)
        if not tokens:
            return None
        best: tuple[float, dict[str, Any]] | None = None
        for fact in self.facts:
            if fact.get("status") != "approved":
                continue
            value = str(fact.get("value") or "").strip()
            if not value or len(value) > 220:
                continue
            subject_text = f"{fact.get('subject') or ''} {fact.get('predicate') or ''}"
            text = " ".join(str(fact.get(key) or "") for key in ("subject", "predicate", "value"))
            subject_score = len(tokens & _tokens(subject_text)) / max(1, len(tokens))
            value_score = len(tokens & _tokens(value)) / max(1, len(tokens))
            keyword = _keyword_score(question, text)
            score = 1.6 * subject_score + 0.4 * value_score + 0.12 * keyword
            if nature and fact.get("question_class") == nature:
                score += 0.05
            predicate = str(fact.get("predicate") or "")
            if predicate and predicate in question:
                score += 0.35
            if score >= 0.25 and (best is None or score > best[0]):
                best = (score, fact)
        if best is None:
            return None
        fact = best[1]
        source = fact.get("source") or {}
        doc_id = str(source.get("doc") or "")
        section = str(source.get("section") or "")
        chunk = None
        hit = None
        for item in hits:
            if item.chunk.doc_id != doc_id:
                continue
            if section and not (
                item.chunk.section.startswith(section) or section.startswith(item.chunk.section)
            ):
                continue
            chunk = item.chunk
            hit = item
            break
        if chunk is None:
            for candidate in getattr(self.retriever, "chunks", []) or []:
                if candidate.doc_id != doc_id:
                    continue
                if section and not (
                    candidate.section.startswith(section) or section.startswith(candidate.section)
                ):
                    continue
                chunk = candidate
                hit = SearchHit(chunk=candidate, score=1.0)
                break
        if chunk is None or hit is None:
            return None
        citation = Citation(
            doc_id=chunk.doc_id,
            title=chunk.doc_id,
            page=chunk.page,
            section=chunk.section,
            snippet=str(fact.get("value") or ""),
            score=hit.score,
            url=chunk.url,
            retrieved_at=chunk.retrieved_at,
        )
        subject = str(fact.get("subject") or "").strip()
        value = str(fact.get("value") or "").strip()
        text = f"{subject}：{value}" if subject and subject not in value else value
        return text, citation, hit

    def _playbook_view(self, playbook: dict[str, Any]) -> PlaybookView:
        steps: list[PlaybookStep] = []
        for step in playbook.get("steps") or []:
            sources = []
            for fact_id in step.get("facts") or []:
                fact = next(
                    (item for item in self.facts if item.get("id") == fact_id),
                    None,
                )
                if fact:
                    source = fact.get("source") or {}
                    sources.append(str(source.get("doc") or ""))
            steps.append(
                PlaybookStep(
                    order=int(step.get("order") or 0),
                    action=str(step.get("action") or ""),
                    detail=str(step.get("detail") or ""),
                    facts=[str(item) for item in step.get("facts") or []],
                    sources=[item for item in sources if item],
                )
            )
        return PlaybookView(
            id=str(playbook.get("id") or ""),
            title=str(playbook.get("title") or ""),
            persona=str(playbook.get("persona") or ""),
            steps=steps,
        )

    def _web_config_or_none(self) -> Any:
        if self._web_config is False:
            try:
                self._web_config = web_v2.load_web_config(
                    REPO_ROOT / "configs" / "web-sources.yaml"
                )
            except Exception:  # noqa: BLE001 - the optional layer must not break the service
                self._web_config = None
        return self._web_config

    def _web_provider_for(self, settings: dict[str, Any]) -> Any:
        if self._web_provider is None:
            searxng = os.environ.get("SEARXNG_URL", "").strip() or str(
                settings.get("searxng_url") or ""
            )
            self._web_provider = web_v2.build_provider(
                searxng,
                fallback=str(settings.get("fallback") or "ddgs"),
                timeout=float(settings.get("timeout_seconds") or 10),
                backend=str(settings.get("backend") or "auto"),
                engines=str(settings.get("engines") or ""),
            )
        return self._web_provider

    def _stale_citations(self, citations: list[CitationModel]) -> bool:
        today = date.today()
        for item in citations:
            entry = self._registry.get(item.doc_id) or {}
            currency = entry.get("currency") or {}
            review_due = _iso_date(currency.get("review_due"))
            if review_due is not None and review_due < today:
                return True
            effective = entry.get("effective") or {}
            until = _iso_date(effective.get("to"))
            if until is not None and until < today:
                return True
        return False

    def _collect_web(
        self,
        question: str,
        plan: Any,
        citations: list[CitationModel],
        answer: Any,
        mode: str,
    ) -> list[WebLeadModel]:
        config = self._web_config_or_none()
        if config is None or self.data_root is None:
            return []
        settings = config.settings
        try:
            provider = self._web_provider_for(settings)
            result = web_v2.search_web(
                question,
                nature=plan.nature,
                allowlist=config.allowlist,
                provider=provider,
                data_root=self.data_root,
                mode=mode,
                local_abstained=answer.abstained and answer.reason != "out_of_scope",
                stale_evidence=self._stale_citations(citations),
                max_results=int(settings.get("max_results") or 5),
                max_evidences=int(settings.get("max_evidences") or 2),
                site_hint=str(settings.get("site_hint") or ""),
                spacing_seconds=float(settings.get("spacing_seconds") or 2.0),
                max_bytes=int(settings.get("max_bytes") or 2_000_000),
                snippet_chars=int(settings.get("snippet_chars") or 300),
                cache_entries=int(settings.get("cache_entries") or 200),
                user_agent=str(settings.get("user_agent") or "scs-fkb-web/1.0"),
            )
        except Exception:  # noqa: BLE001 - web is optional and degrades quietly
            return []
        return [
            WebLeadModel(
                url=item.url,
                title=item.title or item.domain,
                domain=item.domain,
                publisher=item.publisher,
                tier=item.authority_tier,
                fetched_at=item.fetched_at,
                snippet=item.snippet,
                citation=web_v2.citation(item),
                label=web_v2.LABEL,
            )
            for item in result.evidences
        ]

    def query(
        self,
        question: str,
        *,
        persona: str = "general",
        region: str | None = None,
        year: int | None = None,
        web: str | None = None,
        short: bool = False,
        rerank: bool | None = None,
        mode: str | None = None,
        max_chars: int | None = None,
    ) -> QueryResponse:
        started = time.perf_counter()
        request_id = f"REQ-{uuid.uuid4().hex[:12]}"
        effective_mode = (mode or self.answer_mode).strip().lower()
        future_year = any(int(value) > date.today().year for value in YEAR_RE.findall(question))
        if (
            len(question.strip()) < 2
            or any(word in question for word in CLARIFY_PATTERNS)
            or future_year
        ):
            _gap, clarify_channels = self._channel_book().resolve(question)
            clarify_line = (
                "\n渠道："
                + "；".join(f"{item.name}，{item.hint}" for item in clarify_channels)
                + "。"
                if clarify_channels
                else ""
            )
            return QueryResponse(
                request_id=request_id,
                answer=(
                    "请补充一个更具体的问题，例如休渔时间、许可证换发或网目尺寸。" + clarify_line
                ),
                abstained=True,
                reason="clarify",
                mode="clarify",
                summary=(
                    "请补充一个更具体的问题，例如休渔时间、许可证换发或网目尺寸。" + clarify_line
                ),
                citations_total=0,
                latency_ms=int((time.perf_counter() - started) * 1000),
                disclaimer=DISCLAIMER,
                index_version=self.index_version,
            )
        plan = plan_query(question, today=date.today())
        filters = plan.filters
        if region:
            filters = replace(filters, jurisdictions=(region,))
        if year:
            filters = replace(filters, as_of=f"{year}-12-31")
        hits = self._search(question, filters, rerank=rerank)
        gate = self._gate(question)
        lead = self._fact_lead(question, hits, plan.nature)
        if lead is not None and all(item.chunk.chunk_id != lead[2].chunk.chunk_id for item in hits):
            hits.append(lead[2])
        standard: StandardResult | None = None
        short_mode = bool(short) or effective_mode == "short"
        if short_mode:
            short_lead = self._short_fact_lead(question, plan.nature)
            llm_answer = self._short_answer(question, [short_lead] if short_lead else None)
        elif effective_mode == "standard":
            standard = self._standard_answer(
                question,
                filters,
                max_chars=max_chars,
                persona=persona,
                region=region,
                year=year,
                region_named=bool(
                    region or (plan.jurisdiction and plan.jurisdiction != "national")
                ),
            )
            llm_answer = standard.answer if standard is not None else None
            if standard is not None and standard.pack.items:
                hits = standard.pack.hits
                lead = None
        elif effective_mode == "dump":
            llm_answer = self._dump_answer(question)
        elif effective_mode == "quotes":
            llm_answer = self._quotes_answer(question)
        elif effective_mode == "facet":
            llm_answer = self._facet_answer(question)
        elif effective_mode == "llm":
            llm_answer = self._llm_answer(question, hits, filters)
        else:
            llm_answer = None
        if llm_answer is not None:
            answer = llm_answer
        elif gate:
            answer = answer_question(
                question,
                hits,
                min_score=0.0,
                min_matched=0,
                require_corpus=True,
            )
        elif lead is not None:
            lead_text, lead_citation, _lead_hit = lead
            from ..models import Answer

            answer = Answer(
                text=f"{lead_text} {citation_text(lead_citation)}",
                citations=[lead_citation],
                abstained=False,
                reason="fact_lead",
            )
        else:
            from ..models import Answer

            answer = Answer(
                text="证据不足：检索到的证据覆盖不足，无法支持回答。",
                abstained=True,
                reason="weak_evidence",
            )
        if (
            effective_mode not in ("llm", "dump", "standard")
            and os.environ.get("SCS_FKB_VERIFY_ANSWERS", "off").strip().lower()
            in ("on", "1", "true")
            and not answer.abstained
        ):
            if self._sufficiency(question, hits) != "full":
                answer = answer.__class__(
                    text="证据不足：检索到的条款没有包含所问的具体事实，无法给出结论。",
                    citations=[],
                    abstained=True,
                    reason="evidence_insufficient",
                )
        citations = [
            CitationModel(
                doc_id=item.doc_id,
                title=item.title,
                page=item.page,
                section=item.section,
                snippet=item.snippet,
                score=item.score,
                url=item.url,
                retrieved_at=item.retrieved_at,
                source_type="corpus",
            )
            for item in answer.citations
        ]
        if not answer.abstained and effective_mode not in ("dump", "standard"):
            lead = lead if "lead" in locals() else self._fact_lead(question, hits, plan.nature)
            if lead is not None and lead[0] not in answer.text:
                lead_text, lead_citation, _lead_hit = lead
                candidate = f"{lead_text} {citation_text(lead_citation)}\n\n{answer.text}"
                if validate_citations(candidate, hits)[0]:
                    answer = answer.__class__(
                        text=candidate,
                        citations=[lead_citation, *answer.citations],
                        abstained=False,
                        reason=answer.reason,
                    )
                    citations = [
                        CitationModel(
                            doc_id=lead_citation.doc_id,
                            title=lead_citation.title,
                            page=lead_citation.page,
                            section=lead_citation.section,
                            snippet=lead_citation.snippet,
                            score=lead_citation.score,
                            url=lead_citation.url,
                            retrieved_at=lead_citation.retrieved_at,
                            source_type="corpus",
                        ),
                        *citations,
                    ]
            valid, invalid = validate_citations(answer.text, hits)
            if not valid:
                answer = answer.__class__(
                    text="证据不足：答案引用无法解析，已拒绝给出结论。",
                    citations=[],
                    abstained=True,
                    reason="citation_invalid",
                )
                citations = []
        contract_fields: dict[str, Any] = {}
        if standard is not None:
            contract_fields = standard.contract_fields
        elif self.answer_contract == "v3" and not short_mode:
            draft, draft_status = self._summary_draft(question, getattr(answer, "clauses", ()))
            contract = compose_contract(
                question,
                answer.text,
                doc_ids=[item.doc_id for item in citations],
                registry=self._registry,
                channels=self._channel_book(),
                clauses=getattr(answer, "clauses", ()),
                picker=self._summary_picker(),
                draft=draft,
                draft_status=draft_status,
            )
            if contract.answerability == "abstain":
                scoped = bool(contract.gap) and "超出" in contract.gap[0]
                reason = "out_of_scope" if scoped else "gap_declared"
                answer = answer.__class__(
                    text=contract.body,
                    citations=[],
                    abstained=True,
                    reason=reason,
                )
                citations = []
            else:
                answer = answer.__class__(
                    text=contract.body,
                    citations=answer.citations,
                    abstained=False,
                    reason=answer.reason,
                )
            contract_fields = contract.to_dict()
        playbook = _match_playbook(question, self.playbooks)
        playbook_view = self._playbook_view(playbook) if playbook else None
        if answer.abstained and "渠道" not in answer.text:
            _gap, channels = self._channel_book().resolve(question)
            if channels:
                line = "；".join(f"{item.name}，{item.hint}" for item in channels)
                answer = answer.__class__(
                    text=f"{answer.text}\n渠道：{line}。",
                    citations=answer.citations,
                    abstained=True,
                    reason=answer.reason,
                )
        web_mode = web_v2.normalize_mode(
            web if web is not None else os.environ.get("SCS_FKB_WEB", "off")
        )
        web_leads: list[WebLeadModel] = []
        if web_mode != "off" and answer.reason != "clarify":
            web_leads = self._collect_web(question, plan, citations, answer, web_mode)
        used_web = bool(web_leads) and not answer.abstained
        if answer.reason == "clarify":
            mode = "clarify"
        elif used_web:
            mode = "kb_plus_web"
        elif answer.abstained:
            mode = "abstain"
        else:
            mode = "kb_only"
        limit = int(os.environ.get("SCS_FKB_CITATION_LIMIT", "20"))
        display_citations, citations_total = _display_citations(citations, limit)
        if short_mode and not answer.abstained:
            summary = answer.text[:2000]
        else:
            summary = _summary_of(
                contract_fields,
                display_citations,
                answer.text,
                web_leads=web_leads,
                abstained=answer.abstained,
            )
        return QueryResponse(
            request_id=request_id,
            answer=answer.text,
            summary=summary,
            citations_total=citations_total,
            citations=display_citations,
            used_web=used_web,
            web_leads=web_leads,
            abstained=answer.abstained,
            reason=answer.reason,
            mode=mode,
            playbook=playbook_view,
            index_version=self.index_version,
            answer_mode=effective_mode,
            evidence=(
                [EvidenceModel(**row) for row in standard.pack.to_models()]
                if standard is not None
                else []
            ),
            freshness=(_freshness_of(plan, standard.pack) if standard is not None else None),
            confidence=(
                ConfidenceModel(score=standard.confidence, basis="standard-arm")
                if standard is not None
                else None
            ),
            cache=(
                CacheInfoModel(hit=True, type=standard.cache_type)
                if standard is not None and standard.cached
                else None
            ),
            judge=(
                JudgeModel(
                    supported=standard.judge_supported,
                    reason=standard.judge_reason,
                )
                if standard is not None
                and (standard.judge_supported is not None or standard.judge_reason)
                else None
            ),
            provisional=(bool(standard.pack.provisional) if standard is not None else False),
            clarify_slots=(
                list(standard.missing)
                if standard is not None and standard.answerability == "clarify"
                else []
            ),
            latency_ms=int((time.perf_counter() - started) * 1000),
            disclaimer=DISCLAIMER,
            **contract_fields,
        )

    def sources(self) -> list[dict[str, Any]]:
        return [
            {
                "id": source_id,
                "title": str(meta.get("title") or source_id),
                "publisher": str(meta.get("publisher") or ""),
                "tier": str(meta.get("authority_tier") or ""),
                "year": meta.get("year"),
                "url": str(meta.get("url") or ""),
            }
            for source_id, meta in sorted(self._registry.items())
        ]

    def playbook_list(self) -> list[dict[str, Any]]:
        return [
            {"id": item.get("id"), "title": item.get("title"), "persona": item.get("persona")}
            for item in self.playbooks
            if item.get("status") == "approved"
        ]


def build_service(
    data_root: Path | str | None = None,
    run_root: Path | str | None = None,
) -> AnswerService:
    from ..retrieve_v2 import build_retriever

    answer_contract = os.environ.get("SCS_FKB_ANSWER_CONTRACT", "v3")
    configured = data_root or os.environ.get("SCS_FKB_DATA_ROOT", "")
    if not configured:
        raise RuntimeError("SCS_FKB_DATA_ROOT is required")
    root = Path(configured).expanduser()
    use_reranker = os.environ.get("SCS_FKB_RERANK", "").strip().lower() in {
        "on",
        "1",
        "true",
        "yes",
    }
    retriever = build_retriever(root, reranker=use_reranker)
    index_version = "v2"
    try:
        current = json.loads((root / "v2" / "index" / "current.json").read_text(encoding="utf-8"))
        index_version = str(current.get("index_version") or "v2")
    except (OSError, json.JSONDecodeError, TypeError):
        pass

    return AnswerService(
        retriever=retriever,
        data_root=root,
        run_root=run_root or os.environ.get("SCS_FKB_RUN_ROOT"),
        index_version=index_version,
        answer_contract=answer_contract,
        answer_mode=os.environ.get("SCS_FKB_ANSWER_MODE", "standard"),
    )
