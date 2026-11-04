from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCT_MODULES = [
    "answer.py",
    "bm25.py",
    "candidates.py",
    "chunking.py",
    "claims.py",
    "corpus.py",
    "dense.py",
    "embed.py",
    "expand.py",
    "fusion.py",
    "ingest.py",
    "jurisdiction.py",
    "knowledge.py",
    "knowledge_build.py",
    "lexicon.py",
    "llm.py",
    "models.py",
    "patterns.py",
    "reference.py",
    "registry.py",
    "retrieve.py",
    "stats.py",
    "store.py",
    "text.py",
    "watch.py",
    "web.py",
]
PRODUCT_PACKAGES = ["parsers"]


def test_product_modules_do_not_read_eval_config() -> None:
    paths = [ROOT / "src" / "scs_fkb" / name for name in PRODUCT_MODULES]
    paths += [
        path
        for package in PRODUCT_PACKAGES
        for path in (ROOT / "src" / "scs_fkb" / package).glob("*.py")
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "eval.yaml" not in text, f"{path} reads eval.yaml"
        assert "configs/eval" not in text, f"{path} reads the eval config"
