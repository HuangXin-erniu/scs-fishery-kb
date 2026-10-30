# Method

- Status: planned. The `v0.1.0-alpha` baseline contains no retrieval or service code.
- Scope: knowledge-layer corpus, retrieval-augmented answers, citations, abstention and evaluation.

## 1. Pipeline

```text
local data/raw
  → source register (licence / sensitivity / version / hash)
  → parsing and OCR
  → structure-aware chunking and indicator extraction
  → local embeddings + BM25 index
  → query rewriting and hybrid retrieval
  → metadata filtering and optional reranking
  → evidence-only answer with citations / abstention
  → evaluation and reporting
```

## 2. Source registration

Every source must be registered in [configs/corpus.yaml](../configs/corpus.yaml) before parsing. A source with an unknown licence or sensitivity is held. The register records publisher, year, type, format, location, licence, sensitivity, status, priority, volume, update frequency and hash.

## 3. Parsing and chunking

- PDF text layer first; Word, Excel and HTML supported.
- Scanned pages may use OCR; OCR output carries page and confidence metadata.
- Chunking is section-aware, 512–800 tokens with 10–15% overlap.
- Each chunk keeps `doc_id`, `page`, `section`, `table_id`, `char_start` and `char_end`.
- Complex tables that cannot be extracted reliably are marked low quality and quarantined.

## 4. Indexing

- Local text embeddings from a compact Chinese model.
- BM25 keyword index with Chinese tokenisation.
- Embedded vector store with metadata filtering.
- Index and manifest carry a version for traceability.
- Indexes live under local `data/index/` and are not committed.

## 5. Retrieval

- Query rewriting normalises terminology, years, sea areas and operation types.
- Hybrid retrieval combines BM25 and dense results with reciprocal-rank fusion.
- Metadata filters apply source, year, sea area, document type and sensitivity.
- Sensitivity filtering happens before retrieval results reach the model.
- Reranking is optional and depends on measured benefit and local resources.

## 6. Answers, citations and abstention

- The model receives only the retrieved evidence.
- Answers must state a conclusion first, then the supporting evidence.
- Each factual claim carries a citation in the form `[doc_id p.page]` or `[doc_id §section]`.
- Citations are validated against the retrieved chunks.
- If evidence is insufficient, out of scope or disallowed by sensitivity, the system abstains explicitly.
- The system must not fabricate a source, page or quotation.

## 7. Evaluation

- Retrieval: Recall@k, MRR and Hit@k.
- Citation: precision, coverage and invalid-citation rate.
- Answer: correctness, faithfulness and completeness on a reviewed question set.
- Abstention: out-of-scope refusal accuracy and false-refusal rate.
- Baselines: BM25-only, dense-only and hybrid.
- Human review is authoritative for answer correctness.

## 8. Reproducibility and locality

- Configuration is file-based; secrets come from environment variables.
- Runs record commands, model identifiers, index versions and evidence hashes.
- Data and run artifacts stay under local `data/` and `runs/`; neither is committed.
- The public repository contains code, configuration, documentation and tests only.

## 9. Next milestone

The first implementation milestone builds the minimal pipeline on two or three public documents, then evaluates retrieval and citation quality before expanding the corpus. See [roadmap.md](roadmap.md).
