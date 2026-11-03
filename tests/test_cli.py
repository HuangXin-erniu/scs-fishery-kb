from __future__ import annotations

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
