from pathlib import Path

from config_handler import ConfigHandler
from constants import (
    DEFAULT_CONFIG,
    HTTP_METHODS,
    LOGGING_LEVEL_FAILED,
    LOGGING_LEVEL_FAILED_WITHOUT_PAYLOADS,
)


def _base_runtime() -> dict:
    return {
        "baseURL": "https://example.com",
        "auth": {"mode": "none", "client_id": "", "client_secret": ""},
        "requestEndpoints": [
            {
                "name": "Endpoint 1",
                "method": "GET",
                "path": "/",
                "headers": {},
                "query": {},
            }
        ],
        "k6": {
            "executionType": "Constant VUs",
            "vus": 1,
            "duration": "10s",
            "thresholds": {"http_req_duration": ["p(95)<500"]},
        },
    }


def test_update_from_fields_builds_nested_payload_without_ui_types():
    config = {"k6": {"spikeStages": [{}]}, "requestEndpoints": [{}]}
    fields = {
        "input___baseURL": "https://example.com",
        "input___k6__vus": "10",
        "input___k6__spikeStages__0__target": "25",
        "textarea___requestEndpoints__0__body": '{"ok": true}',
        "select___k6__executionType": "Constant VUs",
    }

    updated = ConfigHandler.update_from_fields(config, fields)

    assert updated["baseURL"] == "https://example.com"
    assert updated["k6"]["vus"] == 10
    assert updated["k6"]["spikeStages"][0]["target"] == 25
    assert updated["requestEndpoints"][0]["body"] == {"ok": True}
    assert updated["k6"]["executionType"] == "Constant VUs"


def test_build_runtime_config_keeps_only_fields_needed_for_selected_run():
    ui_config = {
        "baseURL": "https://example.com",
        "auth": {
            "mode": "client_id_enforcement",
            "client_id": "cid",
            "client_secret": "sec",
            "token_url": "should-be-removed",
            "scope": "should-be-removed",
        },
        "requestEndpoints": [
            {
                "name": "Endpoint 1",
                "method": "GET",
                "path": "/health",
                "headers": {},
                "body": None,
                "query": {},
            },
        ],
        "k6": {
            "executionType": "Constant VUs",
            "vus": 3,
            "duration": "10s",
            "rate": 100,
            "thresholds": {"http_req_duration": ["p(95)<500"]},
            "logging": {
                "enabled": True,
                "level": "all",
                "outputToUI": True,
                "webDashboard": False,
                "webDashboardUrl": "http://localhost:5665",
                "htmlSummaryReport": False,
            },
        },
    }

    runtime = ConfigHandler.build_runtime_config(ui_config)

    assert runtime["auth"]["mode"] == "client_id_enforcement"
    assert "token_url" not in runtime["auth"]
    assert "scope" not in runtime["auth"]
    assert "rate" not in runtime["k6"]
    assert runtime["k6"]["vus"] == 3
    assert runtime["k6"]["duration"] == "10s"


def test_validate_runtime_config_rejects_invalid_thresholds():
    runtime = _base_runtime()
    runtime["k6"]["thresholds"] = {"http_req_duration": [""]}

    errors = ConfigHandler.validate_runtime_config(runtime)

    assert any("thresholds" in error for error in errors)


def test_save_to_file_writes_json_to_target_file(tmp_path: Path):
    target = tmp_path / "test_config.json"

    ConfigHandler.save_to_file({"ok": True}, str(target))

    assert target.exists()
    assert target.read_text(encoding="utf-8").strip().startswith("{")


def test_validate_runtime_config_allows_auth_modes():
    valid_modes = [
        ("none", {}),
        ("basic", {"client_id": "cid", "client_secret": "sec"}),
        (
            "oauth2_client_credentials",
            {
                "client_id": "cid",
                "client_secret": "sec",
                "token_url": "https://idp.example.com/token",
                "scope": "read",
            },
        ),
        ("client_id_enforcement", {"client_id": "cid", "client_secret": "sec"}),
    ]

    for mode, auth_fields in valid_modes:
        runtime = _base_runtime()
        runtime["auth"] = {"mode": mode, **auth_fields}
        errors = ConfigHandler.validate_runtime_config(runtime)
        assert not any(error.startswith("auth") for error in errors), (mode, errors)


