import asyncio

from k6.service import K6Service


class _FakeStream:
    async def readline(self):
        return b""


class _FakeProcess:
    def __init__(self) -> None:
        self.stdout = _FakeStream()
        self.stderr = _FakeStream()

    async def wait(self):
        return 0


class _FakeManager:
    def __init__(self) -> None:
        self.process = None

    async def start_run(self):
        self.process = _FakeProcess()
        return self.process

    async def stream_metrics_events(self):
        yield "metric", '{"name":"http_reqs","type":"counter"}'
        yield "metric", '{"name":"http_req_duration","type":"trend"}'
        yield "metric", '{"name":"vus","type":"gauge"}'
        yield "snapshot", '[[1772804950362, 100, 12.5], [1772804950362, 150.2, 190.5, 160.0, 120.0, 175.0, 188.0, 195.0], [1772804950362, 3]]'

    def clear_process(self):
        self.process = None


async def _collect_metrics_output() -> list[str]:
    service = K6Service()
    service.process_manager = _FakeManager()

    logs: list[str] = []
    metrics: list[str] = []

    await service.run_k6_process(
        on_log=logs.append,
        on_status=lambda _msg: None,
        output_to_ui=True,
        on_metrics=metrics.append,
    )

    return metrics


def test_metrics_stream_parses_single_metric_object_and_matrix_snapshot():
    metrics = asyncio.run(_collect_metrics_output())
    rendered = "\n".join(metrics)

    assert "Req Rate: 12.50 req/s" in rendered
    assert "Req Duration: 150.20 ms" in rendered
    assert "VUs:" in rendered and "3" in rendered
