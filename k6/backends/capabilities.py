from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionCapabilities:
    can_stop: bool
    can_scale: bool
    can_capture_logs: bool
    can_read_metrics: bool
