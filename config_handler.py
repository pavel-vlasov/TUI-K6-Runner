import json
import os
import copy
from textual.widgets import TextArea

class ConfigHandler:
    @staticmethod
    def update_from_ui(app, current_config: dict) -> dict:
        new_config = copy.deepcopy(current_config)

        def set_by_path(d, path, value):
            keys = path.split('__') 
            for key in keys[:-1]:
                if key not in d or not isinstance(d[key], dict):
                    d[key] = {}
                d = d[key]
            
            last_key = keys[-1]
            
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
            
            d[last_key] = value


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
