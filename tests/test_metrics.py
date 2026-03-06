from k6.metrics import extract_snapshot, format_metrics_snapshot
from k6.presenters import format_run_summary


def test_extract_snapshot_from_k6_status_payload():
    payload = {
        "metrics": {
            "http_reqs": {"rate": 31.5},
            "iterations": {"rate": 25.1},
            "http_req_duration": {"avg": 145.6, "p(95)": 220.8},
            "vus": {"value": 6},
            "vus_max": {"value": 20},
            "checks": {"rate": 0.99},
            "data_received": {"rate": 1024},
            "data_sent": {"rate": 512},
        }
    }

    snapshot = extract_snapshot(payload)

    assert snapshot["http_reqs_rate"] == 31.5
    assert snapshot["iterations_rate"] == 25.1
    assert snapshot["latency_avg_ms"] == 145.6
    assert snapshot["latency_p95_ms"] == 220.8
    assert snapshot["vus"] == 6


def test_format_metrics_snapshot_contains_main_sections():
    rendered = format_metrics_snapshot({"http_reqs_rate": 10.0, "vus": 2})

    assert "Metrics (xk6-top style)" in rendered
    assert "Req Rate:" in rendered
    assert "Req Rate chart" in rendered
    assert "VUs:" in rendered


def test_extract_snapshot_accepts_raw_metrics_payload_from_sse():
    payload = {
        "http_reqs": {"rate": 15.0},
        "http_req_duration": {"avg": 120.5},
        "vus": {"value": 3},
    }

    snapshot = extract_snapshot(payload)

    assert snapshot["http_reqs_rate"] == 15.0
    assert snapshot["latency_avg_ms"] == 120.5
    assert snapshot["vus"] == 3


def test_format_run_summary_contains_counts():
    summary = format_run_summary(12, 3)

    assert "Run summary" in summary
    assert "Total processed:" in summary
    assert "12" in summary
    assert "3" in summary


def test_extract_snapshot_ignores_timestamp_like_checks_value():
    payload = {
        "checks": {"value": 1772804950362},
        "http_reqs": {"rate": 42.0},
    }

    snapshot = extract_snapshot(payload)

    assert snapshot["checks_rate"] is None
    assert snapshot["http_reqs_rate"] == 42.0
