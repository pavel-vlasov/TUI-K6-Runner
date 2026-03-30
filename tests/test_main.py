import main
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
