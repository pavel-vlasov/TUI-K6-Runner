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

TREND_COLUMNS = ("avg", "min", "max", "med", "p(90)", "p(95)", "p(99)")
RATE_COLUMNS = ("rate", "passes", "fails")


def build_html_summary(summary_json: dict, title: str | None = None) -> str:
    """Build a styled HTML summary report from k6 summary JSON."""
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
                threshold_ok = threshold.get("ok", True) if isinstance(threshold, dict) else bool(threshold)
                if not threshold_ok:
                    threshold_failures += 1

    check_passes, check_failures = _count_checks_in_group(data.get("root_group") or {})

    grouped_metrics = {
        "trend": [m for m in metric_names if _metric_type(metrics, m) == "trend" and m not in OTHER_METRICS],
        "rate": [m for m in metric_names if _metric_type(metrics, m) == "rate" and m not in OTHER_METRICS],
        "counter": [m for m in metric_names if _metric_type(metrics, m) == "counter" and m not in OTHER_METRICS],
        "gauge": [m for m in metric_names if _metric_type(metrics, m) == "gauge" and m not in OTHER_METRICS],
    }

    report_title = title or f"{DEFAULT_TITLE_PREFIX}: {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    total_requests = _metric_value(metrics.get("http_reqs", {}), "count")
    failed_requests = _metric_value(metrics.get("http_req_failed", {}), "fails")

    return HTML_TEMPLATE.format(
        title=escape(report_title),
        total_requests=escape(_format_value(total_requests)),
        failed_requests=escape(_format_value(failed_requests)),
        threshold_failures=threshold_failures,
        check_failures=check_failures,
        trend_rows=_render_detailed_rows(grouped_metrics["trend"], metrics),
        rate_rows=_render_rate_rows(grouped_metrics["rate"], metrics),
        run_rows=_render_metric_rows(grouped_metrics["counter"] + grouped_metrics["gauge"], metrics),
        check_rows=_render_metric_rows([m for m in metric_names if m in OTHER_METRICS], metrics),
        threshold_rows=_render_threshold_rows(metric_names, metrics),
        threshold_count=threshold_count,
        check_passes=check_passes,
    )


def _metric_type(metrics: dict[str, dict[str, Any]], metric_name: str) -> str:
    metric_type = str((metrics.get(metric_name) or {}).get("type", ""))
    return metric_type.strip().lower()


def _metric_value(metric: dict[str, Any], key: str) -> Any:
    values = metric.get("values", {}) if isinstance(metric, dict) else {}
    if isinstance(values, dict):
        return values.get(key)
    return None


def _count_checks_in_group(group: Any) -> tuple[int, int]:
    passes = 0
    fails = 0

    if not isinstance(group, dict):
        return passes, fails

    for check in _iter_collection(group.get("checks")):
        if not isinstance(check, dict):
            continue
        passes += int(check.get("passes", 0) or 0)
        fails += int(check.get("fails", 0) or 0)

    for subgroup in _iter_collection(group.get("groups")):
        sub_passes, sub_fails = _count_checks_in_group(subgroup)
        passes += sub_passes
        fails += sub_fails

    return passes, fails


def _iter_collection(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return list(value.values())
    return []


def _render_detailed_rows(metric_names: list[str], metrics: dict[str, dict[str, Any]]) -> str:
    if not metric_names:
        return '<tr><td colspan="8">No metrics</td></tr>'

    rows: list[str] = []
    for name in metric_names:
        values = (metrics.get(name, {}) or {}).get("values", {}) or {}
        columns = "".join(f"<td>{escape(_format_value(values.get(col)))}</td>" for col in TREND_COLUMNS)
        rows.append(f"<tr><td class=\"metric-name\">{escape(name)}</td>{columns}</tr>")
    return "".join(rows)


def _render_rate_rows(metric_names: list[str], metrics: dict[str, dict[str, Any]]) -> str:
    if not metric_names:
        return '<tr><td colspan="4">No metrics</td></tr>'

    rows: list[str] = []
    for name in metric_names:
        values = (metrics.get(name, {}) or {}).get("values", {}) or {}
        columns = "".join(f"<td>{escape(_format_value(values.get(col)))}</td>" for col in RATE_COLUMNS)
        rows.append(f"<tr><td class=\"metric-name\">{escape(name)}</td>{columns}</tr>")
    return "".join(rows)


def _render_metric_rows(metric_names: list[str], metrics: dict[str, dict[str, Any]]) -> str:
    if not metric_names:
        return '<tr><td colspan="4">No metrics</td></tr>'

    rows: list[str] = []
    for name in metric_names:
        metric = metrics.get(name, {}) or {}
        contains = metric.get("contains", "")
        values = metric.get("values", {}) or {}
        values_compact = ", ".join(f"{k}={_format_value(v)}" for k, v in sorted(values.items())) if values else "-"
        th_summary = _render_threshold_summary(metric)
        rows.append(
            "<tr>"
            f"<td class=\"metric-name\">{escape(name)}</td>"
            f"<td>{escape(str(contains))}</td>"
            f"<td>{escape(values_compact)}</td>"
            f"<td>{escape(th_summary)}</td>"
            "</tr>"
        )

    return "".join(rows)



def _render_threshold_rows(metric_names: list[str], metrics: dict[str, dict[str, Any]]) -> str:
    rows: list[str] = []
    for name in metric_names:
        summary = _render_threshold_summary(metrics.get(name, {}) or {})
        if summary == "-":
            continue
        rows.append(f"<tr><td class=\"metric-name\">{escape(name)}</td><td>{escape(summary)}</td></tr>")
    if not rows:
        return '<tr><td colspan="2">No threshold details</td></tr>'
    return "".join(rows)

def _render_threshold_summary(metric: dict[str, Any]) -> str:
    thresholds = metric.get("thresholds") or {}
    if not thresholds:
        return "-"

    parts: list[str] = []
    for threshold_name, threshold_result in thresholds.items():
        threshold_ok = (
            threshold_result.get("ok", True)
            if isinstance(threshold_result, dict)
            else bool(threshold_result)
        )
        status = "ok" if threshold_ok else "failed"
        parts.append(f"{threshold_name}: {status}")
    return "; ".join(parts)


def _format_value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, int):
        return f"{value}"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


