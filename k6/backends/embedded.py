from __future__ import annotations

import asyncio
from pathlib import Path
from collections.abc import Callable

from k6.backends.base import ExecutionBackend
from k6.backends.capabilities import ExecutionCapabilities
from k6.output_parser import clean_cursor_sequences, is_run_complete_line
from k6.process_manager import K6ProcessManager


def _split_stream_buffer(
    buffer: str, pending_progress_flag: bool = False
) -> tuple[list[tuple[str, bool]], str, bool]:
    lines: list[tuple[str, bool]] = []
    start = 0
    segment_is_progress = pending_progress_flag

    for index, char in enumerate(buffer):
        if char not in {"\n", "\r"}:
            continue

        segment = buffer[start:index]
        lines.append((segment, segment_is_progress or char == "\r"))
        segment_is_progress = char == "\r"
        start = index + 1

    return lines, buffer[start:], segment_is_progress


class EmbeddedProcessBackend(ExecutionBackend):
    def __init__(self, process_manager: K6ProcessManager | None = None) -> None:
        self.process_manager = process_manager or K6ProcessManager()

    @property
    def capabilities(self) -> ExecutionCapabilities:
        return ExecutionCapabilities(can_stop=True, can_scale=True, can_capture_logs=True, can_read_metrics=True)

    async def start_run(
        self,
        *,
        connection_management: str,
        enable_web_dashboard: bool,
        web_dashboard_url: str | None,
        enable_html_summary: bool,
        summary_json_path: Path,
        on_log: Callable[[str], None],
        on_status: Callable[[str], None],
        on_output_line: Callable[[str, str, bool], bool],
        on_run_complete: Callable[[], None],
    ) -> None:
        process = await self.process_manager.start_run(
            connection_management=connection_management,
            enable_web_dashboard=enable_web_dashboard,
            web_dashboard_url=web_dashboard_url,
            summary_json_path=str(summary_json_path),
            enable_html_summary=enable_html_summary,
        )

        run_result_reported = False

        async def read_stream(stream, color: str) -> None:
            nonlocal run_result_reported
            pending = ""
            pending_progress_flag = False
            while True:
                chunk = await stream.read(1024)
                if not chunk:
                    break

                pending += chunk.decode("utf-8", errors="replace")
                lines, pending, pending_progress_flag = _split_stream_buffer(pending, pending_progress_flag)

                for line, has_carriage_return in lines:
                    clean_text = clean_cursor_sequences(line).rstrip()
                    if not clean_text.strip():
                        continue

                    hide_line = on_output_line(clean_text, color, has_carriage_return)

                    if is_run_complete_line(clean_text) and not run_result_reported:
                        run_result_reported = True
                        on_run_complete()

                    if not hide_line and not has_carriage_return:
                        on_log(f"[{color}]{clean_text}[/{color}]")

            if pending.strip():
                clean_text = clean_cursor_sequences(pending).rstrip()
                hide_line = on_output_line(clean_text, color, pending_progress_flag)
                if is_run_complete_line(clean_text) and not run_result_reported:
                    run_result_reported = True
                    on_run_complete()
                if not hide_line and not pending_progress_flag:
                    on_log(f"[{color}]{clean_text}[/{color}]")

        await asyncio.gather(
            read_stream(process.stdout, "white"),
            read_stream(process.stderr, "pale_turquoise4"),
        )
        await process.wait()

        if not run_result_reported:
            on_run_complete()

    async def stop(self) -> bool:
        return await self.process_manager.stop()

    async def scale(self, vus: int) -> tuple[int, bytes, bytes]:
        return await self.process_manager.scale(vus)

    def clear(self) -> None:
        self.process_manager.clear_process()
