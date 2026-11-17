# Answer-defect audit (SCS-FKB)

This document defines the **single audited object** and the D1–D11 fingerprint
checks. It is deliberately separate from the acceptance aggregate metrics: a
100 KB dump block with `依据摘录` must never be scored as a delivered answer.

## Audited object

`audit-answers.jsonl` is the only input to the scanner. Each record contains:

- `visible_answer`: what a user sees;
- `citations` / `evidence_ids`: pointers for support checks;
- `abstained`, `reason`, `pipeline_stage`;
- `source`, `theme`, `gap_status`, `trace_ref`;
- `index_version`, `commit`, `prompt_version`.

The dump remains a trace only. `scripts/build_audit_artifact.py` supports:

```bash
# already delivered blind/recheck answers
python scripts/build_audit_artifact.py --mode reviewed --out "$RUN/AUDIT/audit-answers-reviewed.jsonl"

# 512 questions through the product path (not the dump arm)
python scripts/build_audit_artifact.py --mode service --out "$RUN/AUDIT/audit-answers-512.jsonl"
```

`--mode dump-trimmed` exists only for historical comparison and is marked
`answer_kind=dump_trimmed`; its `原文：` findings are not product findings.

The product run is one question per worker request. `--timeout 240` is the
per-question wall clock; a blocked worker is killed and restarted, and
`--resume` keeps completed ids. Each LLM call writes a metadata-only trace
(`<out>.llm-trace.jsonl`: stage, prompt size, elapsed, outcome) when
`SCS_FKB_LLM_TRACE` is set. No prompt text or key is written.

## Detectors

Thresholds live in `configs/audit.yaml`; implementation is
`src/scs_fkb/audit/detectors.py`.

| ID | Meaning | Severity |
|---|---|---|
| D1 | verbatim dump / OCR markers | S2 |
| D2 | scope (`口径：`) entity mismatch | S2 |
| D3 | truncation or unbalanced brackets | S2 |
| D4 | internal system phrase leaked | S2 |
| D5 | abstained while evidence covers the question | S1 |
| D6 | sub-question entity omitted | S2 |
| D7 | cited chunk does not support the claim | S1 |
| D8 | national/current assertion against province/expired chunk | S1 |
| D9 | numeric claim absent from cited chunks | S1 |
| D10 | question entity vs answer entity mismatch | S1 |
| D11 | versioned citation without as-of statement | S3 |

Each detector has five bad and five good canaries in
`tests/fixtures/audit/` and is executed by `tests/test_audit_detectors.py` and
`tests/test_audit_canary_d5_d11.py`.

## Run

```bash
export SCS_FKB_DATA_ROOT=/path/to/private/data
export SCS_FKB_RUN_ROOT=/path/to/private/runs
python scripts/run_audit.py \
  --answers "$SCS_FKB_RUN_ROOT/AUDIT/audit-answers-512.jsonl" \
  --out-dir "$SCS_FKB_RUN_ROOT/AUDIT/run-512"
```

Outputs:

- `defect-ledger.csv`;
- `defect-distribution.csv`;
- `stage-attribution.csv`.

`scripts/audit_corpus.py` writes the five corpus checks. `scripts/audit_gate.py`
reads an artifact and its ledger and writes `gate.json`; it deliberately does
not decide acceptance.

## Human sample

```bash
python scripts/sample_audit.py --answers ... --ledger ... --out ... --limit 150
```

The sampler always includes all S1 IDs and all gap/refusal IDs, then fills fixed
theme quotas, excluding ids already used in earlier reviews. `wilson(143, 150)
= 0.9068` is the lower bound used by the gate; a 137/150 pass reaches about
0.858. A 30-row double annotation computes Cohen's kappa; below 0.6 the rubric
is revised before the 150-row review proceeds. The AI pre-label is advisory and
never fills the human columns.

Before any batch is used for a pass rate, run
`scripts/check_answer_consistency.py --answers <file> --out <json>`; a non-empty
`dup_answer` means two ids received the same body and the whole batch is invalid.
`scripts/validate_human_review.py` checks that every row is filled, rejects
unknown verdicts and computes the blind-pass rate with its Wilson lower bound;
it exits non-zero until the sheet is complete and above both lines.

The acceptance spot check is separate: `scripts/draw_expert_sample.py` draws a
fresh 30-question blind pack (excluding the 150-row sample and earlier review
sets), and `scripts/score_expert_sample.py` scores the signed worksheet against
citation >=0.95, conclusion >=0.85 and refusal >=0.90.

## Gate

Acceptance requires all of:

- blind pass rate ≥ 0.90 and Wilson lower bound ≥ 0.85;
- S1 = 0;
- D1/D3/D4 = 0;
- citation existence = 100%;
- D7 support ≥ 0.95;
- D5 = 0;
- as-of declaration ≥ 0.95.

The older aggregate metrics remain diagnostic/regression only. A signed expert
worksheet is the only human-judged layer; a model score is never reported as
human review.

## Corpus checks

`scripts/audit_corpus.py` writes `corpus-title.csv`, `corpus-level.csv`,
`corpus-currency.csv`, `corpus-version.csv`, and `corpus-quality.csv`. It reads
the current manifest-derived registry, not the stale 131-document count.

## Open-source route

The deterministic D1–D11 layer stays in-repo because the gate must be fast,
auditable and free of judge variance. The model-judged layer uses
[RAGAS](https://github.com/explodinggradients/ragas) 0.4.3 (faithfulness,
answer correctness, context precision/recall) in the isolated `venv-ragas`; its
scores are reported as model-judged, never as human review. D7 borrows the
claim-level orientation of
[RAGChecker](https://github.com/amazon-science/RAGChecker) but not its
dependency stack. [DeepEval](https://github.com/confident-ai/deepeval) and
[promptfoo](https://www.promptfoo.dev/docs/intro/) were evaluated and not added:
they would duplicate the judge or the existing pytest canaries.
[TruLens](https://github.com/truera/trulens) and
[Arize Phoenix](https://github.com/Arize-ai/phoenix) contributed the span model
only; the client writes a lightweight stage trace instead of running a tracing
backend.
