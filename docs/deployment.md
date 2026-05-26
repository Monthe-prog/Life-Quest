# Deployment

## Local Docker

```bash
cp .env.example .env
docker compose up --build
```

Services:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Backend health: `http://localhost:8000/health`
- Ollama: `http://localhost:11434`

## VPS Notes

1. Install Docker and Docker Compose.
2. Clone or copy the repository to the server.
3. Create `.env` from `.env.example` and replace all secrets.
4. Pull the desired Ollama model:

```bash
docker compose up -d ollama-service
docker compose exec ollama-service ollama pull llama3
```

5. Start the stack:

```bash
docker compose up -d --build
```

For public hosting, put Nginx, Caddy, or Traefik in front of the app and route `/api` plus `/ws` to the backend.

