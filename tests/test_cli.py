from __future__ import annotations

from types import SimpleNamespace

from scs_fkb import cli


def test_cli_exposes_only_the_shipped_commands() -> None:
    parser = cli.build_parser()
    actions = [item for item in parser._actions if item.dest == "command"]
    assert actions
    choices = sorted(actions[0].choices)
    assert choices == ["ask", "check", "serve"]


def test_legacy_command_is_rejected() -> None:
    parser = cli.build_parser()
    try:
        parser.parse_args(["eval"])
    except SystemExit as exc:
        assert exc.code == 2
    else:  # pragma: no cover - argparse must reject it
        raise AssertionError("legacy command was accepted")


def _result() -> SimpleNamespace:
    citation = SimpleNamespace(doc_id="POL-CLOS-015", section="三、休渔时间", page=1, title="通告")
    return SimpleNamespace(
        answer="结论：5月1日。\n依据摘录：\n5月1日12时起休渔。 [POL-CLOS-015 §三、休渔时间]",
        summary="结论：5月1日。",
        citations=[citation],
        citations_total=1,
        abstained=False,
        mode="kb_only",
    )


def test_ask_defaults_to_the_summary(monkeypatch, capsys) -> None:
    result = _result()
    monkeypatch.setattr(cli, "_service", lambda args: SimpleNamespace(query=lambda q: result))
    code = cli.main(["--data-root", "/tmp/data", "ask", "休渔时间"])
    assert code == 0
    out = capsys.readouterr().out
    assert "结论：5月1日。" in out
    assert "依据摘录" not in out
    assert "完整证据" in out
    assert "POL-CLOS-015" in out


def test_ask_full_prints_the_evidence(monkeypatch, capsys) -> None:
    result = _result()
    monkeypatch.setattr(cli, "_service", lambda args: SimpleNamespace(query=lambda q: result))
    code = cli.main(["--data-root", "/tmp/data", "ask", "--full", "休渔时间"])
    assert code == 0
    out = capsys.readouterr().out
    assert "依据摘录" in out
    assert "POL-CLOS-015" in out


def test_check_delegates_to_the_public_tree_script(monkeypatch) -> None:
    seen = {}

    def fake_call(argv, cwd=None):  # noqa: ANN001
        seen["argv"] = argv
        seen["cwd"] = cwd
        return 0

    monkeypatch.setattr(cli.subprocess, "call", fake_call)
    assert cli.main(["check"]) == 0
    assert seen["argv"][-1].endswith("check_public_tree.py")
