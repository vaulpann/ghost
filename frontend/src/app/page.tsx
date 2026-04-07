"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getSentinelScenarios, getSentinelPlayer } from "@/lib/api";
import { cn } from "@/lib/utils";
import { RegistryBadge } from "@/components/analysis/registry-badge";

function getSessionId(): string {
  if (typeof window === "undefined") return "ssr";
  let id = localStorage.getItem("ghost-session-id");
  if (!id) { id = crypto.randomUUID(); localStorage.setItem("ghost-session-id", id); }
  return id;
}

/** Get today's date string in EST (America/New_York) as YYYY-MM-DD */
function getTodayEST(): string {
  return new Date().toLocaleDateString("en-CA", { timeZone: "America/New_York" });
}

/** Get completed challenges, auto-expiring if date has changed */
function getCompleted(): Record<string, any> {
  if (typeof window === "undefined") return {};
  try {
    const raw = JSON.parse(localStorage.getItem("ghost-completed") || "{}");
    const today = getTodayEST();
    // If stored date doesn't match today, clear completions
    if (raw._date !== today) {
      const fresh = { _date: today };
      localStorage.setItem("ghost-completed", JSON.stringify(fresh));
      return fresh;
    }
    return raw;
  } catch {
    return { _date: getTodayEST() };
  }
}

/**
 * Pick 4 daily challenges from the scenario pool based on today's date.
 * Uses a seeded shuffle so everyone sees the same 4 on a given day,
 * and they rotate at midnight EST.
 */
