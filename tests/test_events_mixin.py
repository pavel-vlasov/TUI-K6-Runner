import asyncio
from types import SimpleNamespace

from app_mixins.events_mixin import EventsMixin


class DummySwitch:
    def __init__(self, switch_id, value=False):
        self.id = switch_id
        self.value = value


class DummyEventsUI(EventsMixin):
    def __init__(self):
        self.switches = {}
        self.auth_toggle_count = 0
        self.logging_toggle_count = 0
        self.notifications = []
        self.full_config = {
            "k6": {
                "logging": {
                    "webDashboard": True,
                    "webDashboardUrl": "http://localhost:5665",
                }
            }
        }
        self.run_controller = SimpleNamespace(is_running=True)

    def query_one(self, selector, _widget_type):
        return self.switches[selector]

    def toggle_auth_fields(self):
        self.auth_toggle_count += 1

    def toggle_logging_fields(self):
        self.logging_toggle_count += 1

    def notify(self, message, severity="information"):
        self.notifications.append((message, severity))


class DummyLogLine:
    def __init__(self, text):
        self.text = text


class DummyLogView:
    def __init__(self):
        self.lines = [DummyLogLine("line 1"), DummyLogLine("line 2")]

    def write(self, _message):
        return None


class DummyStatusBar:
    def update(self, _message):
        return None


class DummyButtonUI(EventsMixin):
    def __init__(self):
        self.notifications = []
        self.scale_calls = []
        self.widgets = {
            "#output_log": DummyLogView(),
            "#status_bar": DummyStatusBar(),
            "#vu_input": SimpleNamespace(value=""),
        }
        self.run_controller = SimpleNamespace(is_running=False, scale=self._scale)

    def query_one(self, selector, _widget_type):
        return self.widgets[selector]

    def notify(self, message, severity="information"):
        self.notifications.append((message, severity))

    async def _scale(self, vu_value, _on_log):
        self.scale_calls.append(vu_value)


def test_on_switch_changed_no_auth_disables_other_auth_modes():
    ui = DummyEventsUI()
    event = SimpleNamespace(select=SimpleNamespace(id="select___auth__mode"))

    ui.on_select_changed(event)

    assert ui.auth_toggle_count == 1


def test_with_cache_busting_query_keeps_existing_params():
    ui = DummyEventsUI()

    result = ui._with_cache_busting_query("http://localhost:5665/path?a=1")

    assert "a=1" in result
    assert "run=" in result


def test_on_switch_changed_toggles_logging_fields_for_logging_switches():
    ui = DummyEventsUI()
    event = SimpleNamespace(
        switch=SimpleNamespace(id="bool___k6__logging__enabled"), value=True
    )

    ui.on_switch_changed(event)

    assert ui.logging_toggle_count == 1


def test_on_button_pressed_web_dashboard_rejects_invalid_url(monkeypatch):
    ui = DummyEventsUI()
    ui.full_config["k6"]["logging"]["webDashboardUrl"] = "bad-url"
    ui.run_controller = SimpleNamespace(is_running=True)
    event = SimpleNamespace(button=SimpleNamespace(id="web_dashboard_btn"))
    monkeypatch.setattr("app_mixins.events_mixin.webbrowser.open", lambda _url: True)

    asyncio.run(ui.on_button_pressed(event))

    assert ui.notifications[-1][1] == "error"
    assert "Web Dashboard URL is invalid" in ui.notifications[-1][0]


def test_on_button_pressed_web_dashboard_uses_public_url_validator(monkeypatch):
    ui = DummyEventsUI()
    ui.full_config["k6"]["logging"]["webDashboardUrl"] = "http://localhost:5665"
    event = SimpleNamespace(button=SimpleNamespace(id="web_dashboard_btn"))
    monkeypatch.setattr("app_mixins.events_mixin.webbrowser.open", lambda _url: True)
    monkeypatch.setattr("app_mixins.events_mixin.ConfigHandler.is_valid_http_url", lambda _url: False)

    asyncio.run(ui.on_button_pressed(event))

    assert ui.notifications[-1][1] == "error"
    assert "Web Dashboard URL is invalid" in ui.notifications[-1][0]


def test_on_button_pressed_copy_btn_notify_warning_when_clipboard_copy_fails(
    monkeypatch,
):
    ui = DummyButtonUI()
    event = SimpleNamespace(button=SimpleNamespace(id="copy_btn"))

    def failing_copy(_value):
        raise RuntimeError("clipboard unavailable")

    monkeypatch.setattr("app_mixins.events_mixin.pyperclip.copy", failing_copy)

    asyncio.run(ui.on_button_pressed(event))

    assert ui.notifications[-1][1] == "warning"
    assert "clipboard backend" in ui.notifications[-1][0]


def test_on_button_pressed_apply_vu_btn_invalid_input_shows_warning_and_does_not_scale():
    ui = DummyButtonUI()
    ui.widgets["#vu_input"].value = "abc"
    event = SimpleNamespace(button=SimpleNamespace(id="apply_vu_btn"))

    asyncio.run(ui.on_button_pressed(event))

    assert ui.notifications[-1] == ("Please enter a valid VU value (positive integer).", "warning")
    assert ui.scale_calls == []
