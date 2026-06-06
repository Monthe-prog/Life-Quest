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
  Eye,
  EyeOff,
  Globe2,
  Heart,
  Home,
  Info,
  Lock,
  LogOut,
  MessageSquare,
  Minus,
  Plus,
  Search,
  Shield,
  ShieldPlus,
  Sparkles,
  Target,
  Trash2,
  Trophy,
  UserMinus,
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
  compareWeeklyReviews,
  completeCalendarBlock,
  createCalendarBlock,
  deleteWeeklyReview,
  createGoal,
  deleteCalendarBlock,
  discoverGuilds,
  exportWeeklyReviews,
  forgeGuild,
  getCharacterProfile,
  getCalendarWeek,
  getGlobalFeed,
  getGlobalLeaderboard,
  getGuildMessages,
  getGuildOverview,
  getGuildStatus,
  getLatestWeeklyReview,
  getMe,
  getOracleStatus,
  joinGuild,
  interrogateOracle,
  listWeeklyReviewExports,
  listWeeklyReviews,
  listGoals,
  login,
  logout,
  oracleBreakdown,
  hideGuildMessage,
  postGuildMessage,
  register,
  removeGuildMember,
  setCallsign,
  suggestCalendar,
  spawnChildGoal,
  toggleGuildReaction,
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
  type GuildMember,
  type GuildMessage,
  type GuildOverview,
  type GuildStatus,
  type LeaderboardEntry,
  type OracleReply,
  type OracleStatus,
  type ModerationEvent,
  type WeeklyReview,
  type WeeklyReviewCompare,
  type WeeklyReviewExport,
  updateGuildMemberRole,
  updateLeaderboardPrivacy,
  updateCharacterCustomizer
} from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

type View = "HOME" | "GOALS" | "CALENDAR" | "REVIEW" | "CHARACTER" | "GUILD" | "ABOUT";

const navItems: { label: View; icon: typeof Home }[] = [
  { label: "HOME", icon: Home },
  { label: "GOALS", icon: Target },
  { label: "CALENDAR", icon: CalendarDays },
  { label: "REVIEW", icon: BookOpen },
  { label: "CHARACTER", icon: UserRound },
  { label: "GUILD", icon: Shield },
  { label: "ABOUT", icon: Info }
];

const developers = [
  {
    name: "Yann Aymerick Atsa Atsa",
    role: "Scrum Master + Frontend Lead",
    image:
      "https://scontent-los4-1.xx.fbcdn.net/v/t39.30808-1/396287513_312706138148572_7324980911721982528_n.jpg?stp=dst-jpg_s200x200_tt6&_nc_cat=102&ccb=1-7&_nc_sid=e99d92&_nc_eui2=AeFAfrVmq1j4R/dQm_skI1AzcdNuxzUNrDJ1027HNQ2sMnUFLW2-niWjGxxDeNrLYP9aBFnoGFiXgUmsvVYiV1jg2&_nc_ohc=IKH2NfQUMn8Q7kNvwHEp8qG&_nc_oc=AdojM2_nTDgCT2usmlT8tdDEtqw-fOGCJeJmYcSohttVJRJsYw65CxWqh4oaAjJcpJc&_nc_zt=24&_nc_ht=scontent-los4-1.xx&_nc_gid=Rsd7vwUpJVheF6ThRg6njw&_nc_ss=7b2a8&oh=00_Af_oIRnfEIETB-u-jnHwoO2qD4YRJe-8CLH2f_dH2j9LoQ&oe=6A28E533"
  },
  {
    name: "Monthe Joseph Christian",
    role: "Product Owner + Backend Lead",
    image:
      "https://scontent-los4-1.xx.fbcdn.net/v/t39.30808-6/643864765_122277132314033125_3220683603402811466_n.jpg?_nc_cat=109&ccb=1-7&_nc_sid=6ee11a&_nc_eui2=AeECwSHSsJXianuMvYeWNsedNt1O0Qz92GY23U7RDP3YZnGoTKx3ga1FGTMPhaqWvhSfuF0quVd-FEYGGsWW8q10&_nc_ohc=rzgJF8Jc658Q7kNvwHAeWqi&_nc_oc=Adp08Bx4Yhr4rM6siUFlq1kJL8jOzp7xrd2BfnYuDabZ-J5SrUCDc7qd4t4fitrvNmE&_nc_zt=23&_nc_ht=scontent-los4-1.xx&_nc_gid=OZdn7qevPrs8aLSSE12GQQ&_nc_ss=7b2a8&oh=00_Af9EXAwAL1kJ0zRrSllyewmSjrkeHI3hhvGIsVjhUza90Q&oe=6A28E2D5"
  }
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

const OPERATOR_LOGO_SRC = "/operator-logo.png";

type AmbienceMode = "auth" | "app";

function useBackgroundAmbience(mode: AmbienceMode) {
  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const AudioCtor =
      window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioCtor) {
      return;
    }

    let context: AudioContext | null = null;
    let gain: GainNode | null = null;
    let oscillators: OscillatorNode[] = [];
    let timer: number | null = null;
    let stopped = false;

    const stop = () => {
      stopped = true;
      if (timer) {
        window.clearInterval(timer);
      }
      oscillators.forEach((oscillator) => oscillator.stop());
      oscillators = [];
      if (gain && context) {
        gain.gain.cancelScheduledValues(context.currentTime);
        gain.gain.linearRampToValueAtTime(0.0001, context.currentTime + 0.25);
      }
      context?.close().catch(() => undefined);
    };

    const start = async () => {
      if (context || stopped) {
        return;
      }

      context = new AudioCtor();
      await context.resume().catch(() => undefined);
      if (context.state !== "running") {
        return;
      }

      gain = context.createGain();
      gain.gain.setValueAtTime(0.0001, context.currentTime);
      gain.gain.linearRampToValueAtTime(mode === "auth" ? 0.022 : 0.017, context.currentTime + 0.8);
      gain.connect(context.destination);

      const notes = mode === "auth" ? [98, 147, 196] : [130.81, 196, 261.63];
      oscillators = notes.map((frequency, index) => {
        const oscillator = context!.createOscillator();
        const filter = context!.createBiquadFilter();
        oscillator.type = index === 0 ? "sine" : "triangle";
        oscillator.frequency.value = frequency;
        filter.type = "lowpass";
        filter.frequency.value = mode === "auth" ? 420 : 560;
        oscillator.connect(filter);
        filter.connect(gain!);
        oscillator.start();
        return oscillator;
      });

      timer = window.setInterval(() => {
        if (!context || !gain) {
          return;
        }
        const now = context.currentTime;
        const accent = context.createOscillator();
        const accentGain = context.createGain();
        accent.type = "sine";
        accent.frequency.value = mode === "auth" ? 294 : 392;
        accentGain.gain.setValueAtTime(0.0001, now);
        accentGain.gain.linearRampToValueAtTime(mode === "auth" ? 0.016 : 0.012, now + 0.06);
        accentGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.7);
        accent.connect(accentGain);
        accentGain.connect(gain);
        accent.start(now);
        accent.stop(now + 0.75);
      }, mode === "auth" ? 4200 : 5200);
    };

    const unlock = () => {
      start().catch(() => undefined);
    };

    window.addEventListener("pointerdown", unlock, { once: true });
    window.addEventListener("keydown", unlock, { once: true });
    void start();

    return () => {
      window.removeEventListener("pointerdown", unlock);
      window.removeEventListener("keydown", unlock);
      stop();
    };
  }, [mode]);
}

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
  const [confirmPassword, setConfirmPassword] = useState("");
  const [callsign, setCallsignValue] = useState("");
  const [activeView, setActiveView] = useState<View>("HOME");
  const [battleEvent, setBattleEvent] = useState<BattleEvent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const playSound = useRetroSound();
  useBackgroundAmbience(!accessToken || !user ? "auth" : "app");

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
      if (mode === "register" && password !== confirmPassword) {
        throw new Error("Passwords do not match");
      }
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
        confirmPassword={confirmPassword}
        setEmail={setEmail}
        setMode={setMode}
        setPassword={setPassword}
        setConfirmPassword={setConfirmPassword}
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
          <div className="flex items-center gap-4">
            <OperatorLogo className="h-16 w-16 shrink-0" />
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-white/55">System Online</p>
              <h1 className="operator-glow mt-2 text-4xl uppercase leading-none text-white">{callsign}</h1>
            </div>
          </div>
          <button className="border border-white/25 p-3 text-white/55" onClick={submitLogout} title="Logout">
            <LogOut size={22} />
          </button>
        </header>

        {activeView === "HOME" && <HomeView accessToken={accessToken} battleEvent={battleEvent} callsign={callsign} playSound={playSound} />}
        {activeView === "GOALS" && <GoalsMatrix accessToken={accessToken} onBattleEvent={setBattleEvent} playSound={playSound} />}
        {activeView === "CALENDAR" && <CalendarView accessToken={accessToken} />}
        {activeView === "REVIEW" && <WeeklyReviewView accessToken={accessToken} playSound={playSound} />}
        {activeView === "CHARACTER" && <CharacterView accessToken={accessToken} battleEvent={battleEvent} playSound={playSound} />}
        {activeView === "GUILD" && <GuildView accessToken={accessToken} playSound={playSound} />}
        {activeView === "ABOUT" && <AboutView />}
      </section>

      <nav className="fixed inset-x-0 bottom-0 border-t border-operator-purple/65 bg-[#08080b]/95">
        <div className="mx-auto grid max-w-3xl grid-cols-7">
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

