import asyncio
import json
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

    assert str(json_path).endswith("artifacts/summary_20260307_195400.json")
    assert str(html_path).endswith("artifacts/summary_20260307_195400.html")


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

    assert service.state.fail_count == 4
    assert service.state.fail_categories["4xx"] == 1
    assert service.state.fail_categories["500"] == 1
    assert service.state.fail_categories["5xx (not 500)"] == 1
    assert service.state.fail_categories["EOF"] == 1
    assert "errors:" in service.state.last_counter
    assert "4xx: 1" in service.state.last_counter
    assert "500: 1" in service.state.last_counter
    assert "5xx (not 500): 1" in service.state.last_counter
    assert "EOF: 1" in service.state.last_counter
    assert "\n" not in service.state.last_counter


def test_request_failed_without_eof_is_not_double_counted():
    service = K6Service()
    statuses = []

    service._handle_counter_lines(
        'time="2025" level=warning msg="Request Failed" error="Get "https://x": context deadline exceeded"',
        statuses.append,
    )

    assert service.state.fail_count == 0
    assert service.state.fail_categories == {}


def test_non_200_status_zero_is_filtered_from_ui_and_not_counted():
    service = K6Service()
    statuses = []

    handled = service._handle_counter_lines(
        'time="2026-03-12T14:07:46+03:00" level=info msg="❌ Non-200 Response (Endpoint 1) | Correlation-Id: 928cc85a-a8f7-429e-b7bc-7167e664f1fe | Status: 0" source=console',
        statuses.append,
    )

    assert handled is True
    assert service.state.fail_count == 0
    assert service.state.fail_categories == {}


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
                'time="2026" level=warning msg="Request Failed" error="Get "https://x": EOF"\n',
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
    assert service.state.fail_categories == {"4xx": 1, "EOF": 1}
    assert any("✅ Done." in status for status in statuses)
    assert "4xx: 1" in service.state.last_counter
    assert "EOF: 1" in service.state.last_counter


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
    assert "--out web-dashboard=period=5s&open=false" in command
    assert "K6_WEB_DASHBOARD_HOST=127.0.0.1" in command
    assert "K6_WEB_DASHBOARD_PORT=7777" in command
    assert "--summary-export" in command
    assert str(summary_json_path) in command
