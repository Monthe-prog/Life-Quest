# Microservices Migration Plan

This plan moves OPERATOR from a modular monolith to a microservice architecture without breaking the working Docker Compose deployment or the VPS-safe Kubernetes demo.

## Current State

The project is already organized as a modular monolith:

- `apps/frontend`: Next.js UI and client API adapter.
- `apps/backend`: FastAPI API with modules for auth, onboarding, oracle, goals, calendar, character, guilds, weekly reviews, and quests.
- `postgres`: primary relational store.
- `redis`: cache and real-time support.
- `prometheus` and `grafana`: monitoring.
- `infra/kubernetes/vps-safe`: Kubernetes copy exposed on high NodePorts.

This is a good starting point. The migration should preserve the existing API contract while internal modules are split into services.

## Target Architecture

```text
Browser / Next.js frontend
        |
        v
API gateway / backend-for-frontend
        |
        +--> identity-service
        +--> goals-service
        +--> oracle-service
        +--> calendar-service
        +--> character-service
        +--> guild-service
        +--> realtime-service
        |
        +--> PostgreSQL databases
        +--> Redis
        +--> Prometheus / Grafana
```

## Proposed Service Boundaries

| Service | Owns | Start From |
| --- | --- | --- |
| `identity-service` | registration, login, JWT refresh, callsign ownership | `app/modules/auth` |
| `goals-service` | goal hierarchy, progress, breakdown accept flow | `app/modules/goals` |
| `oracle-service` | OpenAI/Ollama calls, degraded fallback, goal breakdown text | `app/modules/oracle` |
| `calendar-service` | planner blocks, schedule suggestions | `app/modules/calendar` |
| `character-service` | XP, stats, achievements, rewards, quests | `app/modules/character`, `app/modules/quests` |
| `guild-service` | guilds, invites, leaderboard, moderation, chat persistence | `app/modules/guilds` |
| `realtime-service` | WebSocket fan-out and live guild feed | `app/ws` |
| `api-gateway` | stable public `/api` and `/ws` contract for the frontend | current `app/main.py` and `app/api/router.py` |

## Migration Rules

1. Keep the existing frontend contract stable until each service has tests and monitoring.
2. Keep Docker Compose as the stable production/demo deployment while Kubernetes is being repaired.
3. Split one service at a time; do not split the database at the same time as the code.
4. Start with service-owned schemas inside the same PostgreSQL instance, then move to database-per-service later.
5. Use async events for cross-service side effects instead of direct shared table writes.
6. Keep shared code small: request schemas, auth token verification, logging, and metrics helpers only.

## Phased Plan

### Phase 0: Stabilize Kubernetes

Goal: Kubernetes must show all app pods healthy before any architecture split.

Required checks:

```bash
sudo kubectl get nodes
sudo kubectl get pods -n operator -o wide
sudo kubectl get svc -n operator
curl -i http://127.0.0.1:31000/health
curl -I http://127.0.0.1:31080
```

If backend is in `CrashLoopBackOff`:

```bash
sudo kubectl logs -n operator deployment/backend --previous --tail=120
sudo kubectl describe pod -n operator -l app=backend
```

### Phase 1: Create The Gateway Boundary

Keep the current backend running as the public gateway. Internally, move business modules behind service interfaces:

```text
frontend -> api-gateway -> local module adapters
```

This keeps behavior unchanged while the code gains clean seams for extraction.

Started:

- Oracle routes now depend on an `OracleClient` boundary in `app/modules/oracle/client.py`.
- The gateway uses the existing local `OracleService` when `ORACLE_SERVICE_URL` is unset, so runtime behavior and API paths stay unchanged by default.
- A standalone Oracle app exists at `app/modules/oracle/service_app.py` and can be run as the `oracle-service` Docker Compose profile.

### Phase 2: Extract Oracle First

Oracle is the best first service because it has a narrow external dependency and already degrades safely when the AI provider fails.

Target flow:

```text
goals-service or api-gateway -> oracle-service -> OpenAI/Ollama
```

Keep fallback generation inside `oracle-service` so the rest of the app does not fail when AI is unavailable.

Run the first optional microservice locally or on the VPS:

```bash
ORACLE_SERVICE_URL=http://oracle-service:8010 docker compose --profile microservices up -d --build oracle-service backend
curl http://127.0.0.1:8010/health
curl http://127.0.0.1:8000/health
```

If `oracle-service` is unavailable, the gateway degrades to the same deterministic fallback instead of failing requests.

### Phase 3: Extract Guild And Realtime

Move guild chat, feed, moderation, and WebSocket fan-out after Oracle. This gives a visible microservice demo without touching the most sensitive auth and goal data first.

Target flow:

```text
api-gateway -> guild-service
api-gateway -> realtime-service
guild-service -> event stream -> realtime-service
```

### Phase 4: Extract Goals And Character With Events

Goals and character are tightly coupled today because goal completion awards XP. Split them only after an event pattern exists:

```text
goals-service emits GoalCompleted
character-service consumes GoalCompleted and awards XP
guild-service consumes GoalCompleted for feeds and leaderboard signals
```

Use a PostgreSQL outbox table first. Redis Streams or a message broker can come later.

### Phase 5: Split Databases

Only split databases after service behavior is stable:

```text
identity_db
goals_db
calendar_db
character_db
guild_db
oracle_db
```

Until then, use one PostgreSQL instance with service-owned tables and migrations.

## Kubernetes Target

The eventual Kubernetes layout should look like:

```text
namespace/operator
  deployment/frontend
  deployment/api-gateway
  deployment/identity-service
  deployment/goals-service
  deployment/oracle-service
  deployment/calendar-service
  deployment/character-service
  deployment/guild-service
  deployment/realtime-service
  statefulset/postgres
  deployment/redis
  service/* internal ClusterIP
  service/frontend NodePort or Ingress
```

For the VPS demo, keep using high NodePorts until the cluster is stable:

- frontend: `31080`
- gateway/backend health: `31000`

## CI/CD Changes

Build and test each service independently:

```text
Frontend Typecheck
Backend Unit Tests
Gateway Tests
Oracle Service Tests
Goals Service Tests
Guild Service Tests
Docker Build Per Service
Deploy To VPS
Kubernetes Smoke Tests
```

The first microservice split should not remove the existing backend image. Keep both until the new service passes smoke tests in Kubernetes.

## Monitoring Changes

Each service should expose:

- `/health`
- `/metrics`
- service name label in Prometheus
- request count, latency, error count
- dependency health where useful

Prometheus scrape targets should become:

```text
api-gateway:8000/metrics
oracle-service:8010/metrics
goals-service:8020/metrics
guild-service:8030/metrics
frontend:3000 if needed
```

## Decisions Needed

Before code is split, decide:

1. Should Kubernetes become the real production deployment, or stay as a presentation/demo deployment beside Docker Compose?
2. Which service do you want to show first in the presentation: Oracle AI, Guild social, or Goals?
3. Do you need database-per-service now for grading, or is service-owned schema inside one PostgreSQL acceptable?
4. Should the frontend call only the gateway, or is it acceptable for the browser to call multiple public service URLs?

Recommended answers for the current project:

1. Keep Docker Compose as production/demo until Kubernetes backend is healthy.
2. Split Oracle first.
3. Use one PostgreSQL instance at first.
4. Keep the frontend calling only the gateway.
