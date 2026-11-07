"""Deterministic point terms for acceptance scoring.

The private instrument states required points in prose. Scoring them needs a
stable, auditable rule, so a point is reduced to anchors: numbers with units,
quoted titles, document numbers and domain concepts. Points without anchors are
reported as ``needs_review`` instead of being scored as hits or misses.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

NUMBER_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:年|月|日|时|天|小时|分钟|米|厘米|毫米|公里|海里|吨|公斤|千克|"
    r"千元|万元|亿元|元|%|‰|个月|次|人|艘|台|个|级|类|度|分|秒|成|倍|尾|份|项|条|款|号)?"
)
SIGN_MAP = str.maketrans({"°": "度", "′": "分", "″": "秒", "℃": "度"})
QUOTE_RE = re.compile(r"《[^》]{2,40}》")
DOCNO_RE = re.compile(r"[\u4e00-\u9fa5A-Za-z]{0,12}〔\d{4}〕\s*\d+\s*号")
GENERIC_CONCEPTS = {
    "渔业",
    "船舶",
    "管理",
    "规定",
    "办法",
    "标准",
    "要求",
    "水域",
    "海域",
    "海洋",
    "中国",
    "国家",
    "部门",
    "机构",
    "系统",
    "数据",
    "信息",
    "服务",
    "情况",
    "问题",
    "地方",
    "以上",
}


def normalize(text: str) -> str:
    """Fold width, degree symbols and whitespace so values compare directly."""
    folded = unicodedata.normalize("NFKC", str(text)).translate(SIGN_MAP)
    return "".join(folded.split())


# Typed rules score an element by the kind of statement it requires (a date
# range, an approval level, a penalty, a ratio) when the point names no literal
# anchor. Each rule still runs only on cited text.
POINT_RULES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    (
        "time",
        ("时间", "日期", "期限", "起止", "时效", "多久", "何时"),
        r"\d{1,2}月\d{1,2}日|\d{4}年\d{1,2}月|连续\s*\d+\s*天|\d+\s*个月|\d+\s*年",
    ),
    (
        "level",
        ("层级", "审批", "受理", "批准", "备案", "核发", "主管"),
        r"(国家|部|省|市|县|乡镇|海警|海事|渔政).{0,12}"
        r"(审批|受理|批准|备案|核发|主管)|"
        r"(审批|受理|批准|备案|核发).{0,12}(国家|部|省|市|县|乡镇|海警|海事|渔政)",
    ),
    ("materials", ("材料", "资料", "证件", "证明", "提交"), r"申请|提交|材料|资料|证件|证书|证明"),
    (
        "penalty",
        ("罚则", "处罚", "罚款", "刑罚", "立案", "追诉", "罪名"),
        r"罚款|没收|吊销|责令|处罚|拘留|有期徒刑|立案|追诉",
    ),
    ("ratio", ("比例", "占比", "百分比", "幼鱼"), r"\d+(?:\.\d+)?\s*%|比例|占比|百分比"),
    ("list", ("名录", "名单", "种类", "品种", "附件"), r"名录|名单|种类|品种|附件"),
    (
        "channel",
        ("渠道", "引导", "办理", "咨询"),
        r"咨询|办理|申请|报备|备案|主管部门|渔政|海事|海警",
    ),
    ("record", ("日志", "记录", "台账", "填报"), r"记录|填写|日志|台账|保存"),
    ("inspection", ("检验", "检查", "年检", "换证"), r"检验|检查|年检|换证"),
    (
        "certificate",
        ("持证", "证书", "证件", "证照"),
        r"证书|持证|许可证|证件|证照",
    ),
    (
        "condition",
        ("条件", "前提", "资格"),
        r"条件|前提|资格|具备|满足|不符合",
    ),
    (
        "scope",
        ("范围", "海域", "海区", "适用"),
        r"海域|海区|范围|适用|区域|海区",
    ),
    (
        "relief",
        ("救济", "复议", "诉讼", "投诉", "申诉"),
        r"复议|诉讼|投诉|申诉|救济",
    ),
    (
        "category",
        ("类型", "类别", "分类", "种类"),
        r"分类|类型|类别|种类|类",
    ),
    (
        "measure",
        ("计量", "单位", "口径", "鲜重", "按重量", "按尾数"),
        r"单位|口径|计量|鲜重|重量|尾数",
    ),
    (
        "compare",
        ("区别", "区分", "对比", "不同"),
        r"区别|不同|区分|相比|分别",
    ),
    (
        "forecast",
        ("预报", "预测", "产品说明"),
        r"预报|预测|说明|不提供|无法",
    ),
    (
        "responsibility",
        ("责任", "职责", "主体", "负责"),
        r"责任|职责|负责|主体|主管",
    ),
    (
        "frequency",
        ("频次", "更新", "时效", "周期", "多久一次"),
        r"每日|每周|每月|每季度|每年|频次|周期|更新|实时",
    ),
    (
        "definition",
        ("定义", "含义", "概念", "是指"),
        r"是指|定义|含义|概念|即",
    ),
    (
        "sampling",
        ("取样", "抽样", "样本", "称重"),
        r"取样|抽样|样本|称重|随机",
    ),
    (
        "identification",
        ("识别", "认定", "判定", "辨认"),
        r"识别|认定|判定|辨认|核对",
    ),
    (
        "method",
        ("办法", "方法", "程序", "流程", "步骤", "方式"),
        r"办法|方法|程序|流程|步骤|方式|按照",
    ),
)


def rule_for(point_text: str) -> str:
    """Return the typed rule that matches a point's element, if any."""
    text = normalize(point_text)
    for name, cues, _pattern in POINT_RULES:
        if any(cue in text for cue in cues):
            return name
    return ""


