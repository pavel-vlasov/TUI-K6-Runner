import asyncio

from k6.process_manager import K6ProcessManager


def test_start_run_enables_web_dashboard_env_when_enabled(monkeypatch):
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

    env = captured["kwargs"].get("env")
    assert env is not None
    assert env["K6_WEB_DASHBOARD"] == "true"


def test_start_run_sets_web_dashboard_export_env_when_enabled(monkeypatch):
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

    env = captured["kwargs"].get("env")
    assert env is not None
    assert env.get("K6_WEB_DASHBOARD_EXPORT")


def test_start_run_does_not_enable_web_dashboard_env_when_disabled(monkeypatch):
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

    env = captured["kwargs"].get("env")
    assert env is not None
    assert "K6_WEB_DASHBOARD" not in env


def test_start_run_overwrites_dashboard_export_env_when_enabled(monkeypatch):
    captured = {}

    async def fake_create_subprocess_exec(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

        class DummyProcess:
            returncode = None
            pid = 1

        return DummyProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    monkeypatch.setenv("K6_WEB_DASHBOARD_EXPORT", "old/path/dashboard.html")

    manager = K6ProcessManager()
    asyncio.run(manager.start_run(enable_web_dashboard=True))

    env = captured["kwargs"].get("env")
    assert env is not None
    assert env["K6_WEB_DASHBOARD_EXPORT"] == "artifacts/dashboard.html"




def test_start_run_sets_dashboard_port_and_bind_host_from_local_url(monkeypatch):
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
    asyncio.run(manager.start_run(enable_web_dashboard=True, web_dashboard_url="http://127.0.0.1:7777"))

    env = captured["kwargs"].get("env")
    assert env is not None
    assert env["K6_WEB_DASHBOARD_HOST"] == "0.0.0.0"
    assert env["K6_WEB_DASHBOARD_PORT"] == "7777"





def test_start_run_replaces_stale_dashboard_host_env_for_local_url(monkeypatch):
    captured = {}

    async def fake_create_subprocess_exec(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

        class DummyProcess:
            returncode = None
            pid = 1

        return DummyProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    monkeypatch.setenv("K6_WEB_DASHBOARD_HOST", "0.0.0.0")
    monkeypatch.setenv("K6_WEB_DASHBOARD_PORT", "9999")

    manager = K6ProcessManager()
    asyncio.run(manager.start_run(enable_web_dashboard=True, web_dashboard_url="http://localhost:5665"))

    env = captured["kwargs"].get("env")
    assert env is not None
    assert env["K6_WEB_DASHBOARD_HOST"] == "0.0.0.0"
    assert env["K6_WEB_DASHBOARD_PORT"] == "5665"

def test_start_run_sets_dashboard_host_for_non_local_url(monkeypatch):
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
    asyncio.run(manager.start_run(enable_web_dashboard=True, web_dashboard_url="http://0.0.0.0:7777"))

    env = captured["kwargs"].get("env")
    assert env is not None
    assert env["K6_WEB_DASHBOARD_HOST"] == "0.0.0.0"
    assert env["K6_WEB_DASHBOARD_PORT"] == "7777"

def test_start_run_sets_dashboard_port_and_bind_host_from_local_url_without_scheme(monkeypatch):
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
    asyncio.run(manager.start_run(enable_web_dashboard=True, web_dashboard_url="localhost:7777"))

    env = captured["kwargs"].get("env")
    assert env is not None
    assert env["K6_WEB_DASHBOARD_HOST"] == "0.0.0.0"
    assert env["K6_WEB_DASHBOARD_PORT"] == "7777"


def test_start_run_sets_dashboard_host_for_non_local_url_without_scheme(monkeypatch):
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
    asyncio.run(manager.start_run(enable_web_dashboard=True, web_dashboard_url="0.0.0.0:8888"))

    env = captured["kwargs"].get("env")
    assert env is not None
    assert env["K6_WEB_DASHBOARD_HOST"] == "0.0.0.0"
    assert env["K6_WEB_DASHBOARD_PORT"] == "8888"

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
