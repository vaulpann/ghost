"use client";

import { useEffect, useState } from "react";
import { getFeed, getStats, triggerPoll } from "@/lib/api";
import type { FeedItem as FeedItemType, Stats } from "@/lib/types";
import { FeedItem } from "@/components/feed/feed-item";
import { cn, formatNumber } from "@/lib/utils";

const PER_PAGE = 20;

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [feed, setFeed] = useState<FeedItemType[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [polling, setPolling] = useState(false);

  const fetchData = async (p: number = page) => {
    try {
      const [statsData, feedData] = await Promise.all([getStats(), getFeed(p, PER_PAGE)]);
      setStats(statsData);
      setFeed(feedData.items);
      setTotal(feedData.total);
    } catch (e) {
      console.error("Failed to fetch dashboard data:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => fetchData(), 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    fetchData(page);
  }, [page]);

  const handlePoll = async () => {
    setPolling(true);
    try {
      await triggerPoll();
      await fetchData(1);
      setPage(1);
    } catch (e) {
      console.error("Poll failed:", e);
    } finally {
      setPolling(false);
    }
  };

  const totalPages = Math.ceil(total / PER_PAGE);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground/50 text-sm">Loading...</div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 animate-fade-in">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight gradient-text">
            Threat Overview
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground/70 mt-1">
            Live monitoring across npm, PyPI, and GitHub
          </p>
        </div>
        <button
          onClick={handlePoll}
          disabled={polling}
          className={cn(
            "rounded-full px-5 py-2 text-[13px] font-medium transition-all duration-300",
            "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
            "hover:bg-emerald-500/20 hover:border-emerald-500/30 hover:shadow-lg hover:shadow-emerald-500/10",
            "disabled:opacity-40 disabled:cursor-not-allowed"
          )}
        >
          {polling ? (
            <span className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Polling...
            </span>
          ) : (
            "Poll Now"
          )}
        </button>
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

      {/* Feed */}
      <div className="animate-fade-in animate-fade-in-delay-2">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[15px] font-medium text-foreground/60">Recent Activity</h2>
          {total > 0 && (
            <span className="text-[11px] text-muted-foreground/50 tabular-nums">
              {total} analyses
            </span>
          )}
        </div>

        {feed.length === 0 ? (
          <div className="rounded-2xl glass p-12 text-center">
            <div className="text-muted-foreground/30 text-sm">
              No analyses yet. Waiting for package version changes.
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            {feed.map((item, i) => (
              <FeedItem key={item.id} item={item} index={i} />
            ))}
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
