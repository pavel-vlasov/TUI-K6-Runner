from app_bootstrap import ensure_runtime_dependencies


def main(app_cls=None) -> None:
    ensure_runtime_dependencies()

    if app_cls is None:
        from app import K6TestApp

        app_cls = K6TestApp

    app_cls().run()


if __name__ == "__main__":
    main()
