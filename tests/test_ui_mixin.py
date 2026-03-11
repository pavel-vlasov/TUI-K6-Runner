from app_mixins.ui_mixin import UIMixin


class DummyButton:
    def __init__(self):
        self.disabled = False
        self.display = True


class DummySwitch:
    def __init__(self, value=False):
        self.value = value


class DummyStyles:
    def __init__(self):
        self.display = "block"


class DummyRow:
    def __init__(self):
        self.styles = DummyStyles()


class DummyUI(UIMixin):
    def __init__(self, web_dashboard_enabled: bool, use_oauth2: bool = False, no_auth: bool = False):
        self.full_config = {"k6": {"logging": {"webDashboard": web_dashboard_enabled}}}
        self.buttons = {
            "#run_btn": DummyButton(),
            "#stop_btn": DummyButton(),
            "#apply_vu_btn": DummyButton(),
            "#web_dashboard_btn": DummyButton(),
        }
        self.auth_switches = {
            "#bool___auth__useOAuth2": DummySwitch(use_oauth2),
            "#auth_noauth_switch": DummySwitch(no_auth),
        }
        self.auth_rows = {
            "#auth_row__client_id": DummyRow(),
            "#auth_row__client_secret": DummyRow(),
            "#auth_oauth_row__token_url": DummyRow(),
            "#auth_oauth_row__scope": DummyRow(),
        }

    def query_one(self, selector, _widget_type):
        if selector in self.buttons:
            return self.buttons[selector]
        if selector in self.auth_switches:
            return self.auth_switches[selector]
        if selector in self.auth_rows:
            return self.auth_rows[selector]
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
    ui = DummyUI(web_dashboard_enabled=False, no_auth=True)

    ui.toggle_auth_fields()

    assert ui.auth_rows["#auth_row__client_id"].styles.display == "none"
    assert ui.auth_rows["#auth_row__client_secret"].styles.display == "none"


def test_toggle_auth_fields_shows_client_fields_when_auth_selected():
    ui = DummyUI(web_dashboard_enabled=False, no_auth=False)

    ui.toggle_auth_fields()

    assert ui.auth_rows["#auth_row__client_id"].styles.display == "block"
    assert ui.auth_rows["#auth_row__client_secret"].styles.display == "block"
