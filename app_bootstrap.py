import os
import shutil
import sys
from pathlib import Path


def ensure_runtime_dependencies() -> None:
    missing = []
    for dependency in ("textual", "pyperclip"):
        try:
            __import__(dependency)
        except ImportError:
            missing.append(dependency)

    if missing:
        deps = ", ".join(missing)
        raise RuntimeError(
            f"Missing runtime dependencies: {deps}. Install project dependencies via requirements.txt/pyproject before start."
        )

    if shutil.which("k6") is None:
        raise RuntimeError(
            "k6 binary was not found in PATH. Install k6 and ensure the `k6` command is available in your shell. "
            "Install guide: https://grafana.com/docs/k6/latest/set-up/install-k6/"
        )


def get_resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    resource_path = os.path.join(base_path, relative_path)
    return Path(resource_path).as_posix()
