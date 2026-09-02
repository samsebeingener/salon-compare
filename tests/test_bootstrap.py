from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_env_example_lists_required_keys() -> None:
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "TWOGIS_API_KEY" in text
    assert "YANDEX_MAPS_API_KEY" not in text
    assert "LLM_API_KEY" in text
    assert "LLM_BASE_URL" in text
    assert "LLM_MODEL" in text
    assert "HTTP_PROXY" in text
    assert "HTTPS_PROXY" in text
    assert "USER:PASSWORD@HOST:PORT" in text
    assert "127.0.0.1:8080" not in text


def test_readme_documents_rf_llm_proxy() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "HTTP_PROXY" in text
    assert "HTTPS_PROXY" in text
    assert "РФ" in text or "Росси" in text
    assert "USER:PASSWORD@HOST:PORT" in text
    assert "127.0.0.1:8080" not in text


def test_httpx_client_trusts_env_proxy() -> None:
    from salon_compare.proxy import httpx_client_kwargs

    kwargs = httpx_client_kwargs()
    assert kwargs["trust_env"] is True


def test_quality_script_exists() -> None:
    assert (ROOT / "scripts" / "run_quality.py").is_file()


def test_ci_invokes_quality_script() -> None:
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "scripts/run_quality.py" in text


def test_compose_file_exists() -> None:
    assert (ROOT / "compose.yaml").is_file()


def test_compose_forwards_proxy_env() -> None:
    text = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    assert "HTTP_PROXY" in text
    assert "HTTPS_PROXY" in text


def test_streamlit_app_module_exists() -> None:
    assert (ROOT / "src" / "salon_compare" / "app.py").is_file()
