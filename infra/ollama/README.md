# Ollama Service

Ollama is optional now that OPERATOR's Oracle uses the OpenAI API by default.

Start the local LLM profile with:

```bash
docker compose --profile local-llm up -d ollama-service
```

The Docker Compose service exposes Ollama inside the shared network as:

```text
http://ollama-service:11434
```

The backend owns all model calls through this internal endpoint. The frontend never calls Ollama directly.

Recommended first model:

```bash
docker compose exec ollama-service ollama pull llama3
```

Use `OLLAMA_MODEL` in `.env` to switch models without changing application code.
