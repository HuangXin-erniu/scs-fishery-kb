from __future__ import annotations

import json

import httpx
import pytest
from openai import APITimeoutError

from scs_fkb import llm
from scs_fkb.llm import LLMClient, LLMConfig, LLMConfigError, LLMTimeoutError


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


def _reply(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def test_trace_records_stage_without_prompt_text(monkeypatch, tmp_path) -> None:
    trace = tmp_path / "trace.jsonl"
    monkeypatch.setenv("SCS_FKB_LLM_TRACE", str(trace))
    monkeypatch.setenv("SCS_FKB_TRACE_ID", "Q-001")

    def handler(request: httpx.Request) -> httpx.Response:
        return _reply("正常")

    client = LLMClient(_config(), http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert (
        client.chat([{"role": "user", "content": "私有问题正文"}], max_tokens=32, stage="standard")
        == "正常"
    )
    rows = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["stage"] == "standard"
    assert rows[0]["question_id"] == "Q-001"
    assert rows[0]["outcome"] == "ok"
    assert rows[0]["prompt_chars"] == len("私有问题正文")
    assert "私有问题正文" not in trace.read_text(encoding="utf-8")


def test_timeout_raises_dedicated_error(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("SCS_FKB_LLM_TRACE", str(tmp_path / "trace.jsonl"))

    def handler(request: httpx.Request) -> httpx.Response:
        raise APITimeoutError(request=request)

    client = LLMClient(_config(), http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(LLMTimeoutError):
        client.chat([{"role": "user", "content": "hi"}], stage="probe_long")
    rows = [
        json.loads(line)
        for line in (tmp_path / "trace.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert rows[0]["outcome"] == "timeout"


def test_default_deadline_and_retry_are_tight(monkeypatch) -> None:
    monkeypatch.setattr(llm, "load_dotenv", lambda: None)
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_API_KEY", "secret")
    monkeypatch.setenv("LLM_MODEL", "deepseek-v4.1-flash")
    monkeypatch.delenv("LLM_TIMEOUT", raising=False)
    monkeypatch.delenv("LLM_MAX_RETRIES", raising=False)
    config = LLMConfig.from_env()
    assert config.timeout == 30.0
    assert config.max_retries == 1


def test_invalid_timeout_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(llm, "load_dotenv", lambda: None)
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_API_KEY", "secret")
    monkeypatch.setenv("LLM_MODEL", "deepseek-v4.1-flash")
    monkeypatch.setenv("LLM_TIMEOUT", "0")
    with pytest.raises(LLMConfigError):
        LLMConfig.from_env()
