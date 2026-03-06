import pyperclip
from textual.containers import ScrollableContainer
from textual.widgets import Button, Input, RichLog, Select, Static, Switch, TextArea

from application import RunCallbacks
from config_handler import ConfigHandler
from constants import AUTH_MAP


class EventsMixin:
    def on_switch_changed(self, event: Switch.Changed):
        if not event.switch.id:
            return

        if event.switch.id in AUTH_MAP and event.value is True:
            for sw_id in AUTH_MAP:
                if sw_id != event.switch.id:
                    self.query_one(f"#{sw_id}", Switch).value = False

    def on_select_changed(self, event: Select.Changed):
        if event.select.id == "select___k6__executionType":
            self.toggle_execution_type_fields()

    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "add_request_endpoint_btn":
            await self.add_request_endpoint_tab()
            return
        if event.button.id == "remove_request_endpoint_btn":
            self.remove_last_request_endpoint_tab()
            return
        if event.button.id == "add_spike_stage_btn":
            self.add_spike_stage()
            return
        if event.button.id == "remove_last_spike_stage_btn":
            self.remove_last_spike_stage()
            return
        if event.button.id == "add_arrival_stage_btn":
            self.add_arrival_stage()
            return
        if event.button.id == "remove_last_arrival_stage_btn":
            self.remove_last_arrival_stage()
            return

        log_view = self.query_one("#output_log", RichLog)
        status_bar = self.query_one("#status_bar", Static)
        metrics_view = self.query_one("#metrics_view", Static)

        if event.button.id == "run_btn":
            if self.run_controller.is_running:
                self.notify("⛔ Тест уже выполняется. Дождитесь завершения.", severity="warning")
                return

            self.action_save_config()
            log_view.clear()
            self.notify("Running K6 execution...")

            callbacks = RunCallbacks(
                on_log=log_view.write,
                on_status=status_bar.update,
                on_run_state_changed=self.set_run_ui_state,
                on_metrics=metrics_view.update,
            )

            if not self.full_config.get("k6", {}).get("logging", {}).get("metricsEnabled", False):
                metrics_view.update(
                    "Metrics are disabled.\nEnable k6.logging.metricsEnabled in Settings → Logging."
                )
            else:
                metrics_view.update("[bold yellow]Collecting metrics...[/bold yellow]")

            await self.run_controller.start_run(self.full_config, callbacks)
        elif event.button.id == "stop_btn":
            await self.run_controller.stop_run()
            self.notify("Stop command sent", severity="warning")
        elif event.button.id == "copy_btn":
            pyperclip.copy("\n".join([str(line.text) for line in log_view.lines]))
            self.notify("Logs is copied")
        elif event.button.id == "apply_vu_btn":
            vu_input = self.query_one("#vu_input", Input)
            if vu_input.value.isdigit():
                await self.run_controller.scale(int(vu_input.value), log_view.write)
                vu_input.value = ""

    def _collect_ui_field_values(self) -> dict[str, object]:
        field_values: dict[str, object] = {}
        for widget in self.query("Input, Switch, Select, TextArea"):
            if not widget.id or "___" not in widget.id:
                continue
            if isinstance(widget, TextArea):
                field_values[widget.id] = widget.text
            else:
                field_values[widget.id] = widget.value
        return field_values

    def action_save_config(self):
        spike_rows_count = len(self.query_one("#spike_stages_container", ScrollableContainer).children)
        self.full_config.setdefault("k6", {})["spikeStages"] = [{} for _ in range(spike_rows_count)]

        arrival_rows_count = len(self.query_one("#arrival_stages_container", ScrollableContainer).children)
        self.full_config.setdefault("k6", {})["rampingArrivalStages"] = [{} for _ in range(arrival_rows_count)]

        request_tabs_count = len(self._get_request_tab_panes())
        self.full_config["requestEndpoints"] = [{} for _ in range(request_tabs_count)]

        self.full_config = ConfigHandler.update_from_fields(self.full_config, self._collect_ui_field_values())
        if self.full_config.get("requestEndpoints"):
            self.full_config["request"] = self.full_config["requestEndpoints"][0]

        try:
            self.run_controller.save_config(self.full_config)
            self.notify("Configuration saved successfully!", severity="information")
        except Exception as e:
            self.notify(f"Error while saving configuration file: {e}", severity="error")
