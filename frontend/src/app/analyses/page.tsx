"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getAnalyses, getStats } from "@/lib/api";
import type { Analysis, Stats } from "@/lib/types";
import { RegistryBadge } from "@/components/analysis/registry-badge";
import { RiskBadge } from "@/components/analysis/risk-badge";
import { cn, timeAgo, formatNumber } from "@/lib/utils";

const PER_PAGE = 20;

export default function AnalysesPage() {
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [riskFilter, setRiskFilter] = useState("");
  const [registryFilter, setRegistryFilter] = useState("");

  useEffect(() => {
    setPage(1);
  }, [riskFilter, registryFilter]);

  useEffect(() => {
    async function load() {
      try {
        const params = new URLSearchParams();
        if (riskFilter) params.set("risk_level", riskFilter);
        if (registryFilter) params.set("registry", registryFilter);
        params.set("page", String(page));
        params.set("per_page", String(PER_PAGE));
        const [data, statsData] = await Promise.all([
          getAnalyses(params.toString()),
          page === 1 ? getStats() : Promise.resolve(null),
        ]);
        setAnalyses(data.items);
        setTotal(data.total);
        if (statsData) setStats(statsData);
      } catch (e) {
        console.error("Failed to fetch analyses:", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [riskFilter, registryFilter, page]);

  const totalPages = Math.ceil(total / PER_PAGE);

  return (
    <div className="space-y-6">
      <div className="animate-fade-in">
        <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight gradient-text">Analyses</h1>
        <p className="text-xs sm:text-sm text-muted-foreground/70 mt-1">
          Live monitoring across npm, PyPI, and GitHub
        </p>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 animate-fade-in animate-fade-in-delay-1">
          <StatCard label="Monitored" value={stats.total_packages} />
          <StatCard label="Analyses" value={stats.total_analyses} />
          <StatCard
            label="Flagged"
            value={stats.flagged_count}
            accent={stats.flagged_count > 0 ? "yellow" : undefined}
          />
          <StatCard
            label="Critical"
            value={stats.critical_count}
            accent={stats.critical_count > 0 ? "red" : undefined}
          />
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 animate-fade-in animate-fade-in-delay-2">
        <select
          value={riskFilter}
          onChange={(e) => setRiskFilter(e.target.value)}
          className="rounded-xl glass border-0 bg-foreground/[0.03] px-4 py-2.5 text-[13px] text-foreground/60 focus:outline-none focus:ring-1 focus:ring-ring/20 appearance-none cursor-pointer"
        >
          <option value="">All risk levels</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
          <option value="none">None</option>
        </select>
        <select
          value={registryFilter}
          onChange={(e) => setRegistryFilter(e.target.value)}
          className="rounded-xl glass border-0 bg-foreground/[0.03] px-4 py-2.5 text-[13px] text-foreground/60 focus:outline-none focus:ring-1 focus:ring-ring/20 appearance-none cursor-pointer"
        >
          <option value="">All registries</option>
          <option value="npm">npm</option>
          <option value="pypi">PyPI</option>
          <option value="github">GitHub</option>
        </select>
      </div>

      {/* List */}
      <div className="space-y-2 animate-fade-in animate-fade-in-delay-2">
        {analyses.map((a, i) => (
          <Link
            key={a.id}
            href={`/analyses/${a.id}`}
            className="group flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 rounded-xl glass glass-hover p-4 animate-fade-in"
            style={{ animationDelay: `${i * 0.03}s` }}
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2.5 mb-1.5">
                <span className="font-medium text-[13px] text-foreground/80 group-hover:text-foreground transition-colors">
                  {a.package_name}
                </span>
                {a.package_registry && <RegistryBadge registry={a.package_registry} />}
                <span className="text-[11px] text-muted-foreground/50 font-mono">
                  {a.previous_version_string} &rarr; {a.version_string}
                </span>
              </div>
              <p className="text-[12px] text-muted-foreground/70 truncate">
                {a.summary || `Status: ${a.status}`}
              </p>
            </div>
            <div className="flex items-center gap-4 shrink-0">
              {a.finding_count > 0 && (
                <span className="text-[11px] text-muted-foreground/50 tabular-nums">
                  {a.finding_count} findings
                </span>
              )}
              {a.total_cost_usd !== null && (
                <span className="text-[11px] text-muted-foreground/30 font-mono tabular-nums">
                  ${a.total_cost_usd.toFixed(4)}
                </span>
              )}
              <RiskBadge level={a.risk_level} score={a.risk_score} />
              <span className="text-[11px] text-muted-foreground/50 w-14 text-right tabular-nums">
                {timeAgo(a.created_at)}
              </span>
            </div>
          </Link>
        ))}
        {analyses.length === 0 && !loading && (
          <div className="rounded-2xl glass p-12 text-center text-muted-foreground/50 text-sm">
            No analyses yet.
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between animate-fade-in">
          <p className="text-[12px] text-muted-foreground/50 tabular-nums">
            {(page - 1) * PER_PAGE + 1}–{Math.min(page * PER_PAGE, total)} of {total}
          </p>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(1)}
              disabled={page === 1}
              className="px-2.5 py-1.5 rounded-lg text-[12px] text-muted-foreground/70 hover:text-foreground/60 hover:bg-foreground/[0.03] disabled:opacity-20 disabled:cursor-not-allowed transition-all"
            >
              First
            </button>
            <button
              onClick={() => setPage(page - 1)}
              disabled={page === 1}
              className="px-2.5 py-1.5 rounded-lg text-[12px] text-muted-foreground/70 hover:text-foreground/60 hover:bg-foreground/[0.03] disabled:opacity-20 disabled:cursor-not-allowed transition-all"
            >
              Prev
            </button>
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              let p: number;
              if (totalPages <= 5) {
                p = i + 1;
              } else if (page <= 3) {
                p = i + 1;
              } else if (page >= totalPages - 2) {
                p = totalPages - 4 + i;
              } else {
                p = page - 2 + i;
              }
              return (
                <button
                  key={p}
                  onClick={() => setPage(p)}
                  className={cn(
                    "w-8 h-8 rounded-lg text-[12px] font-medium transition-all",
                    p === page
                      ? "bg-foreground/[0.08] text-foreground"
                      : "text-muted-foreground/70 hover:text-foreground/60 hover:bg-foreground/[0.03]"
                  )}
                >
                  {p}
                </button>
              );
            })}
            <button
              onClick={() => setPage(page + 1)}
              disabled={page === totalPages}
              className="px-2.5 py-1.5 rounded-lg text-[12px] text-muted-foreground/70 hover:text-foreground/60 hover:bg-foreground/[0.03] disabled:opacity-20 disabled:cursor-not-allowed transition-all"
            >
              Next
            </button>
            <button
              onClick={() => setPage(totalPages)}
              disabled={page === totalPages}
              className="px-2.5 py-1.5 rounded-lg text-[12px] text-muted-foreground/70 hover:text-foreground/60 hover:bg-foreground/[0.03] disabled:opacity-20 disabled:cursor-not-allowed transition-all"
            >
              Last
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: number | string;
  accent?: "yellow" | "red";
}) {
  return (
    <div
      className={cn(
        "rounded-2xl glass p-5",
        accent === "red" && "glow-red border-red-500/10",
        accent === "yellow" && "glow-yellow border-yellow-500/10"
      )}
    >
      <p className="text-[11px] text-muted-foreground/60 uppercase tracking-wider font-medium">{label}</p>
      <p
        className={cn(
          "text-3xl font-semibold mt-2 tabular-nums",
          accent === "red" ? "text-red-400" : accent === "yellow" ? "text-yellow-400" : "stat-number"
        )}
      >
        {typeof value === "number" ? formatNumber(value) : value}
      </p>
    </div>
  );
}