def rule_pattern(name: str) -> str:
    return next((pattern for rule, _cues, pattern in POINT_RULES if rule == name), "")


@dataclass(frozen=True)
class PointSpec:
    terms: tuple[str, ...]
    mode: str = "section"
    skip: bool = False
    note: str = ""
    rule: str = ""


@dataclass
class ConceptSource:
    """Domain concepts used as anchors, loaded from public configuration."""

    concepts: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def load(cls, terms_path: Path | str, extra_path: Path | str | None = None) -> ConceptSource:
        import yaml

        found: set[str] = set()
        terms_file = Path(terms_path).expanduser()
        if terms_file.is_file():
            data = yaml.safe_load(terms_file.read_text(encoding="utf-8")) or {}
            for term in data.get("terms") or []:
                if term.get("status") not in (None, "approved"):
                    continue
                for name in [term.get("standard"), *(term.get("variants") or [])]:
                    text = normalize(str(name or ""))
                    if len(text) >= 2 and text not in GENERIC_CONCEPTS:
                        found.add(text)
        if extra_path:
            extra_file = Path(extra_path).expanduser()
            if extra_file.is_file():
                data = yaml.safe_load(extra_file.read_text(encoding="utf-8")) or {}
                for name in data.get("terms") or []:
                    text = normalize(str(name or ""))
                    if len(text) >= 2 and text not in GENERIC_CONCEPTS:
                        found.add(text)
        ordered = tuple(sorted(found, key=lambda item: (-len(item), item)))
        return cls(concepts=ordered)

    def matches(self, text: str, limit: int = 3) -> list[str]:
        """Return the longest non-overlapping concepts present in ``text``."""
        normalized = normalize(text)
        found: list[str] = []
        occupied: list[tuple[int, int]] = []
        for concept in self.concepts:
            start = normalized.find(concept)
            if start < 0:
                continue
            end = start + len(concept)
            if any(start < right and left < end for left, right in occupied):
                continue
            found.append(concept)
            occupied.append((start, end))
            if len(found) >= limit:
                break
        return found


@dataclass
class PointOverrides:
    """Private per-point overrides for points the automatic rule cannot score."""

    specs: dict[tuple[str, int], PointSpec] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | str | None) -> PointOverrides:
        import yaml

        if not path:
            return cls()
        override_path = Path(path).expanduser()
        if not override_path.is_file():
            return cls()
        data = yaml.safe_load(override_path.read_text(encoding="utf-8")) or {}
        specs: dict[tuple[str, int], PointSpec] = {}
        for identifier, items in (data.get("points") or {}).items():
            for index, item in enumerate(items or []):
                if not isinstance(item, dict):
                    raise ValueError(f"override {identifier}[{index}] must be an object")
                terms = item.get("terms")
                specs[(str(identifier), int(item.get("index", index)))] = PointSpec(
                    terms=tuple(normalize(str(term)) for term in (terms or [])),
                    mode=str(item.get("mode") or "section"),
                    skip=bool(item.get("skip")),
                    note=str(item.get("note") or ""),
                )
        return cls(specs=specs)

    def get(self, identifier: str, index: int) -> PointSpec | None:
        return self.specs.get((identifier, index))


def derive_terms(
    point_text: str,
    *,
    concepts: ConceptSource,
    override: PointSpec | None = None,
    max_terms: int = 3,
) -> PointSpec:
    """Reduce one required point to anchors and a matching mode."""
    if override is not None and (override.terms or override.skip):
        mode = override.mode or "section"
        return PointSpec(terms=override.terms, mode=mode, skip=override.skip, note=override.note)

    text = normalize(point_text)
    numbers = [match.group(0) for match in NUMBER_RE.finditer(text) if match.group(0)]
    quoted = [match.group(0) for match in QUOTE_RE.finditer(text)]
    docnos = [match.group(0) for match in DOCNO_RE.finditer(text)]
    strong = _dedupe([*numbers, *quoted, *docnos])
    if strong:
        return PointSpec(terms=tuple(strong[: max(1, max_terms + 1)]), mode="section")
    found = concepts.matches(text, limit=max_terms)
    if found:
        mode = "section" if len(found) <= 2 else "document"
        return PointSpec(terms=tuple(found), mode=mode)
    rule = rule_for(text)
    if rule:
        return PointSpec(terms=(), mode="section", note=f"typed rule: {rule}", rule=rule)
    return PointSpec(terms=(), mode="section", note="no anchor derived")


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def point_specs(
    row: dict[str, Any],
    *,
    concepts: ConceptSource,
    overrides: PointOverrides,
    max_terms: int = 3,
) -> list[PointSpec]:
    """Derive the spec for every required point of one question."""
    specs: list[PointSpec] = []
    for index, point in enumerate(row.get("required_points") or []):
        override = overrides.get(str(row.get("id")), index)
        specs.append(
            derive_terms(str(point), concepts=concepts, override=override, max_terms=max_terms)
        )
    return specs
