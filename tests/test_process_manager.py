import asyncio
import logging

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
    assert "web-dashboard=period=5s&open=false" in captured["args"]


def test_start_run_sets_web_dashboard_open_env_when_enabled(monkeypatch):
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
    assert env.get("K6_WEB_DASHBOARD_OPEN") == "false"


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


def test_start_run_adds_no_connection_reuse_flag(monkeypatch):
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
    asyncio.run(manager.start_run(connection_management="no connection reuse"))

    assert "--no-connection-reuse" in captured["args"]
    assert "--no-vu-connection-reuse" not in captured["args"]


def test_start_run_adds_no_vu_connection_reuse_flag(monkeypatch):
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
    asyncio.run(manager.start_run(connection_management="no vu connection reuse"))

    assert "--no-vu-connection-reuse" in captured["args"]
    assert "--no-connection-reuse" not in captured["args"]


def test_start_run_sets_dashboard_host_and_port_from_local_url(monkeypatch):
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
    assert env["K6_WEB_DASHBOARD_HOST"] == "127.0.0.1"
    assert env["K6_WEB_DASHBOARD_PORT"] == "7777"


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


def test_start_run_keeps_default_port_when_dashboard_url_has_no_port(monkeypatch, caplog):
    captured = {}

    async def fake_create_subprocess_exec(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

        class DummyProcess:
            returncode = None
            pid = 1

        return DummyProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    caplog.set_level(logging.INFO)

    manager = K6ProcessManager()
    asyncio.run(manager.start_run(enable_web_dashboard=True, web_dashboard_url="http://localhost"))

    env = captured["kwargs"].get("env")
    assert env is not None
    assert env["K6_WEB_DASHBOARD_HOST"] == "localhost"
    assert "K6_WEB_DASHBOARD_PORT" not in env
    assert "does not include a port" in caplog.text


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


def test_stop_returns_true_after_graceful_stop():
    class DummyProcess:
        def __init__(self):
            self.returncode = None
            self.pid = 123
            self.sent_signal = None
            self.terminate_called = False
            self.kill_called = False

        def send_signal(self, sig):
            self.sent_signal = sig
            self.returncode = 0

        async def wait(self):
            return self.returncode

        def terminate(self):
            self.terminate_called = True

        def kill(self):
            self.kill_called = True

    manager = K6ProcessManager()
    manager.process = DummyProcess()

    result = asyncio.run(manager.stop(timeout=0.1))

    assert result is True
    assert manager.process.sent_signal is not None
    assert manager.process.terminate_called is False
    assert manager.process.kill_called is False


def test_stop_uses_ctrl_break_event_on_windows(monkeypatch):
    ctrl_break_event = 12345

    class DummyProcess:
        def __init__(self):
            self.returncode = None
            self.pid = 123
            self.sent_signal = None
            self.terminate_called = False
            self.kill_called = False

        def send_signal(self, sig):
            self.sent_signal = sig
            self.returncode = 0

        async def wait(self):
            return self.returncode

        def terminate(self):
            self.terminate_called = True

        def kill(self):
            self.kill_called = True

    monkeypatch.setattr("k6.process_manager.platform.system", lambda: "Windows")
    monkeypatch.setattr("k6.process_manager.signal.CTRL_BREAK_EVENT", ctrl_break_event, raising=False)
    manager = K6ProcessManager()
    manager.process = DummyProcess()

    result = asyncio.run(manager.stop(timeout=0.1))

    assert result is True
    assert manager.process.sent_signal == ctrl_break_event
    assert manager.process.terminate_called is False
    assert manager.process.kill_called is False


def test_stop_escalates_to_terminate_on_timeout():
    class DummyProcess:
        def __init__(self):
            self.returncode = None
            self.pid = 123
            self.sent_signal = None
            self.terminate_called = False
            self.kill_called = False
            self.wait_attempts = 0

        def send_signal(self, sig):
            self.sent_signal = sig

        async def wait(self):
            self.wait_attempts += 1
            if self.wait_attempts == 1:
                await asyncio.sleep(0.05)
            self.returncode = 0
            return self.returncode

        def terminate(self):
            self.terminate_called = True
            self.returncode = 0

        def kill(self):
            self.kill_called = True

    manager = K6ProcessManager()
    manager.process = DummyProcess()

    result = asyncio.run(manager.stop(timeout=0.01))

    assert result is True
    assert manager.process.terminate_called is True
    assert manager.process.kill_called is False


def test_stop_escalates_to_kill_after_terminate_timeout():
    class DummyProcess:
        def __init__(self):
            self.returncode = None
            self.pid = 123
            self.sent_signal = None
            self.terminate_called = False
            self.kill_called = False
            self.wait_attempts = 0

        def send_signal(self, sig):
            self.sent_signal = sig

        async def wait(self):
            self.wait_attempts += 1
            if self.wait_attempts <= 2:
                await asyncio.sleep(0.05)
            self.returncode = -9
            return self.returncode

        def terminate(self):
            self.terminate_called = True

        def kill(self):
            self.kill_called = True
            self.returncode = -9

    manager = K6ProcessManager()
    manager.process = DummyProcess()

    result = asyncio.run(manager.stop(timeout=0.01))

    assert result is True
    assert manager.process.terminate_called is True
    assert manager.process.kill_called is True


def test_stop_returns_false_when_process_is_none():
    manager = K6ProcessManager()
    manager.process = None

    result = asyncio.run(manager.stop())

    assert result is False


def test_stop_returns_true_when_process_already_finished():
    class DummyProcess:
        returncode = 0

    manager = K6ProcessManager()
    manager.process = DummyProcess()

    result = asyncio.run(manager.stop())

    assert result is True


def test_stop_uses_terminate_when_graceful_signal_raises(monkeypatch):
    class DummyProcess:
        def __init__(self):
            self.returncode = None
            self.pid = 123
            self.terminate_called = False
            self.kill_called = False

        def send_signal(self, _sig):
            raise RuntimeError("cannot send signal")

        async def wait(self):
            self.returncode = 0
            return self.returncode

        def terminate(self):
            self.terminate_called = True
            self.returncode = 0

        def kill(self):
            self.kill_called = True

    monkeypatch.setattr("k6.process_manager.platform.system", lambda: "Linux")
    manager = K6ProcessManager()
    manager.process = DummyProcess()

    result = asyncio.run(manager.stop(timeout=0.01))

    assert result is True
    assert manager.process.terminate_called is True
    assert manager.process.kill_called is False


def test_stop_returns_false_when_kill_wait_times_out():
    class DummyProcess:
        def __init__(self):
            self.returncode = None
            self.pid = 123
            self.terminate_called = False
            self.kill_called = False

        def send_signal(self, _sig):
            pass

        async def wait(self):
            await asyncio.sleep(0.05)
            return self.returncode

        def terminate(self):
            self.terminate_called = True

        def kill(self):
            self.kill_called = True

    manager = K6ProcessManager()
    manager.process = DummyProcess()

    result = asyncio.run(manager.stop(timeout=0.01))

    assert result is False
    assert manager.process.terminate_called is True
    assert manager.process.kill_called is True


def test_scale_returns_stdout_stderr_when_returncode_is_non_zero(monkeypatch):
    class DummyProcess:
        returncode = 42

        async def communicate(self):
            return b"scale stdout", b"scale stderr"

    async def fake_create_subprocess_exec(*_args, **_kwargs):
        return DummyProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    manager = K6ProcessManager()
    returncode, stdout, stderr = asyncio.run(manager.scale(target_vus=10))

    assert returncode == 42
    assert stdout == b"scale stdout"
    assert stderr == b"scale stderr"


def test_apply_web_dashboard_binding_logs_warning_for_url_without_host(caplog):
    manager = K6ProcessManager()
    env = {}
    caplog.set_level(logging.WARNING)

    manager._apply_web_dashboard_binding(env, "http://:7777")

    assert "Could not determine web dashboard host" in caplog.text
    assert "K6_WEB_DASHBOARD_HOST" not in env
