# ui_components.py
import json
from textual.widgets import Label, Switch, Select, Input, TextArea
from textual.containers import Horizontal, Vertical
from constants import HTTP_METHODS


def get_valid_id(key_path, prefix="input"):
    safe_path = key_path.replace(".", "__")
    return f"{prefix}___{safe_path}"


def build_config_fields(data, parent_path):
    items = []

    ordered_items = list(data.items())
    if parent_path.startswith("requestEndpoints."):
        priority = {"name": 0, "method": 1}
        position = {key: idx for idx, key in enumerate(data.keys())}
        ordered_items.sort(
            key=lambda item: (priority.get(item[0], 2), position[item[0]])
        )

    for k, v in ordered_items:
        multiline_keys = ["headers", "body", "query", "thresholds"]

        if isinstance(v, dict) and k not in multiline_keys:
            continue

        full_key = f"{parent_path}.{k}"

        if k in multiline_keys:
            val_str = (
                json.dumps(v, indent=2, ensure_ascii=False)
                if isinstance(v, (dict, list))
                else str(v)
            )

            ta_widget = TextArea(
                val_str,
                id=get_valid_id(full_key, "input"),
                language="json",
            )
            if hasattr(ta_widget, "soft_wrap"):
                ta_widget.soft_wrap = True
            ta_widget.show_line_numbers = False
            ta_widget.highlight_cursor_line = False

            items.append(
                Vertical(Label(f"{k}:"), ta_widget, classes="field-row-multiline")
            )

        elif isinstance(v, bool):
            label = Label(f"{k}:", classes="field-label")
            widget = Switch(v, id=get_valid_id(full_key, "bool"))
            items.append(Horizontal(label, widget, classes="field-row"))

        elif (
            k == "method"
            or (k == "level" and parent_path == "k6.logging")
            or (k == "mode" and parent_path == "auth")
        ):
            label = Label(f"{k}:", classes="field-label")
            if k == "method":
                options = list(HTTP_METHODS)
            elif k == "mode":
                options = [
                    "none",
                    "oauth2_client_credentials",
                    "basic",
                    "client_id_enforcement",
                ]
            else:
                options = ["all", "failed", "Failures - without payloads"]
            widget = Select(
                [(o, o) for o in options], value=v, id=get_valid_id(full_key, "select")
            )
            items.append(Horizontal(label, widget, classes="field-row"))

        else:
            label = Label(f"{k}:", classes="field-label")
            val_str = str(v)
            widget = Input(val_str, id=get_valid_id(full_key, "input"))
            items.append(Horizontal(label, widget, classes="field-row"))

    return items
