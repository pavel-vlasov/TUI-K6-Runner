import os
import shutil
import sys
from importlib.resources import files
from pathlib import Path

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
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    resource_path = Path(base_path, relative_path)
    if resource_path.exists() or hasattr(sys, "_MEIPASS"):
        return resource_path.as_posix()

    try:
        packaged_resource = files("tui_k6_runner.resources").joinpath(*relative_path.split("/"))
    except ModuleNotFoundError:
        return resource_path.as_posix()

    return Path(str(packaged_resource)).as_posix()


def ensure_k6_script(filename: str = "test.js") -> str:
    script_path = Path.cwd() / filename
    if script_path.exists():
        return filename

    packaged_script = files("tui_k6_runner.resources").joinpath(filename)
    script_path.write_bytes(packaged_script.read_bytes())
    return filename

