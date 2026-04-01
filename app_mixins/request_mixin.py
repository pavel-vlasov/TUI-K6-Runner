from copy import deepcopy
import re

from textual.containers import ScrollableContainer
from textual.widgets import TabbedContent, TabPane

from constants import DEFAULT_CONFIG
from ui_components import build_config_fields


class RequestMixin:
    REQUEST_ENDPOINT_NAME_INPUT_RE = re.compile(r"^input___requestEndpoints__(\d+)__name$")

    def request_endpoint_key(self, index: int) -> str:
        return f"requestEndpoints[{index}]"

    def request_endpoint_tab_id(self, index: int) -> str:
        return f"tab_req_endpoint_{index}"

    def scenario_tab_id(self, index: int) -> str:
        return f"k6_scenario_{index}"

    def parse_request_endpoint_name_input_id(self, field_id: str | None) -> int | None:
        if not field_id:
            return None
        match = self.REQUEST_ENDPOINT_NAME_INPUT_RE.match(field_id)
        if not match:
            return None
        return int(match.group(1))

    def _get_request_tab_panes(self) -> list[TabPane]:
        request_subtabs = self.query_one("#request_subtabs", TabbedContent)
        return list(request_subtabs.query(TabPane))

    def get_request_endpoints(self):
        requests = self.ui_config.get("requestEndpoints")
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

        fallback = deepcopy(DEFAULT_CONFIG["requestEndpoints"][0])
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
            id=self.request_endpoint_tab_id(index),
        )

    def _set_tab_pane_title(self, pane: TabPane, title: str) -> None:
        if hasattr(pane, "title"):
            pane.title = title

    def _set_endpoint_tab_name(self, index: int, endpoint_name: str) -> None:
        tab_id = self.request_endpoint_tab_id(index)
        for pane in self._get_request_tab_panes():
            if pane.id == tab_id:
                self._set_tab_pane_title(pane, endpoint_name)
                break

    def _set_scenario_tab_name(self, index: int, endpoint_name: str) -> None:
        try:
            scenario_subtabs = self.query_one("#k6_scenarios_subtabs", TabbedContent)
        except Exception:
            return
        tab_id = self.scenario_tab_id(index)
        for pane in scenario_subtabs.query(TabPane):
            if pane.id == tab_id:
                self._set_tab_pane_title(pane, endpoint_name)
                break

    def rename_request_endpoint(self, index: int, endpoint_name: str) -> None:
        normalized_name = endpoint_name.strip() or f"Endpoint {index + 1}"
        self._set_endpoint_tab_name(index, normalized_name)
        self._set_scenario_tab_name(index, normalized_name)

    async def add_request_endpoint_tab(self):
        request_subtabs = self.query_one("#request_subtabs", TabbedContent)
        existing_tabs = self._get_request_tab_panes()

        if len(existing_tabs) >= 5:
            self.notify("Maximum 5 endpoints allowed", severity="warning")
            return

        endpoint_index = len(existing_tabs)
        new_endpoint = deepcopy(DEFAULT_CONFIG["requestEndpoints"][0])
        new_endpoint["name"] = f"Endpoint {endpoint_index + 1}"

        await request_subtabs.add_pane(self.build_request_subtab(endpoint_index, new_endpoint))
        request_subtabs.active = self.request_endpoint_tab_id(endpoint_index)
        await self.rebuild_k6_scenario_tabs()

    async def remove_last_request_endpoint_tab(self):
        request_subtabs = self.query_one("#request_subtabs", TabbedContent)
        existing_tabs = self._get_request_tab_panes()

        if len(existing_tabs) <= 1:
            self.notify("At least 1 endpoint must remain", severity="warning")
            return

        removed_index = len(existing_tabs) - 1
        last_tab = existing_tabs[-1]
        request_subtabs.remove_pane(last_tab.id)
        remaining_endpoints = self.get_request_endpoints()[:removed_index]
        self.ui_config["requestEndpoints"] = remaining_endpoints

        await self._rebuild_request_subtabs(remaining_endpoints)
        request_subtabs.active = self.request_endpoint_tab_id(removed_index - 1)
        await self.rebuild_k6_scenario_tabs()

    async def _rebuild_request_subtabs(self, request_endpoints: list[dict]) -> None:
        request_subtabs = self.query_one("#request_subtabs", TabbedContent)

        removal_ops = []
        for pane in list(request_subtabs.query(TabPane)):
            removal_result = request_subtabs.remove_pane(pane.id)
            if hasattr(removal_result, "__await__"):
                removal_ops.append(removal_result)

        for removal_op in removal_ops:
            await removal_op

        for index, request_data in enumerate(request_endpoints):
            await request_subtabs.add_pane(self.build_request_subtab(index, request_data))
