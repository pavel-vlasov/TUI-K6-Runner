import asyncio
import json
import platform
import shlex
from pathlib import Path

from k6.service import K6Service


def test_build_summary_paths_uses_timestamped_files(monkeypatch):
    class FrozenDatetime:
        @classmethod
        def now(cls):
            class _D:
                def strftime(self, _fmt):
                    return "20260307_195400"

            return _D()

    monkeypatch.setattr("k6.service.datetime", FrozenDatetime)

    service = K6Service()
    json_path, html_path = service._build_summary_paths()

    assert json_path.name == "summary_20260307_195400.json"
    assert str(json_path.parent).endswith("artifacts")
    assert html_path.name == "summary_20260307_195400.html"
    assert str(html_path.parent).endswith("artifacts")


def test_handle_counter_lines_accumulates_categories_and_totals():
    service = K6Service()
    statuses = []

    service._handle_counter_lines(
        'time="2025" level=error msg="❌ Non-200 Response (ep) | Correlation-Id: c1 | Status: 404"',
        statuses.append,
    )
    service._handle_counter_lines(
        'time="2025" level=error msg="❌ Non-200 Response (ep) | Correlation-Id: c2 | Status: 500"',
        statuses.append,
    )
    service._handle_counter_lines(
        'time="2025" level=error msg="❌ Non-200 Response (ep) | Correlation-Id: c3 | Status: 503"',
        statuses.append,
    )
    service._handle_counter_lines(
        'time="2025" level=warning msg="Request Failed" error="Get "https://x": EOF"',
        statuses.append,
    )
    service._handle_counter_lines(
        'time="2025" level=warning msg="Request Failed" error="Get "https://x": context deadline exceeded"',
        statuses.append,
    )
    service._handle_counter_lines(
        'time="2025" level=error msg="❌ Non-200 Response (ep) | Correlation-Id: c4 | Status: 0"',
        statuses.append,
    )

    assert service.state.fail_count == 5
    assert service.state.fail_categories["4xx"] == 1
    assert service.state.fail_categories["500"] == 1
    assert service.state.fail_categories["5xx (not 500)"] == 1
    assert service.state.fail_categories["EOF"] == 1
    assert service.state.fail_categories["timeout"] == 1
    assert "errors:" in service.state.last_counter
    assert "4xx: 1" in service.state.last_counter
    assert "500: 1" in service.state.last_counter
    assert "5xx (not 500): 1" in service.state.last_counter
    assert "EOF: 1" in service.state.last_counter
    assert "timeout: 1" in service.state.last_counter
    assert "\n" not in service.state.last_counter


def test_request_failed_without_eof_is_counted_with_category():
    service = K6Service()
    statuses = []

    service._handle_counter_lines(
        'time="2025" level=warning msg="Request Failed" error="Get "https://x": context deadline exceeded"',
        statuses.append,
    )

    assert service.state.fail_count == 1
    assert service.state.fail_categories == {"timeout": 1}


def test_non_200_status_zero_is_filtered_from_ui_and_not_double_counted():
    service = K6Service()
    statuses = []

    handled = service._handle_counter_lines(
        'time="2026-03-12T14:07:46+03:00" level=info msg="❌ Non-200 Response (Endpoint 1) | Correlation-Id: 928cc85a-a8f7-429e-b7bc-7167e664f1fe | Status: 0" source=console',
        statuses.append,
    )

    assert handled is True
    assert service.state.fail_count == 0
    assert service.state.fail_categories == {}


def test_request_failed_can_be_hidden_from_ui_but_still_updates_counters():
    service = K6Service()
    statuses = []

    handled = service._handle_counter_lines(
        'time="2026-03-12T14:07:46+03:00" level=warning msg="Request Failed" error="Get "https://x": lookup api.example.test: no such host"',
        statuses.append,
    )

    assert handled is True
    assert service.state.fail_count == 1
    assert service.state.fail_categories == {"dns": 1}
    assert "dns: 1" in service.state.last_counter


