from pathlib import Path

from salon_compare.load_env import load_dotenv_file

ROOT = Path(__file__).resolve().parents[1]


def test_dotenv_fills_empty_environ(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text("TWOGIS_API_KEY=dummy-maps-key\n# comment\nEMPTY=\n", encoding="utf-8")
    environ: dict[str, str] = {}
    load_dotenv_file(path, environ)
    assert environ["TWOGIS_API_KEY"] == "dummy-maps-key"
    assert "EMPTY" not in environ


def test_dotenv_does_not_override_existing(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text("TWOGIS_API_KEY=from-file\n", encoding="utf-8")
    environ = {"TWOGIS_API_KEY": "from-process"}
    load_dotenv_file(path, environ)
    assert environ["TWOGIS_API_KEY"] == "from-process"


def test_missing_dotenv_is_ok(tmp_path: Path) -> None:
    environ: dict[str, str] = {}
    load_dotenv_file(tmp_path / "nope.env", environ)
    assert environ == {}


def test_app_loads_project_dotenv() -> None:
    text = (ROOT / "src" / "salon_compare" / "app.py").read_text(encoding="utf-8")
    assert "load_project_env" in text


def test_readme_says_streamlit_reads_env() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "streamlit" in text
    assert ".env" in text
    assert "читает" in text or "берёт" in text or "загруж" in text
