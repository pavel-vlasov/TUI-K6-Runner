from k6.service import K6Service


def test_build_summary_paths_uses_timestamped_files(monkeypatch):
    class FrozenDatetime:
        @classmethod
        def now(cls):
            class _D:
                def strftime(self, _fmt):
                    return "20260307_195400"

            return _D()

    monkeypatch.setattr("k6.service.datetime", FrozenDatetime)

    service = K6Service()
    json_path, html_path = service._build_summary_paths()

    assert str(json_path).endswith("artifacts/summary_20260307_195400.json")
    assert str(html_path).endswith("artifacts/summary_20260307_195400.html")


def test_handle_counter_lines_accumulates_categories_and_totals():
    service = K6Service()
    statuses = []

    service._handle_counter_lines('time="2025" level=error msg="❌ Non-200 Response (ep) | Correlation-Id: c1 | Status: 404"', statuses.append)
    service._handle_counter_lines('time="2025" level=error msg="❌ Non-200 Response (ep) | Correlation-Id: c2 | Status: 500"', statuses.append)
    service._handle_counter_lines('time="2025" level=error msg="❌ Non-200 Response (ep) | Correlation-Id: c3 | Status: 503"', statuses.append)
    service._handle_counter_lines('time="2025" level=warning msg="Request Failed" error="Get "https://x": EOF"', statuses.append)

    assert service.state.fail_count == 4
    assert service.state.fail_categories["4xx"] == 1
    assert service.state.fail_categories["500"] == 1
    assert service.state.fail_categories["5xx (not 500)"] == 1
    assert service.state.fail_categories["EOF"] == 1
    assert "errors:" in service.state.last_counter
    assert "4xx: 1" in service.state.last_counter
    assert "500: 1" in service.state.last_counter
    assert "5xx (not 500): 1" in service.state.last_counter
    assert "EOF: 1" in service.state.last_counter
    assert "\n" not in service.state.last_counter


def test_request_failed_without_eof_is_not_double_counted():
    service = K6Service()
    statuses = []

    service._handle_counter_lines('time="2025" level=warning msg="Request Failed" error="Get "https://x": context deadline exceeded"', statuses.append)

    assert service.state.fail_count == 0
    assert service.state.fail_categories == {}


def test_non_200_status_zero_is_filtered_from_ui_and_not_counted():
    service = K6Service()
    statuses = []

    handled = service._handle_counter_lines(
        'time="2026-03-12T14:07:46+03:00" level=info msg="❌ Non-200 Response (Endpoint 1) | Correlation-Id: 928cc85a-a8f7-429e-b7bc-7167e664f1fe | Status: 0" source=console',
        statuses.append,
    )

    assert handled is True
    assert service.state.fail_count == 0
    assert service.state.fail_categories == {}
