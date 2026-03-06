import asyncio
import json
import platform
import subprocess
import time

from k6.output_parser import (
    clean_cursor_sequences,
    is_default_line,
    is_fail_line,
    is_running_line,
    is_scenario_progress_line,
    is_success_line,
)
from k6.metrics import extract_snapshot, format_metrics_snapshot
from k6.presenters import (
    format_done_status,
    format_run_summary,
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

    async def run_k6_process(self, on_log, on_status, output_to_ui: bool = True, on_metrics=None, metrics_enabled=False):
        if self.state.is_running:
            try:
                on_status("[bold red]⛔ k6 уже выполняется. Дождитесь завершения текущего запуска.[/bold red]")
                on_log("[bold red]⛔ Повторный запуск заблокирован: тест уже идёт.[/bold red]\n")
            except Exception:
                pass
            return

        self.state.is_running = True
        self.state.success_count = 0
        self.state.fail_count = 0
        self.state.last_counter = "requests: ✅ 0  [bold white]│[/bold white]  ❌ 0"
        self.last_update_time = 0.0

        try:
            if output_to_ui:
                on_status(format_start_status())
                on_log(format_start_log())

                process = await self.process_manager.start_run()

                async def poll_metrics():
                    if not on_metrics or not metrics_enabled:
                        return

                    last_error = ""
                    metric_types: dict[str, str] = {}
                    ordered_metric_names: list[str] = []
                    on_metrics("[bold yellow]Collecting metrics from SSE stream /events...[/bold yellow]")

                    def aggregate_names(metric_type: str) -> list[str]:
                        mapping = {
                            "gauge": ["value"],
                            "rate": ["rate"],
                            "counter": ["count", "rate"],
                            "trend": ["avg", "max", "med", "min", "p(90)", "p(95)", "p(99)"],
                        }
                        return mapping.get(metric_type, [])

                    def parse_aggregates_matrix(matrix: list[list[float]]) -> dict[str, dict[str, float]]:
                        result: dict[str, dict[str, float]] = {}

                        for idx, sample_values in enumerate(matrix):
                            if idx >= len(ordered_metric_names):
                                continue

                            metric_name = ordered_metric_names[idx]
                            metric_type = metric_types.get(metric_name, "")
                            keys = aggregate_names(metric_type)

                            normalized_values = sample_values
                            if len(sample_values) > len(keys) and sample_values and sample_values[0] > 1_000_000_000_000:
                                normalized_values = sample_values[1:]

                            if len(keys) != len(normalized_values):
                                continue

                            result[metric_name] = {keys[i]: normalized_values[i] for i in range(len(keys))}

                        return result

                    try:
                        async for event_name, event_data in self.process_manager.stream_metrics_events():
                            if not self.state.is_running:
                                break

                            try:
                                payload = json.loads(event_data)
                                if event_name == "metric" and isinstance(payload, dict):
                                    for metric_name, metric_info in payload.items():
                                        if isinstance(metric_info, dict):
                                            metric_type = metric_info.get("type")
                                            if isinstance(metric_type, str):
                                                metric_types[metric_name] = metric_type
                                    ordered_metric_names = sorted(metric_types.keys())
                                    continue

                                if event_name == "metric" and isinstance(payload, list):
                                    for metric_info in payload:
                                        if not isinstance(metric_info, dict):
                                            continue
                                        metric_name = metric_info.get("name")
                                        metric_type = metric_info.get("type")
                                        if isinstance(metric_name, str) and isinstance(metric_type, str):
                                            metric_types[metric_name] = metric_type
                                    ordered_metric_names = sorted(metric_types.keys())
                                    continue

                                if event_name in {"snapshot", "cumulative", "start", "stop"}:
                                    if isinstance(payload, dict):
                                        snapshot = extract_snapshot(payload)
                                        on_metrics(format_metrics_snapshot(snapshot))
                                        last_error = ""
                                        continue

                                    if isinstance(payload, list) and all(isinstance(item, list) for item in payload):
                                        metrics_payload = parse_aggregates_matrix(payload)
                                        if metrics_payload:
                                            snapshot = extract_snapshot(metrics_payload)
                                            on_metrics(format_metrics_snapshot(snapshot))
                                            last_error = ""
                            except json.JSONDecodeError:
                                current_error = "metrics SSE event is not valid JSON"
                                if current_error != last_error:
                                    on_metrics("[bold yellow]⚠ SSE event is not JSON.[/bold yellow]")
                                    last_error = current_error
                    except Exception as e:
                        on_metrics(f"[bold red]⚠ SSE metrics stream error: {str(e)}[/bold red]")

                async def read_stream(stream, color):
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

                        on_log(f"[{color}]{clean_text}[/{color}]")

                await asyncio.gather(
                    read_stream(process.stdout, "white"),
                    read_stream(process.stderr, "pale_turquoise4"),
                    poll_metrics(),
                )

                await process.wait()
                on_log(format_run_summary(self.state.success_count, self.state.fail_count))
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

        if is_fail_line(clean_text):
            self.state.fail_count += 1
            self._refresh_counter()
            self._update_ui(on_status)
            return True

        return False

    def _refresh_counter(self):
        self.state.last_counter = (
            f"requests: ✅ {self.state.success_count}  [bold white]│[/bold white]  ❌ {self.state.fail_count}"
        )

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
