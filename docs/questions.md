# Evaluation Questions

- Status: **retired design samples**. The 48-question set was retired with the v1 cleanup; the working instrument is the private 512-question acceptance set. The table below is kept as sanitized question-design samples and is not scored.
- Four personas: captain/crew, owner/operator, enforcement and extension. The samples keep their original persona labels; nothing here is scored.
- The retired set carried gold points and persona/split metadata; neither is part of the public tree or the current instrument.

## How to use this set

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

## Questions for fisheries administration (dev)

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

## Held-out questions by persona (test split)

| ID | Question (English) | Original (Chinese) | Type | Expected evidence | Notes |
|---|---|---|---|---|---|
| Q-C01 | What must the master ensure for a fishing-vessel navigation watch? | 渔业船舶航行值班中，船长应当保证哪些事项？ | procedure | POL-WATCH-082 第三条 | Test split; captain. |
| Q-C02 | What must be handed over at a watch change on a fishing vessel? | 渔业船舶交接班时必须交清哪些内容？ | procedure | POL-WATCH-082 第十五条 | Test split; captain. |
| Q-C03 | What visa and watchkeeping requirements apply when a fishing vessel enters or leaves port, and what penalties apply? | 渔业船舶进出渔港、在港停泊期间有哪些签证和值班要求？违反如何处罚？ | policy | POL-PEN-078 第九条 | Test split; captain. |
| Q-C04 | What is the 2026 fuel-subsidy standard for fishing vessels in the South China Sea? | 2026 年南海区渔船油价补贴的发放标准是多少？ | policy | none registered | Test split; abstention: only a possible deduction is mentioned, not the standard. |
| Q-O01 | How long is a fishing permit valid, and when must renewal be applied for? | 渔业捕捞许可证的使用期限是多久？期满换发应在何时申请？ | policy | POL-STD-010 第三十五条、第三十六条 | Test split; owner. |
| Q-O02 | How long is a vessel-and-gear quota approval valid, and can it be extended? | 渔业船网工具指标批准书的有效期是多久？可以延展吗？ | procedure | POL-STD-010 第十六条 | Test split; owner. |
| Q-O03 | What types of fishing-vessel inspection exist, and when is each required? | 渔业船舶检验分为哪几种？分别在什么情形下申报？ | standard | POL-RULE-019 第四条、第六条、第十三条、第十九条 | Test split; owner. |
| Q-O04 | What is the process and interest rate for a fishing-vessel mortgage loan? | 渔船抵押贷款的办理流程和利率是多少？ | policy | none registered | Test split; abstention: only mortgage registration is required, not the loan process or rate. |
| Q-F01 | What types of fishery administrative penalties exist, and how is the fine unit determined? | 渔业行政处罚有哪些种类？罚款的计罚单位如何确定？ | policy | POL-PEN-080 第二条、第五条 | Test split; enforcement. |
| Q-F02 | What penalties apply to unauthorised dangerous-cargo handling, construction or obstructing fishing in a fishing port? | 在渔港内未经批准装卸危险货物、新建改建设施或从事碍航捕捞养殖，如何处罚？ | policy | POL-PEN-078 第十条 | Test split; enforcement. |
| Q-F03 | What are the port-of-registry closure and special-permit requirements in the 2026 closure enforcement action? | 2026 年伏季休渔执法行动中，船籍港休渔制度和专项捕捞作业监管分别有哪些要求？ | procedure | POL-ENF-068 一、重点任务 | Test split; enforcement. |
| Q-F04 | In which circumstances must a fishing permit not be issued? | 哪些情形不得发放捕捞许可证？ | policy | POL-RULE-018 第十七条 | Test split; enforcement. |
| Q-T01 | What is the writing order for fishing-gear classification names and codes? Give examples. | 渔具分类代号的书写顺序是什么？请举例说明。 | standard | OPS-STD-039 | Test split; extension. |
| Q-T02 | How is the marine capture sampling survey stratified, and what is the minimum sample per stratum? | 海洋捕捞信息采集抽样调查如何分层？每层样本量至少多少？ | procedure | OPS-STD-035 | Test split; extension. |
| Q-T03 | What is the total resource-protection fee collected in the South China Sea in 2026? | 2026 年南海区渔业资源增殖保护费的征收总额是多少？ | statistic | none registered | Test split; abstention: rates exist, no total is published. |

