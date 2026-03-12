import re


RUNNING_LINE_PATTERN = re.compile(r"running \(.*\),\s*\d+/\d+\s*VUs")
SCENARIO_PROGRESS_PATTERN = re.compile(
    r"^\s*[A-Za-z0-9_-]+\s+\[\s*\d+%\s*\]\s+\d+/\d+\s+VUs\s+\S+/\S+"
)
RUN_COMPLETE_PATTERN = re.compile(r"^\s*[A-Za-z0-9_-]+\s+\[\s*100%\s*\]\s+")
HTTP_STATUS_PATTERN = re.compile(r"(?:\bStatus:\s*|\bstatus:\s*)(\d{3})")


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


def get_fail_category(text: str) -> str | None:
    if "Request Failed" in text and "EOF" in text:
        return "EOF"

    if "Request Failed" in text:
        return "Request Failed"

    if "Non-200" in text:
        status_match = HTTP_STATUS_PATTERN.search(text)
        if status_match:
            return f"HTTP {status_match.group(1)}"
        return "Non-200"

    return None


def is_fail_line(text: str) -> bool:
    return get_fail_category(text) is not None


def parse_http_status_code(text: str) -> int | None:
    patterns = (
        r"Non-200 status:\s*(\d{3})",
        r"status\s*[:=]\s*(\d{3})",
        r"\bHTTP\s*(\d{3})\b",
    )

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))

    return None


def is_run_complete_line(text: str) -> bool:
    return bool(RUN_COMPLETE_PATTERN.search(text))