function getDailyChallenges(scenarios: any[]): { dailies: any[]; open: any[] } {
  if (scenarios.length <= 4) return { dailies: scenarios, open: [] };

  const today = getTodayEST();
  // Simple hash from date string to get a seed
  let seed = 0;
  for (let i = 0; i < today.length; i++) seed = today.charCodeAt(i) + ((seed << 5) - seed);

  // Seeded shuffle (Fisher-Yates with deterministic pseudo-random)
  const indices = scenarios.map((_, i) => i);
  const mulberry32 = (a: number) => () => {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
  const rng = mulberry32(seed);
  for (let i = indices.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [indices[i], indices[j]] = [indices[j], indices[i]];
  }

  const dailyIndices = indices.slice(0, 4);
  const openIndices = indices.slice(4);
  return {
    dailies: dailyIndices.map(i => scenarios[i]),
    open: openIndices.map(i => scenarios[i]),
  };
}

const PUZZLE_IMAGES = Array.from({ length: 10 }, (_, i) => `/puzzle-${i + 1}.jpg`);

export default function ResolverPage() {
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [player, setPlayer] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [completed, setCompleted] = useState<Record<string, any>>({});

  useEffect(() => {
    setCompleted(getCompleted());
    async function load() {
      try {
        const [scenData, playerData] = await Promise.all([
          getSentinelScenarios("per_page=50"),
          getSentinelPlayer(getSessionId()).catch(() => null),
        ]);
        setScenarios(scenData.items);
        setPlayer(playerData);
      } catch (e) { console.error(e); }
      finally { setLoading(false); }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground/50 text-sm">Loading...</div>
      </div>
    );
  }

  const { dailies, open } = getDailyChallenges(scenarios);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="animate-fade-in">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground/90">
          Can you spot the supply chain attack?
        </h1>
        <p className="text-[13px] sm:text-[14px] text-muted-foreground/50 mt-2 max-w-lg leading-relaxed">
          Real packages. Real diffs. Review the evidence and decide — is this update safe, or has it been compromised?
        </p>
      </div>

      {/* Daily Challenges — 2x2 grid */}
      {dailies.length > 0 && (
        <div className="animate-fade-in animate-fade-in-delay-1">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-[15px] font-medium text-foreground/60">Today's Challenges</h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {dailies.map((d, idx) => {
              const res = completed[d.id];
              if (res) {
                return (
                  <div key={d.id} className="rounded-2xl glass overflow-hidden">
                    <img
                      src={PUZZLE_IMAGES[idx]}
                      alt=""
                      className="w-full object-cover"
                      style={{ height: 160 }}
                    />
                    <div className="p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="font-semibold text-[15px] text-foreground/90 truncate">{d.package_name}</span>
                        <RegistryBadge registry={d.registry} />
                      </div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={cn("text-[12px] font-bold", res.is_correct ? "text-green-600" : "text-red-500")}>
                          {res.is_correct ? "Correct" : "Incorrect"}
                        </span>
                        <span className="text-[12px] font-semibold text-foreground/50">{res.score > 0 ? "+" : ""}{res.score} pts</span>
                        <span className={cn(
                          "text-[10px] px-2 py-0.5 rounded-full font-medium",
                          res.verdict === "safe" && "bg-green-50 text-green-600",
                          res.verdict === "suspicious" && "bg-amber-50 text-amber-600",
                          res.verdict === "malicious" && "bg-red-50 text-red-600",
                        )}>
                          {res.verdict}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              }
              return (
                <Link
                  key={d.id}
                  href={`/sentinel/inspect/${d.id}`}
                  className="group block rounded-2xl glass glass-hover overflow-hidden"
                >
                  <img
                    src={PUZZLE_IMAGES[idx]}
                    alt=""
                    className="w-full object-cover group-hover:scale-[1.02] transition-transform duration-300"
                    style={{ height: 160 }}
                  />
                  <div className="p-4">
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="font-semibold text-[15px] text-foreground/90 group-hover:text-foreground transition-colors truncate">
                        {d.package_name}
                      </span>
                      <RegistryBadge registry={d.registry} />
                    </div>
                    <div className="flex items-center justify-between">
                      <p className="text-[12px] text-muted-foreground/50 font-mono">
                        {d.version_from || "?"} &rarr; {d.version_to || "?"}
                      </p>
                      <span className="text-[12px] font-semibold text-[#1e3a5f] group-hover:text-[#2a4f7a] transition-colors">
                        Play &rarr;
                      </span>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      )}

      {/* Open Puzzles — locked */}
      {open.length > 0 && (
        <div className="animate-fade-in animate-fade-in-delay-2 relative">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-[15px] font-medium text-foreground/60">Open Puzzles</h2>
            <span className="text-[11px] text-muted-foreground/50 tabular-nums">
              {open.length} available
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 opacity-40 pointer-events-none select-none" style={{ filter: "grayscale(0.6)" }}>
            {open.map((s, i) => (
              <div
                key={s.id}
                className="flex items-center gap-4 rounded-xl glass p-4"
              >
                <img
                  src={PUZZLE_IMAGES[(i + 4) % PUZZLE_IMAGES.length]}
                  alt=""
                  className="shrink-0 rounded-lg object-cover"
                  style={{ width: 40, height: 40 }}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 sm:gap-2.5 flex-wrap">
                    <span className="font-medium text-[13px] text-foreground/80">
                      {s.package_name}
                    </span>
                    <RegistryBadge registry={s.registry} />
                    <span className="text-[11px] text-muted-foreground/50 font-mono">
                      {s.version_from || "?"} &rarr; {s.version_to || "?"}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Sign up overlay */}
          <div className="absolute inset-0 flex items-center justify-center" style={{ top: 36 }}>
            <div className="rounded-xl bg-white/80 backdrop-blur-sm border border-foreground/[0.06] px-6 py-4 text-center shadow-sm">
              <p className="text-[14px] font-semibold text-foreground/80">Sign up to unlock all puzzles</p>
              <p className="text-[12px] text-muted-foreground/50 mt-1">Coming soon</p>
            </div>
          </div>
        </div>
      )}

      {scenarios.length === 0 && (
        <div className="rounded-2xl glass p-12 text-center">
          <div className="text-muted-foreground/30 text-sm">
            No puzzles available yet.
          </div>
        </div>
      )}
    </div>
  );
}
