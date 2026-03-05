from app_bootstrap import ensure_runtime_dependencies

ensure_runtime_dependencies()

from app import K6TestApp


if __name__ == "__main__":
    K6TestApp().run()
