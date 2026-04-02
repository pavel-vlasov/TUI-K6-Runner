from app_mixins.ui_mixin import UIMixin
from constants import AuthMode, ExecutionType, LOGGING_LEVEL_ALL, LOGGING_LEVEL_FAILED, LOGGING_LEVEL_FAILED_WITHOUT_PAYLOADS
from k6.backends import ExecutionCapabilities


class DummyButton:
    def __init__(self):
        self.disabled = False
        self.display = True


class DummyValueWidget:
    def __init__(self, value=False):
        self.value = value


class DummyStyles:
    def __init__(self):
        self.display = "block"


class DummyRow:
    def __init__(self):
        self.styles = DummyStyles()


class DummyWidget:
    def __init__(self):
        self.styles = DummyStyles()
        self.renderable = ""

    def update(self, value):
        self.renderable = value


class DummyRequestSubtabs:
    def __init__(self):
        self.added_panes = []

    async def add_pane(self, pane):
        self.added_panes.append(pane)


class DummyPane:
    def __init__(self, pane_id: str):
        self.id = pane_id


class DummyScenarioSubtabs:
    def __init__(self, pane_ids: list[str] | None = None, active: str | None = None, field_widgets=None):
        self.panes = [DummyPane(pane_id) for pane_id in (pane_ids or [])]
        self.active = active
        self.field_widgets = field_widgets or []

    def query(self, widget_type):
        if widget_type == "Input, Select, Switch, TextArea":
            return self.field_widgets
        return self.panes

    async def remove_pane(self, pane_id):
        self.panes = [pane for pane in self.panes if pane.id != pane_id]

    async def add_pane(self, pane):
        self.panes.append(pane)


class DummyUI(UIMixin):
    def __init__(
        self,
        web_dashboard_enabled: bool,
        auth_mode: str = AuthMode.NONE.value,
        execution_type: str = ExecutionType.EXTERNAL_EXECUTOR.value,
        capabilities: ExecutionCapabilities | None = None,
    ):
        self.execution_capabilities = capabilities or ExecutionCapabilities(
            can_stop=True,
            can_scale=True,
            can_capture_logs=True,
            can_read_metrics=True,
        )
        self.ui_config = {
            "k6": {
                "executionType": execution_type,
                "logging": {"webDashboard": web_dashboard_enabled, "outputToUI": True},
            }
        }
        self.run_controller = type(
            "RC",
            (),
            {
                "is_running": False,
                "resolve_capabilities": lambda _self, _config: self.execution_capabilities,
            },
        )()
        self.buttons = {
            "#run_btn": DummyButton(),
            "#stop_btn": DummyButton(),
            "#apply_vu_btn": DummyButton(),
            "#web_dashboard_btn": DummyButton(),
        }
        self.auth_selects = {
            "#select___auth__mode": DummyValueWidget(auth_mode),
        }
        self.auth_rows = {
            "#auth_row__client_id": DummyRow(),
            "#auth_row__client_secret": DummyRow(),
            "#auth_oauth_row__token_url": DummyRow(),
            "#auth_oauth_row__scope": DummyRow(),
        }
        self.logging_switches = {
            "#bool___k6__logging__enabled": DummyValueWidget(False),
            "#bool___k6__logging__webDashboard": DummyValueWidget(False),
        }
        self.logging_selects = {
            "#select___k6__logging__outputToUI": DummyValueWidget(True),
        }
        self.logging_widgets = {
            "#logging_level_label": DummyWidget(),
            "#select___k6__logging__level": DummyWidget(),
            "#logging_web_dashboard_url_label": DummyWidget(),
            "#input___k6__logging__webDashboardUrl": DummyWidget(),
            "#logging_external_mode_warning": DummyWidget(),
        }
        self.execution_select = DummyValueWidget(execution_type)
        self.request_mode_select = DummyValueWidget("parallel")
        self.execution_rows = {
            "#k6_vus_row": DummyRow(),
            "#k6_maxvus_row": DummyRow(),
            "#k6_duration_row": DummyRow(),
            "#k6_rate_row": DummyRow(),
            "#k6_timeunit_row": DummyRow(),
            "#k6_preallocated_row": DummyRow(),
            "#k6_start_rate_row": DummyRow(),
            "#spike_stages_group": DummyRow(),
            "#arrival_stages_group": DummyRow(),
            "#ramping_arrival_scroll_group": DummyRow(),
        }
        self.request_subtabs = DummyRequestSubtabs()
        self.scenario_widgets = []
        self.k6_scenario_subtabs = DummyScenarioSubtabs(
            ["tab_k6_scenario_0", "tab_k6_scenario_1"],
            "tab_k6_scenario_1",
            self.scenario_widgets,
        )
        self.request_tab_panes = []
        self.request_endpoints = []
        self.built_request_tabs = []
        self.built_k6_tabs = []
        self.notifications = []
        self.config_load_error = None
        self.config_load_error_details = None

    def query_one(self, selector, _widget_type=None):
        if selector == "#select___k6__executionType":
            return self.execution_select
        if selector == "#request_subtabs":
            return self.request_subtabs
        if selector == "#k6_scenario_subtabs":
            return self.k6_scenario_subtabs
        if selector == "#select___k6__requestMode":
            return self.request_mode_select
        if selector in self.execution_rows:
            return self.execution_rows[selector]
        if selector in self.buttons:
            return self.buttons[selector]
        if selector in self.auth_selects:
            return self.auth_selects[selector]
        if selector in self.auth_rows:
            return self.auth_rows[selector]
        if selector in self.logging_switches:
            return self.logging_switches[selector]
        if selector in self.logging_selects:
            return self.logging_selects[selector]
        if selector in self.logging_widgets:
            return self.logging_widgets[selector]
        raise KeyError(selector)

    def query(self, selector):
        if selector == "Input, Select, Switch, TextArea":
            return self.scenario_widgets
        return []

    def _get_request_tab_panes(self):
        return self.request_tab_panes

    def get_request_endpoints(self):
        return self.request_endpoints

    def build_request_subtab(self, index, request_data):
        tab = {"index": index, "request_data": request_data}
        self.built_request_tabs.append(tab)
        return tab

    def notify(self, message, severity="information"):
        self.notifications.append((severity, message))

    def build_k6_settings_tab(self, tab_title, index):
        pane = DummyPane(f"tab_k6_scenario_{index}")
        pane.title = tab_title
        self.built_k6_tabs.append((tab_title, index))
        return pane


