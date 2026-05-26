const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
};

export type OperatorUser = {
  id: string;
  email: string;
  callsign: string | null;
  requires_callsign: boolean;
};

export type GoalHorizon = "five_year" | "yearly" | "monthly" | "weekly" | "daily_part_1" | "daily_part_2";

export type Goal = {
  id: string;
  parent_id: string | null;
  title: string;
  horizon: GoalHorizon;
  part: string | null;
  target_count: number;
  completed_count: number;
  priority: number;
  is_complete: boolean;
};

export type GoalList = {
  goals: Goal[];
  grouped: Record<GoalHorizon, Goal[]>;
};

export type BattleEvent = {
  goal_id: string;
  goal_title: string;
  xp_awarded: number;
  boss_damage: number;
  stat_key: string;
  leveled_up: boolean;
  achievement_unlocked: string | null;
};

export type CalendarBlock = {
  id: string;
  goal_id: string | null;
  title: string;
  day_of_week: number;
  start_hour: number;
  end_hour: number;
  source: "manual" | "oracle_suggested" | string;
};

export type CharacterClass = "Cyber-Monk" | "Netrunner" | "Dreadnought";

export type CharacterStat = {
  stat_key: string;
  label: string;
  level: number;
  xp: number;
  class_bonus: number;
  effective_level: number;
};

export type CharacterSkill = {
  skill_key: string;
  label: string;
  stat_key: string;
  required_level: number;
  unlocked: boolean;
};

export type CharacterAchievement = {
  achievement_key: string;
  label: string;
  unlocked: boolean;
};

export type CharacterProfile = {
  callsign: string;
  character_class: CharacterClass;
  head_cosmetic: string;
  body_cosmetic: string;
  gear_cosmetic: string;
  level: number;
  xp: number;
  stats: CharacterStat[];
  skills: CharacterSkill[];
  achievements: CharacterAchievement[];
};

export type Guild = {
  id: string;
  name: string;
  motto: string | null;
  role: string | null;
  invite_code: string | null;
};

export type GuildStatus = {
  aligned: boolean;
  guild: Guild | null;
};

export type FeedEvent = {
  id: string;
  event_type: string;
  operator: string;
  goal_title: string | null;
  xp_awarded: number | null;
  stat_key: string | null;
  created_at: string;
};

export type OracleReply = {
  response: string;
  provider: string;
  degraded: boolean;
};

export type OracleStatus = {
  provider: string;
  configured: boolean;
  model: string;
};

async function apiRequest<T>(path: string, options: RequestInit = {}) {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {})
    }
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail ?? "Request failed");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export async function getHealth() {
  const response = await fetch(`${apiBaseUrl}/health`, {
    next: { revalidate: 30 }
  });

  if (!response.ok) {
    throw new Error("Backend health check failed");
  }

  return response.json() as Promise<{ status: string; service: string }>;
}

export function register(email: string, password: string) {
  return apiRequest<TokenPair>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
}

export function login(email: string, password: string) {
  return apiRequest<TokenPair>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
}

export function getMe(accessToken: string) {
  return apiRequest<OperatorUser>("/api/auth/me", {
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });
}

export function setCallsign(accessToken: string, callsign: string) {
  return apiRequest<OperatorUser>("/api/auth/callsign", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`
    },
    body: JSON.stringify({ callsign })
  });
}

export function logout(refreshToken: string) {
  return apiRequest<void>("/api/auth/logout", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken })
  });
}

export function listGoals(accessToken: string) {
  return apiRequest<GoalList>("/api/goals", {
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });
}

export function createGoal(
  accessToken: string,
  payload: { title: string; horizon: GoalHorizon; parent_id?: string | null; target_count?: number; priority?: number }
) {
  return apiRequest<Goal>("/api/goals", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`
    },
    body: JSON.stringify(payload)
  });
}

export function changeGoalProgress(accessToken: string, goalId: string, delta: number) {
  return apiRequest<{ goal: Goal; battle_event: BattleEvent | null }>(`/api/goals/${goalId}/progress`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`
    },
    body: JSON.stringify({ delta })
  });
}

export function spawnChildGoal(
  accessToken: string,
  goalId: string,
  payload: { title: string; horizon: GoalHorizon; target_count?: number; priority?: number }
) {
  return apiRequest<Goal>(`/api/goals/${goalId}/children`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`
    },
    body: JSON.stringify(payload)
  });
}

export function oracleBreakdown(accessToken: string, goalId: string) {
  return apiRequest<{ parent: Goal; child_horizon: GoalHorizon; tasks: string[] }>(`/api/goals/${goalId}/breakdown`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });
}

export function acceptOracleBreakdown(accessToken: string, goalId: string, tasks: string[]) {
  return apiRequest<{ parent: Goal; children: Goal[] }>(`/api/goals/${goalId}/breakdown/accept`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`
    },
    body: JSON.stringify({ tasks })
  });
}

export function getCalendarWeek(accessToken: string) {
  return apiRequest<{ blocks: CalendarBlock[] }>("/api/calendar/week", {
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });
}

export function createCalendarBlock(
  accessToken: string,
  payload: { title: string; day_of_week: number; start_hour: number; end_hour: number; goal_id?: string | null }
) {
  return apiRequest<CalendarBlock>("/api/calendar/blocks", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`
    },
    body: JSON.stringify(payload)
  });
}

export function deleteCalendarBlock(accessToken: string, blockId: string) {
  return apiRequest<void>(`/api/calendar/blocks/${blockId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });
}

export function suggestCalendar(accessToken: string) {
  return apiRequest<{ blocks: CalendarBlock[] }>("/api/calendar/suggest", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });
}

export function getCharacterProfile(accessToken: string) {
  return apiRequest<CharacterProfile>("/api/character/profile", {
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });
}

export function updateCharacterCustomizer(
  accessToken: string,
  payload: Partial<{
    character_class: CharacterClass;
    head_cosmetic: string;
    body_cosmetic: string;
    gear_cosmetic: string;
  }>
) {
  return apiRequest<CharacterProfile>("/api/character/customizer", {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${accessToken}`
    },
    body: JSON.stringify(payload)
  });
}

export function getGuildStatus(accessToken: string) {
  return apiRequest<GuildStatus>("/api/guilds/status", {
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });
}

export function forgeGuild(accessToken: string, payload: { name: string; motto?: string }) {
  return apiRequest<GuildStatus>("/api/guilds/forge", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`
    },
    body: JSON.stringify(payload)
  });
}

export function joinGuild(accessToken: string, code: string) {
  return apiRequest<GuildStatus>("/api/guilds/join", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`
    },
    body: JSON.stringify({ code })
  });
}

export function discoverGuilds(accessToken: string) {
  return apiRequest<Guild[]>("/api/guilds/discover", {
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });
}

export function getGlobalFeed(accessToken: string) {
  return apiRequest<FeedEvent[]>("/api/guilds/global", {
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });
}

export function getOracleStatus(accessToken: string) {
  return apiRequest<OracleStatus>("/api/oracle/status", {
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });
}

export function interrogateOracle(accessToken: string, message: string, context: Record<string, string> = {}) {
  return apiRequest<OracleReply>("/api/oracle/interrogate", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`
    },
    body: JSON.stringify({ message, context })
  });
}
