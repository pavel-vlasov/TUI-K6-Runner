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
