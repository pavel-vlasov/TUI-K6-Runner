from k6.output_parser import (
    is_fail_line,
    is_run_complete_line,
    is_scenario_progress_line,
    is_success_line,
    parse_http_status_code,
)


def test_detects_success_line():
    line = 'time="2025-01-01" level=info msg="Processed request: 200 ✅"'
    assert is_success_line(line)


def test_detects_fail_line_non_200():
    line = 'time="2025-01-01" level=error msg="Non-200 status: 500"'
    assert is_fail_line(line)


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
