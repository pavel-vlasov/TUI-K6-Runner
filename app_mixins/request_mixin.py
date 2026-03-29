from textual.containers import ScrollableContainer
from textual.widgets import Static, TabbedContent, TabPane

from constants import DEFAULT_CONFIG
from ui_components import build_config_fields


class RequestMixin:
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
        method = str(request_data.get("method", "GET")).upper().strip() or "GET"
        path = str(request_data.get("path", "")).strip() or "/"
        return TabPane(
            endpoint_name,
            ScrollableContainer(
                Static(f"[bold]{endpoint_name}[/bold]"),
                Static(f"method: {method}"),
                Static(f"path: {path}"),
                classes="tab-container",
            ),
            id=f"tab_k6_scenario_{index}",
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

    async def sync_k6_scenario_tabs(self) -> None:
        try:
            scenario_subtabs = self.query_one("#k6_scenarios_subtabs", TabbedContent)
        except Exception:
            return

        existing_tabs = list(scenario_subtabs.query(TabPane))
        for pane in existing_tabs:
            scenario_subtabs.remove_pane(pane.id)

        endpoints = self._collect_request_endpoint_data_from_ui()
        for index, request_data in enumerate(endpoints):
            await scenario_subtabs.add_pane(self.build_k6_scenario_subtab(index, request_data))

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
        request_subtabs.remove_pane(last_tab.id)
        request_subtabs.active = existing_tabs[-2].id
        await self.sync_k6_scenario_tabs()
