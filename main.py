import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import K6TestApp
from app_bootstrap import ensure_runtime_dependencies


def main() -> None:
    ensure_runtime_dependencies()
    K6TestApp().run()


if __name__ == "__main__":
    main()
