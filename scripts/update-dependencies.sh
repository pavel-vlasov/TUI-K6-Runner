#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip pip-tools

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
