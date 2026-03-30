import re


RUNNING_LINE_PATTERN = re.compile(r"running \(.*\),\s*\d+/\d+\s*VUs")
SCENARIO_PROGRESS_PATTERN = re.compile(
    r"^\s*[A-Za-z0-9_-]+\s+\[\s*\d+%\s*\]\s+\d+/\d+\s+VUs\s+\S+/\S+"
)
RUN_COMPLETE_PATTERN = re.compile(r"^\s*[A-Za-z0-9_-]+\s+\[\s*100%\s*\]\s+")
HTTP_STATUS_PATTERN = re.compile(r"(?:\bStatus:\s*|\bstatus:\s*)(\d+)")


def clean_cursor_sequences(line: str) -> str:
    line = re.sub(r"\x1b\[[0-9;]*[ABCDGKsu]", "", line)
    line = re.sub(r"\\x1b\[[0-9;]*[ABCDGKsu]", "", line)
    line = line.replace('\\"', '"')
    line = line.replace("\\n", "\n")
    if "\x1b" in line:
        ansi_escape = re.compile(r"(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]")
        line = ansi_escape.sub("", line)
    return line


def is_running_line(text: str) -> bool:
    return bool(RUNNING_LINE_PATTERN.search(text)) or ("running (" in text and "VUs" in text)


def is_default_line(text: str) -> bool:
    return "default" in text and "%" in text


def is_scenario_progress_line(text: str) -> bool:
    return bool(SCENARIO_PROGRESS_PATTERN.search(text))


def is_success_line(text: str) -> bool:
    return 'msg="Processed request: 200 ✅"' in text


def _bucket_http_status(status: int) -> str | None:
    if status == 0:
        return "status 0"
    if 400 <= status <= 499:
        return "4xx"
    if status == 500:
        return "500"
    if 501 <= status <= 599:
        return "5xx (not 500)"
    return None


def get_fail_category(text: str) -> str | None:
    if "Request Failed" in text:
        lowered = text.lower()
        if "eof" in lowered:
            return "EOF"
        if any(pattern in lowered for pattern in ("context deadline exceeded", "timed out", "timeout")):
            return "timeout"
        if any(pattern in lowered for pattern in ("no such host", "name resolution", "dns")):
            return "dns"
        if "connection refused" in lowered:
            return "connection refused"
        if "reset by peer" in lowered or "connection reset" in lowered:
            return "reset by peer"
        if "tls" in lowered or "handshake" in lowered or "x509" in lowered:
            return "tls/handshake"
        return "other"

    if "Non-200" in text:
        status_match = HTTP_STATUS_PATTERN.search(text)
        if not status_match:
            return "transport/no_status"

        status = int(status_match.group(1))
        if status == 0:
            return "transport/no_status"

        category = _bucket_http_status(status)
        if category:
            return category
        return "transport/no_status"

    return None


def is_fail_line(text: str) -> bool:
    return get_fail_category(text) is not None


def is_run_complete_line(text: str) -> bool:
    return bool(RUN_COMPLETE_PATTERN.search(text))
