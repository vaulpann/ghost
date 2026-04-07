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

function getCompleted(): Record<string, any> {
  if (typeof window === "undefined") return {};
  try { return JSON.parse(localStorage.getItem("ghost-completed") || "{}"); }
  catch { return {}; }
}

const PUZZLE_IMAGES = Array.from({ length: 10 }, (_, i) => `/puzzle-${i + 1}.jpg`);

function PuzzleImage({ index }: { index: number }) {
  return (
    <img
      src={PUZZLE_IMAGES[index % PUZZLE_IMAGES.length]}
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

  const daily = scenarios.length > 0 ? scenarios[0] : null;
  const open = scenarios.slice(1);
  const dailyResult = daily ? completed[daily.id] : null;

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

      {/* Daily */}
      {daily && (
        <div className="animate-fade-in animate-fade-in-delay-1">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-[15px] font-medium text-foreground/60">Daily Challenge</h2>
          </div>

          {dailyResult ? (
            /* Completed state */
            <div className="rounded-2xl glass p-6">
              <div className="flex items-center gap-5">
                <img
                  src={PUZZLE_IMAGES[0]}
                  alt=""
                  className="shrink-0 rounded-xl object-cover"
                  style={{ width: 80, height: 80 }}
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2.5 mb-1.5">
                    <span className="font-semibold text-[20px] sm:text-[22px] text-foreground/90">
                      {daily.package_name}
                    </span>
                    <RegistryBadge registry={daily.registry} />
                  </div>
                  <p className="text-[13px] text-muted-foreground/50 font-mono">
                    {daily.version_from || "?"} &rarr; {daily.version_to || "?"}
                  </p>
                </div>
              </div>

              {/* Result summary */}
              <div className="mt-5 pt-5 border-t border-foreground/[0.06]">
                <div className="flex items-center gap-3 mb-3">
                  <span className={cn(
                    "text-[13px] font-bold",
                    dailyResult.is_correct ? "text-green-600" : "text-red-500"
                  )}>
                    {dailyResult.is_correct ? "Correct" : "Incorrect"}
                  </span>
                  <span className="text-[13px] font-semibold text-foreground/70">
                    {dailyResult.score > 0 ? "+" : ""}{dailyResult.score} pts
                  </span>
                  <span className={cn(
                    "text-[11px] px-2 py-0.5 rounded-full font-medium",
                    dailyResult.verdict === "safe" && "bg-green-50 text-green-600",
                    dailyResult.verdict === "suspicious" && "bg-amber-50 text-amber-600",
                    dailyResult.verdict === "malicious" && "bg-red-50 text-red-600",
                  )}>
                    You voted: {dailyResult.verdict}
                  </span>
                </div>
                <p className="text-[13px] text-muted-foreground/60 leading-relaxed">
                  {dailyResult.was_malicious
                    ? dailyResult.attack_name || "This was a malicious package."
                    : "This was a legitimate, safe update."}
                </p>
                {dailyResult.postmortem && (
                  <p className="text-[12px] text-muted-foreground/40 mt-2 leading-relaxed">
                    {dailyResult.postmortem}
                  </p>
                )}
              </div>
            </div>
          ) : (
            /* Not yet played */
            <Link
              href={`/sentinel/inspect/${daily.id}`}
              className="group block rounded-2xl glass glass-hover p-6"
            >
              <div className="flex items-center gap-5">
                <img
                  src={PUZZLE_IMAGES[0]}
                  alt=""
                  className="shrink-0 rounded-xl object-cover"
                  style={{ width: 80, height: 80 }}
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2.5 mb-1.5">
                    <span className="font-semibold text-[20px] sm:text-[22px] text-foreground/90 group-hover:text-foreground transition-colors">
                      {daily.package_name}
                    </span>
                    <RegistryBadge registry={daily.registry} />
                  </div>
                  <p className="text-[13px] text-muted-foreground/50 font-mono">
                    {daily.version_from || "?"} &rarr; {daily.version_to || "?"}
                  </p>
                  {daily.total_inspections > 0 && (
                    <p className="text-[11px] text-muted-foreground/40 mt-2">
                      {daily.total_inspections} inspections completed
                    </p>
                  )}
                </div>
                <div className="rounded-lg bg-[#1e3a5f] px-5 py-2.5 text-[13px] font-semibold text-white group-hover:bg-[#2a4f7a] transition-colors shrink-0">
                  Play
                </div>
              </div>
            </Link>
          )}
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

          <div className="space-y-2 opacity-40 pointer-events-none select-none" style={{ filter: "grayscale(0.6)" }}>
            {open.map((s, i) => (
              <div
                key={s.id}
                className="flex items-center gap-4 rounded-xl glass p-4"
              >
                <PuzzleImage index={i + 1} />

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 sm:gap-2.5 mb-1 sm:mb-1.5 flex-wrap">
                    <span className="font-medium text-[13px] text-foreground/80">
                      {s.package_name}
                    </span>
                    <RegistryBadge registry={s.registry} />
                    <span className="text-[11px] text-muted-foreground/50 font-mono">
                      {s.version_from || "?"} &rarr; {s.version_to || "?"}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <span className="text-[11px] text-muted-foreground/20">
                    &rarr;
                  </span>
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
