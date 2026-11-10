# Operations: Weekly Checks and Source Admission

> **中文摘要**：本文件定义更新闭环：每周只读巡检（时效、watch、候选、事实、术语、playbook、缺口）→ 人工复核 → 抓取与登记 → 重建索引 → 回归 → 记录。巡检不下载、不入库、不自动晋升；只有人能决定一个新页面是否成为来源。

## 1. Invariants

- The weekly cycle is **read-only**: no download into the corpus, no register edit, no index rebuild, no candidate promotion.
- A changed page is a prompt, not an update. A web result is a lead, not evidence.
- Only a human review may accept a candidate. Acceptance is followed by the normal capture, hash, register, rebuild and regression steps below.
- Run artifacts stay under `$SCS_FKB_RUN_ROOT`; source snapshots stay under `$SCS_FKB_DATA_ROOT`. Nothing in this file is published.
- The 512-question instrument and its document map are frozen. A weekly cycle never changes them.

## 2. Weekly cycle (one command)

```bash
export SCS_FKB_DATA_ROOT=/path/to/data
export SCS_FKB_RUN_ROOT=/path/to/runs
export PYTHONPATH=src

# 1. Hard gate: currency, watch coverage, candidate queue (offline)
python scripts/check_sources.py --today "$(date +%F)"

# 2. Read-only report: registry, currency, watch replay, candidates, facts,
#    playbooks, terms, index manifest and the local gap summary
python scripts/weekly_report.py --today "$(date +%F)" --task-id weekly
```

The report is written to `$SCS_FKB_RUN_ROOT/weekly/weekly-YYYY-MM-DD.md`. It never
writes anywhere else.

To populate the gap section, run the service with the opt-in local query log:

```bash
SCS_FKB_LOG_QUERIES=on python -m scs_fkb serve
```

The log is `$SCS_FKB_RUN_ROOT/queries/YYYY-MM-DD.jsonl` with `request_id`,
timestamp, question, mode, reason, abstained and latency. It never stores answers,
citations or personal data, and it is off by default.

## 3. Watch list

```bash
# replay the recorded statuses, no socket
python scripts/watch_sources.py --offline --task-id weekly

# live check; record the current hashes under $SCS_FKB_DATA_ROOT/watch/baseline.json
python scripts/watch_sources.py --baseline --task-id weekly

# changed or unbaselined pages become candidate drafts under the run root only
python scripts/watch_sources.py --propose --task-id weekly
```

- `configs/source-watch.yaml` lists the curated authoritative pages with tier,
  publisher and cadence.
- Recorded hashes are the 2026-11-02 baseline; `--baseline` records the current
  hashes locally so later runs compare against today rather than a stale file.
- `--propose` writes `candidates-proposed.yaml` next to the watch report. It never
  edits `configs/corpus.yaml` or `configs/candidates.yaml`.
- Some networks intercept TLS. Set `SCS_FKB_CA_BUNDLE` to a bundle exported from
  the system keychain; the checker never disables verification.

## 4. Candidate admission (human-gated)

1. **Review.** Read the changed page and the proposed candidate. Reject a repost,
   news item, login-only page or a page with no licence.
2. **Decide.** Record the decision and open a task. The candidate record carries
   `watch_ref`, `first_seen`, `expires_at` and `reason` (`changed`, `gap`, `new` or
   `supersede`).
3. **Capture.** Use `scripts/capture_source.py --url ... --source-id ...`; it
   refuses non-HTTPS URLs and hosts outside the official allowlist, writes the
   snapshot under the data root and prints the provenance block.
4. **Register.** Add the entry to `configs/corpus.yaml` with publisher, tier,
   class, licence, sensitivity, `provenance`, `effective`, `quality` and a
   `currency.review_due` inside the cadence cap. Set `supersedes` when replacing a
   version; never delete the older entry.
5. **Rebuild.** `rm -f data/v2/processed/*.jsonl && PYTHONPATH=src python
   scripts/build_v2.py && PYTHONPATH=src python scripts/build_index_v2.py`.
6. **Gate.** `python scripts/check_sources.py --today ...`, then the retrieval
   regression (`scripts/eval_index_v2.py`) and the 512 acceptance smoke with
   `SCS_FKB_WEB=off`.
7. **Internalise.** Re-run `scripts/build_provision_facts.py` for draft facts,
   `scripts/audit_term_coverage.py`, `scripts/check_playbooks.py` and the weekly
   report. Draft facts and terms need a human review before approval.
8. **Record.** Update the project log and, when the change is user-visible, the
   README status. Commit, review, merge and close.

Nothing in steps 1–8 happens automatically.

## 5. Quarterly review

- Re-date every active source (`currency.as_of`, `review_due`) within its cadence
  cap, retire what is no longer supported and resolve every open candidate.
- Re-check facts whose `review_due` has passed and playbooks marked `stale`.
- The next scheduled quarterly review is **2027-02-02**.

## 6. Rollback

- Keep the previous index and the previous `main` commit. A failed rebuild or a
  regression restores the previous index and reverts the merge; data is never
  deleted.
- A failed source admission reverts the register entry and leaves the snapshot in
  place for audit.
- Watch baselines are local files; deleting the baseline only forces
  `unbaselined` on the next live run, it never changes a source.

## 7. Roles

- **Human reviewer:** decides admission, approves facts and terms, resolves a
  changed page, and signs off the quarterly review.
- **Agent executor:** runs the read-only checks, prepares candidate drafts,
  captures after a decision, rebuilds and runs the gates. Never promotes on its
  own.
