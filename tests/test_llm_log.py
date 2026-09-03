from __future__ import annotations

import json

from salon_compare.llm_log import _mask_key, log_llm_event, log_path


def test_mask_key_hides_middle() -> None:
    assert _mask_key("sk-or-v1-abcdefghijklmnop") == "sk-o…mnop"


def test_log_writes_json_line(tmp_path, monkeypatch) -> None:
    target = tmp_path / "llm.log"
    monkeypatch.setattr("salon_compare.llm_log._LOG_PATH", target)
    monkeypatch.setenv("LLM_LOG", "1")
    log_llm_event("request", api_key="secret-key-12345678", model="test")
    lines = target.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["event"] == "request"
    assert payload["api_key_masked"] == "secr…5678"
    assert "secret" not in lines[0]


def test_log_disabled_by_env(tmp_path, monkeypatch) -> None:
    target = tmp_path / "llm.log"
    monkeypatch.setattr("salon_compare.llm_log._LOG_PATH", target)
    monkeypatch.setenv("LLM_LOG", "0")
    log_llm_event("skipped", reason="test")
    assert not target.exists()


def test_log_path_under_data() -> None:
    assert log_path().name == "llm-interactions.log"
    assert log_path().parent.name == "data"
