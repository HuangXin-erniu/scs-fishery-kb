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

## 7. Batch 3 — 2026-11-06

| Source | Term | Official page | Published | SHA-256 (short) | Evidence |
|---|---|---|---|---|---|
| `INT-SUS-092` (existing) | 数据共享 | [UN sustainable fisheries report](https://www.un.org/oceancapacity/sites/www.un.org.oceancapacity/files/china.pdf) | undated | `3e67a3ce5fe9` | 正文 |
| `POL-OBS-072` (existing) | 海温 | registered source record | existing | `existing` | 第三十八条 |
| `POL-MARKET-093` | 渔获物上市交易 | [长江流域禁捕通知](https://www.gov.cn/zhengce/content/2020-07/08/content_5525124.htm) | 2020-07-08 | `99692398d8e4` | 禁止非法渔获物上市交易 |
| `INT-MSY-095` | 最大可持续产量 | [拓展渔业增收增效空间](http://www.jl.gov.cn/szfzt/jlssxsxnyxdh/zcyt/202411/t20241127_3324852.html) | 2024-11-27 | `7d7c3025626d` | 近海资源最大可持续产量 |
| `POL-SUB-094` | 休渔补贴 | [广东省渔业资源养护补贴政策实施方案](http://www.gd.gov.cn/attachment/0/601/601690/4832105.pdf) | 2025 | `86fb60a97f00` | 海洋伏季休渔补贴 |

- `TERM-145` changes standard from `海表温度` to the source's operational `海温`, keeping `海表温度` and `SST` as variants.
- `TERM-107` uses the official `渔获物上市交易` and keeps `渔获物交易` as a variant.
- `POL-MARKET-093` is a national State Council notice; `INT-MSY-095` is a national policy report reprinted by Jilin; `POL-SUB-094` is a provincial policy PDF.
- Batch 3 result: **133 approved / 17 draft**.

### Batch 3 A/B

| Arm | Before | After |
|---|---|---|
| v1 docs/chunks/index | 38 / 920 / `0a8d928f2ad2` | 41 / 971 / `43491719734d` |
| v1 anchors / abstention | 31/31 / 8/11 | 31/31 / 8/11 |
| v2 chunks/index | 920 / `659a7a8c507e` | 971 / `7d372c2b5f47` |
| v2 dev / test / overall | 0.8945 / 0.6327 / 0.8072 | 0.8945 / 0.6310 / 0.8066 |
| v2 citation / recall / abstention | 1.0000 / 0.9667 / 0.9000 | 1.0000 / 0.9667 / 0.9000 |
| External store | 499 / 555 / `7c58c522ab5c` | 504 / 560 / `c03a133b9f2e` |

All five new terms retrieve in the external top 5. The small v2 test/overall movement is report-only and within the agreed gate.

## 8. Batch 4 — 2026-11-06 (partial)

| Source | Term | Official page | SHA-256 (short) | Evidence |
|---|---|---|---|---|
| `POL-OCEAN-096` | 叶绿素a浓度 | [卫星遥感远洋渔场环境监测产品编目规范](http://www.lasac.cn/gfpdf/2020/5standard.pdf) | `f665e2da077d` | 渔场环境要素编码表 |
| `POL-OCEAN-096` | 海面风场 | same | same | 渔场环境要素编码表 |
| `POL-OCEAN-096` | 有效波高 | same | same | 渔场环境要素编码表 |
| `STD-MDR-098` (candidate only) | 数据元 | [GB/T 18391.3-2009](http://spec.nstl.gov.cn/metadata/download/upload/attpdf/4cc36296-b010-4fe3-ae23-d4414b36967f.pdf) | `d0bd827f0d75` | 术语和定义 |
| `STD-MDR-098` (candidate only) | 元数据 | same | same | 术语和定义 |

- Three ocean terms were approved from `POL-OCEAN-096`.
- `数据元` and `元数据` stayed **draft**: the 89-page GB/T copy caused Q-M06 (voyage/port definitions) to be answered from generic metadata chunks, dropping v1 abstention to 7/11. The candidate remains open; no source record or pipeline document was added.
- Batch 4 result: **136 approved / 14 draft**.

### Batch 4 A/B (with metadata standard excluded)

| Arm | Before | After |
|---|---|---|
| v1 docs/chunks/index | 41 / 971 / `43491719734d` | 42 / 1014 / `f7a244373e77` |
| v1 anchors / abstention | 31/31 / 8/11 | 31/31 / 8/11 |
| v2 chunks/index | 971 / `7d372c2b5f47` | 1014 / `d007984ae168` |
| v2 dev / test / overall | 0.8945 / 0.6310 / 0.8066 | 0.8945 / 0.6161 / 0.8017 |
| v2 citation / recall / abstention | 1.0000 / 0.9667 / 0.9000 | 1.0000 / 0.9667 / 0.9000 |
| External store | 504 / 560 / `c03a133b9f2e` | 507 / 563 / `458aad366fe1` |

The test split fell 1.49pp; it is report-only under the agreed gate. Dev correctness, citation, recall and abstention held.
