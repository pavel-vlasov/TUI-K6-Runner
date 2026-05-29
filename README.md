# TUI-K6-Runner

[![Quality Pipeline](https://github.com/pavel-vlasov/TUI-K6-Runner/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/pavel-vlasov/TUI-K6-Runner/actions/workflows/ci.yml)
[![Python version](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/downloads/release/python-3110/)

A terminal UI application for configuring and running k6 load tests with real-time feedback.



## Installation

### Requirements

- Python **3.11.x**
- [k6](https://grafana.com/docs/k6/latest/set-up/install-k6/) installed and available in `PATH`

### Install from Git

Install the runnable CLI directly from GitHub:

```bash
pip install "git+https://github.com/pavel-vlasov/TUI-K6-Runner.git"
```

Install a specific tag or branch when you need a reproducible version:

```bash
pip install "git+https://github.com/pavel-vlasov/TUI-K6-Runner.git@v0.1.0"
```

After installation, start the application with:

```bash
tui-k6-runner
```

The first run in a directory that does not already contain `test.js` creates the packaged k6 script there, next to the generated `test_config.json`.

### Development setup

```bash
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

### Quality checks

```bash
ruff check .
pytest -q
pip-audit
bandit -r .
```

### Dependency policy

- `pyproject.toml` is the only source of truth.
- No requirements lock files are used.
- CI intentionally installs latest compatible dependencies according to `pyproject.toml`.
- If CI fails after dependency updates, either fix code or add version constraints in `pyproject.toml`.

## Usage

Run the application from a source checkout:

```bash
python main.py
```

Run the installed CLI:

```bash
tui-k6-runner
```

If `k6` is not found in `PATH`, the app stops at startup with a clear error.

## Key Features

- Interactive TUI for test setup and execution
- Support for multiple authentication modes
- Runtime configuration validation
- Built-in k6 output parsing and run state tracking
- Optional HTML summary report integration

## Execution Modes

The app supports these k6 execution modes:

- External executor
- Spike Tests
- Constant VUs
- Constant Arrival Rate
- Ramping Arrival Rate

## Architecture

Core modules are split by responsibility:

- `main.py` — application bootstrap and startup
- `app.py` — `K6TestApp` composition and app initialization
- `app_mixins/` — UI, events, request, and stage behavior
- `k6/` — process control, state management, output parsing, and presentation logic
- `schema/test_config.schema.json` — runtime configuration schema

Configuration flow:

- `ui_config` stores editable UI state
- `runtime_config` is built from `ui_config` right before validation and execution
