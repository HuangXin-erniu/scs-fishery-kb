from __future__ import annotations

import http.client
import json
import os
import time
import uuid
from dataclasses import dataclass
from urllib import error, request

from .config import load_dotenv
from .web import _tls_context

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
    """Small OpenAI-compatible chat client with a stable OpenCode session."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self.calls = 0

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1200,
    ) -> str:
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "reasoning_effort": self.config.reasoning_effort,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "scs-fkb/0.1",
            "x-opencode-session": self.config.session,
        }
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries + 1):
            try:
                req = request.Request(
                    f"{self.config.base_url}/chat/completions",
                    data=body,
                    headers=headers,
                    method="POST",
                )
                with request.urlopen(
                    req, timeout=self.config.timeout, context=_tls_context()
                ) as response:
                    raw = response.read().decode("utf-8")
                parsed = json.loads(raw)
                content = parsed["choices"][0]["message"]["content"]
                if not isinstance(content, str) or not content.strip():
                    raise LLMError("model returned an empty completion")
                self.calls += 1
                return content
            except (
                error.HTTPError,
                error.URLError,
                http.client.HTTPException,
                ConnectionError,
                TimeoutError,
                json.JSONDecodeError,
                KeyError,
                IndexError,
            ) as exc:
                last_error = exc
                if attempt < self.config.max_retries:
                    time.sleep(1.5 * (attempt + 1))
        raise LLMError(
            f"LLM request failed after {self.config.max_retries + 1} attempts: {last_error}"
        )

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
