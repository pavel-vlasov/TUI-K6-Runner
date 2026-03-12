import asyncio
import json
import platform
import subprocess
import time
from datetime import datetime
from pathlib import Path

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

                if not run_result_reported:
                    if enable_html_summary:
                        self._generate_html_summary_report(summary_json_path, summary_html_path, on_log)

                    on_log("\n[bold green]✅ Test finished.[/bold green]")
                    on_status(format_done_status(self.state.last_counter))
            else:
                on_log("📤 k6 starting in external terminal.\n")

                if platform.system() == "Windows":
                    subprocess.Popen(
                        'start powershell.exe -NoExit -Command "chcp 65001; k6 run test.js"',
                        shell=True,
                    )
                else:
                    subprocess.Popen(
                        ["x-terminal-emulator", "-e", "bash", "-c", "k6 run test.js; exec bash"]
                    )

                on_status("[bold green]📤 External terminal is started.[/bold green]")

        except Exception as e:
            on_log(f"[bold red]💥 Error: {str(e)}[/bold red]")
        finally:
            self.state.is_running = False
            self.process_manager.clear_process()


    def _build_summary_paths(self) -> tuple[Path, Path]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        artifacts_dir = Path("artifacts")
        return artifacts_dir / f"summary_{timestamp}.json", artifacts_dir / f"summary_{timestamp}.html"


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
            self._update_ui(on_status)
            return True

        fail_category = get_fail_category(clean_text)
        if fail_category:
            self.state.fail_count += 1
            self.state.fail_categories[fail_category] = self.state.fail_categories.get(fail_category, 0) + 1
            self._refresh_counter()
            self._update_ui(on_status)
            return True

        return False

    def _refresh_counter(self):
        totals = f"requests: ✅ {self.state.success_count}  [bold white]│[/bold white]  ❌ {self.state.fail_count}"
        categories_table = format_error_categories_table(self.state.fail_categories)
        self.state.last_counter = f"{totals}\n{categories_table}"

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
