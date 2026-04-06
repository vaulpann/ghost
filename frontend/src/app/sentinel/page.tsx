"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getSentinelScenarios, getSentinelPlayer, getSentinelStats } from "@/lib/api";
import { cn } from "@/lib/utils";

function getSessionId(): string {
  if (typeof window === "undefined") return "ssr";
  let id = localStorage.getItem("ghost-session-id");
  if (!id) { id = crypto.randomUUID(); localStorage.setItem("ghost-session-id", id); }
  return id;
}

const DIFFICULTY_STYLES: Record<string, { label: string; color: string }> = {
  tutorial: { label: "Tutorial", color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
  easy: { label: "Easy", color: "text-sky-400 bg-sky-500/10 border-sky-500/20" },
  medium: { label: "Medium", color: "text-amber-400 bg-amber-500/10 border-amber-500/20" },
  hard: { label: "Hard", color: "text-orange-400 bg-orange-500/10 border-orange-500/20" },
  expert: { label: "Expert", color: "text-rose-400 bg-rose-500/10 border-rose-500/20" },
};

export default function SentinelPage() {
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [player, setPlayer] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [diffFilter, setDiffFilter] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const params = new URLSearchParams();
        if (diffFilter) params.set("difficulty", diffFilter);
        params.set("per_page", "20");

        const [scenData, playerData, statsData] = await Promise.all([
          getSentinelScenarios(params.toString()),
          getSentinelPlayer(getSessionId()).catch(() => null),
          getSentinelStats().catch(() => null),
        ]);
        setScenarios(scenData.items);
        setTotal(scenData.total);
        setPlayer(playerData);
        setStats(statsData);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [diffFilter]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="animate-fade-in">
        <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight gradient-text">
          Supply Chain Sentinel
        </h1>
        <p className="text-xs sm:text-sm text-muted-foreground/70 mt-1">
          Inspect incoming packages. Flag the suspicious ones. Protect the supply chain.
        </p>
      </div>

      {/* Player stats bar */}
      {player && (
        <div className="flex items-center gap-6 rounded-2xl glass p-4 animate-fade-in animate-fade-in-delay-1">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-emerald-500/20 flex items-center justify-center text-emerald-400 font-bold text-lg">
              {player.level}
            </div>
            <div>
              <p className="text-[13px] font-medium text-foreground/80">{player.title}</p>
              <p className="text-[11px] text-muted-foreground/50">Level {player.level}</p>
            </div>
          </div>
          <div className="flex gap-6 text-[11px] text-muted-foreground/50">
            <span>Score: <span className="text-foreground/70 font-mono">{player.total_score}</span></span>
            <span>Streak: <span className="text-foreground/70 font-mono">{player.streak}</span></span>
            <span>Detection: <span className="text-foreground/70 font-mono">{player.detection_rate ? `${(player.detection_rate * 100).toFixed(0)}%` : "—"}</span></span>
            <span>Inspected: <span className="text-foreground/70 font-mono">{player.total_inspections}</span></span>
          </div>
        </div>
      )}

      {/* Filter */}
      <div className="flex gap-3 animate-fade-in animate-fade-in-delay-1">
        <select
          value={diffFilter}
          onChange={(e) => setDiffFilter(e.target.value)}
          className="rounded-xl glass border-0 bg-foreground/[0.03] px-4 py-2.5 text-[13px] text-foreground/60 focus:outline-none focus:ring-1 focus:ring-ring/20 appearance-none cursor-pointer"
        >
          <option value="">All difficulties</option>
          <option value="tutorial">Tutorial</option>
          <option value="easy">Easy</option>
          <option value="medium">Medium</option>
          <option value="hard">Hard</option>
          <option value="expert">Expert</option>
        </select>
        {stats && (
          <div className="ml-auto flex gap-4 text-[11px] text-muted-foreground/40">
            <span>{stats.total_scenarios} scenarios</span>
            <span>{stats.total_inspections} inspections</span>
            <span>{stats.total_players} inspectors</span>
          </div>
        )}
      </div>

      {/* Scenario Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 animate-fade-in animate-fade-in-delay-2">
        {scenarios.map((s, i) => {
          const ds = DIFFICULTY_STYLES[s.difficulty] || DIFFICULTY_STYLES.easy;
          return (
            <Link
              key={s.id}
              href={`/sentinel/inspect/${s.id}`}
              className="group rounded-xl glass glass-hover p-5 animate-fade-in"
              style={{ animationDelay: `${i * 0.03}s` }}
            >
              <div className="flex items-center gap-2 mb-3">
                <span className={cn("text-[10px] font-medium uppercase tracking-wider px-2 py-0.5 rounded-full border", ds.color)}>
                  {ds.label}
                </span>
                <span className="text-[10px] text-muted-foreground/40 font-mono">{s.registry}</span>
              </div>

              <h3 className="text-[15px] font-medium text-foreground/80 group-hover:text-foreground transition-colors mb-1">
                {s.package_name}
              </h3>
              <p className="text-[12px] text-muted-foreground/50 font-mono">
                {s.version_from || "?"} &rarr; {s.version_to || "?"}
              </p>

              <div className="flex items-center justify-between mt-4 pt-3 border-t border-foreground/[0.04] text-[11px] text-muted-foreground/40">
                <span>{s.total_inspections} inspection{s.total_inspections !== 1 ? "s" : ""}</span>
                {s.correct_rate !== null && (
                  <span className="font-mono">{(s.correct_rate * 100).toFixed(0)}% accuracy</span>
                )}
              </div>
            </Link>
          );
        })}
      </div>

      {scenarios.length === 0 && !loading && (
        <div className="rounded-2xl glass p-12 text-center text-muted-foreground/50 text-sm">
          No scenarios available yet.
        </div>
      )}
    </div>
  );
}
