"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getAnalyses } from "@/lib/api";
import type { Analysis } from "@/lib/types";
import { RegistryBadge } from "@/components/analysis/registry-badge";
import { RiskBadge } from "@/components/analysis/risk-badge";
import { timeAgo } from "@/lib/utils";

export default function AnalysesPage() {
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [riskFilter, setRiskFilter] = useState("");
  const [registryFilter, setRegistryFilter] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const params = new URLSearchParams();
        if (riskFilter) params.set("risk_level", riskFilter);
        if (registryFilter) params.set("registry", registryFilter);
        params.set("per_page", "100");
        const data = await getAnalyses(params.toString());
        setAnalyses(data.items);
        setTotal(data.total);
      } catch (e) {
        console.error("Failed to fetch analyses:", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [riskFilter, registryFilter]);

  return (
    <div className="space-y-6">
      <div className="animate-fade-in">
        <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight gradient-text">Analyses</h1>
        <p className="text-xs sm:text-sm text-white/30 mt-1">{total} security scans completed</p>
      </div>

      {/* Filters */}
      <div className="flex gap-3 animate-fade-in animate-fade-in-delay-1">
        <select
          value={riskFilter}
          onChange={(e) => setRiskFilter(e.target.value)}
          className="rounded-xl glass border-0 bg-white/[0.03] px-4 py-2.5 text-[13px] text-white/60 focus:outline-none focus:ring-1 focus:ring-white/10 appearance-none cursor-pointer"
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
          className="rounded-xl glass border-0 bg-white/[0.03] px-4 py-2.5 text-[13px] text-white/60 focus:outline-none focus:ring-1 focus:ring-white/10 appearance-none cursor-pointer"
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
                <span className="font-medium text-[13px] text-white/80 group-hover:text-white transition-colors">
                  {a.package_name}
                </span>
                {a.package_registry && <RegistryBadge registry={a.package_registry} />}
                <span className="text-[11px] text-white/20 font-mono">
                  {a.previous_version_string} &rarr; {a.version_string}
                </span>
              </div>
              <p className="text-[12px] text-white/30 truncate">
                {a.summary || `Status: ${a.status}`}
              </p>
            </div>
            <div className="flex items-center gap-4 shrink-0">
              {a.finding_count > 0 && (
                <span className="text-[11px] text-white/20 tabular-nums">
                  {a.finding_count} findings
                </span>
              )}
              {a.total_cost_usd !== null && (
                <span className="text-[11px] text-white/15 font-mono tabular-nums">
                  ${a.total_cost_usd.toFixed(4)}
                </span>
              )}
              <RiskBadge level={a.risk_level} score={a.risk_score} />
              <span className="text-[11px] text-white/20 w-14 text-right tabular-nums">
                {timeAgo(a.created_at)}
              </span>
            </div>
          </Link>
        ))}
        {analyses.length === 0 && !loading && (
          <div className="rounded-2xl glass p-12 text-center text-white/20 text-sm">
            No analyses yet.
          </div>
        )}
      </div>
    </div>
  );
}
