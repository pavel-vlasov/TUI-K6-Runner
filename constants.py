from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return str(self.value)


class AuthMode(StrEnum):
    NONE = "none"
    OAUTH2_CLIENT_CREDENTIALS = "oauth2_client_credentials"
    BASIC = "basic"
    CLIENT_ID_ENFORCEMENT = "client_id_enforcement"


class ExecutionType(StrEnum):
    EXTERNAL_EXECUTOR = "external executor"
    SPIKE_TESTS = "Spike Tests"
    CONSTANT_VUS = "Constant VUs"
    CONSTANT_ARRIVAL_RATE = "Constant Arrival Rate"
    RAMPING_ARRIVAL_RATE = "Ramping Arrival Rate"


class LoggingLevel(StrEnum):
    ALL = "all"
    FAILED = "failed"
    FAILED_WITHOUT_PAYLOADS = "failed_without_payloads"


HTTP_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")

AUTH_MODES = tuple(mode.value for mode in AuthMode)
AUTH_MODE_OPTIONS = tuple((mode.value, mode.value) for mode in AuthMode)

EXECUTION_TYPES = tuple(execution_type.value for execution_type in ExecutionType)
EXECUTION_TYPE_LABELS = {
    ExecutionType.EXTERNAL_EXECUTOR.value: "External executor",
    ExecutionType.SPIKE_TESTS.value: "Spike Tests",
    ExecutionType.CONSTANT_VUS.value: "Constant VUs",
    ExecutionType.CONSTANT_ARRIVAL_RATE.value: "Constant Arrival Rate",
    ExecutionType.RAMPING_ARRIVAL_RATE.value: "Ramping Arrival Rate",
}
EXECUTION_TYPE_OPTIONS = tuple((EXECUTION_TYPE_LABELS[value], value) for value in EXECUTION_TYPES)

LOGGING_LEVEL_ALL = LoggingLevel.ALL.value
LOGGING_LEVEL_FAILED = LoggingLevel.FAILED.value
LOGGING_LEVEL_FAILED_WITHOUT_PAYLOADS = LoggingLevel.FAILED_WITHOUT_PAYLOADS.value

LOGGING_LEVELS = tuple(level.value for level in LoggingLevel)

LOGGING_LEVEL_LABELS = {
    LOGGING_LEVEL_ALL: "All requests",
    LOGGING_LEVEL_FAILED: "Failed only",
    LOGGING_LEVEL_FAILED_WITHOUT_PAYLOADS: "Failed (without payloads)",
}
LOGGING_LEVEL_OPTIONS = tuple((LOGGING_LEVEL_LABELS[level], level) for level in LOGGING_LEVELS)

LOGGING_LEVEL_ALIASES = {
    "all": LOGGING_LEVEL_ALL,
    "failed": LOGGING_LEVEL_FAILED,
    "failed_without_payloads": LOGGING_LEVEL_FAILED_WITHOUT_PAYLOADS,
    "failures_without_payloads": LOGGING_LEVEL_FAILED_WITHOUT_PAYLOADS,
}

DEFAULT_CONFIG_PATH = "test_config.json"


def normalize_logging_level(raw_value: object, default: str = LOGGING_LEVEL_FAILED) -> str:
    if isinstance(raw_value, str):
        normalized = raw_value.strip().lower().replace("-", "_").replace(" ", "_")
        normalized = "_".join(part for part in normalized.split("_") if part)
        return LOGGING_LEVEL_ALIASES.get(normalized, default)
    return default


DEFAULT_CONFIG = {
    "baseURL": "https://www.baseURL.com/",
    "auth": {
        "mode": AuthMode.CLIENT_ID_ENFORCEMENT.value,
        "token_url": "https://oAuthproviderURL.com/ID/oauth2/v2.0/token",
        "client_id": "876878764",
        "client_secret": "0",
        "scope": "read",
    },
    "requestEndpoints": [
        {
            "name": "Endpoint 1",
            "method": "GET",
            "path": "/healthcheck",
            "headers": {"Content-Type": "application/json", "test": "123"},
            "body": {"sample": "payload2"},
            "query": {},
        }
    ],
    "k6": {
        "executionType": ExecutionType.EXTERNAL_EXECUTOR.value,
        "vus": 1,
        "maxVUs": 10,
        "duration": "10s",
        "rate": 10,
        "timeUnit": "1s",
        "preAllocatedVUs": 10,
        "startRate": 1,
        "spikeStages": [{"duration": "30s", "target": 10}],
        "rampingArrivalStages": [{"duration": "30s", "target": 10}],
        "thresholds": {
            "http_req_duration": [
                {
                    "threshold": "p(99) < 2000",
                    "abortOnFail": False,
                    "delayAbortEval": "2s",
                }
            ]
        },
        "logging": {
            "enabled": False,
            "level": LOGGING_LEVEL_FAILED,
            "outputToUI": True,
            "webDashboard": False,
            "webDashboardUrl": "http://localhost:5665",
            "htmlSummaryReport": False,
        },
    },
}
