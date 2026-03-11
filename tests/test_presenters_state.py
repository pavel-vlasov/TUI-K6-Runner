from k6.presenters import (
    format_done_status,
    format_running_status,
    format_start_log,
    format_start_status,
)
from k6.state import K6State


def test_presenters_render_expected_fragments():
    running = format_running_status("cnt", "run", "def")
    assert "cnt" in running and "run" in running and "def" in running

    done = format_done_status("final")
    assert "Done" in done and "final" in done

    assert "Preparing test execution" in format_start_status()
    assert "Starting k6 test" in format_start_log()


def test_k6_state_defaults():
    state = K6State()

    assert state.success_count == 0
    assert state.fail_count == 0
    assert state.is_running is False
    assert state.current_vus_internal == 1
