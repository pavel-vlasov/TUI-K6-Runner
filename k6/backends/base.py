from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from collections.abc import Callable

from k6.backends.capabilities import ExecutionCapabilities


class ExecutionBackend(ABC):
    @property
    @abstractmethod
    def capabilities(self) -> ExecutionCapabilities:
        raise NotImplementedError

    @abstractmethod
    async def start_run(
        self,
        *,
        connection_management: str,
        enable_web_dashboard: bool,
        web_dashboard_url: str | None,
        enable_html_summary: bool,
        summary_mode: str,
        summary_json_path: Path,
        on_log: Callable[[str], None],
        on_status: Callable[[str], None],
        on_output_line: Callable[[str, str], bool],
        on_run_complete: Callable[[], None],
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def stop(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def scale(self, vus: int) -> tuple[int, bytes, bytes]:
        raise NotImplementedError

    def clear(self) -> None:
        return None
