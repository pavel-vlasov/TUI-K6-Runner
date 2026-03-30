from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExecutionCapabilities:
    can_stop: bool
    can_scale: bool
    can_capture_logs: bool
    can_read_metrics: bool


@dataclass
class K6State:
    success_count: int = 0
    fail_count: int = 0
    fail_categories: dict[str, int] = field(default_factory=dict)
    status_running: str = "Waiting for the run..."
    status_default: str = "Preparing..."
    last_counter: str = "✅ 0  │  ❌ 0"
    is_running: bool = False
    current_vus_internal: int = 1
