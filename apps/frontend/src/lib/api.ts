const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  (typeof window !== "undefined" ? `${window.location.protocol}//${window.location.hostname}:8000` : "http://localhost:8000");

function formatApiError(error: unknown): string {
  if (!error || typeof error !== "object" || !("detail" in error)) {
    return "Request failed";
  }

  const detail = (error as { detail: unknown }).detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          const location = "loc" in item && Array.isArray(item.loc) ? item.loc.join(".") : "field";
          return `${location}: ${String(item.msg)}`;
        }

        return String(item);
      })
      .join("; ");
  }

  return "Request failed";
}

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
  is_recurring: boolean;
  recurrence_pattern: string | null;
  completed: boolean;
  alignment_status: string;
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

export type OnboardingState = {
  life_mission: string;
  vision_3_5_year: string;
  one_year_goal: string;
  monthly_goals: string[];
  character_class: CharacterClass | null;
  completed: boolean;
};

export type WeeklyReview = {
  id: string;
  week_ending: string;
  wins: string;
  friction: string;
  alignment: string;
  directive: string;
  completion_rate: number;
  xp_gained: number;
  streak: number;
  locked: boolean;
  updated_at: string;
};

export type WeeklyReviewExport = {
  id: string;
  filename: string;
  settings: Record<string, unknown>;
  created_at: string;
};

export type QuestStep = {
  id: string;
  title: string;
  completed: boolean;
};

export type Quest = {
  id: string;
  title: string;
  description: string;
  skill_key: string | null;
  status: string;
  reward_xp: number;
  claimed: boolean;
  expires_at: string | null;
  steps: QuestStep[];
};

export type BossBattle = {
  id: string;
  title: string;
  goal_id: string | null;
  required_count: number;
  progress_count: number;
  reward_xp: number;
  status: string;
  percent_complete: number;
  claimed: boolean;
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
    throw new Error(formatApiError(error));
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
  payload: {
    title: string;
    day_of_week: number;
    start_hour: number;
    end_hour: number;
    goal_id?: string | null;
    is_recurring?: boolean;
    recurrence_pattern?: string | null;
    alignment_status?: string;
  }
) {
  return apiRequest<CalendarBlock>("/api/calendar/blocks", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`
    },
    body: JSON.stringify(payload)
  });
}

export function updateCalendarBlock(
  accessToken: string,
  blockId: string,
  payload: Partial<{
    title: string;
    day_of_week: number;
    start_hour: number;
    end_hour: number;
    goal_id: string | null;
    is_recurring: boolean;
    recurrence_pattern: string | null;
    alignment_status: string;
  }>
) {
  return apiRequest<CalendarBlock>(`/api/calendar/blocks/${blockId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${accessToken}`
    },
    body: JSON.stringify(payload)
  });
}

export function completeCalendarBlock(accessToken: string, blockId: string) {
  return apiRequest<CalendarBlock>(`/api/calendar/blocks/${blockId}/complete`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
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

export function getOnboardingState(accessToken: string) {
  return apiRequest<OnboardingState>("/api/onboarding/state", {
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });
}

export function saveOnboardingState(accessToken: string, payload: Omit<OnboardingState, "completed">) {
  return apiRequest<OnboardingState>("/api/onboarding/state", {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${accessToken}`
    },
    body: JSON.stringify(payload)
  });
}

export function getLatestWeeklyReview(accessToken: string) {
  return apiRequest<WeeklyReview | null>("/api/weekly-reviews/latest", {
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });
}

export function listWeeklyReviews(accessToken: string) {
  return apiRequest<WeeklyReview[]>("/api/weekly-reviews", {
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });
}

export function saveWeeklyReview(
  accessToken: string,
  payload: {
    week_ending: string;
    wins: string;
    friction: string;
    alignment: string;
    directive: string;
    completion_rate: number;
    xp_gained: number;
    streak: number;
    lock: boolean;
  }
) {
  return apiRequest<WeeklyReview>("/api/weekly-reviews", {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${accessToken}`
    },
    body: JSON.stringify(payload)
  });
}

export function deleteWeeklyReview(accessToken: string, reviewId: string) {
  return apiRequest<void>(`/api/weekly-reviews/${reviewId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });
}

export function exportWeeklyReviews(accessToken: string, reviewIds: string[], sections: string[]) {
  return apiRequest<WeeklyReviewExport>("/api/weekly-reviews/exports", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`
    },
    body: JSON.stringify({ review_ids: reviewIds, sections })
  });
}

export function listWeeklyReviewExports(accessToken: string) {
  return apiRequest<WeeklyReviewExport[]>("/api/weekly-reviews/exports", {
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });
}

export function listQuests(accessToken: string) {
  return apiRequest<Quest[]>("/api/quests", {
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });
}

export function createQuest(accessToken: string, payload: { title: string; description?: string; steps: string[]; reward_xp?: number }) {
  return apiRequest<Quest>("/api/quests", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`
    },
    body: JSON.stringify(payload)
  });
}

export function completeQuestStep(accessToken: string, questId: string, stepId: string) {
  return apiRequest<Quest>(`/api/quests/${questId}/steps/${stepId}/complete`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });
}

export function claimQuest(accessToken: string, questId: string) {
  return apiRequest<Quest>(`/api/quests/${questId}/claim`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });
}
