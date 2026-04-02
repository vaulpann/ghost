"use client";

import { useEffect, useState } from "react";
import { getFeed, getStats, triggerPoll } from "@/lib/api";
import type { FeedItem as FeedItemType, Stats } from "@/lib/types";
import { FeedItem } from "@/components/feed/feed-item";
import { cn, formatNumber } from "@/lib/utils";

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [feed, setFeed] = useState<FeedItemType[]>([]);
  const [loading, setLoading] = useState(true);
  const [polling, setPolling] = useState(false);

  const fetchData = async () => {
    try {
      const [statsData, feedData] = await Promise.all([getStats(), getFeed(50)]);
      setStats(statsData);
      setFeed(feedData.items);
    } catch (e) {
      console.error("Failed to fetch dashboard data:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const handlePoll = async () => {
    setPolling(true);
    try {
      await triggerPoll();
      await fetchData();
    } catch (e) {
      console.error("Poll failed:", e);
    } finally {
      setPolling(false);
    }
  };

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
          {feed.length > 0 && (
            <span className="text-[11px] text-muted-foreground/50 tabular-nums">
              {feed.length} analyses
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
