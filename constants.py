# constants.py
HTTP_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")

AUTH_MODES = (
    "none",
    "oauth2_client_credentials",
    "basic",
    "client_id_enforcement",
)

DEFAULT_CONFIG = {
    "baseURL": "https://www.baseURL.com/",
    "auth": {
        "mode": "client_id_enforcement",
        "token_url": "https://oAuthproviderURL.com/ID/oauth2/v2.0/token",
        "client_id": "876878764",
        "client_secret": "0",
        "scope": "read",
    },
    "request": {
        "name": "Endpoint 1",
        "method": "GET",
        "path": "/healthcheck",
        "headers": {"Content-Type": "application/json", "test": "123"},
        "body": {"sample": "payload2"},
        "query": {},
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
        "executionType": "external executor",
        "requestMode": "batch",
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
            "level": "failed",
            "outputToUI": True,
            "webDashboard": False,
            "webDashboardUrl": "http://localhost:5665",
            "htmlSummaryReport": False,
        },
    },
}
