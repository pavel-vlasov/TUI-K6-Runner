import asyncio

from app_mixins.request_mixin import RequestMixin


class DummyTabPane:
    def __init__(self, id_value):
        self.id = id_value


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

    def query_one(self, selector, _widget_type):
        if selector == "#request_subtabs":
            return self.request_subtabs
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

    ui.remove_last_request_endpoint_tab()

    assert ui.notifications == [("At least 1 endpoint must remain", "warning")]


def test_remove_last_request_endpoint_tab_sets_previous_active():
    ui = DummyRequestUI({}, pane_count=3)

    ui.remove_last_request_endpoint_tab()

    assert len(ui.request_subtabs._panes) == 2
    assert ui.request_subtabs.active == "tab_req_endpoint_1"
