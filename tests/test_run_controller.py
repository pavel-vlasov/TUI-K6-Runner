import asyncio

from application.run_controller import RunCallbacks, RunController


class DummyService:
    def __init__(self) -> None:
        self.is_running = False
        self.calls = 0

    async def run_k6_process(self, **_kwargs):
        self.calls += 1
        self.is_running = True
        await asyncio.sleep(0.05)
        self.is_running = False


async def _run_twice_and_capture() -> tuple[int, list[str]]:
    service = DummyService()
    controller = RunController(service)
    logs: list[str] = []

    callbacks = RunCallbacks(
        on_log=logs.append,
        on_status=lambda _msg: None,
        on_run_state_changed=lambda _running: None,
    )

    config = {"k6": {"logging": {"outputToUI": True}}}

    first_task = await controller.start_run(config, callbacks)
    second_task = await controller.start_run(config, callbacks)

    assert second_task is None
    assert first_task is not None
    await first_task
    return service.calls, logs


def test_start_run_blocks_second_ui_launch_while_first_pending():
    calls, logs = asyncio.run(_run_twice_and_capture())

    assert calls == 1
    assert any("Повторный запуск заблокирован" in line for line in logs)
