from pathlib import Path

from salon_compare.env_file import (
    dump_env,
    empty_keys,
    ensure_catalog_keys,
    ensure_env_from_example,
    fill_empty_keys,
    format_env_value,
    keys_from_example,
    parse_env_text,
    set_key,
    values_map,
    write_env_atomic,
)


def test_example_catalog_has_llm_and_maps() -> None:
    root = Path(__file__).resolve().parents[1]
    catalog = keys_from_example((root / ".env.example").read_text(encoding="utf-8"))
    assert catalog[0] == "TWOGIS_API_KEY"
    assert "LLM_API_KEY" in catalog
    assert "LLM_BASE_URL" in catalog
    assert "HTTPS_PROXY" in catalog


def test_empty_keys_skip_filled() -> None:
    lines = parse_env_text("A=1\nB=\n")
    assert empty_keys(lines, ["A", "B"]) == ["B"]


def test_set_key_preserves_comments() -> None:
    lines = parse_env_text("# keep\nA=\n")
    text = dump_env(set_key(lines, "A", "secret#1"))
    assert "# keep" in text
    assert 'A="secret#1"' in text
    assert "secret#1" == values_map(parse_env_text(text))["A"]


def test_format_quotes_spaces() -> None:
    assert format_env_value("http://u:p@h:1") == "http://u:p@h:1"
    assert format_env_value("a b") == '"a b"'


def test_ensure_catalog_appends_missing() -> None:
    lines = ensure_catalog_keys(parse_env_text("A=1\n"), ["A", "B"])
    assert empty_keys(lines, ["A", "B"]) == ["B"]


def test_write_env_atomic(tmp_path: Path) -> None:
    target = tmp_path / ".env"
    write_env_atomic(target, "K=v\n")
    assert target.read_text(encoding="utf-8") == "K=v\n"
    assert not (tmp_path / ".env.tmp").exists()


def test_ensure_env_from_example_creates_once(tmp_path: Path) -> None:
    example = tmp_path / ".env.example"
    example.write_text("A=\n", encoding="utf-8")
    env_path = tmp_path / ".env"
    assert ensure_env_from_example(env_path, example) is True
    assert ensure_env_from_example(env_path, example) is False


def test_fill_empty_keys_writes_only_answered() -> None:
    example = "A=\nB=\nC=keep\n"
    env = "A=\nB=\nC=keep\n"
    answers = {"A": "one", "B": ""}

    def reader(key: str) -> str:
        return answers[key]

    text, filled = fill_empty_keys(env, example, reader)
    values = values_map(parse_env_text(text))
    assert filled == ["A"]
    assert values["A"] == "one"
    assert values["B"] == ""
    assert values["C"] == "keep"


def test_start_bat_calls_python_script() -> None:
    root = Path(__file__).resolve().parents[1]
    bat = (root / "START.bat").read_text(encoding="utf-8")
    assert "scripts\\start_local.py" in bat
    assert (root / "scripts" / "start_local.py").is_file()
