from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any

DEFAULT_TITLE_PREFIX = "Test Report"
OTHER_METRICS = {
    "iterations",
    "data_sent",
    "checks",
    "http_reqs",
    "data_received",
    "vus_max",
    "vus",
    "http_req_duration{expected_response:true}",
}


def build_html_summary(summary_json: dict, title: str | None = None) -> str:
    """Build an HTML summary report from k6 summary JSON.

    The calculation logic follows k6-reporter's report.js:
    - thresholdCount / thresholdFailures
    - recursive check pass/fail counting from root_group
    - metric grouping by trend/rate/counter/gauge and excluding special metrics
    """
    data = summary_json or {}
    metrics = data.get("metrics", {}) or {}

    metric_names = sorted(metrics.keys())

    threshold_count = 0
    threshold_failures = 0
    for metric_name in metric_names:
        metric = metrics.get(metric_name, {}) or {}
        thresholds = metric.get("thresholds") or {}
        if thresholds:
            threshold_count += 1
            for threshold in thresholds.values():
                if not threshold.get("ok", True):
                    threshold_failures += 1

    check_passes, check_failures = _count_checks_in_group(data.get("root_group") or {})

    grouped_metrics = {
        "trend": [m for m in metric_names if _metric_type(metrics, m) == "trend" and m not in OTHER_METRICS],
        "rate": [m for m in metric_names if _metric_type(metrics, m) == "rate" and m not in OTHER_METRICS],
        "counter": [m for m in metric_names if _metric_type(metrics, m) == "counter" and m not in OTHER_METRICS],
        "gauge": [m for m in metric_names if _metric_type(metrics, m) == "gauge" and m not in OTHER_METRICS],
    }

    report_title = title or f"{DEFAULT_TITLE_PREFIX}: {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    return HTML_TEMPLATE.format(
        title=escape(report_title),
        threshold_count=threshold_count,
        threshold_failures=threshold_failures,
        check_passes=check_passes,
        check_failures=check_failures,
        trend_rows=_render_metric_rows(grouped_metrics["trend"], metrics),
        rate_rows=_render_metric_rows(grouped_metrics["rate"], metrics),
        counter_rows=_render_metric_rows(grouped_metrics["counter"], metrics),
        gauge_rows=_render_metric_rows(grouped_metrics["gauge"], metrics),
        other_rows=_render_metric_rows([m for m in metric_names if m in OTHER_METRICS], metrics),
    )


def _metric_type(metrics: dict[str, dict[str, Any]], metric_name: str) -> str:
    return str((metrics.get(metric_name) or {}).get("type", ""))


def _count_checks_in_group(group: dict[str, Any]) -> tuple[int, int]:
    passes = 0
    fails = 0

    for check in group.get("checks", []) or []:
        passes += int(check.get("passes", 0) or 0)
        fails += int(check.get("fails", 0) or 0)

    for subgroup in group.get("groups", []) or []:
        sub_passes, sub_fails = _count_checks_in_group(subgroup)
        passes += sub_passes
        fails += sub_fails

    return passes, fails


def _render_metric_rows(metric_names: list[str], metrics: dict[str, dict[str, Any]]) -> str:
    if not metric_names:
        return '<tr><td colspan="4">No metrics</td></tr>'

    rows: list[str] = []
    for name in metric_names:
        metric = metrics.get(name, {}) or {}
        contains = metric.get("contains", "")
        values = metric.get("values", {}) or {}
        values_compact = ", ".join(f"{k}={v}" for k, v in sorted(values.items())) if values else "-"
        th_summary = _render_threshold_summary(metric)
        rows.append(
            "<tr>"
            f"<td>{escape(name)}</td>"
            f"<td>{escape(str(contains))}</td>"
            f"<td>{escape(values_compact)}</td>"
            f"<td>{escape(th_summary)}</td>"
            "</tr>"
        )

    return "".join(rows)


def _render_threshold_summary(metric: dict[str, Any]) -> str:
    thresholds = metric.get("thresholds") or {}
    if not thresholds:
        return "-"

    parts: list[str] = []
    for threshold_name, threshold_result in thresholds.items():
        status = "ok" if threshold_result.get("ok", True) else "failed"
        parts.append(f"{threshold_name}: {status}")
    return "; ".join(parts)


HTML_TEMPLATE = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{title}</title>
  <style>
    body {{ font-family: Inter, Arial, sans-serif; margin: 24px; color: #1f2937; }}
    h1 {{ margin-bottom: 8px; }}
    .cards {{ display: flex; gap: 12px; margin: 16px 0 24px; flex-wrap: wrap; }}
    .card {{ border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 16px; min-width: 220px; }}
    .label {{ font-size: 12px; color: #6b7280; text-transform: uppercase; }}
    .value {{ font-size: 28px; font-weight: 700; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 24px; }}
    th, td {{ border: 1px solid #e5e7eb; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f3f4f6; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <div class=\"cards\">
    <div class=\"card\"><div class=\"label\">Threshold failures</div><div class=\"value\">{threshold_failures}</div><div>{threshold_count} metrics with thresholds</div></div>
    <div class=\"card\"><div class=\"label\">Check passes</div><div class=\"value\">{check_passes}</div></div>
    <div class=\"card\"><div class=\"label\">Check failures</div><div class=\"value\">{check_failures}</div></div>
  </div>

  <h2>Trend metrics</h2>
  <table><thead><tr><th>Metric</th><th>Contains</th><th>Values</th><th>Thresholds</th></tr></thead><tbody>{trend_rows}</tbody></table>

  <h2>Rate metrics</h2>
  <table><thead><tr><th>Metric</th><th>Contains</th><th>Values</th><th>Thresholds</th></tr></thead><tbody>{rate_rows}</tbody></table>

  <h2>Counter metrics</h2>
  <table><thead><tr><th>Metric</th><th>Contains</th><th>Values</th><th>Thresholds</th></tr></thead><tbody>{counter_rows}</tbody></table>

  <h2>Gauge metrics</h2>
  <table><thead><tr><th>Metric</th><th>Contains</th><th>Values</th><th>Thresholds</th></tr></thead><tbody>{gauge_rows}</tbody></table>

  <h2>Other stats</h2>
  <table><thead><tr><th>Metric</th><th>Contains</th><th>Values</th><th>Thresholds</th></tr></thead><tbody>{other_rows}</tbody></table>
</body>
</html>
"""