HTML_TEMPLATE = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{title}</title>
  <style>
    :root {{
      --bg: #f5f6fb;
      --text: #13233a;
      --muted: #d8dce8;
      --card-purple: linear-gradient(135deg, #5f72ff, #6e42c1);
      --card-red: linear-gradient(135deg, #ff7f88, #f35d65);
      --card-green: linear-gradient(135deg, #5fcb88, #43b777);
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Inter, Arial, sans-serif; background: var(--bg); color: var(--text); }}
    .container {{ max-width: 1220px; margin: 24px auto; padding: 0 16px 24px; }}
    .header {{ background: var(--card-purple); color: #fff; border-radius: 18px; padding: 24px 28px; font-size: 48px; font-weight: 700; }}
    .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin: 20px 0; }}
    .card {{ border-radius: 14px; color: #fff; padding: 18px 22px; box-shadow: 0 8px 18px rgba(23, 26, 42, 0.16); }}
    .card h3 {{ margin: 0; font-size: 14px; text-transform: uppercase; opacity: .9; }}
    .card p {{ margin: 10px 0 0; font-size: 52px; font-weight: 700; }}
    .purple {{ background: var(--card-purple); }}
    .red {{ background: var(--card-red); }}
    .green {{ background: var(--card-green); }}
    .panel {{ background: #fff; border: 1px solid #dbe0ec; border-radius: 14px; padding: 20px; }}
    .tabs {{ display: flex; gap: 8px; margin-bottom: 16px; }}
    .tab {{ border: 1px solid #dbe0ec; border-radius: 10px 10px 0 0; padding: 10px 14px; background: #eff2fa; font-weight: 600; color: #4b5f7a; }}
    .tab.active {{ background: #fff; color: #6941ff; }}
    h2 {{ margin: 18px 0 10px; font-size: 34px; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; overflow: hidden; border-radius: 10px; }}
    thead tr {{ background: var(--card-purple); color: #fff; }}
    th, td {{ padding: 10px 14px; border-bottom: 1px solid #e8ecf5; text-align: left; }}
    .metric-name {{ font-weight: 600; }}
    @media (max-width: 980px) {{
      .summary {{ grid-template-columns: repeat(2, minmax(180px, 1fr)); }}
      .header {{ font-size: 36px; }}
    }}
  </style>
</head>
<body>
  <div class=\"container\">
    <div class=\"header\">{title}</div>
    <div class="summary">
      <div class="card purple"><h3>Total requests</h3><p>{total_requests}</p></div>
      <div class="card red"><h3>Failed requests</h3><p>{failed_requests}</p></div>
      <div class="card green"><h3>Threshold failures</h3><p>{threshold_failures}</p></div>
      <div class="card purple"><h3>Check passes</h3><p>{check_passes}</p></div>
      <div class="card red"><h3>Check failures</h3><p>{check_failures}</p></div>
    </div>

    <div class="panel">
      <div class=\"tabs\">
        <div class=\"tab active\">Detailed Metrics</div>
        <div class=\"tab\">Test Run Details</div>
        <div class=\"tab\">Checks & Groups</div>
      </div>

      <h2>Trends & Times</h2>
      <table>
        <thead><tr><th>Metric</th><th>AVG</th><th>MIN</th><th>MAX</th><th>MED</th><th>P(90)</th><th>P(95)</th><th>P(99)</th></tr></thead>
        <tbody>{trend_rows}</tbody>
      </table>

      <h2>Rates</h2>
      <table>
        <thead><tr><th>Metric</th><th>RATE</th><th>PASSES</th><th>FAILS</th></tr></thead>
        <tbody>{rate_rows}</tbody>
      </table>

      <h2>Run details</h2>
      <table>
        <thead><tr><th>Metric</th><th>Contains</th><th>Values</th><th>Thresholds</th></tr></thead>
        <tbody>{run_rows}</tbody>
      </table>

      <h2>Checks & other stats</h2>
      <table>
        <thead><tr><th>Metric</th><th>Contains</th><th>Values</th><th>Thresholds</th></tr></thead>
        <tbody>{check_rows}</tbody>
      </table>

      <h2>Threshold details</h2>
      <table>
        <thead><tr><th>Metric</th><th>Thresholds</th></tr></thead>
        <tbody>{threshold_rows}</tbody>
      </table>

      <p><strong>Threshold metrics:</strong> {threshold_count} &nbsp; <strong>Check passes:</strong> {check_passes}</p>
    </div>
  </div>
</body>
</html>
"""
