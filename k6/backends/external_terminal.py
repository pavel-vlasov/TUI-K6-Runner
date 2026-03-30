from __future__ import annotations

import os
import platform
import shlex
import shutil
import subprocess
from pathlib import Path
from collections.abc import Callable
from urllib.parse import urlparse

from k6.backends.base import ExecutionBackend
from k6.backends.capabilities import ExecutionCapabilities


class ExternalTerminalBackend(ExecutionBackend):
    @property
    def capabilities(self) -> ExecutionCapabilities:
        return ExecutionCapabilities(can_stop=False, can_scale=False, can_capture_logs=False, can_read_metrics=False)

    async def start_run(
        self,
        *,
        enable_web_dashboard: bool,
        web_dashboard_url: str | None,
        enable_html_summary: bool,
        summary_json_path: Path,
        on_log: Callable[[str], None],
        on_status: Callable[[str], None],
        on_output_line,
        on_run_complete,
    ) -> None:
        del on_output_line, on_run_complete
        system_name = platform.system()
        shell_type = "powershell" if system_name == "Windows" else "posix"
        external_command = self._build_external_k6_command(
            enable_web_dashboard=enable_web_dashboard,
            web_dashboard_url=web_dashboard_url,
            enable_html_summary=enable_html_summary,
            summary_json_path=summary_json_path,
            shell_type=shell_type,
        )

        on_log("📤 k6 starting in external terminal.\n")
        on_log("[bold yellow]⚠️ External terminal mode: stop/scale from UI are unavailable for this run.[/bold yellow]\n")
        self._spawn_external_terminal(external_command)
        on_status(
            "[bold green]📤 External terminal is started. "
            "[/bold green][bold yellow]Stop/scale are limited in this mode.[/bold yellow]"
        )

    async def stop(self) -> bool:
        return False

    async def scale(self, vus: int) -> tuple[int, bytes, bytes]:
        del vus
        return 1, b"", b"Scaling is not supported by external terminal backend"

    def _build_external_terminal_command(self, command: str, system_name: str | None = None) -> list[str]:
        system_name = system_name or platform.system()

        if system_name == "Windows":
            return ["powershell.exe", "-NoExit", "-Command", f"chcp 65001; {command}"]
        if system_name == "Darwin":
            if not shutil.which("osascript"):
                raise RuntimeError("`osascript` was not found on PATH. Cannot open Terminal on macOS.")
            escaped_command = command.replace("\\", "\\\\").replace('"', '\\"')
            return [
                "osascript",
                "-e",
                f'tell application "Terminal" to do script "{escaped_command}"',
                "-e",
                'tell application "Terminal" to activate',
            ]

        bash_command = f"{command}; exec bash"
        preferred_terminal = os.environ.get("TERMINAL")
        terminal_candidates: list[tuple[str, list[str]]] = []

        if preferred_terminal:
            terminal_candidates.append((preferred_terminal, ["-e", "bash", "-lc", bash_command]))

        terminal_candidates.extend(
            [
                ("x-terminal-emulator", ["-e", "bash", "-lc", bash_command]),
                ("gnome-terminal", ["--", "bash", "-lc", bash_command]),
                ("konsole", ["-e", "bash", "-lc", bash_command]),
                ("xfce4-terminal", ["-e", "bash", "-lc", bash_command]),
                ("xterm", ["-e", "bash", "-lc", bash_command]),
                ("alacritty", ["-e", "bash", "-lc", bash_command]),
                ("kitty", ["-e", "bash", "-lc", bash_command]),
            ]
        )

        for terminal, args in terminal_candidates:
            if shutil.which(terminal):
                return [terminal, *args]

        raise RuntimeError(
            "No supported terminal emulator found. "
            "Install one of: x-terminal-emulator, gnome-terminal, konsole, xfce4-terminal, xterm, alacritty, kitty."
        )

    def _spawn_external_terminal(self, command: str) -> subprocess.Popen:
        system_name = platform.system()
        terminal_command = self._build_external_terminal_command(command, system_name=system_name)

        if system_name == "Windows":
            create_new_console = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
            return subprocess.Popen(terminal_command, creationflags=create_new_console)

        return subprocess.Popen(terminal_command)

    def _build_external_k6_command(
        self,
        *,
        enable_web_dashboard: bool,
        web_dashboard_url: str | None,
        enable_html_summary: bool,
        summary_json_path: Path,
        shell_type: str = "posix",
    ) -> str:
        def _powershell_quote(value: str) -> str:
            return "'" + value.replace("'", "''") + "'"

        command_parts = ["k6", "run", "test.js"]
        env_parts: list[tuple[str, str]] = []

        if enable_web_dashboard:
            command_parts.extend(["--out", "web-dashboard=period=5s&open=false"])
            env_parts.append(("K6_WEB_DASHBOARD_OPEN", "false"))
            parsed_url = urlparse(web_dashboard_url or "")
            if parsed_url.hostname:
                env_parts.append(("K6_WEB_DASHBOARD_HOST", parsed_url.hostname))
            if parsed_url.port:
                env_parts.append(("K6_WEB_DASHBOARD_PORT", str(parsed_url.port)))

        if enable_html_summary:
            summary_json_path.parent.mkdir(parents=True, exist_ok=True)
            command_parts.extend(["--summary-export", str(summary_json_path)])

        if shell_type == "powershell":
            command_text = " ".join(_powershell_quote(part) for part in command_parts)
            if not env_parts:
                return command_text
            env_commands = [f"$env:{name}={_powershell_quote(value)};" for name, value in env_parts]
            return f"{' '.join(env_commands)} {command_text}"

        command_text = shlex.join(command_parts)
        if not env_parts:
            return command_text
        env_prefix = " ".join(f"{name}={shlex.quote(value)}" for name, value in env_parts)
        return f"{env_prefix} {command_text}"
