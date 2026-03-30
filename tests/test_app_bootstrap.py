import builtins
import os
import sys
from pathlib import Path

import pytest

from app_bootstrap import ensure_runtime_dependencies, get_resource_path


def test_ensure_runtime_dependencies_passes_when_all_present(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in {"textual", "pyperclip", "jsonschema", "pygments"}:
            return object()
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr("app_bootstrap.shutil.which", lambda _: "/usr/local/bin/k6")

    ensure_runtime_dependencies()


def test_ensure_runtime_dependencies_raises_with_missing(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in {"jsonschema", "pygments"}:
            raise ImportError("missing")
        if name in {"textual", "pyperclip"}:
            return object()
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr("app_bootstrap.shutil.which", lambda _: "/usr/local/bin/k6")

    with pytest.raises(RuntimeError) as exc:
        ensure_runtime_dependencies()

    assert "jsonschema" in str(exc.value)
    assert "pygments" in str(exc.value)


def test_ensure_runtime_dependencies_raises_when_k6_missing(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in {"textual", "pyperclip", "jsonschema", "pygments"}:
            return object()
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr("app_bootstrap.shutil.which", lambda _: None)

    with pytest.raises(RuntimeError) as exc:
        ensure_runtime_dependencies()

    assert "k6 binary was not found in PATH" in str(exc.value)


def test_get_resource_path_prefers_meipass(monkeypatch):
    monkeypatch.setattr(sys, "_MEIPASS", "/tmp/bundle", raising=False)

    assert get_resource_path("style.tcss") == "/tmp/bundle/style.tcss"


def test_get_resource_path_uses_module_dir_when_no_meipass(monkeypatch):
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)

    path = get_resource_path("style.tcss")
    assert path.endswith("TUI-K6-Runner/style.tcss")


def test_get_resource_path_posix_path_still_allows_file_read(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    expected_content = "Screen { background: black; }"
    resource_file = tmp_path / "style.tcss"
    resource_file.write_text(expected_content, encoding="utf-8")

    path = get_resource_path("style.tcss")

    assert "\\" not in path
    assert Path(path).read_text(encoding="utf-8") == expected_content
