from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scs_fkb.expand import BridgeError, concepts_for, expanded_query, load_bridge

BRIDGE = """schema_version: 1
terms:
  - {zh: 捕捞努力量, en: [fishing, effort]}
  - {zh: 上岸量, en: [landings]}
  - {zh: 渔获量, en: [catch]}
  - {zh: 产量, en: [catch, production]}
  - {zh: 作业日志, en: [logbook]}
"""


def _bridge(tmp_path: Path) -> Path:
    path = tmp_path / "bridge.yaml"
    path.write_text(BRIDGE, encoding="utf-8")
    return path


def test_concepts_for_single_term(tmp_path: Path) -> None:
    bridge = load_bridge(_bridge(tmp_path))
    assert concepts_for("上岸量怎么定义", bridge) == ["landings"]


def test_concepts_for_multiple_terms(tmp_path: Path) -> None:
    bridge = load_bridge(_bridge(tmp_path))
    concepts = concepts_for("渔获量统计中的产量、上岸量、捕捞努力量分别怎么定义？", bridge)
    assert concepts == ["catch", "production", "landings", "fishing", "effort"]


def test_concepts_deduplicate(tmp_path: Path) -> None:
    bridge = load_bridge(_bridge(tmp_path))
    assert concepts_for("产量和渔获量", bridge) == ["catch", "production"]


def test_concepts_ignore_unmapped_questions(tmp_path: Path) -> None:
    bridge = load_bridge(_bridge(tmp_path))
    for question in (
        "某渔场的历史渔汛期与主要经济鱼种是什么？",
        "渔情通报里的 SST 距平、叶绿素浓度应该怎么解读？",
        "海洋环境/渔情产品的时空分辨率与适用场景是什么？",
    ):
        assert concepts_for(question, bridge) == []


def test_expanded_query_appends_concepts(tmp_path: Path) -> None:
    bridge = load_bridge(_bridge(tmp_path))
    concepts = concepts_for("上岸量", bridge)
    assert expanded_query("上岸量", concepts) == "上岸量 landings"
    assert expanded_query("休渔期", []) == "休渔期"


def test_project_bridge_maps_ocean_colour_terms() -> None:
    bridge = load_bridge()
    assert concepts_for("水色产品的覆盖周期是多少", bridge) == ["ocean colour", "coverage cycle"]
    assert concepts_for("幅宽与重访", bridge) == ["swath", "revisit"]
    assert concepts_for("海洋水色水温扫描仪", bridge) == ["ocean colour"]


def test_bridge_rejects_malformed_entries(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    payload = {"schema_version": 1, "terms": [{"zh": "产量"}]}
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(BridgeError, match="incomplete"):
        load_bridge(path)
