# Phase 9 Validation

## Completed In This Pass

- Installed backend dependencies into a local virtual environment.
- Fixed Python 3.9 import compatibility while keeping Docker's Python 3.12 path valid.
- Fixed FastAPI `204 No Content` route declarations.
- Fixed SQLAlchemy nullable model annotations for local runtime imports.
- Made Ollama optional in Docker Compose because Oracle now uses OpenAI by default.
- Verified backend Python compilation.
- Verified FastAPI app import.
- Verified Alembic migration head loading.

## Commands That Passed

```bash
cd apps/backend
.venv/Scripts/python.exe -m compileall app
.venv/Scripts/python.exe -c "from app.main import app; print(app.title)"
.venv/Scripts/python.exe -m alembic heads
```

## Blocked In This Environment

Frontend dependency installation could not complete because npm registry commands repeatedly hung and timed out. Docker validation could not run because Docker is not installed on this machine.

Run these when network and Docker are available:

```bash
cd apps/frontend
npm install
npm run typecheck
npm run build
```

```bash
cd ../..
docker compose up --build
docker compose exec backend alembic upgrade head
```

## Production Notes

- Set `OPENAI_API_KEY` only in backend/server environments.
- Replace `JWT_SECRET_KEY` with a long random secret.
- Use strong Postgres credentials outside local development.
- Put the app behind TLS on the VPS.
- Keep `ollama-service` disabled unless you explicitly want local LLM hosting:

```bash
docker compose --profile local-llm up -d ollama-service
```

