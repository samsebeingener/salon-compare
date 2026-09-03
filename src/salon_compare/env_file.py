"""Чтение и безопасная запись `.env` без печати значений."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EnvLine:
    raw: str
    key: str | None
    value: str | None


def parse_env_text(text: str) -> list[EnvLine]:
    lines: list[EnvLine] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            lines.append(EnvLine(raw=raw, key=None, value=None))
            continue
        key, _, rest = stripped.partition("=")
        key = key.strip()
        if key.lower().startswith("export "):
            key = key[7:].strip()
        value = _unquote(rest.strip())
        lines.append(EnvLine(raw=raw, key=key or None, value=value if key else None))
    return lines


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        inner = value[1:-1]
        if value[0] == '"':
            return inner.replace('\\"', '"').replace("\\\\", "\\")
        return inner
    return value


def format_env_value(value: str) -> str:
    if not value:
        return ""
    special = any(ch in value for ch in " \t#\"'")
    if not special:
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def keys_from_example(example_text: str) -> list[str]:
    seen: list[str] = []
    for line in parse_env_text(example_text):
        if line.key and line.key not in seen:
            seen.append(line.key)
    return seen


def values_map(lines: list[EnvLine]) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in lines:
        if line.key:
            out[line.key] = line.value or ""
    return out


def empty_keys(lines: list[EnvLine], catalog: list[str]) -> list[str]:
    current = values_map(lines)
    missing: list[str] = []
    for key in catalog:
        if not current.get(key, "").strip():
            missing.append(key)
    return missing


def ensure_catalog_keys(lines: list[EnvLine], catalog: list[str]) -> list[EnvLine]:
    present = {line.key for line in lines if line.key}
    extra = list(lines)
    for key in catalog:
        if key not in present:
            extra.append(EnvLine(raw=f"{key}=", key=key, value=""))
            present.add(key)
    return extra


def set_key(lines: list[EnvLine], key: str, value: str) -> list[EnvLine]:
    updated: list[EnvLine] = []
    found = False
    encoded = f"{key}={format_env_value(value)}"
    for line in lines:
        if line.key == key and not found:
            updated.append(EnvLine(raw=encoded, key=key, value=value))
            found = True
        else:
            updated.append(line)
    if not found:
        updated.append(EnvLine(raw=encoded, key=key, value=value))
    return updated


def dump_env(lines: list[EnvLine]) -> str:
    body = "\n".join(line.raw for line in lines)
    if not body:
        return ""
    return body if body.endswith("\n") else f"{body}\n"


def fill_empty_keys(
    env_text: str,
    example_text: str,
    reader: Callable[[str], str],
) -> tuple[str, list[str]]:
    catalog = keys_from_example(example_text)
    lines = ensure_catalog_keys(parse_env_text(env_text), catalog)
    filled: list[str] = []
    for key in empty_keys(lines, catalog):
        value = reader(key).strip()
        if not value:
            continue
        lines = set_key(lines, key, value)
        filled.append(key)
    return dump_env(lines), filled


def write_env_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(path)


def ensure_env_from_example(env_path: Path, example_path: Path) -> bool:
    """Создаёт `.env` из образца. True — файл только что создан."""
    if env_path.is_file():
        return False
    env_path.write_text(example_path.read_text(encoding="utf-8-sig"), encoding="utf-8")
    return True
