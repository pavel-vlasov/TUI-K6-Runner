from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Select,
    Static,
    Switch,
    TabbedContent,
    TabPane,
)

from ui_components import build_config_fields


class UIMixin:
    def set_run_ui_state(self, running: bool) -> None:
        run_btn = self.query_one("#run_btn", Button)
        stop_btn = self.query_one("#stop_btn", Button)
        apply_btn = self.query_one("#apply_vu_btn", Button)
        web_dashboard_btn = self.query_one("#web_dashboard_btn", Button)
        web_dashboard_enabled = self.full_config.get("k6", {}).get("logging", {}).get("webDashboard", False)

        run_btn.disabled = running
        stop_btn.disabled = not running
        apply_btn.disabled = not running
        web_dashboard_btn.display = True
        web_dashboard_btn.disabled = (not running) or (not web_dashboard_enabled)

    async def on_mount(self) -> None:
        self.set_run_ui_state(False)
        self.toggle_execution_type_fields()
        self.toggle_auth_fields()
        self.toggle_logging_fields()
        if getattr(self, "config_load_error", None):
            message = self.config_load_error
            details = getattr(self, "config_load_error_details", None)
            if details:
                message = f"{message} {details} Using default config and leaving the source file untouched."
            self.notify(message, severity="warning")

        request_subtabs = self.query_one("#request_subtabs", TabbedContent)
        if self._get_request_tab_panes():
            return

        request_endpoints = self.get_request_endpoints()
        for index, request_data in enumerate(request_endpoints):
            await request_subtabs.add_pane(self.build_request_subtab(index, request_data))

    def toggle_execution_type_fields(self) -> None:
        execution_select = self.query_one("#select___k6__executionType", Select)

        show_external_fields = execution_select.value == "external executor"
        show_spike_fields = execution_select.value == "Spike Tests"
        show_constant_vus_fields = execution_select.value == "Constant VUs"
        show_constant_arrival_fields = execution_select.value == "Constant Arrival Rate"
        show_ramping_arrival_fields = execution_select.value == "Ramping Arrival Rate"

        self.query_one("#k6_vus_row").styles.display = (
            "block" if (show_external_fields or show_constant_vus_fields) else "none"
        )
        self.query_one("#k6_maxvus_row").styles.display = (
            "block"
            if (show_external_fields or show_constant_arrival_fields or show_ramping_arrival_fields)
            else "none"
        )
        self.query_one("#k6_duration_row").styles.display = (
            "block" if (show_external_fields or show_constant_vus_fields or show_constant_arrival_fields) else "none"
        )

        ramping_arrival_scroll_group = self.query_one("#ramping_arrival_scroll_group", Vertical)
        ramping_arrival_scroll_group.styles.display = (
            "block" if (show_constant_arrival_fields or show_ramping_arrival_fields) else "none"
        )

        for row_id in ["#k6_rate_row", "#k6_timeunit_row", "#k6_preallocated_row"]:
            self.query_one(row_id).styles.display = (
                "block" if (show_constant_arrival_fields or show_ramping_arrival_fields) else "none"
            )

        self.query_one("#k6_start_rate_row").styles.display = "block" if show_ramping_arrival_fields else "none"
        self.query_one("#spike_stages_group", Vertical).styles.display = "block" if show_spike_fields else "none"
        self.query_one("#arrival_stages_group", Vertical).styles.display = (
            "block" if show_ramping_arrival_fields else "none"
        )

    def toggle_auth_fields(self) -> None:
        auth_mode_select = self.query_one("#select___auth__mode", Select)
        selected_mode = str(auth_mode_select.value or "none")
        oauth_enabled = selected_mode == "oauth2_client_credentials"
        no_auth_enabled = selected_mode == "none"

        for row_id in ["#auth_row__client_id", "#auth_row__client_secret"]:
            self.query_one(row_id, Horizontal).styles.display = "none" if no_auth_enabled else "block"

        for row_id in ["#auth_oauth_row__token_url", "#auth_oauth_row__scope"]:
            self.query_one(row_id, Horizontal).styles.display = "block" if oauth_enabled else "none"

    def _normalize_logging_level(self, raw_value: object) -> str:
        allowed_levels = {"all", "failed", "Failures - without payloads"}
        if raw_value in allowed_levels:
            return str(raw_value)
        return "failed"

    def toggle_logging_fields(self) -> None:
        logging_enabled_switch = self.query_one("#bool___k6__logging__enabled", Switch)
        web_dashboard_switch = self.query_one("#bool___k6__logging__webDashboard", Switch)

        level_display = "block" if bool(logging_enabled_switch.value) else "none"
        web_dashboard_url_display = "block" if bool(web_dashboard_switch.value) else "none"

        self.query_one("#logging_level_label", Label).styles.display = level_display
        self.query_one("#select___k6__logging__level", Select).styles.display = level_display
        self.query_one("#logging_web_dashboard_url_label", Label).styles.display = web_dashboard_url_display
        self.query_one("#input___k6__logging__webDashboardUrl", Input).styles.display = web_dashboard_url_display

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="main_tabs"):
            with TabPane("Settings", id="tab_settings"):
                with TabbedContent(id="settings_subtabs"):
                    with TabPane("Auth", id="tab_auth"):
                        auth_data = self.full_config.get("auth", {})
                        auth_mode = str(auth_data.get("mode", "")).strip()
                        if auth_mode not in [
                            "none",
                            "oauth2_client_credentials",
                            "basic",
                            "client_id_enforcement",
                        ]:
                            auth_mode = "none"

                        yield ScrollableContainer(
                            Horizontal(
                                Label("mode:", classes="field-label"),
                                Select(
                                    [
                                        ("none", "none"),
                                        ("oauth2_client_credentials", "oauth2_client_credentials"),
                                        ("basic", "basic"),
                                        ("client_id_enforcement", "client_id_enforcement"),
                                    ],
                                    value=auth_mode,
                                    id="select___auth__mode",
                                ),
                                classes="field-row",
                            ),
                            Horizontal(
                                Label("client_id:", classes="field-label"),
                                Input(str(auth_data.get("client_id", "")), id="input___auth__client_id"),
                                classes="field-row",
                                id="auth_row__client_id",
                            ),
                            Horizontal(
                                Label("client_secret:", classes="field-label"),
                                Input(str(auth_data.get("client_secret", "")), id="input___auth__client_secret"),
                                classes="field-row",
                                id="auth_row__client_secret",
                            ),
                            Horizontal(
                                Label("token_url:", classes="field-label"),
                                Input(str(auth_data.get("token_url", "")), id="input___auth__token_url"),
                                classes="field-row",
                                id="auth_oauth_row__token_url",
                            ),
                            Horizontal(
                                Label("scope:", classes="field-label"),
                                Input(str(auth_data.get("scope", "")), id="input___auth__scope"),
                                classes="field-row",
                                id="auth_oauth_row__scope",
                            ),
                            classes="tab-container",
                        )

                    with TabPane("Request", id="tab_req"):
                        yield ScrollableContainer(
                            Horizontal(
                                Label("baseURL:", classes="field-label"),
                                Input(self.full_config.get("baseURL", ""), id="input___baseURL"),
                                classes="field-row",
                            ),
                            Horizontal(
                                Label("endpoints:", classes="field-label"),
                                Button("+", id="add_request_endpoint_btn", variant="primary"),
                                Button("-", id="remove_request_endpoint_btn", variant="error"),
                                classes="field-row",
                            ),
                            TabbedContent(id="request_subtabs"),
                            classes="tab-container",
                        )

                    with TabPane("K6", id="tab_k6"):
                        k6_config = self.full_config.get("k6", {})
                        execution_type = k6_config.get("executionType", "external executor")
                        if execution_type not in [
                            "external executor",
                            "Spike Tests",
                            "Constant VUs",
                            "Constant Arrival Rate",
                            "Ramping Arrival Rate",
                        ]:
                            execution_type = "external executor"
                        k6_other_data = {
                            k: v
                            for k, v in k6_config.items()
                            if k
                            not in [
                                "logging",
                                "executionType",
                                "vus",
                                "maxVUs",
                                "duration",
                                "spikeStages",
                                "rate",
                                "timeUnit",
                                "preAllocatedVUs",
                                "startRate",
                                "rampingArrivalStages",
                                "requestMode",
                            ]
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
                                    id="select___k6__executionType",
                                ),
                                classes="field-row",
                            ),
                            Horizontal(
                                Label("vus:", classes="field-label"),
                                Input(str(k6_config.get("vus", "")), id="input___k6__vus"),
                                classes="field-row",
                                id="k6_vus_row",
                            ),
                            Horizontal(
                                Label("maxVUs:", classes="field-label"),
                                Input(str(k6_config.get("maxVUs", "")), id="input___k6__maxVUs"),
                                classes="field-row",
                                id="k6_maxvus_row",
                            ),
                            Horizontal(
                                Label("duration:", classes="field-label"),
                                Input(str(k6_config.get("duration", "")), id="input___k6__duration"),
                                classes="field-row",
                                id="k6_duration_row",
                            ),
                            Vertical(
                                Horizontal(
                                    Label("rate:", classes="field-label"),
                                    Input(str(k6_config.get("rate", "")), id="input___k6__rate"),
                                    classes="field-row",
                                    id="k6_rate_row",
                                ),
                                Horizontal(
                                    Label("timeUnit:", classes="field-label"),
                                    Input(str(k6_config.get("timeUnit", "")), id="input___k6__timeUnit"),
                                    classes="field-row",
                                    id="k6_timeunit_row",
                                ),
                                Horizontal(
                                    Label("preAllocatedVUs:", classes="field-label"),
                                    Input(str(k6_config.get("preAllocatedVUs", "")), id="input___k6__preAllocatedVUs"),
                                    classes="field-row",
                                    id="k6_preallocated_row",
                                ),
                                Horizontal(
                                    Label("startRate:", classes="field-label"),
                                    Input(str(k6_config.get("startRate", "")), id="input___k6__startRate"),
                                    classes="field-row",
                                    id="k6_start_rate_row",
                                ),
                                Vertical(
                                    ScrollableContainer(
                                        *[
                                            self.build_arrival_stage_row(i, stage)
                                            for i, stage in enumerate(self.get_ramping_arrival_stages())
                                        ],
                                        id="arrival_stages_container",
                                    ),
                                    Horizontal(
                                        Label("", classes="field-label"),
                                        Button("+", id="add_arrival_stage_btn", variant="primary"),
                                        Button("-", id="remove_last_arrival_stage_btn", variant="error"),
                                        classes="field-row",
                                    ),
                                    id="arrival_stages_group",
                                ),
                                id="ramping_arrival_scroll_group",
                            ),
                            Vertical(
                                ScrollableContainer(
                                    *[
                                        self.build_spike_stage_row(i, stage)
                                        for i, stage in enumerate(self.get_spike_stages())
                                    ],
                                    id="spike_stages_container",
                                ),
                                Horizontal(
                                    Label("", classes="field-label"),
                                    Button("+", id="add_spike_stage_btn", variant="primary"),
                                    Button("-", id="remove_last_spike_stage_btn", variant="error"),
                                    classes="field-row",
                                ),
                                id="spike_stages_group",
                            ),
                            *build_config_fields(k6_other_data, "k6"),
                            classes="tab-container",
                        )

                    with TabPane("Logging", id="tab_logging"):
                        log_data = self.full_config.setdefault("k6", {}).setdefault("logging", {})
                        log_data.setdefault("htmlSummaryReport", False)

                        other_logging_data = {
                            k: v
                            for k, v in log_data.items()
                            if k not in ["enabled", "level", "webDashboard", "webDashboardUrl"]
                        }

                        yield ScrollableContainer(
                            Horizontal(
                                Label("enabled:", classes="field-label"),
                                Switch(bool(log_data.get("enabled", False)), id="bool___k6__logging__enabled"),
                                Label("level:", classes="field-label", id="logging_level_label"),
                                Select(
                                    [
                                        ("all", "all"),
                                        ("failed", "failed"),
                                        ("Failures - without payloads", "Failures - without payloads"),
                                    ],
                                    value=self._normalize_logging_level(log_data.get("level", "failed")),
                                    id="select___k6__logging__level",
                                ),
                                classes="field-row",
                            ),
                            Horizontal(
                                Label("webDashboard:", classes="field-label"),
                                Switch(bool(log_data.get("webDashboard", False)), id="bool___k6__logging__webDashboard"),
                                Label("webDashboardUrl:", classes="field-label", id="logging_web_dashboard_url_label"),
                                Input(
                                    str(log_data.get("webDashboardUrl", "http://localhost:5665")),
                                    id="input___k6__logging__webDashboardUrl",
                                ),
                                classes="field-row",
                            ),
                            *build_config_fields(other_logging_data, "k6.logging"),
                            classes="tab-container",
                        )

            with TabPane("Logs", id="tab_logs"):
                with Vertical(id="log_view_container"):
                    yield Static("Waiting...\nPrepare to run", id="status_bar")
                    yield RichLog(id="output_log", markup=True, wrap=True)

        with Horizontal(id="button_row"):
            yield Button("🌐 Web Dashboard", id="web_dashboard_btn", variant="primary")
            yield Input(placeholder="VUs...", id="vu_input")
            yield Button("✅ Apply", id="apply_vu_btn", variant="primary")
            yield Button("📋 Copy All Logs", id="copy_btn", variant="primary")
            yield Button("Stop k6", id="stop_btn", variant="error")
            yield Button("Save & Run k6 Test", id="run_btn", variant="success")

        yield Footer()
