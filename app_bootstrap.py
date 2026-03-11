import os
import sys


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


def get_resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)