def test_web_dashboard_button_disabled_when_not_running():
    ui = DummyUI(web_dashboard_enabled=True)

    ui.set_run_ui_state(False)

    assert ui.buttons["#web_dashboard_btn"].display is True
    assert ui.buttons["#web_dashboard_btn"].disabled is True


def test_web_dashboard_button_visible_and_disabled_when_feature_off():
    ui = DummyUI(web_dashboard_enabled=False)

    ui.set_run_ui_state(True)

    assert ui.buttons["#web_dashboard_btn"].display is True
    assert ui.buttons["#web_dashboard_btn"].disabled is True


def test_toggle_auth_fields_hides_client_fields_for_no_auth():
    ui = DummyUI(web_dashboard_enabled=False, auth_mode=AuthMode.NONE.value)

    ui.toggle_auth_fields()

    assert ui.auth_rows["#auth_row__client_id"].styles.display == "none"
    assert ui.auth_rows["#auth_row__client_secret"].styles.display == "none"


def test_toggle_auth_fields_shows_client_fields_when_auth_selected():
    ui = DummyUI(web_dashboard_enabled=False, auth_mode=AuthMode.BASIC.value)

    ui.toggle_auth_fields()

    assert ui.auth_rows["#auth_row__client_id"].styles.display == "block"
    assert ui.auth_rows["#auth_row__client_secret"].styles.display == "block"


def test_toggle_auth_fields_shows_oauth_rows_only_for_oauth_mode():
    ui = DummyUI(web_dashboard_enabled=False, auth_mode=AuthMode.OAUTH2_CLIENT_CREDENTIALS.value)

    ui.toggle_auth_fields()

    assert ui.auth_rows["#auth_oauth_row__token_url"].styles.display == "block"
    assert ui.auth_rows["#auth_oauth_row__scope"].styles.display == "block"


