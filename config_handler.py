import copy
import json
import os
from collections.abc import Mapping


class ConfigHandler:
    @staticmethod
    def update_from_fields(current_config: dict, field_values: Mapping[str, object]) -> dict:
        new_config = copy.deepcopy(current_config)

        def is_int_key(part: str) -> bool:
            return part.isdigit()

        def normalize_value(value: object) -> object:
            if not isinstance(value, str):
                return value

            cleaned = "".join(ch for ch in value if ch.isprintable() or ch in "\n\r\t")
            stripped = cleaned.strip()

            try:
                if (stripped.startswith("{") and stripped.endswith("}")) or (
                    stripped.startswith("[") and stripped.endswith("]")
                ):
                    return json.loads(stripped)
                if stripped.isdigit():
                    return int(stripped)
            except Exception:
                pass

            return cleaned

        def set_by_path(data: dict, path: str, value: object) -> None:
            keys = path.split("__")
            current = data
            normalized = normalize_value(value)

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
                        current[idx] = normalized
                        return

                    if not isinstance(current[idx], (dict, list)):
                        current[idx] = [] if is_int_key(next_key) else {}
                    current = current[idx]
                    continue

                if not isinstance(current, dict):
                    return

                if last:
                    current[key] = normalized
                    return

                if key not in current or not isinstance(current[key], (dict, list)):
                    current[key] = [] if is_int_key(next_key) else {}
                current = current[key]

        for widget_id, widget_value in field_values.items():
            if "___" not in widget_id:
                continue

            _, path = widget_id.split("___", 1)
            if not path or path == "vu_input":
                continue

            set_by_path(new_config, path, widget_value)

        return new_config

    @staticmethod
    def save_to_file(config: dict, filename: str = "test_config.json") -> None:
        try:
            data = json.dumps(config, indent=4, ensure_ascii=False)

            with open(filename, "w", encoding="utf-8") as f:
                f.write(data)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    pass
        except Exception as e:
            print(f"Error while saving file: {e}")
