import ui_components as uc
from constants import HTTP_METHODS


class FakeLabel:
    def __init__(self, text, classes=None):
        self.text = text
        self.classes = classes


class FakeInput:
    def __init__(self, value, id=None, placeholder=None):
        self.value = value
        self.id = id
        self.placeholder = placeholder


class FakeSwitch:
    def __init__(self, value, id=None):
        self.value = value
        self.id = id


class FakeSelect:
    def __init__(self, options, value=None, id=None):
        self.options = options
        self.value = value
        self.id = id


class FakeTextArea:
    def __init__(self, value, id=None, language=None, soft_wrap=False):
        self.value = value
        self.id = id
        self.language = language
        self.soft_wrap = soft_wrap
        self.show_line_numbers = True
        self.highlight_cursor_line = True


class FakeRow:
    def __init__(self, *children, classes=None):
        self.children = list(children)
        self.classes = classes


def _patch_ui_components(monkeypatch):
    monkeypatch.setattr(uc, "Label", FakeLabel)
    monkeypatch.setattr(uc, "Input", FakeInput)
    monkeypatch.setattr(uc, "Switch", FakeSwitch)
    monkeypatch.setattr(uc, "Select", FakeSelect)
    monkeypatch.setattr(uc, "TextArea", FakeTextArea)
    monkeypatch.setattr(uc, "Horizontal", FakeRow)
    monkeypatch.setattr(uc, "Vertical", FakeRow)


def test_get_valid_id_replaces_dots():
    assert uc.get_valid_id("a.b.c") == "input___a__b__c"
    assert uc.get_valid_id("x.y", prefix="bool") == "bool___x__y"


def test_build_config_fields_orders_request_name_and_method_first(monkeypatch):
    _patch_ui_components(monkeypatch)
    data = {"path": "/x", "method": "GET", "name": "ep", "headers": {"A": "1"}}

    fields = uc.build_config_fields(data, "requestEndpoints.0")

    first = fields[0]
    second = fields[1]
    assert isinstance(first.children[1], FakeInput)
    assert first.children[1].id.endswith("__name")
    assert isinstance(second.children[1], FakeSelect)


def test_build_config_fields_supports_multiline_and_bool_and_logging_level(monkeypatch):
    _patch_ui_components(monkeypatch)
    data = {
        "headers": {"A": "1"},
        "enabled": True,
        "level": "failed",
    }

    fields = uc.build_config_fields(data, "k6.logging")

    multiline = next(field for field in fields if isinstance(field.children[1], FakeTextArea))
    textarea = multiline.children[1]
    assert textarea.show_line_numbers is False
    assert textarea.highlight_cursor_line is False

    switch_row = next(field for field in fields if isinstance(field.children[1], FakeSwitch))
    assert switch_row.children[1].id.startswith("bool___")

    level_row = next(field for field in fields if isinstance(field.children[1], FakeSelect))
    assert ("failed", "failed") in level_row.children[1].options
    assert ("Failures - without payloads", "Failures - without payloads") in level_row.children[1].options


def test_ui_method_select_uses_same_http_methods_as_validation(monkeypatch):
    _patch_ui_components(monkeypatch)
    fields = uc.build_config_fields({"method": "GET"}, "requestEndpoints.0")
    method_row = fields[0]
    options = [value for _, value in method_row.children[1].options]
    assert tuple(options) == HTTP_METHODS
