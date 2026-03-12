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


def test_detects_fail_line_non_200_with_status():
    line = 'time="2025-01-01" level=error msg="❌ Non-200 Response (ep) | Correlation-Id: c1 | Status: 500"'
    assert is_fail_line(line)


def test_maps_4xx_category_from_non_200_status():
    line = 'time="2025-01-01" level=error msg="❌ Non-200 Response (Endpoint 1) | Correlation-Id: c1 | Status: 404"'
    assert get_fail_category(line) == "4xx"


def test_maps_500_category_from_non_200_status():
    line = 'time="2025-01-01" level=error msg="❌ Non-200 Response (Endpoint 1) | Correlation-Id: c1 | Status: 500"'
    assert get_fail_category(line) == "500"


def test_maps_5xx_not_500_category_from_non_200_status():
    line = 'time="2025-01-01" level=error msg="❌ Non-200 Response (Endpoint 1) | Correlation-Id: c1 | Status: 503"'
    assert get_fail_category(line) == "5xx (not 500)"


def test_non_200_without_3digit_status_is_not_counted():
    line = 'time="2025-01-01" level=error msg="❌ Non-200 Response (Endpoint 1) | Correlation-Id: c1 | Status: 0"'
    assert get_fail_category(line) is None
    assert not is_fail_line(line)


def test_detects_eof_failure_category_from_request_failed_log():
    line = 'time="2026-03-12T11:15:55+03:00" level=warning msg="Request Failed" error="Get "https://www.baseURL.com/xxxx/healthcheck": EOF"'
    assert is_fail_line(line)
    assert get_fail_category(line) == "EOF"


def test_request_failed_without_eof_is_not_counted_to_avoid_double_counting():
    line = 'time="2026-03-12T11:15:55+03:00" level=warning msg="Request Failed" error="Get "https://www.baseURL.com/xxxx/healthcheck": context deadline exceeded"'
    assert get_fail_category(line) is None
    assert not is_fail_line(line)


def test_detects_scenario_progress_line():
    line = "default [  42% ] 21/50 VUs  00m12.5s/00m30.0s"
    assert is_scenario_progress_line(line)


def test_detects_run_complete_line():
    line = "default [ 100% ] 0/10 VUs  10s/10s"
    assert is_run_complete_line(line)


def test_parse_http_status_code_from_non_200_line():
    line = 'time="2025-01-01" level=error msg="Non-200 status: 503"'
    assert parse_http_status_code(line) == 503


def test_parse_http_status_code_returns_none_for_line_without_code():
    line = 'time="2025-01-01" level=error msg="Non-200 status"'
    assert parse_http_status_code(line) is None