def test_handle_counter_lines_throttles_status_updates_but_keeps_totals(monkeypatch):
    service = K6Service()
    statuses = []
    fake_time = {"current": 0.0}

    def _time():
        return fake_time["current"]

    monkeypatch.setattr("k6.service.time.time", _time)

    lines = [
        'time="2026" level=info msg="Processed request: 200 ✅"',
        'time="2026" level=error msg="❌ Non-200 Response (ep) | Correlation-Id: c1 | Status: 404"',
        'time="2026" level=info msg="Processed request: 200 ✅"',
        'time="2026" level=warning msg="Request Failed" error="Get "https://x": EOF"',
        'time="2026" level=info msg="Processed request: 200 ✅"',
        'time="2026" level=error msg="❌ Non-200 Response (ep) | Correlation-Id: c2 | Status: 500"',
    ]

    for line in lines:
        service._handle_counter_lines(line, statuses.append)
        fake_time["current"] += 0.01

    assert len(statuses) < len(lines)
    assert service.state.success_count == 3
    assert service.state.fail_count == 3
    assert service.state.fail_categories == {"4xx": 1, "EOF": 1, "500": 1}


class _FakeStream:
    def __init__(self, lines: list[str]):
        self._lines = [line.encode("utf-8") for line in lines]

    async def readline(self):
        if self._lines:
            return self._lines.pop(0)
        return b""


class _FakeProcess:
    def __init__(self, stdout_lines: list[str], stderr_lines: list[str]):
        self.stdout = _FakeStream(stdout_lines)
        self.stderr = _FakeStream(stderr_lines)

    async def wait(self):
        return 0


def test_run_k6_process_updates_success_and_fail_counters_from_stdout_stderr():
    service = K6Service()
    statuses = []
    logs = []

    async def fake_start_run(**_kwargs):
        return _FakeProcess(
            stdout_lines=[
                'time="2026" level=info msg="Processed request: 200 ✅"\n',
                "default [100%] 1/1 VUs\n",
            ],
            stderr_lines=[
                'time="2026" level=error msg="❌ Non-200 Response (ep) | Correlation-Id: c1 | Status: 404"\n',
                'time="2026" level=warning msg="Request Failed" error="Get "https://x": context deadline exceeded"\n',
            ],
        )

    service.process_manager.start_run = fake_start_run

    asyncio.run(
        service.run_k6_process(
            on_log=logs.append,
            on_status=statuses.append,
            output_to_ui=True,
            enable_html_summary=False,
        )
    )

    assert service.state.success_count == 1
    assert service.state.fail_count == 2
    assert service.state.fail_categories == {"4xx": 1, "timeout": 1}
    assert any("✅ Done." in status for status in statuses)
    assert "4xx: 1" in service.state.last_counter
    assert "timeout: 1" in service.state.last_counter


def test_run_k6_process_blocks_rerun_when_already_running():
    service = K6Service()
    service.state.is_running = True
    statuses = []
    logs = []

    async def fake_start_run(**_kwargs):
        raise AssertionError("start_run must not be called when state.is_running=True")

    service.process_manager.start_run = fake_start_run

    asyncio.run(
        service.run_k6_process(
            on_log=logs.append,
            on_status=statuses.append,
            output_to_ui=True,
            enable_html_summary=False,
        )
    )

    assert any("already running" in status for status in statuses)
    assert any("Re-run blocked" in log for log in logs)


def test_run_k6_process_safely_finishes_when_start_callbacks_raise():
    service = K6Service()
    service.state.is_running = True

    def bad_on_log(_message):
        raise RuntimeError("log callback failed")

    def bad_on_status(_message):
        raise RuntimeError("status callback failed")

    asyncio.run(
        service.run_k6_process(
            on_log=bad_on_log,
            on_status=bad_on_status,
            output_to_ui=True,
            enable_html_summary=False,
        )
    )

    assert service.state.is_running is True
    assert service.process_manager.process is None


def test_run_k6_process_generates_html_summary_when_enabled(tmp_path):
    service = K6Service()
    statuses = []
    logs = []
    summary_json_path = tmp_path / "summary.json"
    summary_html_path = tmp_path / "summary.html"

    async def fake_start_run(**kwargs):
        json_path = Path(kwargs["summary_json_path"])
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps({"metrics": {}, "root_group": {"checks": [], "groups": []}}),
            encoding="utf-8",
        )
        return _FakeProcess(
            stdout_lines=["default [100%] 1/1 VUs\n"],
            stderr_lines=[],
        )

    service.process_manager.start_run = fake_start_run
    service._build_summary_paths = lambda: (summary_json_path, summary_html_path)

    asyncio.run(
        service.run_k6_process(
            on_log=logs.append,
            on_status=statuses.append,
            output_to_ui=True,
            enable_html_summary=True,
        )
    )

    assert summary_html_path.exists()
    assert any("HTML summary report generated" in line for line in logs)


