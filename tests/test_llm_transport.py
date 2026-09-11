from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from salon_compare.llm import OpenAiCompatLlm
from salon_compare.proxy import llm_httpx_client_kwargs, llm_transport_attempts


def test_proxy_then_direct_when_proxy_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_DIRECT", raising=False)
    monkeypatch.delenv("HTTP_PROXY", raising=False)
    monkeypatch.setenv("HTTPS_PROXY", "http://user:secret@proxy.example:8080")
    names = [name for name, _kwargs in llm_transport_attempts()]
    assert names == ["proxy-http", "direct"]
    first = llm_httpx_client_kwargs()
    assert first.get("trust_env") is False
    assert first.get("proxy") == "http://user:secret@proxy.example:8080"


def test_https_proxy_scheme_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_DIRECT", raising=False)
    monkeypatch.delenv("HTTP_PROXY", raising=False)
    monkeypatch.setenv("HTTPS_PROXY", "https://proxy.example:9401")
    first = llm_httpx_client_kwargs()
    assert first.get("proxy") == "https://proxy.example:9401"


def test_http_and_https_proxy_are_two_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LLM_DIRECT", raising=False)
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.example:8080")
    monkeypatch.setenv("HTTPS_PROXY", "https://proxy.example:8080")
    attempts = llm_transport_attempts()
    names = [name for name, _kwargs in attempts]
    assert names == ["proxy-http", "proxy-https", "direct"]
    assert attempts[0][1].get("proxy") == "http://proxy.example:8080"
    assert attempts[1][1].get("proxy") == "https://proxy.example:8080"


def test_identical_proxy_urls_are_one_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LLM_DIRECT", raising=False)
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.example:8080")
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example:8080")
    names = [name for name, _kwargs in llm_transport_attempts()]
    assert names == ["proxy-http", "direct"]


def test_direct_then_proxy_when_llm_direct(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_DIRECT", "1")
    monkeypatch.delenv("HTTP_PROXY", raising=False)
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example:8080")
    names = [name for name, _kwargs in llm_transport_attempts()]
    assert names == ["direct", "proxy-http"]


def test_complete_retries_direct_after_proxy_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LLM_DIRECT", raising=False)
    monkeypatch.delenv("HTTP_PROXY", raising=False)
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example:8080")
    calls = {"n": 0}

    def fake_post(*_args: object, **kwargs: object) -> object:
        calls["n"] += 1
        if kwargs.get("proxy"):
            raise httpx.ProxyError("502 Bad Gateway")
        return SimpleNamespace(
            status_code=200,
            text="{}",
            json=lambda: {
                "choices": [{"message": {"content": '{"ok":true}'}}],
                "usage": {},
            },
        )

    monkeypatch.setattr("salon_compare.llm.httpx.post", fake_post)
    client = OpenAiCompatLlm("k", "https://api.example/v1", "m")
    assert client.complete("hi") == '{"ok":true}'
    assert calls["n"] == 2


def test_kie_url_uses_model_path() -> None:
    from salon_compare.llm import chat_completions_url

    assert (
        chat_completions_url("https://api.kie.ai/", "gemini-3-flash")
        == "https://api.kie.ai/gemini-3-flash/v1/chat/completions"
    )
    assert (
        chat_completions_url("https://api.kie.ai", "gemini-3-flash-openai")
        == "https://api.kie.ai/gemini-3-flash/v1/chat/completions"
    )


def test_openai_url_keeps_v1_chat_completions() -> None:
    from salon_compare.llm import chat_completions_url

    assert (
        chat_completions_url("https://api.openrouter.ai/v1", "qwen/qwen3.8-27b")
        == "https://api.openrouter.ai/v1/chat/completions"
    )


def test_chat_payload_disables_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    from salon_compare.llm import chat_payload

    monkeypatch.delenv("LLM_MAX_TOKENS", raising=False)

    body = chat_payload(
        "gemini-3-flash",
        "sys",
        "user",
        base_url="https://api.kie.ai",
    )
    assert body["stream"] is False
    assert body["include_thoughts"] is False
    assert body["reasoning_effort"] == "low"
    assert body["max_tokens"] == 1500
    assert "reasoning" not in body
    messages = body["messages"]
    assert isinstance(messages, list)
    system_message = messages[0]
    assert isinstance(system_message, dict)
    content = system_message["content"]
    assert isinstance(content, list)
    part = content[0]
    assert isinstance(part, dict)
    assert part["text"] == "sys"


def test_chat_payload_omits_kie_fields_for_openrouter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from salon_compare.llm import chat_payload

    monkeypatch.delenv("LLM_MAX_TOKENS", raising=False)

    body = chat_payload(
        "qwen/qwen3.8-27b",
        "sys",
        "user",
        base_url="https://api.openrouter.ai/v1",
    )
    assert body["stream"] is False
    assert "include_thoughts" not in body
    assert "reasoning_effort" not in body
    assert body["max_tokens"] == 1500
    reasoning = body["reasoning"]
    assert isinstance(reasoning, dict)
    assert reasoning["effort"] == "none"
    assert reasoning["exclude"] is True


def test_chat_payload_reads_max_tokens_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from salon_compare.llm import chat_payload

    monkeypatch.setenv("LLM_MAX_TOKENS", "+800")
    body = chat_payload("m", "s", "u", base_url="https://openrouter.ai/api/v1")
    assert body["max_tokens"] == 800


def test_message_content_joins_text_parts() -> None:
    from salon_compare.llm import message_content_to_str

    assert message_content_to_str([{"type": "text", "text": '{"a":1}'}]) == '{"a":1}'


def test_unwrap_kie_envelope() -> None:
    from salon_compare.llm import unwrap_chat_response

    inner = {"choices": [{"message": {"content": "ok"}}]}
    assert unwrap_chat_response({"code": 200, "data": inner}) == inner
