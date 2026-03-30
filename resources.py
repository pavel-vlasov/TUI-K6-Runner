import sys
from pathlib import Path


class ResourceLocator:
    """Resolve packaged resources and writable user data paths consistently."""

    def __init__(self, user_data_root: Path | None = None) -> None:
        self._resource_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        self._explicit_user_data_root = user_data_root.resolve() if user_data_root else None

    @property
    def resource_root(self) -> Path:
        return self._resource_root

    @property
    def user_data_root(self) -> Path:
        if self._explicit_user_data_root is not None:
            return self._explicit_user_data_root
        return Path.cwd().resolve()

    def resource_path(self, *parts: str) -> Path:
        return self._resource_root.joinpath(*parts)

    def user_data_path(self, *parts: str) -> Path:
        return self.user_data_root.joinpath(*parts)

    def style_path(self) -> Path:
        return self.resource_path("style.tcss")

    def schema_path(self) -> Path:
        return self.resource_path("schema", "test_config.schema.json")

    def test_script_path(self) -> Path:
        return self.resource_path("test.js")

    def default_config_path(self) -> Path:
        return self.user_data_path("test_config.json")

    def artifacts_dir(self) -> Path:
        return self.user_data_path("artifacts")


def get_resource_locator() -> ResourceLocator:
    return ResourceLocator()
