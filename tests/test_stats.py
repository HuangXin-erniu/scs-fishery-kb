from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from scs_fkb.stats import StatsError, parse_query, query, table_path

FIXTURE = Path(__file__).parent / "fixtures" / "statistics-sample.csv"


def _root(tmp_path: Path) -> Path:
    target = tmp_path / "statistics"
    target.mkdir()
    shutil.copy(FIXTURE, target / "core-indicators-v3.csv")
    return tmp_path


def test_parse_query_extracts_dimensions(tmp_path: Path) -> None:
    parsed = parse_query("2019年广东省南海区拖网渔船数量")
    assert parsed["years"] == [2019]
    assert parsed["region"] == "Guangdong"
    assert parsed["sea_area"] == "South China Sea"
    assert parsed["gear"] == "trawl"
    assert parsed["groups"] == ["vessel_count"]


def test_parse_query_detects_trend() -> None:
    assert parse_query("南海区海洋捕捞产量历年趋势")["trend"] is True


def test_missing_table_raises(tmp_path: Path) -> None:
    with pytest.raises(StatsError, match="not found"):
        query("2019年南海区海洋捕捞产量", root=tmp_path)


def test_sea_area_row_and_citation(tmp_path: Path) -> None:
    hits = query("2019年南海区海洋捕捞产量", root=_root(tmp_path))
    assert hits
    first = hits[0]
    assert first.row["basis"] == "published_south_sea"
    assert "1000吨" in first.text
    assert first.citation == "[STAT-YB-2020 §各地区海洋捕捞产量(按海域分)]"


def test_derived_rows_are_hidden(tmp_path: Path) -> None:
    hits = query("2019年南海区海洋捕捞产量", root=_root(tmp_path))
    assert all(hit.row["basis"] not in {"difference", "three_province_subtotal"} for hit in hits)


def test_vessel_count_rows(tmp_path: Path) -> None:
    hits = query("2019年广东省拖网渔船数量", root=_root(tmp_path))
    assert len(hits) == 1
    assert hits[0].row["indicator"] == "vessel_count"
    assert "12艘" in hits[0].text


def test_vessel_with_sea_area_gets_gap_note(tmp_path: Path) -> None:
    hits = query("2019年南海区拖网渔船数量", root=_root(tmp_path))
    assert hits
    assert any("无海域维度" in note for note in hits[0].notes)


def test_production_with_gear_and_sea_gets_gap_note(tmp_path: Path) -> None:
    hits = query("2019年南海区拖网作业的产量", root=_root(tmp_path))
    assert hits
    assert any("按作业类型分的海域产量" in note for note in hits[0].notes)


def test_latest_year_default(tmp_path: Path) -> None:
    hits = query("南海区海洋捕捞产量", root=_root(tmp_path))
    assert {hit.row["data_year"] for hit in hits} == {"2025"}


def test_trend_orders_by_year(tmp_path: Path) -> None:
    hits = query("南海区海洋捕捞产量历年趋势", root=_root(tmp_path))
    years = [int(hit.row["data_year"]) for hit in hits]
    assert years == sorted(years)


def test_2025_sample_note(tmp_path: Path) -> None:
    hits = query("2025年南海区海洋捕捞产量", root=_root(tmp_path))
    assert any("抽样" in note for note in hits[0].notes)


def test_question_without_statistical_cue_returns_nothing(tmp_path: Path) -> None:
    assert query("休渔期违规作业怎么处罚", root=_root(tmp_path)) == []


def test_table_path_uses_statistics_directory(tmp_path: Path) -> None:
    assert table_path(tmp_path) == tmp_path / "statistics" / "core-indicators-v3.csv"


def test_schema_names_match_module() -> None:
    import yaml

    from scs_fkb.config import REPO_ROOT
    from scs_fkb.stats import INDICATOR_NAMES

    data = yaml.safe_load((REPO_ROOT / "configs" / "statistics.yaml").read_text(encoding="utf-8"))
    assert data["indicator_names_zh"] == INDICATOR_NAMES
    assert data["query"]["years"] == [2017, 2025]
    assert data["query"]["gaps"]
