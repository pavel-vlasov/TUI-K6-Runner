import asyncio
import json
import os
import platform
import shlex
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from k6.html_summary_report import build_html_summary
from k6.output_parser import (
    clean_cursor_sequences,
    get_fail_category,
    is_default_line,
    is_running_line,
    is_run_complete_line,
    is_scenario_progress_line,
    is_success_line,
)
from k6.presenters import (
    format_done_status,
    format_error_categories_table,
    format_running_status,
    format_start_log,
    format_start_status,
)
from k6.process_manager import K6ProcessManager
from k6.state import K6State


class K6Service:
    def __init__(self) -> None:
        self.state = K6State()
        self.last_update_time = 0.0
        self.last_counter_update_time = 0.0
        self.counter_update_interval = 0.15
        self.process_manager = K6ProcessManager()

    @property
    def is_running(self) -> bool:
        return self.state.is_running

    @is_running.setter
    def is_running(self, value: bool) -> None:
        self.state.is_running = value

    async def stop_k6_process(self):
        return await self.process_manager.stop()

    async def run_k6_process(
        self,
        on_log,
        on_status,
        output_to_ui: bool = True,
        enable_web_dashboard: bool = False,
        web_dashboard_url: str | None = None,
        enable_html_summary: bool = False,
    ):
        if self.state.is_running:
            try:
                on_status("[bold red]⛔ k6 is already running. Wait for the current run to finish.[/bold red]")
                on_log("[bold red]⛔ Re-run blocked: test is already in progress.[/bold red]\n")
            except Exception:
                pass
            return

        self.state.is_running = True
        self.state.success_count = 0
        self.state.fail_count = 0
        self.state.fail_categories = {}
        self.state.last_counter = "requests: ✅ 0  [bold white]│[/bold white]  ❌ 0"
        self.last_update_time = 0.0
        self.last_counter_update_time = 0.0
        run_result_reported = False

        try:
            if output_to_ui:
                on_status(format_start_status())
                on_log(format_start_log())

                summary_json_path, summary_html_path = self._build_summary_paths()

                process = await self.process_manager.start_run(
                    enable_web_dashboard=enable_web_dashboard,
                    web_dashboard_url=web_dashboard_url,
                    summary_json_path=str(summary_json_path),
                    enable_html_summary=enable_html_summary,
                )

                async def read_stream(stream, color):
                    nonlocal run_result_reported
                    while True:
                        line = await stream.readline()
                        if not line:
                            break

                        text = line.decode("utf-8", errors="replace").rstrip()
                        clean_text = clean_cursor_sequences(text)
                        if not clean_text.strip():
                            continue

                        if self._handle_status_lines(clean_text, on_status):
                            continue

                        if self._handle_counter_lines(clean_text, on_status):
                            continue

                        if is_run_complete_line(clean_text) and not run_result_reported:
                            run_result_reported = True
                            if enable_html_summary:
                                self._generate_html_summary_report(summary_json_path, summary_html_path, on_log)
                            on_log("\n[bold green]✅ Test finished.[/bold green]")
                            on_status(format_done_status(self.state.last_counter))

                        on_log(f"[{color}]{clean_text}[/{color}]")

                await asyncio.gather(
                    read_stream(process.stdout, "white"),
                    read_stream(process.stderr, "pale_turquoise4"),
                )

                await process.wait()

                self._update_ui(on_status)
                if not run_result_reported:
                    if enable_html_summary:
                        self._generate_html_summary_report(summary_json_path, summary_html_path, on_log)

                    on_log("\n[bold green]✅ Test finished.[/bold green]")
                    on_status(format_done_status(self.state.last_counter))
            else:
                summary_json_path, _ = self._build_summary_paths()
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
                on_log(
                    "[bold yellow]⚠️ External terminal mode: stop/scale from UI are unavailable for this run.[/bold yellow]\n"
                )
                self._spawn_external_terminal(external_command)

                on_status(
                    "[bold green]📤 External terminal is started. "
                    "[/bold green][bold yellow]Stop/scale are limited in this mode.[/bold yellow]"
                )

        except Exception as e:
            on_log(f"[bold red]💥 Error: {str(e)}[/bold red]")
        finally:
            self.state.is_running = False
            self.process_manager.clear_process()


    def _build_summary_paths(self) -> tuple[Path, Path]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        artifacts_dir = Path("artifacts")
        return artifacts_dir / f"summary_{timestamp}.json", artifacts_dir / f"summary_{timestamp}.html"

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
            terminal_candidates.append(
                (preferred_terminal, ["-e", "bash", "-lc", bash_command])
            )

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
        enable_web_dashboard: bool,
        web_dashboard_url: str | None,
        enable_html_summary: bool,
        summary_json_path: Path,
        shell_type: str = "posix",
    ) -> str:
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
            def _ps_quote(value: str) -> str:
                return "'" + value.replace("'", "''") + "'"

            command_text = " ".join(_ps_quote(part) for part in command_parts)
            if not env_parts:
                return command_text
            env_commands = [f"$env:{name}={_ps_quote(value)};" for name, value in env_parts]
            return f"{' '.join(env_commands)} {command_text}"

        command_text = " ".join(
            part if part == "web-dashboard=period=5s&open=false" else shlex.quote(part)
            for part in command_parts
        )
        if not env_parts:
            return command_text
        env_prefix = " ".join(f"{name}={shlex.quote(value)}" for name, value in env_parts)
        return f"{env_prefix} {command_text}"


    def _generate_html_summary_report(self, summary_json_path: Path, summary_html_path: Path, on_log) -> None:
        try:
            if not summary_json_path.exists():
                on_log(
                    f"[bold yellow]⚠️ HTML summary skipped: JSON summary is missing at {summary_json_path}[/bold yellow]"
                )
                return

            with summary_json_path.open("r", encoding="utf-8") as fp:
                summary_json = json.load(fp)

            summary_html_path.parent.mkdir(parents=True, exist_ok=True)
            html = build_html_summary(summary_json)
            summary_html_path.write_text(html, encoding="utf-8")

            on_log(
                f"[bold cyan]📄 HTML summary report generated: {summary_html_path}[/bold cyan]"
            )
        except Exception as error:
            on_log(f"[bold red]❌ Failed to build HTML summary: {error}[/bold red]")

    def _handle_status_lines(self, clean_text: str, on_status) -> bool:
        running = is_running_line(clean_text)
        default = is_default_line(clean_text)
        scenario = is_scenario_progress_line(clean_text)

        if running:
            self.state.status_running = clean_text
        if default or scenario:
            self.state.status_default = clean_text

        handled = running or default or scenario
        if handled and (time.time() - self.last_update_time > 0.1):
            self._update_ui(on_status)
            self.last_update_time = time.time()

        return handled

    def _handle_counter_lines(self, clean_text: str, on_status) -> bool:
        if is_success_line(clean_text):
            self.state.success_count += 1
            self._refresh_counter()
            self._update_counter_ui(on_status)
            return True

        fail_category = get_fail_category(clean_text)
        if fail_category:
            self.state.fail_count += 1
            self.state.fail_categories[fail_category] = self.state.fail_categories.get(fail_category, 0) + 1
            self._refresh_counter()
            self._update_counter_ui(on_status)
            return True

        # Keep raw k6 failure helper lines (e.g. Non-200 with Status: 0) out of UI log,
        # while counting only lines that have a valid category.
        if "Non-200" in clean_text:
            return True

        return False

    def _refresh_counter(self):
        totals = f"requests: ✅ {self.state.success_count}  [bold white]│[/bold white]  ❌ {self.state.fail_count}"
        categories_table = format_error_categories_table(self.state.fail_categories)
        self.state.last_counter = f"{totals}  [bold white]│[/bold white]  {categories_table}"

    def _update_counter_ui(self, on_status):
        if time.time() - self.last_counter_update_time > self.counter_update_interval:
            self._update_ui(on_status)
            self.last_counter_update_time = time.time()

    def _update_ui(self, on_status):
        on_status(
            format_running_status(
                self.state.last_counter,
                self.state.status_running,
                self.state.status_default,
            )
        )

    async def get_current_vus(self):
        try:
            returncode, stdout, _ = await self.process_manager.status()
            if returncode == 0:
                data = json.loads(stdout.decode())
                vus = data.get("vus") or data.get("metrics", {}).get("vus", {}).get("value")
                if vus is not None:
                    self.state.current_vus_internal = int(vus)
                    return self.state.current_vus_internal
        except Exception:
            pass
        return self.state.current_vus_internal

    async def set_vus(self, target_vus: int, on_log):
        if not self.state.is_running:
            on_log("[bold red]❌ No active execution[/bold red]\n")
            return

        if target_vus < 1:
            target_vus = 1

        try:
            returncode, _, stderr = await self.process_manager.scale(target_vus)
            if returncode == 0:
                self.state.current_vus_internal = target_vus
                on_log(f"[bold cyan]🔼 VUs number is changed to: {target_vus} VUs[/bold cyan]\n")
                return True

            err_text = stderr.decode()
            on_log(f"[bold red]❌ Scaling error: {err_text}[/bold red]\n")
            return False
        except Exception as e:
            on_log(f"[bold red]💥 Error of connection to k6: {str(e)}[/bold red]\n")
            return False
