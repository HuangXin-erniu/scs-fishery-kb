from __future__ import annotations

import importlib.util

import pytest
import yaml

pytest.importorskip("fastapi")
pytest.importorskip("pydantic")

from scs_fkb.config import REPO_ROOT  # noqa: E402
from scs_fkb.service_v2.schemas import CitationModel, QueryResponse  # noqa: E402


def _module():
    path = REPO_ROOT / "scripts" / "eval_public.py"
    spec = importlib.util.spec_from_file_location("eval_public", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _response(docs: list[str]) -> QueryResponse:
    return QueryResponse(
        request_id="REQ-1",
        answer="x",
        citations=[CitationModel(doc_id=doc, title=doc, snippet="x") for doc in docs],
    )


def test_hit_matches_an_expected_document_or_prefix() -> None:
    module = _module()
    row = {"expected_docs": ["POL-CLOS-015"], "expected_prefix": ""}
    assert module._hit(_response(["POL-CLOS-015"]), row) is True
    assert module._hit(_response(["POL-LAW-009"]), row) is False
    assert module._hit(_response([]), row) is False

    prefix_row = {"expected_docs": [], "expected_prefix": "STAT-YB-"}
    assert module._hit(_response(["STAT-YB-2018"]), prefix_row) is True


def test_public_set_is_public_and_complete() -> None:
    data = yaml.safe_load((REPO_ROOT / "configs" / "eval-public.yaml").read_text(encoding="utf-8"))
    entries = data["entries"]
    assert len(entries) == 60
    assert sum(1 for row in entries if row["type"] == "abstain") == 13
    assert sum(1 for row in entries if row.get("reference_answer")) == 12
    text = (REPO_ROOT / "configs" / "eval-public.yaml").read_text(encoding="utf-8")
    assert "acceptance" not in text.lower()
