from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location(
        "capture_source", ROOT / "scripts" / "capture_source.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_slugify_normalizes_names() -> None:
    module = load_module()
    assert module.slugify("Maritime Traffic Safety Law") == "maritime-traffic-safety-law"
    assert module.slugify("A  B___c") == "a-b-c"
    assert module.slugify("") == "source"


def test_extension_for_content_types() -> None:
    module = load_module()
    assert module.extension_for("text/html; charset=utf-8", "https://x/a") == ".html"
    assert module.extension_for("application/pdf", "https://x/a") == ".pdf"
    assert module.extension_for("", "https://x/a.pdf") == ".pdf"


def test_check_url_enforces_https_and_allowlist() -> None:
    module = load_module()
    assert module.check_url("https://www.gov.cn/a") == "www.gov.cn"
    with pytest.raises(module.CaptureError):
        module.check_url("http://www.gov.cn/a")
    with pytest.raises(module.CaptureError):
        module.check_url("https://example.com/a")
    with pytest.raises(module.CaptureError):
        module.check_url("https://evilgov.cn/a")


def test_allow_http_only_for_gov_cn() -> None:
    module = load_module()
    assert module.check_url("http://www.gov.cn/a", allow_http=True) == "www.gov.cn"
    with pytest.raises(module.CaptureError):
        module.check_url("http://example.com/a", allow_http=True)


def test_sha256_and_snapshot_path() -> None:
    module = load_module()
    assert module.sha256_bytes(b"abc").startswith("ba7816bf")
    assert module.snapshot_path("POL-LAW-097", "law", ".html") == (
        "raw/POL-LAW-097/law.html"
    )


def test_provenance_block_records_transport(tmp_path: Path) -> None:
    module = load_module()
    target = tmp_path / "raw/POL-X-001/file.html"
    capture = module.Capture(
        source_id="POL-X-001",
        url="https://www.gov.cn/a",
        path=target,
        relative="raw/POL-X-001/file.html",
        sha256="a" * 64,
        bytes=12,
        mime="text/html",
        unchanged=False,
        transport="http",
    )
    block = capture.provenance(document_no="主席令1号", published_at="2021-04-29")
    assert "url: https://www.gov.cn/a" in block
    assert "document_no: 主席令1号" in block
    assert "transport: http" in block
    assert "transport_note" in block
    assert "sha256: " + "a" * 64 in block


def test_capture_refuses_to_overwrite_different_bytes(tmp_path: Path, monkeypatch) -> None:
    module = load_module()
    target = tmp_path / "raw/POL-X-001/file.html"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"old")

    monkeypatch.setattr(module, "fetch", lambda url, allow_http=False: (b"new", "text/html"))
    with pytest.raises(module.CaptureError):
        module.capture("https://www.gov.cn/a", "POL-X-001", tmp_path, slug="file")

    capture = module.capture(
        "https://www.gov.cn/a", "POL-X-001", tmp_path, slug="file", force=True
    )
    assert capture.unchanged is False
    assert target.read_bytes() == b"new"


def test_capture_reports_unchanged_for_same_bytes(tmp_path: Path, monkeypatch) -> None:
    module = load_module()
    target = tmp_path / "raw/POL-X-002/file.html"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"same")
    monkeypatch.setattr(module, "fetch", lambda url, allow_http=False: (b"same", "text/html"))
    capture = module.capture("https://www.gov.cn/a", "POL-X-002", tmp_path, slug="file")
    assert capture.unchanged is True
