# ADR 0006: LlamaIndex, LanceDB and BGE as the RAG substrate

- Status: Accepted
- Date: 2026-11-06

## Context

The current pipeline is a small self-built stack: character-bigram BM25, a JSONL
vector file with brute-force cosine search, custom parsers and a deterministic
answer gate. It is well tested but has no reranker, no incremental index and no
standard ingestion or evaluation layer. The local machine is an 8 GB Apple
Silicon laptop with no Docker, no GPU and no database server. RAGFlow and Dify
would add several services and exceed the memory budget.

## Decision

- Use **LlamaIndex** for ingestion and query orchestration, with adapters for the
  existing governance, parsers, BM25 gate, citation validator and evaluation
  harness.
- Use **LanceDB** as the embedded vector store; it needs no server and supports
  metadata filtering and incremental writes.
- Use **BGE** models: `BAAI/bge-m3` for embeddings when the spike proves it fits
  within 6 GB RSS and a 2 s retrieval P95; otherwise keep
  `BAAI/bge-small-zh-v1.5`. Use `BAAI/bge-reranker-base` (or the int8 v2-m3
  variant) as a cross-encoder reranker.
- Keep the existing character-bigram BM25 and its calibrated lexical gate as a
  custom retriever behind the orchestration layer. Replacing a measured
  component with a less understood one is not a refactor goal.
- Pin dependency versions and keep a thin adapter around every third-party API
  so a version change does not reach the domain code.

## Consequences

- The public test suite must not download models or require LanceDB; unit tests
  use fixtures and synthetic vectors, and the real index is built locally.
- The BGE-M3 decision is conditional on the spike. The fallback is a documented
  outcome, not a failure.
- RAGFlow/Dify stay out of scope unless the environment changes to Docker with
  substantially more memory.

## References

- [Architecture](../architecture.md)
- [RAG standard](../rag-standard.md)
- [LlamaIndex](https://docs.llamaindex.ai/)
- [LanceDB](https://lancedb.github.io/lancedb/)
- [BGE-M3](https://huggingface.co/BAAI/bge-m3)
