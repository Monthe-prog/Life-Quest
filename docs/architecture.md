# OPERATOR Architecture

## Phase 1 Decisions

OPERATOR is structured as a monorepo with clear frontend, backend, infrastructure, and documentation boundaries.

The product is single-user-first. Guild infrastructure exists as an API and data boundary, but collaborative multiplayer logic is deferred until the core solo loop is stable.

Onboarding is integrated into the Oracle Terminal on the Home dashboard. The Oracle will progressively interrogate vague desires and convert them into concrete, time-bound goals.

## Stack

- Frontend: React through Next.js 14 App Router, TypeScript, Tailwind CSS, Lucide React, Radix primitives
- Backend: FastAPI, Pydantic v2, SQLAlchemy async, Alembic-ready migrations
- Database: PostgreSQL
- Cache and real-time state: Redis
- AI orchestration: Backend-owned LangChain/Ollama integration point
- Deployment: Docker Compose with service-specific Dockerfiles

## Service Boundaries

```text
apps/frontend    React UI, route shell, visual system, client API adapters
apps/backend     REST API, WebSockets, auth, persistence, AI orchestration
infra/docker     Production-oriented Dockerfiles
infra/ollama     Local LLM configuration notes
infra/nginx      VPS reverse proxy example
docs             Architecture, deployment, and API notes
```

## Backend Modules

- `auth`: email/password and JWT access/refresh token flow
- `oracle`: AI prompt orchestration and onboarding interrogation
- `goals`: hierarchical goals and execution tracking
- `calendar`: weekly time-block grid and schedule suggestions
- `character`: stats, classes, skill trees, achievements
- `guilds`: forge/join/global feed boundaries

## Planned Core Entities

```text
User
UserProfile
RefreshToken
OnboardingAnswer
Goal
GoalProgress
CalendarBlock
CharacterProfile
CharacterStat
Achievement
SkillUnlock
Guild
GuildMembership
GuildInviteCode
ActivityEvent
OracleConversation
```

## Auth Flow

Registration accepts only email and password. The backend creates the account plus default character, stat, skill, and achievement records. The first dashboard entry is blocked until the user sets a unique callsign.

Access tokens are short-lived JWTs. Refresh tokens are JWTs too, but their hashes are persisted in Postgres so they can be rotated and revoked.

## Goals Matrix

Goals use arbitrary execution counters, so a target may be `0/1`, `0/10`, or any bounded count. The hierarchy is:

```text
five_year -> yearly -> monthly -> weekly -> daily_part_1 -> daily_part_2
```

Daily Part 1 represents morning execution. Daily Part 2 represents evening execution.

Oracle Breakdown previews generated child goals first. The user can edit, accept, or reject the preview; only accepted tasks are persisted.

## Calendar Scheduling

The weekly planner spans Monday through Sunday and 07:00 through 22:00. Manual blocks are allowed without a goal link. Suggested schedule generation reads incomplete weekly and daily goals, orders them by priority, and appends 60-minute `oracle_suggested` blocks into available slots without deleting older suggestions.

## Character Progression

Base stats start at level 0 for new users. Character class adds immediate effective stat bonuses:

```text
Cyber-Monk: wisdom +2, charisma +1
Netrunner: intellect +2, wealth +1
Dreadnought: strength +2, wisdom +1
```

The frontend renders a cyberpunk pixel-style avatar from simple cosmetic layers now. A more detailed pixel-art avatar system remains a later enhancement. Retro UI sound effects use the browser Web Audio API, so no bundled audio assets are required.

## Battle Rewards

When a goal completion reaches its target count for the first time, OPERATOR grants XP once and emits a battle event for the frontend simulator. Stat growth is inferred from goal-title keywords for now. Completed goals remain visible with completed styling; Review Archive is planned as a later destination for historic completions.

## Guilds

Guilds are layered on top of the single-user core. An operator can belong to one guild at a time. Forge creates an owner membership and a single-use 6-character invite code. Join consumes that code and creates a member record. Global feed surfaces public battle reward events from all users through both REST and the `/ws/guild-feed` WebSocket.

## Oracle AI

Oracle AI calls OpenAI from the FastAPI backend through the Responses API. The API key is read from `OPENAI_API_KEY` and is never exposed to the browser. Oracle responses are allowed to be free-form so the RPG voice can stay expressive. If the key is missing or a request fails, the Oracle service returns a degraded deterministic fallback.

The default model is `gpt-5.5` in `.env.example`, chosen as the current recommended flagship default based on OpenAI model guidance; it can be changed with `OPENAI_MODEL`.
