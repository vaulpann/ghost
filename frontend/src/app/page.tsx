"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { RegistryBadge } from "@/components/analysis/registry-badge";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://ghostapi.validia.ai";

function getSessionId(): string {
  if (typeof window === "undefined") return "ssr";
  let id = localStorage.getItem("ghost-session-id");
  if (!id) { id = crypto.randomUUID(); localStorage.setItem("ghost-session-id", id); }
  return id;
}

function getTodayEST(): string {
  return new Date().toLocaleDateString("en-CA", { timeZone: "America/New_York" });
}

function getDayNumber(): number {
  const start = new Date("2026-04-07T00:00:00-04:00");
  const todayStr = getTodayEST();
  const [y, m, d] = todayStr.split("-").map(Number);
  const today = new Date(y, m - 1, d);
  const startLocal = new Date(start.getFullYear(), start.getMonth(), start.getDate());
  return Math.floor((today.getTime() - startLocal.getTime()) / (1000 * 60 * 60 * 24));
}

const PUZZLE_IMAGES = Array.from({ length: 10 }, (_, i) => `/puzzle-${i + 1}.jpg`);

export default function ResolverPage() {
  const [dailies, setDailies] = useState<any[]>([]);
  const [open, setOpen] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [completed, setCompleted] = useState<Record<string, any>>({});

  useEffect(() => {
    async function load() {
      try {
        const sessionId = getSessionId();
        const res = await fetch(`${API_BASE}/api/v1/sentinel/daily?session_id=${sessionId}`);
        const data = await res.json();
        setDailies(data.dailies || []);
        setOpen(data.open || []);
        setCompleted(data.completions || {});
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

  return (
    <div className="space-y-8 max-w-3xl mx-auto">
      {/* Header */}
      <div className="animate-fade-in">
        <p className="text-[12px] font-semibold text-muted-foreground/40 tracking-widest mb-2">
          <span className="uppercase">Day #{getDayNumber()}</span>, {new Date().toLocaleDateString("en-US", { timeZone: "America/New_York", month: "long", day: "numeric", year: "numeric" })}
        </p>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground/90">
          Can you spot the supply chain attack?
        </h1>
        <p className="text-[13px] sm:text-[14px] text-muted-foreground/50 mt-2 max-w-lg leading-relaxed">
          Real packages. Real diffs. Review the evidence and decide: is this update safe, or has it been compromised?
        </p>
      </div>

      {/* Daily Challenges */}
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
                    <img src={PUZZLE_IMAGES[idx]} alt="" className="w-full object-cover h-[160px] sm:h-auto sm:aspect-square" />
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
                <Link key={d.id} href={`/sentinel/inspect/${d.id}`} className="group block rounded-2xl glass glass-hover overflow-hidden">
                  <img src={PUZZLE_IMAGES[idx]} alt="" className="w-full object-cover h-[160px] sm:h-auto sm:aspect-square group-hover:scale-[1.02] transition-transform duration-300" />
                  <div className="p-4">
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="font-semibold text-[15px] text-foreground/90 group-hover:text-foreground transition-colors truncate">{d.package_name}</span>
                      <RegistryBadge registry={d.registry} />
                    </div>
                    <div className="flex items-center justify-between">
                      <p className="text-[12px] text-muted-foreground/50 font-mono">{d.version_from || "?"} &rarr; {d.version_to || "?"}</p>
                      <span className="text-[12px] font-semibold text-[#1e3a5f] group-hover:text-[#2a4f7a] transition-colors">Play &rarr;</span>
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
            <span className="text-[11px] text-muted-foreground/50 tabular-nums">{open.length} available</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 opacity-40 pointer-events-none select-none" style={{ filter: "grayscale(0.6)" }}>
            {open.map((s, i) => (
              <div key={s.id} className="flex items-center gap-4 rounded-xl glass p-4">
                <img src={PUZZLE_IMAGES[(i + 4) % PUZZLE_IMAGES.length]} alt="" className="shrink-0 rounded-lg object-cover" style={{ width: 40, height: 40 }} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 sm:gap-2.5 flex-wrap">
                    <span className="font-medium text-[13px] text-foreground/80">{s.package_name}</span>
                    <RegistryBadge registry={s.registry} />
                    <span className="text-[11px] text-muted-foreground/50 font-mono">{s.version_from || "?"} &rarr; {s.version_to || "?"}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="absolute inset-0 flex items-center justify-center" style={{ top: 36 }}>
            <div className="rounded-xl bg-white/80 backdrop-blur-sm border border-foreground/[0.06] px-6 py-4 text-center shadow-sm">
              <p className="text-[14px] font-semibold text-foreground/80">Sign up to unlock all puzzles</p>
              <p className="text-[12px] text-muted-foreground/50 mt-1">Coming soon</p>
            </div>
          </div>
        </div>
      )}

      {dailies.length === 0 && (
        <div className="rounded-2xl glass p-12 text-center">
          <div className="text-muted-foreground/30 text-sm">No puzzles available yet.</div>
        </div>
      )}
    </div>
  );
}