def test_toggle_logging_fields_hides_level_and_dashboard_url_when_switches_off():
    ui = DummyUI(web_dashboard_enabled=False)

    ui.logging_switches["#bool___k6__logging__enabled"].value = False
    ui.logging_switches["#bool___k6__logging__webDashboard"].value = False
    ui.toggle_logging_fields()

    assert ui.logging_widgets["#logging_level_label"].styles.display == "none"
    assert ui.logging_widgets["#select___k6__logging__level"].styles.display == "none"
    assert ui.logging_widgets["#logging_web_dashboard_url_label"].styles.display == "none"
    assert ui.logging_widgets["#input___k6__logging__webDashboardUrl"].styles.display == "none"


def test_toggle_logging_fields_shows_level_and_dashboard_url_when_switches_on():
    ui = DummyUI(web_dashboard_enabled=False)

    ui.logging_switches["#bool___k6__logging__enabled"].value = True
    ui.logging_switches["#bool___k6__logging__webDashboard"].value = True
    ui.toggle_logging_fields()

    assert ui.logging_widgets["#logging_level_label"].styles.display == "block"
    assert ui.logging_widgets["#select___k6__logging__level"].styles.display == "block"
    assert ui.logging_widgets["#logging_web_dashboard_url_label"].styles.display == "block"
    assert ui.logging_widgets["#input___k6__logging__webDashboardUrl"].styles.display == "block"


def test_toggle_logging_fields_shows_external_mode_warning_and_disables_stop_scale():
    ui = DummyUI(
        web_dashboard_enabled=False,
        capabilities=ExecutionCapabilities(
            can_stop=False,
            can_scale=False,
            can_capture_logs=False,
            can_read_metrics=False,
        ),
    )
    ui.run_controller.is_running = True

    ui.toggle_logging_fields()

    assert ui.logging_widgets["#logging_external_mode_warning"].styles.display == "block"
    assert ui.buttons["#stop_btn"].disabled is True
    assert ui.buttons["#apply_vu_btn"].disabled is True


def test_set_run_ui_state_enables_apply_for_supported_capabilities_when_running():
    ui = DummyUI(
        web_dashboard_enabled=False,
        capabilities=ExecutionCapabilities(
            can_stop=True,
            can_scale=True,
            can_capture_logs=True,
            can_read_metrics=True,
        ),
    )
    ui.run_controller.is_running = True

    ui.set_run_ui_state(True)

    assert ui.buttons["#apply_vu_btn"].disabled is False


def test_set_run_ui_state_disables_apply_when_scale_capability_is_missing():
    ui = DummyUI(
        web_dashboard_enabled=False,
        capabilities=ExecutionCapabilities(
            can_stop=True,
            can_scale=False,
            can_capture_logs=True,
            can_read_metrics=True,
        ),
    )
    ui.run_controller.is_running = True

    ui.set_run_ui_state(True)

    assert ui.buttons["#apply_vu_btn"].disabled is True


def test_normalize_logging_level_falls_back_for_invalid_values():
    ui = DummyUI(web_dashboard_enabled=False)

    assert ui._normalize_logging_level("failed") == LOGGING_LEVEL_FAILED
    assert ui._normalize_logging_level("all") == LOGGING_LEVEL_ALL
    assert ui._normalize_logging_level("Failures - without payloads") == LOGGING_LEVEL_FAILED_WITHOUT_PAYLOADS
    assert ui._normalize_logging_level("Select.BLANK") == LOGGING_LEVEL_FAILED
    assert ui._normalize_logging_level("") == LOGGING_LEVEL_FAILED
    assert ui._normalize_logging_level(None) == LOGGING_LEVEL_FAILED


def test_toggle_execution_type_fields_for_external_executor():
    ui = DummyUI(web_dashboard_enabled=False, execution_type=ExecutionType.EXTERNAL_EXECUTOR.value)
    ui.execution_select.value = ExecutionType.EXTERNAL_EXECUTOR.value

    ui.toggle_execution_type_fields()

    assert ui.execution_rows["#k6_vus_row"].styles.display == "block"
    assert ui.execution_rows["#k6_maxvus_row"].styles.display == "block"
    assert ui.execution_rows["#k6_duration_row"].styles.display == "block"
    assert ui.execution_rows["#k6_rate_row"].styles.display == "none"
    assert ui.execution_rows["#k6_timeunit_row"].styles.display == "none"
    assert ui.execution_rows["#k6_preallocated_row"].styles.display == "none"
    assert ui.execution_rows["#k6_start_rate_row"].styles.display == "none"
    assert ui.execution_rows["#spike_stages_group"].styles.display == "none"
    assert ui.execution_rows["#arrival_stages_group"].styles.display == "none"
    assert ui.execution_rows["#ramping_arrival_scroll_group"].styles.display == "none"


