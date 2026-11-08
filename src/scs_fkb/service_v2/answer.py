from __future__ import annotations

import os
import re
import time
import uuid
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Any

from ..answer import answer_question, citation_text, validate_citations
from ..answer_v3 import ChannelBook
from ..answer_v3 import compose as compose_contract
from ..answer_v3.llm_answer import answer_with_llm
from ..facts import DEFAULT_FACTS_DIR, load_all
from ..knowledge_v2 import load_playbooks
from ..llm import LLMClient, LLMConfig, LLMError
from ..models import Citation, SearchHit
from ..rag import LLMCache
from ..registry import load_registry
from ..retrieve_v2 import plan_query
from .schemas import (
    CitationModel,
    PlaybookStep,
    PlaybookView,
    QueryResponse,
)

DISCLAIMER = "以官方发布文本为准；本服务不构成法律意见。"
WEB_LABEL = "网络检索 · 未入知识库"
YEAR_RE = re.compile(r"(20\d{2})\s*年?")
CLARIFY_PATTERNS = ("某渔场", "某海域", "某年度", "某类", "某品种", "某一")
WEATHER_WORDS = ("台风", "海温", "预报", "风暴潮", "赤潮", "海浪", "预警")
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


class AnswerService:
    """Compose v2 retrieval, playbooks and optional labelled web evidence."""

    def __init__(
        self,
        *,
        retriever: Any,
        playbooks: list[dict[str, Any]] | None = None,
        facts: list[dict[str, Any]] | None = None,
        data_root: Path | str | None = None,
        run_root: Path | str | None = None,
        index_version: str = "v2",
        web_search: Any = None,
        answer_contract: str = "v3",
    ) -> None:
        self.retriever = retriever
        self.playbooks = playbooks if playbooks is not None else load_playbooks()
        self.facts = facts if facts is not None else load_all(DEFAULT_FACTS_DIR)
        self.data_root = Path(data_root).expanduser().resolve() if data_root else None
        self.run_root = Path(run_root).expanduser().resolve() if run_root else None
        self.index_version = index_version
        self.web_search = web_search
        self.answer_contract = answer_contract
        self.answer_mode = os.environ.get("SCS_FKB_ANSWER_MODE", "extractive").strip().lower()
        self._llm: Any = False
        self._channels: ChannelBook | None = None
        self._registry = load_registry()

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

    def _channel_book(self) -> ChannelBook:
        if self._channels is None:
            self._channels = ChannelBook.load()
        return self._channels

    def _search(self, question: str, filters: Any) -> list[SearchHit]:
        try:
            return self.retriever.search(question, top_k=5, filters=filters, rerank=False)
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
        return str(fact.get("value") or "").strip(), citation, hit

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

    def _web_result(self, question: str, nature: str, filters: Any) -> Any:
        if self.web_search is None:
            return None
        try:
            return self.web_search(question, nature=nature, filters=filters)
        except TypeError:
            return self.web_search(question)

    def query(
        self,
        question: str,
        *,
        persona: str = "general",
        region: str | None = None,
        year: int | None = None,
        web: str = "auto",
    ) -> QueryResponse:
        started = time.perf_counter()
        request_id = f"REQ-{uuid.uuid4().hex[:12]}"
        future_year = any(int(value) > date.today().year for value in YEAR_RE.findall(question))
        if (
            len(question.strip()) < 2
            or any(word in question for word in CLARIFY_PATTERNS)
            or future_year
            or (
                any(word in question for word in WEATHER_WORDS)
                and not any(word in question for word in ("规定", "制度", "办法"))
            )
        ):
            return QueryResponse(
                request_id=request_id,
                answer="请补充一个更具体的问题，例如休渔时间、许可证换发或网目尺寸。",
                abstained=True,
                reason="clarify",
                mode="clarify",
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
        hits = self._search(question, filters)
        gate = self._gate(question)
        lead = self._fact_lead(question, hits, plan.nature)
        if lead is not None and all(item.chunk.chunk_id != lead[2].chunk.chunk_id for item in hits):
            hits.append(lead[2])
        llm_answer = (
            self._llm_answer(question, hits, filters) if self.answer_mode == "llm" else None
        )
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
        if not answer.abstained:
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
        if self.answer_contract == "v3":
            contract = compose_contract(
                question,
                answer.text,
                doc_ids=[item.doc_id for item in citations],
                registry=self._registry,
                channels=self._channel_book(),
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
        used_web = False
        started_abstained = answer.abstained
        should_web = web == "on" or (web == "auto" and (answer.abstained or plan.freshness))
        if should_web:
            web_result = self._web_result(question, plan.nature, filters)
            evidences = list(getattr(web_result, "evidences", []) or [])
            if evidences:
                lines = [answer.text] if not answer.abstained else []
                for evidence in evidences[:2]:
                    snippet = str(getattr(evidence, "snippet", "") or "")[:300]
                    label = f"{WEB_LABEL}：{snippet}"
                    lines.append(label)
                    citations.append(
                        CitationModel(
                            doc_id=str(getattr(evidence, "evidence_id", "WEB")),
                            title=str(getattr(evidence, "title", "") or "网络资料"),
                            page=None,
                            section=None,
                            snippet=snippet,
                            score=0.0,
                            url=str(getattr(evidence, "url", "")),
                            retrieved_at=str(getattr(evidence, "fetched_at", ""))[:10],
                            source_type="web",
                            label=WEB_LABEL,
                        )
                    )
                if lines:
                    answer = answer.__class__(
                        text="\n\n".join(lines),
                        citations=answer.citations,
                        abstained=False if answer.abstained else answer.abstained,
                        reason="web_supplement" if answer.abstained else answer.reason,
                    )
                    used_web = True
        mode = "clarify" if answer.reason == "clarify" else "abstain"
        if used_web and started_abstained:
            mode = "web_only"
        elif not answer.abstained:
            mode = "kb_plus_web" if used_web else "kb_only"
        return QueryResponse(
            request_id=request_id,
            answer=answer.text,
            citations=citations,
            abstained=answer.abstained,
            reason=answer.reason,
            mode=mode,
            used_web=used_web,
            playbook=playbook_view,
            index_version=self.index_version,
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
    retriever = build_retriever(root, reranker=False)

    def web_search(question: str, *, nature: str, filters: Any) -> Any:
        from ..web_v2 import build_provider, load_allowlist, search_web

        allowlist = load_allowlist()
        provider = build_provider(os.environ.get("SEARXNG_URL", ""))
        return search_web(
            question,
            nature=nature,
            allowlist=allowlist,
            provider=provider,
            data_root=root,
            max_results=2,
        )

    return AnswerService(
        retriever=retriever,
        data_root=root,
        run_root=run_root or os.environ.get("SCS_FKB_RUN_ROOT"),
        web_search=web_search,
        answer_contract=answer_contract,
    )
