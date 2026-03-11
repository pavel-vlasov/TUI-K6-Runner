from textual.containers import Horizontal, Vertical
from textual.widgets import Input, Select, Switch, TextArea

from ui_components import build_config_fields, get_valid_id


def test_get_valid_id_replaces_dots():
    assert get_valid_id("a.b.c") == "input___a__b__c"
    assert get_valid_id("x.y", prefix="bool") == "bool___x__y"


def test_build_config_fields_orders_request_name_and_method_first():
    data = {"path": "/x", "method": "GET", "name": "ep", "headers": {"A": "1"}}

    fields = build_config_fields(data, "requestEndpoints.0")

    first = fields[0]
    second = fields[1]
    assert isinstance(first, Horizontal)
    assert isinstance(second, Horizontal)
    assert isinstance(first._pending_children[1], Input)
    assert first._pending_children[1].id.endswith("__name")
    assert isinstance(second._pending_children[1], Select)


def test_build_config_fields_supports_multiline_and_bool_and_logging_level():
    data = {
        "headers": {"A": "1"},
        "enabled": True,
        "level": "failed",
    }

    fields = build_config_fields(data, "k6.logging")

    multiline = next(field for field in fields if isinstance(field, Vertical))
    textarea = multiline._pending_children[1]
    assert isinstance(textarea, TextArea)
    assert textarea.show_line_numbers is False
    assert textarea.highlight_cursor_line is False

    switch_row = next(field for field in fields if isinstance(field, Horizontal) and isinstance(field._pending_children[1], Switch))
    assert switch_row._pending_children[1].id.startswith("bool___")

    level_row = next(field for field in fields if isinstance(field, Horizontal) and isinstance(field._pending_children[1], Select))
    options = dict(level_row._pending_children[1]._options)
    assert options["failed"] == "failed"
