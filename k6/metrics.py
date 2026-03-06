from __future__ import annotations

from collections.abc import Mapping
from typing import Any


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


def extract_snapshot(status_payload: Mapping[str, Any]) -> dict[str, float | int | None]:
    metrics = status_payload.get("metrics", {}) if isinstance(status_payload, Mapping) else {}

    http_reqs = metrics.get("http_reqs", {})
    iterations = metrics.get("iterations", {})
    http_req_duration = metrics.get("http_req_duration", {})
    vus = metrics.get("vus", {})
    vus_max = metrics.get("vus_max", {})
    checks = metrics.get("checks", {})
    data_received = metrics.get("data_received", {})
    data_sent = metrics.get("data_sent", {})

    return {
        "http_reqs_rate": _pick(http_reqs, "rate", "value"),
        "iterations_rate": _pick(iterations, "rate", "value"),
        "latency_avg_ms": _pick(http_req_duration, "avg", "value"),
        "latency_p95_ms": _pick(http_req_duration, "p(95)", "p95"),
        "vus": _pick(vus, "value", "current"),
        "vus_max": _pick(vus_max, "value", "max"),
        "checks_rate": _pick(checks, "rate", "value"),
        "data_received_rate": _pick(data_received, "rate", "value"),
        "data_sent_rate": _pick(data_sent, "rate", "value"),
    }


def _fmt_metric(value: float | int | None, suffix: str = "", precision: int = 2) -> str:
    if value is None:
        return "—"
    if isinstance(value, int):
        return f"{value}{suffix}"
    return f"{value:.{precision}f}{suffix}"


def format_metrics_snapshot(snapshot: Mapping[str, float | int | None]) -> str:
    return "\n".join(
        [
            "[bold cyan]📈 Metrics (xk6-top style)[/bold cyan]",
            "",
            f"[bold]HTTP req/s:[/bold] {_fmt_metric(snapshot.get('http_reqs_rate'), ' req/s')}",
            f"[bold]Iterations/s:[/bold] {_fmt_metric(snapshot.get('iterations_rate'), ' it/s')}",
            f"[bold]Latency avg:[/bold] {_fmt_metric(snapshot.get('latency_avg_ms'), ' ms')}",
            f"[bold]Latency p95:[/bold] {_fmt_metric(snapshot.get('latency_p95_ms'), ' ms')}",
            f"[bold]VUs:[/bold] {_fmt_metric(snapshot.get('vus'))}",
            f"[bold]VUs max:[/bold] {_fmt_metric(snapshot.get('vus_max'))}",
            f"[bold]Checks/s:[/bold] {_fmt_metric(snapshot.get('checks_rate'), ' checks/s')}",
            f"[bold]Data recv/s:[/bold] {_fmt_metric(snapshot.get('data_received_rate'), ' B/s')}",
            f"[bold]Data sent/s:[/bold] {_fmt_metric(snapshot.get('data_sent_rate'), ' B/s')}",
        ]
    )
