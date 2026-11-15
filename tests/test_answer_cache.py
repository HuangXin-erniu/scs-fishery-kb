from __future__ import annotations

from datetime import UTC, datetime, timedelta

from scs_fkb.answer_v3.cache import AnswerCache, question_key


class FakeEncoder:
    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self.vectors = vectors

    def embed_query(self, text: str) -> list[float]:
        return self.vectors.get(text, [0.0, 0.0, 0.0])


def _payload(text: str = "答案") -> dict:
    return {"answer": text, "citations": [], "evidence": [], "confidence": 0.9}


def test_exact_key_roundtrip(tmp_path) -> None:
    cache = AnswerCache(tmp_path)
    key = question_key("休渔时间", index_version="idx-1")
    cache.put(key, _payload("5月1日"), question="休渔时间", index_version="idx-1")
    hit = cache.get(key, question="休渔时间", index_version="idx-1")
    assert hit is not None
    assert hit["answer"] == "5月1日"
    assert hit["cache"]["hit"] is True
    assert hit["cache"]["type"] == "exact"


def test_index_version_invalidates(tmp_path) -> None:
    cache = AnswerCache(tmp_path)
    key = question_key("休渔时间", index_version="idx-1")
    cache.put(key, _payload(), question="休渔时间", index_version="idx-1")
    assert cache.get(key, question="休渔时间", index_version="idx-2") is None


def test_ttl_invalidates(tmp_path) -> None:
    cache = AnswerCache(tmp_path, ttl_days=0)
    key = question_key("休渔时间")
    cache.put(key, _payload(), question="休渔时间")
    later = datetime.now(UTC) + timedelta(seconds=5)
    assert cache.get(key, question="休渔时间", now=later) is None


def test_semantic_lookup_uses_embedding(tmp_path) -> None:
    encoder = FakeEncoder(
        {
            "休渔时间": [1.0, 0.0, 0.0],
            "今年什么时候休渔": [0.99, 0.01, 0.0],
            "许可证怎么办": [0.0, 1.0, 0.0],
        }
    )
    cache = AnswerCache(tmp_path, encoder=encoder, threshold=0.95)
    key = question_key("休渔时间")
    cache.put(key, _payload("5月1日"), question="休渔时间")
    hit = cache.get("different-key", question="今年什么时候休渔")
    assert hit is not None
    assert hit["cache"]["type"] == "semantic"
    assert hit["answer"] == "5月1日"
    assert cache.get("different-key", question="许可证怎么办") is None


def test_question_key_is_stable_and_sensitive() -> None:
    base = question_key("休渔时间", persona="captain", index_version="idx-1")
    assert base == question_key("休渔时间", persona="captain", index_version="idx-1")
    assert base != question_key("休渔时间", persona="owner", index_version="idx-1")
    assert base != question_key("休渔时间", persona="captain", index_version="idx-2")
    assert base != question_key(" 休渔时间\n", persona="captain")
