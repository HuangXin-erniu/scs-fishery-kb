from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load(name: str):
    return yaml.safe_load((ROOT / "configs" / name).read_text(encoding="utf-8"))


def test_corpus_registry_is_complete() -> None:
    data = load("corpus.yaml")
    sources = data["sources"]
    assert len(sources) == 100
    ids = [source["id"] for source in sources]
    assert len(ids) == len(set(ids))
    for source in sources:
        assert source["license"], source["id"]
        assert source["sensitivity"], source["id"]
        assert source["status"] in {"acquired", "candidate", "held", "dropped"}, source["id"]


def test_pipeline_documents_are_registered() -> None:
    pipeline = load("pipeline.yaml")["documents"]
    registered = {source["id"] for source in load("corpus.yaml")["sources"]}
    assert len(pipeline) == 61
    assert len(set(pipeline)) == 61
    assert set(pipeline) <= registered


def test_schema_and_acceptance_configs_load() -> None:
    assert load("schema.yaml")["schema_version"] == 1
    accept = load("eval-accept.yaml")
    assert accept["counts"]["questions"] == 512
    thresholds = accept["thresholds"]
    assert thresholds["point_coverage"]["min"] == 0.80
    assert thresholds["citation_accuracy"]["min"] == 0.90
    assert thresholds["basis_accuracy"]["min"] == 0.85
    assert thresholds["misanswer_rate"]["max"] == 0.10


def test_runtime_configs_load() -> None:
    for name in (
        "terms.yaml",
        "glossary-bridge.yaml",
        "lexicon.yaml",
        "answer-channels.yaml",
        "claims.yaml",
    ):
        data = load(name)
        assert data["schema_version"] == 1, name
    assert load("terms.yaml")["terms"]
    assert load("glossary-bridge.yaml")["terms"]
    assert load("lexicon.yaml")["groups"]
    assert load("answer-channels.yaml")["default"]
    assert load("claims.yaml")["natures"]


def test_corpus_gaps_are_recorded() -> None:
    gaps = load("corpus.yaml")["gaps"]
    assert gaps
    assert all(isinstance(item, (str, dict)) for item in gaps)


def test_retired_configs_are_gone() -> None:
    for name in (
        "eval.yaml",
        "eval-v2.yaml",
        "web-cards.yaml",
        "web-sources.yaml",
        "statistics.yaml",
        "candidates.yaml",
        "faq.yaml",
        "source-watch.yaml",
        "species-seed.yaml",
        "cwp-handbook.yaml",
        "reference-collections.yaml",
        "sc-standards.yaml",
    ):
        assert not (ROOT / "configs" / name).exists(), name
