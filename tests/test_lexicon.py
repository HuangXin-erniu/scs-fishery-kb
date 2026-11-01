from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scs_fkb.lexicon import LexiconError, expand_query, load_lexicon

SAMPLE = """schema_version: 1
groups:
  - {term: 捕捞日志, variants: [渔捞日志]}
  - {term: 日志, variants: [记录]}
  - {term: 例外, variants: [专项, 特许]}
"""


def _lexicon(tmp_path: Path) -> list[dict[str, object]]:
    path = tmp_path / "lexicon.yaml"
    path.write_text(SAMPLE, encoding="utf-8")
    return load_lexicon(path)


def test_expands_single_term(tmp_path: Path) -> None:
    groups = _lexicon(tmp_path)
    assert expand_query("例外审批的依据", groups) == "例外审批的依据 专项 特许"


def test_longest_term_wins(tmp_path: Path) -> None:
    groups = _lexicon(tmp_path)
    assert expand_query("捕捞日志的字段", groups) == "捕捞日志的字段 渔捞日志"


def test_no_match_leaves_query_unchanged(tmp_path: Path) -> None:
    groups = _lexicon(tmp_path)
    assert expand_query("南海区伏季休渔的起止日期", groups) == "南海区伏季休渔的起止日期"


def test_variants_added_once(tmp_path: Path) -> None:
    groups = _lexicon(tmp_path)
    assert expand_query("例外和例外", groups).count("专项") == 1


def test_empty_groups_pass_through() -> None:
    assert expand_query("例外", []) == "例外"
    assert expand_query("例外", None) == "例外"


def test_rejects_malformed_group(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    payload = {"schema_version": 1, "groups": [{"term": "例外"}]}
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(LexiconError, match="incomplete"):
        load_lexicon(path)


def test_repository_lexicon_loads() -> None:
    groups = load_lexicon()
    assert [group["term"] for group in groups] == ["例外"]
    assert expand_query("休渔期管理中的例外审批", groups).endswith("专项 特许")
