"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getPuzzles } from "@/lib/api";
import type { Puzzle } from "@/lib/types";
import { RegistryBadge } from "@/components/analysis/registry-badge";
import { cn, timeAgo } from "@/lib/utils";

const PER_PAGE = 20;

const CHALLENGE_STYLES: Record<string, { label: string; color: string }> = {
  reachability: { label: "Reachability", color: "text-sky-400 bg-sky-500/10 border-sky-500/20" },
  exploitability: { label: "Exploitability", color: "text-orange-400 bg-orange-500/10 border-orange-500/20" },
  impact: { label: "Impact", color: "text-violet-400 bg-violet-500/10 border-violet-500/20" },
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
        if (typeFilter) params.set("challenge_type", typeFilter);
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
        <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight gradient-text">Validate</h1>
        <p className="text-xs sm:text-sm text-muted-foreground/70 mt-1">
          Challenge the scanner's findings. Can you prove it wrong?
        </p>
      </div>

      {/* Filters */}
      <div className="flex gap-3 animate-fade-in animate-fade-in-delay-1">
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="rounded-xl glass border-0 bg-foreground/[0.03] px-4 py-2.5 text-[13px] text-foreground/60 focus:outline-none focus:ring-1 focus:ring-ring/20 appearance-none cursor-pointer"
        >
          <option value="">All challenges</option>
          <option value="reachability">Reachability</option>
          <option value="exploitability">Exploitability</option>
          <option value="impact">Impact</option>
        </select>
      </div>

      {/* Puzzle Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 animate-fade-in animate-fade-in-delay-2">
        {puzzles.map((p, i) => {
          const style = CHALLENGE_STYLES[p.challenge_type] || CHALLENGE_STYLES.reachability;
          return (
            <Link
              key={p.id}
              href={`/puzzles/${p.id}`}
              className="group rounded-xl glass glass-hover p-5 animate-fade-in"
              style={{ animationDelay: `${i * 0.03}s` }}
            >
              <div className="flex items-center gap-2 mb-3">
                <span className={cn("text-[10px] font-medium uppercase tracking-wider px-2 py-0.5 rounded-full border", style.color)}>
                  {style.label}
                </span>
                {p.package_registry && <RegistryBadge registry={p.package_registry} />}
                <span className="text-[11px] text-muted-foreground/50 ml-auto tabular-nums">
                  {p.vote_count} vote{p.vote_count !== 1 ? "s" : ""}
                </span>
              </div>

              <h3 className="text-[14px] font-medium text-foreground/80 group-hover:text-foreground transition-colors mb-2 line-clamp-2">
                {p.title}
              </h3>

              <div className="flex items-center gap-2 text-[11px] text-muted-foreground/50">
                <span>{p.package_name}</span>
                <span>·</span>
                <span>{p.vuln_title?.slice(0, 40)}{(p.vuln_title?.length || 0) > 40 ? "..." : ""}</span>
              </div>

              <div className="flex items-center gap-1 mt-3">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div
                    key={i}
                    className={cn(
                      "h-1 w-4 rounded-full",
                      i < p.difficulty ? "bg-foreground/20" : "bg-foreground/[0.05]"
                    )}
                  />
                ))}
                <span className="text-[10px] text-muted-foreground/30 ml-1">difficulty</span>
              </div>
            </Link>
          );
        })}
      </div>

      {puzzles.length === 0 && !loading && (
        <div className="rounded-2xl glass p-12 text-center text-muted-foreground/50 text-sm">
          No validation puzzles yet. Run vulnerability scans to generate them.
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between animate-fade-in">
          <p className="text-[12px] text-muted-foreground/50 tabular-nums">
            {(page - 1) * PER_PAGE + 1}–{Math.min(page * PER_PAGE, total)} of {total}
          </p>
          <div className="flex items-center gap-1">
            <button onClick={() => setPage(page - 1)} disabled={page === 1} className="px-2.5 py-1.5 rounded-lg text-[12px] text-muted-foreground/70 hover:text-foreground/60 hover:bg-foreground/[0.03] disabled:opacity-20 disabled:cursor-not-allowed transition-all">Prev</button>
            <button onClick={() => setPage(page + 1)} disabled={page === totalPages} className="px-2.5 py-1.5 rounded-lg text-[12px] text-muted-foreground/70 hover:text-foreground/60 hover:bg-foreground/[0.03] disabled:opacity-20 disabled:cursor-not-allowed transition-all">Next</button>
          </div>
        </div>
      )}
    </div>
  );
}
