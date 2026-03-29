import asyncio

from app_mixins.request_mixin import RequestMixin


class DummyTabPane:
    def __init__(self, id_value, title="tab"):
        self.id = id_value
        self.title = title


class DummyTabbedContent:
    def __init__(self, panes):
        self._panes = panes
        self.active = None

    def query(self, _kind):
        return self._panes

    async def add_pane(self, pane):
        self._panes.append(pane)

    def remove_pane(self, pane_id):
        self._panes = [pane for pane in self._panes if pane.id != pane_id]


class DummyRequestUI(RequestMixin):
    def __init__(self, full_config, pane_count=1):
        self.full_config = full_config
        self.notifications = []
        panes = [DummyTabPane(f"tab_req_endpoint_{i}") for i in range(pane_count)]
        self.request_subtabs = DummyTabbedContent(panes)
        self.k6_scenarios_subtabs = DummyTabbedContent([])

    def query_one(self, selector, _widget_type=None):
        if selector == "#request_subtabs":
            return self.request_subtabs
        if selector == "#k6_scenarios_subtabs":
            return self.k6_scenarios_subtabs
        if selector.startswith("#input___requestEndpoints__") and selector.endswith("__name"):
            idx = int(selector.split("__")[2])
            endpoint = self.full_config.get("requestEndpoints", [])
            value = endpoint[idx].get("name", "") if idx < len(endpoint) else ""
            return type("NameInput", (), {"value": value})()
        raise KeyError(selector)

    def notify(self, message, severity=None):
        self.notifications.append((message, severity))


def test_get_request_endpoints_from_config_with_limit_and_default_names():
    ui = DummyRequestUI(
        {
            "requestEndpoints": [
                {"path": "/1"},
                "skip",
                {"name": "", "path": "/2"},
                {"name": "A", "path": "/3"},
                {"path": "/4"},
                {"path": "/5"},
            ]
        }
    )

    endpoints = ui.get_request_endpoints()

    assert len(endpoints) == 4
    assert endpoints[0]["name"] == "Endpoint 1"


def test_get_request_endpoints_falls_back_to_legacy_and_default():
    legacy_ui = DummyRequestUI({"request": {"path": "/legacy"}})
    endpoints = legacy_ui.get_request_endpoints()
    assert endpoints[0]["name"] == "Endpoint 1"
    assert endpoints[0]["path"] == "/legacy"

    default_ui = DummyRequestUI({})
    defaults = default_ui.get_request_endpoints()
    assert defaults[0]["name"] == "Endpoint 1"
    assert defaults[0]["path"].startswith("/")


def test_add_request_endpoint_tab_enforces_maximum():
    ui = DummyRequestUI({}, pane_count=5)

    asyncio.run(ui.add_request_endpoint_tab())

    assert ui.notifications == [("Maximum 5 endpoints allowed", "warning")]


def test_remove_last_request_endpoint_tab_enforces_minimum():
    ui = DummyRequestUI({}, pane_count=1)

    asyncio.run(ui.remove_last_request_endpoint_tab())

    assert ui.notifications == [("At least 1 endpoint must remain", "warning")]


def test_remove_last_request_endpoint_tab_sets_previous_active():
    ui = DummyRequestUI({}, pane_count=3)

    asyncio.run(ui.remove_last_request_endpoint_tab())

    assert len(ui.request_subtabs._panes) == 2
    assert ui.request_subtabs.active == "tab_req_endpoint_1"


def test_sync_k6_scenario_tabs_uses_endpoint_names():
    ui = DummyRequestUI(
        {
            "requestEndpoints": [
                {"name": "Users", "method": "GET", "path": "/users"},
                {"name": "", "method": "POST", "path": "/orders"},
            ]
        },
        pane_count=2,
    )

    asyncio.run(ui.sync_k6_scenario_tabs())

    assert len(ui.k6_scenarios_subtabs._panes) == 2
    first_title = str(getattr(ui.k6_scenarios_subtabs._panes[0], "_title", ""))
    second_title = str(getattr(ui.k6_scenarios_subtabs._panes[1], "_title", ""))
    assert "Users" in first_title
    assert "Endpoint 2" in second_title
