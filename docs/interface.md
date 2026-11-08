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
  "web": "auto"
}
```

`persona` is one of `captain`, `owner`, `enforcement`, `extension`, `general`.
`web` is `auto`, `on` or `off`; `auto` supplements only when the answer abstains
or the question carries a freshness cue. `region` and `year` are optional
filters. The question is limited to 500 characters.

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
  "playbook": null,
  "index_version": "v2",
  "answerability": "answerable",
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

Modes: `kb_only`, `kb_plus_web`, `web_only`, `clarify`, `abstain`. A `playbook`
block is a procedure view of approved facts; it never replaces the extractive
citations. `abstained=true` means the service did not find enough usable
evidence; `reason` is `weak_evidence`, `no_evidence`, `citation_invalid` or
`clarify`.

## 4. Citations

Corpus citations use `[doc_id p.N §section]` and resolve to a retrieved chunk.
Web citations use `[WEB:domain:hash8] URL (抓取于 YYYY-MM-DD)` and carry
`source_type: web` and the label `网络检索 · 未入知识库`. Web evidence never
overrides a canonical law or statistic; it is appended only as a supplement or
when the canonical layer abstains and the trigger allows it.

## 5. Auth and limits

If `SCS_FKB_API_KEY` is set, every `/v1` request must send `X-API-Key`. The UI is
local and does not bypass the API key for `/v1` calls. Questions are limited to
500 characters; the service returns at most 5 corpus hits and 2 web evidences.

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
default stays `extractive`. The arm retrieves up to eight clauses, asks the model
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
