import json
from copy import deepcopy

from app import K6TestApp
from constants import DEFAULT_CONFIG


class DummyApp(K6TestApp):
    def __init__(self, config_path: str):
        self.config_path = config_path


def test_load_config_safely_reads_existing_file(tmp_path):
    cfg = {"baseURL": "http://example"}
    config_path = tmp_path / "test_config.json"
    config_path.write_text(json.dumps(cfg), encoding="utf-8")

    app = DummyApp(str(config_path))
    app.full_config = {}
    app.config_load_error = None
    app.config_load_error_details = None
    app.load_config_safely()

    assert app.full_config == cfg
    assert app.config_load_error is None
    assert app.config_load_error_details is None


def test_load_config_safely_falls_back_to_default_on_json_error(tmp_path):
    config_path = tmp_path / "test_config.json"
    config_path.write_text("{invalid", encoding="utf-8")

    app = DummyApp(str(config_path))
    app.full_config = {}
    app.config_load_error = None
    app.config_load_error_details = None
    app.load_config_safely()

    assert app.full_config == deepcopy(DEFAULT_CONFIG)
    assert "Failed to parse JSON config" in app.config_load_error
    assert "line" in app.config_load_error_details


def test_load_config_safely_missing_file_uses_default_without_error(tmp_path):
    app = DummyApp(str(tmp_path / "missing_config.json"))
    app.full_config = {}
    app.config_load_error = None
    app.config_load_error_details = None

    app.load_config_safely()

    assert app.full_config == deepcopy(DEFAULT_CONFIG)
    assert app.config_load_error is None
    assert app.config_load_error_details is None


def test_load_config_safely_falls_back_to_default_on_os_error(tmp_path, monkeypatch):
    config_path = tmp_path / "test_config.json"
    config_path.write_text("{}", encoding="utf-8")

    def _raise_os_error(*_args, **_kwargs):
        raise OSError("permission denied")

    monkeypatch.setattr("builtins.open", _raise_os_error)

    app = DummyApp(str(config_path))
    app.full_config = {}
    app.config_load_error = None
    app.config_load_error_details = None
    app.load_config_safely()

    assert app.full_config == deepcopy(DEFAULT_CONFIG)
    assert "Failed to read config file" in app.config_load_error
    assert "permission denied" in app.config_load_error_details
