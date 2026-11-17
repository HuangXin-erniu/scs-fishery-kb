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

## Human sample

```bash
python scripts/sample_audit.py --answers ... --ledger ... --out ... --limit 150
```

The sampler always includes all S1 IDs and all gap/refusal IDs, then fills fixed
theme quotas. `wilson(143, 150) = 0.9068` is the lower bound used by the gate.
A 30-row double annotation computes Cohen's kappa; below 0.6 the rubric is
revised before the 150-row review proceeds.

## Gate

Acceptance requires all of:

- blind pass rate ≥ 0.90 and Wilson lower bound ≥ 0.85;
- S1 = 0;
- D1/D3/D4 = 0;
- citation existence = 100%;
- D7 support ≥ 0.95;
- D5 = 0;
- as-of declaration ≥ 0.95.

The older aggregate metrics remain diagnostic/regression only.

## Corpus checks

`scripts/audit_corpus.py` writes `corpus-title.csv`, `corpus-level.csv`,
`corpus-currency.csv`, `corpus-version.csv`, and `corpus-quality.csv`. It reads
the current manifest-derived registry, not the stale 131-document count.
