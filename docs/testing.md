# Testing And Coverage

This project includes automated backend unit and integration tests with an 80% coverage gate for the tested backend modules.

## Test Levels

Unit tests:

- Password hashing, JWT creation/decoding, and token hashing.
- Bootstrap defaults for new users.
- Oracle fallback, response parsing, and task parsing.
- Prometheus metrics helpers.

Integration tests:

- FastAPI `/health` endpoint.
- FastAPI `/metrics` endpoint after a real request.

Optional E2E tests can be added later with Playwright once browser flows are stable.

## Run Tests

From the repo root:

```bash
npm run test:backend
```

This runs the backend tests inside Docker so FastAPI, SQLAlchemy, httpx, and the other application dependencies are installed from `apps/backend/requirements.txt`.

Local Python option:

```bash
cd apps/backend
python -m pip install -r requirements.txt
python -m pytest
```

Coverage report:

```bash
npm run coverage:backend
```

Automation script:

```bash
bash scripts/test/run-backend-tests.sh
```

## Reports

Generated reports:

```text
apps/backend/coverage.xml
apps/backend/test-results/coverage.xml
apps/backend/test-results/htmlcov/index.html
```

The test command enforces:

```text
--cov-fail-under=80
```

## Screenshot Checklist

Capture:

1. `python -m pytest` showing all tests passing.
2. Terminal coverage summary showing coverage above 80%.
3. `apps/backend/test-results/htmlcov/index.html` opened in a browser.
4. Jenkins console output after adding/running the test command in the CI pipeline.
