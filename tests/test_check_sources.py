from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

from scs_fkb.config import REPO_ROOT


def _module():
    path = REPO_ROOT / "scripts" / "check_sources.py"
    spec = importlib.util.spec_from_file_location("check_sources", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _copy_registry(tmp_path: Path) -> Path:
    data = yaml.safe_load((REPO_ROOT / "configs" / "corpus.yaml").read_text(encoding="utf-8"))
    target = tmp_path / "corpus.yaml"
    target.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return target


def test_current_registry_passes_at_an_early_date(capsys) -> None:
    module = _module()
    assert module.main(["--today", "2020-01-01", "--json"]) == 0
    capsys.readouterr()


def test_overdue_source_fails(tmp_path: Path, capsys) -> None:
    path = _copy_registry(tmp_path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    first = data["sources"][0]
    first["currency"]["as_of"] = "2020-01-01"
    first["currency"]["review_due"] = "2020-01-02"
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    module = _module()
    code = module.main(
        [
            "--today",
            "2026-11-10",
            "--registry",
            str(path),
            "--watch",
            str(REPO_ROOT / "configs" / "source-watch.yaml"),
            "--candidates",
            str(REPO_ROOT / "configs" / "candidates.yaml"),
            "--json",
        ]
    )
    out = capsys.readouterr().out
    assert code == 1
    assert "overdue" in out


def test_unknown_watch_ref_fails(tmp_path: Path, capsys) -> None:
    path = _copy_registry(tmp_path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["sources"][0]["watch_ref"] = "WATCH-NOT-REAL"
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    module = _module()
    code = module.main(
        [
            "--today",
            "2026-11-10",
            "--registry",
            str(path),
            "--watch",
            str(REPO_ROOT / "configs" / "source-watch.yaml"),
            "--candidates",
            str(REPO_ROOT / "configs" / "candidates.yaml"),
        ]
    )
    captured = capsys.readouterr()
    assert code == 1
    assert "watch" in (captured.out + captured.err)
