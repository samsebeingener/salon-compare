"""Одна команда качества: ruff, mypy, pytest. Та же — в CI."""

from __future__ import annotations

import subprocess


def main() -> int:
    steps = (
        ["ruff", "check", "."],
        ["ruff", "format", "--check", "."],
        ["mypy", "src", "tests"],
        ["pytest", "-q"],
    )
    for cmd in steps:
        print("+", *cmd)
        result = subprocess.run(cmd, check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
