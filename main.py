import os
import sys
import subprocess
import importlib.util
import json
import asyncio


def install_package(package: str):
    print(f"Installing {package}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", package])


try:
    import textual
    import pyperclip
except ImportError:
    install_package("textual")
    install_package("pyperclip")
    os.execl(sys.executable, sys.executable, *sys.argv)


import pyperclip
from textual.app import App, ComposeResult
from textual.widgets import Button, Switch, Input, Label, Footer, Header, RichLog, Select, TabbedContent, TabPane, Static
from textual.containers import Horizontal, Vertical, ScrollableContainer

from k6_logic import K6Logic
from config_handler import ConfigHandler
from constants import DEFAULT_CONFIG, AUTH_MAP
from ui_components import build_config_fields, get_valid_id


def get_resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


class K6TestApp(App):
    TITLE = "K6 Executor"
    CSS_PATH = get_resource_path("style.tcss")

    def __init__(self):
        super().__init__()
        self.k6_logic = K6Logic()
        self.full_config = {}
        self.load_config_safely()

    def load_config_safely(self):
        try:
            if os.path.exists("test_config.json"):
                with open("test_config.json", "r", encoding="utf-8") as f:
                    self.full_config = json.load(f)
            else:
                self.full_config = DEFAULT_CONFIG.copy()
        except Exception:
            self.full_config = DEFAULT_CONFIG.copy()

    def get_spike_stages(self):
        stages = self.full_config.get("k6", {}).get("spikeStages", [])
        if not isinstance(stages, list) or not stages:
            return [{"duration": "30s", "target": 10}]
        normalized = []
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            normalized.append({
                "duration": stage.get("duration", ""),
                "target": stage.get("target", ""),
            })
        return normalized or [{"duration": "30s", "target": 10}]

    def get_ramping_arrival_stages(self):
        stages = self.full_config.get("k6", {}).get("rampingArrivalStages", [])
        if not isinstance(stages, list) or not stages:
            return [{"duration": "30s", "target": 10}]
        normalized = []
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            normalized.append({
                "duration": stage.get("duration", ""),
                "target": stage.get("target", ""),
            })
        return normalized or [{"duration": "30s", "target": 10}]

    def build_spike_stage_row(self, index: int, stage: dict) -> Horizontal:
        return Horizontal(
            Label(f"stage {index + 1}:", classes="field-label"),
            Input(str(stage.get("duration", "")), id=f"input___k6__spikeStages__{index}__duration", placeholder="duration (e.g. 30s)"),
            Input(str(stage.get("target", "")), id=f"input___k6__spikeStages__{index}__target", placeholder="target VUs"),
            classes="field-row spike-stage-row",
            id=f"spike_stage_row_{index}"
        )

    def build_arrival_stage_row(self, index: int, stage: dict) -> Horizontal:
        return Horizontal(
            Label(f"stage {index + 1}:", classes="field-label"),
            Input(str(stage.get("duration", "")), id=f"input___k6__rampingArrivalStages__{index}__duration", placeholder="duration (e.g. 30s)"),
            Input(str(stage.get("target", "")), id=f"input___k6__rampingArrivalStages__{index}__target", placeholder="target rate"),
            classes="field-row spike-stage-row",
            id=f"arrival_stage_row_{index}"
        )

    def _read_spike_stages_from_ui(self):
        container = self.query_one("#spike_stages_container", ScrollableContainer)
        stages = []
        for index, _ in enumerate(container.children):
            duration_input = self.query_one(f"#input___k6__spikeStages__{index}__duration", Input)
            target_input = self.query_one(f"#input___k6__spikeStages__{index}__target", Input)
            stages.append({"duration": duration_input.value, "target": target_input.value})
        return stages

    def _remount_spike_rows(self, stages):
        container = self.query_one("#spike_stages_container", ScrollableContainer)
        for child in list(container.children):
            child.remove()

        if not stages:
            stages = [{"duration": "", "target": ""}]

        for index, stage in enumerate(stages):
            container.mount(self.build_spike_stage_row(index, stage))

    def _read_arrival_stages_from_ui(self):
        container = self.query_one("#arrival_stages_container", ScrollableContainer)
        stages = []
        for index, _ in enumerate(container.children):
            duration_input = self.query_one(f"#input___k6__rampingArrivalStages__{index}__duration", Input)
            target_input = self.query_one(f"#input___k6__rampingArrivalStages__{index}__target", Input)
            stages.append({"duration": duration_input.value, "target": target_input.value})
        return stages

    def _remount_arrival_rows(self, stages):
        container = self.query_one("#arrival_stages_container", ScrollableContainer)
        for child in list(container.children):
            child.remove()

        if not stages:
            stages = [{"duration": "", "target": ""}]

        for index, stage in enumerate(stages):
            container.mount(self.build_arrival_stage_row(index, stage))

    def add_spike_stage(self):
        container = self.query_one("#spike_stages_container", ScrollableContainer)
        stage_idx = len(container.children)
        row = self.build_spike_stage_row(stage_idx, {"duration": "", "target": ""})
        container.mount(row)

    def remove_last_spike_stage(self):
        container = self.query_one("#spike_stages_container", ScrollableContainer)
        if len(container.children) <= 1:
            return
        last_row = list(container.children)[-1]
        last_row.remove()

    def add_arrival_stage(self):
        container = self.query_one("#arrival_stages_container", Vertical)
        stage_idx = len(container.children)
        row = self.build_arrival_stage_row(stage_idx, {"duration": "", "target": ""})
        container.mount(row)

    def remove_last_arrival_stage(self):
        container = self.query_one("#arrival_stages_container", Vertical)
        if len(container.children) <= 1:
            return
        last_row = list(container.children)[-1]
        last_row.remove()

    def set_run_ui_state(self, running: bool) -> None:
        """Disable/enable controls while k6 is running."""
        run_btn = self.query_one("#run_btn", Button)
        stop_btn = self.query_one("#stop_btn", Button)
        apply_btn = self.query_one("#apply_vu_btn", Button)

        run_btn.disabled = running
        stop_btn.disabled = not running
        apply_btn.disabled = not running

    def on_mount(self) -> None:
        # initial state: nothing running
        self.set_run_ui_state(False)
        self.toggle_execution_type_fields()

    def toggle_execution_type_fields(self) -> None:
        execution_select = self.query_one("#select___k6__executionType", Select)
        show_external_fields = execution_select.value == "external executor"
        show_spike_fields = execution_select.value == "Spike Tests"
        show_constant_vus_fields = execution_select.value == "Constant VUs"
        show_constant_arrival_fields = execution_select.value == "Constant Arrival Rate"
        show_ramping_arrival_fields = execution_select.value == "Ramping Arrival Rate"

        vus_row = self.query_one("#k6_vus_row")
        vus_row.styles.display = "block" if (show_external_fields or show_constant_vus_fields) else "none"

        max_vus_row = self.query_one("#k6_maxvus_row")
        max_vus_row.styles.display = "block" if (show_external_fields or show_constant_arrival_fields or show_ramping_arrival_fields) else "none"

        duration_row = self.query_one("#k6_duration_row")
        duration_row.styles.display = "block" if (show_external_fields or show_constant_vus_fields or show_constant_arrival_fields) else "none"

        ramping_arrival_scroll_group = self.query_one("#ramping_arrival_scroll_group", ScrollableContainer)
        ramping_arrival_scroll_group.styles.display = "block" if (show_constant_arrival_fields or show_ramping_arrival_fields) else "none"

        for row_id in ["#k6_rate_row", "#k6_timeunit_row", "#k6_preallocated_row"]:
            row = self.query_one(row_id)
            row.styles.display = "block" if (show_constant_arrival_fields or show_ramping_arrival_fields) else "none"

        start_rate_row = self.query_one("#k6_start_rate_row")
        start_rate_row.styles.display = "block" if show_ramping_arrival_fields else "none"

        spike_group = self.query_one("#spike_stages_group", Vertical)
        spike_group.styles.display = "block" if show_spike_fields else "none"

        arrival_group = self.query_one("#arrival_stages_group", Vertical)
        arrival_group.styles.display = "block" if show_ramping_arrival_fields else "none"

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="main_tabs"):
            # --- Settings tab ---
            with TabPane("Settings", id="tab_settings"):
                with TabbedContent(id="settings_subtabs"):

                    # 1. Auth tab
                    with TabPane("Auth", id="tab_auth"):
                        auth_data = self.full_config.get("auth", {})
                        switches_list = []
                        inputs_list = []
                        for k, v in auth_data.items():
                            full_key = f"auth.{k}"
                            if isinstance(v, bool):
                                switches_list.append(Horizontal(
                                    Label(k),
                                    Switch(v, id=get_valid_id(full_key, "bool")),
                                    classes="switch-group"
                                ))
                            else:
                                inputs_list.append(Horizontal(
                                    Label(f"{k}:", classes="field-label"),
                                    Input(str(v), id=get_valid_id(full_key, "input")),
                                    classes="field-row"
                                ))
                        yield ScrollableContainer(
                            Horizontal(*switches_list, classes="field-row"),
                            *inputs_list,
                            classes="tab-container"
                        )

                    # 2. Request tab
                    with TabPane("Request", id="tab_req"):
                        yield ScrollableContainer(
                            Horizontal(
                                Label("baseURL:", classes="field-label"),
                                Input(self.full_config.get("baseURL", ""), id="input_baseURL"),
                                classes="field-row"
                            ),

                            *build_config_fields(self.full_config.get("request", {}), "request"),
                            classes="tab-container"
                        )

                    # 3. K6 tab
                    with TabPane("K6", id="tab_k6"):
                        k6_config = self.full_config.get("k6", {})
                        execution_type = k6_config.get("executionType", "external executor")
                        if execution_type not in ["external executor", "Spike Tests", "Constant VUs", "Constant Arrival Rate", "Ramping Arrival Rate"]:
                            execution_type = "external executor"
                        k6_other_data = {
                            k: v for k, v in k6_config.items()
                            if k not in ["logging", "executionType", "vus", "maxVUs", "duration", "spikeStages", "rate", "timeUnit", "preAllocatedVUs", "startRate", "rampingArrivalStages"]
                        }

                        yield ScrollableContainer(
                            Horizontal(
                                Label("execution type:", classes="field-label"),
                                Select(
                                    [
                                        ("external executor", "external executor"),
                                        ("Spike Tests", "Spike Tests"),
                                        ("Constant VUs", "Constant VUs"),
                                        ("Constant Arrival Rate", "Constant Arrival Rate"),
                                        ("Ramping Arrival Rate", "Ramping Arrival Rate"),
                                    ],
                                    value=execution_type,
                                    id="select___k6__executionType"
                                ),
                                classes="field-row"
                            ),
                            Horizontal(
                                Label("vus:", classes="field-label"),
                                Input(str(k6_config.get("vus", "")), id="input___k6__vus"),
                                classes="field-row",
                                id="k6_vus_row"
                            ),
                            Horizontal(
                                Label("maxVUs:", classes="field-label"),
                                Input(str(k6_config.get("maxVUs", "")), id="input___k6__maxVUs"),
                                classes="field-row",
                                id="k6_maxvus_row"
                            ),
                            Horizontal(
                                Label("duration:", classes="field-label"),
                                Input(str(k6_config.get("duration", "")), id="input___k6__duration"),
                                classes="field-row",
                                id="k6_duration_row"
                            ),
                            ScrollableContainer(
                                Horizontal(
                                    Label("rate:", classes="field-label"),
                                    Input(str(k6_config.get("rate", "")), id="input___k6__rate"),
                                    classes="field-row",
                                    id="k6_rate_row"
                                ),
                                Horizontal(
                                    Label("timeUnit:", classes="field-label"),
                                    Input(str(k6_config.get("timeUnit", "")), id="input___k6__timeUnit"),
                                    classes="field-row",
                                    id="k6_timeunit_row"
                                ),
                                Horizontal(
                                    Label("preAllocatedVUs:", classes="field-label"),
                                    Input(str(k6_config.get("preAllocatedVUs", "")), id="input___k6__preAllocatedVUs"),
                                    classes="field-row",
                                    id="k6_preallocated_row"
                                ),
                                Horizontal(
                                    Label("startRate:", classes="field-label"),
                                    Input(str(k6_config.get("startRate", "")), id="input___k6__startRate"),
                                    classes="field-row",
                                    id="k6_start_rate_row"
                                ),
                                Vertical(
                                    Vertical(
                                        *[self.build_arrival_stage_row(i, stage) for i, stage in enumerate(self.get_ramping_arrival_stages())],
                                        id="arrival_stages_container"
                                    ),
                                    Horizontal(
                                        Label("", classes="field-label"),
                                        Button("+", id="add_arrival_stage_btn", variant="primary"),
                                        Button("-", id="remove_last_arrival_stage_btn", variant="error"),
                                        classes="field-row"
                                    ),
                                    id="arrival_stages_group"
                                ),
                                id="ramping_arrival_scroll_group"
                            ),
                            Vertical(
                                ScrollableContainer(
                                    *[self.build_spike_stage_row(i, stage) for i, stage in enumerate(self.get_spike_stages())],
                                    id="spike_stages_container"
                                ),
                                Horizontal(
                                    Label("", classes="field-label"),
                                    Button("+", id="add_spike_stage_btn", variant="primary"),
                                    Button("-", id="remove_last_spike_stage_btn", variant="error"),
                                    classes="field-row"
                                ),
                                id="spike_stages_group"
                            ),
                            *build_config_fields(k6_other_data, "k6"),
                            classes="tab-container"
                        )

                    # 4. Logging tab
                    with TabPane("Logging", id="tab_logging"):
                        log_data = self.full_config.get("k6", {}).get("logging", {})
                        yield ScrollableContainer(
                            *build_config_fields(log_data, "k6.logging"),
                            classes="tab-container"
                        )

            # --- Logging tab---
            with TabPane("Logs", id="tab_logs"):
                with Vertical(id="log_view_container"):
                    yield Static("Waiting...\nPrepare to run", id="status_bar")
                    yield RichLog(id="output_log", markup=True, wrap=True)

                with Horizontal(id="button_row"):
                    yield Input(placeholder="VUs...", id="vu_input")
                    yield Button("✅ Apply", id="apply_vu_btn", variant="primary")
                    yield Button("📋 Copy All Logs", id="copy_btn", variant="primary")
                    yield Button("Stop k6", id="stop_btn", variant="error")
                    yield Button("Save & Run k6 Test", id="run_btn", variant="success")

        yield Footer()

    def on_switch_changed(self, event: Switch.Changed):

        if not event.switch.id:
            return

        if event.switch.id in AUTH_MAP and event.value is True:
            for sw_id in AUTH_MAP:
                if sw_id != event.switch.id:
                    other_switch = self.query_one(f"#{sw_id}", Switch)
                    other_switch.value = False

    def on_select_changed(self, event: Select.Changed):
        if event.select.id == "select___k6__executionType":
            self.toggle_execution_type_fields()

    async def on_button_pressed(self, event: Button.Pressed):
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

        if event.button.id == "run_btn":
            # UI-level guard (and K6Logic has its own guard too)
            if self.k6_logic.is_running:
                self.notify("⛔ Тест уже выполняется. Дождитесь завершения.", severity="warning")
                return

            self.action_save_config()
            log_view.clear()
            self.notify("Running K6 execution...")

            output_ui = self.full_config.get("k6", {}).get("logging", {}).get("outputToUI", True)

            # disable controls while running
            self.set_run_ui_state(True)

            task = asyncio.create_task(
                self.k6_logic.run_k6_process(
                    log_view.write,
                    status_bar.update,
                    output_ui
                )
            )

            def _done(_t: asyncio.Task):
                # re-enable controls when finished
                self.set_run_ui_state(False)

            task.add_done_callback(_done)

        elif event.button.id == "stop_btn":
            await self.k6_logic.stop_k6_process()
            self.notify("Stop command sent", severity="warning")

        elif event.button.id == "copy_btn":
            text = "\n".join([str(line.text) for line in log_view.lines])
            pyperclip.copy(text)
            self.notify("Logs is copied")

        elif event.button.id == "apply_vu_btn":
            vu_input = self.query_one("#vu_input", Input)
            if vu_input.value.isdigit():
                await self.k6_logic.set_vus(int(vu_input.value), log_view.write)
                vu_input.value = ""

    def action_save_config(self):
        # Keep spikeStages length in sync with currently visible rows before generic UI-path mapping.
        # Without this reset, removed rows can remain in config because indexed writes only overwrite existing items.
        spike_container = self.query_one("#spike_stages_container", ScrollableContainer)
        spike_rows_count = len(spike_container.children)
        self.full_config.setdefault("k6", {})["spikeStages"] = [{} for _ in range(spike_rows_count)]

        arrival_container = self.query_one("#arrival_stages_container", Vertical)
        arrival_rows_count = len(arrival_container.children)
        self.full_config.setdefault("k6", {})["rampingArrivalStages"] = [{} for _ in range(arrival_rows_count)]

        self.full_config = ConfigHandler.update_from_ui(self, self.full_config)

        try:
            ConfigHandler.save_to_file(self.full_config)
            self.notify("Configuration saved successfully!", severity="information")
        except Exception as e:
            self.notify(f"Error while saving configuration file: {e}", severity="error")


if __name__ == "__main__":
    K6TestApp().run()
