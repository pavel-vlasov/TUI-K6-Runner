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

    def clear(self):
        self.lines = []


class DummyStatusBar:
    def __init__(self):
        self.messages = []

    def update(self, _message):
        self.messages.append(_message)
        return None


class DummyButtonUI(EventsMixin):
    def __init__(
        self,
        *,
        is_running=False,
        action_save_config_result=True,
        remove_last_spike_stage_result=True,
        remove_last_arrival_stage_result=True,
    ):
        self.notifications = []
        self.scale_calls = []
        self.start_run_calls = []
        self.stop_run_calls = 0
        self.save_config_calls = []
        self.add_request_endpoint_tab_calls = 0
        self.remove_last_request_endpoint_tab_calls = 0
        self.add_spike_stage_calls = 0
        self.remove_last_spike_stage_calls = 0
        self.add_arrival_stage_calls = 0
        self.remove_last_arrival_stage_calls = 0
        self.action_save_config_calls = 0
        self.action_save_config_result = action_save_config_result
        self.remove_last_spike_stage_result = remove_last_spike_stage_result
        self.remove_last_arrival_stage_result = remove_last_arrival_stage_result
        self.set_run_ui_state = lambda *_args, **_kwargs: None
        self.runtime_config = {"runtime": True}
        self.full_config = {
            "k6": {
                "logging": {
                    "webDashboard": True,
                    "webDashboardUrl": "http://localhost:5665",
                }
            }
        }
        self.widgets = {
            "#output_log": DummyLogView(),
            "#status_bar": DummyStatusBar(),
            "#vu_input": SimpleNamespace(value=""),
        }
        self.run_controller = SimpleNamespace(
            is_running=is_running,
            start_run=self._start_run,
            stop_run=self._stop_run,
            scale=self._scale,
            save_config=self._save_config,
        )

    def query_one(self, selector, _widget_type):
        return self.widgets[selector]

    def notify(self, message, severity="information"):
        self.notifications.append((message, severity))

    async def _scale(self, vu_value, _on_log):
        self.scale_calls.append(vu_value)

    async def _start_run(self, full_config, callbacks):
        self.start_run_calls.append((full_config, callbacks))

    async def _stop_run(self):
        self.stop_run_calls += 1

    def _save_config(self, full_config):
        self.save_config_calls.append(full_config)

    def action_save_config(self):
        self.action_save_config_calls += 1
        return self.action_save_config_result

    async def add_request_endpoint_tab(self):
        self.add_request_endpoint_tab_calls += 1

    def remove_last_request_endpoint_tab(self):
        self.remove_last_request_endpoint_tab_calls += 1

    def add_spike_stage(self):
        self.add_spike_stage_calls += 1

    def remove_last_spike_stage(self):
        self.remove_last_spike_stage_calls += 1
        return self.remove_last_spike_stage_result

    def add_arrival_stage(self):
        self.add_arrival_stage_calls += 1

    def remove_last_arrival_stage(self):
        self.remove_last_arrival_stage_calls += 1
        return self.remove_last_arrival_stage_result


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


def test_on_button_pressed_web_dashboard_disabled_shows_warning():
    ui = DummyButtonUI()
    ui.full_config["k6"]["logging"]["webDashboard"] = False

    asyncio.run(ui.on_button_pressed(SimpleNamespace(button=SimpleNamespace(id="web_dashboard_btn"))))

    assert ui.notifications[-1] == ("🌐 Web Dashboard is disabled in config.", "warning")


def test_on_button_pressed_web_dashboard_not_running_shows_warning():
    ui = DummyButtonUI(is_running=False)

    asyncio.run(ui.on_button_pressed(SimpleNamespace(button=SimpleNamespace(id="web_dashboard_btn"))))

    assert ui.notifications[-1] == ("🌐 Web Dashboard is available only during a running test.", "warning")


