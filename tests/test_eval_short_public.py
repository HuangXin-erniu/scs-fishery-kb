from __future__ import annotations

import importlib.util

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("pydantic")

from scs_fkb.config import REPO_ROOT  # noqa: E402
from scs_fkb.service_v2.schemas import CitationModel, QueryResponse  # noqa: E402


def _module():
    path = REPO_ROOT / "scripts" / "eval_short_public.py"
    spec = importlib.util.spec_from_file_location("eval_short_public", path)
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


def test_rate_handles_empty_and_mixed_rows() -> None:
    module = _module()
    assert module._rate([], "short") is None
    assert module._rate([{"short": True}, {"short": False}], "short") == 0.5


def test_hit_accepts_expected_document_or_prefix() -> None:
    module = _module()
    assert module._hit(_response(["POL-CLOS-015"]), {"expected_docs": ["POL-CLOS-015"]})
    assert module._hit(
        _response(["POL-GX-060"]), {"expected_docs": [], "expected_prefix": "POL-GX"}
    )
    assert not module._hit(_response([]), {"expected_docs": ["POL-CLOS-015"]})
