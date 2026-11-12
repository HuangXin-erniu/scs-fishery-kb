# 演示脚本

> **中文摘要**：五个演示场景，覆盖休渔时间、许可证换发、处罚、统计口径与越界拒答。每个场景给出
> 命令、预期答案形态与必须出现的引用；不写私有题面。演示前先确认索引版本与服务健康。

## 0. 准备

```bash
cd scs-fishery-kb
pip install -e ".[rag,service]"

export SCS_FKB_DATA_ROOT=/path/to/local/data
export SCS_FKB_RUN_ROOT=/path/to/local/runs
export SCS_FKB_WEB=off
export SCS_FKB_SUMMARY_MODE=model

# 索引版本（应为 67 份文档 / 2,797 块）
python - <<'PY'
import json, os
p = os.path.join(os.environ["SCS_FKB_DATA_ROOT"], "v2", "index", "current.json")
print(json.load(open(p)))
PY
```

服务演示时另开一个终端：

```bash
PYTHONPATH=src python -m scs_fkb serve
curl -s localhost:8765/healthz
```

## 1. 休渔时间（单点事实，应直接回答）

```bash
PYTHONPATH=src python -m scs_fkb ask "2026年南海区伏季休渔从什么时候开始？"
```

- 预期：结论给出 **5月1日12时至8月16日12时**，并说明适用海域（北纬26度30分至北纬12度）。
- 必须出现：`[POL-CLOS-015 §三、休渔时间]`。
- 失败迹象：只给“依据摘录”没有结论；引用指向别的文档；答案里出现“证据不足”。

## 2. 许可证换发（办理路径）

```bash
PYTHONPATH=src python -m scs_fkb ask "捕捞许可证到期后怎么换发？需要哪些材料？"
```

- 预期：给出换发条件与材料清单（申请表、船舶证书、照片等），并指向办理机关。
- 必须出现：捕捞许可相关条款的引用（如 `[POL-STD-010 …]` 或 `[POL-LAW-009 …]`）。
- 失败迹象：只复述法条不给路径；材料清单没有引用。

## 3. 违规处罚（数值必须可核对）

```bash
PYTHONPATH=src python -m scs_fkb ask "禁渔期出海捕捞会怎么处罚？"
```

- 预期：没收渔获物、违法所得和渔具，罚款区间与吊销许可证的条件。
- 必须出现：`[POL-LAW-009 §第七十八条]`。
- 失败迹象：罚款数字与法条不一致；只写“依法处罚”没有数值。

## 4. 统计口径（走统计通道，不是语料召回）

```bash
PYTHONPATH=src python -m scs_fkb ask "南海区海洋捕捞产量的年度趋势如何？"
```

- 预期：给出产量序列的方向与峰值年份，并标注年份与口径。
- 必须出现：统计年鉴或公报类引用（`STAT-ECO-*` / `STAT-YB-*`）。
- 失败迹象：把论文数字当成年鉴口径；不标年份。

## 5. 越界拒答（没有证据时必须拒答）

```bash
PYTHONPATH=src python -m scs_fkb ask "某渔场的历史渔汛期与主要经济鱼种是什么？"
```

- 预期：明确拒答或要求补充信息，并给出渠道行（属地渔业主管部门等）。
- 必须出现：拒答措辞（证据不足/请补充）**与** `渠道：` 行。
- 失败迹象：编出一个渔场答案；拒答但没有渠道。

## 6. 线上接口（可选）

```bash
curl -s localhost:8765/v1/query \
  -H 'Content-Type: application/json' \
  -d '{"question": "2026年南海区伏季休渔从什么时候开始？", "web": "off"}'
```

- 预期：JSON 含 `answer`、`citations`、`abstained`、`index_version`。
- 同一问题两次调用应返回相同的 `index_version`。

## 7. 演示记录表

| 场景 | 是否通过 | 引用 | 备注 |
|---|---|---|---|
| 1 休渔时间 | | | |
| 2 许可证换发 | | | |
| 3 违规处罚 | | | |
| 4 统计口径 | | | |
| 5 越界拒答 | | | |

评审时把这张表连同截图或终端输出一起归档。
