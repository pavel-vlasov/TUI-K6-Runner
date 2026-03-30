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
from constants import DEFAULT_CONFIG
from k6.service import K6Service


class K6TestApp(EventsMixin, UIMixin, RequestMixin, StageMixin, App):
    TITLE = "K6 Executor"
    CSS_PATH = get_resource_path("style.tcss")

    def __init__(self, config_path: str = "test_config.json"):
        super().__init__()
        self.config_path = config_path
        self.run_controller = RunController(K6Service(), config_path=config_path)
        self.full_config = {}
        self.config_load_error = None
        self.config_load_error_details = None
        self.load_config_safely()

    def load_config_safely(self):
        self.config_load_error = None
        self.config_load_error_details = None
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.full_config = json.load(f)
            else:
                self.full_config = deepcopy(DEFAULT_CONFIG)
        except json.JSONDecodeError as exc:
            self.config_load_error = f"Failed to parse JSON config: {self.config_path}."
            self.config_load_error_details = f"line {exc.lineno}, column {exc.colno}: {exc.msg}"
            self.full_config = deepcopy(DEFAULT_CONFIG)
        except OSError as exc:
            self.config_load_error = f"Failed to read config file: {self.config_path}."
            self.config_load_error_details = str(exc)
            self.full_config = deepcopy(DEFAULT_CONFIG)
        except Exception as exc:
            self.config_load_error = f"Failed to load config file: {self.config_path}."
            self.config_load_error_details = str(exc)
            self.full_config = deepcopy(DEFAULT_CONFIG)
