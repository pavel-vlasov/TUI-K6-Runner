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


def test_handle_counter_lines_tracks_fail_categories():
    service = K6Service()
    status_updates = []

    service._handle_counter_lines('level=error msg="Non-200 status: 404"', status_updates.append)
    service._handle_counter_lines('level=error msg="Non-200 status: 500"', status_updates.append)
    service._handle_counter_lines('level=error msg="Non-200 status: 503"', status_updates.append)

    assert service.state.fail_count == 3
    assert service.state.fail_4xx_count == 1
    assert service.state.fail_500_count == 1
    assert service.state.fail_5xx_except_500_count == 1
    assert "4xx=1" in service.state.last_counter
    assert "500=1" in service.state.last_counter
    assert "5xx(except 500)=1" in service.state.last_counter
