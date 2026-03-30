#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

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
