"""OpenAI-compatible LLM. Нет ключа — пустой ответ, без падения."""

from __future__ import annotations

import os
from typing import Protocol
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel

from salon_compare.llm_log import log_llm_event
from salon_compare.proxy import llm_transport_attempts, proxy_public_labels

_TIMEOUT = 120.0
_DEFAULT_SYSTEM = "Отвечай только JSON без пояснений."


def chat_completions_url(base_url: str, model: str) -> str:
    """Kie: origin/{model}/v1/chat/completions. Иначе {base}/chat/completions."""
    parsed = urlparse(base_url if "://" in base_url else f"https://{base_url}")
    host = parsed.netloc.lower()
    if host == "api.kie.ai" or host.endswith(".kie.ai"):
        slug = model.strip().strip("/")
        if slug.endswith("-openai"):
            slug = slug[: -len("-openai")]
        origin = f"{parsed.scheme}://{parsed.netloc}"
        return f"{origin}/{slug}/v1/chat/completions"
    return f"{base_url.rstrip('/')}/chat/completions"


def chat_payload(model: str, system_text: str, prompt: str) -> dict[str, object]:
    """OpenAI-совместимое тело. stream=false: у Kie Gemini по умолчанию SSE."""
    return {
        "model": model,
        "stream": False,
        "include_thoughts": False,
        "reasoning_effort": "low",
        "messages": [
            {
                "role": "system",
                "content": [{"type": "text", "text": system_text}],
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}],
            },
        ],
    }


def unwrap_chat_response(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        return {}
    inner = payload.get("data")
    if isinstance(inner, dict) and "choices" in inner:
        return inner
    return payload


def choice_message_content(payload: dict[str, object]) -> object | None:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if not isinstance(message, dict):
        return None
    return message.get("content")


def message_content_to_str(raw: object) -> str | None:
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        parts: list[str] = []
        for item in raw:
            if isinstance(item, str):
                parts.append(item)
                continue
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text" and isinstance(item.get("text"), str):
                parts.append(item["text"])
        if parts:
            return "".join(parts)
    return None


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
    raw = os.environ.get(name, "").strip().lstrip("$").replace(" ", "")
    if not raw:
        return None
    if "," in raw and "." not in raw:
        raw = raw.replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def estimated_usd_parts(
    usage: LlmUsage,
    prompt_rate: float | None = None,
    completion_rate: float | None = None,
) -> tuple[float, float] | None:
    if usage.cost is not None:
        return None
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
    prompt_usd = (usage.prompt_tokens / 1_000_000) * in_rate
    completion_usd = (usage.completion_tokens / 1_000_000) * out_rate
    return prompt_usd, completion_usd


def format_usd_sum_line(prompt_usd: float, completion_usd: float) -> str:
    digits = 5
    prompt = round(prompt_usd, digits)
    completion = round(completion_usd, digits)
    total = round(prompt + completion, digits)

    def _fmt(value: float) -> str:
        return f"{value:.{digits}f}".replace(".", ",")

    return f"{_fmt(prompt)}+{_fmt(completion)}={_fmt(total)}$"


def estimate_usd(
    usage: LlmUsage,
    prompt_rate: float | None = None,
    completion_rate: float | None = None,
) -> float | None:
    if usage.cost is not None:
        return usage.cost
    parts = estimated_usd_parts(usage, prompt_rate, completion_rate)
    if parts is None:
        return None
    return round(parts[0] + parts[1], 6)


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
        url = chat_completions_url(self.base_url, self.model)
        system_text = system if system else _DEFAULT_SYSTEM
        log_llm_event(
            "request",
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            url=url,
            llm_direct=os.environ.get("LLM_DIRECT", ""),
            proxy=proxy_public_labels(),
            system=system_text,
            user_prompt=prompt,
        )
        payload = chat_payload(self.model, system_text, prompt)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        failures: list[str] = []
        attempts = llm_transport_attempts()
        for index, (channel, kwargs) in enumerate(attempts):
            try:
                response = httpx.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=_TIMEOUT,
                    **kwargs,
                )
            except httpx.HTTPError as exc:
                detail = str(exc)
                if channel.startswith("proxy") and "502" in detail:
                    failures.append(
                        f"{channel}: ProxyError 502 CONNECT "
                        f"(прокси ответил, хост LLM не пустил)"
                    )
                else:
                    failures.append(f"{channel}: {exc.__class__.__name__}")
                log_llm_event(
                    "error",
                    model=self.model,
                    error=f"сеть: {exc.__class__.__name__}",
                    detail=str(exc),
                    channel=channel,
                )
                if index + 1 < len(attempts):
                    continue
                self._usage = LlmUsage()
                self._last_error = "сеть: " + "; ".join(failures)
                return ""
            if response.status_code >= 400:
                body = response.text.strip()
                if len(body) > 120:
                    body = body[:117] + "..."
                status_err = f"HTTP {response.status_code}: {body or 'пустой ответ'}"
                retryable = response.status_code in {502, 503, 504} and index + 1 < len(
                    attempts
                )
                log_llm_event(
                    "error",
                    model=self.model,
                    status_code=response.status_code,
                    error=status_err,
                    response_text=response.text,
                    channel=channel,
                )
                if retryable:
                    failures.append(f"{channel}: {status_err}")
                    continue
                self._usage = LlmUsage()
                if failures:
                    joined = "; ".join(failures)
                    self._last_error = f"сеть: {joined}; {status_err}"
                else:
                    self._last_error = status_err
                return ""
            try:
                data = unwrap_chat_response(response.json())
            except ValueError:
                self._usage = LlmUsage()
                self._last_error = "ответ API не JSON"
                log_llm_event(
                    "error",
                    model=self.model,
                    error=self._last_error,
                    response_text=response.text,
                    channel=channel,
                )
                return ""
            self._usage = usage_from_response(data)
            raw_content = choice_message_content(data)
            if raw_content is None:
                msg = data.get("msg")
                self._last_error = (
                    f"Kie: {msg}"
                    if isinstance(msg, str) and msg
                    else "в ответе API нет choices[0].message.content"
                )
                log_llm_event(
                    "error",
                    model=self.model,
                    error=self._last_error,
                    response_json=data,
                    channel=channel,
                )
                return ""
            content = message_content_to_str(raw_content)
            if content is None:
                self._last_error = "content ответа не строка"
                log_llm_event("error", model=self.model, error=self._last_error)
                return ""
            log_llm_event(
                "response",
                model=self.model,
                status_code=response.status_code,
                usage=self._usage.model_dump(),
                response_text=content,
                channel=channel,
            )
            return content
        self._usage = LlmUsage()
        self._last_error = "сеть: нет канала"
        return ""


def make_llm() -> LlmClient:
    key = (
        os.environ.get("LLM_API_KEY", "").strip()
        or os.environ.get("KIE_API_KEY", "").strip()
    )
    base = os.environ.get("LLM_BASE_URL", "").strip()
    model = os.environ.get("LLM_MODEL", "").strip()
    if not key or not base or not model:
        log_llm_event(
            "skipped",
            reason="missing LLM_API_KEY/KIE_API_KEY, LLM_BASE_URL or LLM_MODEL",
            has_key=bool(key),
            has_base=bool(base),
            has_model=bool(model),
        )
        return NullLlm()
    log_llm_event("client_ready", base_url=base, model=model, api_key=key)
    return OpenAiCompatLlm(key, base, model)
