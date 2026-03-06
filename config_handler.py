import copy
import json
import os
import tempfile
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
    def build_runtime_config(config: dict) -> dict:
        runtime = {
            "baseURL": str(config.get("baseURL", "")).strip(),
            "auth": ConfigHandler._build_auth_config(config.get("auth", {})),
            "requestEndpoints": ConfigHandler._build_request_endpoints(config.get("requestEndpoints", [])),
            "k6": ConfigHandler._build_k6_config(config.get("k6", {})),
        }

        return runtime

    @staticmethod
    def validate_runtime_config(config: dict) -> list[str]:
        errors: list[str] = []

        if not str(config.get("baseURL", "")).strip():
            errors.append("baseURL is required.")

        auth = config.get("auth", {})
        auth_modes = [
            bool(auth.get("useOAuth2")),
            bool(auth.get("basicauth")),
            bool(auth.get("ClientId_Enforcement")),
        ]
        if sum(auth_modes) != 1:
            errors.append("Exactly one auth mode must be enabled.")

        if not str(auth.get("client_id", "")).strip() or not str(auth.get("client_secret", "")).strip():
            errors.append("auth.client_id and auth.client_secret are required.")

        if auth.get("useOAuth2"):
            if not str(auth.get("token_url", "")).strip():
                errors.append("auth.token_url is required when OAuth2 is enabled.")
            if not str(auth.get("scope", "")).strip():
                errors.append("auth.scope is required when OAuth2 is enabled.")

        endpoints = config.get("requestEndpoints", [])
        if not isinstance(endpoints, list) or not endpoints:
            errors.append("At least one request endpoint is required.")
        else:
            for idx, endpoint in enumerate(endpoints, start=1):
                if not str(endpoint.get("name", "")).strip():
                    errors.append(f"requestEndpoints[{idx}].name is required.")
                if not str(endpoint.get("path", "")).strip():
                    errors.append(f"requestEndpoints[{idx}].path is required.")
                method = str(endpoint.get("method", "")).upper()
                if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}:
                    errors.append(f"requestEndpoints[{idx}].method is invalid: {method}.")

        k6cfg = config.get("k6", {})
        execution_type = str(k6cfg.get("executionType", "")).strip()
        if not execution_type:
            errors.append("k6.executionType is required.")

        thresholds = k6cfg.get("thresholds")
        threshold_error = ConfigHandler._validate_thresholds(thresholds)
        if threshold_error:
            errors.append(threshold_error)

        return errors

    @staticmethod
    def save_to_file(config: dict, filename: str = "test_config.json") -> None:
        data = json.dumps(config, indent=4, ensure_ascii=False)
        directory = os.path.dirname(os.path.abspath(filename)) or "."

        temp_name = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory, delete=False) as tmp_file:
                temp_name = tmp_file.name
                tmp_file.write(data)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())

            os.replace(temp_name, filename)
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)

    @staticmethod
    def _build_auth_config(auth: object) -> dict:
        source = auth if isinstance(auth, dict) else {}
        runtime = {
            "useOAuth2": bool(source.get("useOAuth2", False)),
            "basicauth": bool(source.get("basicauth", False)),
            "ClientId_Enforcement": bool(source.get("ClientId_Enforcement", False)),
            "client_id": str(source.get("client_id", "")).strip(),
            "client_secret": str(source.get("client_secret", "")).strip(),
        }
        if runtime["useOAuth2"]:
            runtime["token_url"] = str(source.get("token_url", "")).strip()
            runtime["scope"] = str(source.get("scope", "")).strip()
        return runtime

    @staticmethod
    def _build_request_endpoints(endpoints: object) -> list[dict]:
        if not isinstance(endpoints, list):
            return []

        runtime_endpoints: list[dict] = []
        for index, endpoint in enumerate(endpoints, start=1):
            if not isinstance(endpoint, dict):
                continue
            method = str(endpoint.get("method", "GET")).upper()
            runtime_endpoints.append(
                {
                    "name": str(endpoint.get("name", f"Endpoint {index}")).strip() or f"Endpoint {index}",
                    "method": method,
                    "path": str(endpoint.get("path", "")).strip(),
                    "headers": endpoint.get("headers", {}) if isinstance(endpoint.get("headers", {}), dict) else {},
                    "body": endpoint.get("body"),
                    "query": endpoint.get("query"),
                }
            )
        return runtime_endpoints

    @staticmethod
    def _build_k6_config(k6cfg: object) -> dict:
        source = k6cfg if isinstance(k6cfg, dict) else {}
        execution_type = str(source.get("executionType", "external executor"))

        runtime = {
            "executionType": execution_type,
            "thresholds": source.get("thresholds", {}),
            "logging": ConfigHandler._build_logging_config(source.get("logging", {})),
        }

        if execution_type == "Spike Tests":
            runtime["spikeStages"] = source.get("spikeStages", [])
        elif execution_type == "Constant VUs":
            runtime["vus"] = source.get("vus", 1)
            runtime["duration"] = source.get("duration", "60s")
        elif execution_type == "Constant Arrival Rate":
            runtime["rate"] = source.get("rate", 10)
            runtime["timeUnit"] = source.get("timeUnit", "1s")
            runtime["duration"] = source.get("duration", "60s")
            runtime["preAllocatedVUs"] = source.get("preAllocatedVUs", 10)
            runtime["maxVUs"] = source.get("maxVUs", 50)
        elif execution_type == "Ramping Arrival Rate":
            runtime["startRate"] = source.get("startRate", 1)
            runtime["timeUnit"] = source.get("timeUnit", "1s")
            runtime["preAllocatedVUs"] = source.get("preAllocatedVUs", 10)
            runtime["maxVUs"] = source.get("maxVUs", 50)
            runtime["rampingArrivalStages"] = source.get("rampingArrivalStages", [])
        else:
            runtime["vus"] = source.get("vus", 1)
            runtime["maxVUs"] = source.get("maxVUs", 50)
            runtime["duration"] = source.get("duration", "60s")

        return runtime

    @staticmethod
    def _build_logging_config(logging_cfg: object) -> dict:
        source = logging_cfg if isinstance(logging_cfg, dict) else {}
        return {
            "enabled": bool(source.get("enabled", False)),
            "level": str(source.get("level", "failed")),
            "outputToUI": bool(source.get("outputToUI", True)),
            "webDashboard": bool(source.get("webDashboard", False)),
            "webDashboardUrl": str(source.get("webDashboardUrl", "http://localhost:5665")).strip(),
            "htmlSummaryReport": bool(source.get("htmlSummaryReport", False)),
        }

    @staticmethod
    def _validate_thresholds(thresholds: object) -> str | None:
        if not isinstance(thresholds, dict) or not thresholds:
            return "k6.thresholds must be a non-empty JSON object."

        for metric, rules in thresholds.items():
            if not str(metric).strip():
                return "k6.thresholds contains an empty metric name."
            if not isinstance(rules, list) or not rules:
                return f"k6.thresholds.{metric} must be a non-empty list."

            for rule in rules:
                if isinstance(rule, str):
                    if not rule.strip():
                        return f"k6.thresholds.{metric} contains an empty string rule."
                    continue
                if isinstance(rule, dict):
                    if not str(rule.get("threshold", "")).strip():
                        return f"k6.thresholds.{metric} has a rule with empty 'threshold'."
                    continue
                return f"k6.thresholds.{metric} has an invalid rule type: {type(rule).__name__}."

        return None
