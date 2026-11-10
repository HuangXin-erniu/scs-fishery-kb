from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

from scs_fkb.config import REPO_ROOT


def _module():
    path = REPO_ROOT / "scripts" / "check_rag_conformance.py"
    spec = importlib.util.spec_from_file_location("check_rag_conformance", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _tree(tmp_path: Path) -> Path:
    (tmp_path / "configs").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "configs" / "web-sources.yaml").write_text(
        yaml.safe_dump(
            {"allowlist": [{"domain": f"gov{index}.cn", "publisher": "p"} for index in range(10)]}
        ),
        encoding="utf-8",
    )
    (tmp_path / "configs" / "interface.yaml").write_text(
        yaml.safe_dump({"query": {"web_default": "off", "modes": ["kb_only", "kb_plus_web"]}}),
        encoding="utf-8",
    )
    (tmp_path / "configs" / "eval-accept.yaml").write_text(
        yaml.safe_dump(
            {
                "protocol": "v2",
                "thresholds": {
                    "a": {"max": 0.1},
                    "b": {"min": 0.9},
                    "c": {"min": 0.8},
                    "d": {"min": 0.9},
                    "e": {"min": 0.9},
                    "f": {"min": 0.85},
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "docs" / "rag-conformance.md").write_text(
        "\n".join(f"§{index} row" for index in range(1, 13)), encoding="utf-8"
    )
    return tmp_path


def test_conformance_passes_on_the_repository(capsys) -> None:
    module = _module()
    assert module.main([]) == 0
    capsys.readouterr()


def test_conformance_fails_when_the_matrix_is_missing(tmp_path: Path, monkeypatch, capsys) -> None:
    tree = _tree(tmp_path)
    (tree / "docs" / "rag-conformance.md").unlink()
    module = _module()
    monkeypatch.setattr(module, "REPO_ROOT", tree)
    assert module.main([]) == 1
    capsys.readouterr()
