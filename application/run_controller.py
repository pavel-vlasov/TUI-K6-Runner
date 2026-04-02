import asyncio
from collections.abc import Callable
from dataclasses import dataclass

from config_handler import ConfigHandler
from constants import DEFAULT_CONFIG_PATH
from k6.backends import ExecutionCapabilities
from k6.service import K6Service


@dataclass
class RunCallbacks:
    on_log: Callable[[str], None]
    on_status: Callable[[str], None]
    on_run_state_changed: Callable[[bool], None]
    on_capabilities_changed: Callable[[ExecutionCapabilities], None] | None = None


class RunController:
    def __init__(self, k6_service: K6Service, config_path: str = DEFAULT_CONFIG_PATH) -> None:
        self.k6_service = k6_service
        self.config_path = config_path
        self.execution_capabilities = self.k6_service.get_execution_capabilities()

    @property
    def is_running(self) -> bool:
        return self.k6_service.is_running

    def save_config(self, config: dict) -> None:
        ConfigHandler.save_to_file(config, filename=self.config_path)

    def resolve_capabilities(self, config: dict | None = None) -> ExecutionCapabilities:
        capabilities = self.k6_service.resolve_capabilities(config)
        self.execution_capabilities = capabilities
        return capabilities

    async def start_run(self, config: dict, callbacks: RunCallbacks):
        if self.is_running:
            callbacks.on_status("[bold red]⛔ k6 is already running. Wait for the current run to finish.[/bold red]")
            callbacks.on_log("[bold red]⛔ Re-run blocked: test is already in progress.[/bold red]\n")
            return

        self._notify_capabilities_changed(callbacks, self.resolve_capabilities(config))
        self._notify_run_state_changed(callbacks, True)
        run_task_coro = None
        try:
            output_ui = config.get("k6", {}).get("logging", {}).get("outputToUI", True)
            connection_management = config.get("k6", {}).get("connectionManagement", "keep-alive")
            web_dashboard = config.get("k6", {}).get("logging", {}).get("webDashboard", False)
            html_summary_report = config.get("k6", {}).get("logging", {}).get("htmlSummaryReport", False)
            web_dashboard_url = config.get("k6", {}).get("logging", {}).get("webDashboardUrl", "")

            run_task_coro = self.k6_service.run_k6_process(
                on_log=callbacks.on_log,
                on_status=callbacks.on_status,
                output_to_ui=output_ui,
                connection_management=connection_management,
                enable_web_dashboard=web_dashboard,
                web_dashboard_url=web_dashboard_url,
                enable_html_summary=html_summary_report,
            )
            task = asyncio.create_task(run_task_coro)
            task.add_done_callback(lambda _: self._notify_run_state_changed(callbacks, False))
            return task
        except Exception:
            if run_task_coro is not None:
                run_task_coro.close()
            self._notify_run_state_changed(callbacks, False)
            raise

    async def stop_run(self):
        return await self.k6_service.stop_k6_process()

    async def scale(self, vus: int, on_log: Callable[[str], None]):
        return await self.k6_service.set_vus(vus, on_log)

    def _notify_run_state_changed(self, callbacks: RunCallbacks, running: bool) -> None:
        try:
            callbacks.on_run_state_changed(running)
        except Exception:
            # UI can already be unmounted during shutdown; state callback is best-effort.
            pass

    def _notify_capabilities_changed(self, callbacks: RunCallbacks, capabilities: ExecutionCapabilities) -> None:
        if callbacks.on_capabilities_changed is None:
            return
        try:
            callbacks.on_capabilities_changed(capabilities)
        except Exception:
            # UI can already be unmounted during shutdown; state callback is best-effort.
            pass
