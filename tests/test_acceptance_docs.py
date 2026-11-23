from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_acceptance_docs import check  # noqa: E402


def _config(tmp_path: Path, required: dict, forbidden: dict) -> Path:
    path = tmp_path / "acceptance.yaml"
    path.write_text(
        yaml.safe_dump({"required": required, "forbidden": forbidden}, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def test_required_and_forbidden(tmp_path: Path) -> None:
    (tmp_path / "acceptance.md").write_text("index bfe11941886a\n", encoding="utf-8")
    config = _config(
        tmp_path,
        {"acceptance.md": ["bfe11941886a"]},
        {"acceptance.md": ["251dbf67e804"]},
    )
    assert check(tmp_path, config) == []


def test_missing_required_and_stale(tmp_path: Path) -> None:
    (tmp_path / "acceptance.md").write_text("index 251dbf67e804\n", encoding="utf-8")
    config = _config(
        tmp_path,
        {"acceptance.md": ["bfe11941886a"]},
        {"acceptance.md": ["251dbf67e804"]},
    )
    errors = check(tmp_path, config)
    assert len(errors) == 2
    assert any("missing required" in error for error in errors)
    assert any("stale text" in error for error in errors)


def test_missing_file_is_reported(tmp_path: Path) -> None:
    config = _config(tmp_path, {"missing.md": ["x"]}, {})
    try:
        check(tmp_path, config)
    except FileNotFoundError as exc:
        assert "missing.md" in str(exc)
    else:  # pragma: no cover - the checker must not silently pass
        raise AssertionError("missing document was not reported")
