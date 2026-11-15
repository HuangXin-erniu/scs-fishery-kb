# Architecture Decision Records

Short records of decisions that shape the project. Each record uses the same
structure: status, date, context, decision, consequences and references.

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-no-versioned-releases.md) | No versioned releases | Accepted |
| [0002](0002-bilingual-documentation.md) | Bilingual documentation | Accepted |
| [0003](0003-data-outside-repository.md) | Data and run artifacts outside the repository | Accepted |
| [0004](0004-public-private-boundary.md) | Public/private boundary | Accepted |
| [0005](0005-two-plane-evidence.md) | Canonical and ephemeral evidence planes | Accepted |
| [0006](0006-llamaindex-lancedb-bge.md) | LlamaIndex, LanceDB and BGE substrate | Accepted |
| [0008](0008-playbooks-and-terms.md) | Playbooks and terms internalisation | Accepted |
| [0009](0009-standard-rag-answer-pipeline.md) | Standard RAG answer pipeline as the default | Proposed |
| [0010](0010-dual-track-evaluation.md) | Dual-track evaluation with industry-standard metrics | Proposed |
| [0011](0011-semi-automatic-update-loop.md) | Semi-automatic update loop with a provisional tier | Proposed |
| [0012](0012-practical-sources-and-freshness.md) | Practical sources and freshness for crew-facing knowledge | Proposed |
| [0013](0013-source-schema-v5.md) | Source schema v5 | Proposed |

## Adding a record

1. Copy the structure of an existing record.
2. Use the next four-digit number.
3. Open a pull request; the project owner approves.
4. Link the record from the relevant document.
