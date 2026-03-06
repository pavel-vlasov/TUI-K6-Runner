import asyncio

from application.run_controller import RunCallbacks, RunController


class DummyK6Service:
    def __init__(self):
        self.is_running = False
        self.run_calls = 0

    async def run_k6_process(self, **_kwargs):
        self.run_calls += 1


class FailingStateCallback:
    def __init__(self):
        self.calls = []

    def __call__(self, running: bool):
        self.calls.append(running)
        raise RuntimeError("UI already unmounted")


async def _run_controller_start(controller: RunController, callbacks: RunCallbacks):
    task = await controller.start_run({"k6": {"logging": {}}}, callbacks)
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

    asyncio.run(_run_controller_start(controller, callbacks))

    assert state_callback.calls == [True, False]
    assert service.run_calls == 1
