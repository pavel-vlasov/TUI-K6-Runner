import inspect
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widgets import Input, Label, Select, Static, TabbedContent, TabPane

from constants import DEFAULT_CONFIG
from ui_components import build_config_fields


class RequestMixin:
    SCENARIO_EXECUTION_TYPES = (
        "external executor",
        "Spike Tests",
        "Constant VUs",
        "Constant Arrival Rate",
        "Ramping Arrival Rate",
    )

    def _get_request_tab_panes(self) -> list[TabPane]:
        request_subtabs = self.query_one("#request_subtabs", TabbedContent)
        return list(request_subtabs.query(TabPane))

    def get_request_endpoints(self):
        requests = self.full_config.get("requestEndpoints")
        if isinstance(requests, list) and requests:
            normalized = []
            for index, req in enumerate(requests[:5]):
                if not isinstance(req, dict):
                    continue
                endpoint = req.copy()
                endpoint.setdefault("name", f"Endpoint {index + 1}")
                normalized.append(endpoint)
            if normalized:
                return normalized

        legacy_request = self.full_config.get("request")
        if isinstance(legacy_request, dict):
            endpoint = legacy_request.copy()
            endpoint.setdefault("name", "Endpoint 1")
            return [endpoint]

        fallback = DEFAULT_CONFIG["request"].copy()
        fallback["name"] = "Endpoint 1"
        return [fallback]

    def build_request_subtab(self, index: int, request_data: dict) -> TabPane:
        endpoint_name = str(request_data.get("name", "")).strip() or f"Endpoint {index + 1}"
        return TabPane(
            endpoint_name,
            ScrollableContainer(
                *build_config_fields(request_data, f"requestEndpoints.{index}"),
                classes="tab-container",
            ),
            id=f"tab_req_endpoint_{index}",
        )

    def build_k6_scenario_subtab(self, index: int, request_data: dict) -> TabPane:
        endpoint_name = str(request_data.get("name", "")).strip() or f"Endpoint {index + 1}"
        scenario_data = request_data.get("scenario", {}) if isinstance(request_data.get("scenario"), dict) else {}
        execution_type = str(scenario_data.get("executionType", "external executor")).strip()
        if execution_type not in self.SCENARIO_EXECUTION_TYPES:
            execution_type = "external executor"

        prefix = f"requestEndpoints__{index}__scenario"
        return TabPane(
            endpoint_name,
            ScrollableContainer(
                Static(f"[bold]{endpoint_name}[/bold]"),
                Horizontal(
                    Label("executionType:", classes="field-label"),
                    Select(
                        [(execution_type_name, execution_type_name) for execution_type_name in self.SCENARIO_EXECUTION_TYPES],
                        value=execution_type,
                        id=f"select___{prefix}__executionType",
                    ),
                    classes="field-row",
                ),
                Horizontal(
                    Label("vus:", classes="field-label"),
                    Input(str(scenario_data.get("vus", 1)), id=f"input___{prefix}__vus"),
                    classes="field-row",
                    id=f"req_endpoint_{index}_scenario_vus_row",
                ),
                Horizontal(
                    Label("duration:", classes="field-label"),
                    Input(str(scenario_data.get("duration", "60s")), id=f"input___{prefix}__duration"),
                    classes="field-row",
                    id=f"req_endpoint_{index}_scenario_duration_row",
                ),
                Horizontal(
                    Label("rate:", classes="field-label"),
                    Input(str(scenario_data.get("rate", 10)), id=f"input___{prefix}__rate"),
                    classes="field-row",
                    id=f"req_endpoint_{index}_scenario_rate_row",
                ),
                Horizontal(
                    Label("timeUnit:", classes="field-label"),
                    Input(str(scenario_data.get("timeUnit", "1s")), id=f"input___{prefix}__timeUnit"),
                    classes="field-row",
                    id=f"req_endpoint_{index}_scenario_timeunit_row",
                ),
                Horizontal(
                    Label("preAllocatedVUs:", classes="field-label"),
                    Input(str(scenario_data.get("preAllocatedVUs", 10)), id=f"input___{prefix}__preAllocatedVUs"),
                    classes="field-row",
                    id=f"req_endpoint_{index}_scenario_preallocated_row",
                ),
                Horizontal(
                    Label("maxVUs:", classes="field-label"),
                    Input(str(scenario_data.get("maxVUs", 50)), id=f"input___{prefix}__maxVUs"),
                    classes="field-row",
                    id=f"req_endpoint_{index}_scenario_maxvus_row",
                ),
                Horizontal(
                    Label("startRate:", classes="field-label"),
                    Input(str(scenario_data.get("startRate", 1)), id=f"input___{prefix}__startRate"),
                    classes="field-row",
                    id=f"req_endpoint_{index}_scenario_start_rate_row",
                ),
                Vertical(
                    Label("stages (JSON):"),
                    Input(str(scenario_data.get("stages", [{"duration": "30s", "target": 10}])), id=f"input___{prefix}__stages"),
                    classes="field-row-multiline",
                    id=f"req_endpoint_{index}_scenario_stages_group",
                ),
                classes="tab-container",
            ),
            id=f"tab_k6_scenario_{index}",
        )

    def toggle_endpoint_execution_type_fields(self, index: int) -> None:
        execution_select = self.query_one(f"#select___requestEndpoints__{index}__scenario__executionType", Select)
        execution_type = str(execution_select.value or "").strip()

        show_external_fields = execution_type == "external executor"
        show_spike_fields = execution_type == "Spike Tests"
        show_constant_vus_fields = execution_type == "Constant VUs"
        show_constant_arrival_fields = execution_type == "Constant Arrival Rate"
        show_ramping_arrival_fields = execution_type == "Ramping Arrival Rate"

        self.query_one(f"#req_endpoint_{index}_scenario_vus_row", Horizontal).styles.display = (
            "block" if (show_external_fields or show_constant_vus_fields) else "none"
        )
        self.query_one(f"#req_endpoint_{index}_scenario_maxvus_row", Horizontal).styles.display = (
            "block"
            if (show_external_fields or show_constant_arrival_fields or show_ramping_arrival_fields)
            else "none"
        )
        self.query_one(f"#req_endpoint_{index}_scenario_duration_row", Horizontal).styles.display = (
            "block" if (show_external_fields or show_constant_vus_fields or show_constant_arrival_fields) else "none"
        )

        self.query_one(f"#req_endpoint_{index}_scenario_rate_row", Horizontal).styles.display = (
            "block" if (show_constant_arrival_fields or show_ramping_arrival_fields) else "none"
        )
        self.query_one(f"#req_endpoint_{index}_scenario_timeunit_row", Horizontal).styles.display = (
            "block" if (show_constant_arrival_fields or show_ramping_arrival_fields) else "none"
        )
        self.query_one(f"#req_endpoint_{index}_scenario_preallocated_row", Horizontal).styles.display = (
            "block" if (show_constant_arrival_fields or show_ramping_arrival_fields) else "none"
        )
        self.query_one(f"#req_endpoint_{index}_scenario_start_rate_row", Horizontal).styles.display = (
            "block" if show_ramping_arrival_fields else "none"
        )
        self.query_one(f"#req_endpoint_{index}_scenario_stages_group", Vertical).styles.display = (
            "block" if (show_spike_fields or show_ramping_arrival_fields) else "none"
        )

    def _collect_request_endpoint_data_from_ui(self) -> list[dict]:
        endpoints = self.get_request_endpoints()
        for index, endpoint in enumerate(endpoints):
            try:
                endpoint_name = self.query_one(f"#input___requestEndpoints__{index}__name")
                endpoint["name"] = str(endpoint_name.value).strip() or f"Endpoint {index + 1}"
            except Exception:
                endpoint["name"] = str(endpoint.get("name", "")).strip() or f"Endpoint {index + 1}"
        return endpoints


    async def _remove_pane(self, tabbed_content: TabbedContent, pane_id: str) -> None:
        removal = tabbed_content.remove_pane(pane_id)
        if inspect.isawaitable(removal):
            await removal

    async def sync_k6_scenario_tabs(self) -> None:
        try:
            scenario_subtabs = self.query_one("#k6_scenarios_subtabs", TabbedContent)
        except Exception:
            return

        existing_tabs = list(scenario_subtabs.query(TabPane))
        for pane in existing_tabs:
            await self._remove_pane(scenario_subtabs, pane.id)

        endpoints = self._collect_request_endpoint_data_from_ui()
        for index, request_data in enumerate(endpoints):
            await scenario_subtabs.add_pane(self.build_k6_scenario_subtab(index, request_data))
            try:
                self.toggle_endpoint_execution_type_fields(index)
            except Exception:
                continue

        if endpoints:
            scenario_subtabs.active = "tab_k6_scenario_0"

    async def add_request_endpoint_tab(self):
        request_subtabs = self.query_one("#request_subtabs", TabbedContent)
        existing_tabs = self._get_request_tab_panes()

        if len(existing_tabs) >= 5:
            self.notify("Maximum 5 endpoints allowed", severity="warning")
            return

        endpoint_index = len(existing_tabs)
        new_endpoint = DEFAULT_CONFIG["request"].copy()
        new_endpoint["name"] = f"Endpoint {endpoint_index + 1}"

        await request_subtabs.add_pane(self.build_request_subtab(endpoint_index, new_endpoint))
        request_subtabs.active = f"tab_req_endpoint_{endpoint_index}"
        await self.sync_k6_scenario_tabs()

    async def remove_last_request_endpoint_tab(self):
        request_subtabs = self.query_one("#request_subtabs", TabbedContent)
        existing_tabs = self._get_request_tab_panes()

        if len(existing_tabs) <= 1:
            self.notify("At least 1 endpoint must remain", severity="warning")
            return

        last_tab = existing_tabs[-1]
        await self._remove_pane(request_subtabs, last_tab.id)
        request_subtabs.active = existing_tabs[-2].id
        await self.sync_k6_scenario_tabs()
