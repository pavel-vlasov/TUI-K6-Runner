from types import SimpleNamespace
import asyncio

from app_mixins.events_mixin import EventsMixin


class DummySwitch:
    def __init__(self, switch_id, value=False):
        self.id = switch_id
        self.value = value


class DummyEventsUI(EventsMixin):
    def __init__(self):
        self.switches = {
            "#bool___auth__useOAuth2": DummySwitch("bool___auth__useOAuth2", True),
            "#bool___auth__basicauth": DummySwitch("bool___auth__basicauth", True),
            "#bool___auth__ClientId_Enforcement": DummySwitch("bool___auth__ClientId_Enforcement", True),
            "#auth_noauth_switch": DummySwitch("auth_noauth_switch", False),
        }
        self.toggle_count = 0
        self.logging_toggle_count = 0
        self.notifications = []

    def query_one(self, selector, _widget_type):
        return self.switches[selector]

    def toggle_auth_fields(self):
        self.toggle_count += 1

    def toggle_logging_fields(self):
        self.logging_toggle_count += 1

    def notify(self, message, severity="information"):
        self.notifications.append((message, severity))


def test_on_switch_changed_no_auth_disables_other_auth_modes():
    ui = DummyEventsUI()
    event = SimpleNamespace(switch=SimpleNamespace(id="auth_noauth_switch"), value=True)

    ui.on_switch_changed(event)

    assert ui.switches["#bool___auth__useOAuth2"].value is False
    assert ui.switches["#bool___auth__basicauth"].value is False
    assert ui.switches["#bool___auth__ClientId_Enforcement"].value is False
    assert ui.toggle_count == 1


def test_on_switch_changed_auth_mode_disables_no_auth_and_other_modes():
    ui = DummyEventsUI()
    event = SimpleNamespace(switch=SimpleNamespace(id="bool___auth__useOAuth2"), value=True)

    ui.on_switch_changed(event)

    assert ui.switches["#auth_noauth_switch"].value is False
    assert ui.switches["#bool___auth__basicauth"].value is False
    assert ui.switches["#bool___auth__ClientId_Enforcement"].value is False
    assert ui.toggle_count == 1


def test_with_cache_busting_query_keeps_existing_params():
    ui = DummyEventsUI()

    result = ui._with_cache_busting_query("http://localhost:5665/path?a=1")

    assert "a=1" in result
    assert "run=" in result


def test_on_switch_changed_prevents_disabling_all_auth_modes():
    ui = DummyEventsUI()
    ui.switches["#auth_noauth_switch"].value = False
    ui.switches["#bool___auth__useOAuth2"].value = False
    ui.switches["#bool___auth__ClientId_Enforcement"].value = False
    ui.switches["#bool___auth__basicauth"].value = False
    event = SimpleNamespace(switch=ui.switches["#bool___auth__basicauth"], value=False)

    ui.on_switch_changed(event)

    assert ui.switches["#bool___auth__basicauth"].value is True
    assert ui.notifications[-1][1] == "warning"


def test_on_switch_changed_toggles_logging_fields_for_logging_switches():
    ui = DummyEventsUI()
    event = SimpleNamespace(switch=SimpleNamespace(id="bool___k6__logging__enabled"), value=True)

    ui.on_switch_changed(event)

    assert ui.logging_toggle_count == 1


class DummyLogView:
    def __init__(self):
        self.cleared = 0
        self.lines = []

    def clear(self):
        self.cleared += 1

    def write(self, message):
        self.lines.append(message)


class DummyStatusBar:
    def __init__(self):
        self.messages = []

    def update(self, message):
        self.messages.append(message)


class DummyRunController:
    def __init__(self, ui):
        self.is_running = False
        self.ui = ui

    async def start_run(self, _config, callbacks):
        self.ui.events.append(("start_run", list(self.ui.run_state_updates)))
        callbacks.on_run_state_changed(True)
        callbacks.on_run_state_changed(False)

    async def stop_run(self):
        return None

    async def scale(self, _vus, _on_log):
        return None


class DummyEventsRunUI(EventsMixin):
    def __init__(self):
        self.full_config = {"k6": {"logging": {}}}
        self.log_view = DummyLogView()
        self.status_bar = DummyStatusBar()
        self.notifications = []
        self.run_state_updates = []
        self.events = []
        self.run_controller = DummyRunController(self)

    def query_one(self, selector, _widget_type):
        if selector == "#output_log":
            return self.log_view
        if selector == "#status_bar":
            return self.status_bar
        raise KeyError(selector)

    def action_save_config(self):
        self.events.append(("save", None))
        return True

    def set_run_ui_state(self, running: bool):
        self.run_state_updates.append(running)
        self.events.append(("state", running))

    def notify(self, message, severity="information"):
        self.notifications.append((message, severity))


def test_run_button_updates_ui_only_via_run_state_callback():
    ui = DummyEventsRunUI()
    event = SimpleNamespace(button=SimpleNamespace(id="run_btn"))

    asyncio.run(ui.on_button_pressed(event))

    assert ui.run_state_updates == [True, False]
    assert ui.events == [("save", None), ("start_run", []), ("state", True), ("state", False)]
    assert ui.log_view.cleared == 1
