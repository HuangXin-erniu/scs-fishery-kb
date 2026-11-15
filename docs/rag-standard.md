# RAG Knowledge Base Standard

> **中文摘要**：本文件定义 SCS-FKB 的 RAG 知识库构建标准：来源准入、快照与解析、层级分块、索引、混合检索与重排、证据约束生成、引用/拒答/冲突、网络证据、评测、运维、安全与可复现性。
> 目标是让每个回答都能追溯到具体来源版本；网络证据单独成层、带抓取时间且不自动入库。标准对齐 NIST AI RMF、ISO/IEC 42001、ISO 8000、W3C PROV-O、FAIR 与 RAGAS 的思想，但不声称任何认证。

- Status: adopted 2026-11-06 as the construction standard for the SCS-FKB refactor.
- Scope: source governance, ingestion, knowledge organisation, retrieval, generation, evaluation and operations.
- Non-goals: forecast-model training, raw environmental grids, full AIS/VMS tracks, a production multi-tenant service.

## 1. Source standard

### 1.1 Authority tiers

| Tier | Definition | May be primary for |
|---|---|---|
| A | Publisher's own central or provincial page, or the national law database | Law, regulation, notice, official statistics, standard, definition |
| B | Official gazette, government-information attachment or compilation | The same, when the attachment is the issued text |
| C | Municipal or county official page | Local supplement only; never a substitute for a higher-level document |
| D | Non-official expert source: association, university, extension station, NGO | Background or definition only; never rule, status, quantity or warning |

A and B sources may be primary for a normative or statistical claim. C sources
are labelled with their level and cannot fill a missing provincial or national
document. D sources are labelled `非官方资料` and are never the sole support for
an operational rule.

### 1.2 Admission checklist

A source enters the register only when all of the following hold:

1. The publisher is the body that owns the document, not a repost or aggregator.
2. A stable URL or a supplied file exists, with a document number or publication
   date where one exists.
3. The licence is known and on the allowlist: `public`, `internal`, `licensed` or
   the registered CC BY-NC-SA variant.
4. The sensitivity is known: `public`, `internal` or `restricted`.
5. The text is reachable and parseable, or the entry records why it is not.
6. A SHA-256 and a snapshot location are recorded.
7. A currency cadence and review date are recorded within the cadence cap.
8. A candidate entry exists for a newly discovered page; a watch report alone is
   not an admission.

News, reposts, search-engine caches, login-only pages, paywalled text without a
licence and summaries of a source are not citable sources. They may be recorded
as leads or candidates.

### 1.3 Currency and supersession

- `currency.as_of` records the last check; `review_due` records the next one;
  `cadence` bounds the interval.
- A source past `review_due` plus the grace window fails CI. It is not silently
  treated as current.
- A newer version supersedes but never deletes the older one. The older entry
  keeps its date and hash; the newer entry records `supersedes`.
- An answer that relies on a source at its review date must say so.

### 1.4 Provenance

Every source carries `provenance`: URL, document number, publication date,
retrieval date, SHA-256, byte size, MIME type and snapshot path. The record is
the audit trail from the answer citation back to the bytes that were read.

The register keeps ids and hashes stable. A migration may derive defaults from
legacy fields, but it must not silently change an id, hash or licence.

## 2. Snapshot, parsing and quality gates

1. **Snapshot first.** Copy the bytes into a content-addressed path
   `snapshots/<source_id>/<sha256>/` and hash them before parsing. The index is
   built from snapshots, not from a mutable URL.
2. **Parse with an adapter.** Use Docling for complex PDF/DOCX layout and tables,
   `trafilatura` for web main text, and the existing OFD, HTML, DOCX, PDF and
   spreadsheet adapters for the formats they already handle well.
3. **Preserve anchors.** Every chunk keeps a page, section, article, table id or
   row anchor that can be rendered in a citation. A parse that loses the anchor
   is quarantined.
4. **Quarantine rather than guess.** Low text coverage, missing text layer,
   malformed tables and OCR failures are recorded with a reason; they do not
   become empty evidence.
5. **OCR is opt-in.** A scanned source is marked `ocr: true` and processed only
   when the source owner accepts the quality risk. The OCR text is never treated
   as a verified value without a spot check.
6. **Deduplicate by hash.** Byte-identical files are one source; different
   editions are separate versions with explicit supersession.

## 3. Chunking

- Use a hierarchical model: document → chapter/section → article/clause →
  table row. Retrieval runs on the smallest useful unit; the answer expands to
  the parent section for context.
- Preserve `parent_id`, `section_path`, `article`, `page`, `table_id`, `row` and
  `bbox` where available.
- Keep Chinese legal structure intact: do not split an article in the middle of
  a numbered clause; do not drop headings or table captions.
- Target 300–800 Chinese characters for a text chunk, with a small overlap. A
  clause shorter than the minimum stays with its parent heading.
- A table chunk includes the table title, column headers and the row values, so
  a numeric answer can be checked against the source.
- A chunk inherits `authority_tier`, `source_class`, `trust`, `jurisdiction`,
  `sensitivity`, `license`, `effective_from/to` and `snapshot_hash` from its
  document.

