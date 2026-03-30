# TUI-K6-Runner

[![Quality Pipeline](https://github.com/pavel-vlasov/TUI-K6-Runner/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/pavel-vlasov/TUI-K6-Runner/actions/workflows/ci.yml)
[![Lint](https://img.shields.io/github/actions/workflow/status/pavel-vlasov/TUI-K6-Runner/ci.yml?branch=main&job=Lint&label=Lint)](https://github.com/pavel-vlasov/TUI-K6-Runner/actions/workflows/ci.yml)
[![Tests (summary)](https://img.shields.io/github/actions/workflow/status/pavel-vlasov/TUI-K6-Runner/ci.yml?branch=main&job=Tests&label=Tests%20(summary))](https://github.com/pavel-vlasov/TUI-K6-Runner/actions/workflows/ci.yml)
[![Tests Ubuntu](https://img.shields.io/github/actions/workflow/status/pavel-vlasov/TUI-K6-Runner/ci.yml?branch=main&job=Tests%20(ubuntu-latest)&label=Tests%20ubuntu)](https://github.com/pavel-vlasov/TUI-K6-Runner/actions/workflows/ci.yml)
[![Tests Windows](https://img.shields.io/github/actions/workflow/status/pavel-vlasov/TUI-K6-Runner/ci.yml?branch=main&job=Tests%20(windows-latest)&label=Tests%20windows)](https://github.com/pavel-vlasov/TUI-K6-Runner/actions/workflows/ci.yml)
[![Tests macOS](https://img.shields.io/github/actions/workflow/status/pavel-vlasov/TUI-K6-Runner/ci.yml?branch=main&job=Tests%20(macos-latest)&label=Tests%20macos)](https://github.com/pavel-vlasov/TUI-K6-Runner/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/github/actions/workflow/status/pavel-vlasov/TUI-K6-Runner/ci.yml?branch=main&job=Coverage&label=Coverage)](https://github.com/pavel-vlasov/TUI-K6-Runner/actions/workflows/ci.yml)
[![Security](https://img.shields.io/github/actions/workflow/status/pavel-vlasov/TUI-K6-Runner/ci.yml?branch=main&job=Security&label=Security)](https://github.com/pavel-vlasov/TUI-K6-Runner/actions/workflows/ci.yml)
[![Python version](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/downloads/release/python-3110/)

<img width="1102" height="618" alt="image" src="https://github.com/user-attachments/assets/c4d43c8a-66bf-4ee4-aac3-feb11462fb2d" />

<img width="1118" height="677" alt="image" src="https://github.com/user-attachments/assets/3cef3d48-81fd-4fc7-83ee-445371efc5dc" />

<img width="1118" height="682" alt="image" src="https://github.com/user-attachments/assets/e05ea0ed-60fe-4cd5-bc42-3d5e529745af" />

## CI test badges

- `Tests (summary)` — **strict gate**: job `Tests` (tests-summary) падает, если smoke или любая платформа в матрице tests завершились с ошибкой.
- `Tests ubuntu/windows/macos` — статусы отдельных платформ из матричного job `Tests (${{ matrix.os }})` для отслеживания частичных успехов.

## How to use

- install Python 3.11 (supported version is fixed to 3.11.x)
- install k6 and make sure the `k6` binary is available in your `PATH`
  (official guide: https://grafana.com/docs/k6/latest/set-up/install-k6/)
- install project dependencies from lock files (runtime + dev):

- canonical dependency source: `requirements.txt` (used both locally and in CI)

  ```bash
  pip install --require-hashes -r requirements-dev.txt
  ```

- run app using the only supported entrypoint:

  ```bash
  python main.py
  ```

If k6 is not available in `PATH`, the app will fail at startup with a clear `RuntimeError` and installation link.



## Dependency management

This project uses **pip-tools** as a single source of truth for dependencies.

- `requirements.in` — top-level runtime dependencies
- `requirements-dev.in` — top-level dev dependencies (includes runtime via `-r requirements.in`)
- `requirements.txt` — compiled runtime lock file (pinned + hashes)
- `requirements-dev.txt` — compiled dev lock file (pinned + hashes)
- `requirements-lock-tools.txt` — canonical lock toolchain versions used to compile lock files

### Canonical lock toolchain

Lock files must be generated only with the canonical toolchain below:

- `pip==26.0`
- `pip-tools==7.4.1`

These versions are pinned in `requirements-lock-tools.txt` and are validated in CI (version print + lock regeneration drift check).

### Update dependencies

Use the helper script to re-lock both files:

```bash
./scripts/update-dependencies.sh
```

The script always installs lock tooling from `requirements-lock-tools.txt`, so re-locking with ad-hoc `pip`/`pip-tools` versions is not supported.

Then install with:

```bash
pip install --require-hashes -r requirements-dev.txt
```


## Lint baseline and rollout plan

Ruff linting now uses an expanded baseline in `[tool.ruff.lint].select`:

- `E`, `F`
- `B` (bugbear)
- `I` (isort)
- `UP` (pyupgrade)
- `SIM` (flake8-simplify)
- `C4` (flake8-comprehensions)
- `ASYNC` (async anti-patterns)
- `RUF` (ruff-specific checks)

To avoid breaking CI in a single change, Phase 1 keeps a minimal temporary ignore list in `pyproject.toml` (including `E501` for now).

Rollout strategy:

1. Enable the full rule families above with the temporary baseline ignore list.
2. Reduce `ignore` in small, focused PRs (for example: import sorting first, then simplify/pyupgrade rules).
3. Remove `E501` after targeted line-wrap cleanup and keep line-length enforcement fully enabled.

## Coverage policy

- CI workflow `Coverage` запускает `pytest` с генерацией `coverage.xml`, но не валит job из-за упавших тестов в этом шаге.
- Порог также централизован в `.coveragerc` (`[report] fail_under = 80`) для локального и CI запуска с единым значением.
- Если итоговое покрытие ниже 80%, шаг Coverage завершается с ошибкой, и весь workflow получает статус **failed** (именно по проценту покрытия).

## Architecture note

The launch bootstrap is now in `main.py` only. The main UI and application behavior live in:

- `app.py` — `K6TestApp` composition and app initialization
- `app_mixins/` — UI/event/request/stage behavior split by responsibility
- `k6/` — k6 run state, process control, parsing and service/presenter logic

Please make future UI changes in these modules, not in legacy monolithic entrypoint implementations.

### Config flow in the app

- `ui_config` хранит актуальное состояние полей UI (read/write модель для экранов и миксинов).
- `runtime_config` строится из `ui_config` только перед валидацией/запуском и содержит финальный конфиг, который уходит в k6.
- В кодовой базе используется только имя `ui_config` для UI-модели конфигурации.

## Config schema

В проект добавлена JSON Schema: `schema/test_config.schema.json`.
Она описывает обязательные поля рантайм-конфига, enum-значения (например, `auth.mode`, `requestEndpoints[].method`, `k6.executionType`, `k6.logging.level`) и условные требования для разных режимов запуска.

Пример секции `auth` в JSON-конфиге (только через `auth.mode`):

```json
{
  "auth": {
    "mode": "oauth2_client_credentials",
    "client_id": "my-client",
    "client_secret": "my-secret",
    "token_url": "https://idp.example.com/oauth2/token",
    "scope": "read write"
  }
}
```

Поддерживаются только канонические значения `auth.mode`: `none`, `basic`, `client_id_enforcement`, `oauth2_client_credentials`.

Пример секции `k6.logging` (только канонические `level`):

```json
{
  "k6": {
    "logging": {
      "enabled": true,
      "level": "failed_without_payloads",
      "outputToUI": true,
      "webDashboard": false,
      "webDashboardUrl": "http://localhost:5665",
      "htmlSummaryReport": false
    }
  }
}
```

### Logging warnings

- Детальный лог может исказить результаты нагрузочного теста из-за дополнительного I/O.
- Не рекомендуется включать уровень `all` на production-окружениях и при работе с секретными данными.

Короткие примеры `k6` для каждого `executionType`:

```json
{
  "executionType": "external executor",
  "vus": 1,
  "duration": "30s",
  "thresholds": { "http_req_duration": ["p(95)<500"] }
}
```

```json
{
  "executionType": "Spike Tests",
  "spikeStages": [
    { "duration": "30s", "target": 10 },
    { "duration": "10s", "target": 50 },
    { "duration": "20s", "target": 0 }
  ],
  "thresholds": { "http_req_duration": ["p(95)<500"] }
}
```

```json
{
  "executionType": "Constant VUs",
  "vus": 5,
  "duration": "1m",
  "thresholds": { "http_req_duration": ["p(95)<500"] }
}
```

```json
{
  "executionType": "Constant Arrival Rate",
  "rate": 20,
  "timeUnit": "1s",
  "duration": "1m",
  "preAllocatedVUs": 10,
  "maxVUs": 50,
  "thresholds": { "http_req_duration": ["p(95)<500"] }
}
```

```json
{
  "executionType": "Ramping Arrival Rate",
  "startRate": 1,
  "timeUnit": "1s",
  "preAllocatedVUs": 5,
  "maxVUs": 30,
  "rampingArrivalStages": [
    { "duration": "30s", "target": 10 },
    { "duration": "30s", "target": 20 },
    { "duration": "20s", "target": 0 }
  ],
  "thresholds": { "http_req_duration": ["p(95)<500"] }
}
```