def test_toggle_execution_type_fields_for_spike_tests():
    ui = DummyUI(web_dashboard_enabled=False, execution_type=ExecutionType.SPIKE_TESTS.value)
    ui.execution_select.value = ExecutionType.SPIKE_TESTS.value

    ui.toggle_execution_type_fields()

    assert ui.execution_rows["#k6_vus_row"].styles.display == "none"
    assert ui.execution_rows["#k6_maxvus_row"].styles.display == "none"
    assert ui.execution_rows["#k6_duration_row"].styles.display == "none"
    assert ui.execution_rows["#k6_rate_row"].styles.display == "none"
    assert ui.execution_rows["#k6_timeunit_row"].styles.display == "none"
    assert ui.execution_rows["#k6_preallocated_row"].styles.display == "none"
    assert ui.execution_rows["#k6_start_rate_row"].styles.display == "none"
    assert ui.execution_rows["#spike_stages_group"].styles.display == "block"
    assert ui.execution_rows["#arrival_stages_group"].styles.display == "none"
    assert ui.execution_rows["#ramping_arrival_scroll_group"].styles.display == "none"


def test_toggle_execution_type_fields_for_constant_vus():
    ui = DummyUI(web_dashboard_enabled=False, execution_type=ExecutionType.CONSTANT_VUS.value)
    ui.execution_select.value = ExecutionType.CONSTANT_VUS.value

    ui.toggle_execution_type_fields()

    assert ui.execution_rows["#k6_vus_row"].styles.display == "block"
    assert ui.execution_rows["#k6_maxvus_row"].styles.display == "none"
    assert ui.execution_rows["#k6_duration_row"].styles.display == "block"
    assert ui.execution_rows["#k6_rate_row"].styles.display == "none"
    assert ui.execution_rows["#k6_timeunit_row"].styles.display == "none"
    assert ui.execution_rows["#k6_preallocated_row"].styles.display == "none"
    assert ui.execution_rows["#k6_start_rate_row"].styles.display == "none"
    assert ui.execution_rows["#spike_stages_group"].styles.display == "none"
    assert ui.execution_rows["#arrival_stages_group"].styles.display == "none"
    assert ui.execution_rows["#ramping_arrival_scroll_group"].styles.display == "none"


def test_toggle_execution_type_fields_for_constant_arrival_rate():
    ui = DummyUI(web_dashboard_enabled=False, execution_type=ExecutionType.CONSTANT_ARRIVAL_RATE.value)
    ui.execution_select.value = ExecutionType.CONSTANT_ARRIVAL_RATE.value

    ui.toggle_execution_type_fields()

    assert ui.execution_rows["#k6_vus_row"].styles.display == "none"
    assert ui.execution_rows["#k6_maxvus_row"].styles.display == "block"
    assert ui.execution_rows["#k6_duration_row"].styles.display == "block"
    assert ui.execution_rows["#k6_rate_row"].styles.display == "block"
    assert ui.execution_rows["#k6_timeunit_row"].styles.display == "block"
    assert ui.execution_rows["#k6_preallocated_row"].styles.display == "block"
    assert ui.execution_rows["#k6_start_rate_row"].styles.display == "none"
    assert ui.execution_rows["#spike_stages_group"].styles.display == "none"
    assert ui.execution_rows["#arrival_stages_group"].styles.display == "none"
    assert ui.execution_rows["#ramping_arrival_scroll_group"].styles.display == "block"


