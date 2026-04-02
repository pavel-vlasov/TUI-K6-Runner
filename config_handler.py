import copy
import json
import os
import re
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlparse

from jsonschema import Draft202012Validator, FormatChecker

from constants import (
    AUTH_MODES,
    DEFAULT_CONFIG_PATH,
    HTTP_METHODS,
    LOGGING_LEVEL_FAILED,
    LOGGING_LEVELS,
    AuthMode,
    EXECUTION_TYPES,
    ExecutionType,
    RequestMode,
    normalize_logging_level,
)

K6_DURATION_RE = re.compile(r"^\d+(ms|s|m|h)$")
SCHEMA_PATH = Path(__file__).resolve().parent / "schema" / "test_config.schema.json"
with SCHEMA_PATH.open("r", encoding="utf-8") as schema_file:
    TEST_CONFIG_SCHEMA = json.load(schema_file)
TEST_CONFIG_VALIDATOR = Draft202012Validator(TEST_CONFIG_SCHEMA, format_checker=FormatChecker())


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
        schema_errors = ConfigHandler.validate_against_schema(config)
        errors: list[str] = list(schema_errors)
        errors.extend(ConfigHandler._validate_base_url(config.get("baseURL", "")))
        errors.extend(ConfigHandler._validate_auth(config.get("auth", {})))

        endpoints = config.get("requestEndpoints", [])
        if not isinstance(endpoints, list) or not endpoints:
            errors.append("At least one request endpoint is required.")
        else:
            for idx, endpoint in enumerate(endpoints):
                errors.extend(ConfigHandler._validate_request_endpoint(endpoint, idx))

        errors.extend(ConfigHandler._validate_k6_config(config.get("k6", {})))
        return list(dict.fromkeys(errors))

    @staticmethod
    def validate_against_schema(config: dict) -> list[str]:
        normalized_errors: dict[tuple[str, str], str] = {}
        for error in sorted(TEST_CONFIG_VALIDATOR.iter_errors(config), key=lambda item: list(item.path)):
            path = ConfigHandler._schema_error_path(error)
            dedupe_key = (path, error.validator)
            if dedupe_key not in normalized_errors:
                normalized_errors[dedupe_key] = f"schema[{path}]: {error.message}"
        return list(normalized_errors.values())

    @staticmethod
    def _schema_error_path(error: object) -> str:
        path = ".".join(str(part) for part in error.path) or "<root>"
        if error.validator == "required":
            match = re.search(r"'([^']+)' is a required property", error.message)
            if match:
                return f"{path}.{match.group(1)}" if path != "<root>" else match.group(1)
        return path

    @staticmethod
    def save_to_file(config: dict, filename: str = DEFAULT_CONFIG_PATH) -> None:
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
    def _normalize_auth_mode(auth: object) -> str:
        if not isinstance(auth, dict):
            return AuthMode.NONE.value

        mode = str(auth.get("mode", "")).strip()
        if mode in AUTH_MODES:
            return mode

        return AuthMode.NONE.value

    @staticmethod
    def _build_auth_config(auth: object) -> dict:
        source = auth if isinstance(auth, dict) else {}
        mode = ConfigHandler._normalize_auth_mode(source)
        runtime = {
            "mode": mode,
            "client_id": str(source.get("client_id", "")).strip(),
            "client_secret": str(source.get("client_secret", "")).strip(),
        }
        if mode == AuthMode.OAUTH2_CLIENT_CREDENTIALS.value:
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
            method = str(endpoint.get("method", "GET")).upper().strip()
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
        execution_type = str(source.get("executionType", ExecutionType.EXTERNAL_EXECUTOR.value)).strip()

        runtime = {
            "requestMode": str(source.get("requestMode", RequestMode.BATCH.value)).strip(),
            "executionType": execution_type,
            "thresholds": source.get("thresholds", {}),
            "logging": ConfigHandler._build_logging_config(source.get("logging", {})),
            "scenarios": source.get("scenarios", []) if isinstance(source.get("scenarios", []), list) else [],
        }

        if execution_type == ExecutionType.SPIKE_TESTS.value:
            runtime["spikeStages"] = source.get("spikeStages", [])
        elif execution_type == ExecutionType.CONSTANT_VUS.value:
            runtime["vus"] = source.get("vus", 1)
            runtime["duration"] = str(source.get("duration", "60s")).strip()
        elif execution_type == ExecutionType.CONSTANT_ARRIVAL_RATE.value:
            runtime["rate"] = source.get("rate", 10)
            runtime["timeUnit"] = str(source.get("timeUnit", "1s")).strip()
            runtime["duration"] = str(source.get("duration", "60s")).strip()
            runtime["preAllocatedVUs"] = source.get("preAllocatedVUs", 10)
            runtime["maxVUs"] = source.get("maxVUs", 50)
        elif execution_type == ExecutionType.RAMPING_ARRIVAL_RATE.value:
            runtime["startRate"] = source.get("startRate", 1)
            runtime["timeUnit"] = str(source.get("timeUnit", "1s")).strip()
            runtime["preAllocatedVUs"] = source.get("preAllocatedVUs", 10)
            runtime["maxVUs"] = source.get("maxVUs", 50)
            runtime["rampingArrivalStages"] = source.get("rampingArrivalStages", [])
        else:
            runtime["vus"] = source.get("vus", 1)
            runtime["maxVUs"] = source.get("maxVUs", 50)
            runtime["duration"] = str(source.get("duration", "60s")).strip()

        return runtime

    @staticmethod
    def _build_logging_config(logging_cfg: object) -> dict:
        source = logging_cfg if isinstance(logging_cfg, dict) else {}
        config_handler_module = sys.modules.get("config_handler")
        normalizer = getattr(config_handler_module, "normalize_logging_level", normalize_logging_level)
        return {
            "enabled": bool(source.get("enabled", False)),
            "level": normalizer(source.get("level", LOGGING_LEVEL_FAILED)),
            "outputToUI": bool(source.get("outputToUI", True)),
            "webDashboard": bool(source.get("webDashboard", False)),
            "webDashboardUrl": str(source.get("webDashboardUrl", "http://localhost:5665")).strip(),
            "htmlSummaryReport": bool(source.get("htmlSummaryReport", False)),
        }

    @staticmethod
    def _validate_base_url(base_url: object) -> list[str]:
        errors: list[str] = []
        if not ConfigHandler.is_valid_http_url(base_url):
            errors.append("baseURL must be a valid http/https URL.")
        return errors

    @staticmethod
    def _validate_auth(auth: object) -> list[str]:
        errors: list[str] = []
        source = auth if isinstance(auth, dict) else {}

        mode = ConfigHandler._normalize_auth_mode(source)
        explicit_mode = str(source.get("mode", "")).strip()
        if explicit_mode and explicit_mode not in AUTH_MODES:
            errors.append(f"auth.mode is invalid: {explicit_mode}.")

        if mode in {AuthMode.OAUTH2_CLIENT_CREDENTIALS.value, AuthMode.BASIC.value, AuthMode.CLIENT_ID_ENFORCEMENT.value}:
            client_id = str(source.get("client_id", "")).strip()
            client_secret = str(source.get("client_secret", "")).strip()
            if not client_id and not client_secret:
                errors.append(f"auth.client_id and auth.client_secret are required for auth.mode={mode}.")

        if mode == AuthMode.OAUTH2_CLIENT_CREDENTIALS.value:
            token_url = source.get("token_url", "")
            if not ConfigHandler.is_valid_http_url(token_url):
                errors.append("auth.token_url must be a valid http/https URL.")
            if not str(source.get("scope", "")).strip():
                errors.append(f"auth.scope is required for auth.mode={AuthMode.OAUTH2_CLIENT_CREDENTIALS.value}.")

        return errors

    @staticmethod
    def _validate_request_endpoint(endpoint: object, idx: int) -> list[str]:
        errors: list[str] = []
        path = f"requestEndpoints[{idx}]"

        if not isinstance(endpoint, dict):
            return [f"{path} must be an object."]

        if not str(endpoint.get("name", "")).strip():
            errors.append(f"{path}.name is required.")

        endpoint_path = str(endpoint.get("path", "")).strip()
        if not endpoint_path:
            errors.append(f"{path}.path is required.")
        elif not endpoint_path.startswith("/"):
            errors.append(f"{path}.path must start with '/'.")

        method = str(endpoint.get("method", "")).upper().strip()
        if method not in HTTP_METHODS:
            errors.append(f"{path}.method is invalid: {method}.")

        for field_name in ("headers", "query"):
            value = endpoint.get(field_name)
            if value is not None and not isinstance(value, dict):
                errors.append(f"{path}.{field_name} must be an object.")

        return errors

    @staticmethod
    def _validate_k6_config(k6cfg: object) -> list[str]:
        errors: list[str] = []
        source = k6cfg if isinstance(k6cfg, dict) else {}
        execution_type = str(source.get("executionType", "")).strip()
        request_mode = str(source.get("requestMode", RequestMode.BATCH.value)).strip()
        if request_mode not in {RequestMode.BATCH.value, RequestMode.SCENARIOS.value}:
            errors.append(f"k6.requestMode is invalid: {request_mode}.")
        if not execution_type:
            return ["k6.executionType is required."]

        thresholds = source.get("thresholds")
        threshold_error = ConfigHandler._validate_thresholds(thresholds)
        if threshold_error:
            errors.append(threshold_error)

        mode_rules: dict[str, list[tuple[str, str]]] = {
            ExecutionType.EXTERNAL_EXECUTOR.value: [("vus", "int"), ("duration", "duration")],
            ExecutionType.SPIKE_TESTS.value: [("spikeStages", "stages")],
            ExecutionType.CONSTANT_VUS.value: [("vus", "int"), ("duration", "duration")],
            ExecutionType.CONSTANT_ARRIVAL_RATE.value: [
                ("rate", "int"),
                ("timeUnit", "duration"),
                ("duration", "duration"),
                ("preAllocatedVUs", "int"),
            ],
            ExecutionType.RAMPING_ARRIVAL_RATE.value: [
                ("startRate", "int"),
                ("timeUnit", "duration"),
                ("preAllocatedVUs", "int"),
                ("rampingArrivalStages", "stages"),
            ],
        }

        if execution_type not in EXECUTION_TYPES:
            errors.append(f"k6.executionType is invalid: {execution_type}.")
            return errors

        scenarios = source.get("scenarios", [])
        if scenarios is not None and not isinstance(scenarios, list):
            errors.append("k6.scenarios must be a list when provided.")

        for field, rule_type in mode_rules[execution_type]:
            if field not in source:
                errors.append(f"k6.{field} is required for executionType={execution_type}.")
                continue
            if rule_type == "int":
                int_error = ConfigHandler._validate_positive_int(source.get(field), f"k6.{field}")
                if int_error:
                    errors.append(int_error)
            elif rule_type == "duration":
                dur_error = ConfigHandler._validate_duration(source.get(field), f"k6.{field}")
                if dur_error:
                    errors.append(dur_error)
            elif rule_type == "stages":
                errors.extend(ConfigHandler._validate_stages(source.get(field), field))

        optional_positive_ints = ["maxVUs"]
        for field in optional_positive_ints:
            if field in source and source.get(field) is not None:
                int_error = ConfigHandler._validate_positive_int(source.get(field), f"k6.{field}")
                if int_error:
                    errors.append(int_error)

        logging_cfg = source.get("logging", {})
        if isinstance(logging_cfg, dict):
            logging_level = str(logging_cfg.get("level", "")).strip()
            if logging_level and logging_level not in LOGGING_LEVELS:
                errors.append(f"k6.logging.level is invalid: {logging_level}.")

            if bool(logging_cfg.get("webDashboard", False)):
                dashboard_url = logging_cfg.get("webDashboardUrl", "")
                if not ConfigHandler.is_valid_http_url(dashboard_url):
                    errors.append("k6.logging.webDashboardUrl must be a valid http/https URL when webDashboard is enabled.")

        return errors

    @staticmethod
    def _validate_positive_int(value: object, field_path: str) -> str | None:
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            return f"{field_path} must be a positive integer."
        return None

    @staticmethod
    def _validate_non_negative_int(value: object, field_path: str) -> str | None:
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            return f"{field_path} must be a non-negative integer."
        return None

    @staticmethod
    def _validate_duration(value: object, field_path: str) -> str | None:
        text = str(value).strip() if value is not None else ""
        if not text or not K6_DURATION_RE.match(text):
            return f"{field_path} must be a valid k6 duration like '30s' or '1m'."
        return None

    @staticmethod
    def _validate_stages(stages: object, stage_type: str) -> list[str]:
        errors: list[str] = []
        if not isinstance(stages, list) or not stages:
            return [f"k6.{stage_type} must be a non-empty list."]

        for idx, stage in enumerate(stages):
            path = f"k6.{stage_type}[{idx}]"
            if not isinstance(stage, dict):
                errors.append(f"{path} must be an object.")
                continue

            duration_error = ConfigHandler._validate_duration(stage.get("duration"), f"{path}.duration")
            if duration_error:
                errors.append(duration_error)

            target_error = ConfigHandler._validate_non_negative_int(stage.get("target"), f"{path}.target")
            if target_error:
                errors.append(target_error)

        return errors

    @staticmethod
    def is_valid_http_url(value: object) -> bool:
        text = str(value).strip() if value is not None else ""
        if not text or any(ch.isspace() for ch in text):
            return False
        parsed = urlparse(text)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

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
