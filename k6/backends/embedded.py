from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable

from k6.backends.base import BackendCapabilities, ExecutionBackend
from k6.output_parser import clean_cursor_sequences, is_run_complete_line
from k6.process_manager import K6ProcessManager


class EmbeddedProcessBackend(ExecutionBackend):
    def __init__(self, process_manager: K6ProcessManager | None = None) -> None:
        self.process_manager = process_manager or K6ProcessManager()

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(supports_stop=True, supports_scale=True, supports_status=True)

    async def start_run(
        self,
        *,
        enable_web_dashboard: bool,
        web_dashboard_url: str | None,
        enable_html_summary: bool,
        summary_json_path: Path,
        on_log: Callable[[str], None],
        on_status: Callable[[str], None],
        on_output_line: Callable[[str, str], bool],
        on_run_complete: Callable[[], None],
    ) -> None:
        process = await self.process_manager.start_run(
            enable_web_dashboard=enable_web_dashboard,
            web_dashboard_url=web_dashboard_url,
            summary_json_path=str(summary_json_path),
            enable_html_summary=enable_html_summary,
        )

        run_result_reported = False

        async def read_stream(stream, color: str) -> None:
            nonlocal run_result_reported
            while True:
                line = await stream.readline()
                if not line:
                    break

                text = line.decode("utf-8", errors="replace").rstrip()
                clean_text = clean_cursor_sequences(text)
                if not clean_text.strip():
                    continue

                hide_line = on_output_line(clean_text, color)

                if is_run_complete_line(clean_text) and not run_result_reported:
                    run_result_reported = True
                    on_run_complete()

                if not hide_line:
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

    async def status(self) -> tuple[int, bytes, bytes]:
        return await self.process_manager.status()

    def clear(self) -> None:
        self.process_manager.clear_process()
