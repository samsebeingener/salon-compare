"""Проверка `.env` и запуск Docker Compose + браузер. Значения ключей не печатает."""

from __future__ import annotations

import argparse
import getpass
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from salon_compare.env_file import (  # noqa: E402
    empty_keys,
    ensure_env_from_example,
    fill_empty_keys,
    keys_from_example,
    parse_env_text,
    values_map,
    write_env_atomic,
)
from salon_compare.runtime import (  # noqa: E402
    compose_up_cmd,
    find_docker_executable,
    find_streamlit_cmd,
)

HEALTH_URL = "http://127.0.0.1:8501/_stcore/health"
APP_URL = "http://127.0.0.1:8501"

HINTS: dict[str, str] = {
    "TWOGIS_API_KEY": "Ключ API 2ГИС (Enter — пропустить, карты будут пустые)",
    "LLM_API_KEY": "Ключ модели Kie или OpenRouter (Enter — пропустить)",
    "LLM_BASE_URL": "Базовый URL API модели, например https://api.kie.ai/",
    "LLM_MODEL": "Имя модели, например gemini-3-flash",
    "LLM_USD_PER_1M_PROMPT": "USD за 1M токенов ввода (Enter — пропустить)",
    "LLM_USD_PER_1M_COMPLETION": "USD за 1M токенов выхода (Enter — пропустить)",
    "HTTP_PROXY": "Прокси по HTTP: http://логин:пароль@хост:порт",
    "HTTPS_PROXY": "Прокси по TLS: https://логин:пароль@хост:порт",
    "LLM_DIRECT": "1 — сначала прямой запрос к LLM, без прокси (Enter — пропустить)",
}

SECRET_KEYS = {
    "TWOGIS_API_KEY",
    "LLM_API_KEY",
    "KIE_API_KEY",
    "HTTP_PROXY",
    "HTTPS_PROXY",
}


def _is_secret(key: str) -> bool:
    return key in SECRET_KEYS or key.endswith("_KEY") or "PROXY" in key


def default_reader(key: str, secret: bool) -> str:
    hint = HINTS.get(key, key)
    print(hint)
    if secret:
        return getpass.getpass(f"{key} (ввод скрыт, Enter — пропуск): ")
    return input(f"{key}: ")


def _interactive_reader(key: str) -> str:
    return default_reader(key, secret=_is_secret(key))


def wait_health(url: str, attempts: int = 30, delay: float = 2.0) -> bool:
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if 200 <= response.status < 300:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(delay)
    return False


def run_compose(root: Path) -> int:
    docker = find_docker_executable()
    if docker is None:
        print("Команда docker не найдена в PATH и в папке Docker Desktop.")
        return 127
    try:
        result = subprocess.run(compose_up_cmd(docker), cwd=root, check=False)
    except OSError:
        print("Не удалось запустить docker.exe. Открой Docker Desktop и повтори.")
        return 127
    return result.returncode


def run_local_streamlit(root: Path) -> int:
    cmd = find_streamlit_cmd(root)
    if cmd is None:
        print("Нет Docker и нет uv/.venv — поставь Docker Desktop или uv.")
        return 127
    print("Docker нет — запускаю локальный Streamlit на 8501.")
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NEW_CONSOLE
    try:
        subprocess.Popen(cmd, cwd=root, creationflags=flags)
    except OSError:
        print("Не удалось запустить Streamlit.")
        return 127
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Проверить .env и запустить Docker.")
    parser.add_argument(
        "--skip-docker",
        action="store_true",
        help="Только .env, без compose (для проверки).",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Не открывать браузер.",
    )
    args = parser.parse_args(argv)

    example_path = ROOT / ".env.example"
    env_path = ROOT / ".env"
    if not example_path.is_file():
        print("Нет .env.example — не из чего собрать ключи.")
        return 1

    created = ensure_env_from_example(env_path, example_path)
    if created:
        print("Создан .env по образцу .env.example")

    example_text = example_path.read_text(encoding="utf-8-sig")
    env_text = env_path.read_text(encoding="utf-8-sig")
    new_text, filled = fill_empty_keys(env_text, example_text, _interactive_reader)
    old_keys = set(values_map(parse_env_text(env_text)))
    new_keys = set(values_map(parse_env_text(new_text)))
    if filled or new_keys != old_keys:
        write_env_atomic(env_path, new_text)
        if filled:
            print("Записаны ключи:", ", ".join(filled))
    else:
        leftover = empty_keys(
            parse_env_text(env_text),
            keys_from_example(example_text),
        )
        if leftover:
            print("Пустые ключи оставлены без значения:", ", ".join(leftover))
        else:
            print(".env на месте, обязательные поля с значениями заполнены.")

    if args.skip_docker:
        return 0

    print("Запуск Docker Compose…")
    code = run_compose(ROOT)
    if code != 0:
        print("Пробую без Docker…")
        local = run_local_streamlit(ROOT)
        if local != 0:
            print("Нужен Docker Desktop (в PATH) или uv в проекте.")
            return local

    print("Жду http://127.0.0.1:8501 …")
    if not wait_health(HEALTH_URL):
        print("Приложение не ответило.")
        print("Docker: docker compose logs. Локально — окно Streamlit.")
        return 1
    print(f"Готово: {APP_URL}")
    if not args.no_browser:
        webbrowser.open(APP_URL)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
