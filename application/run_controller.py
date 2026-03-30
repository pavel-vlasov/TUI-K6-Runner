import asyncio
from collections.abc import Callable
from dataclasses import dataclass

from config_handler import ConfigHandler
from k6.service import K6Service
from k6.state import ExecutionCapabilities


@dataclass
class RunCallbacks:
    on_log: Callable[[str], None]
    on_status: Callable[[str], None]
    on_run_state_changed: Callable[[bool, ExecutionCapabilities], None]


class RunController:
    def __init__(self, k6_service: K6Service, config_path: str = "test_config.json") -> None:
        self.k6_service = k6_service
        self.config_path = config_path
        self.current_capabilities = self.k6_service.embedded_capabilities()

    @property
    def is_running(self) -> bool:
        return self.k6_service.is_running

    def save_config(self, config: dict) -> None:
        ConfigHandler.save_to_file(config, filename=self.config_path)

    def resolve_capabilities(self, config: dict) -> ExecutionCapabilities:
        output_ui = config.get("k6", {}).get("logging", {}).get("outputToUI", True)
        self.current_capabilities = self.k6_service.resolve_capabilities(bool(output_ui))
        return self.current_capabilities

    async def start_run(self, config: dict, callbacks: RunCallbacks):
        if self.is_running:
            callbacks.on_status("[bold red]⛔ k6 is already running. Wait for the current run to finish.[/bold red]")
            callbacks.on_log("[bold red]⛔ Re-run blocked: test is already in progress.[/bold red]\n")
            return

        capabilities = self.resolve_capabilities(config)
        self._notify_run_state_changed(callbacks, True, capabilities)
        run_task_coro = None
        try:
            output_ui = config.get("k6", {}).get("logging", {}).get("outputToUI", True)
            web_dashboard = config.get("k6", {}).get("logging", {}).get("webDashboard", False)
            html_summary_report = config.get("k6", {}).get("logging", {}).get("htmlSummaryReport", False)
            web_dashboard_url = config.get("k6", {}).get("logging", {}).get("webDashboardUrl", "")

            run_task_coro = self.k6_service.run_k6_process(
                on_log=callbacks.on_log,
                on_status=callbacks.on_status,
                output_to_ui=output_ui,
                enable_web_dashboard=web_dashboard,
                web_dashboard_url=web_dashboard_url,
                enable_html_summary=html_summary_report,
            )
            task = asyncio.create_task(run_task_coro)
            task.add_done_callback(
                lambda _: self._notify_run_state_changed(callbacks, False, self.current_capabilities)
            )
            return task
        except Exception:
            if run_task_coro is not None:
                run_task_coro.close()
            self._notify_run_state_changed(callbacks, False, self.current_capabilities)
            raise

    async def stop_run(self):
        await self.k6_service.stop_k6_process()

    async def scale(self, vus: int, on_log: Callable[[str], None]):
        return await self.k6_service.set_vus(vus, on_log)

    def _notify_run_state_changed(
        self, callbacks: RunCallbacks, running: bool, capabilities: ExecutionCapabilities
    ) -> None:
        try:
            callbacks.on_run_state_changed(running, capabilities)
        except Exception:
            # UI can already be unmounted during shutdown; state callback is best-effort.
            pass