def test_toggle_execution_type_fields_for_ramping_arrival_rate():
    ui = DummyUI(web_dashboard_enabled=False, execution_type=ExecutionType.RAMPING_ARRIVAL_RATE.value)
    ui.execution_select.value = ExecutionType.RAMPING_ARRIVAL_RATE.value

    ui.toggle_execution_type_fields()

    assert ui.execution_rows["#k6_vus_row"].styles.display == "none"
    assert ui.execution_rows["#k6_maxvus_row"].styles.display == "block"
    assert ui.execution_rows["#k6_duration_row"].styles.display == "none"
    assert ui.execution_rows["#k6_rate_row"].styles.display == "block"
    assert ui.execution_rows["#k6_timeunit_row"].styles.display == "block"
    assert ui.execution_rows["#k6_preallocated_row"].styles.display == "block"
    assert ui.execution_rows["#k6_start_rate_row"].styles.display == "block"
    assert ui.execution_rows["#spike_stages_group"].styles.display == "none"
    assert ui.execution_rows["#arrival_stages_group"].styles.display == "block"
    assert ui.execution_rows["#ramping_arrival_scroll_group"].styles.display == "block"


def test_on_mount_notifies_with_details_when_config_load_error_set():
    import asyncio

    ui = DummyUI(web_dashboard_enabled=False)
    ui.config_load_error = "Failed to load config."
    ui.config_load_error_details = "JSON parse error."

    asyncio.run(ui.on_mount())

    assert len(ui.notifications) == 1
    severity, message = ui.notifications[0]
    assert severity == "warning"
    assert "Failed to load config." in message
    assert "JSON parse error." in message
    assert "Using default config and leaving the source file untouched." in message


def test_on_mount_returns_early_when_request_tabs_already_exist():
    import asyncio

    ui = DummyUI(web_dashboard_enabled=False)
    ui.request_tab_panes = ["existing-pane"]
    ui.request_endpoints = [{"path": "/users"}]

    asyncio.run(ui.on_mount())

    assert ui.request_subtabs.added_panes == []
    assert ui.built_request_tabs == []


def test_on_mount_adds_request_panes_when_none_exist():
    import asyncio

    ui = DummyUI(web_dashboard_enabled=False)
    ui.request_tab_panes = []
    ui.request_endpoints = [{"path": "/users"}, {"path": "/orders"}]

    asyncio.run(ui.on_mount())

    assert len(ui.built_request_tabs) == 2
    assert ui.request_subtabs.added_panes == ui.built_request_tabs


def test_toggle_logging_fields_hides_warning_when_capabilities_are_fully_supported():
    ui = DummyUI(
        web_dashboard_enabled=False,
        capabilities=ExecutionCapabilities(
            can_stop=True,
            can_scale=True,
            can_capture_logs=True,
            can_read_metrics=True,
        ),
    )
    ui.toggle_logging_fields()

    assert ui.logging_widgets["#logging_external_mode_warning"].styles.display == "none"


def test_toggle_logging_fields_updates_warning_message_from_capabilities():
    ui = DummyUI(
        web_dashboard_enabled=False,
        capabilities=ExecutionCapabilities(
            can_stop=False,
            can_scale=True,
            can_capture_logs=False,
            can_read_metrics=True,
        ),
    )
    ui.toggle_logging_fields()

    warning_text = str(ui.logging_widgets["#logging_external_mode_warning"].renderable)
    assert "stop" in warning_text
    assert "capture logs" in warning_text


def test_sync_k6_scenario_tabs_preserves_scenario_values_after_endpoint_rename():
    import asyncio

    class ScenarioField:
        def __init__(self, widget_id, value):
            self.id = widget_id
            self.value = value

    class RequestPane:
        def __init__(self, pane_id):
            self.id = pane_id

    ui = DummyUI(web_dashboard_enabled=False)
    ui.ui_config = {
        "k6": {
            "requestMode": "parallel",
            "scenarios": [
                {"duration": "15s", "rate": 10},
                {"duration": "30s", "rate": 20},
            ],
        }
    }
    ui.request_tab_panes = [RequestPane("tab_req_endpoint_0"), RequestPane("tab_req_endpoint_1")]
    ui.scenario_widgets = [
        ScenarioField("input___k6__scenarios__1__duration", "90s"),
        ScenarioField("input___k6__scenarios__1__rate", "777"),
    ]

    def query_request_name(selector, _widget_type=None):
        if selector == "#input___requestEndpoints__0__name":
            return type("InputValue", (), {"value": "Users Renamed"})()
        if selector == "#input___requestEndpoints__1__name":
            return type("InputValue", (), {"value": "Orders"})()
        return DummyUI.query_one(ui, selector, _widget_type)

    ui.query_one = query_request_name

    asyncio.run(ui.sync_k6_scenario_tabs())

    scenario_one = ui.ui_config["k6"]["scenarios"][1]
    assert scenario_one["duration"] == "90s"
    assert scenario_one["rate"] == 777
    assert ui.k6_scenario_subtabs.active == "tab_k6_scenario_1"


