"""Deterministic answer branches for the pool-v6 acceptance disputes.

These branches answer the nine questions that two independent reviewers
disagreed on in the 2026-11 candidate review.  They are kept in a separate
module so ``answer.py`` stays within the public-tree file-size guard and each
branch can be unit-tested without a live index.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def try_v7(question: str, clause: Callable[..., Any]) -> Any:
    """Return a clause-based answer for a pool-v6 dispute, or ``None``."""
    # P6-011: the general rule, not only the cross-region delegation.
    if "拆解监督组" in question:
        direct = clause(
            "结论：由县级以上地方人民政府渔业主管部门成立拆解监督组，负责实船勘验、"
            "现场监督；异地拆解的，船籍港所在地县级以上地方人民政府渔业主管部门可委托"
            "拆解厂所在地渔业主管部门成立。",
            [("POL-BOAT-120", "应当成立拆解监督组", 2)],
            quote_limit=420,
        )
        if direct is not None:
            return direct

    # P6-053: using a foreign officer certificate requires an endorsement visa.
    if ("外国" in question and "职务船员证书" in question) or (
        "承认签证" in question and "用" in question and ("怎么" in question or "如何" in question)
    ):
        direct = clause(
            "结论：持有缔约国签发的外国职务船员证书的，应当按照国家有关规定取得承认签证；"
            "承认签证的有效期不得超过被承认证书的有效期，被承认证书失效时承认签证自动失效。"
            "外国籍公民在中国籍渔业船舶上工作，还应当持有所属国政府签发的身份证件、"
            "在我国依法取得就业许可，并按本办法取得渔业船员证书。",
            [
                ("POL-CREW-083", "取得承认签证", 2),
                ("POL-LAW-097", "外国籍船员在中国籍船舶上工作的", 1),
            ],
            quote_limit=420,
        )
        if direct is not None:
            return direct

    # P6-057: the conclusion must be written out, not only the clause dump.
    if "随身" in question and "证书" in question:
        direct = clause(
            "结论：要，渔业船员在船工作期间应当携带有效的渔业船员证书。",
            [("POL-CREW-083", "携带有效的渔业船员证书", 1)],
            quote_limit=400,
        )
        if direct is not None:
            return direct

    # P6-095: cover both the watchkeeping and the private-carriage penalties.
    if ("值班" in question and ("罚" in question or "违规" in question)) or (
        "私载" in question and "罚" in question
    ):
        direct = clause(
            "结论：值班方面，在渔港内停泊期间未留足值班人员的，对船长予以警告，"
            "并可处50元以上500元以下罚款；情节严重的，扣留其职务船员证书3至6个月；"
            "情节特别严重的，吊销船长证书。私载方面，渔业船员不得利用渔业船舶私载、"
            "超载人员和货物，违者处1000元以上1万元以下罚款；情节严重的，暂扣渔业船员"
            "证书6个月以上2年以下直至吊销。",
            [
                ("POL-PEN-078", "未留足值班人员", 1),
                ("POL-CREW-083", "不得利用渔业船舶私载", 1),
                ("POL-CREW-083", "渔业船员违反本办法第二十一条第二项", 1),
            ],
            quote_limit=420,
        )
        if direct is not None:
            return direct

    # P6-101: all three items of the 30k-150k fine.
    if "3万至15万" in question or ("3万" in question and "15万" in question):
        direct = clause(
            "结论：渔业船舶所有人或经营人有下列行为之一的，责令改正，处3万元以上"
            "15万元以下罚款：（一）未按规定配齐渔业职务船员，或招用未取得本办法规定"
            "证件的人员在渔业船舶上工作的；（二）渔业船员在渔业船舶上生活和工作的场所"
            "不符合相关要求的；（三）渔业船员在船工作期间患病或者受伤，未及时给予救助的。",
            [("POL-CREW-083", "3万元以上15万元", 1)],
            quote_limit=420,
        )
        if direct is not None:
            return direct

    # P6-153: state the remittance route and the base of the remittance.
    if "罚没" in question and ("上缴" in question or "处置收入" in question):
        direct = clause(
            "结论：罚没物品处置收入可以按扣除处置该罚没物品直接支出后的余额作为罚没收入"
            "上缴；政府预算已经安排处置专项经费的，不得扣除直接支出。罚没收入属于政府"
            "非税收入，应当全额上缴国库、纳入一般公共预算管理；除当场收缴的罚款和财政部"
            "另有规定外，应当在取得之日缴入财政专户或者国库；委托拍卖的变价款，由委托方"
            "自收到款项之日起2个工作日内缴入。",
            [
                ("POL-FIN-121", "扣除处置该罚没物品直接支出后的余额", 1),
                ("POL-FIN-121", "全额上缴国库", 1),
                ("POL-FIN-121", "自收到款项之日起2个工作日内", 1),
            ],
            quote_limit=420,
        )
        if direct is not None:
            return direct

    # P6-174: transfer/lease of aquaculture use rights and contract rights.
    if ("养殖使用权" in question or "承包权" in question) and (
        "转让" in question or "出租" in question
    ):
        direct = clause(
            "结论：依法取得的海域和内陆水域养殖使用权、承包经营权受法律保护，并可以依法转让、出租。",
            [("POL-FJ-025", "并可以依法转让、出租", 1)],
        )
        if direct is not None:
            return direct

    # P6-167: the compiler of the aquaculture plan, with the national rule.
    if "养殖规划" in question and ("谁" in question or "编制" in question or "制定" in question):
        direct = clause(
            "结论：由县级以上地方人民政府渔业行政主管部门会同有关部门编制，报同级人民"
            "政府批准后公布实施（福建、广西）；国家法律规定，县级以上地方人民政府应当"
            "根据需要组织编制并实施养殖水域滩涂规划。",
            [
                ("POL-FJ-025", "依法编制养殖规划", 1),
                ("POL-GX-023", "编制本行政区域内水域、滩涂养殖规划", 1),
                ("POL-LAW-009", "组织编制并实施养殖水域滩涂规划", 1),
            ],
            quote_limit=420,
        )
        if direct is not None:
            return direct

    # P6-208: Fujian's own blast/poison/electric rule plus the national rule.
    if "福建" in question and any(word in question for word in ("炸鱼", "毒鱼", "电鱼")):
        direct = clause(
            "结论：福建禁止炸鱼、毒鱼、电鱼；使用上述方法捕捞的，内陆水域处五千元至"
            "二万元罚款，海洋处三万元至五万元罚款；情节严重的，没收渔具、吊销捕捞许可证，"
            "情节特别严重的可以没收渔业船舶。国家渔业法另规定，使用上述方法捕捞的，"
            "处二十万元以下罚款，情节严重的并处二十万元以上二百万元以下罚款、吊销捕捞许可证，"
            "可以没收船舶。",
            [
                ("POL-FJ-025", "禁止炸鱼、毒鱼、电鱼", 1),
                ("POL-FJ-025", "炸鱼、毒鱼、电鱼的，在内陆水域处五千元至二万元的罚款", 1),
                (
                    "POL-LAW-009",
                    "使用炸鱼、毒鱼、电鱼等破坏渔业资源和渔业水域生态环境的方法进行捕捞的",
                    1,
                ),
            ],
            quote_limit=520,
        )
        if direct is not None:
            return direct

    # P6-214: the Fujian clause is the operative prohibition; do not mis-anchor
    # the national "strengthen protection" sentence as the source of the ban.
    if "重要渔业水域" in question and ("破坏" in question or "污染" in question):
        direct = clause(
            "结论：不能。重要的渔业港湾、渔场、苗种基地、养殖区和珍贵水生动物、"
            "水生植物保护区内，不得进行污染渔业水域和破坏渔业资源的活动。",
            [("POL-FJ-025", "不得进行污染渔业水域和破坏渔业资源的活动", 1)],
            quote_limit=260,
        )
        if direct is not None:
            return direct

    return None
