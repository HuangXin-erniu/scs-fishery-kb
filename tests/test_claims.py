from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scs_fkb.claims import ClaimError, classify, load_claims

CONFIG = Path("configs/claims.yaml")
CASES = {
    "伏季休渔的定义是什么？": ("definition", "policy"),
    "申请捕捞许可证需要提交哪些材料？": ("rule", "policy"),
    "2025年南海捕捞产量是多少？": ("quantity", "statistics"),
    "目前的伏季休渔时间是否有效？": ("status", "policy"),
    "台风预警信号分几级？": ("warning", "hazard"),
    "大黄鱼的学名和保护等级是什么？": ("identification", "species"),
    "休渔制度的修订沿革是什么？": ("history", "policy"),
}


def test_each_nature_and_domain() -> None:
    config = load_claims(CONFIG)
    for question, (nature, domain) in CASES.items():
        result = classify(question, config)
        assert result["nature"] == nature, question
        assert result["domain"] == domain, question


def test_unknown_question_falls_back() -> None:
    config = load_claims(CONFIG)
    result = classify("今天适合出门吗？", config)
    assert result["nature"] == "general"
    assert result["domain"] == "general"


def test_bad_nature_set_is_rejected(tmp_path: Path) -> None:
    data = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    data["natures"].pop("history")
    path = tmp_path / "claims.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ClaimError, match="natures"):
        load_claims(path)


def test_empty_keywords_are_rejected(tmp_path: Path) -> None:
    data = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    data["natures"]["definition"]["keywords"] = []
    path = tmp_path / "claims.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ClaimError, match="definition"):
        load_claims(path)
