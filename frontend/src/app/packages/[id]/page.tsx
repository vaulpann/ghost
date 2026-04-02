"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getPackage, getVersions } from "@/lib/api";
import type { Package, Version } from "@/lib/types";
import { RegistryBadge } from "@/components/analysis/registry-badge";
import { RiskBadge } from "@/components/analysis/risk-badge";
import { formatNumber, timeAgo } from "@/lib/utils";

export default function PackageDetailPage() {
  const params = useParams();
  const [pkg, setPkg] = useState<Package | null>(null);
  const [versions, setVersions] = useState<Version[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [pkgData, versionsData] = await Promise.all([
          getPackage(params.id as string),
          getVersions(params.id as string),
        ]);
        setPkg(pkgData);
        setVersions(versionsData.items);
      } catch (e) {
        console.error("Failed to load package:", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [params.id]);

  if (loading || !pkg) {
    return <div className="text-muted-foreground/50 text-sm">Loading...</div>;
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="animate-fade-in">
        <Link href="/packages" className="text-[12px] text-muted-foreground/60 hover:text-foreground/50 transition-colors">
          &larr; Packages
        </Link>
        <div className="flex items-center gap-2 sm:gap-3 mt-3 mb-2 flex-wrap">
          <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight gradient-text">{pkg.name}</h1>
          <RegistryBadge registry={pkg.registry} />
        </div>
        {pkg.description && (
          <p className="text-sm text-muted-foreground/80">{pkg.description}</p>
        )}
        <div className="flex flex-wrap gap-4 sm:gap-8 mt-4">
          {[
            { label: "Version", value: pkg.latest_known_version || "—" },
            { label: "Downloads", value: `${formatNumber(pkg.weekly_downloads)}/wk` },
            { label: "Priority", value: pkg.priority },
          ].map((item) => (
            <div key={item.label}>
              <p className="text-[10px] text-muted-foreground/50 uppercase tracking-wider">{item.label}</p>
              <p className="text-sm text-foreground/70 font-mono mt-0.5">{item.value}</p>
            </div>
          ))}
          {pkg.repository_url && (
            <div>
              <p className="text-[10px] text-muted-foreground/50 uppercase tracking-wider">Repository</p>
              <a
                href={pkg.repository_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-emerald-400/70 hover:text-emerald-400 transition-colors mt-0.5 block"
              >
                View &rarr;
              </a>
            </div>
          )}
        </div>
      </div>

      {/* Versions */}
      <div className="animate-fade-in animate-fade-in-delay-1">
        <h2 className="text-[15px] font-medium text-foreground/60 mb-4">Version History</h2>
        {versions.length === 0 ? (
          <div className="rounded-2xl glass p-12 text-center text-muted-foreground/50 text-sm">
            No versions detected yet.
          </div>
        ) : (
          <div className="rounded-2xl glass overflow-hidden overflow-x-auto">
            <table className="w-full text-[13px] min-w-[500px]">
              <thead>
                <tr className="border-b border-border">
                  <th className="px-5 py-3.5 text-left text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">Version</th>
                  <th className="px-5 py-3.5 text-left text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">Previous</th>
                  <th className="px-5 py-3.5 text-left text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">Diff</th>
                  <th className="px-5 py-3.5 text-left text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">Risk</th>
                  <th className="px-5 py-3.5 text-left text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">Detected</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50">
                {versions.map((v) => (
                  <tr key={v.id} className="hover:bg-foreground/[0.02] transition-colors">
                    <td className="px-5 py-3.5 font-mono text-[12px] text-foreground/70 font-medium">{v.version_string}</td>
                    <td className="px-5 py-3.5 font-mono text-[12px] text-muted-foreground/70">{v.previous_version_string || "—"}</td>
                    <td className="px-5 py-3.5 text-[12px] text-muted-foreground/60">
                      {v.diff_file_count ? `${v.diff_file_count} files` : "—"}
                    </td>
                    <td className="px-5 py-3.5">
                      {v.has_analysis ? (
                        <RiskBadge level={v.risk_level} score={v.risk_score} size="sm" />
                      ) : (
                        <span className="text-[11px] text-muted-foreground/30">—</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-[12px] text-muted-foreground/60">{timeAgo(v.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
