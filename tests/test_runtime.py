from pathlib import Path

import pytest

from salon_compare.runtime import (
    compose_up_cmd,
    find_docker_executable,
    find_streamlit_cmd,
)


def test_compose_up_cmd_uses_resolved_binary() -> None:
    assert compose_up_cmd(r"C:\Docker\docker.exe") == [
        r"C:\Docker\docker.exe",
        "compose",
        "up",
        "-d",
        "--build",
    ]


def test_find_docker_in_program_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bin_dir = tmp_path / "Docker" / "Docker" / "resources" / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "docker.exe").write_bytes(b"")
    monkeypatch.setenv("ProgramFiles", str(tmp_path))
    monkeypatch.setenv("PATH", str(tmp_path / "nowhere"))
    monkeypatch.setattr("salon_compare.runtime.shutil.which", lambda _name: None)
    found = find_docker_executable()
    assert found is not None
    assert Path(found).name == "docker.exe"


def test_find_streamlit_prefers_uv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "salon_compare.runtime.shutil.which",
        lambda name: r"C:\uv.exe" if name in {"uv", "uv.exe"} else None,
    )
    cmd = find_streamlit_cmd(tmp_path)
    assert cmd is not None
    assert cmd[0] == r"C:\uv.exe"
    assert "streamlit" in cmd
