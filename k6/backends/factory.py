from __future__ import annotations

from k6.backends.base import ExecutionBackend
from k6.backends.embedded import EmbeddedProcessBackend
from k6.backends.external_terminal import ExternalTerminalBackend


def select_backend(config: dict | None = None) -> ExecutionBackend:
    output_to_ui = True
    if config:
        output_to_ui = bool(config.get("k6", {}).get("logging", {}).get("outputToUI", True))
    if output_to_ui:
        return EmbeddedProcessBackend()
    return ExternalTerminalBackend()
