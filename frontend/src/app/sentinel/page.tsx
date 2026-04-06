"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getSentinelScenarios, getSentinelPlayer } from "@/lib/api";
import { cn } from "@/lib/utils";

function getSessionId(): string {
  if (typeof window === "undefined") return "ssr";
  let id = localStorage.getItem("ghost-session-id");
  if (!id) { id = crypto.randomUUID(); localStorage.setItem("ghost-session-id", id); }
  return id;
}

const DIFF_COLORS: Record<string, string> = {
  tutorial: "bg-emerald-500", easy: "bg-sky-500", medium: "bg-amber-500", hard: "bg-orange-500", expert: "bg-rose-500",
};

export default function SentinelPage() {
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [player, setPlayer] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
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

  if (loading) return <div className="min-h-screen flex items-center justify-center"><div className="text-muted-foreground/50">Loading...</div></div>;

  return (
    <div className="max-w-2xl mx-auto py-8 px-4 space-y-8">
      {/* Header */}
      <div className="text-center space-y-3">
        <h1 className="text-4xl font-bold tracking-tight">
          <span className="gradient-text">Sentinel</span>
        </h1>
        <p className="text-muted-foreground/60 text-[15px] max-w-md mx-auto">
          Inspect software packages arriving at the registry. Flag the suspicious ones. Can you spot the supply chain attack?
        </p>
      </div>

      {/* Player card */}
      {player && player.total_inspections > 0 && (
        <div className="rounded-2xl bg-foreground/[0.03] border border-foreground/[0.06] p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="text-2xl font-bold text-emerald-400">{player.total_score}</div>
              <div className="text-[12px] text-muted-foreground/50 leading-tight">
                <div className="font-medium text-foreground/60">{player.title}</div>
                <div>{player.total_inspections} inspected</div>
              </div>
            </div>
            <div className="flex gap-6 text-center text-[11px]">
              <div>
                <div className="text-lg font-bold text-foreground/70">{player.streak}</div>
                <div className="text-muted-foreground/40">Streak</div>
              </div>
              <div>
                <div className="text-lg font-bold text-foreground/70">{player.detection_rate ? `${(player.detection_rate * 100).toFixed(0)}%` : "—"}</div>
                <div className="text-muted-foreground/40">Detection</div>
              </div>
              <div>
                <div className="text-lg font-bold text-foreground/70">{player.best_streak}</div>
                <div className="text-muted-foreground/40">Best</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Scenario list */}
      <div className="space-y-2">
        {scenarios.map((s) => (
          <Link
            key={s.id}
            href={`/sentinel/inspect/${s.id}`}
            className="group flex items-center gap-4 rounded-xl bg-foreground/[0.02] border border-foreground/[0.05] hover:border-foreground/[0.12] hover:bg-foreground/[0.04] p-4 transition-all"
          >
            <div className={cn("h-3 w-3 rounded-full shrink-0", DIFF_COLORS[s.difficulty] || "bg-foreground/20")} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-[14px] font-medium text-foreground/80 group-hover:text-foreground transition-colors">{s.package_name}</span>
                <span className="text-[11px] text-muted-foreground/40 font-mono">{s.registry}</span>
              </div>
              <p className="text-[12px] text-muted-foreground/40 font-mono mt-0.5">{s.version_from || "?"} &rarr; {s.version_to || "?"}</p>
            </div>
            <div className="text-right shrink-0">
              {s.total_inspections > 0 ? (
                <span className="text-[11px] text-muted-foreground/40">{s.total_inspections} inspected</span>
              ) : (
                <span className="text-[11px] text-emerald-400/60 font-medium">New</span>
              )}
            </div>
            <svg className="w-4 h-4 text-muted-foreground/20 group-hover:text-foreground/40 transition-colors shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </Link>
        ))}
      </div>

      {scenarios.length === 0 && (
        <div className="text-center py-12 text-muted-foreground/40 text-sm">No scenarios available.</div>
      )}

      <div className="flex justify-center gap-4 text-[10px] text-muted-foreground/30">
        {Object.entries(DIFF_COLORS).map(([d, c]) => (
          <div key={d} className="flex items-center gap-1">
            <div className={cn("h-2 w-2 rounded-full", c)} />
            <span className="capitalize">{d}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
