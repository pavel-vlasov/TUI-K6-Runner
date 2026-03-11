import builtins
import os
import sys

import pytest

from app_bootstrap import ensure_runtime_dependencies, get_resource_path


def test_ensure_runtime_dependencies_passes_when_all_present(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in {"textual", "pyperclip"}:
            return object()
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    ensure_runtime_dependencies()


def test_ensure_runtime_dependencies_raises_with_missing(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pyperclip":
            raise ImportError("missing")
        if name == "textual":
            return object()
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(RuntimeError) as exc:
        ensure_runtime_dependencies()

    assert "pyperclip" in str(exc.value)


def test_get_resource_path_prefers_meipass(monkeypatch):
    monkeypatch.setattr(sys, "_MEIPASS", "/tmp/bundle", raising=False)

    assert get_resource_path("style.tcss") == "/tmp/bundle/style.tcss"


def test_get_resource_path_uses_module_dir_when_no_meipass(monkeypatch):
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)

    path = get_resource_path("style.tcss")
    assert path.endswith(os.path.join("TUI-K6-Runner", "style.tcss"))
