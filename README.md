# TUI-K6-Runner

[![Quality Pipeline](https://github.com/pavel-vlasov/TUI-K6-Runner/actions/workflows/ci.yml/badge.svg?branch=main&event=push)](https://github.com/pavel-vlasov/TUI-K6-Runner/actions/workflows/ci.yml)
[![Python version](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/downloads/release/python-3110/)

A terminal UI application for configuring and running k6 load tests with real-time feedback.

<img width="1102" height="618" alt="image" src="https://github.com/user-attachments/assets/c4d43c8a-66bf-4ee4-aac3-feb11462fb2d" />

<img width="1118" height="677" alt="image" src="https://github.com/user-attachments/assets/3cef3d48-81fd-4fc7-83ee-445371efc5dc" />

<img width="1118" height="682" alt="image" src="https://github.com/user-attachments/assets/e05ea0ed-60fe-4cd5-bc42-3d5e529745af" />

## Installation

### Requirements

- Python **3.11.x**
- [k6](https://grafana.com/docs/k6/latest/set-up/install-k6/) installed and available in `PATH`

### Setup

```bash
pip install --require-hashes -r requirements-dev.txt
```

## Usage

Run the application:

```bash
python main.py
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
