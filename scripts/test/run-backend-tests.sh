#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../../apps/backend"
python -m pytest --cov-report=term-missing --cov-report=xml:test-results/coverage.xml --cov-report=html:test-results/htmlcov
