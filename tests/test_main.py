import main


def test_main_runs_bootstrap_then_app(monkeypatch):
    calls = []

    class DummyApp:
        def run(self):
            calls.append("run")

    monkeypatch.setattr(main, "ensure_runtime_dependencies", lambda: calls.append("deps"))
    monkeypatch.setattr(main, "K6TestApp", DummyApp)

    main.main()

    assert calls == ["deps", "run"]
