import asyncio

from app_mixins.request_mixin import RequestMixin
from constants import DEFAULT_CONFIG


class DummyTabPane:
    def __init__(self, id_value, title=""):
        self.id = id_value
        self.title = title


class ImmutableIdDummyTabPane(DummyTabPane):
    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        if hasattr(self, "_id"):
            raise AttributeError("id is immutable")
        self._id = value


class DummyTabbedContent:
    def __init__(self, panes, async_remove=False):
        self._panes = panes
        self.active = None
        self.async_remove = async_remove

    def query(self, _kind):
        return self._panes

    async def add_pane(self, pane):
        self._panes.append(pane)

    def remove_pane(self, pane_id):
        if self.async_remove:
            async def _remove_async():
                self._panes = [pane for pane in self._panes if pane.id != pane_id]

            return _remove_async()

        self._panes = [pane for pane in self._panes if pane.id != pane_id]


class DummyRequestUI(RequestMixin):
    def __init__(self, ui_config, pane_count=1, async_remove=False):
        self.ui_config = ui_config
        self.notifications = []
        panes = [DummyTabPane(f"tab_req_endpoint_{i}", title=f"Endpoint {i + 1}") for i in range(pane_count)]
        self.request_subtabs = DummyTabbedContent(panes, async_remove=async_remove)
        self.scenario_subtabs = DummyTabbedContent(
            [DummyTabPane(f"k6_scenario_{i}", title=f"Endpoint {i + 1}") for i in range(pane_count)]
        )
        self.rebuild_k6_scenario_tabs_calls = 0

    def query_one(self, selector, _widget_type):
        if selector == "#request_subtabs":
            return self.request_subtabs
        if selector == "#k6_scenarios_subtabs":
            return self.scenario_subtabs
        raise KeyError(selector)

    def notify(self, message, severity=None):
        self.notifications.append((message, severity))

    async def rebuild_k6_scenario_tabs(self):
        self.rebuild_k6_scenario_tabs_calls += 1


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


def test_get_request_endpoints_falls_back_to_default():
    default_ui = DummyRequestUI({})
    defaults = default_ui.get_request_endpoints()
    assert defaults[0] == DEFAULT_CONFIG["requestEndpoints"][0]


def test_default_config_has_no_root_request_template():
    assert "request" not in DEFAULT_CONFIG


def test_add_request_endpoint_tab_uses_request_endpoints_default_template():
    class CapturingRequestUI(DummyRequestUI):
        def __init__(self):
            super().__init__({}, pane_count=1)
            self.captured_request_data = None

        def build_request_subtab(self, index, request_data):
            self.captured_request_data = request_data
            return DummyTabPane(f"tab_req_endpoint_{index}")

    ui = CapturingRequestUI()

    asyncio.run(ui.add_request_endpoint_tab())

    assert len(ui.request_subtabs._panes) == 2
    assert ui.request_subtabs.active == "tab_req_endpoint_1"
    assert ui.captured_request_data == {
        **DEFAULT_CONFIG["requestEndpoints"][0],
        "name": "Endpoint 2",
    }
    assert ui.rebuild_k6_scenario_tabs_calls == 1


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
    assert ui.rebuild_k6_scenario_tabs_calls == 1


def test_remove_last_request_endpoint_tab_removes_only_last_endpoint_from_ui_snapshot():
    class SnapshotRequestUI(DummyRequestUI):
        def _collect_ui_field_values(self):
            return {
                "input___requestEndpoints__0__name": "Endpoint 1",
                "input___requestEndpoints__0__path": "/one",
                "input___requestEndpoints__1__name": "Endpoint 2",
                "input___requestEndpoints__1__path": "/two",
                "input___requestEndpoints__2__name": "Endpoint 3",
                "input___requestEndpoints__2__path": "/three",
            }

    ui = SnapshotRequestUI(
        {
            "requestEndpoints": [
                {"name": "Old 1", "path": "/old-1"},
            ]
        },
        pane_count=3,
        async_remove=True,
    )

    asyncio.run(ui.remove_last_request_endpoint_tab())

    assert len(ui.request_subtabs._panes) == 2
    assert ui.request_subtabs.active == "tab_req_endpoint_1"
    assert ui.ui_config["requestEndpoints"] == [
        {"name": "Endpoint 1", "path": "/one"},
        {"name": "Endpoint 2", "path": "/two"},
    ]
    assert ui.rebuild_k6_scenario_tabs_calls == 1


def test_rename_request_endpoint_updates_request_and_scenario_titles():
    ui = DummyRequestUI({}, pane_count=2)

    ui.rename_request_endpoint(1, "Checkout API")

    assert ui.request_subtabs._panes[1].title == "Checkout API"
    assert ui.scenario_subtabs._panes[1].title == "Checkout API"


def test_parse_request_endpoint_name_input_id_returns_index():
    ui = DummyRequestUI({}, pane_count=1)

    assert ui.parse_request_endpoint_name_input_id("input___requestEndpoints__0__name") == 0
    assert ui.parse_request_endpoint_name_input_id("input___requestEndpoints__x__name") is None
    assert ui.parse_request_endpoint_name_input_id("input___k6__scenarios__0__vus") is None


def test_remove_last_request_endpoint_tab_handles_immutable_ids_and_syncs_config():
    ui = DummyRequestUI(
        {
            "requestEndpoints": [
                {"name": "Endpoint 1", "path": "/1"},
                {"name": "Endpoint 2", "path": "/2"},
                {"name": "Endpoint 3", "path": "/3"},
            ]
        },
        pane_count=3,
    )
    ui.request_subtabs._panes = [
        ImmutableIdDummyTabPane("tab_req_endpoint_0", title="Endpoint 1"),
        ImmutableIdDummyTabPane("tab_req_endpoint_1", title="Endpoint 2"),
        ImmutableIdDummyTabPane("tab_req_endpoint_2", title="Endpoint 3"),
    ]

    asyncio.run(ui.remove_last_request_endpoint_tab())

    assert len(ui.request_subtabs._panes) == 2
    assert [pane.id for pane in ui.request_subtabs._panes] == [
        "tab_req_endpoint_0",
        "tab_req_endpoint_1",
    ]
    assert len(ui.ui_config["requestEndpoints"]) == 2
