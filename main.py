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

        for row_id in ["#k6_vus_row", "#k6_maxvus_row", "#k6_duration_row"]:
            row = self.query_one(row_id)
            row.styles.display = "block" if show_external_fields else "none"

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
                        if execution_type != "external executor":
                            execution_type = "external executor"
                        k6_other_data = {
                            k: v for k, v in k6_config.items()
                            if k not in ["logging", "executionType", "vus", "maxVUs", "duration"]
                        }

                        yield ScrollableContainer(
                            Horizontal(
                                Label("execution type:", classes="field-label"),
                                Select(
                                    [("external executor", "external executor")],
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
        self.full_config = ConfigHandler.update_from_ui(self, self.full_config)
        
        try:
            ConfigHandler.save_to_file(self.full_config)
            self.notify("Configuration saved successfully!", severity="information")
        except Exception as e:
            self.notify(f"Error while saving configuration file: {e}", severity="error")


if __name__ == "__main__":
    K6TestApp().run()
