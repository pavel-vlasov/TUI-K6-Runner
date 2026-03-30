import shutil
from pathlib import Path

from resources import get_resource_locator

RUNTIME_DEPENDENCIES = ("textual", "pyperclip", "jsonschema", "pygments")


def ensure_runtime_dependencies() -> None:
    missing = []
    for dependency in RUNTIME_DEPENDENCIES:
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
    resource_path = get_resource_locator().resource_path(relative_path)
    return Path(resource_path).as_posix()
