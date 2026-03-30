from app_bootstrap import ensure_runtime_dependencies

# Exposed for tests that monkeypatch main.K6TestApp directly.
K6TestApp = None


def main(app_cls=None) -> None:
    ensure_runtime_dependencies()

    if app_cls is None:
        selected_app_cls = K6TestApp
        if selected_app_cls is None:
            from app import K6TestApp as imported_k6_test_app

            selected_app_cls = imported_k6_test_app
    else:
        selected_app_cls = app_cls

    selected_app_cls().run()


if __name__ == "__main__":
    main()
