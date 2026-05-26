"use client";

import { type ReactNode, useEffect, useMemo, useState } from "react";
import {
  Award,
  Bot,
  Brain,
  BookOpen,
  CalendarDays,
  ChevronDown,
  ChevronUp,
  Clock,
  Dumbbell,
  Globe2,
  Heart,
  Home,
  Lock,
  LogOut,
  Minus,
  Plus,
  Shield,
  ShieldPlus,
  Sparkles,
  Target,
  Trash2,
  Trophy,
  UserRound,
  Users,
  Wallet,
  X,
  Zap
} from "lucide-react";
import { PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer } from "recharts";
import {
  changeGoalProgress,
  acceptOracleBreakdown,
  createCalendarBlock,
  createGoal,
  deleteCalendarBlock,
  discoverGuilds,
  forgeGuild,
  getCharacterProfile,
  getCalendarWeek,
  getGlobalFeed,
  getGuildStatus,
  getMe,
  getOracleStatus,
  joinGuild,
  interrogateOracle,
  listGoals,
  login,
  logout,
  oracleBreakdown,
  register,
  setCallsign,
  suggestCalendar,
  spawnChildGoal,
  type BattleEvent,
  type CalendarBlock,
  type CharacterClass,
  type CharacterProfile,
  type CharacterStat,
  type FeedEvent,
  type Goal,
  type GoalHorizon,
  type GoalList,
  type Guild,
  type GuildStatus,
  type OracleReply,
  type OracleStatus,
  updateCharacterCustomizer
} from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

type View = "HOME" | "GOALS" | "CALENDAR" | "CHARACTER" | "GUILD";

const navItems: { label: View; icon: typeof Home }[] = [
  { label: "HOME", icon: Home },
  { label: "GOALS", icon: Target },
  { label: "CALENDAR", icon: CalendarDays },
  { label: "CHARACTER", icon: UserRound },
  { label: "GUILD", icon: Shield }
];

const goalSections: { horizon: GoalHorizon; title: string; prompt: string; child?: GoalHorizon }[] = [
  { horizon: "five_year", title: "5-Year Vision", prompt: "Long-range destiny architecture.", child: "yearly" },
  { horizon: "yearly", title: "Yearly Goals", prompt: "This year's breakthrough targets.", child: "monthly" },
  { horizon: "monthly", title: "Monthly Goals", prompt: "The 1-3 conquests for this month.", child: "weekly" },
  { horizon: "weekly", title: "Weekly Goals", prompt: "Priority missions for this week.", child: "daily_part_1" },
  { horizon: "daily_part_1", title: "Daily - Part 1", prompt: "Morning execution list.", child: "daily_part_2" },
  { horizon: "daily_part_2", title: "Daily - Part 2", prompt: "Evening execution list." }
];

const weekDays = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"];
const scheduleHours = Array.from({ length: 16 }, (_, index) => index + 7);
const characterClasses: CharacterClass[] = ["Cyber-Monk", "Netrunner", "Dreadnought"];
const cosmeticOptions = {
  head_cosmetic: ["visor", "halo", "hood"],
  body_cosmetic: ["cloak", "armor", "jacket"],
  gear_cosmetic: ["blade", "deck", "gauntlet"]
};
const statIcons: Record<string, typeof Dumbbell> = {
  strength: Dumbbell,
  wealth: Wallet,
  intellect: BookOpen,
  wisdom: Brain,
  charisma: Users
};

function useRetroSound() {
  return (kind: "select" | "confirm" | "error" = "select") => {
    if (typeof window === "undefined") {
      return;
    }

    const AudioCtor =
      window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioCtor) {
      return;
    }

    const context = new AudioCtor();
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    const frequencies = {
      select: [520, 780],
      confirm: [660, 990],
      error: [180, 120]
    };
    const [first, second] = frequencies[kind];

    oscillator.type = "square";
    oscillator.frequency.setValueAtTime(first, context.currentTime);
    oscillator.frequency.setValueAtTime(second, context.currentTime + 0.06);
    gain.gain.setValueAtTime(0.035, context.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, context.currentTime + 0.16);
    oscillator.connect(gain);
    gain.connect(context.destination);
    oscillator.start();
    oscillator.stop(context.currentTime + 0.17);
  };
}

