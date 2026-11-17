from __future__ import annotations

from types import SimpleNamespace

from scs_fkb.service_v2.answer import _rescue_answer


def _chunk(text: str, doc: str = "STAT-ECO-111") -> SimpleNamespace:
    return SimpleNamespace(doc_id=doc, section="p.8", page=8, text=text)


def test_rescue_finds_the_definition_sentence() -> None:
    chunk = _chunk(
        "第 8 页 海洋热浪是指在一定海域内发生的日海表温度至少连续 5 天"
        "超过当地季节阈值的事件，其持续时间可达数月。"
    )
    result = _rescue_answer("海洋热浪是啥？跟台风一样吗？", [chunk])
    assert result is not None
    assert "海洋热浪是指" in result[0]


def test_rescue_rejects_a_generic_marine_chunk() -> None:
    chunk = _chunk("海洋生态灾害包括赤潮、缺氧和酸化等监测内容。")
    assert _rescue_answer("海洋热浪是啥？跟台风一样吗？", [chunk]) is None
