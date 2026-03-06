import asyncio

from k6.process_manager import K6ProcessManager


def test_start_run_includes_web_dashboard_output_when_enabled(monkeypatch):
    captured = {}

    async def fake_create_subprocess_exec(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

        class DummyProcess:
            returncode = None
            pid = 1

        return DummyProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    manager = K6ProcessManager()
    asyncio.run(manager.start_run(enable_web_dashboard=True))

    assert "--out" in captured["args"]
    assert "web-dashboard=period=1s&open=false" in captured["args"]


def test_start_run_does_not_include_web_dashboard_output_when_disabled(monkeypatch):
    captured = {}

    async def fake_create_subprocess_exec(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

        class DummyProcess:
            returncode = None
            pid = 1

        return DummyProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    manager = K6ProcessManager()
    asyncio.run(manager.start_run(enable_web_dashboard=False))

    assert "--out" not in captured["args"]
    assert "web-dashboard" not in captured["args"]


def test_start_run_includes_summary_export_when_html_summary_enabled(monkeypatch):
    captured = {}

    async def fake_create_subprocess_exec(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

        class DummyProcess:
            returncode = None
            pid = 1

        return DummyProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    manager = K6ProcessManager()
    asyncio.run(
        manager.start_run(
            enable_html_summary=True,
            summary_json_path="artifacts/summary.json",
        )
    )

    assert "--summary-export" in captured["args"]
    assert "artifacts/summary.json" in captured["args"]


def test_start_run_creates_summary_directory_when_needed(monkeypatch, tmp_path):
    async def fake_create_subprocess_exec(*_args, **_kwargs):
        class DummyProcess:
            returncode = None
            pid = 1

        return DummyProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    summary_file = tmp_path / "nested" / "artifacts" / "summary.json"
    manager = K6ProcessManager()
    asyncio.run(
        manager.start_run(
            enable_html_summary=True,
            summary_json_path=str(summary_file),
        )
    )

    assert summary_file.parent.exists()