## 4. Index

- **Dense:** BGE embedding into LanceDB, with metadata columns for filtering.
  The model id, dimension and normalization are recorded in the manifest.
- **Lexical:** character-bigram BM25 with the calibrated lexical gate. The gate
  is the only abstention signal; a dense cosine score is not comparable to a
  BM25 score.
- **Metadata:** `doc_id`, `source_id`, `version_id`, `authority_tier`,
  `source_class`, `trust`, `level`, `jurisdiction`, `sensitivity`, `channel`,
  `effective_from`, `effective_to`, `language`, `chunk_type`.
- **Manifest:** index version, code commit, source-manifest hash, document and
  chunk counts, embedding model, reranker model, chunker/BM25 config hashes,
  build time and peak memory.
- **Atomic build:** write to a new version, validate counts and a smoke query,
  then switch the `current` pointer. Keep the previous version for rollback.

**Implementation status (2026-11-10).** Every build writes an immutable
`v2/index/versions/<index_version>/lancedb` table and its manifest, then switches
`v2/index/current.json` with a temporary file and an atomic rename. The previous
version is kept for `scripts/build_index_v2.py --rollback`; `--prune` keeps the
last two. The manifest records `code_commit`, `pipeline_config_sha256`,
`embedding {model, dim, normalize}`, `bm25 {tokenizer, k1, b}`, `reranker: null`,
the counts, `chunk_digest` and `snapshot_manifest_sha256`. The reader follows the
pointer and falls back to the legacy `v2/index/lancedb` path for older data roots.

The index must not contain data that the public tree may not contain. Indexes
live under the local data root and are never committed.

## 5. Retrieval

1. **Normalize** traditional/simplified variants, full-width characters,
   whitespace and punctuation.
2. **Understand the question**: claim nature, domain, persona, jurisdiction,
   freshness and required slots (region, year, vessel type, gear).
3. **Ask for missing slots** when the answer depends on them. Do not guess a
   province or a year.
4. **Retrieve hybrid**: BM25 top 30 plus dense top 30, fused with weighted
   reciprocal-rank fusion. Keep the weights and `k` in configuration.
5. **Filter** by sensitivity ceiling, authority tier, level, jurisdiction,
   channel and effective date before ranking is finalized.
6. **Rerank** the fused top 20 with a BGE cross-encoder; keep the top 5–8.
7. **Expand** a winning child chunk to its parent section, then deduplicate by
   document and section.
8. **Build an evidence pack** with exact quotes, anchors, source dates, trust
   labels and an explicit note when a source is at or past its review date.
9. **Do not let a reference or web hit decide abstention.** The canonical lexical
   gate decides whether the question is in scope; external evidence only
   supplements a non-abstained answer.

## 6. Generation

- Answer only from the evidence pack. The model may paraphrase, but it may not
  add an uncited fact.
- Every factual sentence ends with a citation in a form the validator can
  resolve: `[DOC_ID §section p.PAGE]` for canonical text and
  `[WEB:domain:hash8] URL (抓取于 YYYY-MM-DD)` for web evidence.
- The validator checks that the cited document/page/section exists in the pack,
  that the quoted span supports the sentence, and that numbers, units and dates
  match the source. A sentence that fails is removed; if the core answer fails,
  the answer abstains.
- **Abstain** when the evidence does not contain the asked fact, when the only
  support is a different place/record, or when the question is out of scope.
- **Clarify** when a required slot is missing and a wrong assumption would be
  harmful.
- **Conflict**: show both statements with dates and authority. Canonical law,
  penalty and statistics win over web evidence; the web statement is labelled as
  a possible newer development, not as the answer.
- **Persona template**: for a captain or owner, prefer a short structure:
  conclusion, applicability, steps, documents, deadline, basis, caveat. Do not
  turn a procedure into a wall of legal text.
- The prompt version, model id, temperature, evidence hashes and output schema
  are recorded with the run.

**Implementation status (2026-11-12).** The product default is
`answer_v3/standard_arm.py`: it retrieves a 50-candidate hybrid pool, reranks to
8 with the BGE cross-encoder, expands to parent sections, builds a bounded
8-item / 12k-character evidence pack, asks for structured JSON (conclusion,
applicability, steps, documents, deadline, basis, caveat, soft gap, missing
slots, citations), then runs the citation/number/support validator and an
optional faithfulness self-check. Unsupported sentences are removed; a failed
conclusion abstains with a gap and a channel. Validated answers are cached by
question, persona, region/year, index version, prompt and config hashes, with an
optional embedding-similarity lookup; the cache is invalidated on index change
or TTL. The clause-dump arm remains for the Track A instrument and diagnostics.

## 7. Web evidence

- Web retrieval is triggered only by an explicit request, a freshness cue, an
  in-scope canonical abstention, or evidence older than the freshness window for
  the claim nature.
- SearXNG runs locally; queries and results are restricted to the allowlist.
  Non-allowlisted domains are discarded and logged.
