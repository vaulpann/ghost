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

const PUZZLE_IMAGES = Array.from({ length: 10 }, (_, i) => `/puzzle-${i + 1}.jpg`);

function PuzzleImage({ name }: { name: string }) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  const idx = Math.abs(hash) % PUZZLE_IMAGES.length;

  return (
    <img
      src={PUZZLE_IMAGES[idx]}
      alt=""
      className="shrink-0 rounded-lg object-cover"
      style={{ width: 40, height: 40 }}
    />
  );
}

export default function ResolverPage() {
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground/50 text-sm">Loading...</div>
      </div>
    );
  }

  const daily = scenarios.length > 0 ? scenarios[0] : null;
  const open = scenarios.slice(1);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 animate-fade-in">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight gradient-text">
            Resolver
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground/70 mt-1">
            Inspect packages. Spot supply chain threats.
          </p>
        </div>
        {player && player.total_inspections > 0 && (
          <div className="flex gap-5 text-right">
            {[
              { label: "Score", value: player.total_score },
              { label: "Streak", value: player.streak },
              { label: "Detection", value: player.detection_rate ? `${(player.detection_rate * 100).toFixed(0)}%` : "—" },
            ].map((s) => (
              <div key={s.label}>
                <p className="text-lg font-semibold tabular-nums text-foreground/80">{s.value}</p>
                <p className="text-[10px] text-muted-foreground/40 uppercase tracking-wider">{s.label}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Daily */}
      {daily && (
        <div className="animate-fade-in animate-fade-in-delay-1">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-[15px] font-medium text-foreground/60">Daily Challenge</h2>
          </div>

          <Link
            href={`/sentinel/inspect/${daily.id}`}
            className="group block rounded-2xl glass glass-hover p-6"
          >
            <div className="flex items-center gap-4">
              <PuzzleImage name={daily.package_name} />
              <div className="flex-1">
                <div className="flex items-center gap-2.5 mb-1.5">
                  <span className="font-semibold text-[18px] text-foreground/90 group-hover:text-foreground transition-colors">
                    {daily.package_name}
                  </span>
                  <RegistryBadge registry={daily.registry} />
                </div>
                <p className="text-[13px] text-muted-foreground/50 font-mono">
                  {daily.version_from || "?"} &rarr; {daily.version_to || "?"}
                </p>
              </div>
              <div className="rounded-lg bg-[#1e3a5f] px-5 py-2.5 text-[13px] font-semibold text-white group-hover:bg-[#2a4f7a] transition-colors shrink-0">
                Play
              </div>
            </div>
            {daily.total_inspections > 0 && (
              <p className="text-[11px] text-muted-foreground/40 mt-3">
                {daily.total_inspections} inspections completed
              </p>
            )}
          </Link>
        </div>
      )}

      {/* Open Puzzles */}
      {open.length > 0 && (
        <div className="animate-fade-in animate-fade-in-delay-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-[15px] font-medium text-foreground/60">Open Puzzles</h2>
            <span className="text-[11px] text-muted-foreground/50 tabular-nums">
              {open.length} available
            </span>
          </div>

          <div className="space-y-2">
            {open.map((s, i) => (
              <Link
                key={s.id}
                href={`/sentinel/inspect/${s.id}`}
                className="group flex items-center gap-4 rounded-xl glass glass-hover p-4 animate-fade-in"
                style={{ animationDelay: `${i * 0.03}s` }}
              >
                <PuzzleImage name={s.package_name} />

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 sm:gap-2.5 mb-1 sm:mb-1.5 flex-wrap">
                    <span className="font-medium text-[13px] text-foreground/80 group-hover:text-foreground transition-colors">
                      {s.package_name}
                    </span>
                    <RegistryBadge registry={s.registry} />
                    <span className="text-[11px] text-muted-foreground/50 font-mono">
                      {s.version_from || "?"} &rarr; {s.version_to || "?"}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  {s.total_inspections > 0 ? (
                    <span className="text-[11px] text-muted-foreground/40 tabular-nums">
                      {s.total_inspections} played
                    </span>
                  ) : (
                    <span className="text-[11px] text-[#1e3a5f] font-medium">New</span>
                  )}
                  <span className="text-[11px] text-muted-foreground/20">
                    &rarr;
                  </span>
                </div>
              </Link>
            ))}
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
