import os
from pathlib import Path

import pytest

from config_handler import ConfigHandler
from constants import (
    DEFAULT_CONFIG,
    HTTP_METHODS,
    LOGGING_LEVEL_ALL,
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


def test_is_valid_http_url_public_contract():
    assert ConfigHandler.is_valid_http_url("https://example.com")
    assert ConfigHandler.is_valid_http_url("http://localhost:5665/path?a=1")
    assert not ConfigHandler.is_valid_http_url("ftp://example.com")
    assert not ConfigHandler.is_valid_http_url("https://bad url")
    assert not ConfigHandler.is_valid_http_url(None)


def test_is_valid_http_url_private_alias_kept_for_backward_compatibility():
    assert ConfigHandler._is_valid_http_url("https://example.com") == ConfigHandler.is_valid_http_url(
        "https://example.com"
    )
    assert ConfigHandler._is_valid_http_url("not-a-url") == ConfigHandler.is_valid_http_url("not-a-url")


def test_runtime_config_k6_keys_are_consumed_by_test_js_smoke():
    runtime = ConfigHandler.build_runtime_config(
        {
            "baseURL": "https://example.com",
            "auth": {
                "mode": "oauth2_client_credentials",
                "client_id": "cid",
                "client_secret": "sec",
                "token_url": "https://idp.example.com/token",
                "scope": "read",
            },
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
                "executionType": "Ramping Arrival Rate",
                "startRate": 5,
                "timeUnit": "1s",
                "preAllocatedVUs": 10,
                "maxVUs": 30,
                "rampingArrivalStages": [{"duration": "30s", "target": 10}],
                "thresholds": {"http_req_duration": ["p(95)<500"]},
                "logging": {
                    "enabled": True,
                    "level": "failed_without_payloads",
                    "outputToUI": True,
                    "webDashboard": True,
                    "webDashboardUrl": "http://localhost:5665",
                    "htmlSummaryReport": True,
                },
            },
        }
    )

    repo_root = Path(__file__).resolve().parents[1]
    script = (repo_root / "test.js").read_text(encoding="utf-8")

    assert "config.baseURL" in script
    assert "config.auth" in script
    assert "config.requestEndpoints" in script
    assert "config.request" not in script
    assert "reqConfig" not in script
    assert "config.k6" in script

    for key in runtime["k6"]:
        if key == "logging":
            continue
        assert f"k6cfg.{key}" in script

    assert "logConfig.enabled" in script
    assert "logConfig.level" in script

    python_side_logging_keys = {"outputToUI", "webDashboard", "webDashboardUrl", "htmlSummaryReport"}
    assert python_side_logging_keys.issubset(set(runtime["k6"]["logging"].keys()))


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


def test_build_runtime_config_normalizes_logging_level_with_hyphens_to_canonical():
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
                "logging": {"enabled": True, "level": "failures-without-payloads"},
            },
        }
    )

    assert runtime["k6"]["logging"]["level"] == LOGGING_LEVEL_FAILED_WITHOUT_PAYLOADS


def test_build_runtime_config_normalizes_logging_level_with_spaces_to_canonical():
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
                "logging": {"enabled": True, "level": "  ALL  "},
            },
        }
    )

    assert runtime["k6"]["logging"]["level"] == LOGGING_LEVEL_ALL


def test_validate_runtime_config_rejects_non_canonical_logging_level():
    runtime = _base_runtime()
    runtime["k6"]["logging"] = {"enabled": True, "level": "Failures - without payloads"}

    errors = ConfigHandler.validate_runtime_config(runtime)

    assert any("k6.logging.level is invalid" in error for error in errors)


def test_validate_runtime_config_allows_zero_target_stages_for_spike_and_ramping_arrival():
    base_k6 = {
        "thresholds": {"http_req_duration": ["p(95)<500"]},
    }

    runtime_spike = _base_runtime()
    runtime_spike["k6"] = {
        **base_k6,
        "executionType": "Spike Tests",
        "spikeStages": [{"duration": "30s", "target": 0}],
    }

    runtime_ramping_arrival = _base_runtime()
    runtime_ramping_arrival["k6"] = {
        **base_k6,
        "executionType": "Ramping Arrival Rate",
        "startRate": 1,
        "timeUnit": "1s",
        "preAllocatedVUs": 5,
        "rampingArrivalStages": [{"duration": "30s", "target": 0}],
    }

    assert ConfigHandler.validate_runtime_config(runtime_spike) == []
    assert ConfigHandler.validate_runtime_config(runtime_ramping_arrival) == []


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