- Each result becomes a `WebEvidence` record with URL, publisher, authority tier,
  fetched time, content hash, TTL and a short snippet. The full text stays in the
  local cache and is never republished.
- Web evidence is untrusted data. It is delimited in the prompt, never treated
  as an instruction, and never copied into the system prompt.
- TTL defaults: warning/status 7 days; rule 30 days; statistics/history 365 days.
  Expired evidence is not used.
- A web result may be promoted only by creating a candidate and passing the
  normal source admission review. No automatic ingest.

**Implementation status (2026-11-10).** The layer lives in
`src/scs_fkb/web_v2/` and is off by default: `SCS_FKB_WEB=off` and the API
default `web: "off"` make no network call. `auto` triggers on a freshness cue, a
cited source past its review or effective date, or an in-scope abstention. The
allowlist is `configs/web-sources.yaml` and is HTTPS-only. Leads are capped at
two per response, snippets at 300 characters, pages at 2 MB with a 10 s timeout
and 2 s spacing, and cache TTLs are 7/30/90/365 days by claim nature. Leads are
returned in `web_leads`, separate from `citations` and from `answer`; they never
decide abstention. The cache stays under the local data root and a promotion
draft is produced for the candidate queue instead of writing the register.

## 8. Evaluation

- Maintain a reviewed set of at least 120 questions across four personas:
  captain/crew, owner/operator, enforcement and extension. Split into dev and
  test; the test split is report-only and is not used for tuning.
- Each item records the question, persona, intent, region/year, gold answer,
  gold points, evidence spans, answerability and tags.
- Metrics: Recall@5, MRR, nDCG@10, citation resolution, citation precision,
  citation coverage, answer correctness, completeness, faithfulness, abstention
  accuracy, false-refusal rate, latency and cost.
- Use RAGAS-compatible metrics for faithfulness/answer relevancy/context
  precision/context recall and keep deterministic metrics for CI. Human review
  is authoritative; a model judge is supporting evidence.
- A regression gate compares the candidate index/answer path with the previous
  accepted baseline. A key metric drop above the agreed threshold blocks merge.
  The shipped gate is `scripts/eval_index_v2.py` (public set, Recall@5/MRR,
  `configs/eval-baseline.yaml`); the private 512 run remains the acceptance
  measure. RAGAS-style model-judged metrics are documented as `partial` in
  [rag-conformance.md](rag-conformance.md) and are not a merge gate.
- No evaluation question, gold answer or real-user question is copied into the
  FAQ, playbook or corpus content.

## 9. Operations

- **Weekly:** run source currency, watch, gap-driven web discovery, knowledge
  checks and a quick dev evaluation; write a report. A human reviews candidates,
  facts and playbooks; nothing is promoted automatically.
- **Quarterly:** re-date every source and fact, retire what is no longer
  supported, review the claim matrix and refresh the test set.
- **Monitoring:** index version, query latency, retrieval hit rate, abstention
  rate, web failure rate, citation-validation failure rate and feedback.
- **Rollback:** keep the previous index and code path; a failed build or a
  regression switches back without deleting data.
- **Incident:** a wrong answer with a citation is traced to the cited chunk,
  snapshot and source; the source is marked stale or retired and the answer path
  is re-evaluated.

## 10. Security and privacy

- `restricted` sources stay local and never reach an external model or the web.
  `internal` sources require owner approval before any external use.
- Web evidence is treated as hostile input: prompt injection, hidden text and
  links are not instructions.
- Secrets come from `.env`; logs record request metadata, not sensitive text.
- The public tree contains no data, index, run artifact, state database,
  credential or absolute path.
- The web service binds to localhost by default; any wider binding requires an
  API key and a documented decision.

## 11. Reproducibility

A run is reproducible when another maintainer can rerun the same commands
against the same source snapshots and index version. Each run records:

- code commit and index version;
- source-manifest hash and the ids of the sources used;
- parsing, chunking, embedding and reranking configuration;
- model identifiers and prompt version;
- commands, environment variables (names only) and timestamps;
- evaluation results and evidence hashes.

## 12. Compliance checklist

Before a release or a new index:

- [ ] Every active source has a known licence, sensitivity, tier, level and
      currency block.
- [ ] No candidate is treated as a source; no web result is cited as canonical.
- [ ] Every chunk has an anchor and a snapshot hash.
- [ ] The index manifest records the model and config hashes.
- [ ] Retrieval regression is not worse than the accepted baseline.
- [ ] Citation resolution is 100% on the reviewed set; abstention is measured.
- [ ] Restricted/internal content did not leave the machine.
- [ ] The public-tree check and the private release gate are clean.
- [ ] The project log records the change and the evidence.

## 13. References

- [Architecture](architecture.md)
- [Sources and authority](sources.md)
- [Data model](data-model.md)
- [Knowledge policy](knowledge-policy.md)
- [Evaluation](evaluation.md)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- [ISO/IEC 42001](https://www.iso.org/standard/42001)
- [W3C PROV-O](https://www.w3.org/TR/prov-o/)
- [FAIR Principles](https://www.go-fair.org/fair-principles/)
- [RAGAS](https://docs.ragas.io/)
