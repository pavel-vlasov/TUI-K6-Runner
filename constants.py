# constants.py
DEFAULT_CONFIG = {
    "baseURL": "https://www.baseURL.com/",
    "auth": {
        "useOAuth2": False,
        "basicauth": False,
        "ClientId_Enforcement": True,
        "token_url": "https://oAuthproviderURL.com/ID/oauth2/v2.0/token",
        "client_id": "876878764", "client_secret": "0", "scope": "read"
    },
    "request": {
        "name": "Endpoint 1",
        "method": "GET", "path": "xxxx/healthcheck",
        "headers": {"Content-Type": "application/json", "test": "123"},
        "body": {"sample": "payload2"}, "query": {}
    },
    "requestEndpoints": [
        {
            "name": "Endpoint 1",
            "method": "GET", "path": "xxxx/healthcheck",
            "headers": {"Content-Type": "application/json", "test": "123"},
            "body": {"sample": "payload2"}, "query": {}
        }
    ],
    "k6": {
        "executionType": "external executor",
        "requestMode": "batch",
        "vus": 1, "maxVUs": 10, "duration": "10s",
        "rate": 10,
        "timeUnit": "1s",
        "preAllocatedVUs": 10,
        "startRate": 1,
        "spikeStages": [
            {"duration": "30s", "target": 10}
        ],
        "rampingArrivalStages": [
            {"duration": "30s", "target": 10}
        ],
        "thresholds": {
            "http_req_duration": [{"threshold": "p(99) < 2000", "abortOnFail": False, "delayAbortEval": "2s"}]
        },
        "logging": {
            "enabled": False,
            "level": "failed",
            "outputToUI": True,
            "metricsViewer": False,
        }
    }
}

AUTH_MAP = {
    "bool___auth__useOAuth2": "useOAuth2",
    "bool___auth__basicauth": "basicauth",
    "bool___auth__ClientId_Enforcement": "ClientId_Enforcement"
}
