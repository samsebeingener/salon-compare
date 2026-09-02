"""OpenAI-compatible LLM. Нет ключа — пустой ответ, без падения."""

from __future__ import annotations

import os
from typing import Protocol

import httpx

from salon_compare.proxy import httpx_client_kwargs

_TIMEOUT = 30.0


class LlmClient(Protocol):
    def complete(self, prompt: str) -> str: ...


class NullLlm:
    def complete(self, prompt: str) -> str:
        del prompt
        return ""


class OpenAiCompatLlm:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

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
            return ""
        if response.status_code >= 400:
            return ""
        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError):
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
