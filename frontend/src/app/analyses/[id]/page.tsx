"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getAnalysis, getFindings, getVersionDiff } from "@/lib/api";
import type { Analysis, Finding } from "@/lib/types";
import Markdown from "react-markdown";
import { RiskBadge } from "@/components/analysis/risk-badge";
import { RegistryBadge } from "@/components/analysis/registry-badge";
import { cn } from "@/lib/utils";

export default function AnalysisDetailPage() {
  const params = useParams();
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [diff, setDiff] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"report" | "findings" | "diff" | "raw">("report");

  useEffect(() => {
    async function load() {
      try {
        const analysisData = await getAnalysis(params.id as string);
        setAnalysis(analysisData);
        const [findingsData, diffData] = await Promise.all([
          getFindings(params.id as string),
          getVersionDiff(analysisData.version_id),
        ]);
        setFindings(findingsData);
        setDiff(diffData.diff);
      } catch (e) {
        console.error("Failed to load analysis:", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [params.id]);

  if (loading || !analysis) {
    return <div className="text-white/20 text-sm">Loading analysis...</div>;
  }

  const synthesisResult = analysis.synthesis_result as any;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="animate-fade-in">
        <Link href="/analyses" className="text-[12px] text-white/25 hover:text-white/50 transition-colors">
          &larr; Analyses
        </Link>
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mt-3">
          <div>
            <div className="flex items-center gap-2 sm:gap-3 mb-2 flex-wrap">
              <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight gradient-text">
                {analysis.package_name}
              </h1>
              {analysis.package_registry && <RegistryBadge registry={analysis.package_registry} />}
              <RiskBadge level={analysis.risk_level} score={analysis.risk_score} size="lg" />
            </div>
            <p className="text-xs sm:text-sm text-white/30 font-mono">
              {analysis.previous_version_string} &rarr; {analysis.version_string}
            </p>
          </div>
          <div className="flex sm:flex-col gap-3 sm:gap-1 sm:text-right text-[11px] text-white/20">
            <p>Status: <span className="text-white/50">{analysis.status}</span></p>
            {analysis.total_cost_usd !== null && (
              <p>Cost: <span className="text-white/50 font-mono">${analysis.total_cost_usd.toFixed(4)}</span></p>
            )}
            <p>{analysis.finding_count} finding{analysis.finding_count !== 1 ? "s" : ""}</p>
          </div>
        </div>
      </div>

      {/* Summary card */}
      {analysis.summary && (
        <div className="rounded-2xl glass p-6 animate-fade-in animate-fade-in-delay-1">
          <p className="text-[11px] text-white/25 uppercase tracking-wider font-medium mb-3">Executive Summary</p>
          <p className="text-[14px] text-white/60 leading-relaxed">{analysis.summary}</p>
          {synthesisResult?.recommended_action && (
            <div className="mt-4 pt-4 border-t border-white/[0.04]">
              <p className="text-[11px] text-white/25 uppercase tracking-wider font-medium mb-1">Recommended Action</p>
              <p className="text-[13px] text-white/50">{synthesisResult.recommended_action.replace(/_/g, " ")}</p>
            </div>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="animate-fade-in animate-fade-in-delay-2">
        <div className="flex gap-1 p-1 rounded-xl bg-white/[0.03] w-fit overflow-x-auto">
          {(["report", "findings", "diff", "raw"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                "px-4 py-1.5 rounded-lg text-[12px] font-medium capitalize transition-all duration-200",
                activeTab === tab
                  ? "bg-white/[0.08] text-white/90 shadow-sm"
                  : "text-white/30 hover:text-white/50"
              )}
            >
              {tab}
              {tab === "findings" && findings.length > 0 && (
                <span className="ml-1.5 text-[10px] text-white/25">{findings.length}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="animate-fade-in animate-fade-in-delay-3">
        {activeTab === "report" && (
          <div className="space-y-4">
            {synthesisResult?.detailed_report ? (
              <div className="rounded-2xl glass p-8 prose-ghost">
                <Markdown
                  components={{
                    h1: ({ children }) => <h1 className="text-xl font-semibold text-white/90 mb-4 mt-0">{children}</h1>,
                    h2: ({ children }) => <h2 className="text-lg font-semibold text-white/85 mb-3 mt-8 first:mt-0 pb-2 border-b border-white/[0.05]">{children}</h2>,
                    h3: ({ children }) => <h3 className="text-[15px] font-medium text-white/75 mb-2 mt-6">{children}</h3>,
                    p: ({ children }) => <p className="text-[13px] text-white/50 leading-relaxed mb-4">{children}</p>,
                    ul: ({ children }) => <ul className="space-y-2 mb-4 ml-1">{children}</ul>,
                    ol: ({ children }) => <ol className="space-y-2 mb-4 ml-1 list-decimal list-inside">{children}</ol>,
                    li: ({ children }) => (
                      <li className="text-[13px] text-white/50 leading-relaxed flex gap-2">
                        <span className="text-emerald-400/40 mt-1.5 shrink-0">&#8226;</span>
                        <span>{children}</span>
                      </li>
                    ),
                    strong: ({ children }) => <strong className="text-white/70 font-medium">{children}</strong>,
                    em: ({ children }) => <em className="text-white/60 italic">{children}</em>,
                    code: ({ children }) => (
                      <code className="text-[12px] font-mono bg-white/[0.04] text-emerald-400/70 px-1.5 py-0.5 rounded-md border border-white/[0.04]">
                        {children}
                      </code>
                    ),
                    pre: ({ children }) => (
                      <pre className="bg-white/[0.02] border border-white/[0.04] rounded-lg p-4 overflow-x-auto mb-4">
                        {children}
                      </pre>
                    ),
                    blockquote: ({ children }) => (
                      <blockquote className="border-l-2 border-emerald-500/30 pl-4 my-4 text-white/40 italic">
                        {children}
                      </blockquote>
                    ),
                    hr: () => <hr className="border-white/[0.05] my-6" />,
                    a: ({ href, children }) => (
                      <a href={href} target="_blank" rel="noopener noreferrer" className="text-emerald-400/70 hover:text-emerald-400 underline underline-offset-2 transition-colors">
                        {children}
                      </a>
                    ),
                  }}
                >
                  {synthesisResult.detailed_report}
                </Markdown>
              </div>
            ) : (
              <p className="text-white/20 text-sm">No detailed report available.</p>
            )}
          </div>
        )}

        {activeTab === "findings" && (
          <div className="space-y-3">
            {findings.length === 0 ? (
              <p className="text-white/20 text-sm">No findings.</p>
            ) : (
              findings.map((f, i) => (
                <FindingCard key={f.id} finding={f} index={i} />
              ))
            )}
          </div>
        )}

        {activeTab === "diff" && (
          <div className="rounded-2xl glass overflow-hidden">
            <pre className="p-5 text-[12px] font-mono overflow-x-auto max-h-[700px] overflow-y-auto leading-relaxed">
              {diff ? (
                diff.split("\n").map((line, i) => (
                  <div
                    key={i}
                    className={cn(
                      "px-3 -mx-1 rounded-sm",
                      line.startsWith("+") && !line.startsWith("+++") && "diff-add",
                      line.startsWith("-") && !line.startsWith("---") && "diff-remove",
                      (line.startsWith("@@") || line.startsWith("diff")) && "diff-header"
                    )}
                  >
                    <span className="text-white/15 select-none inline-block w-10 text-right mr-4 text-[10px]">
                      {i + 1}
                    </span>
                    <span className="text-white/50">{line}</span>
                  </div>
                ))
              ) : (
                <span className="text-white/20">No diff available.</span>
              )}
            </pre>
          </div>
        )}

        {activeTab === "raw" && (
          <div className="space-y-4">
            <CollapsibleJSON title="Triage Result" data={analysis.triage_result} />
            <CollapsibleJSON title="Deep Analysis Result" data={analysis.deep_analysis_result} />
            <CollapsibleJSON title="Synthesis Result" data={analysis.synthesis_result} />
          </div>
        )}
      </div>
    </div>
  );
}

function FindingCard({ finding, index }: { finding: Finding; index: number }) {
  const [expanded, setExpanded] = useState(false);

  const glowMap: Record<string, string> = {
    critical: "glow-critical border-red-500/15",
    high: "glow-red border-orange-500/15",
    medium: "glow-yellow border-yellow-500/15",
    low: "glow-green border-blue-500/15",
    info: "border-white/[0.06]",
  };

  return (
    <div
      className={cn(
        "rounded-xl glass cursor-pointer transition-all duration-200 animate-fade-in",
        glowMap[finding.severity] || glowMap.info,
        expanded && "ring-1 ring-white/[0.06]"
      )}
      style={{ animationDelay: `${index * 0.05}s` }}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-center gap-3 p-4">
        <RiskBadge level={finding.severity} size="sm" />
        <span className="text-[10px] text-white/20 font-mono uppercase tracking-wider">{finding.category}</span>
        <span className="font-medium text-[13px] text-white/70 flex-1">{finding.title}</span>
        <span className="text-[11px] text-white/20 tabular-nums">
          {(finding.confidence * 100).toFixed(0)}%
        </span>
        <svg
          className={cn("w-4 h-4 text-white/15 transition-transform", expanded && "rotate-180")}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-white/[0.03] pt-3">
          <p className="text-[13px] text-white/40 leading-relaxed">{finding.description}</p>

          {finding.evidence?.items?.map((ev, i) => (
            <div key={i} className="rounded-lg bg-white/[0.02] border border-white/[0.04] p-3">
              <p className="text-[11px] text-white/25 font-mono mb-2">
                {ev.file_path} <span className="text-white/15">L{ev.line_start}–{ev.line_end}</span>
              </p>
              <pre className="text-[12px] font-mono text-white/50 overflow-x-auto">{ev.snippet}</pre>
              <p className="text-[11px] text-white/30 mt-2">{ev.explanation}</p>
            </div>
          ))}

          {finding.mitre_technique && (
            <p className="text-[11px] text-white/20">MITRE ATT&CK: <span className="text-white/40">{finding.mitre_technique}</span></p>
          )}
          {finding.remediation && (
            <p className="text-[11px] text-white/20">Remediation: <span className="text-white/40">{finding.remediation}</span></p>
          )}
        </div>
      )}
    </div>
  );
}

function CollapsibleJSON({ title, data }: { title: string; data: any }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-xl glass overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-5 py-3.5 text-left text-[13px] font-medium text-white/50 flex items-center justify-between hover:bg-white/[0.02] transition-colors"
      >
        {title}
        <span className="text-[11px] text-white/20">{expanded ? "collapse" : "expand"}</span>
      </button>
      {expanded && (
        <pre className="border-t border-white/[0.04] p-5 text-[11px] font-mono text-white/35 overflow-x-auto max-h-96 overflow-y-auto leading-relaxed">
          {data ? JSON.stringify(data, null, 2) : "null"}
        </pre>
      )}
    </div>
  );
}
