# Term Source Batch 1 — 2026-11-06

> **中文摘要**：本批为 7 个草稿术语补充公开、A 级官方来源，先登记候选、抓取并哈希，再在 staging 做 v1/v2 A/B；门禁通过后才进入主库。7 个术语中 `统计范围` 已由既有 `TERM-131` 覆盖，因此 `TERM-130` 采用同来源的 `调查对象` 作为标准形，旧词保留为变体。所有来源均为 public，正文不进入公开树。

## 1. Sources

| Source | Term | Official page | Published | SHA-256 (short) | Evidence section |
|---|---|---|---|---|---|
| `POL-CREW-083` | 渔业职务船员证书 | [渔业船员管理办法](https://www.gov.cn/zhengce/2022-01/07/content_5721358.htm) | 2022-01-07 | `335092a951c3` | 第五条、第八条 |
| `POL-CODE-084` | 渔船编码 | [农业部公告第1100号](https://www.moa.gov.cn/govpublic/YYJ/201006/t20100606_1538517.htm) | 2008-10-31 | `9e4aa06c9817` | 二、证书证件修订主要内容 |
| `POL-ID-085` | 船舶识别号 | [船舶识别号管理规定](https://www.gov.cn/gongbao/content/2011/content_1786420.htm) | 2010-09-01 | `1eab91202ff5` | 第二条、第三条 |
| `POL-SANWU-086` | 涉渔“三无”船舶 | [亮剑2024典型案例](https://www.moa.gov.cn:10443/govpublic/YYJ/202505/t20250506_6473730.htm) | 2025-05-06 | `98709dce539f` | 五、福建漳州案 |
| `POL-FUEL-087` | 渔业成品油价格补助 | [财建〔2009〕1006号](https://www.gov.cn/gongbao/content/2010/content_1629134.htm) | 2009-12-31 | `40c4e44a0ece` | 第一条、第二条 |
| `POL-STAT-088` | 调查对象 | [渔业统计调查制度](https://www.stats.gov.cn/fw/bmdcxmsp/bmzd/202407/t20240719_1955798.html) | 2024-07-19 | `ee29cca7e24c` | 二、调查对象和统计范围 |
| `POL-RED-089` | 赤潮 | [赤潮灾害应急预案通知](https://www.gov.cn/zhengce/zhengceku/2021-08/07/content_5630005.htm) | 2021-07-09 | `f7a934965631` | 标题/正文 |

`POL-CODE-084` replaced the initially selected 2011 announcement 1562. The 1562 page introduced unrelated mortgage-registration material that made the staging v1 gate answer the out-of-scope loan question; the 1100 notice is narrowly about 渔船编码, contains no mortgage text, and preserves the 8/11 abstention baseline.

## 2. Term changes

| Term ID | Old standard | New standard | Variants |
|---|---|---|---|
| `TERM-030` | 渔业船员适任证书 | 渔业职务船员证书 | 渔业船员适任证书、职务船员证书、船员证书 |
| `TERM-084` | 渔船编码 | 渔船编码 | 渔船编号 |
| `TERM-085` | 船舶识别号 | 船舶识别号 | 船舶ID |
| `TERM-094` | 三无船 | 涉渔“三无”船舶 | 三无船、三无船舶 |
| `TERM-123` | 油价补贴 | 渔业成品油价格补助 | 油价补贴、燃油补贴 |
| `TERM-130` | 统计口径 | 调查对象 | 统计对象、统计口径 |
| `TERM-150` | 赤潮 | 赤潮 | 有害藻华 |

`TERM-131` already approved `统计范围`; `TERM-130` therefore uses the same official section's `调查对象` standard instead of creating a duplicate. The old `统计口径` remains a variant.

Result: 150 terms, **123 approved / 27 draft**, `terms check` 0 errors.

## 3. A/B gate

| Arm | Before | After | Gate |
|---|---|---|---|
| v1 docs/chunks/index | 28 / 785 / `20910f0964df` | 35 / 905 / `4d94e7c7f27c` | — |
| v1 dev | 19/19, MRR 0.6816 | 19/19, MRR 0.6842 | pass |
| v1 test | 12/12, MRR 0.8611 | 12/12, MRR 0.8611 | pass |
| v1 abstention | 8/11 | 8/11 | pass |
| v2 chunks/index | 785 / `23e933753e22` | 905 / `c25ddffea992` | — |
| v2 dev correctness | 0.8945 | 0.8945 | pass (≥0.8745) |
| v2 citation | 1.0000 | 1.0000 | pass |
| v2 context recall | 0.9750 | 0.9667 | pass (≥0.95) |
| v2 abstention | 0.9000 | 0.9000 | pass |
| Term exact evidence | — | 7/7 | pass |

The v2 test correctness moved from 0.6189 to 0.6319; test is report-only.

## 4. External store

After the term approvals, the separate external store was rebuilt:

- 487 → **494 documents**
- 543 → **550 chunks**
- chunk index `0b1ecdf229fe` → `9405a2f93585`
- dense index `6bdf2aad95935994` → `f1e02a628271a87b`
- 7/7 new terms retrieved in the top 5 for their standard forms.

## 5. Boundaries and review

- Raw HTML stays under `$SCS_FKB_DATA_ROOT/raw/`; the public tree carries only URL, publisher, hash and metadata.
- The seven candidates were accepted only after the staging gate; all seven now have `source_id`.
- `POL-SANWU-086` and `POL-RED-089` are official usage sources, not statutory definitions; their notes say so.
- The AI-assisted review remains subject to owner spot-check; no tag or release was created.

## 6. Batch 2 — 2026-11-06

| Source | Term | Official page | Published | SHA-256 (short) | Evidence |
|---|---|---|---|---|---|
| `POL-SANWU-086` (existing) | 非法捕捞水产品罪 | [亮剑2024典型案例](https://www.moa.gov.cn:10443/govpublic/YYJ/202505/t20250506_6473730.htm) | 2025-05-06 | `98709dce539f` | 六、江西鹰潭案 |
| `POL-CODE-084` (existing) | 型宽 | [农业部公告第1100号](https://www.moa.gov.cn/govpublic/YYJ/201006/t20100606_1538517.htm) | 2008-10-31 | `9e4aa06c9817` | 二、证书证件修订主要内容 |
| `POL-CONS-090` | 过度捕捞 | [海洋渔业资源衰退报道](https://www.moa.gov.cn/ztzl/ymksn/rmrbbd/202412/t20241205_6467503.htm) | 2024-12-05 | `d943c9d0b054` | 正文 |
| `POL-MIN-091` | 最小可捕规格 | [农业部通告〔2018〕3号](https://www.moa.gov.cn/govpublic/YYJ/201802/t20180213_6136943.htm) | 2018-02-12 | `af9068fe40c7` | 一、15种重要经济鱼类最小可捕规格 |
| `INT-SUS-092` | 兼捕 | [中国积极行动促进可持续渔业发展](https://www.un.org/oceancapacity/sites/www.un.org.oceancapacity/files/china.pdf) | undated | `3e67a3ce5fe9` | 一（二） |

- `TERM-048` was already supported by `POL-SANWU-086`; `TERM-088` changes standard from `船宽` to the official `型宽` and keeps `船宽` as a variant.
- `POL-CONS-090` and `POL-MIN-091` were initially captured as the 2006 action outline and the 64-page gazette PDF. Staging showed those broad pages answered the out-of-scope loan and voyage-definition questions, so the narrow 2024 news page and the standalone 2018 notice were substituted; both contain the exact terms and no loan/mortgage text.
- Batch 2 result: **128 approved / 22 draft**.

### Batch 2 A/B

| Arm | Before | After |
|---|---|---|
| v1 docs/chunks/index | 35 / 905 / `4d94e7c7f27c` | 38 / 920 / `0a8d928f2ad2` |
| v1 anchors / abstention | 31/31 / 8/11 | 31/31 / 8/11 |
| v2 chunks/index | 905 / `c25ddffea992` | 920 / `659a7a8c507e` |
| v2 dev / test / overall | 0.8945 / 0.6319 / 0.8069 | 0.8945 / 0.6327 / 0.8072 |
| v2 citation / recall / abstention | 1.0000 / 0.9667 / 0.9000 | 1.0000 / 0.9667 / 0.9000 |
| External store | 494 / 550 / `9405a2f93585` | 499 / 555 / `7c58c522ab5c` |

All five new terms retrieve in the external top 5.
