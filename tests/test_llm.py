from __future__ import annotations

import json

import pytest

from scs_fkb import llm
from scs_fkb.llm import LLMClient, LLMConfig, LLMConfigError, LLMError, parse_json_object


class _Response:
    def __init__(self, payload: dict) -> None:
        self.payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_missing_config_raises(monkeypatch) -> None:
    monkeypatch.setattr(llm, "load_dotenv", lambda: None)
    for name in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(LLMConfigError, match="LLM_BASE_URL"):
        LLMConfig.from_env()


def test_chat_sends_openai_payload_and_session(monkeypatch) -> None:
    captured: dict = {}

    def fake_urlopen(req, timeout, context=None):
        captured["url"] = req.full_url
        captured["auth"] = req.get_header("Authorization")
        captured["session"] = req.get_header("X-opencode-session")
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        return _Response({"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr(llm.request, "urlopen", fake_urlopen)
    client = LLMClient(
        LLMConfig(
            base_url="https://example.test/v1",
            api_key="secret",
            model="deepseek-v4.1-flash",
            reasoning_effort="low",
            session="s1",
        )
    )
    assert client.chat([{"role": "user", "content": "hi"}]) == "ok"
    assert captured["url"] == "https://example.test/v1/chat/completions"
    assert captured["auth"] == "Bearer secret"
    assert captured["session"] == "s1"
    assert captured["payload"]["reasoning_effort"] == "low"
    assert captured["payload"]["model"] == "deepseek-v4.1-flash"


def test_parse_json_object_tolerates_fences() -> None:
    assert parse_json_object('```json\n{"answerable": false}\n```') == {"answerable": False}
    with pytest.raises(LLMError):
        parse_json_object("no json here")
