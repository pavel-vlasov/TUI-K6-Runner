from k6.output_parser import (
    get_fail_category,
    is_fail_line,
    is_run_complete_line,
    is_scenario_progress_line,
    is_success_line,
)


def test_detects_success_line():
    line = 'time="2025-01-01" level=info msg="Processed request: 200 ✅"'
    assert is_success_line(line)


def test_detects_fail_line_non_200():
    line = 'time="2025-01-01" level=error msg="Non-200 status: 500"'
    assert is_fail_line(line)


def test_extracts_non_200_http_category_from_status():
    line = 'time="2025-01-01" level=error msg="❌ Non-200 Response (Endpoint 1) | Correlation-Id: c1 | Status: 503"'
    assert get_fail_category(line) == "HTTP 503"


def test_detects_eof_failure_category_from_request_failed_log():
    line = 'time="2026-03-12T11:15:55+03:00" level=warning msg="Request Failed" error="Get "https://www.baseURL.com/xxxx/healthcheck": EOF"'
    assert is_fail_line(line)
    assert get_fail_category(line) == "EOF"


def test_detects_scenario_progress_line():
    line = "default [  42% ] 21/50 VUs  00m12.5s/00m30.0s"
    assert is_scenario_progress_line(line)


def test_detects_run_complete_line():
    line = "default [ 100% ] 0/10 VUs  10s/10s"
    assert is_run_complete_line(line)