def test_build_runtime_config_migrates_legacy_use_oauth2_flag_to_mode():
    runtime = ConfigHandler.build_runtime_config(
        {
            "baseURL": "https://example.com",
            "auth": {
                "useOAuth2": True,
                "client_id": "cid",
                "client_secret": "sec",
                "token_url": "https://idp.example.com/token",
                "scope": "read",
            },
            "requestEndpoints": [
                {
                    "name": "Endpoint 1",
                    "method": "GET",
                    "path": "/",
                    "headers": {},
                    "query": {},
                }
            ],
            "k6": {
                "executionType": "Constant VUs",
                "vus": 1,
                "duration": "10s",
                "thresholds": {},
            },
        }
    )
    assert runtime["auth"]["mode"] == "oauth2_client_credentials"


def test_build_runtime_config_migrates_legacy_basic_flag_to_mode():
    runtime = ConfigHandler.build_runtime_config(
        {
            "baseURL": "https://example.com",
            "auth": {"basicauth": True, "client_id": "cid", "client_secret": "sec"},
            "requestEndpoints": [
                {
                    "name": "Endpoint 1",
                    "method": "GET",
                    "path": "/",
                    "headers": {},
                    "query": {},
                }
            ],
            "k6": {
                "executionType": "Constant VUs",
                "vus": 1,
                "duration": "10s",
                "thresholds": {},
            },
        }
    )
    assert runtime["auth"]["mode"] == "basic"


def test_build_runtime_config_migrates_legacy_client_id_enforcement_flag_to_mode():
    runtime = ConfigHandler.build_runtime_config(
        {
            "baseURL": "https://example.com",
            "auth": {
                "ClientId_Enforcement": True,
                "client_id": "cid",
                "client_secret": "sec",
            },
            "requestEndpoints": [
                {
                    "name": "Endpoint 1",
                    "method": "GET",
                    "path": "/",
                    "headers": {},
                    "query": {},
                }
            ],
            "k6": {
                "executionType": "Constant VUs",
                "vus": 1,
                "duration": "10s",
                "thresholds": {},
            },
        }
    )
    assert runtime["auth"]["mode"] == "client_id_enforcement"


def test_validate_runtime_config_requires_fields_per_auth_mode():
    runtime = _base_runtime()
    runtime["auth"] = {
        "mode": "oauth2_client_credentials",
        "client_id": "",
        "client_secret": "sec",
        "token_url": "bad",
        "scope": "",
    }

    errors = ConfigHandler.validate_runtime_config(runtime)

    assert any("auth.client_id" in error for error in errors)
    assert any("auth.token_url" in error for error in errors)
    assert any("auth.scope" in error for error in errors)


def test_validate_runtime_config_accepts_only_http_methods_from_constants():
    for method in HTTP_METHODS:
        runtime = _base_runtime()
        runtime["requestEndpoints"][0]["method"] = method
        errors = ConfigHandler.validate_runtime_config(runtime)
        assert not any("method is invalid" in error for error in errors), (
            method,
            errors,
        )

    runtime = _base_runtime()
    runtime["requestEndpoints"][0]["method"] = "TRACE"
    errors = ConfigHandler.validate_runtime_config(runtime)
    assert any("method is invalid" in error for error in errors)


def test_validate_runtime_config_rejects_invalid_urls_and_k6_values():
    runtime = _base_runtime()
    runtime["baseURL"] = "not-url"
    runtime["requestEndpoints"][0]["path"] = "relative"
    runtime["k6"]["duration"] = "10"
    runtime["k6"]["vus"] = 0

    errors = ConfigHandler.validate_runtime_config(runtime)

    assert any("baseURL" in error for error in errors)
    assert any("path must start" in error for error in errors)
    assert any("k6.duration" in error for error in errors)
    assert any("k6.vus" in error for error in errors)


