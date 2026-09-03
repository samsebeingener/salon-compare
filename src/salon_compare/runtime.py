"""Поиск Docker / Streamlit для START.bat. Значения секретов не трогает."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def _program_files() -> Path:
    return Path(os.environ.get("ProgramFiles", r"C:\Program Files"))


def docker_bin_dirs() -> list[Path]:
    root = _program_files() / "Docker" / "Docker" / "resources" / "bin"
    return [root]


def prepend_docker_bin_to_path() -> None:
    parts = os.environ.get("PATH", "").split(os.pathsep)
    extra: list[str] = []
    for folder in docker_bin_dirs():
        text = str(folder)
        if folder.is_dir() and text not in parts:
            extra.append(text)
    if extra:
        os.environ["PATH"] = os.pathsep.join(extra + parts)


def find_docker_executable() -> str | None:
    prepend_docker_bin_to_path()
    for name in ("docker.exe", "docker"):
        found = shutil.which(name)
        if found:
            return found
    for folder in docker_bin_dirs():
        candidate = folder / "docker.exe"
        if candidate.is_file():
            return str(candidate)
        unix = folder / "docker"
        if unix.is_file():
            return str(unix)
    return None


def compose_up_cmd(docker: str) -> list[str]:
    return [docker, "compose", "up", "-d", "--build"]


def find_streamlit_cmd(root: Path) -> list[str] | None:
    app = str(root / "src" / "salon_compare" / "app.py")
    flags = ["--server.port=8501", "--server.address=127.0.0.1"]
    uv = shutil.which("uv.exe") or shutil.which("uv")
    if uv:
        return [uv, "run", "streamlit", "run", app, *flags]
    win = root / ".venv" / "Scripts" / "streamlit.exe"
    if win.is_file():
        return [str(win), "run", app, *flags]
    unix = root / ".venv" / "bin" / "streamlit"
    if unix.is_file():
        return [str(unix), "run", app, *flags]
    return None
