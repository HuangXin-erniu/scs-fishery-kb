from __future__ import annotations

import re

from .contract import NumericAnchor

NUMBER_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(毫米|厘米|米|公里|海里|吨|公斤|千克|毫克|微克|升|立方米|元|万元|亿元|%|‰|天|个月|小时|年|月|日|时|艘|人|尾|倍|级|度|千瓦|马力)"
)
NUMERIC_QUESTION = re.compile(
    r"多少|几[个天年月日岁]?|多大|多长|多重|比例|限值|标准|尺寸|网目|幼鱼|规格|罚款|罚多少|金额|上限|下限|阈值|浓度|温度|产量"
)
BASIS_WORDS = {
    "全国": "全国口径",
    "南海": "南海海区",
    "海区": "海区口径",
    "分区": "分区口径",
    "年度": "年度值",
    "年均": "年均值",
    "单次": "单次值",
    "航次": "航次口径",
    "重量": "按重量计",
    "尾数": "按尾数计",
    "表": "表列值",
    "图": "图列值",
}


def is_numeric_question(question: str) -> bool:
    return bool(NUMERIC_QUESTION.search(question))


def extract(text: str, *, location: str = "") -> list[NumericAnchor]:
    """Extract number/unit pairs and the nearest basis word from a sentence."""
    anchors: list[NumericAnchor] = []
    for match in NUMBER_RE.finditer(text):
        window = text[max(0, match.start() - 18) : match.end() + 18]
        basis = next((label for word, label in BASIS_WORDS.items() if word in window), "")
        anchors.append(
            NumericAnchor(
                value=match.group(1),
                unit=match.group(2),
                basis=basis or "未标注口径",
                location=location,
            )
        )
    return anchors