export function OperatorApp() {
  const { accessToken, refreshToken, user, setTokens, setUser, hydrate, clear } = useAuthStore();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("operator@domain.com");
  const [password, setPassword] = useState("");
  const [callsign, setCallsignValue] = useState("");
  const [activeView, setActiveView] = useState<View>("HOME");
  const [battleEvent, setBattleEvent] = useState<BattleEvent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const playSound = useRetroSound();

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (!accessToken || user) {
      return;
    }

    getMe(accessToken).then(setUser).catch(clear);
  }, [accessToken, clear, setUser, user]);

  async function submitAuth() {
    setLoading(true);
    setError(null);
    try {
      playSound("confirm");
      const tokens = mode === "login" ? await login(email, password) : await register(email, password);
      setTokens(tokens);
      const me = await getMe(tokens.access_token);
      setUser(me);
    } catch (err) {
      playSound("error");
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  async function submitCallsign() {
    if (!accessToken) {
      return;
    }

    setLoading(true);
    setError(null);
    try {
      playSound("confirm");
      const me = await setCallsign(accessToken, callsign);
      setUser(me);
    } catch (err) {
      playSound("error");
      setError(err instanceof Error ? err.message : "Callsign rejected");
    } finally {
      setLoading(false);
    }
  }

  async function submitLogout() {
    if (refreshToken) {
      await logout(refreshToken).catch(() => undefined);
    }
    clear();
  }

  if (!accessToken || !user) {
    return (
      <AuthFrame
        email={email}
        error={error}
        loading={loading}
        mode={mode}
        password={password}
        setEmail={setEmail}
        setMode={setMode}
        setPassword={setPassword}
        submitAuth={submitAuth}
      />
    );
  }

  if (user.requires_callsign) {
    return (
      <CallsignGate
        callsign={callsign}
        error={error}
        loading={loading}
        setCallsignValue={setCallsignValue}
        submitCallsign={submitCallsign}
        submitLogout={submitLogout}
      />
    );
  }

  return (
    <Shell
      accessToken={accessToken}
      activeView={activeView}
      battleEvent={battleEvent}
      callsign={user.callsign ?? "OPERATOR"}
      playSound={playSound}
      setActiveView={setActiveView}
      setBattleEvent={setBattleEvent}
      submitLogout={submitLogout}
    />
  );
}

function Shell({
  accessToken,
  activeView,
  battleEvent,
  callsign,
  playSound,
  setActiveView,
  setBattleEvent,
  submitLogout
}: {
  accessToken: string;
  activeView: View;
  battleEvent: BattleEvent | null;
  callsign: string;
  playSound: (kind?: "select" | "confirm" | "error") => void;
  setActiveView: (view: View) => void;
  setBattleEvent: (event: BattleEvent | null) => void;
  submitLogout: () => void;
}) {
  return (
    <main className="min-h-screen pb-24 text-white">
      <section className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-5 py-8">
        <header className="flex items-start justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-white/55">System Online</p>
            <h1 className="operator-glow mt-2 text-4xl uppercase leading-none text-white">{callsign}</h1>
          </div>
          <button className="border border-white/25 p-3 text-white/55" onClick={submitLogout} title="Logout">
            <LogOut size={22} />
          </button>
        </header>

        {activeView === "HOME" && <HomeView accessToken={accessToken} battleEvent={battleEvent} callsign={callsign} playSound={playSound} />}
        {activeView === "GOALS" && <GoalsMatrix accessToken={accessToken} onBattleEvent={setBattleEvent} playSound={playSound} />}
        {activeView === "CALENDAR" && <CalendarView accessToken={accessToken} />}
        {activeView === "CHARACTER" && <CharacterView accessToken={accessToken} battleEvent={battleEvent} playSound={playSound} />}
        {activeView === "GUILD" && <GuildView accessToken={accessToken} playSound={playSound} />}
      </section>

      <nav className="fixed inset-x-0 bottom-0 border-t border-operator-purple/65 bg-[#08080b]/95">
        <div className="mx-auto grid max-w-3xl grid-cols-5">
          {navItems.map(({ label, icon: Icon }) => (
            <button
              className={`flex flex-col items-center gap-1 px-2 py-3 text-[11px] uppercase ${
                activeView === label ? "text-operator-purple" : "text-white/55"
              }`}
              key={label}
              onClick={() => {
                playSound("select");
                setActiveView(label);
              }}
            >
              <Icon size={20} />
              {label}
            </button>
          ))}
        </div>
      </nav>
    </main>
  );
}

function HomeView({
  accessToken,
  battleEvent,
  callsign,
  playSound
}: {
  accessToken: string;
  battleEvent: BattleEvent | null;
  callsign: string;
  playSound: (kind?: "select" | "confirm" | "error") => void;
}) {
  const [oracleStatus, setOracleStatus] = useState<OracleStatus | null>(null);
  const [oracleInput, setOracleInput] = useState("");
  const [messages, setMessages] = useState<Array<{ role: "oracle" | "operator"; text: string; provider?: string }>>([
    {
      role: "oracle",
      text: `${callsign}. Your mission channel is open. Define one objective for the next twelve hours. Ambiguity is enemy terrain. Convert it into a target.`
    }
  ]);
  const [oracleBusy, setOracleBusy] = useState(false);

  useEffect(() => {
    getOracleStatus(accessToken).then(setOracleStatus).catch(() => setOracleStatus(null));
  }, [accessToken]);

  async function transmitIntent() {
    const message = oracleInput.trim();
    if (!message) {
      return;
    }
    setMessages((current) => [...current, { role: "operator", text: message }]);
    setOracleInput("");
    setOracleBusy(true);
    try {
      const reply: OracleReply = await interrogateOracle(accessToken, message, { callsign });
      playSound(reply.degraded ? "select" : "confirm");
      setMessages((current) => [...current, { role: "oracle", text: reply.response, provider: reply.provider }]);
    } catch (err) {
      playSound("error");
      setMessages((current) => [
        ...current,
        {
          role: "oracle",
          text: "Oracle channel fault. Stand by, preserve intent, and retry transmission."
        }
      ]);
    } finally {
      setOracleBusy(false);
    }
  }

  return (
    <>
      <section className="grid grid-cols-3 gap-3">
        {[
          ["0", "Streak"],
          ["0", "Total XP"],
          ["0/0", "Today"]
        ].map(([value, label]) => (
          <article className="operator-panel px-4 py-5 text-center" key={label}>
            <p className="text-xl text-operator-cyan">{value}</p>
            <p className="mt-2 text-xs uppercase text-white/55">{label}</p>
          </article>
        ))}
      </section>

      <BattleSimulator battleEvent={battleEvent} callsign={callsign} />

      <section className="operator-cyan-panel p-5">
        <div className="flex flex-wrap items-center justify-between gap-3 text-operator-cyan">
          <div className="flex items-center gap-2">
            <Bot size={18} />
            <h2 className="text-sm uppercase tracking-[0.35em]">Oracle</h2>
          </div>
          <span className="text-[10px] uppercase tracking-[0.2em] text-white/45">
            {oracleStatus?.configured ? `${oracleStatus.provider} / ${oracleStatus.model}` : "fallback / no api key"}
          </span>
        </div>
        <div className="mt-4 max-h-72 space-y-3 overflow-y-auto border border-white/10 bg-black/35 p-3">
          {messages.map((message, index) => (
            <div
              className={`text-sm leading-6 ${message.role === "oracle" ? "text-white/88" : "text-operator-cyan"}`}
              key={`${message.role}-${index}`}
            >
              <span className="mr-2 text-xs uppercase text-operator-purple">
                {message.role === "oracle" ? "Oracle" : callsign}
              </span>
              {message.text}
            </div>
          ))}
        </div>
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          <button className="border border-white/15 px-3 py-2 text-xs uppercase text-white/55" onClick={() => playSound("select")}>
            I will create goals manually
          </button>
          <button className="border border-operator-purple px-3 py-2 text-xs uppercase text-operator-purple" onClick={() => playSound("select")}>
            Generate goals automatically
          </button>
        </div>
        <div className="mt-5 flex gap-2">
          <input
            className="min-w-0 flex-1 border border-operator-purple/60 bg-black/50 px-3 py-3 text-sm outline-none focus:border-operator-cyan"
            placeholder="Transmit intent..."
            value={oracleInput}
            onChange={(event) => setOracleInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                transmitIntent();
              }
            }}
          />
          <button
            className="border border-operator-cyan bg-operator-cyan/10 px-4 text-xs uppercase tracking-[0.22em] text-operator-cyan disabled:opacity-40"
            disabled={oracleBusy}
            onClick={transmitIntent}
          >
            {oracleBusy ? "Sync" : "Send"}
          </button>
        </div>
      </section>
    </>
  );
}