function AboutView() {
  return (
    <section className="space-y-5">
      <div className="operator-panel p-5">
        <p className="text-xs uppercase tracking-[0.28em] text-operator-cyan">Project Team</p>
        <h2 className="operator-glow mt-2 text-3xl uppercase">About OPERATOR</h2>
        <p className="mt-3 text-sm leading-6 text-white/65">
          OPERATOR / Life Quest was designed as an AI-assisted gamified life-management platform for the Software Architecture project.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {developers.map((developer) => (
          <article className="border border-operator-purple/70 bg-operator-surface p-5" key={developer.name}>
            <div className="flex items-center gap-4">
              <div className="relative h-24 w-24 shrink-0 overflow-hidden border border-operator-cyan bg-black">
                <img
                  alt={developer.name}
                  className="h-full w-full object-cover"
                  referrerPolicy="no-referrer"
                  src={developer.image}
                />
              </div>
              <div className="min-w-0">
                <h3 className="operator-glow break-words text-xl uppercase leading-tight">{developer.name}</h3>
                <p className="mt-2 text-xs uppercase tracking-[0.18em] text-operator-cyan">{developer.role}</p>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function currentSunday() {
  const today = new Date();
  const day = today.getDay();
  const delta = day === 0 ? 0 : 7 - day;
  const sunday = new Date(today);
  sunday.setDate(today.getDate() + delta);
  return sunday.toISOString().slice(0, 10);
}

function emptyReview(): Omit<WeeklyReview, "id" | "locked" | "updated_at" | "summary"> {
  return {
    week_ending: currentSunday(),
    wins: "",
    friction: "",
    alignment: "",
    directive: "",
    completion_rate: 0,
    xp_gained: 0,
    streak: 0
  };
}

function WeeklyReviewView({
  accessToken,
  playSound
}: {
  accessToken: string;
  playSound: (kind?: "select" | "confirm" | "error") => void;
}) {
  const [draft, setDraft] = useState(emptyReview);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [locked, setLocked] = useState(false);
  const [editMode, setEditMode] = useState(true);
  const [dirty, setDirty] = useState(false);
  const [archive, setArchive] = useState<WeeklyReview[]>([]);
  const [exports, setExports] = useState<WeeklyReviewExport[]>([]);
  const [sections, setSections] = useState(["wins", "friction", "alignment", "directive", "metrics"]);
  const [selectedArchiveIds, setSelectedArchiveIds] = useState<string[]>([]);
  const [compareResult, setCompareResult] = useState<WeeklyReviewCompare | null>(null);
  const [statusText, setStatusText] = useState("Loading review channel...");

  async function refreshReviews() {
    const [latest, reviews, exportRows] = await Promise.all([
      getLatestWeeklyReview(accessToken),
      listWeeklyReviews(accessToken),
      listWeeklyReviewExports(accessToken)
    ]);
    setArchive(reviews);
    setExports(exportRows);
    if (latest) {
      setActiveId(latest.id);
      setDraft({
        week_ending: latest.week_ending,
        wins: latest.wins,
        friction: latest.friction,
        alignment: latest.alignment,
        directive: latest.directive,
        completion_rate: latest.completion_rate,
        xp_gained: latest.xp_gained,
        streak: latest.streak
      });
      setLocked(latest.locked);
      setEditMode(!latest.locked);
    }
    setDirty(false);
    setStatusText(latest ? "Saved" : "No saved ceremony yet");
  }

  useEffect(() => {
    refreshReviews().catch(() => setStatusText("Review archive unavailable"));
  }, [accessToken]);

  function updateDraft(field: keyof typeof draft, value: string | number) {
    setDraft((current) => ({ ...current, [field]: value }));
    setDirty(true);
    setStatusText("Unsaved changes");
  }

  async function save(lock: boolean) {
    try {
      playSound("confirm");
      const saved = await saveWeeklyReview(accessToken, { ...draft, lock });
      setActiveId(saved.id);
      setLocked(saved.locked);
      setDirty(false);
      setEditMode(!saved.locked);
      setStatusText(lock ? "Locked and saved" : "Saved");
      await refreshReviews();
    } catch (err) {
      playSound("error");
      setStatusText(err instanceof Error ? err.message : "Save failed");
    }
  }

  async function removeReview(reviewId: string) {
    try {
      await deleteWeeklyReview(accessToken, reviewId);
      setActiveId(null);
      setDraft(emptyReview());
      setLocked(false);
      setEditMode(true);
      setDirty(false);
      await refreshReviews();
      setStatusText("Ceremony deleted");
    } catch (err) {
      setStatusText(err instanceof Error ? err.message : "Delete failed");
    }
  }

  async function exportCurrent() {
    const reviewIds = selectedArchiveIds.length > 0 ? selectedArchiveIds : activeId ? [activeId] : [];
    if (reviewIds.length === 0) {
      setStatusText("Save the ceremony before exporting");
      return;
    }
    try {
      const result = await exportWeeklyReviews(accessToken, reviewIds, sections);
      setExports((current) => [result, ...current]);
      setStatusText(`Export registered: ${result.filename}`);
    } catch (err) {
      setStatusText(err instanceof Error ? err.message : "Export failed");
    }
  }

  async function compareSelected() {
    if (selectedArchiveIds.length !== 2) {
      setStatusText("Select exactly two ceremonies to compare");
      return;
    }
    try {
      const result = await compareWeeklyReviews(accessToken, selectedArchiveIds[0], selectedArchiveIds[1]);
      setCompareResult(result);
      setStatusText("Comparison loaded");
    } catch (err) {
      setStatusText(err instanceof Error ? err.message : "Compare failed");
    }
  }

  function loadReview(review: WeeklyReview) {
    setActiveId(review.id);
    setDraft({
      week_ending: review.week_ending,
      wins: review.wins,
      friction: review.friction,
      alignment: review.alignment,
      directive: review.directive,
      completion_rate: review.completion_rate,
      xp_gained: review.xp_gained,
      streak: review.streak
    });
    setLocked(review.locked);
    setEditMode(!review.locked);
    setDirty(false);
    setStatusText("Saved");
  }

  const fields: Array<[keyof typeof draft, string, "textarea" | "number" | "date"]> = [
    ["week_ending", "Week ending Sunday", "date"],
    ["wins", "Wins", "textarea"],
    ["friction", "Friction", "textarea"],
    ["alignment", "Alignment check", "textarea"],
    ["directive", "Oracle directive", "textarea"],
    ["completion_rate", "Completion rate", "number"],
    ["xp_gained", "XP gained", "number"],
    ["streak", "Streak", "number"]
  ];

  return (
    <section className="flex flex-col gap-5">
      <div className="border border-operator-purple/70 bg-operator-surface p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="operator-glow text-3xl uppercase">Weekly Review</h2>
            <p className="mt-1 text-xs uppercase tracking-[0.2em] text-white/50">{statusText}</p>
          </div>
          <div className="flex gap-2">
            <button className="border border-operator-cyan px-3 py-2 text-xs uppercase text-operator-cyan" onClick={() => setEditMode((value) => !value)}>
              {editMode ? "View mode" : "Edit mode"}
            </button>
            <button className="border border-operator-purple px-3 py-2 text-xs uppercase text-operator-purple" onClick={() => save(false)}>
              Save
            </button>
            <button className="border border-operator-cyan bg-operator-cyan/10 px-3 py-2 text-xs uppercase text-operator-cyan" onClick={() => save(true)}>
              Lock
            </button>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-3 text-xs uppercase">
          <span className={dirty ? "text-yellow-300" : "text-operator-cyan"}>{dirty ? "Unsaved changes" : "Saved"}</span>
          <span className={locked ? "text-operator-purple" : "text-white/45"}>{locked ? "Directive locked" : "Unlocked"}</span>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {fields.map(([field, label, kind]) => (
          <label className="flex flex-col gap-2 border border-operator-purple/45 bg-operator-surface p-4" key={field}>
            <span className="text-xs uppercase tracking-[0.2em] text-operator-purple">{label}</span>
            {kind === "textarea" ? (
              <textarea
                className="min-h-28 resize-y border border-white/10 bg-black/40 p-3 text-sm outline-none focus:border-operator-cyan disabled:text-white/45"
                disabled={!editMode}
                value={String(draft[field])}
                onChange={(event) => updateDraft(field, event.target.value)}
              />
            ) : (
              <input
                className="border border-white/10 bg-black/40 p-3 text-sm outline-none focus:border-operator-cyan disabled:text-white/45"
                disabled={!editMode}
                type={kind}
                value={draft[field]}
                onChange={(event) => updateDraft(field, kind === "number" ? Number(event.target.value) : event.target.value)}
              />
            )}
          </label>
        ))}
      </div>

      {activeId && (
        <section className="operator-cyan-panel p-4">
          <h3 className="text-sm uppercase tracking-[0.3em] text-operator-cyan">Oracle Summary</h3>
          <p className="mt-3 text-sm leading-6 text-white/70">
            {archive.find((review) => review.id === activeId)?.summary || "Save or lock this ceremony to generate a weekly summary."}
          </p>
        </section>
      )}

      <div className="border border-operator-cyan/60 bg-operator-surface p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="operator-glow text-xl uppercase">Export Settings</h3>
          <button className="border border-operator-cyan px-3 py-2 text-xs uppercase text-operator-cyan" onClick={exportCurrent}>
            Export PDF{selectedArchiveIds.length > 1 ? ` x${selectedArchiveIds.length}` : ""}
          </button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {["wins", "friction", "alignment", "directive", "metrics"].map((section) => (
            <button
              className={`border px-3 py-2 text-xs uppercase ${
                sections.includes(section) ? "border-operator-cyan text-operator-cyan" : "border-white/15 text-white/45"
              }`}
              key={section}
              onClick={() =>
                setSections((current) => (current.includes(section) ? current.filter((item) => item !== section) : [...current, section]))
              }
            >
              {section}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="border border-operator-purple/60 bg-operator-surface p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="operator-glow text-xl uppercase">Review Archive</h3>
            <button className="border border-operator-cyan px-3 py-2 text-xs uppercase text-operator-cyan" onClick={compareSelected}>
              Compare
            </button>
          </div>
          <div className="mt-3 flex max-h-72 flex-col gap-2 overflow-y-auto">
            {archive.map((review) => (
              <div className="flex items-center justify-between border border-white/10 p-3" key={review.id}>
                <div className="flex min-w-0 items-center gap-3">
                  <input
                    checked={selectedArchiveIds.includes(review.id)}
                    className="h-4 w-4 accent-cyan-300"
                    type="checkbox"
                    onChange={(event) =>
                      setSelectedArchiveIds((current) =>
                        event.target.checked ? [...current, review.id].slice(-2) : current.filter((id) => id !== review.id)
                      )
                    }
                  />
                  <button className="min-w-0 text-left text-sm uppercase text-white" onClick={() => loadReview(review)}>
                    {review.week_ending} / {review.completion_rate}%
                  </button>
                </div>
                <button className="shrink-0 text-red-300" onClick={() => removeReview(review.id)} title="Delete review">
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
            {archive.length === 0 && <p className="text-sm text-white/45">No saved ceremonies yet.</p>}
          </div>
          {compareResult && (
            <div className="mt-4 grid gap-2 text-xs uppercase sm:grid-cols-3">
              <StatTile label="Completion Delta" value={`${compareResult.completion_rate_delta > 0 ? "+" : ""}${compareResult.completion_rate_delta}%`} />
              <StatTile label="XP Delta" value={`${compareResult.xp_gained_delta > 0 ? "+" : ""}${compareResult.xp_gained_delta}`} />
              <StatTile label="Streak Delta" value={`${compareResult.streak_delta > 0 ? "+" : ""}${compareResult.streak_delta}`} />
            </div>
          )}
        </div>
        <div className="border border-operator-cyan/60 bg-operator-surface p-4">
          <h3 className="operator-glow text-xl uppercase">Export History</h3>
          <div className="mt-3 flex max-h-72 flex-col gap-2 overflow-y-auto">
            {exports.map((row) => (
              <div className="border border-white/10 p-3 text-sm" key={row.id}>
                <p className="text-operator-cyan">{row.filename}</p>
                <p className="text-xs text-white/45">{new Date(row.created_at).toLocaleString()}</p>
              </div>
            ))}
            {exports.length === 0 && <p className="text-sm text-white/45">No PDF exports registered.</p>}
          </div>
        </div>
      </div>
    </section>
  );
}

function CalendarView({ accessToken }: { accessToken: string }) {
  const [blocks, setBlocks] = useState<CalendarBlock[]>([]);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [title, setTitle] = useState("");
  const [day, setDay] = useState(0);
  const [startHour, setStartHour] = useState(7);
  const [endHour, setEndHour] = useState(8);
  const [selectedGoalId, setSelectedGoalId] = useState("");
  const [selectedBlock, setSelectedBlock] = useState<CalendarBlock | null>(null);
  const [dragPayload, setDragPayload] = useState<string | null>(null);
  const [editBlockId, setEditBlockId] = useState<string | null>(null);
  const [isRecurring, setIsRecurring] = useState(false);
  const [alignmentStatus, setAlignmentStatus] = useState("unknown");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refreshBlocks() {
    const [calendarResponse, goalResponse] = await Promise.all([getCalendarWeek(accessToken), listGoals(accessToken)]);
    setBlocks(calendarResponse.blocks);
    setGoals(goalResponse.goals.filter((goal) => !goal.is_complete));
  }

  useEffect(() => {
    refreshBlocks().catch((err) => setError(err instanceof Error ? err.message : "Unable to load calendar"));
  }, [accessToken]);

  function resetBlockForm() {
    setTitle("");
    setEditBlockId(null);
    setIsRecurring(false);
    setAlignmentStatus("unknown");
    setSelectedGoalId("");
  }

  function loadBlockForEdit(block: CalendarBlock) {
    setEditBlockId(block.id);
    setTitle(block.title);
    setDay(block.day_of_week);
    setStartHour(block.start_hour);
    setEndHour(block.end_hour);
    setIsRecurring(block.is_recurring);
    setAlignmentStatus(block.alignment_status);
    setSelectedGoalId(block.goal_id ?? "");
    setSelectedBlock(block);
  }

  async function addBlock() {
    if (!title.trim()) {
      return;
    }

    setBusy(true);
    setError(null);
    try {
      const payload = {
        title: title.trim(),
        day_of_week: day,
        start_hour: startHour,
        end_hour: Math.max(endHour, startHour + 1),
        is_recurring: isRecurring,
        recurrence_pattern: isRecurring ? "weekly" : null,
        alignment_status: alignmentStatus,
        goal_id: selectedGoalId || null
      };
      if (editBlockId) {
        await updateCalendarBlock(accessToken, editBlockId, payload);
      } else {
        await createCalendarBlock(accessToken, payload);
      }
      resetBlockForm();
      await refreshBlocks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Block save failed");
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

  async function toggleComplete(block: CalendarBlock) {
    setBusy(true);
    setError(null);
    try {
      await completeCalendarBlock(accessToken, block.id);
      await refreshBlocks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Block completion failed");
    } finally {
      setBusy(false);
    }
  }

  function blocksFor(dayIndex: number, hour: number) {
    return blocks.filter((block) => block.day_of_week === dayIndex && block.start_hour <= hour && block.end_hour > hour);
  }

  const goalById = useMemo(() => new Map(goals.map((goal) => [goal.id, goal])), [goals]);
  const daySummaries = useMemo(
    () =>
      weekDays.map((_, dayIndex) => {
        const scheduled = blocks
          .filter((block) => block.day_of_week === dayIndex)
          .reduce((total, block) => total + Math.max(0, block.end_hour - block.start_hour), 0);
        const bufferPercent = Math.max(0, Math.round(((15 - scheduled) / 15) * 100));
        return { scheduled, bufferPercent, warning: bufferPercent < 20 };
      }),
    [blocks]
  );
  const alignedCount = blocks.filter((block) => block.alignment_status === "aligned").length;
  const misalignedCount = blocks.filter((block) => block.alignment_status === "misaligned").length;
  const isSunday = new Date().getDay() === 0;

  async function placeDrag(dayIndex: number, hour: number) {
    if (!dragPayload) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      if (dragPayload.startsWith("goal:")) {
        const goalId = dragPayload.replace("goal:", "");
        const goal = goalById.get(goalId);
        if (goal) {
          await createCalendarBlock(accessToken, {
            title: goal.title,
            day_of_week: dayIndex,
            start_hour: hour,
            end_hour: hour + 1,
            goal_id: goal.id,
            alignment_status: goal.priority > 0 ? "aligned" : "unknown"
          });
        }
      } else if (dragPayload.startsWith("block:")) {
        const blockId = dragPayload.replace("block:", "");
        const block = blocks.find((item) => item.id === blockId);
        if (block) {
          const duration = Math.max(1, block.end_hour - block.start_hour);
          await updateCalendarBlock(accessToken, block.id, {
            day_of_week: dayIndex,
            start_hour: hour,
            end_hour: Math.min(22, hour + duration)
          });
        }
      }
      await refreshBlocks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Drag placement failed");
    } finally {
      setBusy(false);
      setDragPayload(null);
    }
  }

  function blockTone(block: CalendarBlock) {
    const linkedGoal = block.goal_id ? goalById.get(block.goal_id) : null;
    if (block.alignment_status === "misaligned") {
      return "border-red-400/70 bg-red-950/30 text-red-200";
    }
    if (linkedGoal?.priority || block.alignment_status === "aligned" || block.source === "oracle_suggested") {
      return "border-operator-cyan bg-operator-cyan/10 text-operator-cyan";
    }
    return "border-white/20 bg-white/5 text-white/60";
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
      {isSunday && (
        <p className="operator-cyan-panel p-3 text-sm text-operator-cyan">
          Sunday planning mode is active. Load your weekly goals, place priority blocks, then lock the directive in Weekly Review.
        </p>
      )}

      <section className="grid gap-3 md:grid-cols-7">
        {weekDays.map((label, index) => (
          <article className={`border p-3 text-center ${daySummaries[index].warning ? "border-red-400/70 bg-red-950/20" : "border-white/10 bg-black/25"}`} key={label}>
            <p className="text-xs uppercase text-white/50">{label}</p>
            <p className={daySummaries[index].warning ? "text-lg text-red-300" : "text-lg text-operator-cyan"}>
              {daySummaries[index].bufferPercent}% buffer
            </p>
          </article>
        ))}
      </section>

      <section className="operator-cyan-panel p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-sm uppercase tracking-[0.3em] text-operator-cyan">Goal Alignment</h3>
          <p className="text-xs uppercase text-white/45">
            {alignedCount} aligned / {misalignedCount} misaligned
          </p>
        </div>
        <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
          {goals.slice(0, 12).map((goal) => (
            <button
              className={`min-w-52 border px-3 py-2 text-left text-xs uppercase ${
                goal.priority > 0 ? "border-operator-cyan bg-operator-cyan/10 text-operator-cyan" : "border-white/15 bg-black/30 text-white/55"
              }`}
              draggable
              key={goal.id}
              onDragStart={() => setDragPayload(`goal:${goal.id}`)}
              onClick={() => {
                setTitle(goal.title);
                setSelectedGoalId(goal.id);
                setAlignmentStatus(goal.priority > 0 ? "aligned" : "unknown");
              }}
            >
              {goal.title}
              <span className="mt-1 block text-[10px] text-white/40">{goal.horizon.replaceAll("_", " ")} / priority {goal.priority}</span>
            </button>
          ))}
          {goals.length === 0 && <p className="text-sm text-white/45">No active goals available for scheduling.</p>}
        </div>
      </section>

      <section className="operator-panel p-4">
        <div className="grid gap-2 md:grid-cols-[1fr_150px_110px_100px_100px_120px_100px_44px]">
          <input
            className="min-w-0 border border-operator-purple/50 bg-black/40 px-3 py-3 text-sm outline-none focus:border-operator-cyan"
            placeholder="Manual block title..."
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
          <select
            className="min-w-0 border border-operator-purple/50 bg-black/40 px-3 py-3 text-sm outline-none focus:border-operator-cyan"
            value={selectedGoalId}
            onChange={(event) => setSelectedGoalId(event.target.value)}
          >
            <option className="bg-black" value="">
              No goal link
            </option>
            {goals.map((goal) => (
              <option className="bg-black" key={goal.id} value={goal.id}>
                {goal.title}
              </option>
            ))}
          </select>
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
          <select
            className="border border-operator-purple/50 bg-black/40 px-3 py-3 text-sm outline-none focus:border-operator-cyan"
            value={alignmentStatus}
            onChange={(event) => setAlignmentStatus(event.target.value)}
          >
            {["unknown", "aligned", "misaligned"].map((value) => (
              <option className="bg-black" key={value} value={value}>
                {value.toUpperCase()}
              </option>
            ))}
          </select>
          <button
            className={`border px-3 py-3 text-xs uppercase ${isRecurring ? "border-operator-cyan text-operator-cyan" : "border-white/15 text-white/45"}`}
            onClick={() => setIsRecurring((value) => !value)}
            type="button"
          >
            Habit
          </button>
          <button
            className="flex items-center justify-center border border-operator-purple text-operator-purple disabled:opacity-40"
            disabled={busy}
            onClick={addBlock}
            title={editBlockId ? "Save block" : "Add manual block"}
          >
            {editBlockId ? <Zap size={18} /> : <Plus size={18} />}
          </button>
        </div>
        {editBlockId && (
          <button className="mt-3 text-xs uppercase text-white/45" onClick={resetBlockForm}>
            Cancel edit
          </button>
        )}
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
                    <div
                      className="mb-1 flex min-h-8 items-center justify-center border border-dashed border-white/10 text-[10px] uppercase text-white/25"
                      onDragOver={(event) => event.preventDefault()}
                      onDrop={() => placeDrag(dayIndex, hour)}
                    >
                      Drop
                    </div>
                    {cellBlocks.map((block) => (
                      <div
                        className={`mb-1 border px-2 py-2 text-[11px] ${blockTone(block)}`}
                        draggable
                        key={block.id}
                        onDragStart={() => setDragPayload(`block:${block.id}`)}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <button className="min-w-0 break-words text-left uppercase leading-4" onClick={() => loadBlockForEdit(block)}>
                            {block.completed ? "[DONE] " : ""}
                            {block.title}
                          </button>
                          <div className="flex shrink-0 gap-1">
                            <button className="text-operator-cyan" disabled={busy} onClick={() => toggleComplete(block)} title="Toggle complete">
                              <Award size={12} />
                            </button>
                            <button className="text-white/45" disabled={busy} onClick={() => removeBlock(block)} title="Delete block">
                              <Trash2 size={12} />
                            </button>
                          </div>
                        </div>
                        <div className="mt-1 flex items-center gap-1 text-[10px] text-white/45">
                          <Clock size={10} />
                          {formatHour(block.start_hour)}-{formatHour(block.end_hour)}
                          {block.is_recurring && <span>/ HABIT</span>}
                          <span>/ {block.alignment_status}</span>
                          {block.goal_id && <span>/ goal linked</span>}
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

      {selectedBlock && (
        <section className="operator-cyan-panel p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-sm uppercase tracking-[0.3em] text-operator-cyan">Block Detail</h3>
              <p className="mt-2 text-lg uppercase text-white">{selectedBlock.title}</p>
              <p className="mt-1 text-sm text-white/50">
                {weekDays[selectedBlock.day_of_week]} / {formatHour(selectedBlock.start_hour)}-{formatHour(selectedBlock.end_hour)}
              </p>
              <p className="mt-2 text-sm text-white/60">
                Serves: {selectedBlock.goal_id ? goalById.get(selectedBlock.goal_id)?.title ?? "Archived goal source" : "No linked goal source"}
              </p>
            </div>
            <button className="text-white/45" onClick={() => setSelectedBlock(null)} title="Close detail">
              <X size={18} />
            </button>
          </div>
        </section>
      )}
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
  const [activeTab, setActiveTab] = useState<"MY GUILD" | "CHAT" | "GLOBAL">("MY GUILD");
  const [status, setStatus] = useState<GuildStatus | null>(null);
  const [overview, setOverview] = useState<GuildOverview | null>(null);
  const [guilds, setGuilds] = useState<Guild[]>([]);
  const [feed, setFeed] = useState<FeedEvent[]>([]);
  const [messages, setMessages] = useState<GuildMessage[]>([]);
  const [globalLeaderboard, setGlobalLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [modal, setModal] = useState<"forge" | "join" | null>(null);
  const [guildName, setGuildName] = useState("");
  const [motto, setMotto] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [chatInput, setChatInput] = useState("");
  const [taskRef, setTaskRef] = useState("");
  const [messageSearch, setMessageSearch] = useState("");
  const [memberFilter, setMemberFilter] = useState("");
  const [reactionFilter, setReactionFilter] = useState("");
  const [globalMetric, setGlobalMetric] = useState<"total_xp" | "streak" | "stat">("total_xp");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refreshGuild() {
    const [nextStatus, nextGuilds, nextFeed, nextGlobalLeaderboard] = await Promise.all([
      getGuildStatus(accessToken),
      discoverGuilds(accessToken),
      getGlobalFeed(accessToken),
      getGlobalLeaderboard(accessToken, globalMetric, globalMetric === "stat" ? "intellect" : undefined)
    ]);
    setStatus(nextStatus);
    setGuilds(nextGuilds);
    setFeed(nextFeed);
    setGlobalLeaderboard(nextGlobalLeaderboard);
    if (nextStatus.aligned) {
      const [nextOverview, nextMessages] = await Promise.all([
        getGuildOverview(accessToken),
        getGuildMessages(accessToken, {
          search: messageSearch,
          member_id: memberFilter,
          reaction: reactionFilter
        })
      ]);
      setOverview(nextOverview);
      setMessages(nextMessages);
    } else {
      setOverview(null);
      setMessages([]);
    }
  }

  useEffect(() => {
    refreshGuild().catch((err) => setError(err instanceof Error ? err.message : "Unable to load guild data"));
  }, [accessToken, globalMetric, memberFilter, messageSearch, reactionFilter]);

  useEffect(() => {
    const wsBase =
      process.env.NEXT_PUBLIC_WS_BASE_URL ||
      (typeof window !== "undefined"
        ? `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.hostname}:8000`
        : "ws://localhost:8000");
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

  const myRole = overview?.guild.role ?? status?.guild?.role ?? "member";
  const canModerate = myRole === "owner" || myRole === "moderator";
  const canOwn = myRole === "owner";

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

  async function sendMessage() {
    if (!chatInput.trim()) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      playSound("confirm");
      await postGuildMessage(accessToken, { body: chatInput.trim(), task_ref: taskRef.trim() || undefined });
      setChatInput("");
      setTaskRef("");
      setMessages(await getGuildMessages(accessToken, { search: messageSearch, member_id: memberFilter, reaction: reactionFilter }));
    } catch (err) {
      playSound("error");
      setError(err instanceof Error ? err.message : "Message send failed");
    } finally {
      setBusy(false);
    }
  }

  async function reactToMessage(message: GuildMessage, emoji: string) {
    try {
      playSound("select");
      const updated = await toggleGuildReaction(accessToken, message.id, emoji);
      setMessages((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (err) {
      playSound("error");
      setError(err instanceof Error ? err.message : "Reaction rate limit active");
    }
  }

  async function moderateMessage(message: GuildMessage) {
    setBusy(true);
    setError(null);
    try {
      await hideGuildMessage(accessToken, message.id);
      setMessages((current) => current.filter((item) => item.id !== message.id));
      setOverview(await getGuildOverview(accessToken));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Message moderation failed");
    } finally {
      setBusy(false);
    }
  }

  async function changeRole(member: GuildMember, role: "moderator" | "member") {
    setBusy(true);
    setError(null);
    try {
      playSound("confirm");
      setOverview(await updateGuildMemberRole(accessToken, member.user_id, role));
    } catch (err) {
      playSound("error");
      setError(err instanceof Error ? err.message : "Role update failed");
    } finally {
      setBusy(false);
    }
  }

  async function kickMember(member: GuildMember) {
    setBusy(true);
    setError(null);
    try {
      playSound("confirm");
      setOverview(await removeGuildMember(accessToken, member.user_id));
    } catch (err) {
      playSound("error");
      setError(err instanceof Error ? err.message : "Member removal failed");
    } finally {
      setBusy(false);
    }
  }

  async function togglePrivacy(enabled: boolean) {
    await updateLeaderboardPrivacy(accessToken, enabled).catch((err) => setError(err instanceof Error ? err.message : "Privacy update failed"));
    await refreshGuild().catch(() => undefined);
  }

  return (
    <section className="space-y-5">
      <div>
        <h2 className="operator-glow text-3xl uppercase">Guild</h2>
        <p className="mt-2 text-xs uppercase tracking-[0.22em] text-white/45">Accountability collective</p>
      </div>

      {error && <p className="border border-red-500/70 px-3 py-2 text-sm text-red-300">{error}</p>}

      <div className="grid grid-cols-3 border border-white/10 bg-black/40">
        {(["MY GUILD", "CHAT", "GLOBAL"] as const).map((tab) => (
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
            {tab === "CHAT" && <MessageSquare size={15} />}
            {tab === "GLOBAL" && <Globe2 size={15} />}
            {tab}
          </button>
        ))}
      </div>

      {activeTab === "MY GUILD" && (
        <section className="operator-panel p-5">
          {status?.aligned && status.guild ? (
            <GuildDashboard
              canModerate={canModerate}
              canOwn={canOwn}
              guild={overview?.guild ?? status.guild}
              members={overview?.members ?? []}
              moderationFeed={overview?.moderation_feed ?? []}
              leaderboard={overview?.leaderboard ?? []}
              busy={busy}
              onKick={kickMember}
              onPrivacyToggle={togglePrivacy}
              onRoleChange={changeRole}
            />
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

      {activeTab === "CHAT" && (
        status?.aligned ? (
          <GuildChat
            busy={busy}
            canModerate={canModerate}
            chatInput={chatInput}
            members={overview?.members ?? []}
            memberFilter={memberFilter}
            messageSearch={messageSearch}
            messages={messages}
            reactionFilter={reactionFilter}
            setChatInput={setChatInput}
            setMemberFilter={setMemberFilter}
            setMessageSearch={setMessageSearch}
            setReactionFilter={setReactionFilter}
            setTaskRef={setTaskRef}
            taskRef={taskRef}
            onHide={moderateMessage}
            onReact={reactToMessage}
            onSend={sendMessage}
          />
        ) : (
          <section className="operator-panel p-5 text-sm text-white/45">Join a guild to open chat.</section>
        )
      )}

      {activeTab === "GLOBAL" && (
        <GlobalSocial
          feed={feed}
          guilds={guilds}
          leaderboard={globalLeaderboard}
          metric={globalMetric}
          setMetric={setGlobalMetric}
        />
      )}

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

function GuildDashboard({
  busy,
  canModerate,
  canOwn,
  guild,
  leaderboard,
  members,
  moderationFeed,
  onKick,
  onPrivacyToggle,
  onRoleChange
}: {
  busy: boolean;
  canModerate: boolean;
  canOwn: boolean;
  guild: Guild;
  leaderboard: LeaderboardEntry[];
  members: GuildMember[];
  moderationFeed: ModerationEvent[];
  onKick: (member: GuildMember) => void;
  onPrivacyToggle: (enabled: boolean) => void;
  onRoleChange: (member: GuildMember, role: "moderator" | "member") => void;
}) {
  const self = members.find((member) => member.is_current_user);
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h3 className="operator-glow text-2xl uppercase">{guild.name}</h3>
          <p className="mt-2 text-sm text-white/55">{guild.motto || "No motto encoded."}</p>
        </div>
        <span className="border border-operator-cyan px-3 py-2 text-xs uppercase text-operator-cyan">{guild.role}</span>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <StatTile label="Members" value={`${guild.member_count}/10`} />
        <StatTile label="Guild XP" value={guild.guild_xp.toLocaleString()} />
        <StatTile label="Invite" value={guild.invite_code ?? "PRIVATE"} />
      </div>

      {self && (
        <label className="flex items-center justify-between gap-4 border border-white/10 bg-black/30 p-3 text-sm text-white/60">
          <span>Anonymous global leaderboard display</span>
          <input
            checked={self.anonymous_on_leaderboard}
            className="h-5 w-5 accent-cyan-300"
            type="checkbox"
            onChange={(event) => onPrivacyToggle(event.target.checked)}
          />
        </label>
      )}

      <section>
        <h4 className="mb-3 text-xs uppercase tracking-[0.25em] text-operator-cyan">Guild Leaderboard</h4>
        <div className="space-y-2">
          {leaderboard.map((entry) => (
            <article className="grid grid-cols-[40px_1fr_auto] items-center gap-3 border border-white/10 bg-black/25 p-3" key={entry.user_id}>
              <span className="text-lg text-operator-purple">#{entry.rank}</span>
              <div>
                <p className="text-sm uppercase text-white">{entry.display_name}</p>
                <p className="text-xs text-white/45">Weekly reset score: {entry.weekly_xp} XP</p>
              </div>
              <span className="text-sm text-operator-cyan">{entry.xp} XP</span>
            </article>
          ))}
        </div>
      </section>

      <section>
        <h4 className="mb-3 text-xs uppercase tracking-[0.25em] text-operator-cyan">Roster</h4>
        <div className="space-y-2">
          {members.map((member) => (
            <article className="border border-white/10 bg-black/25 p-3" key={member.user_id}>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm uppercase text-white">{member.callsign}</p>
                  <p className="text-xs uppercase text-white/45">
                    {member.role} / Level {member.level} / {member.completion_rate}% completion
                  </p>
                </div>
                <div className="flex gap-2">
                  {canOwn && member.role !== "owner" && (
                    <button
                      className="border border-operator-cyan px-2 py-1 text-xs uppercase text-operator-cyan disabled:opacity-40"
                      disabled={busy}
                      onClick={() => onRoleChange(member, member.role === "moderator" ? "member" : "moderator")}
                    >
                      {member.role === "moderator" ? "Demote" : "Mod"}
                    </button>
                  )}
                  {canModerate && member.role !== "owner" && (
                    <button
                      className="border border-red-400/70 px-2 py-1 text-red-300 disabled:opacity-40"
                      disabled={busy}
                      title="Remove member"
                      onClick={() => onKick(member)}
                    >
                      <UserMinus size={15} />
                    </button>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>

      <ModerationFeed events={moderationFeed} />
    </div>
  );
}

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <article className="border border-white/10 bg-black/30 p-3 text-center">
      <p className="text-lg uppercase text-operator-cyan">{value}</p>
      <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-white/45">{label}</p>
    </article>
  );
}

function GuildChat({
  busy,
  canModerate,
  chatInput,
  memberFilter,
  members,
  messageSearch,
  messages,
  reactionFilter,
  setChatInput,
  setMemberFilter,
  setMessageSearch,
  setReactionFilter,
  setTaskRef,
  taskRef,
  onHide,
  onReact,
  onSend
}: {
  busy: boolean;
  canModerate: boolean;
  chatInput: string;
  memberFilter: string;
  members: GuildMember[];
  messageSearch: string;
  messages: GuildMessage[];
  reactionFilter: string;
  setChatInput: (value: string) => void;
  setMemberFilter: (value: string) => void;
  setMessageSearch: (value: string) => void;
  setReactionFilter: (value: string) => void;
  setTaskRef: (value: string) => void;
  taskRef: string;
  onHide: (message: GuildMessage) => void;
  onReact: (message: GuildMessage, emoji: string) => void;
  onSend: () => void;
}) {
  const emojiOptions = ["🔥", "💪", "✅", "🎯", "🙌", "🧠"];
  return (
    <section className="operator-cyan-panel space-y-4 p-4">
      <div className="grid gap-2 sm:grid-cols-[1fr_150px_110px]">
        <label className="flex items-center gap-2 border border-white/10 bg-black/30 px-3">
          <Search size={16} className="text-white/35" />
          <input
            className="min-w-0 flex-1 bg-transparent py-2 text-sm outline-none"
            placeholder="Search messages"
            value={messageSearch}
            onChange={(event) => setMessageSearch(event.target.value)}
          />
        </label>
        <select className="border border-white/10 bg-black/60 px-2 py-2 text-sm" value={memberFilter} onChange={(event) => setMemberFilter(event.target.value)}>
          <option value="">All members</option>
          {members.map((member) => (
            <option key={member.user_id} value={member.user_id}>
              {member.callsign}
            </option>
          ))}
        </select>
        <select className="border border-white/10 bg-black/60 px-2 py-2 text-sm" value={reactionFilter} onChange={(event) => setReactionFilter(event.target.value)}>
          <option value="">All emoji</option>
          {emojiOptions.map((emoji) => (
            <option key={emoji} value={emoji}>
              {emoji}
            </option>
          ))}
        </select>
      </div>

      <div className="max-h-[34rem] space-y-3 overflow-y-auto pr-1">
        {messages.length === 0 && <p className="py-4 text-sm text-white/45">No guild messages match this view.</p>}
        {messages.map((message) => (
          <article className="border border-white/10 bg-black/35 p-3" key={message.id}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-operator-purple">{message.author}</p>
                <p className="mt-2 text-sm leading-6 text-white/85">{message.body}</p>
                {message.task_ref && <p className="mt-2 text-xs uppercase text-operator-cyan">Task: {message.task_ref}</p>}
              </div>
              {canModerate && (
                <button className="text-white/40 hover:text-red-300" title="Hide message" onClick={() => onHide(message)}>
                  <Trash2 size={16} />
                </button>
              )}
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              {[message.suggested_emoji, ...emojiOptions.filter((emoji) => emoji !== message.suggested_emoji)].slice(0, 6).map((emoji) => (
                <button
                  className={`border px-2 py-1 text-sm ${message.my_reaction === emoji ? "border-operator-cyan bg-operator-cyan/15" : "border-white/10 bg-black/40"}`}
                  key={emoji}
                  title={trendTitle(message)}
                  onClick={() => onReact(message, emoji)}
                >
                  {emoji} {message.reactions[emoji] ?? 0}
                </button>
              ))}
              {message.trend.top_emoji && (
                <span className="text-xs uppercase text-white/40" title={trendTitle(message)}>
                  Top {message.trend.top_emoji} {message.trend.top_count}
                </span>
              )}
            </div>
          </article>
        ))}
      </div>

      <div className="grid gap-2 sm:grid-cols-[1fr_160px_auto]">
        <input
          className="min-w-0 border border-operator-cyan/60 bg-black/50 px-3 py-3 text-sm outline-none"
          placeholder="Check in, ask for accountability, or paste a goal link"
          value={chatInput}
          onChange={(event) => setChatInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              onSend();
            }
          }}
        />
        <input
          className="min-w-0 border border-white/15 bg-black/50 px-3 py-3 text-sm outline-none"
          placeholder="Task ref"
          value={taskRef}
          onChange={(event) => setTaskRef(event.target.value)}
        />
        <button className="border border-operator-cyan bg-operator-cyan/10 px-4 text-sm uppercase text-operator-cyan disabled:opacity-40" disabled={busy} onClick={onSend}>
          Send
        </button>
      </div>
    </section>
  );
}

function trendTitle(message: GuildMessage) {
  const changed = message.trend.last_changed_at ? new Date(message.trend.last_changed_at).toLocaleString() : "No changes yet";
  return `Last change: ${changed}. Previous top: ${message.trend.previous_top_emoji ?? "none"} (${message.trend.previous_top_count}).`;
}

function ModerationFeed({ events }: { events: ModerationEvent[] }) {
  return (
    <section>
      <h4 className="mb-3 text-xs uppercase tracking-[0.25em] text-operator-cyan">Moderation Feed</h4>
      <div className="space-y-2">
        {events.length === 0 && <p className="border border-white/10 bg-black/25 p-3 text-sm text-white/45">No moderation events recorded.</p>}
        {events.map((event) => (
          <article className="border border-white/10 bg-black/25 p-3 text-xs uppercase text-white/50" key={event.id}>
            <span className="text-white">{event.actor}</span> {event.event_type.replace("_", " ")}
            {event.target ? <span> / {event.target}</span> : null}
            <span className="block pt-1 text-white/35">{new Date(event.created_at).toLocaleString()}</span>
          </article>
        ))}
      </div>
    </section>
  );
}

function GlobalSocial({
  feed,
  guilds,
  leaderboard,
  metric,
  setMetric
}: {
  feed: FeedEvent[];
  guilds: Guild[];
  leaderboard: LeaderboardEntry[];
  metric: "total_xp" | "streak" | "stat";
  setMetric: (metric: "total_xp" | "streak" | "stat") => void;
}) {
  return (
    <section className="space-y-4">
      <section className="operator-cyan-panel p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-sm uppercase tracking-[0.3em] text-operator-cyan">Global Leaderboard</h3>
          <select className="border border-white/10 bg-black/60 px-2 py-2 text-sm" value={metric} onChange={(event) => setMetric(event.target.value as "total_xp" | "streak" | "stat")}>
            <option value="total_xp">Weekly XP</option>
            <option value="streak">Streak</option>
            <option value="stat">Intellect</option>
          </select>
        </div>
        <div className="mt-4 space-y-2">
          {leaderboard.map((entry) => (
            <article className="grid grid-cols-[40px_1fr_auto] items-center gap-3 border border-white/10 bg-black/30 p-3" key={entry.user_id}>
              <span className="text-operator-purple">#{entry.rank}</span>
              <p className="text-sm uppercase text-white">{entry.display_name}</p>
              <span className="text-xs uppercase text-operator-cyan">
                {metric === "streak" ? `${entry.streak_length} days` : metric === "stat" ? `${entry.stat_xp ?? 0} XP` : `${entry.weekly_xp} XP`}
              </span>
            </article>
          ))}
        </div>
      </section>

      <section className="operator-panel p-4">
        <h3 className="text-sm uppercase tracking-[0.3em] text-operator-purple">Private Guild Signals</h3>
        <div className="mt-4 space-y-3">
          {guilds.length === 0 && <p className="text-sm text-white/45">No guild signals discovered.</p>}
          {guilds.map((guild) => (
            <article className="border border-white/10 bg-black/30 p-3" key={guild.id}>
              <p className="text-sm uppercase text-white">{guild.name}</p>
              <p className="mt-1 text-xs text-white/45">
                {guild.member_count}/10 members / {guild.guild_xp} guild XP
              </p>
            </article>
          ))}
        </div>
      </section>

      <section className="operator-cyan-panel p-4">
        <h3 className="text-sm uppercase tracking-[0.3em] text-operator-cyan">Global Feed</h3>
        <div className="mt-4 space-y-3">
          {feed.length === 0 && <p className="py-4 text-sm text-white/45">No public completions broadcast yet.</p>}
          {feed.map((event) => (
            <article className="border border-white/10 bg-black/30 p-3" key={event.id}>
              <p className="text-sm uppercase text-white">{event.operator} defeated {event.goal_title || "an unnamed target"}</p>
              <p className="mt-1 text-xs uppercase text-operator-cyan">
                +{event.xp_awarded ?? 0} XP / {event.stat_key ?? "unknown"} sync
              </p>
            </article>
          ))}
        </div>
      </section>
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
  confirmPassword: string;
  email: string;
  error: string | null;
  loading: boolean;
  mode: "login" | "register";
  password: string;
  setConfirmPassword: (value: string) => void;
  setEmail: (value: string) => void;
  setMode: (value: "login" | "register") => void;
  setPassword: (value: string) => void;
  submitAuth: () => void;
};

function AuthFrame(props: AuthFrameProps) {
  const [showPassword, setShowPassword] = useState(false);
  const strength = getPasswordStrength(props.password);
  const passwordsMatch = props.confirmPassword.length === 0 || props.password === props.confirmPassword;

  return (
    <main className="flex min-h-screen items-center justify-center px-5 text-white">
      <section className="w-full max-w-md">
        <div className="mb-8 text-center">
          <OperatorLogo className="mx-auto mb-5 h-24 w-24" />
          <h1 className="operator-glow text-4xl uppercase">OPERATOR</h1>
          <p className="mt-2 text-xs uppercase tracking-[0.45em] text-white/45">Level Up Your Life</p>
        </div>

        <div className="space-y-4">
          <CyberInput label="Email" value={props.email} onChange={props.setEmail} />
          <CyberInput label="Password" minLength={8} type="password" value={props.password} onChange={props.setPassword} />
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
          onClick={() => {
            props.setConfirmPassword("");
            props.setMode(props.mode === "login" ? "register" : "login");
          }}
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
        <OperatorLogo className="mx-auto mb-6 h-24 w-24" />
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
  action,
  label,
  minLength,
  onChange,
  type = "text",
  value
}: {
  action?: ReactNode;
  label: string;
  minLength?: number;
  onChange: (value: string) => void;
  type?: string;
  value: string;
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm uppercase tracking-[0.22em] text-operator-purple">{label}</span>
      <input
        className="w-full border border-operator-purple/70 bg-operator-surface px-4 py-4 text-sm outline-none focus:border-operator-cyan"
        minLength={minLength}
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function OperatorLogo({ className = "" }: { className?: string }) {
  return (
    <img
      alt="Operator"
      className={`operator-logo object-contain ${className}`}
      height={128}
      src={OPERATOR_LOGO_SRC}
      width={128}
    />
  );
}

function getPasswordStrength(password: string) {
  const checks = [
    password.length >= 8,
    /[A-Z]/.test(password),
    /[a-z]/.test(password),
    /[0-9]/.test(password),
    /[^A-Za-z0-9]/.test(password)
  ];
  const score = password.length === 0 ? 0 : checks.filter(Boolean).length;
  const labels = ["Empty", "Weak", "Fair", "Good", "Strong", "Elite"];
  return { label: labels[score], score };
}

function PasswordStrengthMeter({ label, score }: { label: string; score: number }) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-xs uppercase tracking-[0.18em]">
        <span className="text-white/45">Password Strength</span>
        <span className={score >= 4 ? "text-operator-cyan" : score >= 3 ? "text-operator-purple" : "text-red-300"}>
          {label}
        </span>
      </div>
      <div className="grid grid-cols-5 gap-2">
        {Array.from({ length: 5 }, (_, index) => (
          <span
            className={`h-1 border border-white/10 ${
              index < score ? (score >= 4 ? "bg-operator-cyan" : "bg-operator-purple") : "bg-white/10"
            }`}
            key={index}
          />
        ))}
      </div>
    </div>
  );
}
