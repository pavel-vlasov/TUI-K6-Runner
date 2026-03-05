import json
import os

from textual.app import App

from app_bootstrap import get_resource_path
from app_mixins.events_mixin import EventsMixin
from app_mixins.request_mixin import RequestMixin
from app_mixins.stage_mixin import StageMixin
from app_mixins.ui_mixin import UIMixin
from constants import DEFAULT_CONFIG
from k6_logic import K6Logic


class K6TestApp(EventsMixin, UIMixin, RequestMixin, StageMixin, App):
    TITLE = "K6 Executor"
    CSS_PATH = get_resource_path("style.tcss")

    def __init__(self):
        super().__init__()
        self.k6_logic = K6Logic()
        self.full_config = {}
        self.load_config_safely()

    def load_config_safely(self):
        try:
            if os.path.exists("test_config.json"):
                with open("test_config.json", "r", encoding="utf-8") as f:
                    self.full_config = json.load(f)
            else:
                self.full_config = DEFAULT_CONFIG.copy()
        except Exception:
            self.full_config = DEFAULT_CONFIG.copy()
