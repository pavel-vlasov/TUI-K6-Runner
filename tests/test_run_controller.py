import asyncio

from application.run_controller import RunCallbacks, RunController


class DummyK6Service:
    def __init__(self):
        self.is_running = False
        self.run_calls = 0
        self.last_kwargs = None

    async def run_k6_process(self, **kwargs):
        self.run_calls += 1
        self.last_kwargs = kwargs


class FailingStateCallback:
    def __init__(self):
        self.calls = []

    def __call__(self, running: bool):
        self.calls.append(running)
        raise RuntimeError("UI already unmounted")


async def _run_controller_start(controller: RunController, callbacks: RunCallbacks, config: dict):
    task = await controller.start_run(config, callbacks)
    assert task is not None
    await task


def test_start_run_ignores_run_state_callback_errors():
    service = DummyK6Service()
    controller = RunController(service)

    state_callback = FailingStateCallback()
    callbacks = RunCallbacks(
        on_log=lambda _msg: None,
        on_status=lambda _msg: None,
        on_run_state_changed=state_callback,
    )

    asyncio.run(_run_controller_start(controller, callbacks, {"k6": {"logging": {}}}))

    assert state_callback.calls == [True, False]
    assert service.run_calls == 1


def test_start_run_passes_dashboard_url_to_service():
    service = DummyK6Service()
    controller = RunController(service)
    callbacks = RunCallbacks(
        on_log=lambda _msg: None,
        on_status=lambda _msg: None,
        on_run_state_changed=lambda _running: None,
    )

    asyncio.run(
        _run_controller_start(
            controller,
            callbacks,
            {"k6": {"logging": {"webDashboard": True, "webDashboardUrl": "http://localhost:9999"}}},
        )
    )

    assert service.last_kwargs is not None
    assert service.last_kwargs["web_dashboard_url"] == "http://localhost:9999"


def test_start_run_notifies_false_when_task_creation_fails(monkeypatch):
    service = DummyK6Service()
    controller = RunController(service)
    state_changes = []

    callbacks = RunCallbacks(
        on_log=lambda _msg: None,
        on_status=lambda _msg: None,
        on_run_state_changed=state_changes.append,
    )

    def failing_create_task(_coroutine):
        raise RuntimeError("task creation failed")

    monkeypatch.setattr(asyncio, "create_task", failing_create_task)

    try:
        asyncio.run(controller.start_run({"k6": {"logging": {}}}, callbacks))
    except RuntimeError as error:
        assert str(error) == "task creation failed"
    else:
        assert False, "Expected RuntimeError to be raised"

    assert state_changes == [True, False]
