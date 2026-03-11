import re


RUNNING_LINE_PATTERN = re.compile(r"running \(.*\),\s*\d+/\d+\s*VUs")
SCENARIO_PROGRESS_PATTERN = re.compile(
    r"^\s*[A-Za-z0-9_-]+\s+\[\s*\d+%\s*\]\s+\d+/\d+\s+VUs\s+\S+/\S+"
)
RUN_COMPLETE_PATTERN = re.compile(r"^\s*[A-Za-z0-9_-]+\s+\[\s*100%\s*\]\s+")


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


def is_fail_line(text: str) -> bool:
    return 'msg="❌' in text or "Non-200" in text


def is_run_complete_line(text: str) -> bool:
    return bool(RUN_COMPLETE_PATTERN.search(text))
