# RAG Conformance Matrix

> **中文摘要**：逐条对照 [rag-standard.md](rag-standard.md) 的 12 节，记录实现位置、状态（met/partial/gap）和剩余缺口。矩阵是声明，不是认证；标 partial 的条目在右列写清原因。

The standard was adopted on 2026-11-06. This matrix records where each section is
implemented and what is still missing. `scripts/check_rag_conformance.py`
enforces the machine-checkable subset (manifest fields, pointer, allowlist, web
default, thresholds, no tags).

| § | Requirement | Implementation | Status | Remaining gap |
|---|---|---|---|---|
| §1 | Source authority, licence, currency and supersession | `configs/corpus.yaml`, `src/scs_fkb/registry.py`, `scripts/check_sources.py`, [sources.md](sources.md) | met | None |
| §2 | Snapshot first, adapter parsing, anchors, quarantine, OCR opt-in | `src/scs_fkb/ingest_v2/`, `src/scs_fkb/parsers/`, `docs/corpus.md` OCR note | partial | Docling is optional and used only when installed; most PDFs use the PyMuPDF adapter |
| §3 | Hierarchical chunking with article/row anchors | `src/scs_fkb/ingest_v2/chunking.py`, 2,797 chunks in the current index | met | None |
| §4 | Dense + lexical index, metadata, manifest, atomic switch | `src/scs_fkb/index_v2/store.py`, `scripts/build_index_v2.py` | met | Version directories with an atomic `current.json` pointer and rollback were added on 2026-11-10 |
| §5 | Hybrid retrieval, filters, rerank, expansion | `src/scs_fkb/retrieve_v2/`, BM25 + BGE + RRF | partial | Rerank is available per request or via `SCS_FKB_RERANK`; the 2026-11-10 public A/B measured recall@5 0.8298 → 0.8085 and p95 22 ms → 1947 ms, so it stays off by default |
| §6 | Evidence-only generation, citation validation, abstention | `src/scs_fkb/answer_v3/standard_arm.py`, `evidence.py`, `cache.py`, `src/scs_fkb/service_v2/answer.py` | met | The product default is the standard arm; the clause-dump arm remains for Track A |
| §7 | Controlled web evidence | `src/scs_fkb/web_v2/`, `configs/web-sources.yaml` | met | Off by default; leads never enter the answer; no auto-ingest |
| §8 | Evaluation: reviewed set, RAGAS-compatible metrics, regression gate | `scripts/eval_accept.py` (private 512), `scripts/eval_public.py`, `scripts/eval_index_v2.py`, `scripts/ragas_runner.py`, Track B dataset | partial | RAGAS 0.4.3 runs in an isolated venv and Track B is built (300/200/100); the gate is not armed until `gate_ready` is true |
| §9 | Weekly/quarterly operations and rollback | [operations.md](operations.md), `scripts/weekly_report.py`, `scripts/watch_sources.py` | met | None |
| §10 | Security: sensitivity, hostile web input, localhost, no secrets | `docs/data-policy.md`, `src/scs_fkb/web_v2/fetch.py`, `service_v2/api.py` | met | None |
| §11 | Reproducibility: commit, manifest hashes, model and prompt ids | `v2/index/versions/<id>/manifest.json`, `v2/index/current.json` | met | `code_commit` and `pipeline_config_sha256` were added on 2026-11-10 |
| §12 | Compliance checklist before release | `scripts/check_public_tree.py`, private release gate, `scripts/check_rag_conformance.py` | met | None |

## Notes

- Status values: `met` means the requirement is implemented and exercised by a
  test or a recorded run; `partial` means it is implemented but one stated
  element is deliberately not shipped; `gap` would mean it is missing.
- The private 512-question instrument and its document map remain frozen and are
  never copied into this repository.
- The matrix is updated with the project log when a partial row changes.
