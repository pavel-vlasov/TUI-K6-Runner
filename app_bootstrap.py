import os
import subprocess
import sys


def install_package(package: str) -> None:
    print(f"Installing {package}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", package])


def ensure_runtime_dependencies() -> None:
    try:
        import textual  # noqa: F401
        import pyperclip  # noqa: F401
    except ImportError:
        install_package("textual")
        install_package("pyperclip")
        os.execl(sys.executable, sys.executable, *sys.argv)


def get_resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)