def test_build_external_terminal_command_for_macos(monkeypatch):
    service = K6Service()
    monkeypatch.setattr("k6.service.platform.system", lambda: "Darwin")
    monkeypatch.setattr("k6.service.shutil.which", lambda name: "/usr/bin/osascript" if name == "osascript" else None)

    command = service._build_external_terminal_command('k6 run "test.js"')

    assert command[0] == "osascript"
    assert "tell application \"Terminal\" to do script" in command[2]
    assert 'k6 run \\"test.js\\"' in command[2]


def test_build_external_terminal_command_for_macos_raises_when_osascript_missing(monkeypatch):
    service = K6Service()
    monkeypatch.setattr("k6.service.platform.system", lambda: "Darwin")
    monkeypatch.setattr("k6.service.shutil.which", lambda _name: None)

    try:
        service._build_external_terminal_command("k6 run test.js")
    except RuntimeError as error:
        assert "osascript" in str(error)
    else:
        raise AssertionError("Expected RuntimeError when osascript is unavailable")


def test_run_k6_process_external_terminal_mode_keeps_dashboard_and_summary_options(tmp_path):
    service = K6Service()
    logs = []
    statuses = []
    captured = {}

    summary_json_path = tmp_path / "nested" / "summary.json"
    service._build_summary_paths = lambda: (summary_json_path, tmp_path / "nested" / "summary.html")

    def fake_spawn_external_terminal(command: str):
        captured["command"] = command
        return None

    service._spawn_external_terminal = fake_spawn_external_terminal

    asyncio.run(
        service.run_k6_process(
            on_log=logs.append,
            on_status=statuses.append,
            output_to_ui=False,
            enable_web_dashboard=True,
            web_dashboard_url="http://127.0.0.1:7777",
            enable_html_summary=True,
        )
    )

    command = captured["command"]
    assert "--out" in command
    assert "web-dashboard=period=5s&open=false" in command
    assert "K6_WEB_DASHBOARD_HOST" in command
    assert "K6_WEB_DASHBOARD_PORT" in command
    if platform.system() == "Windows":
        assert "$env:K6_WEB_DASHBOARD_HOST='127.0.0.1';" in command
        assert "$env:K6_WEB_DASHBOARD_PORT='7777';" in command
    else:
        assert "K6_WEB_DASHBOARD_HOST=127.0.0.1" in command
        assert "K6_WEB_DASHBOARD_PORT=7777" in command
    assert "cd " in command
    assert "--summary-export" in command
    assert str(summary_json_path) in command


def test_build_external_k6_command_windows_uses_powershell_env_syntax(monkeypatch, tmp_path):
    service = K6Service()
    monkeypatch.setattr("k6.service.platform.system", lambda: "Windows")

    command = service._build_external_k6_command(
        enable_web_dashboard=True,
        web_dashboard_url="http://127.0.0.1:7777",
        enable_html_summary=True,
        summary_json_path=tmp_path / "summary.json",
        shell_type="powershell",
    )

    assert "$env:K6_WEB_DASHBOARD_OPEN='false';" in command
    assert "$env:K6_WEB_DASHBOARD_HOST='127.0.0.1';" in command
    assert "$env:K6_WEB_DASHBOARD_PORT='7777';" in command
    assert "'k6' 'run'" in command
    assert "test.js" in command


def test_build_external_k6_command_posix_quotes_web_dashboard_out_as_single_token(tmp_path):
    service = K6Service()
    summary_json_path = tmp_path / "summary.json"

    command = service._build_external_k6_command(
        enable_web_dashboard=True,
        web_dashboard_url="http://127.0.0.1:7777",
        enable_html_summary=True,
        summary_json_path=summary_json_path,
        shell_type="posix",
    )

    assert "'web-dashboard=period=5s&open=false'" in command
    assert "web-dashboard=period=5s&open=false --summary-export" not in command

    tokens = shlex.split(command)

    out_index = tokens.index("--out")
    assert tokens[out_index + 1] == "web-dashboard=period=5s&open=false"

    summary_export_index = tokens.index("--summary-export")
    assert tokens[summary_export_index + 1] == str(summary_json_path)


