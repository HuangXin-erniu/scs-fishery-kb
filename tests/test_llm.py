from __future__ import annotations

import json

import httpx
import pytest

from scs_fkb import llm
from scs_fkb.llm import LLMClient, LLMConfig, LLMConfigError, LLMError, parse_json_object


def _config(**overrides) -> LLMConfig:
    values = {
        "base_url": "https://example.test/v1",
        "api_key": "secret",
        "model": "deepseek-v4.1-flash",
        "reasoning_effort": "low",
        "session": "s1",
        "timeout": 5.0,
        "max_retries": 0,
    }
    values.update(overrides)
    return LLMConfig(**values)


def _client(handler, **overrides) -> LLMClient:
    return LLMClient(
        _config(**overrides), http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )


def _reply(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def test_missing_config_raises(monkeypatch) -> None:
    monkeypatch.setattr(llm, "load_dotenv", lambda: None)
    for name in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(LLMConfigError, match="LLM_BASE_URL"):
        LLMConfig.from_env()


def test_chat_sends_openai_payload_and_session() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["auth"] = request.headers.get("authorization")
        captured["session"] = request.headers.get("x-opencode-session")
        captured["body"] = json.loads(request.content)
        return _reply("ok")

    client = _client(handler)
    assert client.chat([{"role": "user", "content": "hi"}]) == "ok"
    assert captured["path"] == "/v1/chat/completions"
    assert captured["auth"] == "Bearer secret"
    assert captured["session"] == "s1"
    assert captured["body"]["model"] == "deepseek-v4.1-flash"
    assert captured["body"]["reasoning_effort"] == "low"


def test_empty_completion_is_retried_with_a_bigger_budget() -> None:
    budgets: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        budgets.append(body["max_tokens"])
        return _reply("" if len(budgets) == 1 else "recovered")

    client = _client(handler)
    assert client.chat([{"role": "user", "content": "hi"}], max_tokens=64) == "recovered"
    assert len(budgets) == 2
    assert budgets[1] >= 1500


def test_http_error_becomes_llm_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "bad key"}})

    client = _client(handler)
    with pytest.raises(LLMError, match="LLM request failed"):
        client.chat([{"role": "user", "content": "hi"}])


def test_parse_json_object_tolerates_fences() -> None:
    assert parse_json_object('```json\n{"answerable": false}\n```') == {"answerable": False}
    with pytest.raises(LLMError):
        parse_json_object("no json here")
