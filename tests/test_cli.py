from __future__ import annotations

from pathlib import Path

import yaml

from scs_fkb import cli


class _FakeRetriever:
    def search(self, query, top_k=5, sensitivity_ceiling=None):
        return []


def test_retrieve_passes_the_data_root(monkeypatch, tmp_path):
    seen: dict[str, object] = {}

    def fake_retriever(chunks, manifest, pipeline, lexicon=None, root=None):
        seen["root"] = root
        return _FakeRetriever()

    monkeypatch.setattr(cli, "load_chunks", lambda root: ([], {"index_version": "test"}))
    monkeypatch.setattr(cli, "_lexicon_for", lambda args: [])
    monkeypatch.setattr(cli, "_retriever", fake_retriever)

    code = cli.main(["retrieve", "南海区伏季休渔", "--data-root", str(tmp_path), "--json"])

    assert code == 0
    assert seen["root"] == tmp_path


def _write_corpus(tmp_path: Path, *, cadence: str | None = "monthly") -> Path:
    currency = {
        "as_of": "2026-11-03",
        "basis": "publication",
        "review_due": "2026-12-03",
    }
    if cadence is not None:
        currency["cadence"] = cadence
    path = tmp_path / "corpus.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "sources": [
                    {
                        "id": "POL-TEST-001",
                        "title": "test",
                        "level": "national",
                        "authority_tier": "A",
                        "source_class": "normative",
                        "license": "public",
                        "sensitivity": "public",
                        "status": "acquired",
                        "currency": currency,
                        "retrieval": {
                            "channel": "collection",
                            "parseable": True,
                            "note": "test",
                        },
                        "lifecycle": "active",
                    }
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return path


def _write_candidates(tmp_path: Path, items: list[dict] | None = None) -> Path:
    path = tmp_path / "candidates.yaml"
    path.write_text(
        yaml.safe_dump({"schema_version": 1, "candidates": items or []}, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def _write_watch(tmp_path: Path) -> Path:
    path = tmp_path / "watch.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "defaults": {"timeout_seconds": 1, "user_agent": "test"},
                "sources": [
                    {
                        "id": "WATCH-TEST-1",
                        "url": "https://example.org/a",
                        "authority": "A",
                        "publisher": "Test publisher",
                        "status": "changed",
                        "sha256": "a" * 64,
                    }
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return path


def test_sources_check_exit_codes(tmp_path: Path, capsys) -> None:
    corpus = _write_corpus(tmp_path)
    candidates = _write_candidates(tmp_path)
    code = cli.main(
        [
            "sources",
            "check",
            "--config",
            str(corpus),
            "--candidates",
            str(candidates),
            "--today",
            "2026-11-04",
        ]
    )
    assert code == 0
    code = cli.main(
        [
            "sources",
            "check",
            "--config",
            str(corpus),
            "--candidates",
            str(candidates),
            "--today",
            "2027-01-15",
        ]
    )
    assert code == 1
    assert "overdue" in capsys.readouterr().out


def test_sources_check_rejects_missing_cadence(tmp_path: Path, capsys) -> None:
    corpus = _write_corpus(tmp_path, cadence=None)
    candidates = _write_candidates(tmp_path)
    code = cli.main(
        [
            "sources",
            "check",
            "--config",
            str(corpus),
            "--candidates",
            str(candidates),
            "--today",
            "2026-11-04",
        ]
    )
    assert code == 2
    assert "currency.cadence" in capsys.readouterr().err


def test_sources_check_fails_on_expired_candidate(tmp_path: Path, capsys) -> None:
    corpus = _write_corpus(tmp_path)
    candidates = _write_candidates(
        tmp_path,
        [
            {
                "id": "CAND-2026-001",
                "title": "Stale proposal",
                "url": "https://example.org/stale",
                "publisher": "Test publisher",
                "proposed_tier": "A",
                "proposed_class": "normative",
                "reason": "new",
                "watch_ref": None,
                "first_seen": "2026-04-01",
                "expires_at": "2026-10-01",
                "status": "open",
                "decision_key": None,
                "source_id": None,
                "note": "",
            }
        ],
    )
    code = cli.main(
        [
            "sources",
            "check",
            "--config",
            str(corpus),
            "--candidates",
            str(candidates),
            "--today",
            "2026-11-04",
        ]
    )
    assert code == 1
    assert "expired" in capsys.readouterr().out


def test_watch_propose_does_not_write_configs(tmp_path: Path, capsys) -> None:
    watch = _write_watch(tmp_path)
    candidates = _write_candidates(tmp_path)
    corpus = Path("configs/corpus.yaml")
    before_watch = watch.read_bytes()
    before_candidates = candidates.read_bytes()
    before_corpus = corpus.read_bytes()
    code = cli.main(
        [
            "watch",
            "--offline",
            "--propose",
            "--config",
            str(watch),
            "--candidates",
            str(candidates),
            "--today",
            "2026-11-04",
            "--json",
        ]
    )
    assert code == 0
    assert watch.read_bytes() == before_watch
    assert candidates.read_bytes() == before_candidates
    assert corpus.read_bytes() == before_corpus
    assert "CAND-2026-001" in capsys.readouterr().out


def test_facts_check_reports_zero_and_failure(monkeypatch, capsys) -> None:
    clean = {
        "facts": 80,
        "approved": 80,
        "draft": 0,
        "errors": [],
        "conflicts": [],
        "expired": [],
        "due": [],
        "today": "2026-11-04",
    }
    monkeypatch.setattr(cli, "check_facts", lambda *args, **kwargs: clean)
    assert cli.main(["facts", "check", "--data-root", "/tmp"]) == 0
    bad = {**clean, "errors": ["FACT-POLICY-001: evidence is wrong"]}
    monkeypatch.setattr(cli, "check_facts", lambda *args, **kwargs: bad)
    assert cli.main(["facts", "check", "--data-root", "/tmp"]) == 1
    assert "FACT-POLICY-001" in capsys.readouterr().out


def test_terms_and_faq_checks_return_zero(monkeypatch) -> None:
    monkeypatch.setattr(
        cli, "check_terms", lambda *args, **kwargs: {"terms": 24, "approved": 24, "errors": []}
    )
    monkeypatch.setattr(
        cli, "check_faqs", lambda *args, **kwargs: {"faqs": 12, "approved": 12, "errors": []}
    )
    assert cli.main(["terms", "check", "--data-root", "/tmp"]) == 0
    assert cli.main(["faq", "check"]) == 0
