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
