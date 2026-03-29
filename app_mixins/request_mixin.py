from textual.containers import ScrollableContainer
from textual.widgets import Static, TabbedContent, TabPane

from constants import DEFAULT_CONFIG
from ui_components import build_config_fields


class RequestMixin:
    def get_request_mode(self) -> str:
        try:
            request_mode_switch = self.query_one("#k6_request_mode_switch")
            return "scenarios" if bool(request_mode_switch.value) else "batch"
        except Exception:
            pass
        mode = str(self.full_config.get("k6", {}).get("requestMode", "batch")).strip().lower()
        return mode if mode in {"batch", "scenarios"} else "batch"

    def _get_request_tab_panes(self) -> list[TabPane]:
        request_subtabs = self.query_one("#request_subtabs", TabbedContent)
        return list(request_subtabs.query(TabPane))

    def _get_k6_scenario_tab_panes(self) -> list[TabPane]:
        try:
            scenario_subtabs = self.query_one("#k6_scenario_subtabs", TabbedContent)
        except Exception:
            return []
        return [pane for pane in scenario_subtabs.query(TabPane) if pane.id and pane.id.startswith("tab_k6_endpoint_")]

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

    def remove_last_request_endpoint_tab(self):
        request_subtabs = self.query_one("#request_subtabs", TabbedContent)
        existing_tabs = self._get_request_tab_panes()

        if len(existing_tabs) <= 1:
            self.notify("At least 1 endpoint must remain", severity="warning")
            return

        last_tab = existing_tabs[-1]
        request_subtabs.remove_pane(last_tab.id)
        request_subtabs.active = existing_tabs[-2].id
        refresher = getattr(self, "call_after_refresh", None)
        if callable(refresher):
            refresher(self.sync_k6_scenario_tabs)

    async def sync_k6_scenario_tabs(self) -> None:
        scenario_subtabs = self.query_one("#k6_scenario_subtabs", TabbedContent)
        mode = self.get_request_mode()
        endpoint_tabs = self._get_request_tab_panes()
        existing = {pane.id: pane for pane in self._get_k6_scenario_tab_panes()}
        base_pane = self.query_one("#tab_k6_base", TabPane)

        if endpoint_tabs:
            base_pane.title = self._resolve_endpoint_name(0)

        if mode != "scenarios":
            for pane_id in list(existing):
                scenario_subtabs.remove_pane(pane_id)
            return

        valid_ids = {f"tab_k6_endpoint_{index}" for index in range(1, len(endpoint_tabs))}
        for pane_id in list(existing):
            if pane_id not in valid_ids:
                scenario_subtabs.remove_pane(pane_id)

        for index in range(1, len(endpoint_tabs)):
            pane_id = f"tab_k6_endpoint_{index}"
            endpoint_name = self._resolve_endpoint_name(index)
            if pane_id in existing:
                existing[pane_id].title = endpoint_name
                continue

            await scenario_subtabs.add_pane(
                TabPane(
                    endpoint_name,
                    self._build_scenario_settings_preview(endpoint_name),
                    id=pane_id,
                )
            )

    def _build_scenario_settings_preview(self, endpoint_name: str) -> ScrollableContainer:
        k6_config = self.full_config.get("k6", {})
        settings = [
            f"executionType: {k6_config.get('executionType', '')}",
            f"vus: {k6_config.get('vus', '')}",
            f"duration: {k6_config.get('duration', '')}",
            f"maxVUs: {k6_config.get('maxVUs', '')}",
            f"rate: {k6_config.get('rate', '')}",
            f"timeUnit: {k6_config.get('timeUnit', '')}",
            f"preAllocatedVUs: {k6_config.get('preAllocatedVUs', '')}",
            f"startRate: {k6_config.get('startRate', '')}",
            f"spikeStages: {k6_config.get('spikeStages', [])}",
            f"rampingArrivalStages: {k6_config.get('rampingArrivalStages', [])}",
        ]
        return ScrollableContainer(
            Static(f"Scenario for endpoint: {endpoint_name}", classes="field-row"),
            Static("\n".join(settings), classes="field-row"),
            classes="tab-container",
        )

    def _resolve_endpoint_name(self, index: int) -> str:
        endpoint_name = f"Endpoint {index + 1}"
        try:
            endpoint_input = self.query_one(f"#input___requestEndpoints__{index}__name")
            value = str(endpoint_input.value).strip()
            if value:
                endpoint_name = value
        except Exception:
            endpoint = self.get_request_endpoints()[index] if index < len(self.get_request_endpoints()) else {}
            endpoint_name = str(endpoint.get("name", endpoint_name)).strip() or endpoint_name
        return endpoint_name