def test_sync_k6_scenario_tabs_updates_only_titles_for_rename():
    import asyncio

    class RequestPane:
        def __init__(self, pane_id):
            self.id = pane_id

    ui = DummyUI(web_dashboard_enabled=False)
    ui.request_tab_panes = [RequestPane("tab_req_endpoint_0"), RequestPane("tab_req_endpoint_1")]
    ui.k6_scenario_subtabs = DummyScenarioSubtabs(["tab_k6_scenario_0", "tab_k6_scenario_1"], "tab_k6_scenario_1")
    ui.k6_scenario_subtabs.panes[0].title = "Old Users"
    ui.k6_scenario_subtabs.panes[1].title = "Old Orders"
    ui._k6_scenario_tabs_mode = "parallel"

    removed = []
    added = []

    async def remove_with_tracking(pane_id):
        removed.append(pane_id)
        await DummyScenarioSubtabs.remove_pane(ui.k6_scenario_subtabs, pane_id)

    async def add_with_tracking(pane):
        added.append(pane.id)
        await DummyScenarioSubtabs.add_pane(ui.k6_scenario_subtabs, pane)

    ui.k6_scenario_subtabs.remove_pane = remove_with_tracking
    ui.k6_scenario_subtabs.add_pane = add_with_tracking

    def query_request_name(selector, _widget_type=None):
        if selector == "#input___requestEndpoints__0__name":
            return type("InputValue", (), {"value": "Users Renamed"})()
        if selector == "#input___requestEndpoints__1__name":
            return type("InputValue", (), {"value": "Orders"})()
        return DummyUI.query_one(ui, selector, _widget_type)

    ui.query_one = query_request_name

    asyncio.run(ui.sync_k6_scenario_tabs())

    assert removed == []
    assert added == []
    assert ui.k6_scenario_subtabs.panes[0].title == "Users Renamed"
    assert ui.k6_scenario_subtabs.panes[1].title == "Orders"
    assert ui.k6_scenario_subtabs.active == "tab_k6_scenario_1"


def test_sync_k6_scenario_tabs_adds_tail_and_toggles_only_new_indexes():
    import asyncio

    class RequestPane:
        def __init__(self, pane_id):
            self.id = pane_id

    ui = DummyUI(web_dashboard_enabled=False)
    ui.request_tab_panes = [
        RequestPane("tab_req_endpoint_0"),
        RequestPane("tab_req_endpoint_1"),
        RequestPane("tab_req_endpoint_2"),
    ]
    ui.k6_scenario_subtabs = DummyScenarioSubtabs(["tab_k6_scenario_0", "tab_k6_scenario_1"], "tab_k6_scenario_1")
    ui._k6_scenario_tabs_mode = "parallel"
    toggled_indexes = []
    ui.toggle_scenario_execution_type_fields = lambda index: toggled_indexes.append(index)

    def query_request_name(selector, _widget_type=None):
        if selector == "#input___requestEndpoints__0__name":
            return type("InputValue", (), {"value": "Users"})()
        if selector == "#input___requestEndpoints__1__name":
            return type("InputValue", (), {"value": "Orders"})()
        if selector == "#input___requestEndpoints__2__name":
            return type("InputValue", (), {"value": "Payments"})()
        return DummyUI.query_one(ui, selector, _widget_type)

    ui.query_one = query_request_name

    asyncio.run(ui.sync_k6_scenario_tabs())

    assert [pane.id for pane in ui.k6_scenario_subtabs.panes] == [
        "tab_k6_scenario_0",
        "tab_k6_scenario_1",
        "tab_k6_scenario_2",
    ]
    assert toggled_indexes == [2]
    assert ui.k6_scenario_subtabs.active == "tab_k6_scenario_1"


