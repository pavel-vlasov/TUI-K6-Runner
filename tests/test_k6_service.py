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

    service._handle_counter_lines('time="2025" level=error msg="❌ Non-200 Response (ep) | Correlation-Id: c1 | Status: 500"', statuses.append)
    service._handle_counter_lines('time="2025" level=warning msg="Request Failed" error="Get "https://x": EOF"', statuses.append)

    assert service.state.fail_count == 2
    assert service.state.fail_categories["HTTP 500"] == 1
    assert service.state.fail_categories["EOF"] == 1
    assert "errors:" in service.state.last_counter
    assert "HTTP 500: 1" in service.state.last_counter
    assert "EOF: 1" in service.state.last_counter
    assert "\n" not in service.state.last_counter
