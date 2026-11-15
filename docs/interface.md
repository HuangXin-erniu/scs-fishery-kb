# Answer Service Interface

> **中文摘要**：本文件定义本地 v2 问答服务的 `/v1` 合同。服务默认绑定 `127.0.0.1`，单机单用户，不是多租户部署。问题先查知识库；只有显式开启或触发条件满足时才补充网络证据，并标注“网络检索 · 未入知识库”。每个事实句必须带可解析引用；证据不足返回 `abstain` 或 `clarify`。设置 `SCS_FKB_API_KEY` 后所有 `/v1` 请求必须带 `X-API-Key`。反馈写入运行目录的 JSONL，不进入公开树。

## 1. Scope

The service is a local, single-user interface over the v2 retrieval and knowledge
layers. It is not a public or multi-tenant deployment. The v1 CLI and extractive
answer path are unchanged; this service is an additional surface.

Default bind: `127.0.0.1:8765`.

## 2. Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/query` | Answer a question |
| GET | `/v1/sources` | List registered sources |
| GET | `/v1/playbooks` | List approved playbooks |
| POST | `/v1/feedback` | Record helpfulness |
| GET | `/healthz` | Liveness |
| GET | `/readyz` | Readiness and index version |
| GET | `/` | Server-rendered Web UI |
| POST | `/` | Web UI query form |

## 3. Query

Request:

```json
{
  "question": "2026年南海区伏季休渔从什么时候开始？",
  "persona": "captain",
  "region": "guangdong",
  "year": 2026,
  "web": "auto",
  "short": false,
  "rerank": null,
  "mode": "standard",
  "max_chars": 12000
}
```

`persona` is one of `captain`, `owner`, `enforcement`, `extension`, `general`.
`region` and `year` are optional filters. The question is limited to 500
characters. `mode` overrides the configured answer arm for one request
(`standard` is the product default; `short`, `full`, `dump`, `llm`, `quotes`,
`facet`, `extractive` remain available). `max_chars` bounds the standard arm's
evidence pack (1000–20000, default 12000).

`short` selects the optional short-answer arm (at most 300 Chinese characters,
conclusion → basis → deadline/documents, every claim cited). It defaults to
false; a failed validation falls back to the deterministic path, which is not
capped at 300 characters. Citations are checked per rendered line, so one
trailing `[DOC §section]` covers the clauses a line joins with `；`; an answer
that is only too long is truncated at the last sentence boundary inside the cap
and re-validated. The arm reads at most `MAX_HITS` (8) retrieved chunks, so a
wider retrieval window does not change its evidence. Abstention on unsupported
questions requires `SCS_FKB_VERIFY_ANSWERS=on`; without it the arm answers
instead of refusing. `SCS_FKB_SHORT_DIAG=<path>` records one content-free line
per short-arm failure for diagnosis. `rerank` is
`true`, `false` or `null` (use `SCS_FKB_RERANK`, default off) and enables the
cross-encoder for this request.

`web` is `off` (default), `auto` or `on`. `off` performs no network call and is
the only mode used by the acceptance instrument. `on` always queries the
allowlisted search backend. `auto` queries only when the question carries a
freshness cue, a cited source is past its review or effective date, or the
in-scope answer abstains. A web result is a lead, not evidence: it is returned in
`web_leads`, never in `citations`, never in `answer`, and it never changes the
abstention decision. Nothing is ingested automatically.

Response:

```json
{
  "request_id": "REQ-...",
  "answer": "...",
  "citations": [
    {
      "doc_id": "POL-CLOS-015",
      "title": "POL-CLOS-015",
      "page": 3,
      "section": "三、休渔时间",
      "snippet": "5月1日12时至8月16日12时",
      "score": 0.03,
      "url": "",
      "retrieved_at": "",
      "source_type": "corpus",
      "label": ""
    }
  ],
  "abstained": false,
  "reason": "ok",
  "mode": "kb_only",
  "used_web": false,
  "web_leads": [],
  "playbook": null,
  "index_version": "v2",
  "answerability": "answerable",
  "summary_source": "model",
  "conclusion": "（三）北纬26度30分至北纬12度的东海和南海海域为5月1日12时至8月16日12时。",
  "conditions": [],
  "gap": [],
  "channel": [],
  "as_of": {
    "declared": "按农业农村部关于调整海洋伏季休渔制度的通告（2023年版）",
    "basis": "question_time_cue",
    "versions": [
      {"doc_id": "POL-CLOS-015", "document_no": "", "effective": "2023-05-01", "title": "农业农村部关于调整海洋伏季休渔制度的通告"}
    ]
  },
  "numbers": [
    {"value": "26", "unit": "度", "basis": "南海海区", "location": ""}
  ],
  "latency_ms": 24,
  "disclaimer": "以官方发布文本为准；本服务不构成法律意见。"
}
```

