# API Contract

Phase 1 exposes foundational service boundaries. Feature-complete payloads will be expanded during later implementation phases.

## Hosted API Documentation

Swagger UI is the project API documentation source because the FastAPI backend generates it from the live route definitions.

- Local Swagger UI: `http://localhost:8000/api/docs`
- Hosted Swagger UI: `http://158.220.90.106/api/docs`
- OpenAPI schema: `http://158.220.90.106/api/openapi.json`

## System

`GET /health`

```json
{
  "status": "online",
  "service": "operator-backend"
}
```

## Auth

`POST /api/auth/register`

Creates a user with `email + password`, initializes character/stat records, and returns JWT tokens. The user must set a callsign before entering the dashboard.

`POST /api/auth/login`

```json
{
  "email": "operator@domain.com",
  "password": "password"
}
```

Returns:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

`GET /api/auth/me`

Requires `Authorization: Bearer <access_token>`.

```json
{
  "id": "...",
  "email": "operator@domain.com",
  "callsign": null,
  "requires_callsign": true
}
```

`POST /api/auth/callsign`

Requires `Authorization: Bearer <access_token>`.

```json
{
  "callsign": "NOVA_01"
}
```

`POST /api/auth/refresh`

Rotates a refresh token. Refresh tokens are stored as hashed records in Postgres so logout and revocation work.

`POST /api/auth/logout`

Revokes a refresh token.

## Oracle

All Oracle endpoints require `Authorization: Bearer <access_token>`. Oracle AI uses the backend `OPENAI_API_KEY`; the frontend never receives the key.

`GET /api/oracle/status`

Returns the active Oracle provider, model, and whether an API key is configured.

`POST /api/oracle/interrogate`

```json
{
  "message": "I do not know what to focus on.",
  "context": {}
}
```

Returns free-form Oracle voice text. If OpenAI is unavailable or `OPENAI_API_KEY` is missing, the backend returns a deterministic fallback response with `degraded: true`.

`POST /api/oracle/breakdown-goal`

Breaks a goal into child tasks using OpenAI first, with fallback parsing.

`POST /api/oracle/schedule-review`

Reviews schedule text and returns directive Oracle feedback.

## WebSockets

`WS /ws/guild-feed`

Planned for guild and global activity events.

## Goals

All goal endpoints require `Authorization: Bearer <access_token>`.

`GET /api/goals`

Returns flat and grouped goal lists.

`POST /api/goals`

```json
{
  "title": "Build a calm, profitable business",
  "horizon": "yearly",
  "target_count": 10,
  "priority": 2
}
```

Supported horizons:

```text
five_year
yearly
monthly
weekly
daily_part_1
daily_part_2
```

Daily Part 1 defaults to morning. Daily Part 2 defaults to evening.

`POST /api/goals/{goal_id}/progress`

```json
{
  "delta": 1
}
```

Progress supports arbitrary execution counters such as `0/10`.

When a goal reaches completion for the first time, the endpoint returns a battle reward payload:

```json
{
  "goal": {},
  "battle_event": {
    "goal_id": "...",
    "goal_title": "Read 20 pages",
    "xp_awarded": 75,
    "boss_damage": 40,
    "stat_key": "intellect",
    "leveled_up": false,
    "achievement_unlocked": null
  }
}
```

`POST /api/goals/{goal_id}/children`

Creates a child milestone under the selected goal.

`POST /api/goals/{goal_id}/breakdown`

Returns an Oracle-generated preview. Nothing is saved until the user accepts the tasks.

```json
{
  "parent": {},
  "child_horizon": "monthly",
  "tasks": ["Define checkpoint", "Schedule execution", "Report proof"]
}
```

`POST /api/goals/{goal_id}/breakdown/accept`

Persists accepted Oracle preview tasks as child goals.

```json
{
  "tasks": ["Define checkpoint", "Schedule execution", "Report proof"]
}
```

## Calendar

All calendar endpoints require `Authorization: Bearer <access_token>`.

`GET /api/calendar/week`

Returns all current week blocks ordered by day and hour.

`POST /api/calendar/blocks`

Manual calendar blocks do not need to link to a goal.

```json
{
  "title": "Deep work sprint",
  "day_of_week": 0,
  "start_hour": 9,
  "end_hour": 10,
  "goal_id": null
}
```

`PATCH /api/calendar/blocks/{block_id}`

Updates title, day, time range, or goal link.

`DELETE /api/calendar/blocks/{block_id}`

Deletes a user-owned block.

`POST /api/calendar/suggest`

Appends new `oracle_suggested` 60-minute blocks for incomplete weekly and daily goals. Existing suggested blocks are preserved.

## Character

All character endpoints require `Authorization: Bearer <access_token>`.

`GET /api/character/profile`

Returns the character class, cosmetic layers, level, XP, base stats, class bonuses, effective stat levels, skill unlocks, and achievements.

`PATCH /api/character/customizer`

Class selection affects effective gameplay stats immediately.

```json
{
  "character_class": "Netrunner",
  "head_cosmetic": "visor",
  "body_cosmetic": "cloak",
  "gear_cosmetic": "deck"
}
```

Supported classes:

```text
Cyber-Monk
Netrunner
Dreadnought
```

`GET /api/character/skills`

Returns skill unlock state.

`GET /api/character/achievements`

Returns achievement unlock state.

## Activity Events

Battle reward events are persisted in `activity_events` for future Review Archive and feed features.

## Guilds

All guild REST endpoints require `Authorization: Bearer <access_token>`.

`GET /api/guilds/status`

Returns whether the current operator is aligned with a guild.

`POST /api/guilds/forge`

Creates a guild and owner membership. Operators are limited to one guild at a time.

```json
{
  "name": "Night Circuit",
  "motto": "Execute after dark"
}
```

`POST /api/guilds/join`

Consumes a single-use 6-character alphanumeric invite code.

```json
{
  "code": "A1B2C3"
}
```

`GET /api/guilds/my-guild`

Returns the current operator's guild.

`GET /api/guilds/discover`

Returns recently forged guilds.

`GET /api/guilds/global`

Returns public completion events from all users.

`WS /ws/guild-feed?token=<access_token>`

Authenticates with a JWT access token and streams recent global completion events on connect.
