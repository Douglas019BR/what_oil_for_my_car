#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

.venv/bin/python -m compileall -q app scripts test
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/codespell AGENTS.md README.md requirements.txt docker-compose.yml .env.example sql app scripts test static
mapfile -t secret_files < <(
  find AGENTS.md README.md requirements.txt docker-compose.yml .env.example \
    sql app scripts test static -type f -print 2>/dev/null
)
.venv/bin/detect-secrets-hook --baseline secrets.baseline "${secret_files[@]}"
.venv/bin/python -m unittest discover -s test -v

echo "VERIFY_OK"
