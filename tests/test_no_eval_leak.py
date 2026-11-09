from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL_ONLY = {"cli.py", "coverage.py", "__main__.py"}
PRODUCT_PACKAGES = [
    "answer_v3",
    "ingest_v2",
    "index_v2",
    "knowledge_v2",
    "parsers",
    "retrieve_v2",
    "service_v2",
]


def _product_paths() -> list[Path]:
    modules = [
        path for path in (ROOT / "src" / "scs_fkb").glob("*.py") if path.name not in EVAL_ONLY
    ]
    packages = [
        path
        for package in PRODUCT_PACKAGES
        for path in (ROOT / "src" / "scs_fkb" / package).glob("*.py")
    ]
    return modules + packages


def test_product_modules_do_not_read_eval_config() -> None:
    for path in _product_paths():
        text = path.read_text(encoding="utf-8")
        assert "eval.yaml" not in text, f"{path} reads a retired eval config"
        assert "configs/eval" not in text, f"{path} reads a retired eval config"


PRIVATE_INSTRUMENT_MARKERS = (
    "doc-map.yaml",
    "dataset.jsonl",
    "eval/acceptance",
)


def test_product_code_does_not_read_the_private_instrument() -> None:
    for path in _product_paths():
        text = path.read_text(encoding="utf-8")
        for marker in PRIVATE_INSTRUMENT_MARKERS:
            assert marker not in text, f"{path} references the private instrument ({marker})"
