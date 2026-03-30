#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

normalize_via_requirements_paths() {
  python - "$@" <<'PY'
from pathlib import Path
import re
import sys

for filename in sys.argv[1:]:
    path = Path(filename)
    text = path.read_text(encoding="utf-8")
    normalized = text
    patterns = (
        (r"(^\s*#\s*via\s+-r\s+)/.*/([^/\s]+\.in)\s*$", r"\1\2"),
        (r"(^\s*#\s+-r\s+)/.*/([^/\s]+\.in)\s*$", r"\1\2"),
    )
    for pattern, replacement in patterns:
        normalized = re.sub(pattern, replacement, normalized, flags=re.MULTILINE)
    if normalized != text:
        path.write_text(normalized, encoding="utf-8")
PY
}

if [[ "${1:-}" == "--normalize-only" ]]; then
  shift
  if [[ "$#" -eq 0 ]]; then
    set -- requirements.txt requirements-dev.txt
  fi
  normalize_via_requirements_paths "$@"
  exit 0
fi

unset \
  PIP_INDEX_URL \
  PIP_EXTRA_INDEX_URL \
  PIP_CERT \
  PIP_CLIENT_CERT \
  PIP_TRUSTED_HOST \
  PIP_CONFIG_FILE \
  PIP_TOOLS_CACHE_DIR \
  PIP_TOOLS_BUILD_ISOLATION \
  PIP_TOOLS_EMIT_INDEX_URL \
  PIP_TOOLS_EMIT_TRUSTED_HOST \
  PIP_TOOLS_QUIET \
  PIP_TOOLS_VERBOSE \
  PIP_TOOLS_NO_HEADER \
  PIP_TOOLS_NO_ANNOTATIONS \
  PIP_TOOLS_NO_EMIT_INDEX_URL \
  PIP_TOOLS_NO_EMIT_TRUSTED_HOST \
  PIP_TOOLS_NO_BINARY \
  PIP_TOOLS_ONLY_BINARY \
  CUSTOM_COMPILE_COMMAND

export CUSTOM_COMPILE_COMMAND="./scripts/update-dependencies.sh"

normalize_requirement_annotations() {
  local file="$1"
  python - "$file" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text()
text = re.sub(
    r"(#\s+via\s+-r\s+)(?:[A-Za-z]:)?[^\n]*?/((?:requirements|requirements-dev)\.in)",
    r"\1\2",
    text,
)
text = re.sub(
    r"(#\s+-r\s+)(?:[A-Za-z]:)?[^\n]*?/((?:requirements|requirements-dev)\.in)",
    r"\1\2",
    text,
)
path.write_text(text)
PY
}

python -m pip install --upgrade -r requirements-lock-tools.txt

pip-compile \
  --generate-hashes \
  --allow-unsafe \
  --resolver=backtracking \
  --output-file=requirements.txt \
  requirements.in

pip-compile \
  --generate-hashes \
  --allow-unsafe \
  --resolver=backtracking \
  --output-file=requirements-dev.txt \
  requirements-dev.in

normalize_requirement_annotations requirements.txt
normalize_requirement_annotations requirements-dev.txt
