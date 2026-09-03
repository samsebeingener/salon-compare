from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_names_code_layout() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "как уложен" in lowered or "укладка" in lowered
    assert "app.py" in text
    assert "collect.py" in text
    assert "score.py" in text
    assert "llm.py" in text
    assert "store.py" in text


def test_readme_names_sqlite_entities() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "runs" in text
    assert "payload" in text
    assert "created_at" in text or "created at" in text
    assert "ключ" in text
    assert "не пиш" in text or "не попад" in text


def test_readme_states_out_of_scope() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "за рамками" in text
    assert "instagram" in text or "инстаграм" in text
    assert "капч" in text
    assert "фссп" in text


def test_readme_names_agent_and_models() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "агент" in lowered
    assert "cursor" in lowered
    assert "grok" in lowered
    assert "openspec" in lowered
    assert "мерж" in lowered or "merge" in lowered
    assert ".env" in text


def test_app_still_has_delivery_screen() -> None:
    text = (ROOT / "src" / "salon_compare" / "app.py").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "Зацепка 1" in text
    assert "Поля точек" in text
    assert "Сохранённые разборы" in text
    assert "покупай" not in lowered
