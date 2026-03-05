from app import K6TestApp
from app_bootstrap import ensure_runtime_dependencies


def main() -> None:
    ensure_runtime_dependencies()
    K6TestApp().run()


if __name__ == "__main__":
    main()
