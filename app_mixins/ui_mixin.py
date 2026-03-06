from textual.app import ComposeResult
from textual.css.query import NoMatches
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

from ui_components import build_config_fields, get_valid_id


class UIMixin:
    def set_run_ui_state(self, running: bool) -> None:
        try:
            run_btn = self.query_one("#run_btn", Button)
            stop_btn = self.query_one("#stop_btn", Button)
            apply_btn = self.query_one("#apply_vu_btn", Button)
        except NoMatches:
            return

        run_btn.disabled = running
        stop_btn.disabled = not running
        apply_btn.disabled = not running

    async def on_mount(self) -> None:
        self.set_run_ui_state(False)
        self.toggle_execution_type_fields()

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

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="main_tabs"):
            with TabPane("Settings", id="tab_settings"):
                with TabbedContent(id="settings_subtabs"):
                    with TabPane("Auth", id="tab_auth"):
                        auth_data = self.full_config.get("auth", {})
                        switches_list = []
                        inputs_list = []
                        for k, v in auth_data.items():
                            full_key = f"auth.{k}"
                            if isinstance(v, bool):
                                switches_list.append(
                                    Horizontal(
                                        Label(k),
                                        Switch(v, id=get_valid_id(full_key, "bool")),
                                        classes="switch-group",
                                    )
                                )
                            else:
                                inputs_list.append(
                                    Horizontal(
                                        Label(f"{k}:", classes="field-label"),
                                        Input(str(v), id=get_valid_id(full_key, "input")),
                                        classes="field-row",
                                    )
                                )
                        yield ScrollableContainer(
                            Horizontal(*switches_list, classes="field-row"),
                            *inputs_list,
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
                        log_data = self.full_config.get("k6", {}).get("logging", {}).copy()
                        log_data.setdefault("metricsEnabled", False)
                        yield ScrollableContainer(*build_config_fields(log_data, "k6.logging"), classes="tab-container")

            with TabPane("Logs", id="tab_logs"):
                with TabbedContent(id="logs_subtabs"):
                    with TabPane("Output", id="tab_logs_output"):
                        with Vertical(id="log_view_container"):
                            yield Static("Waiting...\nPrepare to run", id="status_bar")
                            yield RichLog(id="output_log", markup=True, wrap=True)

                    with TabPane("Metrics", id="tab_logs_metrics"):
                        with ScrollableContainer(classes="tab-container"):
                            yield Static("Metrics are disabled.\nEnable k6.logging.metricsEnabled in Settings → Logging.", id="metrics_view")

        with Horizontal(id="button_row"):
            yield Input(placeholder="VUs...", id="vu_input")
            yield Button("✅ Apply", id="apply_vu_btn", variant="primary")
            yield Button("📋 Copy All Logs", id="copy_btn", variant="primary")
            yield Button("Stop k6", id="stop_btn", variant="error")
            yield Button("Save & Run k6 Test", id="run_btn", variant="success")

        yield Footer()
