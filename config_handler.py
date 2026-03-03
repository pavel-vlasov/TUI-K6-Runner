import json
import os
import copy
from textual.widgets import TextArea

class ConfigHandler:
    @staticmethod
    def update_from_ui(app, current_config: dict) -> dict:
        new_config = copy.deepcopy(current_config)

        def is_int_key(part: str) -> bool:
            return part.isdigit()

        def set_by_path(d, path, value):
            keys = path.split('__')

            if isinstance(value, str):
                value = "".join(ch for ch in value if ch.isprintable() or ch in "\n\r\t")
                stripped = value.strip()
                
                try:
                    if (stripped.startswith('{') and stripped.endswith('}')) or \
                       (stripped.startswith('[') and stripped.endswith(']')):
                        value = json.loads(stripped)
                    elif stripped.isdigit():
                        value = int(stripped)
                except:
                    pass

            current = d
            for i, key in enumerate(keys):
                last = i == len(keys) - 1
                next_key = keys[i + 1] if not last else None

                if isinstance(current, list):
                    if not is_int_key(key):
                        return
                    idx = int(key)
                    while len(current) <= idx:
                        current.append({})

                    if last:
                        current[idx] = value
                        return

                    if not isinstance(current[idx], (dict, list)):
                        current[idx] = [] if is_int_key(next_key) else {}
                    current = current[idx]
                    continue

                if not isinstance(current, dict):
                    return

                if last:
                    current[key] = value
                    return

                if key not in current or not isinstance(current[key], (dict, list)):
                    current[key] = [] if is_int_key(next_key) else {}
                current = current[key]


        for widget in app.query("Input, Switch, Select, TextArea"):
            if not widget.id or "___" not in widget.id:
                continue
            
            prefix, path = widget.id.split("___", 1)
            
            if not path or path == "vu_input":
                continue

            if isinstance(widget, TextArea):
                current_value = widget.text
            else:
                current_value = widget.value

            set_by_path(new_config, path, current_value)
            
        return new_config

    @staticmethod
    def save_to_file(config, filename="test_config.json"):
        try:
            data = json.dumps(config, indent=4, ensure_ascii=False)
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write(data)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except:
                    pass
        except Exception as e:
            print(f"Error while saving file: {e}")
