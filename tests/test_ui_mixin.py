from app_mixins.ui_mixin import UIMixin


class DummyButton:
    def __init__(self):
        self.disabled = False
        self.display = True


class DummyUI(UIMixin):
    def __init__(self, web_dashboard_enabled: bool):
        self.full_config = {"k6": {"logging": {"webDashboard": web_dashboard_enabled}}}
        self.buttons = {
            "#run_btn": DummyButton(),
            "#stop_btn": DummyButton(),
            "#apply_vu_btn": DummyButton(),
            "#web_dashboard_btn": DummyButton(),
        }

    def query_one(self, selector, _widget_type):
        return self.buttons[selector]


def test_web_dashboard_button_disabled_when_not_running():
    ui = DummyUI(web_dashboard_enabled=True)

    ui.set_run_ui_state(False)

    assert ui.buttons["#web_dashboard_btn"].disabled is True


def test_web_dashboard_button_hidden_and_disabled_when_feature_off():
    ui = DummyUI(web_dashboard_enabled=False)

    ui.set_run_ui_state(True)

    assert ui.buttons["#web_dashboard_btn"].display is False
    assert ui.buttons["#web_dashboard_btn"].disabled is True