def test_validate_runtime_config_rejects_invalid_web_dashboard_url_when_enabled():
    runtime = _base_runtime()
    runtime["k6"]["logging"] = {
        "enabled": True,
        "level": "all",
        "outputToUI": True,
        "webDashboard": True,
        "webDashboardUrl": "not-a-url",
        "htmlSummaryReport": False,
    }

    errors = ConfigHandler.validate_runtime_config(runtime)

    assert any("k6.logging.webDashboardUrl" in error for error in errors)


def test_build_runtime_config_normalizes_legacy_logging_level_to_canonical_wire_format():
    runtime = ConfigHandler.build_runtime_config(
        {
            "baseURL": "https://example.com",
            "auth": {"mode": "none"},
            "requestEndpoints": [{"name": "Endpoint 1", "method": "GET", "path": "/", "headers": {}, "query": {}}],
            "k6": {
                "executionType": "Constant VUs",
                "vus": 1,
                "duration": "10s",
                "thresholds": {"http_req_duration": ["p(95)<500"]},
                "logging": {"enabled": True, "level": "Failures - without payloads"},
            },
        }
    )

    assert runtime["k6"]["logging"]["level"] == LOGGING_LEVEL_FAILED_WITHOUT_PAYLOADS


def test_build_runtime_config_falls_back_to_default_canonical_logging_level():
    runtime = ConfigHandler.build_runtime_config(
        {
            "baseURL": "https://example.com",
            "auth": {"mode": "none"},
            "requestEndpoints": [{"name": "Endpoint 1", "method": "GET", "path": "/", "headers": {}, "query": {}}],
            "k6": {
                "executionType": "Constant VUs",
                "vus": 1,
                "duration": "10s",
                "thresholds": {"http_req_duration": ["p(95)<500"]},
                "logging": {"enabled": True, "level": "INVALID"},
            },
        }
    )

    assert runtime["k6"]["logging"]["level"] == LOGGING_LEVEL_FAILED


def test_validate_runtime_config_rejects_non_canonical_logging_level():
    runtime = _base_runtime()
    runtime["k6"]["logging"] = {"enabled": True, "level": "Failures - without payloads"}

    errors = ConfigHandler.validate_runtime_config(runtime)

    assert any("k6.logging.level is invalid" in error for error in errors)


def test_validate_runtime_config_rejects_invalid_stage_shape():
    runtime = _base_runtime()
    runtime["k6"] = {
        "executionType": "Ramping Arrival Rate",
        "startRate": 1,
        "timeUnit": "1s",
        "preAllocatedVUs": 5,
        "rampingArrivalStages": [{"duration": "", "target": -1}],
        "thresholds": {"http_req_duration": ["p(95)<500"]},
    }

    errors = ConfigHandler.validate_runtime_config(runtime)

    assert any("rampingArrivalStages[0].duration" in error for error in errors)
    assert any("rampingArrivalStages[0].target" in error for error in errors)


def test_schema_validation_accepts_minimal_and_full_runtime_configs():
    minimal_runtime = {
        "baseURL": "https://example.com",
        "auth": {"mode": "none", "client_id": "", "client_secret": ""},
        "requestEndpoints": [
            {
                "name": "Endpoint 1",
                "method": "GET",
                "path": "/health",
                "headers": {},
                "query": {},
            }
        ],
        "k6": {
            "executionType": "Constant VUs",
            "vus": 1,
            "duration": "10s",
            "thresholds": {"http_req_duration": ["p(95)<500"]},
            "logging": {
                "enabled": True,
                "level": "failed",
                "outputToUI": True,
                "webDashboard": False,
                "webDashboardUrl": "http://localhost:5665",
                "htmlSummaryReport": False,
            },
        },
    }

    full_runtime = ConfigHandler.build_runtime_config(DEFAULT_CONFIG)

    assert ConfigHandler.validate_against_schema(minimal_runtime) == []
    assert ConfigHandler.validate_against_schema(full_runtime) == []
