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
from copy import deepcopy

from constants import (
    AUTH_MODE_OPTIONS,
    EXECUTION_TYPES,
    EXECUTION_TYPE_OPTIONS,
    AuthMode,
    ExecutionType,
    LOGGING_LEVEL_FAILED,
    LOGGING_LEVEL_OPTIONS,
    normalize_logging_level,
)
from k6.backends import ExecutionCapabilities
from ui_components import build_config_fields


class UIMixin:
    execution_capabilities: ExecutionCapabilities

    def _ensure_execution_capabilities(self) -> ExecutionCapabilities:
        capabilities = getattr(self, "execution_capabilities", None)
        if capabilities is None:
            capabilities = self.run_controller.resolve_capabilities(self.ui_config)
            self.execution_capabilities = capabilities
        return capabilities

    def refresh_execution_capabilities(self, config: dict | None = None) -> ExecutionCapabilities:
        capabilities_source = deepcopy(config or self.ui_config)
        try:
            output_mode_select = self.query_one("#select___k6__logging__outputToUI", Select)
            capabilities_source.setdefault("k6", {}).setdefault("logging", {})["outputToUI"] = bool(
                output_mode_select.value
            )
        except Exception:
            pass

        capabilities = self.run_controller.resolve_capabilities(capabilities_source)
        self.execution_capabilities = capabilities
        return capabilities

    def _capabilities_warning_text(self, capabilities: ExecutionCapabilities) -> str:
        missing = []
        if not capabilities.can_stop:
            missing.append("stop")
        if not capabilities.can_scale:
            missing.append("scale")
        if not capabilities.can_capture_logs:
            missing.append("capture logs")
        if not capabilities.can_read_metrics:
            missing.append("read metrics")

        if not missing:
            return "✅ Selected execution mode supports stop, scaling, logs, and metrics."

        return "⚠️ Selected execution mode has limited features: " + ", ".join(missing) + "."

    def set_run_ui_state(self, running: bool) -> None:
        run_btn = self.query_one("#run_btn", Button)
        stop_btn = self.query_one("#stop_btn", Button)
        apply_btn = self.query_one("#apply_vu_btn", Button)
        web_dashboard_btn = self.query_one("#web_dashboard_btn", Button)
        web_dashboard_enabled = self.ui_config.get("k6", {}).get("logging", {}).get("webDashboard", False)
        capabilities = self._ensure_execution_capabilities()

        run_btn.disabled = running
        stop_btn.disabled = (not running) or (not capabilities.can_stop)
        apply_btn.disabled = (not running) or (not capabilities.can_scale)
        web_dashboard_btn.display = True
        web_dashboard_btn.disabled = (not running) or (not web_dashboard_enabled)

    async def on_mount(self) -> None:
        self.refresh_execution_capabilities(self.ui_config)
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
        await self.rebuild_k6_scenario_tabs()
        self.update_k6_request_mode_ui()

    def _get_k6_scenario_tab_panes(self) -> list[TabPane]:
        try:
            scenario_subtabs = self.query_one("#k6_scenarios_subtabs", TabbedContent)
        except Exception:
            return []
        return list(scenario_subtabs.query(TabPane))

    async def rebuild_k6_scenario_tabs(self) -> None:
        try:
            scenario_subtabs = self.query_one("#k6_scenarios_subtabs", TabbedContent)
        except Exception:
            return
        active_tab_id = scenario_subtabs.active

        removal_ops = []
        for pane in list(scenario_subtabs.query(TabPane)):
            removal_result = scenario_subtabs.remove_pane(pane.id)
            if hasattr(removal_result, "__await__"):
                removal_ops.append(removal_result)

        for removal_op in removal_ops:
            await removal_op

        for index, endpoint in enumerate(self.get_request_endpoints()):
            await scenario_subtabs.add_pane(self.build_k6_scenario_subtab(index, endpoint))

        panes = self._get_k6_scenario_tab_panes()
        if panes:
            scenario_subtabs.active = active_tab_id if any(pane.id == active_tab_id for pane in panes) else self.scenario_tab_id(0)

    def update_k6_request_mode_ui(self) -> None:
        try:
            select = self.query_one("#select___k6__requestMode", Select)
            k6_subtabs = self.query_one("#k6_request_mode_subtabs", TabbedContent)
        except (KeyError, AttributeError, TypeError) as error:
            self.notify(f"Unable to update k6 request mode UI: {error}", severity="warning")
            return

        request_mode = str(select.value).strip().lower()
        target_tab = "tab_k6_scenarios" if request_mode == "scenarios" else "tab_k6_batch"
        tab_pane_ids = {pane.id for pane in k6_subtabs.query(TabPane) if pane.id}
        if target_tab not in tab_pane_ids:
            self.notify(
                f"Expected k6 request mode tab '{target_tab}' was not found.",
                severity="warning",
            )
            return

        k6_subtabs.active = target_tab

    def build_k6_scenario_subtab(self, index: int, endpoint_data: dict) -> TabPane:
        k6_config = self.ui_config.get("k6", {})
        endpoint_name = str(endpoint_data.get("name", "")).strip() or f"Endpoint {index + 1}"
        return TabPane(
            endpoint_name,
            ScrollableContainer(
                Horizontal(
                    Label("execution type:", classes="field-label"),
                    Select(
                        list(EXECUTION_TYPE_OPTIONS),
                        value=k6_config.get("executionType", ExecutionType.EXTERNAL_EXECUTOR.value),
                        id=f"select___k6__scenarios__{index}__executionType",
                    ),
                    classes="field-row",
                ),
                Horizontal(
                    Label("vus:", classes="field-label"),
                    Input(str(k6_config.get("vus", "")), id=f"input___k6__scenarios__{index}__vus"),
                    classes="field-row",
                ),
                Horizontal(
                    Label("duration:", classes="field-label"),
                    Input(str(k6_config.get("duration", "")), id=f"input___k6__scenarios__{index}__duration"),
                    classes="field-row",
                ),
                Horizontal(
                    Label("maxVUs:", classes="field-label"),
                    Input(str(k6_config.get("maxVUs", "")), id=f"input___k6__scenarios__{index}__maxVUs"),
                    classes="field-row",
                ),
                Horizontal(
                    Label("rate:", classes="field-label"),
                    Input(str(k6_config.get("rate", "")), id=f"input___k6__scenarios__{index}__rate"),
                    classes="field-row",
                ),
                Horizontal(
                    Label("timeUnit:", classes="field-label"),
                    Input(str(k6_config.get("timeUnit", "")), id=f"input___k6__scenarios__{index}__timeUnit"),
                    classes="field-row",
                ),
                Horizontal(
                    Label("preAllocatedVUs:", classes="field-label"),
                    Input(
                        str(k6_config.get("preAllocatedVUs", "")),
                        id=f"input___k6__scenarios__{index}__preAllocatedVUs",
                    ),
                    classes="field-row",
                ),
                Horizontal(
                    Label("startRate:", classes="field-label"),
                    Input(str(k6_config.get("startRate", "")), id=f"input___k6__scenarios__{index}__startRate"),
                    classes="field-row",
                ),
                Horizontal(
                    Label("spikeStages:", classes="field-label"),
                    Input(str(k6_config.get("spikeStages", "")), id=f"input___k6__scenarios__{index}__spikeStages"),
                    classes="field-row",
                ),
                Horizontal(
                    Label("rampingArrivalStages:", classes="field-label"),
                    Input(
                        str(k6_config.get("rampingArrivalStages", "")),
                        id=f"input___k6__scenarios__{index}__rampingArrivalStages",
                    ),
                    classes="field-row",
                ),
                classes="tab-container",
            ),
            id=self.scenario_tab_id(index),
        )

    def toggle_execution_type_fields(self) -> None:
        execution_select = self.query_one("#select___k6__executionType", Select)

        show_external_fields = execution_select.value == ExecutionType.EXTERNAL_EXECUTOR.value
        show_spike_fields = execution_select.value == ExecutionType.SPIKE_TESTS.value
        show_constant_vus_fields = execution_select.value == ExecutionType.CONSTANT_VUS.value
        show_constant_arrival_fields = execution_select.value == ExecutionType.CONSTANT_ARRIVAL_RATE.value
        show_ramping_arrival_fields = execution_select.value == ExecutionType.RAMPING_ARRIVAL_RATE.value

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
        selected_mode = str(auth_mode_select.value or AuthMode.NONE.value)
        oauth_enabled = selected_mode == AuthMode.OAUTH2_CLIENT_CREDENTIALS.value
        no_auth_enabled = selected_mode == AuthMode.NONE.value

        for row_id in ["#auth_row__client_id", "#auth_row__client_secret"]:
            self.query_one(row_id, Horizontal).styles.display = "none" if no_auth_enabled else "block"

        for row_id in ["#auth_oauth_row__token_url", "#auth_oauth_row__scope"]:
            self.query_one(row_id, Horizontal).styles.display = "block" if oauth_enabled else "none"

    def _normalize_logging_level(self, raw_value: object) -> str:
        return normalize_logging_level(raw_value)

    def toggle_logging_fields(self) -> None:
        logging_enabled_switch = self.query_one("#bool___k6__logging__enabled", Switch)
        web_dashboard_switch = self.query_one("#bool___k6__logging__webDashboard", Switch)
        warning_widget = self.query_one("#logging_external_mode_warning", Static)
        capabilities = self.refresh_execution_capabilities(self.ui_config)

        level_display = "block" if bool(logging_enabled_switch.value) else "none"
        web_dashboard_url_display = "block" if bool(web_dashboard_switch.value) else "none"
        external_warning_display = (
            "block"
            if (not capabilities.can_stop)
            or (not capabilities.can_scale)
            or (not capabilities.can_capture_logs)
            or (not capabilities.can_read_metrics)
            else "none"
        )

        self.query_one("#logging_level_label", Label).styles.display = level_display
        self.query_one("#select___k6__logging__level", Select).styles.display = level_display
        self.query_one("#logging_web_dashboard_url_label", Label).styles.display = web_dashboard_url_display
        self.query_one("#input___k6__logging__webDashboardUrl", Input).styles.display = web_dashboard_url_display
        warning_widget.styles.display = external_warning_display
        warning_widget.update(self._capabilities_warning_text(capabilities))
        self.set_run_ui_state(self.run_controller.is_running)

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="main_tabs"):
            with TabPane("Settings", id="tab_settings"):
                with TabbedContent(id="settings_subtabs"):
                    with TabPane("Auth", id="tab_auth"):
                        auth_data = self.ui_config.get("auth", {})
                        auth_mode = str(auth_data.get("mode", "")).strip()
                        if auth_mode not in {option[1] for option in AUTH_MODE_OPTIONS}:
                            auth_mode = AuthMode.NONE.value

                        yield ScrollableContainer(
                            Horizontal(
                                Label("mode:", classes="field-label"),
                                Select(
                                    list(AUTH_MODE_OPTIONS),
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
                                Input(self.ui_config.get("baseURL", ""), id="input___baseURL"),
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
                        k6_config = self.ui_config.get("k6", {})
                        execution_type = k6_config.get("executionType", ExecutionType.EXTERNAL_EXECUTOR.value)
                        if execution_type not in EXECUTION_TYPES:
                            execution_type = ExecutionType.EXTERNAL_EXECUTOR.value
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
                            ]
                        }

                        with Vertical(classes="tab-container"):
                            yield Horizontal(
                                Label("requestMode:", classes="field-label"),
                                Select(
                                    [("batch", "batch"), ("scenarios", "scenarios")],
                                    value=str(k6_config.get("requestMode", "batch")),
                                    id="select___k6__requestMode",
                                ),
                                classes="field-row",
                            )
                            with TabbedContent(id="k6_request_mode_subtabs"):
                                with TabPane("Batch", id="tab_k6_batch"):
                                    yield ScrollableContainer(
                                    Horizontal(
                                        Label("execution type:", classes="field-label"),
                                        Select(
                                            list(EXECUTION_TYPE_OPTIONS),
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
                                            Input(
                                                str(k6_config.get("preAllocatedVUs", "")),
                                                id="input___k6__preAllocatedVUs",
                                            ),
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
                            with TabPane("Scenarios", id="tab_k6_scenarios"):
                                yield TabbedContent(id="k6_scenarios_subtabs")

                    with TabPane("Logging", id="tab_logging"):
                        log_data = self.ui_config.setdefault("k6", {}).setdefault("logging", {})
                        log_data.setdefault("htmlSummaryReport", False)

                        other_logging_data = {
                            k: v
                            for k, v in log_data.items()
                            if k
                            not in [
                                "enabled",
                                "level",
                                "outputToUI",
                                "webDashboard",
                                "webDashboardUrl",
                                "htmlSummaryReport",
                            ]
                        }

                        yield ScrollableContainer(
                            Horizontal(
                                Label("enabled:", classes="field-label"),
                                Switch(bool(log_data.get("enabled", False)), id="bool___k6__logging__enabled"),
                                Label("level:", classes="field-label", id="logging_level_label"),
                                Select(
                                    list(LOGGING_LEVEL_OPTIONS),
                                    value=self._normalize_logging_level(log_data.get("level", LOGGING_LEVEL_FAILED)),
                                    id="select___k6__logging__level",
                                ),
                                classes="field-row",
                            ),
                            Horizontal(
                                Label("executionMode:", classes="field-label"),
                                Select(
                                    [
                                        ("Embedded UI terminal", True),
                                        ("External terminal (separate window)", False),
                                    ],
                                    value=bool(log_data.get("outputToUI", True)),
                                    id="select___k6__logging__outputToUI",
                                ),
                                classes="field-row",
                            ),
                            Static(
                                "⚠️ External terminal mode runs k6 outside this app. "
                                "Stop and scale actions from UI are unavailable.",
                                id="logging_external_mode_warning",
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
                            Horizontal(
                                Label("htmlSummaryReport:", classes="field-label"),
                                Switch(
                                    bool(log_data.get("htmlSummaryReport", False)),
                                    id="bool___k6__logging__htmlSummaryReport",
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
