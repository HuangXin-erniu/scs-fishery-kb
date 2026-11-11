from __future__ import annotations

import importlib.util

from scs_fkb.config import REPO_ROOT


def _module():
    path = REPO_ROOT / "scripts" / "eval_index_v2.py"
    spec = importlib.util.spec_from_file_location("eval_index_v2", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reachable_accepts_an_indexed_expected_document() -> None:
    module = _module()
    row = {"expected_docs": ["POL-CLOS-015"], "expected_prefix": ""}
    assert module._reachable(row, {"POL-CLOS-015", "POL-LAW-009"})


def test_reachable_accepts_an_indexed_prefix() -> None:
    module = _module()
    row = {"expected_docs": [], "expected_prefix": "STAT-YB-"}
    assert module._reachable(row, {"STAT-YB-2024"})


def test_unreachable_document_is_excluded() -> None:
    module = _module()
    row = {"expected_docs": ["STD-CWP-043"], "expected_prefix": ""}
    assert not module._reachable(row, {"POL-CLOS-015"})
