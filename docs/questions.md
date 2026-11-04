# Evaluation Questions (Draft)

- Status: **all three batches reviewed**. Decisions and gold answer points were approved by the project owner on 2026-11-04.
- 24 questions: 12 for vessel operators and 12 for fisheries administration.
- Gold answer points live in [configs/eval.yaml](../configs/eval.yaml) under `gold`; the table below stays the question bank.

## How to use this draft

1. Review each question with a domain expert: is it a real task, and are the sea area, year, vessel type and operation type specific enough?
2. Remove questions that cannot be answered from the registered knowledge layer.
3. Add gold answers and evidence (`doc_id`, page or section) only when a reliable source exists.
4. Mark unanswerable questions as abstention tests; do not invent answers.
5. Re-check the set before using it for evaluation.

## Questions for vessel operators and captains

| ID | Question (English) | Original (Chinese) | Type | Expected evidence | Notes |
|---|---|---|---|---|---|
| Q-E01 | What are the start and end dates and the scope of the seasonal fishing closure in the South China Sea? | 南海区伏季休渔的起止日期与适用范围是什么？ | policy | POL-LAW-009 | Confirm sea area and year |
| Q-E02 | Which operation types may be exempted or obtain a special permit during the closure? | 哪些作业类型在休渔期可以豁免或申请特许？ | policy | POL-LAW-009 / POL-STD-010 | Confirm operation type and approval level |
| Q-E03 | What must a marine large or medium fishing vessel record in its fishing logbook? | 海洋大中型渔船渔捞日志应记录哪些内容？ | procedure | POL-STD-010 / POL-WATCH-082 | Full field list not registered; answer from articles 50-53 |
| Q-E04 | What are the administrative consequences of missing or incorrect logbook entries? | 捕捞日志漏填或错填会有什么管理后果？ | policy | POL-STD-010 / POL-LAW-009 | Confirm legal basis and discretion |
| Q-E05 | How do the CWP definitions distinguish catch, landings and fishing effort? | CWP 统计口径如何区分捕捞产量、上岸量与捕捞努力量？ | definition | STD-CWP-043 | Reference collection; the Chinese official definition is production only |
| Q-E06 | What is the annual production trend for the South China Sea area? | 南海区海洋捕捞产量的年度趋势如何？ | statistic | STAT-YB-2018–STAT-YB-2025 | Sea-area series; the yearbooks publish no production by operation type |
| Q-E07 | What are the historical fishing seasons and main commercial species of a given fishing ground? | 某渔场的历史渔汛期与主要经济鱼种是什么？ | fact | none registered | Confirm fishing ground and period |
| Q-E08 | How should SST anomalies and chlorophyll concentrations in a fishery bulletin be interpreted? | 渔情通报里的 SST 距平、叶绿素浓度应该怎么解读？ | definition | none registered | Deferred to the web channel; not scored in v1 |
| Q-E09 | How are changes to the operating area or method handled during the validity of a fishing permit? | 渔业捕捞许可证有效期内，作业场所或作业方式变更应如何办理？ | policy | POL-STD-010 | Article 36 |
| Q-E10 | When did the minimum mesh-size regime for permitted and transitional marine capture gear take effect, and which sea areas does it cover? | 海洋捕捞准用渔具与过渡渔具最小网目尺寸制度从何时实施、适用哪些海区？ | standard | POL-GEAR-016 | Implementation date and sea areas |
| Q-E11 | How should a fishery bulletin be interpreted when it conflicts with historical experience? | 渔情通报与历史经验不一致时，应如何理解和使用？ | procedure | none registered | Confirm bulletin type and use case |
| Q-E12 | What are the legal basis and penalty types for fishing during a closure? | 休渔期违规作业的处罚依据与处罚种类是什么？ | policy | POL-LAW-009 | Article 78; gate regression case |
| Q-E13 | What conditions must a fishing vessel meet for permit annual review? | 渔业捕捞许可证年审需要符合哪些条件？ | procedure | POL-STD-010 | Article 41 |
| Q-E14 | What vessel-and-gear quota rules apply to building or rebuilding a marine capture vessel? | 制造、更新改造海洋捕捞渔船应遵守哪些船网工具指标规定？ | policy | POL-STD-010 | Article 14 |
| Q-E15 | What must a fishing vessel do when entering or leaving a fishing port? | 渔业船舶进出渔港应当遵守哪些报告和检查要求？ | procedure | POL-PORT-077 | Article 6 and 20 |

## Questions for fisheries administration

