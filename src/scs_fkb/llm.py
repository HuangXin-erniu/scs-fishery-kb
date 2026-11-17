from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from openai import APITimeoutError, OpenAI, OpenAIError

from .config import load_dotenv

PROMPT_VERSION = "rag-v3"


class LLMError(RuntimeError):
    """Raised when the configured LLM endpoint cannot be used."""


class LLMTimeoutError(LLMError):
    """Raised when one completion attempt exceeds its deadline."""


class LLMConfigError(LLMError):
    """Raised when the LLM environment is incomplete."""


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    api_key: str
    model: str
    reasoning_effort: str = "low"
    session: str = ""
    timeout: float = 30.0
    max_retries: int = 1

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
        raw_timeout = os.environ.get("LLM_TIMEOUT", "30").strip() or "30"
        raw_retries = os.environ.get("LLM_MAX_RETRIES", "1").strip() or "1"
        try:
            timeout = float(raw_timeout)
        except ValueError as exc:
            raise LLMConfigError(f"invalid LLM_TIMEOUT: {raw_timeout!r}") from exc
        try:
            max_retries = int(raw_retries)
        except ValueError as exc:
            raise LLMConfigError(f"invalid LLM_MAX_RETRIES: {raw_retries!r}") from exc
        if timeout <= 0:
            raise LLMConfigError("LLM_TIMEOUT must be positive")
        if max_retries < 0:
            raise LLMConfigError("LLM_MAX_RETRIES must be non-negative")
        session = os.environ.get("SCS_FKB_LLM_SESSION", "").strip()
        return cls(
            base_url=base_url,
            api_key=api_key,
            model=model,
            reasoning_effort=os.environ.get("LLM_REASONING_EFFORT", "low").strip() or "low",
            session=session or f"scs-fkb-{uuid.uuid4().hex[:12]}",
            timeout=timeout,
            max_retries=max_retries,
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
        self.trace_path = os.environ.get("SCS_FKB_LLM_TRACE", "").strip() or None
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

    def _trace(
        self,
        *,
        stage: str,
        prompt_chars: int,
        max_tokens: int,
        attempt: int,
        elapsed_ms: int,
        outcome: str,
        error: str = "",
    ) -> None:
        """Append one metadata-only call record; never write prompt text or keys."""
        if not self.trace_path:
            return
        record = {
            "ts": datetime.now(UTC).isoformat(timespec="seconds"),
            "question_id": os.environ.get("SCS_FKB_TRACE_ID", ""),
            "stage": stage or "unspecified",
            "model": self.config.model,
            "prompt_chars": prompt_chars,
            "max_tokens": max_tokens,
            "attempt": attempt,
            "elapsed_ms": elapsed_ms,
            "outcome": outcome,
        }
        if error:
            record["error"] = error
        try:
            fd = os.open(self.trace_path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o644)
            try:
                line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
                os.write(fd, line.encode("utf-8"))
            finally:
                os.close(fd)
        except OSError:
            return

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1200,
        stage: str = "",
    ) -> str:
        extra_body = (
            {"reasoning_effort": self.config.reasoning_effort}
            if self.config.reasoning_effort
            else None
        )
        budget = int(max_tokens)
        prompt_chars = sum(len(str(message.get("content") or "")) for message in messages)
        for attempt in range(1, 3):
            started = time.perf_counter()
            try:
                response = self._client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=budget,
                    extra_body=extra_body,
                )
            except OpenAIError as exc:
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                timed_out = isinstance(exc, APITimeoutError)
                self._trace(
                    stage=stage,
                    prompt_chars=prompt_chars,
                    max_tokens=budget,
                    attempt=attempt,
                    elapsed_ms=elapsed_ms,
                    outcome="timeout" if timed_out else "error",
                    error=type(exc).__name__,
                )
                message = f"LLM request failed: {type(exc).__name__}: {exc}"
                if timed_out:
                    raise LLMTimeoutError(message) from exc
                raise LLMError(message) from exc
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            content = response.choices[0].message.content if response.choices else None
            if isinstance(content, str) and content.strip():
                self.calls += 1
                self._trace(
                    stage=stage,
                    prompt_chars=prompt_chars,
                    max_tokens=budget,
                    attempt=attempt,
                    elapsed_ms=elapsed_ms,
                    outcome="ok",
                )
                return content
            self._trace(
                stage=stage,
                prompt_chars=prompt_chars,
                max_tokens=budget,
                attempt=attempt,
                elapsed_ms=elapsed_ms,
                outcome="empty",
            )
            budget = max(budget, 1500)
        raise LLMError(f"model returned an empty completion after 2 attempts ({stage or 'call'})")

    def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1200,
        stage: str = "",
    ) -> dict:
        return parse_json_object(
            self.chat(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stage=stage,
            )
        )
