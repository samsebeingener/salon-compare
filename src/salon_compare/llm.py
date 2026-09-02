"""OpenAI-compatible LLM. Нет ключа — пустой ответ, без падения."""

from __future__ import annotations

import os
from typing import Protocol

import httpx
from pydantic import BaseModel

from salon_compare.proxy import httpx_client_kwargs

_TIMEOUT = 30.0


class LlmUsage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None

    @property
    def total_tokens(self) -> int | None:
        if self.prompt_tokens is None and self.completion_tokens is None:
            return None
        return (self.prompt_tokens or 0) + (self.completion_tokens or 0)


class LlmClient(Protocol):
    def complete(self, prompt: str) -> str: ...

    def last_usage(self) -> LlmUsage: ...


def usage_from_response(payload: object) -> LlmUsage:
    if not isinstance(payload, dict):
        return LlmUsage()
    raw = payload.get("usage")
    if not isinstance(raw, dict):
        return LlmUsage()
    prompt = raw.get("prompt_tokens")
    completion = raw.get("completion_tokens")
    return LlmUsage(
        prompt_tokens=prompt if isinstance(prompt, int) else None,
        completion_tokens=completion if isinstance(completion, int) else None,
    )


def _env_rate(name: str) -> float | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def estimate_usd(
    usage: LlmUsage,
    prompt_rate: float | None = None,
    completion_rate: float | None = None,
) -> float | None:
    in_rate = (
        prompt_rate if prompt_rate is not None else _env_rate("LLM_USD_PER_1M_PROMPT")
    )
    out_rate = (
        completion_rate
        if completion_rate is not None
        else _env_rate("LLM_USD_PER_1M_COMPLETION")
    )
    if (
        in_rate is None
        or out_rate is None
        or usage.prompt_tokens is None
        or usage.completion_tokens is None
    ):
        return None
    return round(
        (usage.prompt_tokens / 1_000_000) * in_rate
        + (usage.completion_tokens / 1_000_000) * out_rate,
        6,
    )


class NullLlm:
    def complete(self, prompt: str) -> str:
        del prompt
        return ""

    def last_usage(self) -> LlmUsage:
        return LlmUsage()


class OpenAiCompatLlm:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._usage = LlmUsage()

    def last_usage(self) -> LlmUsage:
        return self._usage

    def complete(self, prompt: str) -> str:
        url = f"{self.base_url}/chat/completions"
        try:
            response = httpx.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Отвечай только JSON без пояснений.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                },
                timeout=_TIMEOUT,
                **httpx_client_kwargs(),
            )
        except httpx.HTTPError:
            self._usage = LlmUsage()
            return ""
        if response.status_code >= 400:
            self._usage = LlmUsage()
            return ""
        try:
            data = response.json()
        except ValueError:
            self._usage = LlmUsage()
            return ""
        self._usage = usage_from_response(data)
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return ""
        if not isinstance(content, str):
            return ""
        return content


def make_llm() -> LlmClient:
    key = os.environ.get("LLM_API_KEY", "").strip()
    base = os.environ.get("LLM_BASE_URL", "").strip()
    model = os.environ.get("LLM_MODEL", "").strip()
    if not key or not base or not model:
        return NullLlm()
    return OpenAiCompatLlm(key, base, model)