| ID | Question (English) | Original (Chinese) | Type | Expected evidence | Notes |
|---|---|---|---|---|---|
| Q-M01 | What is the current legal basis and amendment history of the seasonal closure system in the South China Sea? | 南海区伏季休渔制度的现行法律依据与修订沿革是什么？ | policy | POL-LAW-009 | Confirm national/local level |
| Q-M02 | Which fields should a vessel management record contain for a given vessel type? | 某类渔船的管理档案应包含哪些字段？ | procedure | none registered (deferred) | Abstention test; vessel/voyage dictionary not registered |
| Q-M03 | What are the requirements for submitting and reporting fishing logbooks? | 渔捞日志的提交与上报要求是什么？ | procedure | POL-STD-010 | Article 51 |
| Q-M04 | What are the official differences between production, landed weight and fishing effort? | 产量、上岸量、捕捞努力量的官方口径差异是什么？ | definition | DICT-STAT-013 | Confirm yearbook version |
| Q-M05 | What were the production and vessel counts for a given year, sea area and operation type? | 某年度某海域某作业类型的产量与船数统计是多少？ | statistic | STAT-YB-2018–STAT-YB-2025 | Confirm sea area and year; the yearbooks publish no production by operation type |
| Q-M06 | How are voyage, operating day and port stay defined in vessel/voyage data? | 船位/航次数据中的“航次”“作业日”“停港”如何定义？ | definition | none registered (deferred) | Abstention test; vessel/voyage dictionary not registered |
| Q-M07 | Which agencies publish fishery bulletins, how often, and in what format? | 渔场/渔汛预报通报的发布机构、频次与格式是什么？ | fact | none registered | Confirm publisher level and period |
| Q-M08 | How have historical fishing seasons and the central fishing ground changed for a given area? | 某渔场历史渔汛记录与中心渔场变化如何？ | fact | none registered | Confirm fishing ground and period |
| Q-M09 | What are the spatial/temporal resolutions and appropriate uses of ocean and fishery products? | 海洋环境/渔情产品的时空分辨率与适用场景是什么？ | definition | none registered | Deferred to the web channel; not scored in v1 |
| Q-M10 | What documents must be submitted to apply for a marine fishing permit? | 申请海洋渔业捕捞许可证应当提交哪些资料？ | policy | POL-STD-010 | Confirm operation type and region |
| Q-M11 | How should source, version and licence be attributed when data are shared or published? | 数据共享/发布时如何标注来源、版本与许可？ | procedure | none registered (deferred) | Abstention test; metadata and quality rules not registered |
| Q-M12 | What are the exception-approval and penalty rules in seasonal closure management? | 休渔期管理中的例外审批与处罚依据是什么？ | policy | POL-LAW-009 | Confirm exception type and approval level |
| Q-M13 | When must a fishing permit be reissued or reapplied for? | 渔业捕捞许可证在哪些情形下应换发或重新申请？ | procedure | POL-STD-010 | Articles 36 and 37 |
| Q-M14 | How are fishing gear classified, named and coded? | 渔具如何分类、命名和编号？ | standard | OPS-STD-039 | GB/T 5147—2026 |
| Q-M15 | How is the sample of vessels selected in the marine capture sampling survey? | 海洋捕捞信息采集抽样调查如何抽取样本渔船？ | procedure | OPS-STD-035 | SC/T 9460—2025 |
| Q-M16 | What is the annual rate range for the marine fishery resource protection fee? | 海洋渔业资源增殖保护费的年征收幅度是多少？ | policy | POL-RULE-020 | Article 5 |
| Q-M17 | What types of inspection apply to fishing vessels? | 渔业船舶检验分为哪几种？ | standard | POL-RULE-019 | Article 4 |
| Q-M18 | What were the coastal fishing-port classes in the South China Sea for data years 2018 and 2019? | 2018–2019 年南海区沿海渔港等级分类是什么？ | statistic | none registered | Abstention test; yearbook port table missing |

Eight questions have no registered source and form the abstention tests: Q-E07, Q-E11, Q-M02, Q-M06, Q-M07, Q-M08, Q-M11 and Q-M18. Q-E08 and Q-M09 are deferred to the web channel and are not scored. The remaining 23 questions are answerable.

Nineteen questions have gold anchors in [configs/eval.yaml](../configs/eval.yaml): Q-E01, Q-E02, Q-E03, Q-E04, Q-E09, Q-E10, Q-E12, Q-E13, Q-E14, Q-E15, Q-M01, Q-M03, Q-M10, Q-M12, Q-M13, Q-M14, Q-M15, Q-M16 and Q-M17. Q-E05 and Q-M04 are answered by the CWP reference collection and Q-E06 and Q-M05 by the local statistics channel. Gold answer points are recorded under `gold` in the same config.

## Coverage

| Metric | Value |
|---|---:|
| Vessel-operator questions | 15 |
| Fisheries-administration questions | 18 |
| Total | 33 |
| Policy | 10 |
| Procedure | 9 |
| Definition | 5 |
| Statistic | 3 |
| Fact | 3 |
| Standard | 3 |

The expected-evidence column names the sources that can answer each question once acquired. The two statistic questions are limited to sea area, gear group and species: no registered edition publishes capture production by operation type, so the operation-type part of those questions is currently unanswerable. The expected-evidence column otherwise covers the main knowledge categories. Papers and reports may provide background or follow-up evidence, but are not the primary evidence for these questions.

## Next steps

1. Record the owner review decisions in `configs/eval.yaml` (batch 1 is done; batches 2 and 3 follow the same K/R/D pattern).
2. Keep gold answers and evidence anchors in step with the reviewed questions.
3. Run the deterministic answer-level evaluation and report the results in [evaluation.md](evaluation.md).
4. Use the reviewed set for retrieval, citation and answer evaluation.