Eleven questions have no registered source and form the abstention tests: Q-E07, Q-E11, Q-M02, Q-M06, Q-M07, Q-M08, Q-M11, Q-M18, Q-C04, Q-O04 and Q-T03. Q-E08 and Q-M09 are deferred to the web channel and are not scored. The remaining 35 questions are answerable.

The retired set had thirty-one anchor questions, eleven abstention tests, two CWP reference questions, two statistics questions and two deferred web questions. None of them is scored now.

## Coverage

| Metric | Value |
|---|---:|
| Captain / crew | 17 |
| Owner / operator | 4 |
| Enforcement | 18 |
| Extension | 9 |
| **Total** | **48** |
| Dev | 33 |
| Test | 15 |
| Policy | 17 |
| Procedure | 14 |
| Definition | 5 |
| Statistic | 4 |
| Fact | 3 |
| Standard | 5 |
| Anchors | 31 |
| Abstention | 11 |

The persona counts cover all 48 questions. `summary_persona` in `eval` covers the 42 main-index anchors and abstention tests; the 2 CWP reference and 2 statistics questions are reported by their own channels, so their persona rows are not in that summary. The expected-evidence column names the sources that can answer each question once acquired. The two statistic questions are limited to sea area, gear group and species: no registered edition publishes capture production by operation type, so the operation-type part of those questions is currently unanswerable. The expected-evidence column otherwise covers the main knowledge categories. Papers and reports may provide background or follow-up evidence, but are not the primary evidence for these questions.

## Next steps

1. Keep gold answers, evidence anchors and `meta` in step with the reviewed questions.
2. Run the deterministic and LLM evaluations; report dev and test separately and never tune on test.
3. Any test-driven change must first become a new dev question; test stays report-only.
4. Record each run in [evaluation.md](evaluation.md) with commit, index version and model.

## Acceptance samples (sanitized, 2026-11-09)

Twenty representative shapes from the acceptance instrument, with place names,
vessel identifiers and years generalised. Each row states the evidence a complete
answer must cite; none of these rows is used for tuning.

| # | Question (sanitized) | Answer shape | Evidence needed |
|---:|---|---|---|
| 1 | 伏季休渔的起止时间与适用海域是什么？ | dates + sea area + citation | 农业农村部休渔通告 |
| 2 | 休渔期哪些作业类型可以豁免或申请专项许可？ | clause + approval level | 休渔通告 + 专项许可规定 |
| 3 | 拖网网囊的最小网目尺寸是多少，依据哪条？ | value + unit + clause | 网目尺寸标准 |
| 4 | 幼鱼比例超过多少算违规，按重量还是尾数？ | ratio + basis + clause | 最小可捕规格通告 |
| 5 | 捕捞许可证到期前多久换发，逾期怎么办？ | deadline + procedure + channel | 捕捞许可管理规定 |
| 6 | 大中型渔船渔捞日志必须记录哪些内容？ | field list + clause | 捕捞许可管理规定 §50-53 |
| 7 | 未按规定提交渔捞日志的处罚是什么？ | penalty + range + clause | 捕捞许可管理规定 |
| 8 | 渔船进出渔港需要办理什么报告手续？ | procedure + channel | 渔港管理规定 |
| 9 | 渔船检验分为哪几类，多久一次？ | categories + interval | 渔船检验规则 |
| 10 | 什么情况下必须配职务船员，配几名？ | conditions + numbers | 船员管理办法 |
| 11 | 在禁渔区线内作业的认定标准与处罚依据？ | definition + penalty | 渔业法 + 实施细则 |
| 12 | 误捕保护物种应如何处理，能否带回？ | handling + prohibition | 野生动物保护法 + 行动计划 |
| 13 | 渔业资源增殖保护费的征收幅度是多少？ | range + basis | 征收使用管理办法 |
| 14 | 减船转产补助的对象、标准与申请渠道？ | eligibility + amount + channel | 渔业发展支持政策 |
| 15 | 海洋捕捞产量按海区、渔具如何统计？ | definitions + table | 渔业统计年鉴 |
| 16 | 渔情遥感产品的分辨率与更新频率是多少？ | values + caveat | 遥感产品说明（未入库时拒答） |
| 17 | 台风预警分几级，渔民应如何响应？ | levels + actions | 台风预警信号规定 |
| 18 | 涉外渔业纠纷应向哪个部门报告？ | channel + procedure | 涉外渔业管理规定 |
| 19 | 海洋生态公报中的低氧阈值如何判定？ | value + method | 生态预警监测公报 |
| 20 | 历史渔汛期与中心渔场如何变化？ | trend + caveat | 渔情通报/研究资料（无据时拒答） |
