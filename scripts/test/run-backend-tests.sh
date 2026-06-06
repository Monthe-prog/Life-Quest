#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."
mkdir -p apps/backend/test-results
docker compose build backend
docker compose run --rm --no-deps \
  -v "$PWD/apps/backend/test-results:/app/apps/backend/test-results" \
  backend python -m pytest
