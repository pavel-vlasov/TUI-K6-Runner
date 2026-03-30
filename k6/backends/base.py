from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class BackendCapabilities:
    supports_stop: bool
    supports_scale: bool
    supports_status: bool


class ExecutionBackend(ABC):
    @property
    @abstractmethod
    def capabilities(self) -> BackendCapabilities:
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    async def stop(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def scale(self, vus: int) -> tuple[int, bytes, bytes]:
        raise NotImplementedError

    @abstractmethod
    async def status(self) -> tuple[int, bytes, bytes]:
        raise NotImplementedError

    def clear(self) -> None:
        return None