def test_set_vus_returns_false_and_logs_scaling_error_when_scale_fails():
    service = K6Service()
    service.state.is_running = True
    logs = []

    async def fake_scale(_target_vus: int):
        return 1, b"", b"cannot scale"

    service.process_manager.scale = fake_scale

    result = asyncio.run(service.set_vus(10, logs.append))

    assert result is False
    assert any("Scaling error" in line for line in logs)


def test_set_vus_returns_false_and_logs_connection_error_on_scale_exception():
    service = K6Service()
    service.state.is_running = True
    logs = []

    async def fake_scale(_target_vus: int):
        raise RuntimeError("boom")

    service.process_manager.scale = fake_scale

    result = asyncio.run(service.set_vus(10, logs.append))

    assert result is False
    assert any("Error of connection to k6" in line for line in logs)


def test_set_vus_normalizes_target_to_one_before_scale_call():
    service = K6Service()
    service.state.is_running = True
    logs = []
    captured = {}

    async def fake_scale(target_vus: int):
        captured["target_vus"] = target_vus
        return 0, b"", b""

    service.process_manager.scale = fake_scale

    result = asyncio.run(service.set_vus(0, logs.append))

    assert result is True
    assert captured["target_vus"] == 1


def test_get_current_vus_returns_internal_value_when_status_returncode_is_non_zero():
    service = K6Service()
    service.state.current_vus_internal = 7

    async def fake_status():
        return 2, b'{"vus": 999}', b"failed"

    service.process_manager.status = fake_status

    vus = asyncio.run(service.get_current_vus())

    assert vus == 7


def test_get_current_vus_returns_internal_value_when_status_stdout_is_invalid_json():
    service = K6Service()
    service.state.current_vus_internal = 5

    async def fake_status():
        return 0, b"{invalid json", b""

    service.process_manager.status = fake_status

    vus = asyncio.run(service.get_current_vus())

    assert vus == 5


def test_handle_status_lines_throttles_ui_updates_by_interval(monkeypatch):
    service = K6Service()
    statuses = []
    fake_time = {"current": 0.0}

    monkeypatch.setattr("k6.service.time.time", lambda: fake_time["current"])

    handled = service._handle_status_lines("running (10s), 01/10 VUs", statuses.append)
    assert handled is True
    assert len(statuses) == 0

    fake_time["current"] = 0.11
    handled = service._handle_status_lines("default [ 10% ] 1/10 VUs", statuses.append)
    assert handled is True
    assert len(statuses) == 1


def test_handle_status_lines_updates_running_and_default_status_fields():
    service = K6Service()
    statuses = []

    service._handle_status_lines("running (5s), 01/05 VUs", statuses.append)
    service._handle_status_lines("default [ 20% ] 1/5 VUs", statuses.append)

    assert service.state.status_running == "running (5s), 01/05 VUs"
    assert service.state.status_default == "default [ 20% ] 1/5 VUs"


def test_generate_html_summary_logs_warning_when_json_file_missing(tmp_path):
    service = K6Service()
    logs = []
    json_path = tmp_path / "missing.json"
    html_path = tmp_path / "summary.html"

    service._generate_html_summary_report(json_path, html_path, logs.append)

    assert any("HTML summary skipped" in line for line in logs)
    assert not html_path.exists()


def test_generate_html_summary_logs_red_error_when_builder_raises(tmp_path, monkeypatch):
    service = K6Service()
    logs = []
    json_path = tmp_path / "summary.json"
    html_path = tmp_path / "summary.html"
    json_path.write_text('{"metrics": {}, "root_group": {"checks": [], "groups": []}}', encoding="utf-8")

    def fake_build_html_summary(_summary_json):
        raise RuntimeError("boom")

    monkeypatch.setattr("k6.service.build_html_summary", fake_build_html_summary)

    service._generate_html_summary_report(json_path, html_path, logs.append)

    assert any("[bold red]❌ Failed to build HTML summary:" in line for line in logs)
