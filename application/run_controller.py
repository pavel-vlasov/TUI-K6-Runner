import asyncio
from collections.abc import Callable
from dataclasses import dataclass

from config_handler import ConfigHandler
from k6.service import K6Service


@dataclass
class RunCallbacks:
    on_log: Callable[[str], None]
    on_status: Callable[[str], None]
    on_run_state_changed: Callable[[bool], None]
    on_metrics: Callable[[str], None] | None = None


class RunController:
    def __init__(self, k6_service: K6Service, config_path: str = "test_config.json") -> None:
        self.k6_service = k6_service
        self.config_path = config_path

    @property
    def is_running(self) -> bool:
        return self.k6_service.is_running

    def save_config(self, config: dict) -> None:
        ConfigHandler.save_to_file(config, filename=self.config_path)

    async def start_run(self, config: dict, callbacks: RunCallbacks):
        if self.is_running:
            callbacks.on_status("[bold red]⛔ k6 уже выполняется. Дождитесь завершения текущего запуска.[/bold red]")
            callbacks.on_log("[bold red]⛔ Повторный запуск заблокирован: тест уже идёт.[/bold red]\n")
            return

        callbacks.on_run_state_changed(True)
        output_ui = config.get("k6", {}).get("logging", {}).get("outputToUI", True)
        task = asyncio.create_task(
            self.k6_service.run_k6_process(
                on_log=callbacks.on_log,
                on_status=callbacks.on_status,
                output_to_ui=output_ui,
                on_metrics=callbacks.on_metrics
            )
        )
        task.add_done_callback(lambda _: callbacks.on_run_state_changed(False))
        return task

    async def stop_run(self):
        await self.k6_service.stop_k6_process()

    async def scale(self, vus: int, on_log: Callable[[str], None]):
        return await self.k6_service.set_vus(vus, on_log)
