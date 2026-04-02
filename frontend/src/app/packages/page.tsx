"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getPackages } from "@/lib/api";
import type { Package } from "@/lib/types";
import { RegistryBadge } from "@/components/analysis/registry-badge";
import { cn, formatNumber, timeAgo } from "@/lib/utils";

const PER_PAGE = 20;

export default function PackagesPage() {
  const [packages, setPackages] = useState<Package[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [registryFilter, setRegistryFilter] = useState("");

  useEffect(() => {
    setPage(1);
  }, [search, registryFilter]);

  useEffect(() => {
    async function load() {
      try {
        const params = new URLSearchParams();
        if (search) params.set("search", search);
        if (registryFilter) params.set("registry", registryFilter);
        params.set("page", String(page));
        params.set("per_page", String(PER_PAGE));
        const data = await getPackages(params.toString());
        setPackages(data.items);
        setTotal(data.total);
      } catch (e) {
        console.error("Failed to fetch packages:", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [search, registryFilter, page]);

  const totalPages = Math.ceil(total / PER_PAGE);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="animate-fade-in">
        <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight gradient-text">Watchlist</h1>
        <p className="text-xs sm:text-sm text-white/30 mt-1">{total} packages under active surveillance</p>
      </div>

      {/* Filters */}
      <div className="flex gap-3 animate-fade-in animate-fade-in-delay-1">
        <div className="relative flex-1">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search packages..."
            className="w-full rounded-xl glass border-0 bg-white/[0.03] px-4 py-2.5 text-[13px] text-white/80 placeholder:text-white/20 focus:outline-none focus:ring-1 focus:ring-white/10 transition-all"
          />
        </div>
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

      {/* Table */}
      <div className="rounded-2xl glass overflow-hidden overflow-x-auto animate-fade-in animate-fade-in-delay-2">
        <table className="w-full text-[13px]">
          <thead>
            <tr className="border-b border-white/[0.04]">
              <th className="px-5 py-3.5 text-left text-[11px] font-medium text-white/25 uppercase tracking-wider">Package</th>
              <th className="px-5 py-3.5 text-left text-[11px] font-medium text-white/25 uppercase tracking-wider">Registry</th>
              <th className="px-5 py-3.5 text-left text-[11px] font-medium text-white/25 uppercase tracking-wider">Version</th>
              <th className="px-5 py-3.5 text-left text-[11px] font-medium text-white/25 uppercase tracking-wider">Downloads</th>
              <th className="px-5 py-3.5 text-left text-[11px] font-medium text-white/25 uppercase tracking-wider">Last Checked</th>
              <th className="px-5 py-3.5 text-right text-[11px] font-medium text-white/25 uppercase tracking-wider">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.03]">
            {packages.map((pkg, i) => (
              <tr
                key={pkg.id}
                className="group hover:bg-white/[0.02] transition-colors animate-fade-in"
                style={{ animationDelay: `${i * 0.02}s` }}
              >
                <td className="px-5 py-3.5">
                  <Link
                    href={`/packages/${pkg.id}`}
                    className="font-medium text-white/80 group-hover:text-white transition-colors"
                  >
                    {pkg.name}
                  </Link>
                  {pkg.description && (
                    <p className="text-[11px] text-white/20 truncate max-w-xs mt-0.5">
                      {pkg.description}
                    </p>
                  )}
                </td>
                <td className="px-5 py-3.5">
                  <RegistryBadge registry={pkg.registry} />
                </td>
                <td className="px-5 py-3.5 font-mono text-[12px] text-white/40">
                  {pkg.latest_known_version || "—"}
                </td>
                <td className="px-5 py-3.5 text-[12px] text-white/25 tabular-nums">
                  {formatNumber(pkg.weekly_downloads)}
                </td>
                <td className="px-5 py-3.5 text-[12px] text-white/25">
                  {pkg.last_checked_at ? timeAgo(pkg.last_checked_at) : "—"}
                </td>
                <td className="px-5 py-3.5 text-right">
                  <span
                    className={cn(
                      "inline-flex h-1.5 w-1.5 rounded-full",
                      pkg.monitoring_enabled ? "bg-emerald-400/60" : "bg-white/10"
                    )}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {packages.length === 0 && !loading && (
          <div className="p-12 text-center text-white/20 text-sm">
            No packages found.
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between animate-fade-in">
          <p className="text-[12px] text-white/20 tabular-nums">
            {(page - 1) * PER_PAGE + 1}–{Math.min(page * PER_PAGE, total)} of {total}
          </p>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(1)}
              disabled={page === 1}
              className="px-2.5 py-1.5 rounded-lg text-[12px] text-white/30 hover:text-white/60 hover:bg-white/[0.03] disabled:opacity-20 disabled:cursor-not-allowed transition-all"
            >
              First
            </button>
            <button
              onClick={() => setPage(page - 1)}
              disabled={page === 1}
              className="px-2.5 py-1.5 rounded-lg text-[12px] text-white/30 hover:text-white/60 hover:bg-white/[0.03] disabled:opacity-20 disabled:cursor-not-allowed transition-all"
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
                      ? "bg-white/[0.08] text-white/90"
                      : "text-white/30 hover:text-white/60 hover:bg-white/[0.03]"
                  )}
                >
                  {p}
                </button>
              );
            })}
            <button
              onClick={() => setPage(page + 1)}
              disabled={page === totalPages}
              className="px-2.5 py-1.5 rounded-lg text-[12px] text-white/30 hover:text-white/60 hover:bg-white/[0.03] disabled:opacity-20 disabled:cursor-not-allowed transition-all"
            >
              Next
            </button>
            <button
              onClick={() => setPage(totalPages)}
              disabled={page === totalPages}
              className="px-2.5 py-1.5 rounded-lg text-[12px] text-white/30 hover:text-white/60 hover:bg-white/[0.03] disabled:opacity-20 disabled:cursor-not-allowed transition-all"
            >
              Last
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