function CalendarView({ accessToken }: { accessToken: string }) {
  const [blocks, setBlocks] = useState<CalendarBlock[]>([]);
  const [title, setTitle] = useState("");
  const [day, setDay] = useState(0);
  const [startHour, setStartHour] = useState(7);
  const [endHour, setEndHour] = useState(8);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refreshBlocks() {
    const response = await getCalendarWeek(accessToken);
    setBlocks(response.blocks);
  }

  useEffect(() => {
    refreshBlocks().catch((err) => setError(err instanceof Error ? err.message : "Unable to load calendar"));
  }, [accessToken]);

  async function addBlock() {
    if (!title.trim()) {
      return;
    }

    setBusy(true);
    setError(null);
    try {
      await createCalendarBlock(accessToken, {
        title: title.trim(),
        day_of_week: day,
        start_hour: startHour,
        end_hour: Math.max(endHour, startHour + 1)
      });
      setTitle("");
      await refreshBlocks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Block creation failed");
    } finally {
      setBusy(false);
    }
  }

  async function suggest() {
    setBusy(true);
    setError(null);
    try {
      await suggestCalendar(accessToken);
      await refreshBlocks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Schedule suggestion failed");
    } finally {
      setBusy(false);
    }
  }

  async function removeBlock(block: CalendarBlock) {
    setBusy(true);
    setError(null);
    try {
      await deleteCalendarBlock(accessToken, block.id);
      await refreshBlocks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Block deletion failed");
    } finally {
      setBusy(false);
    }
  }

  function blocksFor(dayIndex: number, hour: number) {
    return blocks.filter((block) => block.day_of_week === dayIndex && block.start_hour <= hour && block.end_hour > hour);
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="operator-glow text-3xl uppercase">Week Planner</h2>
          <p className="mt-2 text-xs uppercase tracking-[0.22em] text-white/45">07:00-22:00 command grid</p>
        </div>
        <button
          className="flex items-center gap-2 border border-operator-cyan bg-operator-cyan/10 px-4 py-3 text-xs uppercase tracking-[0.2em] text-operator-cyan disabled:opacity-40"
          disabled={busy}
          onClick={suggest}
        >
          <Sparkles size={16} />
          Suggest Schedule
        </button>
      </div>

      {error && <p className="border border-red-500/70 px-3 py-2 text-sm text-red-300">{error}</p>}

      <section className="operator-panel p-4">
        <div className="grid gap-2 md:grid-cols-[1fr_110px_100px_100px_44px]">
          <input
            className="min-w-0 border border-operator-purple/50 bg-black/40 px-3 py-3 text-sm outline-none focus:border-operator-cyan"
            placeholder="Manual block title..."
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
          <select
            className="border border-operator-purple/50 bg-black/40 px-3 py-3 text-sm outline-none focus:border-operator-cyan"
            value={day}
            onChange={(event) => setDay(Number(event.target.value))}
          >
            {weekDays.map((label, index) => (
              <option className="bg-black" key={label} value={index}>
                {label}
              </option>
            ))}
          </select>
          <select
            className="border border-operator-purple/50 bg-black/40 px-3 py-3 text-sm outline-none focus:border-operator-cyan"
            value={startHour}
            onChange={(event) => {
              const nextStart = Number(event.target.value);
              setStartHour(nextStart);
              setEndHour(Math.max(endHour, nextStart + 1));
            }}
          >
            {scheduleHours.slice(0, -1).map((hour) => (
              <option className="bg-black" key={hour} value={hour}>
                {formatHour(hour)}
              </option>
            ))}
          </select>
          <select
            className="border border-operator-purple/50 bg-black/40 px-3 py-3 text-sm outline-none focus:border-operator-cyan"
            value={endHour}
            onChange={(event) => setEndHour(Number(event.target.value))}
          >
            {scheduleHours
              .filter((hour) => hour > startHour)
              .concat(22)
              .filter((hour, index, values) => values.indexOf(hour) === index)
              .map((hour) => (
                <option className="bg-black" key={hour} value={hour}>
                  {formatHour(hour)}
                </option>
              ))}
          </select>
          <button
            className="flex items-center justify-center border border-operator-purple text-operator-purple disabled:opacity-40"
            disabled={busy}
            onClick={addBlock}
            title="Add manual block"
          >
            <Plus size={18} />
          </button>
        </div>
      </section>

      <section className="overflow-x-auto border border-operator-purple/60 bg-black/30">
        <div className="min-w-[820px]">
          <div className="grid grid-cols-[72px_repeat(7,1fr)] border-b border-operator-purple/40">
            <div className="px-2 py-3 text-xs text-white/35">TIME</div>
            {weekDays.map((label) => (
              <div className="border-l border-operator-purple/25 px-2 py-3 text-center text-xs text-white/65" key={label}>
                {label}
              </div>
            ))}
          </div>

          {scheduleHours.slice(0, -1).map((hour) => (
            <div className="grid min-h-16 grid-cols-[72px_repeat(7,1fr)] border-b border-white/10" key={hour}>
              <div className="px-2 py-3 text-xs text-white/45">{formatHour(hour)}</div>
              {weekDays.map((label, dayIndex) => {
                const cellBlocks = blocksFor(dayIndex, hour);
                return (
                  <div className="min-h-16 border-l border-white/10 p-1" key={`${label}-${hour}`}>
                    {cellBlocks.map((block) => (
                      <div
                        className={`mb-1 border px-2 py-2 text-[11px] ${
                          block.source === "oracle_suggested"
                            ? "border-operator-cyan bg-operator-cyan/10 text-operator-cyan"
                            : "border-operator-purple bg-operator-purple/10 text-white"
                        }`}
                        key={block.id}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span className="min-w-0 break-words uppercase leading-4">{block.title}</span>
                          <button className="shrink-0 text-white/45" disabled={busy} onClick={() => removeBlock(block)} title="Delete block">
                            <Trash2 size={12} />
                          </button>
                        </div>
                        <div className="mt-1 flex items-center gap-1 text-[10px] text-white/45">
                          <Clock size={10} />
                          {formatHour(block.start_hour)}-{formatHour(block.end_hour)}
                        </div>
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>
          ))}

          {blocks.length === 0 && (
            <div className="px-4 py-8 text-center text-sm text-white/45">
              Empty grid. Tap SUGGEST SCHEDULE to let Oracle place this week's priorities.
            </div>
          )}
        </div>
      </section>
    </section>
  );
}

function formatHour(hour: number) {
  return `${String(hour).padStart(2, "0")}:00`;
}

function GoalsMatrix({
  accessToken,
  onBattleEvent,
  playSound
}: {
  accessToken: string;
  onBattleEvent: (event: BattleEvent | null) => void;
  playSound: (kind?: "select" | "confirm" | "error") => void;
}) {
  const [goalList, setGoalList] = useState<GoalList | null>(null);
  const [openSections, setOpenSections] = useState<Record<GoalHorizon, boolean>>({
    five_year: true,
    yearly: true,
    monthly: true,
    weekly: true,
    daily_part_1: true,
    daily_part_2: false
  });
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [targets, setTargets] = useState<Record<string, number>>({});
  const [breakdownPreview, setBreakdownPreview] = useState<{
    goal: Goal;
    childHorizon: GoalHorizon;
    tasks: string[];
  } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refreshGoals() {
    const goals = await listGoals(accessToken);
    setGoalList(goals);
  }

  useEffect(() => {
    refreshGoals().catch((err) => setError(err instanceof Error ? err.message : "Unable to load goals"));
  }, [accessToken]);

  const dailyDone = useMemo(() => {
    const daily = [...(goalList?.grouped.daily_part_1 ?? []), ...(goalList?.grouped.daily_part_2 ?? [])];
    const total = daily.reduce((sum, goal) => sum + goal.target_count, 0);
    const done = daily.reduce((sum, goal) => sum + goal.completed_count, 0);
    return `${done}/${total}`;
  }, [goalList]);

  async function addGoal(horizon: GoalHorizon, parentId?: string) {
    const key = parentId ?? horizon;
    const title = drafts[key]?.trim();
    if (!title) {
      return;
    }

    setBusy(key);
    setError(null);
    try {
      if (parentId) {
        await spawnChildGoal(accessToken, parentId, {
          title,
          horizon,
          target_count: targets[key] || 1,
          priority: horizon.includes("daily") ? 1 : 0
        });
      } else {
        await createGoal(accessToken, {
          title,
          horizon,
          target_count: targets[key] || 1,
          priority: horizon.includes("daily") ? 1 : 0
        });
      }
      setDrafts((current) => ({ ...current, [key]: "" }));
      await refreshGoals();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Goal creation failed");
    } finally {
      setBusy(null);
    }
  }

  async function adjust(goal: Goal, delta: number) {
    setBusy(goal.id);
    try {
      const response = await changeGoalProgress(accessToken, goal.id, delta);
      if (response.battle_event) {
        onBattleEvent(response.battle_event);
        playSound("confirm");
      } else {
        playSound("select");
      }
      await refreshGoals();
    } catch (err) {
      playSound("error");
      setError(err instanceof Error ? err.message : "Progress update failed");
    } finally {
      setBusy(null);
    }
  }

  async function breakDown(goal: Goal) {
    setBusy(goal.id);
    setError(null);
    try {
      const preview = await oracleBreakdown(accessToken, goal.id);
      setBreakdownPreview({
        goal,
        childHorizon: preview.child_horizon,
        tasks: preview.tasks
      });
      playSound("select");
    } catch (err) {
      playSound("error");
      setError(err instanceof Error ? err.message : "Oracle breakdown failed");
    } finally {
      setBusy(null);
    }
  }

  async function acceptBreakdownPreview() {
    if (!breakdownPreview) {
      return;
    }

    setBusy(breakdownPreview.goal.id);
    setError(null);
    try {
      await acceptOracleBreakdown(accessToken, breakdownPreview.goal.id, breakdownPreview.tasks);
      setBreakdownPreview(null);
      playSound("confirm");
      await refreshGoals();
    } catch (err) {
      playSound("error");
      setError(err instanceof Error ? err.message : "Oracle breakdown accept failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="space-y-5">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h2 className="operator-glow text-3xl uppercase">Goals Matrix</h2>
          <p className="mt-2 text-xs uppercase tracking-[0.22em] text-white/45">Daily completion: {dailyDone}</p>
        </div>
      </div>

      {error && <p className="border border-red-500/70 px-3 py-2 text-sm text-red-300">{error}</p>}

      {breakdownPreview && (
        <section className="operator-cyan-panel p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm uppercase tracking-[0.25em] text-operator-cyan">Oracle Preview</h3>
              <p className="mt-1 text-xs text-white/45">
                {breakdownPreview.goal.title} -&gt; {breakdownPreview.childHorizon.replaceAll("_", " ")}
              </p>
            </div>
            <button className="text-xs uppercase text-white/45" onClick={() => setBreakdownPreview(null)}>
              Reject
            </button>
          </div>
          <div className="mt-4 space-y-2">
            {breakdownPreview.tasks.map((task, index) => (
              <input
                className="w-full border border-white/15 bg-black/40 px-3 py-3 text-sm outline-none focus:border-operator-cyan"
                key={`${breakdownPreview.goal.id}-${index}`}
                value={task}
                onChange={(event) =>
                  setBreakdownPreview((current) =>
                    current
                      ? {
                          ...current,
                          tasks: current.tasks.map((item, itemIndex) => (itemIndex === index ? event.target.value : item))
                        }
                      : current
                  )
                }
              />
            ))}
          </div>
          <div className="mt-4 flex gap-2">
            <button
              className="flex-1 border border-operator-cyan bg-operator-cyan/10 px-3 py-3 text-xs uppercase tracking-[0.18em] text-operator-cyan disabled:opacity-40"
              disabled={busy === breakdownPreview.goal.id}
              onClick={acceptBreakdownPreview}
            >
              Accept & Spawn
            </button>
            <button
              className="border border-white/15 px-3 py-3 text-xs uppercase tracking-[0.18em] text-white/55"
              onClick={() => setBreakdownPreview(null)}
            >
              Reject
            </button>
          </div>
        </section>
      )}

      {goalSections.map((section) => {
        const goals = goalList?.grouped[section.horizon] ?? [];
        const open = openSections[section.horizon];
        const sectionTotal = goals.reduce((sum, goal) => sum + goal.target_count, 0);
        const sectionDone = goals.reduce((sum, goal) => sum + goal.completed_count, 0);
        return (
          <article className="operator-panel" key={section.horizon}>
            <button
              className="flex w-full items-center justify-between gap-3 px-4 py-4 text-left"
              onClick={() => setOpenSections((current) => ({ ...current, [section.horizon]: !open }))}
            >
              <span>
                <span className="operator-glow block text-xl uppercase">{section.title}</span>
                <span className="mt-1 block text-xs text-white/45">{section.prompt}</span>
              </span>
              <span className="flex items-center gap-3 text-operator-cyan">
                <span className="text-sm">{sectionDone}/{sectionTotal}</span>
                {open ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
              </span>
            </button>

            {open && (
              <div className="border-t border-operator-purple/40 px-4 py-4">
                <GoalComposer
                  busy={busy === section.horizon}
                  draft={drafts[section.horizon] ?? ""}
                  onDraft={(value) => setDrafts((current) => ({ ...current, [section.horizon]: value }))}
                  onSubmit={() => addGoal(section.horizon)}
                  onTarget={(value) => setTargets((current) => ({ ...current, [section.horizon]: value }))}
                  target={targets[section.horizon] ?? 1}
                />

                <div className="mt-4 space-y-3">
                  {goals.length === 0 && (
                    <p className="py-4 text-sm italic text-white/45">
                      No targets yet. Add one or use Oracle Breakdown from a parent goal.
                    </p>
                  )}
                  {goals.map((goal) => (
                    <GoalRow
                      busy={busy === goal.id}
                      childHorizon={section.child}
                      drafts={drafts}
                      goal={goal}
                      key={goal.id}
                      onAdjust={adjust}
                      onBreakdown={breakDown}
                      onChildDraft={(value) => setDrafts((current) => ({ ...current, [goal.id]: value }))}
                      onChildTarget={(value) => setTargets((current) => ({ ...current, [goal.id]: value }))}
                      onSpawnChild={() => section.child && addGoal(section.child, goal.id)}
                      target={targets[goal.id] ?? 1}
                    />
                  ))}
                </div>
              </div>
            )}
          </article>
        );
      })}
    </section>
  );
}

function GoalComposer({
  busy,
  draft,
  onDraft,
  onSubmit,
  onTarget,
  target
}: {
  busy: boolean;
  draft: string;
  onDraft: (value: string) => void;
  onSubmit: () => void;
  onTarget: (value: number) => void;
  target: number;
}) {
  return (
    <div className="grid grid-cols-[1fr_84px_44px] gap-2">
      <input
        className="min-w-0 border border-operator-purple/50 bg-black/40 px-3 py-3 text-sm outline-none focus:border-operator-cyan"
        placeholder="Add target..."
        value={draft}
        onChange={(event) => onDraft(event.target.value)}
      />
      <input
        className="border border-operator-purple/50 bg-black/40 px-2 py-3 text-center text-sm outline-none focus:border-operator-cyan"
        min={1}
        max={999}
        type="number"
        value={target}
        onChange={(event) => onTarget(Number(event.target.value))}
      />
      <button
        className="flex items-center justify-center border border-operator-purple text-operator-purple disabled:opacity-40"
        disabled={busy}
        onClick={onSubmit}
        title="Add goal"
      >
        <Plus size={18} />
      </button>
    </div>
  );
}

function GoalRow({
  busy,
  childHorizon,
  drafts,
  goal,
  onAdjust,
  onBreakdown,
  onChildDraft,
  onChildTarget,
  onSpawnChild,
  target
}: {
  busy: boolean;
  childHorizon?: GoalHorizon;
  drafts: Record<string, string>;
  goal: Goal;
  onAdjust: (goal: Goal, delta: number) => void;
  onBreakdown: (goal: Goal) => void;
  onChildDraft: (value: string) => void;
  onChildTarget: (value: number) => void;
  onSpawnChild: () => void;
  target: number;
}) {
  const canBreakdown = goal.horizon !== "daily_part_2";
  return (
    <div className="border border-white/10 bg-black/25 p-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <p className={`text-sm uppercase ${goal.is_complete ? "text-operator-cyan" : "text-white"}`}>{goal.title}</p>
          <p className="mt-1 text-xs text-white/40">
            {goal.part ? `${goal.part} / ` : ""}Priority {goal.priority}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="border border-white/20 p-2 text-white/55" disabled={busy} onClick={() => onAdjust(goal, -1)}>
            <Minus size={14} />
          </button>
          <span className="min-w-14 text-center text-sm text-operator-cyan">
            {goal.completed_count}/{goal.target_count}
          </span>
          <button className="border border-operator-cyan p-2 text-operator-cyan" disabled={busy} onClick={() => onAdjust(goal, 1)}>
            <Plus size={14} />
          </button>
        </div>
      </div>

      <div className="mt-3 h-1 bg-white/10">
        <div
          className="h-full bg-operator-cyan"
          style={{ width: `${Math.min(100, (goal.completed_count / goal.target_count) * 100)}%` }}
        />
      </div>

      {childHorizon && (
        <div className="mt-3 grid grid-cols-[1fr_72px_44px] gap-2">
          <input
            className="min-w-0 border border-white/15 bg-black/30 px-3 py-2 text-xs outline-none focus:border-operator-cyan"
            placeholder={`Spawn ${childHorizon.replaceAll("_", " ")}...`}
            value={drafts[goal.id] ?? ""}
            onChange={(event) => onChildDraft(event.target.value)}
          />
          <input
            className="border border-white/15 bg-black/30 px-2 py-2 text-center text-xs outline-none focus:border-operator-cyan"
            min={1}
            max={999}
            type="number"
            value={target}
            onChange={(event) => onChildTarget(Number(event.target.value))}
          />
          <button className="flex items-center justify-center border border-white/25 text-white/65" disabled={busy} onClick={onSpawnChild}>
            <Plus size={16} />
          </button>
        </div>
      )}

      {canBreakdown && (
        <button
          className="mt-3 flex w-full items-center justify-center gap-2 border border-operator-cyan/70 px-3 py-2 text-xs uppercase tracking-[0.18em] text-operator-cyan disabled:opacity-40"
          disabled={busy}
          onClick={() => onBreakdown(goal)}
        >
          <Sparkles size={14} />
          Oracle Breakdown
        </button>
      )}
    </div>
  );
}

function CharacterView({
  accessToken,
  battleEvent,
  playSound
}: {
  accessToken: string;
  battleEvent: BattleEvent | null;
  playSound: (kind?: "select" | "confirm" | "error") => void;
}) {
  const [profile, setProfile] = useState<CharacterProfile | null>(null);
  const [activeSkillStat, setActiveSkillStat] = useState("intellect");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refreshProfile() {
    const response = await getCharacterProfile(accessToken);
    setProfile(response);
    if (response.stats.length > 0 && !response.stats.some((stat) => stat.stat_key === activeSkillStat)) {
      setActiveSkillStat(response.stats[0].stat_key);
    }
  }

  useEffect(() => {
    refreshProfile().catch((err) => setError(err instanceof Error ? err.message : "Unable to load character"));
  }, [accessToken]);

  async function updateCustomizer(payload: Parameters<typeof updateCharacterCustomizer>[1]) {
    setBusy(true);
    setError(null);
    try {
      playSound("confirm");
      const response = await updateCharacterCustomizer(accessToken, payload);
      setProfile(response);
    } catch (err) {
      playSound("error");
      setError(err instanceof Error ? err.message : "Customizer update failed");
    } finally {
      setBusy(false);
    }
  }

  if (!profile) {
    return (
      <section className="operator-panel p-5">
        <h2 className="operator-glow text-2xl uppercase">Character Profile</h2>
        <p className="mt-3 text-sm text-white/55">Loading profile matrix...</p>
      </section>
    );
  }

  const radarData = profile.stats.map((stat) => ({
    stat: stat.label,
    level: stat.effective_level
  }));
  const activeSkills = profile.skills.filter((skill) => skill.stat_key === activeSkillStat);

  return (
    <section className="space-y-5">
      <div>
        <p className="text-xs uppercase tracking-[0.35em] text-operator-purple">Character Profile</p>
        <h2 className="operator-glow mt-1 text-4xl uppercase">{profile.callsign}</h2>
        <p className="mt-2 text-sm text-white/55">
          Level {profile.level} / {profile.xp} Total XP / {profile.character_class}
        </p>
      </div>

      {error && <p className="border border-red-500/70 px-3 py-2 text-sm text-red-300">{error}</p>}

      <BattleSimulator battleEvent={battleEvent} callsign={profile.callsign} />

      <section className="grid gap-5 lg:grid-cols-[280px_1fr]">
        <article className="operator-panel p-4">
          <PixelAvatar profile={profile} />
          <div className="mt-4 grid grid-cols-3 gap-2">
            {characterClasses.map((characterClass) => (
              <button
                className={`border px-2 py-3 text-[11px] uppercase ${
                  profile.character_class === characterClass
                    ? "border-operator-cyan bg-operator-cyan/10 text-operator-cyan"
                    : "border-white/15 text-white/55"
                }`}
                disabled={busy}
                key={characterClass}
                onClick={() => updateCustomizer({ character_class: characterClass })}
              >
                {characterClass}
              </button>
            ))}
          </div>
        </article>

        <article className="operator-panel min-h-80 p-4">
          <ResponsiveContainer height={300} width="100%">
            <RadarChart data={radarData}>
              <PolarGrid stroke="rgba(208,0,255,0.35)" />
              <PolarAngleAxis dataKey="stat" stroke="#D000FF" tick={{ fill: "#D000FF", fontSize: 11 }} />
              <Radar dataKey="level" fill="#00F0FF" fillOpacity={0.22} stroke="#00F0FF" strokeWidth={2} />
            </RadarChart>
          </ResponsiveContainer>
        </article>
      </section>

      <section className="grid gap-3 md:grid-cols-2">
        {profile.stats.map((stat) => (
          <StatCard key={stat.stat_key} stat={stat} />
        ))}
      </section>

      <section className="operator-panel p-4">
        <h3 className="operator-glow text-2xl uppercase">Customizer</h3>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          <CosmeticSelector
            disabled={busy}
            label="Head"
            options={cosmeticOptions.head_cosmetic}
            value={profile.head_cosmetic}
            onChange={(value) => updateCustomizer({ head_cosmetic: value })}
          />
          <CosmeticSelector
            disabled={busy}
            label="Body"
            options={cosmeticOptions.body_cosmetic}
            value={profile.body_cosmetic}
            onChange={(value) => updateCustomizer({ body_cosmetic: value })}
          />
          <CosmeticSelector
            disabled={busy}
            label="Gear"
            options={cosmeticOptions.gear_cosmetic}
            value={profile.gear_cosmetic}
            onChange={(value) => updateCustomizer({ gear_cosmetic: value })}
          />
        </div>
      </section>

      <section className="operator-panel p-4">
        <div className="flex items-center justify-between gap-3">
          <h3 className="operator-glow text-2xl uppercase">Skill Trees</h3>
          <span className="text-xs uppercase text-operator-cyan">
            {profile.skills.filter((skill) => skill.unlocked).length}/{profile.skills.length} Unlocked
          </span>
        </div>
        <div className="mt-4 flex gap-2 overflow-x-auto">
          {profile.stats.map((stat) => (
            <button
              className={`shrink-0 border px-3 py-2 text-xs uppercase ${
                activeSkillStat === stat.stat_key
                  ? "border-operator-purple bg-operator-purple/15 text-operator-purple"
                  : "border-white/15 text-white/55"
              }`}
              key={stat.stat_key}
              onClick={() => {
                playSound("select");
                setActiveSkillStat(stat.stat_key);
              }}
            >
              {stat.label} {stat.effective_level}
            </button>
          ))}
        </div>

        <div className="mt-4 space-y-3">
          {activeSkills.length === 0 && <p className="py-4 text-sm text-white/45">No skill nodes assigned yet.</p>}
          {activeSkills.map((skill) => (
            <div
              className={`flex items-center gap-3 border p-3 ${
                skill.unlocked ? "border-operator-cyan/70 text-operator-cyan" : "border-white/10 text-white/35"
              }`}
              key={skill.skill_key}
            >
              <div className="flex h-10 w-10 items-center justify-center border border-current">
                {skill.unlocked ? <Zap size={18} /> : <Lock size={18} />}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm uppercase">{skill.label}</p>
                <div className="mt-2 h-1 bg-white/10">
                  <div className="h-full bg-current" style={{ width: skill.unlocked ? "100%" : "28%" }} />
                </div>
              </div>
              <span className="text-xs uppercase">Lvl {skill.required_level}</span>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h3 className="operator-glow text-2xl uppercase">Achievements</h3>
        <div className="mt-3 grid grid-cols-3 gap-3">
          {profile.achievements.map((achievement) => (
            <article
              className={`border p-4 text-center ${
                achievement.unlocked ? "border-operator-cyan text-operator-cyan" : "border-white/10 text-white/30"
              }`}
              key={achievement.achievement_key}
            >
              <Trophy className="mx-auto" size={24} />
              <p className="mt-3 text-xs uppercase">{achievement.label}</p>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}

function BattleSimulator({ battleEvent, callsign }: { battleEvent: BattleEvent | null; callsign: string }) {
  const bossHp = battleEvent ? Math.max(0, 100 - battleEvent.boss_damage) : 100;
  return (
    <section className="operator-cyan-panel overflow-hidden p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm uppercase tracking-[0.3em] text-operator-cyan">Battle Simulator</h3>
          <p className="mt-1 text-xs text-white/45">
            {battleEvent ? `Target neutralized: ${battleEvent.goal_title}` : "Awaiting high-priority completion signal."}
          </p>
        </div>
        <span className="text-xs uppercase text-operator-purple">Boss HP {bossHp}%</span>
      </div>

      <div className="relative h-44 border border-white/10 bg-black/60">
        <div className="absolute inset-x-0 bottom-0 h-10 border-t border-operator-purple/30 bg-operator-purple/5" />
        <div
          className={`absolute bottom-10 left-8 h-24 w-16 border-2 border-operator-cyan bg-operator-surface ${
            battleEvent ? "animate-[operatorAttack_900ms_ease-out_1]" : ""
          }`}
        >
          <div className="absolute -top-8 left-2 h-8 w-12 border-2 border-operator-cyan bg-black" />
          <div className="absolute left-4 top-3 h-3 w-8 bg-operator-cyan" />
          <div className="absolute -right-8 top-6 h-3 w-10 bg-operator-purple" />
          <span className="absolute -bottom-6 left-1/2 -translate-x-1/2 text-[10px] uppercase text-white/55">{callsign}</span>
        </div>

        <div className={`absolute bottom-10 right-10 h-28 w-20 border-2 border-operator-purple bg-black ${battleEvent ? "animate-pulse" : ""}`}>
          <div className="absolute left-3 top-3 h-3 w-3 bg-operator-purple" />
          <div className="absolute right-3 top-3 h-3 w-3 bg-operator-purple" />
          <div className="absolute bottom-4 left-2 h-3 w-16 border border-operator-purple" />
          <span className="absolute -bottom-6 left-1/2 -translate-x-1/2 whitespace-nowrap text-[10px] uppercase text-white/55">
            Goal Boss
          </span>
        </div>

        <div className="absolute right-8 top-5 h-2 w-28 bg-white/10">
          <div className="h-full bg-operator-purple" style={{ width: `${bossHp}%` }} />
        </div>

        {battleEvent && (
          <>
            <div className="absolute left-1/2 top-8 animate-[combatFloat_1100ms_ease-out_1] text-xl text-operator-cyan">
              +{battleEvent.xp_awarded} XP
            </div>
            <div className="absolute right-28 top-16 animate-[combatFloat_1100ms_ease-out_1] text-lg text-operator-purple">
              -{battleEvent.boss_damage} HP
            </div>
            <div className="absolute bottom-4 left-4 text-xs uppercase text-white/55">
              {battleEvent.stat_key} sync {battleEvent.leveled_up ? "/ level up" : "/ stable"}
              {battleEvent.achievement_unlocked ? ` / ${battleEvent.achievement_unlocked}` : ""}
            </div>
          </>
        )}
      </div>
    </section>
  );
}

function StatCard({ stat }: { stat: CharacterStat }) {
  const Icon = statIcons[stat.stat_key] ?? Award;
  return (
    <article className="operator-panel p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Icon className="text-operator-purple" size={20} />
          <div>
            <p className="text-sm uppercase">{stat.label}</p>
            <p className="mt-1 text-xs text-white/45">
              Base {stat.level} / Class +{stat.class_bonus}
            </p>
          </div>
        </div>
        <span className="text-sm uppercase text-operator-cyan">Lvl {stat.effective_level}</span>
      </div>
      <div className="mt-3 h-1 bg-white/10">
        <div className="h-full bg-operator-cyan" style={{ width: `${Math.min(100, stat.effective_level * 10)}%` }} />
      </div>
    </article>
  );
}

function CosmeticSelector({
  disabled,
  label,
  onChange,
  options,
  value
}: {
  disabled: boolean;
  label: string;
  onChange: (value: string) => void;
  options: string[];
  value: string;
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs uppercase tracking-[0.22em] text-white/45">{label}</span>
      <select
        className="w-full border border-operator-purple/50 bg-black/40 px-3 py-3 text-sm uppercase outline-none focus:border-operator-cyan"
        disabled={disabled}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map((option) => (
          <option className="bg-black" key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

function PixelAvatar({ profile }: { profile: CharacterProfile }) {
  const classColor =
    profile.character_class === "Cyber-Monk"
      ? "#D000FF"
      : profile.character_class === "Dreadnought"
        ? "#FF7A00"
        : "#00F0FF";
  const bodyWidth = profile.body_cosmetic === "armor" ? 86 : profile.body_cosmetic === "jacket" ? 72 : 64;
  const headShape = profile.head_cosmetic === "hood" ? "rounded-t-[28px]" : "rounded-sm";
  const gearLabel = profile.gear_cosmetic === "deck" ? "DATA" : profile.gear_cosmetic === "gauntlet" ? "FIST" : "BLADE";

  return (
    <div className="relative mx-auto flex h-72 w-full max-w-64 items-center justify-center overflow-hidden border border-operator-cyan/50 bg-black/50">
      <div className="absolute inset-0 opacity-40 [background-image:linear-gradient(rgba(0,240,255,0.12)_1px,transparent_1px),linear-gradient(90deg,rgba(208,0,255,0.1)_1px,transparent_1px)] [background-size:18px_18px]" />
      <div className="relative flex flex-col items-center">
        {profile.head_cosmetic === "halo" && (
          <div className="mb-1 h-2 w-20 border border-operator-purple shadow-[0_0_16px_rgba(208,0,255,0.8)]" />
        )}
        <div
          className={`relative h-16 w-20 border-2 bg-black ${headShape}`}
          style={{ borderColor: classColor, boxShadow: `0 0 18px ${classColor}` }}
        >
          <div className="absolute left-3 top-6 h-2 w-4 bg-operator-cyan" />
          <div className="absolute right-3 top-6 h-2 w-4 bg-operator-cyan" />
          {profile.head_cosmetic === "visor" && <div className="absolute left-4 top-5 h-4 w-12 border border-operator-cyan" />}
        </div>
        <div
          className="relative mt-1 h-24 border-2 bg-operator-surface"
          style={{ width: bodyWidth, borderColor: classColor }}
        >
          <div className="absolute left-1/2 top-3 h-14 w-1 -translate-x-1/2 bg-operator-cyan" />
          {profile.body_cosmetic === "cloak" && (
            <div className="absolute -bottom-8 left-1/2 h-24 w-28 -translate-x-1/2 border-x border-b border-operator-purple/70" />
          )}
        </div>
        <div className="mt-2 flex gap-8">
          <div className="h-12 w-4 border border-white/25 bg-black" />
          <div className="h-12 w-4 border border-white/25 bg-black" />
        </div>
      </div>
      <div className="absolute right-4 top-20 border border-operator-cyan px-2 py-8 text-[10px] uppercase text-operator-cyan">
        {gearLabel}
      </div>
      <Heart className="absolute bottom-4 left-4 text-operator-purple" size={18} />
    </div>
  );
}

function GuildView({
  accessToken,
  playSound
}: {
  accessToken: string;
  playSound: (kind?: "select" | "confirm" | "error") => void;
}) {
  const [activeTab, setActiveTab] = useState<"MY GUILD" | "GUILDS" | "GLOBAL">("MY GUILD");
  const [status, setStatus] = useState<GuildStatus | null>(null);
  const [guilds, setGuilds] = useState<Guild[]>([]);
  const [feed, setFeed] = useState<FeedEvent[]>([]);
  const [modal, setModal] = useState<"forge" | "join" | null>(null);
  const [guildName, setGuildName] = useState("");
  const [motto, setMotto] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refreshGuild() {
    const [nextStatus, nextGuilds, nextFeed] = await Promise.all([
      getGuildStatus(accessToken),
      discoverGuilds(accessToken),
      getGlobalFeed(accessToken)
    ]);
    setStatus(nextStatus);
    setGuilds(nextGuilds);
    setFeed(nextFeed);
  }

  useEffect(() => {
    refreshGuild().catch((err) => setError(err instanceof Error ? err.message : "Unable to load guild data"));
  }, [accessToken]);

  useEffect(() => {
    const wsBase = process.env.NEXT_PUBLIC_WS_BASE_URL ?? "ws://localhost:8000";
    const socket = new WebSocket(`${wsBase}/ws/guild-feed?token=${encodeURIComponent(accessToken)}`);
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload.type !== "battle_reward") {
        return;
      }
      setFeed((current) => [
        {
          id: payload.id,
          event_type: "battle_reward",
          operator: payload.operator,
          goal_title: payload.goal_title,
          xp_awarded: payload.xp_awarded,
          stat_key: payload.stat_key,
          created_at: payload.created_at
        },
        ...current.filter((item) => item.id !== payload.id)
      ].slice(0, 50));
    };
    return () => socket.close();
  }, [accessToken]);

  async function submitForge() {
    if (!guildName.trim()) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      playSound("confirm");
      const nextStatus = await forgeGuild(accessToken, { name: guildName.trim(), motto: motto.trim() || undefined });
      setStatus(nextStatus);
      setModal(null);
      setGuildName("");
      setMotto("");
      await refreshGuild();
    } catch (err) {
      playSound("error");
      setError(err instanceof Error ? err.message : "Guild forge failed");
    } finally {
      setBusy(false);
    }
  }

  async function submitJoin() {
    const code = joinCode.trim().toUpperCase();
    if (!/^[A-Z0-9]{6}$/.test(code)) {
      setError("Code must be exactly 6 alphanumeric characters");
      playSound("error");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      playSound("confirm");
      const nextStatus = await joinGuild(accessToken, code);
      setStatus(nextStatus);
      setModal(null);
      setJoinCode("");
      await refreshGuild();
    } catch (err) {
      playSound("error");
      setError(err instanceof Error ? err.message : "Guild join failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-5">
      <div>
        <h2 className="operator-glow text-3xl uppercase">Guild</h2>
        <p className="mt-2 text-xs uppercase tracking-[0.22em] text-white/45">Accountability collective</p>
      </div>

      {error && <p className="border border-red-500/70 px-3 py-2 text-sm text-red-300">{error}</p>}

      <div className="grid grid-cols-3 border border-white/10 bg-black/40">
        {(["MY GUILD", "GUILDS", "GLOBAL"] as const).map((tab) => (
          <button
            className={`flex items-center justify-center gap-2 px-2 py-3 text-xs uppercase ${
              activeTab === tab ? "bg-operator-purple/15 text-white" : "text-white/50"
            }`}
            key={tab}
            onClick={() => {
              playSound("select");
              setActiveTab(tab);
            }}
          >
            {tab === "MY GUILD" && <Shield size={15} />}
            {tab === "GUILDS" && <Trophy size={15} />}
            {tab === "GLOBAL" && <Globe2 size={15} />}
            {tab}
          </button>
        ))}
      </div>

      {activeTab === "MY GUILD" && (
        <section className="operator-panel p-5">
          {status?.aligned && status.guild ? (
            <div>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h3 className="operator-glow text-2xl uppercase">{status.guild.name}</h3>
                  <p className="mt-2 text-sm text-white/55">{status.guild.motto || "No motto encoded."}</p>
                </div>
                <span className="border border-operator-cyan px-3 py-2 text-xs uppercase text-operator-cyan">
                  {status.guild.role}
                </span>
              </div>
              <div className="mt-5 border border-white/10 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-white/45">Single-use access token</p>
                <p className="mt-2 text-3xl uppercase tracking-[0.35em] text-operator-cyan">
                  {status.guild.invite_code ?? "CONSUMED"}
                </p>
              </div>
            </div>
          ) : (
            <div className="py-5 text-center">
              <Shield className="mx-auto text-operator-purple" size={40} />
              <h3 className="mt-4 text-2xl uppercase">No Guild</h3>
              <p className="mt-2 text-sm text-white/50">Forge your own collective or join an ally's party.</p>
              <div className="mt-6 grid gap-3 sm:grid-cols-2">
                <button
                  className="flex items-center justify-center gap-2 border border-operator-purple bg-operator-purple/20 px-4 py-4 text-sm uppercase text-operator-purple"
                  onClick={() => setModal("forge")}
                >
                  <Plus size={18} />
                  Forge
                </button>
                <button
                  className="flex items-center justify-center gap-2 border border-operator-cyan bg-operator-cyan/10 px-4 py-4 text-sm uppercase text-operator-cyan"
                  onClick={() => setModal("join")}
                >
                  <ShieldPlus size={18} />
                  Join
                </button>
              </div>
            </div>
          )}
        </section>
      )}

      {activeTab === "GUILDS" && (
        <section className="space-y-3">
          {guilds.length === 0 && <p className="operator-panel p-5 text-sm text-white/45">No guild signals discovered.</p>}
          {guilds.map((guild) => (
            <article className="operator-panel p-4" key={guild.id}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-lg uppercase text-white">{guild.name}</h3>
                  <p className="mt-1 text-sm text-white/50">{guild.motto || "No motto encoded."}</p>
                </div>
                {guild.invite_code && <span className="text-xs uppercase text-operator-cyan">Open token</span>}
              </div>
            </article>
          ))}
        </section>
      )}

      {activeTab === "GLOBAL" && <GlobalFeed feed={feed} />}

      {modal === "forge" && (
        <GuildModal title="Forge Guild" onClose={() => setModal(null)}>
          <input
            className="w-full border border-operator-purple bg-black px-4 py-3 outline-none focus:border-operator-cyan"
            placeholder="Guild name"
            value={guildName}
            onChange={(event) => setGuildName(event.target.value)}
          />
          <input
            className="mt-3 w-full border border-white/15 bg-black px-4 py-3 outline-none focus:border-operator-cyan"
            placeholder="Motto (optional)"
            value={motto}
            onChange={(event) => setMotto(event.target.value)}
          />
          <button
            className="mt-4 w-full border border-operator-purple bg-operator-purple/30 px-4 py-3 uppercase text-operator-purple disabled:opacity-40"
            disabled={busy}
            onClick={submitForge}
          >
            Create
          </button>
        </GuildModal>
      )}

      {modal === "join" && (
        <GuildModal title="Join Via Code" onClose={() => setModal(null)}>
          <input
            className="w-full border border-operator-purple bg-black px-4 py-3 text-center uppercase tracking-[0.35em] outline-none focus:border-operator-cyan"
            maxLength={6}
            placeholder="6-CHAR"
            value={joinCode}
            onChange={(event) => setJoinCode(event.target.value.toUpperCase())}
          />
          <button
            className="mt-4 w-full border border-operator-cyan bg-operator-cyan/15 px-4 py-3 uppercase text-operator-cyan disabled:opacity-40"
            disabled={busy}
            onClick={submitJoin}
          >
            Enter
          </button>
        </GuildModal>
      )}
    </section>
  );
}

function GlobalFeed({ feed }: { feed: FeedEvent[] }) {
  return (
    <section className="operator-cyan-panel p-4">
      <h3 className="text-sm uppercase tracking-[0.3em] text-operator-cyan">Global Feed</h3>
      <div className="mt-4 space-y-3">
        {feed.length === 0 && <p className="py-4 text-sm text-white/45">No public completions broadcast yet.</p>}
        {feed.map((event) => (
          <article className="border border-white/10 bg-black/30 p-3" key={event.id}>
            <p className="text-sm uppercase text-white">
              {event.operator} defeated {event.goal_title || "an unnamed target"}
            </p>
            <p className="mt-1 text-xs uppercase text-operator-cyan">
              +{event.xp_awarded ?? 0} XP / {event.stat_key ?? "unknown"} sync
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}

function GuildModal({
  children,
  onClose,
  title
}: {
  children: ReactNode;
  onClose: () => void;
  title: string;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 px-5">
      <section className="w-full max-w-lg border border-operator-purple bg-[#050507] p-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <h3 className="operator-glow text-2xl uppercase">{title}</h3>
          <button className="text-white/60" onClick={onClose} title="Close">
            <X size={18} />
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}

function PlaceholderView({ body, title }: { body: string; title: string }) {
  return (
    <section className="operator-panel p-5">
      <h2 className="operator-glow text-2xl uppercase">{title}</h2>
      <p className="mt-3 text-sm leading-6 text-white/60">{body}</p>
    </section>
  );
}

type AuthFrameProps = {
  email: string;
  error: string | null;
  loading: boolean;
  mode: "login" | "register";
  password: string;
  setEmail: (value: string) => void;
  setMode: (value: "login" | "register") => void;
  setPassword: (value: string) => void;
  submitAuth: () => void;
};

function AuthFrame(props: AuthFrameProps) {
  return (
    <main className="flex min-h-screen items-center justify-center px-5 text-white">
      <section className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center border border-operator-purple text-operator-purple shadow-[0_0_24px_rgba(208,0,255,0.55)]">
            <Zap size={30} />
          </div>
          <h1 className="operator-glow text-4xl uppercase">OPERATOR</h1>
          <p className="mt-2 text-xs uppercase tracking-[0.45em] text-white/45">Level Up Your Life</p>
        </div>

        <div className="space-y-4">
          <CyberInput label="Email" value={props.email} onChange={props.setEmail} />
          <CyberInput label="Password" type="password" value={props.password} onChange={props.setPassword} />
          {props.error && <p className="border border-red-500/70 px-3 py-2 text-sm text-red-300">{props.error}</p>}
          <button
            className="w-full border border-operator-purple bg-operator-purple/10 px-5 py-4 text-lg uppercase tracking-[0.25em] text-operator-purple shadow-[0_0_20px_rgba(208,0,255,0.45)] disabled:opacity-50"
            disabled={props.loading}
            onClick={props.submitAuth}
          >
            {props.loading ? "Syncing" : props.mode === "login" ? "Initialize" : "Create Account"}
          </button>
        </div>

        <button
          className="mt-6 w-full text-center text-xs text-white/55"
          onClick={() => props.setMode(props.mode === "login" ? "register" : "login")}
        >
          {props.mode === "login" ? "New operator? Create account" : "Existing operator? Sign in"}
        </button>
      </section>
    </main>
  );
}

type CallsignGateProps = {
  callsign: string;
  error: string | null;
  loading: boolean;
  setCallsignValue: (value: string) => void;
  submitCallsign: () => void;
  submitLogout: () => void;
};

function CallsignGate(props: CallsignGateProps) {
  return (
    <main className="flex min-h-screen items-center justify-center px-5 text-white">
      <section className="w-full max-w-xl text-center">
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center border border-operator-purple text-operator-purple shadow-[0_0_24px_rgba(208,0,255,0.55)]">
          <Target size={30} />
        </div>
        <h1 className="operator-glow text-3xl uppercase">Create Character</h1>
        <p className="mt-2 text-sm text-white/55">Choose your callsign before entering the command center.</p>
        <input
          className="mt-8 w-full border border-operator-purple bg-operator-surface px-4 py-5 text-center text-2xl uppercase tracking-[0.25em] outline-none focus:border-operator-cyan"
          maxLength={20}
          placeholder="CALLSIGN"
          value={props.callsign}
          onChange={(event) => props.setCallsignValue(event.target.value)}
        />
        <p className="mt-3 text-xs text-white/45">3-20 characters. Letters, numbers, underscores, or hyphens.</p>
        {props.error && <p className="mt-4 border border-red-500/70 px-3 py-2 text-sm text-red-300">{props.error}</p>}
        <button
          className="mt-8 w-full border border-operator-purple bg-operator-purple/10 px-5 py-4 text-lg uppercase tracking-[0.25em] text-operator-purple shadow-[0_0_20px_rgba(208,0,255,0.45)] disabled:opacity-50"
          disabled={props.loading}
          onClick={props.submitCallsign}
        >
          {props.loading ? "Binding" : "Continue"}
        </button>
        <button className="mt-5 text-xs uppercase tracking-[0.2em] text-white/45" onClick={props.submitLogout}>
          Exit
        </button>
      </section>
    </main>
  );
}

function CyberInput({
  label,
  onChange,
  type = "text",
  value
}: {
  label: string;
  onChange: (value: string) => void;
  type?: string;
  value: string;
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm uppercase tracking-[0.22em] text-operator-purple">{label}</span>
      <input
        className="w-full border border-operator-purple/70 bg-operator-surface px-4 py-4 text-sm outline-none focus:border-operator-cyan"
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}
