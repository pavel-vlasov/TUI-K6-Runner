import json
from copy import deepcopy

from app import K6TestApp
from constants import DEFAULT_CONFIG


class DummyApp(K6TestApp):
    def __init__(self):
        pass


def test_load_config_safely_reads_existing_file(tmp_path, monkeypatch):
    cfg = {"baseURL": "http://example"}
    config_path = tmp_path / "test_config.json"
    config_path.write_text(json.dumps(cfg), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    app = DummyApp()
    app.full_config = {}
    app.load_config_safely()

    assert app.full_config == cfg


def test_load_config_safely_falls_back_to_default_on_error(tmp_path, monkeypatch):
    config_path = tmp_path / "test_config.json"
    config_path.write_text("{invalid", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    app = DummyApp()
    app.full_config = {}
    app.load_config_safely()

    assert app.full_config == deepcopy(DEFAULT_CONFIG)
