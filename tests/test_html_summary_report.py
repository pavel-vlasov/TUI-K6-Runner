from k6.html_summary_report import build_html_summary


def test_build_html_summary_handles_empty_checks():
    summary_json = {
        "metrics": {
            "http_req_duration": {
                "type": "trend",
                "contains": "time",
                "values": {"avg": 100.0},
            }
        },
        "root_group": {"checks": [], "groups": []},
    }

    html = build_html_summary(summary_json, title="Smoke")

    assert "Smoke" in html
    assert "Check passes" in html
    assert ">0<" in html
    assert "http_req_duration" in html


def test_build_html_summary_counts_failed_thresholds():
    summary_json = {
        "metrics": {
            "http_req_duration": {
                "type": "trend",
                "contains": "time",
                "values": {"avg": 150.0},
                "thresholds": {
                    "p(95)<200": {"ok": True},
                    "p(99)<100": {"ok": False},
                },
            }
        },
        "root_group": {"checks": [], "groups": []},
    }

    html = build_html_summary(summary_json)

    assert "Threshold failures" in html
    assert ">1<" in html
    assert "p(99)&lt;100: failed" in html


def test_build_html_summary_groups_mixed_metrics_and_excludes_special():
    summary_json = {
        "metrics": {
            "http_req_duration": {
                "type": "trend",
                "contains": "time",
                "values": {"avg": 80.0},
            },
            "custom_rate": {
                "type": "rate",
                "contains": "default",
                "values": {"rate": 0.98},
            },
            "custom_counter": {
                "type": "counter",
                "contains": "default",
                "values": {"count": 120},
            },
            "custom_gauge": {
                "type": "gauge",
                "contains": "default",
                "values": {"value": 4},
            },
            "checks": {
                "type": "rate",
                "contains": "default",
                "values": {"rate": 0.99},
            },
        },
        "root_group": {
            "checks": [{"passes": 3, "fails": 1}],
            "groups": [{"checks": [{"passes": 2, "fails": 0}], "groups": []}],
        },
    }

    html = build_html_summary(summary_json)

    assert "custom_rate" in html
    assert "custom_counter" in html
    assert "custom_gauge" in html
    assert "checks" in html
    assert "Check passes" in html and ">5<" in html
    assert "Check failures" in html and ">1<" in html


def test_build_html_summary_handles_boolean_threshold_values():
    summary_json = {
        "metrics": {
            "http_req_duration": {
                "type": "trend",
                "contains": "time",
                "values": {"avg": 150.0},
                "thresholds": {
                    "p(95)<200": True,
                    "p(99)<100": False,
                },
            }
        },
        "root_group": {"checks": [], "groups": []},
    }

    html = build_html_summary(summary_json)

    assert "Threshold failures" in html
    assert ">1<" in html
    assert "p(99)&lt;100: failed" in html


def test_build_html_summary_handles_dict_checks_and_groups_shapes():
    summary_json = {
        "metrics": {},
        "root_group": {
            "checks": {
                "status 200": {"passes": 2, "fails": 1},
                "raw": "unexpected",
            },
            "groups": {
                "nested": {
                    "checks": {"latency": {"passes": 3, "fails": 0}},
                    "groups": [],
                }
            },
        },
    }

    html = build_html_summary(summary_json)

    assert "Check passes" in html and ">5<" in html
    assert "Check failures" in html and ">1<" in html
