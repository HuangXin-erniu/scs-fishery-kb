from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass

from openai import OpenAI, OpenAIError

from .config import load_dotenv

PROMPT_VERSION = "rag-v3"


class LLMError(RuntimeError):
    """Raised when the configured LLM endpoint cannot be used."""


class LLMConfigError(LLMError):
    """Raised when the LLM environment is incomplete."""


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    api_key: str
    model: str
    reasoning_effort: str = "low"
    session: str = ""
    timeout: float = 120.0
    max_retries: int = 2

    @classmethod
    def from_env(cls) -> LLMConfig:
        load_dotenv()
        base_url = os.environ.get("LLM_BASE_URL", "").strip().rstrip("/")
        api_key = os.environ.get("LLM_API_KEY", "").strip()
        model = os.environ.get("LLM_MODEL", "").strip()
        missing = [
            name
            for name, value in (
                ("LLM_BASE_URL", base_url),
                ("LLM_API_KEY", api_key),
                ("LLM_MODEL", model),
            )
            if not value
        ]
        if missing:
            raise LLMConfigError("missing LLM configuration: " + ", ".join(missing))
        timeout = float(os.environ.get("LLM_TIMEOUT", "120"))
        session = os.environ.get("SCS_FKB_LLM_SESSION", "").strip()
        return cls(
            base_url=base_url,
            api_key=api_key,
            model=model,
            reasoning_effort=os.environ.get("LLM_REASONING_EFFORT", "low").strip() or "low",
            session=session or f"scs-fkb-{uuid.uuid4().hex[:12]}",
            timeout=timeout,
        )


def parse_json_object(text: str) -> dict:
    """Parse a JSON object from a model reply, tolerating fences and prose."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        raise LLMError("model reply does not contain a JSON object")
    try:
        value = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMError(f"model reply is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise LLMError("model reply JSON is not an object")
    return value


class LLMClient:
    """OpenAI-compatible chat client built on the openai SDK."""

    def __init__(self, config: LLMConfig, *, http_client=None) -> None:
        self.config = config
        self.calls = 0
        self._client = OpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=config.timeout,
            max_retries=config.max_retries,
            default_headers={
                "User-Agent": "scs-fkb/0.1",
                "x-opencode-session": config.session,
            },
            http_client=http_client,
        )

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1200,
    ) -> str:
        extra_body = (
            {"reasoning_effort": self.config.reasoning_effort}
            if self.config.reasoning_effort
            else None
        )
        budget = int(max_tokens)
        for _attempt in range(2):
            try:
                response = self._client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=budget,
                    extra_body=extra_body,
                )
            except OpenAIError as exc:
                raise LLMError(f"LLM request failed: {type(exc).__name__}: {exc}") from exc
            content = response.choices[0].message.content if response.choices else None
            if isinstance(content, str) and content.strip():
                self.calls += 1
                return content
            budget = max(budget, 1500)
        raise LLMError("model returned an empty completion after 2 attempts")

    def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1200,
    ) -> dict:
        return parse_json_object(
            self.chat(messages, temperature=temperature, max_tokens=max_tokens)
        )
