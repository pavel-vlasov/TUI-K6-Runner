from app_mixins.ui_mixin import UIMixin


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


class DummyUI(UIMixin):
    def __init__(self, web_dashboard_enabled: bool, auth_mode: str = "none"):
        self.full_config = {"k6": {"logging": {"webDashboard": web_dashboard_enabled, "outputToUI": True}}}
        self.run_controller = type("RC", (), {"is_running": False})()
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

    def query_one(self, selector, _widget_type):
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


def test_toggle_logging_fields_shows_external_mode_warning_and_disables_stop_scale():
    ui = DummyUI(web_dashboard_enabled=False)
    ui.run_controller.is_running = True
    ui.logging_selects["#select___k6__logging__outputToUI"].value = False

    ui.toggle_logging_fields()

    assert ui.logging_widgets["#logging_external_mode_warning"].styles.display == "block"
    assert ui.buttons["#stop_btn"].disabled is True
    assert ui.buttons["#apply_vu_btn"].disabled is True


def test_normalize_logging_level_falls_back_for_invalid_values():
    ui = DummyUI(web_dashboard_enabled=False)

    assert ui._normalize_logging_level("failed") == "failed"
    assert ui._normalize_logging_level("all") == "all"
    assert ui._normalize_logging_level("Failures - without payloads") == "failed_without_payloads"
    assert ui._normalize_logging_level("Select.BLANK") == "failed"
    assert ui._normalize_logging_level("") == "failed"
    assert ui._normalize_logging_level(None) == "failed"
