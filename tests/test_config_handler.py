from pathlib import Path

from config_handler import ConfigHandler


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
            "ClientId_Enforcement": True,
            "useOAuth2": False,
            "basicauth": False,
            "client_id": "cid",
            "client_secret": "sec",
            "token_url": "should-be-removed",
            "scope": "should-be-removed",
        },
        "requestEndpoints": [
            {"name": "Endpoint 1", "method": "GET", "path": "/health", "headers": {}, "body": None, "query": {}},
        ],
        "k6": {
            "executionType": "Constant VUs",
            "vus": 3,
            "duration": "10s",
            "rate": 100,
            "thresholds": {"http_req_duration": ["p(95)<500"]},
            "logging": {"enabled": True, "level": "all", "outputToUI": True, "webDashboard": False, "webDashboardUrl": "http://localhost:5665", "htmlSummaryReport": False},
        },
    }

    runtime = ConfigHandler.build_runtime_config(ui_config)

    assert "token_url" not in runtime["auth"]
    assert "scope" not in runtime["auth"]
    assert "rate" not in runtime["k6"]
    assert runtime["k6"]["vus"] == 3
    assert runtime["k6"]["duration"] == "10s"


def test_validate_runtime_config_rejects_invalid_thresholds():
    runtime = {
        "baseURL": "https://example.com",
        "auth": {
            "ClientId_Enforcement": True,
            "useOAuth2": False,
            "basicauth": False,
            "client_id": "cid",
            "client_secret": "sec",
        },
        "requestEndpoints": [{"name": "Endpoint 1", "method": "GET", "path": "/"}],
        "k6": {"executionType": "Constant VUs", "thresholds": {"http_req_duration": [""]}},
    }

    errors = ConfigHandler.validate_runtime_config(runtime)

    assert any("thresholds" in error for error in errors)


def test_save_to_file_writes_json_to_target_file(tmp_path: Path):
    target = tmp_path / "test_config.json"

    ConfigHandler.save_to_file({"ok": True}, str(target))

    assert target.exists()
    assert target.read_text(encoding="utf-8").strip().startswith("{")