def test_sync_k6_scenario_tabs_defaults_to_first_tab_when_active_missing():
    import asyncio

    class RequestPane:
        def __init__(self, pane_id):
            self.id = pane_id

    ui = DummyUI(web_dashboard_enabled=False)
    ui.request_tab_panes = [
        RequestPane("tab_req_endpoint_0"),
        RequestPane("tab_req_endpoint_1"),
        RequestPane("tab_req_endpoint_2"),
        RequestPane("tab_req_endpoint_3"),
        RequestPane("tab_req_endpoint_4"),
    ]
    ui.k6_scenario_subtabs = DummyScenarioSubtabs(
        [
            "tab_k6_scenario_0",
            "tab_k6_scenario_1",
            "tab_k6_scenario_2",
            "tab_k6_scenario_3",
            "tab_k6_scenario_4",
        ],
        active=None,
    )
    ui._k6_scenario_tabs_mode = "parallel"

    def query_request_name(selector, _widget_type=None):
        if selector.startswith("#input___requestEndpoints__") and selector.endswith("__name"):
            index = int(selector.split("__")[-2])
            return type("InputValue", (), {"value": f"Endpoint {index + 1}"})()
        return DummyUI.query_one(ui, selector, _widget_type)

    ui.query_one = query_request_name

    asyncio.run(ui.sync_k6_scenario_tabs())

    assert ui.k6_scenario_subtabs.active == "tab_k6_scenario_0"


def test_sync_k6_scenario_tabs_fallback_uses_first_existing_pane_id():
    import asyncio

    class RequestPane:
        def __init__(self, pane_id):
            self.id = pane_id

    ui = DummyUI(web_dashboard_enabled=False)
    ui.request_tab_panes = [RequestPane("tab_req_endpoint_0")]
    ui.request_mode_select.value = "batch"
    ui.k6_scenario_subtabs = DummyScenarioSubtabs(["custom_first"], active=None)
    ui._k6_scenario_tabs_mode = "batch"

    asyncio.run(ui.sync_k6_scenario_tabs())

    assert ui.k6_scenario_subtabs.active == "custom_first"


def test_collect_k6_scenario_fields_snapshot_uses_only_scenario_subtabs_scope(monkeypatch):
    class ScenarioField:
        def __init__(self, widget_id, value):
            self.id = widget_id
            self.value = value

    class FakeTextAreaField:
        def __init__(self, widget_id, text):
            self.id = widget_id
            self.text = text

    monkeypatch.setattr("app_mixins.ui_mixin.TextArea", FakeTextAreaField)

    ui = DummyUI(web_dashboard_enabled=False)
    ui.scenario_widgets.extend(
        [
            ScenarioField("input___k6__scenarios__0__duration", "15s"),
            FakeTextAreaField("textarea___k6__scenarios__0__notes", "scenario note"),
            ScenarioField("input___k6__executionType", "external"),  # inside container, but not scenario id
        ]
    )

    def fail_if_global_query_is_used(_selector):
        raise AssertionError("Global query should not be used for scenario snapshot")

    ui.query = fail_if_global_query_is_used

    snapshot = ui._collect_k6_scenario_fields_snapshot()

    assert snapshot == {
        "input___k6__scenarios__0__duration": "15s",
        "textarea___k6__scenarios__0__notes": "scenario note",
    }


def test_sync_k6_scenario_tabs_passes_stable_snapshot_keys_to_update_from_fields(monkeypatch):
    import asyncio

    class ScenarioField:
        def __init__(self, widget_id, value):
            self.id = widget_id
            self.value = value

    ui = DummyUI(web_dashboard_enabled=False)
    ui.scenario_widgets.extend(
        [
            ScenarioField("input___k6__scenarios__0__duration", "20s"),
            ScenarioField("input___k6__scenarios__0__rate", "33"),
        ]
    )

    captured_keys = []

    def fake_update_from_fields(config, fields):
        captured_keys.append(set(fields.keys()))
        return config

    monkeypatch.setattr("app_mixins.ui_mixin.ConfigHandler.update_from_fields", fake_update_from_fields)

    asyncio.run(ui.sync_k6_scenario_tabs())
    asyncio.run(ui.sync_k6_scenario_tabs())

    assert len(captured_keys) == 2
    assert captured_keys[0] == captured_keys[1]
    assert captured_keys[0] == {
        "input___k6__scenarios__0__duration",
        "input___k6__scenarios__0__rate",
    }
