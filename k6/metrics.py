from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


TIMESTAMP_THRESHOLD = 1_000_000_000_000


def _as_number(value: Any) -> float | int | None:
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            return float(value) if "." in value else int(value)
        except ValueError:
            return None
    return None


def _pick(source: Mapping[str, Any] | None, *keys: str) -> float | int | None:
    if not isinstance(source, Mapping):
        return None

    for key in keys:
        if key in source:
            value = _as_number(source[key])
            if value is not None:
                return value
    return None


def _pick_rate(source: Mapping[str, Any] | None, *keys: str) -> float | int | None:
    value = _pick(source, *keys)
    if value is None:
        return None

    if isinstance(value, (int, float)) and value > TIMESTAMP_THRESHOLD:
        return None

    return value


def extract_snapshot(status_payload: Mapping[str, Any]) -> dict[str, float | int | None]:
    if not isinstance(status_payload, Mapping):
        metrics = {}
    elif isinstance(status_payload.get("metrics"), Mapping):
        metrics = status_payload.get("metrics", {})
    else:
        metrics = status_payload

    http_reqs = metrics.get("http_reqs", {})
    iterations = metrics.get("iterations", {})
    http_req_duration = metrics.get("http_req_duration", {})
    http_req_waiting = metrics.get("http_req_waiting", {})
    http_req_connecting = metrics.get("http_req_connecting", {})
    http_req_failed = metrics.get("http_req_failed", {})
    checks = metrics.get("checks", {})
    data_received = metrics.get("data_received", {})
    data_sent = metrics.get("data_sent", {})
    vus = metrics.get("vus", {})
    vus_max = metrics.get("vus_max", {})

    return {
        "http_reqs_rate": _pick_rate(http_reqs, "rate", "value"),
        "iterations_rate": _pick_rate(iterations, "rate", "value"),
        "latency_avg_ms": _pick(http_req_duration, "avg", "value"),
        "latency_p95_ms": _pick(http_req_duration, "p(95)", "p95"),
        "http_req_waiting_avg_ms": _pick(http_req_waiting, "avg", "value"),
        "http_req_connecting_avg_ms": _pick(http_req_connecting, "avg", "value"),
        "http_req_failed_rate": _pick_rate(http_req_failed, "rate", "value"),
        "checks_rate": _pick_rate(checks, "rate"),
        "checks_pass_rate": _pick_rate(checks, "passes", "value"),
        "data_received_rate": _pick_rate(data_received, "rate", "value"),
        "data_sent_rate": _pick_rate(data_sent, "rate", "value"),
        "vus": _pick(vus, "value", "current"),
        "vus_max": _pick(vus_max, "value", "max"),
    }


def _fmt_metric(value: float | int | None, suffix: str = "", precision: int = 2) -> str:
    if value is None:
        return "—"
    if isinstance(value, int):
        return f"{value}{suffix}"
    return f"{value:.{precision}f}{suffix}"


def _sparkline(values: Sequence[float | int], width: int = 56) -> str:
    if not values:
        return "—"

    blocks = "▁▂▃▄▅▆▇█"
    if len(values) > width:
        values = values[-width:]

    min_v = min(values)
    max_v = max(values)
    if max_v == min_v:
        return blocks[0] * len(values)

    chart = []
    for value in values:
        idx = int((value - min_v) / (max_v - min_v) * (len(blocks) - 1))
        chart.append(blocks[idx])
    return "".join(chart)


def format_metrics_snapshot(snapshot: Mapping[str, float | int | None], history: Sequence[float | int] | None = None) -> str:
    rate_history = list(history or [])
    min_rate = min(rate_history) if rate_history else None
    max_rate = max(rate_history) if rate_history else None

    return "\n".join(
        [
            "[bold cyan]📈 Metrics (xk6-top style)[/bold cyan]",
            "",
            "[bold]Top metrics[/bold]",
            (
                "Req Rate: "
                f"{_fmt_metric(snapshot.get('http_reqs_rate'), ' req/s')} | "
                "Req Duration: "
                f"{_fmt_metric(snapshot.get('latency_avg_ms'), ' ms')} | "
                "Req Failed: "
                f"{_fmt_metric(snapshot.get('http_req_failed_rate'), ' /s')} | "
                "Data Received: "
                f"{_fmt_metric(snapshot.get('data_received_rate'), ' B/s')} | "
                "Data Sent: "
                f"{_fmt_metric(snapshot.get('data_sent_rate'), ' B/s')}"
            ),
            "",
            "[bold]Req Rate chart[/bold]",
            _sparkline(rate_history),
            (
                f"min={_fmt_metric(min_rate)}  "
                f"max={_fmt_metric(max_rate)}  "
                f"now={_fmt_metric(snapshot.get('http_reqs_rate'))}"
            ),
            "",
            "[bold]Additional trends[/bold]",
            f"[bold]Iterations/s:[/bold] {_fmt_metric(snapshot.get('iterations_rate'), ' it/s')}",
            f"[bold]Latency p95:[/bold] {_fmt_metric(snapshot.get('latency_p95_ms'), ' ms')}",
            f"[bold]HTTP waiting avg:[/bold] {_fmt_metric(snapshot.get('http_req_waiting_avg_ms'), ' ms')}",
            f"[bold]HTTP connecting avg:[/bold] {_fmt_metric(snapshot.get('http_req_connecting_avg_ms'), ' ms')}",
            f"[bold]Checks/s:[/bold] {_fmt_metric(snapshot.get('checks_rate'), ' checks/s')}",
            f"[bold]Checks pass:[/bold] {_fmt_metric(snapshot.get('checks_pass_rate'))}",
            f"[bold]VUs:[/bold] {_fmt_metric(snapshot.get('vus'))}",
            f"[bold]VUs max:[/bold] {_fmt_metric(snapshot.get('vus_max'))}",
        ]
    )


def format_final_metrics_summary(snapshot: Mapping[str, float | int | None]) -> str:
    return "\n".join(
        [
            "\n[bold magenta]📊 k6 metrics summary[/bold magenta]",
            f"[bold]HTTP req/s:[/bold] {_fmt_metric(snapshot.get('http_reqs_rate'), ' req/s')}",
            f"[bold]Latency avg/p95:[/bold] {_fmt_metric(snapshot.get('latency_avg_ms'), ' ms')} / {_fmt_metric(snapshot.get('latency_p95_ms'), ' ms')}",
            f"[bold]Checks/s:[/bold] {_fmt_metric(snapshot.get('checks_rate'), ' checks/s')}",
            f"[bold]HTTP req failed/s:[/bold] {_fmt_metric(snapshot.get('http_req_failed_rate'), ' /s')}",
            f"[bold]Data recv/s:[/bold] {_fmt_metric(snapshot.get('data_received_rate'), ' B/s')}",
            f"[bold]Data sent/s:[/bold] {_fmt_metric(snapshot.get('data_sent_rate'), ' B/s')}",
        ]
    )
