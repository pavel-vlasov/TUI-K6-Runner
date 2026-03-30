import json
import os
from copy import deepcopy

from textual.app import App

from app_bootstrap import get_resource_path
from app_mixins.events_mixin import EventsMixin
from app_mixins.request_mixin import RequestMixin
from app_mixins.stage_mixin import StageMixin
from app_mixins.ui_mixin import UIMixin
from application import RunController
from constants import DEFAULT_CONFIG, DEFAULT_CONFIG_PATH
from k6.service import K6Service


class K6TestApp(EventsMixin, UIMixin, RequestMixin, StageMixin, App):
    TITLE = "K6 Executor"
    CSS_PATH = get_resource_path("style.tcss")

    def __init__(self):
        super().__init__()
        self.run_controller = RunController(K6Service(), config_path=DEFAULT_CONFIG_PATH)
        self.full_config = {}
        self.config_load_error = None
        self.config_load_error_details = None
        self.load_config_safely()

    @property
    def full_config(self):
        """Backward-compatible alias for UI configuration model."""
        return self.ui_config

    @full_config.setter
    def full_config(self, value):
        self.ui_config = value

    def load_config_safely(self):
        config_path = DEFAULT_CONFIG_PATH
        self.config_load_error = None
        self.config_load_error_details = None
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    self.ui_config = json.load(f)
            else:
                self.ui_config = deepcopy(DEFAULT_CONFIG)
        except json.JSONDecodeError as exc:
            self.config_load_error = f"Failed to parse JSON config: {config_path}."
            self.config_load_error_details = f"line {exc.lineno}, column {exc.colno}: {exc.msg}"
            self.ui_config = deepcopy(DEFAULT_CONFIG)
        except OSError as exc:
            self.config_load_error = f"Failed to read config file: {config_path}."
            self.config_load_error_details = str(exc)
            self.ui_config = deepcopy(DEFAULT_CONFIG)
        except Exception as exc:
            self.config_load_error = f"Failed to load config file: {config_path}."
            self.config_load_error_details = str(exc)
            self.ui_config = deepcopy(DEFAULT_CONFIG)
