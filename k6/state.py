from dataclasses import dataclass


@dataclass
class K6State:
    success_count: int = 0
    fail_count: int = 0
    fail_4xx_count: int = 0
    fail_500_count: int = 0
    fail_5xx_except_500_count: int = 0
    status_running: str = "Waiting for the run..."
    status_default: str = "Prepairing..."
    last_counter: str = "✅ 0  │  ❌ 0"
    is_running: bool = False
    current_vus_internal: int = 1
