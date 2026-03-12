from types import SimpleNamespace

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
