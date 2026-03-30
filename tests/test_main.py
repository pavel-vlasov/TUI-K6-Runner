import main
import runpy
import sys
import types


def test_main_runs_bootstrap_then_app(monkeypatch):
    calls = []

    class DummyApp:
        def run(self):
            calls.append("run")

    monkeypatch.setattr(main, "ensure_runtime_dependencies", lambda: calls.append("deps"))

    main.main(DummyApp)

    assert calls == ["deps", "run"]


def test_main_default_path_uses_k6_test_app(monkeypatch):
    calls = []

    class DummyApp:
        def run(self):
            calls.append("run")

    monkeypatch.setattr(main, "ensure_runtime_dependencies", lambda: calls.append("deps"))
    fake_app_module = types.ModuleType("app")
    fake_app_module.K6TestApp = DummyApp
    monkeypatch.setitem(sys.modules, "app", fake_app_module)

    main.main()

    assert calls == ["deps", "run"]


def test_running_main_as_script_calls_main_and_runs_app(monkeypatch):
    calls = []

    fake_bootstrap_module = types.ModuleType("app_bootstrap")
    fake_bootstrap_module.ensure_runtime_dependencies = lambda: calls.append("deps")
    monkeypatch.setitem(sys.modules, "app_bootstrap", fake_bootstrap_module)

    class DummyApp:
        def run(self):
            calls.append("run")

    fake_app_module = types.ModuleType("app")
    fake_app_module.K6TestApp = DummyApp
    monkeypatch.setitem(sys.modules, "app", fake_app_module)

    runpy.run_module("main", run_name="__main__")

    assert calls == ["deps", "run"]
