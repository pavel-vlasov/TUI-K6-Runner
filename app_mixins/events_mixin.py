import time
import webbrowser
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import pyperclip
from textual.containers import ScrollableContainer
from textual.widgets import Button, Input, RichLog, Select, Static, Switch, TextArea

from application import RunCallbacks
from config_handler import ConfigHandler


class EventsMixin:
    def on_input_changed(self, event: Input.Changed):
        endpoint_index = self.parse_request_endpoint_name_input_id(event.input.id)
        if endpoint_index is None:
            return
        self.rename_request_endpoint(endpoint_index, event.value)

    def on_switch_changed(self, event: Switch.Changed):
        if not event.switch.id:
            return

        if event.switch.id in {"bool___k6__logging__enabled", "bool___k6__logging__webDashboard"}:
            self.toggle_logging_fields()

    async def on_select_changed(self, event: Select.Changed):
        if event.select.id == "select___k6__executionType":
            self.toggle_execution_type_fields()
        if event.select.id == "select___k6__requestMode":
            await self.rebuild_k6_scenario_tabs()
            self.update_k6_request_mode_ui()
        if event.select.id == "select___auth__mode":
            self.toggle_auth_fields()
        if event.select.id == "select___k6__logging__outputToUI":
            self.refresh_execution_capabilities(self.ui_config)
            self.toggle_logging_fields()

    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "web_dashboard_btn":
            logging_config = self.ui_config.get("k6", {}).get("logging", {})
            web_dashboard_enabled = logging_config.get("webDashboard", False)

            if not web_dashboard_enabled:
                self.notify("🌐 Web Dashboard is disabled in config.", severity="warning")
                return

            if not self.run_controller.is_running:
                self.notify("🌐 Web Dashboard is available only during a running test.", severity="warning")
                return

            web_dashboard_url = logging_config.get("webDashboardUrl", "http://localhost:5665")
            if not ConfigHandler.is_valid_http_url(web_dashboard_url):
                self.notify("❌ Web Dashboard URL is invalid. Please provide a valid http/https URL.", severity="error")
                return
            refreshed_url = self._with_cache_busting_query(web_dashboard_url)
            webbrowser.open(refreshed_url)
            self.notify(f"Opening Web Dashboard: {refreshed_url}")
            return
        if event.button.id == "add_request_endpoint_btn":
            await self.add_request_endpoint_tab()
            return
        if event.button.id == "remove_request_endpoint_btn":
            await self.remove_last_request_endpoint_tab()
            return
        if event.button.id == "add_spike_stage_btn":
            self.add_spike_stage()
            return
        if event.button.id == "remove_last_spike_stage_btn":
            if not self.remove_last_spike_stage():
                self.notify("At least one spike stage must remain.", severity="warning")
            return
        if event.button.id == "add_arrival_stage_btn":
            self.add_arrival_stage()
            return
        if event.button.id == "remove_last_arrival_stage_btn":
            if not self.remove_last_arrival_stage():
                self.notify("At least one arrival stage must remain.", severity="warning")
            return

        log_view = self.query_one("#output_log", RichLog)
        status_bar = self.query_one("#status_bar", Static)

        if event.button.id == "run_btn":
            if self.run_controller.is_running:
                self.notify("⛔ Test is already running. Please wait until it finishes.", severity="warning")
                return

            if not self.action_save_config():
                return

            log_view.clear()
            self.notify("Running K6 execution...")

            callbacks = RunCallbacks(
                on_log=log_view.write,
                on_status=status_bar.update,
                on_run_state_changed=self.set_run_ui_state,
                on_capabilities_changed=lambda capabilities: setattr(self, "execution_capabilities", capabilities),
            )
            await self.run_controller.start_run(self.runtime_config, callbacks)

        elif event.button.id == "stop_btn":
            await self.run_controller.stop_run()
            self.notify("Stop command sent", severity="warning")
        elif event.button.id == "copy_btn":
            try:
                pyperclip.copy("\n".join([str(line.text) for line in log_view.lines]))
                self.notify("Logs copied")
            except Exception:
                self.notify(
                    "Unable to copy logs to clipboard. Please install/configure a clipboard backend for pyperclip.",
                    severity="warning",
                )
        elif event.button.id == "apply_vu_btn":
            vu_input = self.query_one("#vu_input", Input)
            vu_raw_value = vu_input.value.strip()
            if not vu_raw_value.isdigit():
                self.notify("Please enter a valid VU value (positive integer).", severity="warning")
                return

            vu_value = int(vu_raw_value)
            if vu_value < 1:
                self.notify("VU value must be at least 1.", severity="error")
                return

            await self.run_controller.scale(vu_value, log_view.write)
            self.notify(f"Scaled to {vu_value} VU(s).", severity="information")
            vu_input.value = ""

    def _with_cache_busting_query(self, url: str) -> str:
        parsed = urlparse(url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query["run"] = str(int(time.time() * 1000))
        new_query = urlencode(query)
        return urlunparse(parsed._replace(query=new_query))

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

    def action_save_config(self) -> bool:
        spike_rows_count = len(self.query_one("#spike_stages_container", ScrollableContainer).children)
        self.ui_config.setdefault("k6", {})["spikeStages"] = [{} for _ in range(spike_rows_count)]

        arrival_rows_count = len(self.query_one("#arrival_stages_container", ScrollableContainer).children)
        self.ui_config.setdefault("k6", {})["rampingArrivalStages"] = [{} for _ in range(arrival_rows_count)]

        request_tabs_count = len(self._get_request_tab_panes())
        self.ui_config["requestEndpoints"] = [{} for _ in range(request_tabs_count)]

        self.ui_config = ConfigHandler.update_from_fields(self.ui_config, self._collect_ui_field_values())

        runtime_config = ConfigHandler.build_runtime_config(self.ui_config)
        errors = ConfigHandler.validate_runtime_config(runtime_config)
        if errors:
            self.notify("Configuration validation failed:", severity="error")
            for error in errors:
                self.notify(f"• {error}", severity="error")
            return False

        self.runtime_config = runtime_config

        try:
            self.run_controller.save_config(self.runtime_config)
            self.notify("Configuration saved successfully!", severity="information")
            return True
        except Exception as e:
            self.notify(f"Error while saving configuration file: {e}", severity="error")
            return False
