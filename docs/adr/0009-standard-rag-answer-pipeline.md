# ADR 0009: Standard RAG answer pipeline as the default

> 中文摘要：把默认答案臂从“10 万字条款倾倒”换成“检索→重排→父级扩展→证据包→结构化生成→引用校验→自检→拒答/澄清→语义缓存”；dump 只保留给 512 回归与诊断。

- Status: Proposed
- Date: 2026-11-12

## Context

The shipped default is the deterministic clause-dump arm: it retrieves up to
300 hits, quotes up to 100,000 characters and asks the model for a summary.
The 512 instrument scores the evidence pack, so the arm reached 0.8092 point
coverage, but the user-facing summary was judged correct on only 9 of 20 rows
in the fourth holdout. The arm is expensive, hard to explain and not a standard
RAG pipeline. The project needs a default that a reader can trust and that an
external reviewer recognises as retrieval-augmented generation.

## Decision

- The default answer arm becomes a standard pipeline:
  1. normalise the question and identify claim nature, domain and required slots;
  2. hybrid retrieval (BM25 + dense, RRF) to top 50;
  3. cross-encoder rerank to top 8;
  4. expand each winning child chunk to its parent section and deduplicate;
  5. build an evidence pack capped at 8–12k characters, with document id,
     section, page, authority tier, effective date and freshness;
  6. generate structured JSON: answerability, conclusion, applicability, steps,
     documents, deadline, basis, caveat, citations and missing slots;
  7. validate every citation against the pack (resolution, quote support,
     number/date match); drop unsupported sentences and abstain if the
     conclusion fails;
  8. optionally self-check with a RAGAS faithfulness judge (product default on,
     batch default off) and run one repair pass;
  9. answer from a reviewed canonical-answer bank when one matches, still cited;
  10. cache the validated answer by question, persona, region/year, index
      version, prompt version and config hash.
- The clause-dump arm stays in the tree as a **Track A instrument arm and a
  diagnostic**; it is no longer the default and is enabled only explicitly with
  `SCS_FKB_ANSWER_MODE=dump`.
- The `short` and `full` presentation modes remain; both read the same evidence
  pack and pass the same validator.
- The `/v1` contract gains additive fields (`answer_mode`, `evidence`,
  `freshness`, `confidence`, `provisional`, `cache`, `judge`, `clarify_slots`);
  existing fields and clients keep working.

## Consequences

- Answer quality is measured on the user-visible answer, not only on the
  evidence pack; Track A and Track B remain separate (ADR 0010).
- Latency and cost move from one long generation to a bounded pack plus one
  generation and one optional judge call; the cache and the deterministic
  fallback bound the worst case.
- The validator, abstention and cache need unit tests with golden evidence
  packs and a mock LLM; CI must not call the network.
- A standard pipeline can fail more visibly than the dump arm. That is
  intentional: a labelled abstention or clarification is better than a wall of
  text whose decisive clause the reader cannot find.
- The old v1 helpers (`answer.py`, `rag.py`, `retrieve.py`) are retired only
  after their remaining imports are moved and the regression suite is green.

## Alternatives considered

- **Keep the dump arm as default**: highest 512 point coverage, lowest
  usability; rejected because the product goal is a worker-facing answer.
- **One-pass LLM over the whole corpus**: unbounded cost and no citation
  discipline; rejected.
- **Extractive-only answer**: safe but does not compose steps, documents and
  deadlines; kept as a fallback, not the default.

## References

- [RAG standard](../rag-standard.md) sections 5–6
- [Evaluation](../evaluation.md) sections 25–42
- [Metrics report](../metrics-report.md)
- [RAGAS](https://docs.ragas.io/)
