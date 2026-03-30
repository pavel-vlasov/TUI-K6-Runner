import asyncio
import json
import platform
import shlex
from pathlib import Path

from k6.backends.embedded import EmbeddedProcessBackend
from k6.backends.external_terminal import ExternalTerminalBackend
from k6.backends.factory import select_backend
from k6.service import K6Service


def test_select_backend_uses_output_to_ui_flag():
    backend_ui = select_backend({"k6": {"logging": {"outputToUI": True}}})
    backend_external = select_backend({"k6": {"logging": {"outputToUI": False}}})

    assert isinstance(backend_ui, EmbeddedProcessBackend)
    assert isinstance(backend_external, ExternalTerminalBackend)


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
    assert json_path.parent.name == "artifacts"
    assert html_path.name == "summary_20260307_195400.html"
    assert html_path.parent.name == "artifacts"


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


class _FakeEmbeddedBackend:
    class _Caps:
        supports_stop = True
        supports_scale = True
        supports_status = True

    capabilities = _Caps()

    def __init__(self):
        self.cleared = False

    async def start_run(self, **kwargs):
        kwargs["on_output_line"]('time="2026" level=info msg="Processed request: 200 ✅"\n', "white")
        kwargs["on_output_line"](
            'time="2026" level=warning msg="Request Failed" error="Get "https://x": context deadline exceeded"\n',
            "pale_turquoise4",
        )
        kwargs["on_run_complete"]()

    async def stop(self):
        return True

    async def scale(self, vus):
        return 0, b"", b""

    async def status(self):
        return 0, b'{"vus": 5}', b""

    def clear(self):
        self.cleared = True


class _FakeExternalBackend:
    class _Caps:
        supports_stop = False
        supports_scale = False
        supports_status = False

    capabilities = _Caps()

    async def start_run(self, **kwargs):
        kwargs["on_log"]("📤 k6 starting in external terminal.\n")
        kwargs["on_status"]("external started")

    async def stop(self):
        return False

    async def scale(self, vus):
        del vus
        return 1, b"", b"unsupported"

    async def status(self):
        return 1, b"", b"unsupported"

    def clear(self):
        return None


def test_run_k6_process_embedded_backend_updates_counters(monkeypatch):
    service = K6Service()
    statuses = []
    logs = []

    monkeypatch.setattr("k6.service.select_backend", lambda _cfg: _FakeEmbeddedBackend())

    asyncio.run(
        service.run_k6_process(
            on_log=logs.append,
            on_status=statuses.append,
            output_to_ui=True,
            enable_html_summary=False,
        )
    )

    assert service.state.success_count == 1
    assert service.state.fail_count == 1
    assert service.state.fail_categories == {"timeout": 1}
    assert any("✅ Done." in status for status in statuses)


def test_run_k6_process_external_backend_does_not_emit_ui_start(monkeypatch):
    service = K6Service()
    statuses = []
    logs = []

    monkeypatch.setattr("k6.service.select_backend", lambda _cfg: _FakeExternalBackend())

    asyncio.run(
        service.run_k6_process(
            on_log=logs.append,
            on_status=statuses.append,
            output_to_ui=False,
            enable_html_summary=False,
        )
    )

    assert any("external started" in s for s in statuses)
    assert not any("Starting" in s for s in statuses)


def test_run_k6_process_blocks_rerun_when_already_running():
    service = K6Service()
    service.state.is_running = True
    statuses = []
    logs = []

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


def test_build_external_terminal_command_for_macos(monkeypatch):
    backend = ExternalTerminalBackend()
    monkeypatch.setattr("k6.backends.external_terminal.platform.system", lambda: "Darwin")
    monkeypatch.setattr(
        "k6.backends.external_terminal.shutil.which",
        lambda name: "/usr/bin/osascript" if name == "osascript" else None,
    )

    command = backend._build_external_terminal_command('k6 run "test.js"')

    assert command[0] == "osascript"
    assert "tell application \"Terminal\" to do script" in command[2]
    assert 'k6 run \\"test.js\\"' in command[2]


def test_build_external_terminal_command_for_macos_raises_when_osascript_missing(monkeypatch):
    backend = ExternalTerminalBackend()
    monkeypatch.setattr("k6.backends.external_terminal.platform.system", lambda: "Darwin")
    monkeypatch.setattr("k6.backends.external_terminal.shutil.which", lambda _name: None)

    try:
        backend._build_external_terminal_command("k6 run test.js")
    except RuntimeError as error:
        assert "osascript" in str(error)
    else:
        raise AssertionError("Expected RuntimeError when osascript is unavailable")


def test_build_external_k6_command_windows_uses_powershell_env_syntax(monkeypatch, tmp_path):
    backend = ExternalTerminalBackend()
    monkeypatch.setattr("k6.backends.external_terminal.platform.system", lambda: "Windows")

    command = backend._build_external_k6_command(
        enable_web_dashboard=True,
        web_dashboard_url="http://127.0.0.1:7777",
        enable_html_summary=True,
        summary_json_path=tmp_path / "summary.json",
        shell_type="powershell",
    )

    assert "$env:K6_WEB_DASHBOARD_OPEN='false';" in command
    assert "$env:K6_WEB_DASHBOARD_HOST='127.0.0.1';" in command
    assert "$env:K6_WEB_DASHBOARD_PORT='7777';" in command
    assert "'k6' 'run' 'test.js'" in command


def test_build_external_k6_command_posix_quotes_web_dashboard_out_as_single_token(tmp_path):
    backend = ExternalTerminalBackend()
    summary_json_path = tmp_path / "summary.json"

    command = backend._build_external_k6_command(
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


def test_set_vus_returns_false_when_backend_has_no_scale(monkeypatch):
    service = K6Service()
    service.state.is_running = True
    service.backend = _FakeExternalBackend()
    logs = []

    result = asyncio.run(service.set_vus(10, logs.append))

    assert result is False
    assert any("unavailable" in line for line in logs)


def test_get_current_vus_returns_internal_value_when_backend_has_no_status():
    service = K6Service()
    service.state.current_vus_internal = 7
    service.backend = _FakeExternalBackend()

    vus = asyncio.run(service.get_current_vus())

    assert vus == 7


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
