#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

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
