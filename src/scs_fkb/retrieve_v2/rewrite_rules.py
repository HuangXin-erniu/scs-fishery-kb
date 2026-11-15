"""Deterministic domain query rewriting for the standard RAG arm.

The rewrite adds legal/practical synonyms only. It is deliberately not used by
the dump/acceptance arm or the public regression, so frozen Track A behaviour is
unchanged.
"""

from __future__ import annotations

RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (
        ("休渔", "禁渔", "出海", "船在港", "网在船上"),
        "禁渔期 船籍港 停泊 携带网具 认定 法律责任",
    ),
    (("渔业法", "新法", "旧法", "施行"), "法律适用 时间效力 从旧兼从轻 行政处罚"),
    (
        ("白海豚", "误捕", "保护动物", "野生动物"),
        "国家重点保护野生动物 水生野生动物 误捕 报告 处置",
    ),
    (("名录",), "重点保护水生野生动物名录 国家重点保护 广东省"),
    (
        ("违法所得", "渔获物", "从轻", "听证", "处罚", "罚则", "没收"),
        "行政处罚 没收 听证 期限 集体讨论 法律责任",
    ),
    (("三无",), "无船名船号 无船舶证书 无船籍港 认定 没收"),
    (
        ("日志", "作业类型", "刺网", "笼壶", "无证", "未按证"),
        "渔捞日志 填写 捕捞许可证 作业类型 变更 罚则",
    ),
    (("热浪", "死鱼", "污染", "赤潮"), "海洋环境污染 渔业水域 污染事故 报告 赤潮"),
    (("外籍渔船", "登临"), "专属经济区 登临检查 权限 程序"),
    (("油补", "补助资金", "虚报"), "渔业油价补贴 补助资金 虚报 追回"),
    (("禁用渔具", "网目", "鉴定", "缩水"), "禁用渔具 目录 网目尺寸 测量 认定"),
    (("渔情", "执法依据"), "渔情预报 证据 执法"),
)


def rewrite_question(question: str) -> str:
    """Append domain synonyms when a rule matches; never removes original text."""
    extras: list[str] = []
    for keywords, terms in RULES:
        if any(keyword in question for keyword in keywords):
            extras.append(terms)
    if not extras:
        return question
    return question + " " + " ".join(extras)


__all__ = ["RULES", "rewrite_question"]