def test_on_button_pressed_web_dashboard_running_opens_url_and_notifies(monkeypatch):
    ui = DummyButtonUI(is_running=True)
    opened = []

    monkeypatch.setattr("app_mixins.events_mixin.webbrowser.open", lambda url: opened.append(url) or True)

    asyncio.run(ui.on_button_pressed(SimpleNamespace(button=SimpleNamespace(id="web_dashboard_btn"))))

    assert len(opened) == 1
    assert opened[0].startswith("http://localhost:5665")
    assert "run=" in opened[0]
    assert ui.notifications[-1] == (f"Opening Web Dashboard: {opened[0]}", "information")


def test_on_button_pressed_run_btn_when_already_running_warns_and_returns_early():
    ui = DummyButtonUI(is_running=True)

    asyncio.run(ui.on_button_pressed(SimpleNamespace(button=SimpleNamespace(id="run_btn"))))

    assert ui.notifications[-1] == ("⛔ Test is already running. Please wait until it finishes.", "warning")
    assert ui.action_save_config_calls == 0
    assert ui.start_run_calls == []


def test_on_button_pressed_run_btn_skips_start_when_save_config_fails():
    ui = DummyButtonUI(action_save_config_result=False)

    asyncio.run(ui.on_button_pressed(SimpleNamespace(button=SimpleNamespace(id="run_btn"))))

    assert ui.action_save_config_calls == 1
    assert ui.start_run_calls == []


def test_on_button_pressed_run_btn_happy_path_clears_log_and_starts_run():
    ui = DummyButtonUI(action_save_config_result=True)
    output_log = ui.widgets["#output_log"]

    asyncio.run(ui.on_button_pressed(SimpleNamespace(button=SimpleNamespace(id="run_btn"))))

    assert output_log.lines == []
    assert ("Running K6 execution...", "information") in ui.notifications
    assert len(ui.start_run_calls) == 1
    full_config, callbacks = ui.start_run_calls[0]
    assert full_config is ui.runtime_config
    assert callable(callbacks.on_log)
    assert callable(callbacks.on_status)


def test_on_button_pressed_stop_btn_calls_stop_run_and_warns():
    ui = DummyButtonUI()

    asyncio.run(ui.on_button_pressed(SimpleNamespace(button=SimpleNamespace(id="stop_btn"))))

    assert ui.stop_run_calls == 1
    assert ui.notifications[-1] == ("Stop command sent", "warning")


def test_on_button_pressed_apply_vu_btn_zero_value_shows_error():
    ui = DummyButtonUI()
    ui.widgets["#vu_input"].value = "0"

    asyncio.run(ui.on_button_pressed(SimpleNamespace(button=SimpleNamespace(id="apply_vu_btn"))))

    assert ui.notifications[-1] == ("VU value must be at least 1.", "error")
    assert ui.scale_calls == []


def test_on_button_pressed_apply_vu_btn_valid_value_scales_and_clears_input():
    ui = DummyButtonUI()
    ui.widgets["#vu_input"].value = "10"

    asyncio.run(ui.on_button_pressed(SimpleNamespace(button=SimpleNamespace(id="apply_vu_btn"))))

    assert ui.scale_calls == [10]
    assert ui.widgets["#vu_input"].value == ""


def test_on_button_pressed_remove_last_spike_stage_warns_when_cannot_remove():
    ui = DummyButtonUI(remove_last_spike_stage_result=False)

    asyncio.run(ui.on_button_pressed(SimpleNamespace(button=SimpleNamespace(id="remove_last_spike_stage_btn"))))

    assert ui.remove_last_spike_stage_calls == 1
    assert ui.notifications[-1] == ("At least one spike stage must remain.", "warning")


def test_on_button_pressed_remove_last_arrival_stage_warns_when_cannot_remove():
    ui = DummyButtonUI(remove_last_arrival_stage_result=False)

    asyncio.run(ui.on_button_pressed(SimpleNamespace(button=SimpleNamespace(id="remove_last_arrival_stage_btn"))))

    assert ui.remove_last_arrival_stage_calls == 1
    assert ui.notifications[-1] == ("At least one arrival stage must remain.", "warning")
