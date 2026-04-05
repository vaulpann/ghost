"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getVulnerability } from "@/lib/api";
import type { Vulnerability } from "@/lib/types";
import { RiskBadge } from "@/components/analysis/risk-badge";
import { RegistryBadge } from "@/components/analysis/registry-badge";
import { cn } from "@/lib/utils";

export default function VulnerabilityDetailPage() {
  const params = useParams();
  const [vuln, setVuln] = useState<Vulnerability | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"details" | "poc" | "code" | "scan">("details");

  useEffect(() => {
    async function load() {
      try {
        const data = await getVulnerability(params.id as string);
        setVuln(data);
      } catch (e) {
        console.error("Failed to load vulnerability:", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [params.id]);

  if (loading || !vuln) {
    return <div className="text-muted-foreground/50 text-sm">Loading...</div>;
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="animate-fade-in">
        <Link href="/vulnerabilities" className="text-[12px] text-muted-foreground/60 hover:text-foreground/50 transition-colors">
          &larr; Vulnerabilities
        </Link>
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mt-3">
          <div>
            <div className="flex items-center gap-2 sm:gap-3 mb-2 flex-wrap">
              <RiskBadge level={vuln.severity} size="lg" />
              <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight gradient-text">
                {vuln.title}
              </h1>
            </div>
            <div className="flex items-center gap-3 text-sm text-muted-foreground/70">
              <span>{vuln.package_name}</span>
              {vuln.package_registry && <RegistryBadge registry={vuln.package_registry} />}
              {vuln.version_string && <span className="font-mono text-[12px]">v{vuln.version_string}</span>}
              {vuln.cwe_id && (
                <span className="font-mono text-[12px] text-muted-foreground/50">{vuln.cwe_id}</span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-4">
            {vuln.cvss_score && (
              <div className="text-center">
                <p className={cn(
                  "text-2xl font-bold tabular-nums",
                  vuln.cvss_score >= 9 ? "text-red-400" : vuln.cvss_score >= 7 ? "text-orange-400" : "text-yellow-400"
                )}>
                  {vuln.cvss_score.toFixed(1)}
                </p>
                <p className="text-[10px] text-muted-foreground/50 uppercase">CVSS</p>
              </div>
            )}
            <div className="text-center">
              <p className="text-2xl font-bold tabular-nums text-foreground/80">{(vuln.confidence * 100).toFixed(0)}%</p>
              <p className="text-[10px] text-muted-foreground/50 uppercase">Confidence</p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="animate-fade-in animate-fade-in-delay-1">
        <div className="flex gap-1 p-1 rounded-xl bg-foreground/[0.03] w-fit overflow-x-auto">
          {(["details", "poc", "code", "scan"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                "px-4 py-1.5 rounded-lg text-[12px] font-medium capitalize transition-all duration-200",
                activeTab === tab
                  ? "bg-foreground/[0.08] text-foreground shadow-sm"
                  : "text-muted-foreground/70 hover:text-foreground/50"
              )}
            >
              {tab === "poc" ? "PoC" : tab}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="animate-fade-in animate-fade-in-delay-2">
        {activeTab === "details" && (
          <div className="space-y-4">
            <div className="rounded-2xl glass p-6">
              <h3 className="text-[11px] text-muted-foreground/60 uppercase tracking-wider font-medium mb-3">Description</h3>
              <p className="text-[14px] text-foreground/60 leading-relaxed">{vuln.description}</p>
            </div>
            {vuln.attack_vector && (
              <div className="rounded-2xl glass p-6">
                <h3 className="text-[11px] text-muted-foreground/60 uppercase tracking-wider font-medium mb-3">Attack Vector</h3>
                <p className="text-[13px] text-foreground/50 leading-relaxed">{vuln.attack_vector}</p>
              </div>
            )}
            {vuln.impact && (
              <div className="rounded-2xl glass p-6">
                <h3 className="text-[11px] text-muted-foreground/60 uppercase tracking-wider font-medium mb-3">Impact</h3>
                <p className="text-[13px] text-foreground/50 leading-relaxed">{vuln.impact}</p>
              </div>
            )}
            {vuln.remediation && (
              <div className="rounded-2xl glass p-6 border-emerald-500/10">
                <h3 className="text-[11px] text-emerald-400/60 uppercase tracking-wider font-medium mb-3">Remediation</h3>
                <p className="text-[13px] text-foreground/50 leading-relaxed">{vuln.remediation}</p>
              </div>
            )}
            <div className="flex gap-4 text-[12px] text-muted-foreground/50">
              <span>Category: <span className="text-foreground/60">{vuln.category}{vuln.subcategory ? ` / ${vuln.subcategory}` : ""}</span></span>
              {vuln.file_path && <span>File: <span className="text-foreground/60 font-mono">{vuln.file_path}:{vuln.line_start}</span></span>}
            </div>
          </div>
        )}

        {activeTab === "poc" && (
          <div className="space-y-4">
            {vuln.poc_code ? (
              <>
                {vuln.poc_description && (
                  <div className="rounded-2xl glass p-6">
                    <h3 className="text-[11px] text-muted-foreground/60 uppercase tracking-wider font-medium mb-3">How to reproduce</h3>
                    <p className="text-[13px] text-foreground/50 leading-relaxed">{vuln.poc_description}</p>
                  </div>
                )}
                <div className="rounded-2xl glass overflow-hidden">
                  <div className="px-5 py-3 border-b border-border">
                    <span className="text-[11px] text-muted-foreground/60 uppercase tracking-wider font-medium">Proof of Concept</span>
                  </div>
                  <pre className="p-5 text-[12px] font-mono text-foreground/60 overflow-x-auto leading-relaxed">
                    {vuln.poc_code}
                  </pre>
                </div>
              </>
            ) : (
              <div className="rounded-2xl glass p-12 text-center text-muted-foreground/50 text-sm">
                No proof-of-concept available for this vulnerability.
              </div>
            )}
          </div>
        )}

        {activeTab === "code" && (
          <div className="rounded-2xl glass overflow-hidden">
            {vuln.code_snippet ? (
              <>
                <div className="px-5 py-3 border-b border-border flex items-center justify-between">
                  <span className="text-[12px] text-muted-foreground/70 font-mono">{vuln.file_path}</span>
                  {vuln.line_start && (
                    <span className="text-[11px] text-muted-foreground/50">
                      Lines {vuln.line_start}–{vuln.line_end || vuln.line_start}
                    </span>
                  )}
                </div>
                <pre className="p-5 text-[12px] font-mono text-foreground/60 overflow-x-auto leading-relaxed">
                  {vuln.code_snippet}
                </pre>
              </>
            ) : (
              <div className="p-12 text-center text-muted-foreground/50 text-sm">
                No code snippet available.
              </div>
            )}
          </div>
        )}

        {activeTab === "scan" && (
          <div className="rounded-2xl glass p-6 space-y-3">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-[12px]">
              <div>
                <p className="text-muted-foreground/50">Scan ID</p>
                <p className="text-foreground/60 font-mono text-[11px] mt-1 truncate">{vuln.scan_id}</p>
              </div>
              <div>
                <p className="text-muted-foreground/50">Package</p>
                <p className="text-foreground/60 mt-1">{vuln.package_name}</p>
              </div>
              <div>
                <p className="text-muted-foreground/50">Version</p>
                <p className="text-foreground/60 font-mono mt-1">{vuln.version_string}</p>
              </div>
              <div>
                <p className="text-muted-foreground/50">Validated</p>
                <p className="text-foreground/60 mt-1">{vuln.validated ? "Yes" : "No"}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