def test_validate_runtime_config_allows_zero_stage_target_for_spike_and_ramping_arrival():
    runtime = _base_runtime()
    runtime["k6"] = {
        "executionType": "Spike Tests",
        "spikeStages": [{"duration": "20s", "target": 0}],
        "thresholds": {"http_req_duration": ["p(95)<500"]},
    }
    assert ConfigHandler.validate_runtime_config(runtime) == []
    assert ConfigHandler.validate_against_schema(runtime) == []

    runtime["k6"] = {
        "executionType": "Ramping Arrival Rate",
        "startRate": 1,
        "timeUnit": "1s",
        "preAllocatedVUs": 5,
        "rampingArrivalStages": [{"duration": "20s", "target": 0}],
        "thresholds": {"http_req_duration": ["p(95)<500"]},
    }
    assert ConfigHandler.validate_runtime_config(runtime) == []
    assert ConfigHandler.validate_against_schema(runtime) == []


def test_validate_runtime_config_and_schema_reject_negative_stage_target():
    runtime = _base_runtime()
    runtime["k6"] = {
        "executionType": "Spike Tests",
        "spikeStages": [{"duration": "20s", "target": -1}],
        "thresholds": {"http_req_duration": ["p(95)<500"]},
    }
    runtime_errors = ConfigHandler.validate_runtime_config(runtime)
    schema_errors = ConfigHandler.validate_against_schema(runtime)

    assert any("non-negative integer" in error for error in runtime_errors)
    assert any("minimum" in error and "k6.spikeStages.0.target" in error for error in schema_errors)


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



def test_save_to_file_removes_temp_file_when_replace_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    target = tmp_path / "test_config.json"
    created_temp_files: list[Path] = []

    class _TmpFileWrapper:
        def __init__(self, path: Path):
            self.name = str(path)
            self._handle = open(path, "w", encoding="utf-8")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self._handle.close()

        def write(self, data: str) -> int:
            return self._handle.write(data)

        def flush(self) -> None:
            self._handle.flush()

        def fileno(self) -> int:
            return self._handle.fileno()

    def _fake_named_temporary_file(*args, **kwargs):
        temp_path = tmp_path / "config.tmp.json"
        created_temp_files.append(temp_path)
        return _TmpFileWrapper(temp_path)

    monkeypatch.setattr("config_handler.tempfile.NamedTemporaryFile", _fake_named_temporary_file)
    monkeypatch.setattr("config_handler.os.replace", lambda src, dst: (_ for _ in ()).throw(OSError("boom")))

    with pytest.raises(OSError, match="boom"):
        ConfigHandler.save_to_file({"ok": True}, str(target))

    assert created_temp_files, "Temporary file should be created through patched NamedTemporaryFile."
    assert not os.path.exists(created_temp_files[0])


def test_validate_against_schema_returns_prefixed_errors_for_invalid_payload():
    errors = ConfigHandler.validate_against_schema({"baseURL": "https://example.com"})

    assert errors
    assert all(error.startswith("schema[") for error in errors)


def test_normalize_auth_mode_returns_none_when_multiple_legacy_flags_enabled():
    assert (
        ConfigHandler._normalize_auth_mode(
            {"useOAuth2": True, "basicauth": True, "ClientId_Enforcement": False}
        )
        == "none"
    )


def test_build_logging_config_uses_normalize_logging_level_for_unknown_values(
    monkeypatch: pytest.MonkeyPatch,
):
    received: list[str] = []

    def _fake_normalize(level: object) -> str:
        received.append(str(level))
        return "normalized-from-fake"

    monkeypatch.setattr("config_handler.normalize_logging_level", _fake_normalize)

    logging_cfg = ConfigHandler._build_logging_config({"enabled": True, "level": "???"})

    assert received == ["???"]
    assert logging_cfg["level"] == "normalized-from-fake"
