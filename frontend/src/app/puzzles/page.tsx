"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getPuzzles } from "@/lib/api";
import type { Puzzle } from "@/lib/types";
import { cn } from "@/lib/utils";

const PER_PAGE = 20;

const GAME_TYPES: Record<string, { label: string; icon: string; color: string }> = {
  maze: { label: "Maze Escape", icon: "M", color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
  parser: { label: "Code Cracker", icon: "P", color: "text-amber-400 bg-amber-500/10 border-amber-500/20" },
  timing: { label: "Timing Heist", icon: "T", color: "text-rose-400 bg-rose-500/10 border-rose-500/20" },
  routing: { label: "Route Runner", icon: "R", color: "text-sky-400 bg-sky-500/10 border-sky-500/20" },
  gatekeeper: { label: "Gatekeeper", icon: "G", color: "text-violet-400 bg-violet-500/10 border-violet-500/20" },
  factory: { label: "Factory Hack", icon: "F", color: "text-orange-400 bg-orange-500/10 border-orange-500/20" },
  blueprint: { label: "Blueprint", icon: "B", color: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20" },
};

export default function PuzzlesPage() {
  const [puzzles, setPuzzles] = useState<Puzzle[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState("");

  useEffect(() => { setPage(1); }, [typeFilter]);

  useEffect(() => {
    async function load() {
      try {
        const params = new URLSearchParams();
        if (typeFilter) params.set("game_type", typeFilter);
        params.set("page", String(page));
        params.set("per_page", String(PER_PAGE));
        const data = await getPuzzles(params.toString());
        setPuzzles(data.items);
        setTotal(data.total);
      } catch (e) {
        console.error("Failed to fetch puzzles:", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [typeFilter, page]);

  const totalPages = Math.ceil(total / PER_PAGE);

  return (
    <div className="space-y-6">
      <div className="animate-fade-in">
        <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight gradient-text">Puzzles</h1>
        <p className="text-xs sm:text-sm text-muted-foreground/70 mt-1">
          Solve logic puzzles to validate real findings. No security knowledge needed.
        </p>
      </div>

      <div className="flex gap-3 animate-fade-in animate-fade-in-delay-1">
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="rounded-xl glass border-0 bg-foreground/[0.03] px-4 py-2.5 text-[13px] text-foreground/60 focus:outline-none focus:ring-1 focus:ring-ring/20 appearance-none cursor-pointer"
        >
          <option value="">All types</option>
          {Object.entries(GAME_TYPES).map(([key, val]) => (
            <option key={key} value={key}>{val.label}</option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 animate-fade-in animate-fade-in-delay-2">
        {puzzles.map((p, i) => {
          const gt = GAME_TYPES[p.game_type] || { label: p.game_type, icon: "?", color: "text-foreground/50 bg-foreground/5 border-foreground/10" };
          const solveRatePct = p.solve_rate !== null ? (p.solve_rate * 100) : null;
          return (
            <Link
              key={p.id}
              href={`/puzzles/${p.id}`}
              className="group rounded-xl glass glass-hover p-5 animate-fade-in flex flex-col"
              style={{ animationDelay: `${i * 0.03}s` }}
            >
              <div className="flex items-center gap-2 mb-3">
                <span className={cn("flex h-8 w-8 items-center justify-center rounded-lg text-[13px] font-bold border", gt.color)}>
                  {gt.icon}
                </span>
                <span className={cn("text-[11px] font-medium uppercase tracking-wider", gt.color.split(" ")[0])}>
                  {gt.label}
                </span>
              </div>

              <h3 className="text-[15px] font-medium text-foreground/80 group-hover:text-foreground transition-colors mb-2 line-clamp-2 flex-1">
                {p.title}
              </h3>

              <p className="text-[12px] text-muted-foreground/50 line-clamp-2 mb-4">
                {p.flavor_text}
              </p>

              <div className="flex items-center justify-between text-[11px] text-muted-foreground/40 mt-auto pt-3 border-t border-foreground/[0.04]">
                <div className="flex items-center gap-3">
                  <div className="flex gap-0.5">
                    {Array.from({ length: 5 }).map((_, j) => (
                      <div key={j} className={cn("h-1.5 w-1.5 rounded-full", j < p.difficulty ? "bg-foreground/25" : "bg-foreground/[0.06]")} />
                    ))}
                  </div>
                  <span>{p.total_attempts} plays</span>
                </div>
                {solveRatePct !== null && (
                  <span className={cn("font-mono font-medium",
                    solveRatePct > 60 ? "text-emerald-400/60" :
                    solveRatePct > 30 ? "text-amber-400/60" : "text-rose-400/60"
                  )}>
                    {solveRatePct.toFixed(0)}% solved
                  </span>
                )}
              </div>
            </Link>
          );
        })}
      </div>

      {puzzles.length === 0 && !loading && (
        <div className="rounded-2xl glass p-12 text-center text-muted-foreground/50 text-sm">
          No puzzles yet. Vulnerability scans generate interactive game levels.
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-between animate-fade-in">
          <p className="text-[12px] text-muted-foreground/50 tabular-nums">{(page - 1) * PER_PAGE + 1}–{Math.min(page * PER_PAGE, total)} of {total}</p>
          <div className="flex items-center gap-1">
            <button onClick={() => setPage(page - 1)} disabled={page === 1} className="px-2.5 py-1.5 rounded-lg text-[12px] text-muted-foreground/70 hover:text-foreground/60 hover:bg-foreground/[0.03] disabled:opacity-20 disabled:cursor-not-allowed transition-all">Prev</button>
            <button onClick={() => setPage(page + 1)} disabled={page === totalPages} className="px-2.5 py-1.5 rounded-lg text-[12px] text-muted-foreground/70 hover:text-foreground/60 hover:bg-foreground/[0.03] disabled:opacity-20 disabled:cursor-not-allowed transition-all">Next</button>
          </div>
        </div>
      )}
    </div>
  );
}
