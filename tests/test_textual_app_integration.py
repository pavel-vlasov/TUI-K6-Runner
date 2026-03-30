from __future__ import annotations

import asyncio
from types import MethodType

import pytest
from textual.widgets import Button, Input, Select, Static

from app import K6TestApp
from application import RunCallbacks


class FakeRunController:
    def __init__(self) -> None:
        self.is_running = False
        self.scale_calls: list[int] = []
        self.start_calls: list[dict] = []
        self.stop_calls = 0
        self.saved_configs: list[dict] = []
        self._callbacks: RunCallbacks | None = None

    def save_config(self, config: dict) -> None:
        self.saved_configs.append(config)

    async def start_run(self, config: dict, callbacks: RunCallbacks):
        self.start_calls.append(config)
        self.is_running = True
        self._callbacks = callbacks
        callbacks.on_run_state_changed(True)

    async def stop_run(self):
        self.stop_calls += 1
        self.is_running = False
        if self._callbacks is not None:
            self._callbacks.on_run_state_changed(False)

    async def scale(self, vus: int, _on_log):
        self.scale_calls.append(vus)


def test_start_stop_toggles_run_controls_state() -> None:
    async def scenario() -> None:
        app = K6TestApp()
        fake_controller = FakeRunController()
        notifications: list[tuple[str, str]] = []

        app.run_controller = fake_controller
        app.action_save_config = MethodType(lambda _self: True, app)
        app.notify = MethodType(
            lambda _self, message, severity="information", **_kwargs: notifications.append((message, severity)), app
        )

        async with app.run_test(size=(140, 40)) as pilot:
            run_btn = app.query_one("#run_btn", Button)
            stop_btn = app.query_one("#stop_btn", Button)
            apply_vu_btn = app.query_one("#apply_vu_btn", Button)

            assert run_btn.disabled is False
            assert stop_btn.disabled is True
            assert apply_vu_btn.disabled is True

            await pilot.click("#run_btn")
            await pilot.pause()

            assert fake_controller.is_running is True
            assert run_btn.disabled is True
            assert stop_btn.disabled is False
            assert apply_vu_btn.disabled is False

            await pilot.click("#stop_btn")
            await pilot.pause()

            assert fake_controller.stop_calls == 1
            assert run_btn.disabled is False
            assert stop_btn.disabled is True
            assert apply_vu_btn.disabled is True
            assert ("Stop command sent", "warning") in notifications

    asyncio.run(scenario())


def test_invalid_vu_shows_warning_and_does_not_call_scale() -> None:
    async def scenario() -> None:
        app = K6TestApp()
        fake_controller = FakeRunController()
        notifications: list[tuple[str, str]] = []

        app.run_controller = fake_controller
        app.notify = MethodType(
            lambda _self, message, severity="information", **_kwargs: notifications.append((message, severity)), app
        )

        async with app.run_test(size=(140, 40)) as pilot:
            fake_controller.is_running = True
            app.set_run_ui_state(True)
            await pilot.pause()
            vu_input = app.query_one("#vu_input", Input)
            vu_input.value = "invalid-vu"

            await pilot.click("#apply_vu_btn")
            await pilot.pause()

            assert notifications[-1] == ("Please enter a valid VU value (positive integer).", "warning")
            assert fake_controller.scale_calls == []
            assert vu_input.value == "invalid-vu"

    asyncio.run(scenario())


def test_external_mode_warning_and_controls_disabled_when_running() -> None:
    async def scenario() -> None:
        app = K6TestApp()
        fake_controller = FakeRunController()

        app.run_controller = fake_controller

        async with app.run_test(size=(140, 40)) as pilot:
            run_btn = app.query_one("#run_btn", Button)
            stop_btn = app.query_one("#stop_btn", Button)
            apply_vu_btn = app.query_one("#apply_vu_btn", Button)
            output_mode_select = app.query_one("#select___k6__logging__outputToUI", Select)
            external_mode_warning = app.query_one("#logging_external_mode_warning", Static)

            fake_controller.is_running = True
            output_mode_select.value = False
            app.toggle_logging_fields()
            await pilot.pause()

            assert external_mode_warning.styles.display == "block"
            assert run_btn.disabled is True
            assert stop_btn.disabled is True
            assert apply_vu_btn.disabled is True

    asyncio.run(scenario())
