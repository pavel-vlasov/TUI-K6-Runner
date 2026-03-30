from app_mixins.ui_mixin import UIMixin
from k6.state import ExecutionCapabilities


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
        self.updated_text = ""

    def update(self, value):
        self.updated_text = value


class DummyRequestSubtabs:
    def __init__(self):
        self.added_panes = []

    async def add_pane(self, pane):
        self.added_panes.append(pane)


class DummyUI(UIMixin):
    def __init__(
        self,
        web_dashboard_enabled: bool,
        auth_mode: str = "none",
        execution_type: str = "external executor",
        capabilities: ExecutionCapabilities | None = None,
    ):
        self.capabilities = capabilities or ExecutionCapabilities(
            can_stop=True,
            can_scale=True,
            can_capture_logs=True,
            can_read_metrics=True,
        )
        self.full_config = {
            "k6": {
                "executionType": execution_type,
                "logging": {"webDashboard": web_dashboard_enabled, "outputToUI": True},
            }
        }
        class _RC:
            def __init__(self, parent):
                self.is_running = False
                self.parent = parent

            def resolve_capabilities(self, _config):
                return self.parent.capabilities

        self.run_controller = _RC(self)
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
        self.request_tab_panes = []
        self.request_endpoints = []
        self.built_request_tabs = []
        self.notifications = []
        self.config_load_error = None
        self.config_load_error_details = None

    def query_one(self, selector, _widget_type=None):
        if selector == "#select___k6__executionType":
            return self.execution_select
        if selector == "#request_subtabs":
            return self.request_subtabs
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
    ui = DummyUI(web_dashboard_enabled=False, auth_mode="none")

    ui.toggle_auth_fields()

    assert ui.auth_rows["#auth_row__client_id"].styles.display == "none"
    assert ui.auth_rows["#auth_row__client_secret"].styles.display == "none"


def test_toggle_auth_fields_shows_client_fields_when_auth_selected():
    ui = DummyUI(web_dashboard_enabled=False, auth_mode="basic")

    ui.toggle_auth_fields()

    assert ui.auth_rows["#auth_row__client_id"].styles.display == "block"
    assert ui.auth_rows["#auth_row__client_secret"].styles.display == "block"


def test_toggle_auth_fields_shows_oauth_rows_only_for_oauth_mode():
    ui = DummyUI(web_dashboard_enabled=False, auth_mode="oauth2_client_credentials")

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


def test_toggle_logging_fields_shows_capabilities_warning_and_disables_stop_scale():
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
    assert "stop" in ui.logging_widgets["#logging_external_mode_warning"].updated_text
    assert ui.buttons["#stop_btn"].disabled is True
    assert ui.buttons["#apply_vu_btn"].disabled is True


def test_set_run_ui_state_enables_apply_when_capability_allows_scaling():
    ui = DummyUI(
        web_dashboard_enabled=False,
        execution_type="Constant VUs",
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


def test_set_run_ui_state_disables_apply_when_capability_disallows_scaling():
    ui = DummyUI(
        web_dashboard_enabled=False,
        execution_type="external executor",
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

    assert ui._normalize_logging_level("failed") == "failed"
    assert ui._normalize_logging_level("all") == "all"
    assert ui._normalize_logging_level("Failures - without payloads") == "failed_without_payloads"
    assert ui._normalize_logging_level("Select.BLANK") == "failed"
    assert ui._normalize_logging_level("") == "failed"
    assert ui._normalize_logging_level(None) == "failed"


def test_toggle_execution_type_fields_for_external_executor():
    ui = DummyUI(web_dashboard_enabled=False, execution_type="external executor")
    ui.execution_select.value = "external executor"

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
    ui = DummyUI(web_dashboard_enabled=False, execution_type="Spike Tests")
    ui.execution_select.value = "Spike Tests"

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
    ui = DummyUI(web_dashboard_enabled=False, execution_type="Constant VUs")
    ui.execution_select.value = "Constant VUs"

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
    ui = DummyUI(web_dashboard_enabled=False, execution_type="Constant Arrival Rate")
    ui.execution_select.value = "Constant Arrival Rate"

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
    ui = DummyUI(web_dashboard_enabled=False, execution_type="Ramping Arrival Rate")
    ui.execution_select.value = "Ramping Arrival Rate"

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


def test_set_run_ui_state_hides_warning_when_capabilities_unrestricted():
    ui = DummyUI(web_dashboard_enabled=False)

    ui.set_run_ui_state(False)

    assert ui.logging_widgets["#logging_external_mode_warning"].styles.display == "none"
    assert ui.logging_widgets["#logging_external_mode_warning"].updated_text == ""
