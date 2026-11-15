from __future__ import annotations

from scs_fkb.answer_v3.channels import ChannelBook


def test_berth_fee_disputes_route_to_market_regulation_and_the_courts():
    book = ChannelBook.load()
    _gap, channels = book.resolve("渔港收我泊位费，这个费用该找谁？")
    names = [item.name for item in channels]
    assert names[0] == "市场监督管理部门"
    assert "人民法院" in names


def test_veterinary_drug_questions_leave_the_fishery_office():
    book = ChannelBook.load()
    _gap, channels = book.resolve("虾发病了用什么渔药？")
    assert channels[0].name == "农业农村部门（兽医）"


def test_a_plain_closure_question_keeps_the_default_channels():
    book = ChannelBook.load()
    _gap, channels = book.resolve("今年休渔时间是什么时候？")
    assert channels[0].name == "属地渔业主管部门"
