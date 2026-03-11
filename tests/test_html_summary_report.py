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


def test_build_html_summary_handles_root_group_dict_shapes_and_scalar_values():
    summary_json = {
        "metrics": {},
        "root_group": {
            "checks": {
                "check-a": {"passes": 2, "fails": 1},
                "broken": "invalid",
            },
            "groups": {
                "nested": {
                    "checks": {
                        "check-b": {"passes": 3, "fails": 0},
                        "also-broken": 123,
                    },
                    "groups": {
                        "deep": {
                            "checks": ["bad", {"passes": 1, "fails": 2}],
                            "groups": "not-a-collection",
                        }
                    },
                }
            },
        },
    }

    html = build_html_summary(summary_json)

    assert "Check passes" in html and ">6<" in html
    assert "Check failures" in html and ">3<" in html


def test_build_html_summary_normalizes_metric_types_for_grouping():
    summary_json = {
        "metrics": {
            "http_req_duration": {
                "type": "Trend",
                "contains": "time",
                "values": {"avg": 21.38, "min": 0.26, "max": 143.33, "med": 20.09, "p(90)": 26.36},
            },
            "http_req_failed": {
                "type": "Rate",
                "contains": "default",
                "values": {"rate": 0.4, "passes": 349, "fails": 529},
            },
        },
        "root_group": {"checks": [], "groups": []},
    }

    html = build_html_summary(summary_json)

    assert "http_req_duration" in html
    assert "21.38" in html
    assert "http_req_failed" in html
    assert "529" in html


def test_build_html_summary_handles_flat_metric_values_without_values_node():
    summary_json = {
        "metrics": {
            "http_reqs": {
                "type": "counter",
                "contains": "default",
                "count": 878,
                "rate": 34.9,
            },
            "http_req_failed": {
                "type": "rate",
                "contains": "default",
                "passes": 349,
                "fails": 529,
                "rate": 0.4,
            },
            "http_req_duration": {
                "contains": "time",
                "avg": 21.38,
                "min": 0.26,
                "max": 143.33,
                "med": 20.09,
                "p(90)": 26.36,
                "p(95)": 30.03,
                "p(99)": 39.58,
                "thresholds": {"p(95)<30": False},
            },
        },
        "root_group": {"checks": [{"passes": 42, "fails": 0}], "groups": []},
    }

    html = build_html_summary(summary_json)

    assert "<h3>Total requests</h3><p>878</p>" in html
    assert "<h3>Failed requests</h3><p>349</p>" in html
    assert "http_req_duration" in html
    assert "21.38" in html
    assert "p(95)&lt;30: failed" in html


def test_build_html_summary_has_tab_switching_script():
    html = build_html_summary({"metrics": {}, "root_group": {"checks": [], "groups": []}})

    assert "data-tab-target=\"detailed-metrics\"" in html
    assert "activateTab" in html


def test_build_html_summary_uses_rate_value_fallback_for_rate_metrics():
    summary_json = {
        "metrics": {
            "http_req_failed": {
                "type": "rate",
                "contains": "default",
                "value": 0.0,
                "passes": 0,
                "fails": 20,
            },
        },
        "root_group": {"checks": [], "groups": []},
    }

    html = build_html_summary(summary_json)

    assert "http_req_failed" in html
    assert "<td>0.00</td>" in html


def test_build_html_summary_applies_requested_summary_card_colors():
    html = build_html_summary({"metrics": {}, "root_group": {"checks": [], "groups": []}})

    assert '<div class="card red"><h3>Threshold failures</h3>' in html
    assert '<div class="card green"><h3>Check passes</h3>' in html


def test_build_html_summary_uses_http_req_failed_passes_as_failed_request_count():
    summary_json = {
        "metrics": {
            "http_reqs": {"type": "counter", "values": {"count": 20}},
            "http_req_failed": {
                "type": "rate",
                "values": {"rate": 0.0, "passes": 0, "fails": 20},
            },
        },
        "root_group": {"checks": [], "groups": []},
    }

    html = build_html_summary(summary_json)

    assert "<h3>Total requests</h3><p>20</p>" in html
    assert "<h3>Failed requests</h3><p>0</p>" in html


def test_build_html_summary_swaps_http_req_failed_rate_columns_for_human_readability():
    summary_json = {
        "metrics": {
            "http_req_failed": {
                "type": "rate",
                "values": {"rate": 0.0, "passes": 0, "fails": 20},
            },
        },
        "root_group": {"checks": [], "groups": []},
    }

    html = build_html_summary(summary_json)

    assert "http_req_failed" in html
    assert "<td>20</td><td>0</td>" in html


def test_build_html_summary_handles_threshold_result_with_failed_flag():
    summary_json = {
        "metrics": {
            "http_req_duration": {
                "type": "trend",
                "values": {"avg": 150.0},
                "thresholds": {
                    "p(95)<20": {"failed": True},
                },
            },
        },
        "root_group": {"checks": [], "groups": []},
    }

    html = build_html_summary(summary_json)

    assert "Threshold failures" in html
    assert ">1<" in html
    assert "p(95)&lt;20: failed" in html
