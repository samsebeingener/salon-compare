"""OpenAI-compatible LLM. Нет ключа — пустой ответ, без падения."""

from __future__ import annotations

import os
from typing import Protocol

import httpx
from pydantic import BaseModel

from salon_compare.llm_log import log_llm_event
from salon_compare.proxy import llm_httpx_client_kwargs

_TIMEOUT = 30.0
_DEFAULT_SYSTEM = "Отвечай только JSON без пояснений."


class LlmUsage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost: float | None = None


class LlmClient(Protocol):
    def complete(self, prompt: str, *, system: str | None = None) -> str: ...

    def last_usage(self) -> LlmUsage: ...

    def last_error(self) -> str | None: ...


def _as_int(raw: object) -> int | None:
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float) and raw.is_integer():
        return int(raw)
    return None


def _as_float(raw: object) -> float | None:
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int | float):
        return float(raw)
    return None


def usage_from_response(payload: object) -> LlmUsage:
    if not isinstance(payload, dict):
        return LlmUsage()
    raw = payload.get("usage")
    if not isinstance(raw, dict):
        return LlmUsage()
    prompt = _as_int(raw.get("prompt_tokens"))
    completion = _as_int(raw.get("completion_tokens"))
    total = _as_int(raw.get("total_tokens"))
    if total is None and (prompt is not None or completion is not None):
        total = (prompt or 0) + (completion or 0)
    cost = _as_float(raw.get("cost"))
    if cost is None:
        cost = _as_float(raw.get("total_cost"))
    return LlmUsage(
        prompt_tokens=prompt,
        completion_tokens=completion,
        total_tokens=total,
        cost=cost,
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
    if usage.cost is not None:
        return usage.cost
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
    def complete(self, prompt: str, *, system: str | None = None) -> str:
        del prompt, system
        return ""

    def last_usage(self) -> LlmUsage:
        return LlmUsage()

    def last_error(self) -> str | None:
        return None


class OpenAiCompatLlm:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._usage = LlmUsage()
        self._last_error: str | None = None

    def last_usage(self) -> LlmUsage:
        return self._usage

    def last_error(self) -> str | None:
        return self._last_error

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        self._last_error = None
        url = f"{self.base_url}/chat/completions"
        system_text = system if system else _DEFAULT_SYSTEM
        log_llm_event(
            "request",
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            url=url,
            llm_direct=os.environ.get("LLM_DIRECT", ""),
            system=system_text,
            user_prompt=prompt,
        )
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
                        {"role": "system", "content": system_text},
                        {"role": "user", "content": prompt},
                    ],
                },
                timeout=_TIMEOUT,
                **llm_httpx_client_kwargs(),
            )
        except httpx.HTTPError as exc:
            self._usage = LlmUsage()
            self._last_error = f"сеть: {exc.__class__.__name__}"
            log_llm_event(
                "error",
                model=self.model,
                error=self._last_error,
                detail=str(exc),
            )
            return ""
        if response.status_code >= 400:
            self._usage = LlmUsage()
            body = response.text.strip()
            if len(body) > 120:
                body = body[:117] + "..."
            self._last_error = f"HTTP {response.status_code}: {body or 'пустой ответ'}"
            log_llm_event(
                "error",
                model=self.model,
                status_code=response.status_code,
                error=self._last_error,
                response_text=response.text,
            )
            return ""
        try:
            data = response.json()
        except ValueError:
            self._usage = LlmUsage()
            self._last_error = "ответ API не JSON"
            log_llm_event(
                "error",
                model=self.model,
                error=self._last_error,
                response_text=response.text,
            )
            return ""
        self._usage = usage_from_response(data)
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            self._last_error = "в ответе API нет choices[0].message.content"
            log_llm_event(
                "error",
                model=self.model,
                error=self._last_error,
                response_json=data,
            )
            return ""
        if not isinstance(content, str):
            self._last_error = "content ответа не строка"
            log_llm_event("error", model=self.model, error=self._last_error)
            return ""
        log_llm_event(
            "response",
            model=self.model,
            status_code=response.status_code,
            usage=self._usage.model_dump(),
            response_text=content,
        )
        return content


def make_llm() -> LlmClient:
    key = os.environ.get("LLM_API_KEY", "").strip()
    base = os.environ.get("LLM_BASE_URL", "").strip()
    model = os.environ.get("LLM_MODEL", "").strip()
    if not key or not base or not model:
        log_llm_event(
            "skipped",
            reason="missing LLM_API_KEY, LLM_BASE_URL or LLM_MODEL",
            has_key=bool(key),
            has_base=bool(base),
            has_model=bool(model),
        )
        return NullLlm()
    log_llm_event("client_ready", base_url=base, model=model, api_key=key)
    return OpenAiCompatLlm(key, base, model)