Answer contract (v3, default; `SCS_FKB_ANSWER_CONTRACT=v1` restores the old
shape): `answerability` is `answerable`, `partial` or `abstain`. The answer text
is 结论 → 适用条件 → 版本 → 数值与口径 → 缺口 → 渠道 → 依据摘录, so the first line
is always a cited conclusion. `partial` names the gap and at least one channel;
`abstain` carries no numeric or document-number claim. `as_of` names the
governing version when the question says 今年/现在 or names a year. `numbers`
lists the numeric anchors with their basis; an empty list on a numeric question
means the value was missing from the evidence and the answer says so.

`summary_source` says where the conclusion and points came from: `model` is a
model-written summary that passed the citation, number and support checks,
`fallback` is the deterministic path because a model draft was dropped by those
checks, and `deterministic` means no model was attempted
(`SCS_FKB_SUMMARY_MODE=off`, no endpoint, or no clauses). It is reported so a
silent fallback is never counted as a model answer; the spot-check worksheet
carries it per row and `score` reports the fallback rate.

Modes: `kb_only`, `kb_plus_web`, `clarify`, `abstain`. `kb_plus_web` means the
canonical answer is unchanged and one or two labelled web leads were attached.
A `playbook` block is a procedure view of approved facts; it never replaces the
extractive citations. `abstained=true` means the service did not find enough usable
evidence; `reason` is `weak_evidence`, `no_evidence`, `citation_invalid` or
`clarify`.

## 4. Citations

Corpus citations use `[doc_id p.N §section]` and resolve to a retrieved chunk.
They are the only entries in `citations`; `citations_total` counts deduplicated
documents, capped at 20 displayed entries.

Web leads use `[WEB:domain:hash8] URL (抓取于 YYYY-MM-DD)` in their `citation`
field and carry the label `网络检索 · 未入知识库`. A lead is shown with its
publisher, authority tier, fetch date and snippet. It never overrides a
canonical law or statistic and never turns an abstention into an answer; for an
abstained response the leads are labelled as leads that cannot support a
conclusion.

## 5. Auth and limits

If `SCS_FKB_API_KEY` is set, every `/v1` request must send `X-API-Key`. The UI is
local and does not bypass the API key for `/v1` calls. Questions are limited to
500 characters; the service returns at most 20 deduplicated corpus citations and
2 web leads. Web fetching is restricted to the allowlist in
`configs/web-sources.yaml` (HTTPS only, 2 MB per page, 10 s timeout, 2 s spacing,
7/30/90/365-day cache TTLs).

## 5.1 UI routes

The service also renders a worker-facing knowledge surface, server-side and
mobile-first:

| Route | Content |
|---|---|
| `/kb` | Task cards (approved playbooks), sourced FAQ, plain terms, numeric quick reference and what-changed, with `persona` and `q` filters |
| `/kb/playbooks/{id}` | One task card: steps, documents, deadlines, penalties and sources |
| `POST /kb/feedback` | Local vote on a task card or FAQ: `item_id`, `kind`, `helpful`, optional `comment` |

Every displayed item names its document and section. These routes are
presentation only: they do not change `/v1/query`, the answer text or the
abstention decision. `/kb/feedback` appends one row to
`$SCS_FKB_RUN_ROOT/feedback.jsonl` with `source: "kb"` and redirects back to
`/kb`; it never stores an answer or citation.

## 6. Feedback

`POST /v1/feedback` accepts `request_id`, `helpful`, optional `comment` and
optional `question`. Rows are appended to `$SCS_FKB_RUN_ROOT/feedback.jsonl`;
when the run root is unset, a temporary directory is used. Feedback is not
written to the public tree and is not used for automatic training.

## 7. Errors

| Status | Meaning |
|---|---|
| 401 | Missing or invalid `X-API-Key` |
| 422 | Invalid request body or form data |
| 500 | Unexpected service error |

## 8. Versioning

The path carries `v1`; the service identifies itself as `scs-fkb-v2`. The
contract is local and may change with the project log; there is no semantic
version tag or release.

### LLM composition arm (2026-11-08)

`SCS_FKB_ANSWER_MODE=llm` switches the answer path to the LLM composition arm; the
default is the deterministic dump arm, and `extractive` remains available. The arm retrieves up to eight clauses, asks the model
for a conclusion-first answer with per-sentence citations, and then enforces three
hard checks before returning anything:

1. every citation resolves to a retrieved clause (document, page or section);
2. every number in a cited sentence appears verbatim in the cited evidence;
3. a support verifier confirms that each conclusion is backed by the cited
   evidence.

A failed check triggers one repair pass; a second failure returns the gap form
(缺口 + 渠道) instead of an answer. If the LLM is not configured or the call
fails, the service falls back to the extractive path. Both arms share the same v3
response contract, so `as_of`, `numeric` and `channel` fields are still produced
by `compose()`.
