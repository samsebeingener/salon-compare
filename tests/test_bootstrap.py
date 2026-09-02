from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_env_example_lists_required_keys() -> None:
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "TWOGIS_API_KEY" in text
    assert "YANDEX_MAPS_API_KEY" in text
    assert "LLM_API_KEY" in text
    assert "LLM_BASE_URL" in text
    assert "LLM_MODEL" in text


def test_quality_script_exists() -> None:
    assert (ROOT / "scripts" / "run_quality.py").is_file()


def test_ci_invokes_quality_script() -> None:
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "scripts/run_quality.py" in text


def test_compose_file_exists() -> None:
    assert (ROOT / "compose.yaml").is_file()


def test_streamlit_hello_module_exists() -> None:
    assert (ROOT / "src" / "salon_compare" / "app.py").is_file()


def test_hello_app_has_no_salon_intake() -> None:
    text = (ROOT / "src" / "salon_compare" / "app.py").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "зацепк" not in lowered
    assert "огрн" not in lowered
