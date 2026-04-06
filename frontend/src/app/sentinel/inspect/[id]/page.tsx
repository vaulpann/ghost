"use client";

import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import Markdown from "react-markdown";
import { getSentinelScenario, submitVerdict } from "@/lib/api";
import { cn } from "@/lib/utils";

function getSessionId(): string {
  if (typeof window === "undefined") return "ssr";
  let id = localStorage.getItem("ghost-session-id");
  if (!id) { id = crypto.randomUUID(); localStorage.setItem("ghost-session-id", id); }
  return id;
}

const TOOL_META: Record<string, { name: string; icon: string; color: string; description: string }> = {
  identity: { name: "ID Badge", icon: "ID", color: "text-violet-400 bg-violet-500/10 border-violet-500/20", description: "Who made this change? Do they belong here?" },
  timing: { name: "Timeline", icon: "TL", color: "text-sky-400 bg-sky-500/10 border-sky-500/20", description: "When did this happen? Is the cadence normal?" },
  shape: { name: "X-Ray", icon: "XR", color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20", description: "What changed structurally? New dependencies?" },
  behavior: { name: "Cargo Scan", icon: "CS", color: "text-amber-400 bg-amber-500/10 border-amber-500/20", description: "What does this update actually do?" },
  flow: { name: "Flight Track", icon: "FT", color: "text-rose-400 bg-rose-500/10 border-rose-500/20", description: "Where does data move? What talks to what?" },
  context: { name: "Context", icon: "CX", color: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20", description: "Does this change make sense for this package?" },
};

const ATTACK_TYPES = [
  { value: "account_hijack", label: "Account Hijack" },
  { value: "maintainer_takeover", label: "Maintainer Takeover" },
  { value: "dependency_confusion", label: "Dependency Confusion" },
  { value: "maintainer_sabotage", label: "Maintainer Sabotage" },
  { value: "ci_cd_poisoning", label: "CI/CD Poisoning" },
  { value: "build_system_compromise", label: "Build System Compromise" },
  { value: "long_con_social_engineering", label: "Social Engineering" },
  { value: "domain_takeover", label: "Domain/Project Takeover" },
  { value: "typosquatting", label: "Typosquatting" },
  { value: "worm", label: "Self-Propagating Worm" },
];

export default function InspectPage() {
  const params = useParams();
  const [scenario, setScenario] = useState<any>(null);
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const [verdict, setVerdict] = useState<string | null>(null);
  const [confidence, setConfidence] = useState(0.7);
  const [attackGuess, setAttackGuess] = useState("");
  const [toolsUsed, setToolsUsed] = useState<Set<string>>(new Set());
  const [result, setResult] = useState<any>(null);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const startTime = useRef(Date.now());

  useEffect(() => {
    async function load() {
      try {
        const data = await getSentinelScenario(params.id as string, getSessionId());
        setScenario(data);
        startTime.current = Date.now();
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [params.id]);

  const handleToolClick = (tool: string) => {
    setActiveTool(activeTool === tool ? null : tool);
    setToolsUsed(prev => new Set([...prev, tool]));
  };

  const handleSubmit = async () => {
    if (!verdict || !scenario) return;
    setSubmitting(true);
    try {
      const res = await submitVerdict(scenario.id, {
        session_id: getSessionId(),
        verdict,
        confidence,
        attack_type_guess: verdict !== "safe" ? attackGuess : null,
        evidence_notes: { tools_checked: [...toolsUsed] },
        time_taken_secs: (Date.now() - startTime.current) / 1000,
        tools_used: [...toolsUsed],
      });
      setResult(res);
    } catch (e: any) {
      if (e.message?.includes("409")) alert("Already inspected this package.");
      else console.error(e);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading || !scenario) return <div className="text-muted-foreground/50 text-sm">Loading inspection...</div>;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="animate-fade-in">
        <Link href="/sentinel" className="text-[12px] text-muted-foreground/60 hover:text-foreground/50 transition-colors">&larr; Triage Queue</Link>
        <div className="flex items-center gap-3 mt-2">
          <h1 className="text-xl sm:text-2xl font-semibold tracking-tight gradient-text">{scenario.package_name}</h1>
          <span className="text-[11px] text-muted-foreground/50 font-mono">{scenario.registry}</span>
        </div>
        <p className="text-[13px] text-muted-foreground/60 font-mono mt-1">{scenario.version_from || "?"} &rarr; {scenario.version_to || "?"}</p>
      </div>

      {!result ? (
        <>
          {/* Tool bar */}
          <div className="flex gap-2 flex-wrap animate-fade-in animate-fade-in-delay-1">
            {scenario.available_tools.map((tool: string) => {
              const tm = TOOL_META[tool];
              const isActive = activeTool === tool;
              const isUsed = toolsUsed.has(tool);
              return (
                <button
                  key={tool}
                  onClick={() => handleToolClick(tool)}
                  className={cn(
                    "flex items-center gap-2 rounded-xl px-4 py-2.5 text-[12px] font-medium transition-all border",
                    isActive ? cn(tm.color, "ring-2 ring-offset-1 ring-offset-background") :
                    isUsed ? "bg-foreground/[0.04] text-foreground/60 border-foreground/10" :
                    "glass text-muted-foreground/50 hover:text-foreground/60"
                  )}
                >
                  <span className={cn("flex h-6 w-6 items-center justify-center rounded text-[10px] font-bold", isActive ? tm.color : "bg-foreground/[0.04]")}>
                    {tm.icon}
                  </span>
                  {tm.name}
                </button>
              );
            })}
          </div>

          {/* Active tool panel */}
          {activeTool && scenario.tools[activeTool] && (
            <div className="rounded-2xl glass p-6 animate-fade-in">
              <div className="flex items-center gap-2 mb-4">
                <span className={cn("text-[11px] font-medium uppercase tracking-wider px-2 py-0.5 rounded-full border", TOOL_META[activeTool].color)}>
                  {TOOL_META[activeTool].name}
                </span>
                <span className="text-[11px] text-muted-foreground/40">{TOOL_META[activeTool].description}</span>
              </div>
              <ToolRenderer tool={activeTool} data={scenario.tools[activeTool]} />
            </div>
          )}

          {!activeTool && (
            <div className="rounded-2xl glass p-8 text-center text-muted-foreground/40 text-sm animate-fade-in">
              Select an inspection tool above to examine this package
            </div>
          )}

          {/* Verdict section */}
          <div className="rounded-2xl glass p-6 space-y-4 animate-fade-in animate-fade-in-delay-2">
            <p className="text-[11px] text-muted-foreground/60 uppercase tracking-wider font-medium">Your Verdict</p>

            <div className="flex gap-2">
              {[
                { value: "safe", label: "Safe", color: "emerald" },
                { value: "suspicious", label: "Suspicious", color: "amber" },
                { value: "malicious", label: "Malicious", color: "rose" },
              ].map((v) => (
                <button
                  key={v.value}
                  onClick={() => setVerdict(v.value)}
                  className={cn(
                    "flex-1 rounded-xl px-4 py-3 text-[13px] font-medium transition-all border",
                    verdict === v.value
                      ? `text-${v.color}-400 bg-${v.color}-500/10 border-${v.color}-500/30 ring-2 ring-${v.color}-500/20`
                      : "glass text-muted-foreground/50 hover:text-foreground/60"
                  )}
                >
                  {v.label}
                </button>
              ))}
            </div>

            {verdict && verdict !== "safe" && (
              <select
                value={attackGuess}
                onChange={(e) => setAttackGuess(e.target.value)}
                className="w-full rounded-xl glass border-0 bg-foreground/[0.03] px-4 py-2.5 text-[13px] text-foreground/60 focus:outline-none focus:ring-1 focus:ring-ring/20"
              >
                <option value="">What type of attack? (optional, bonus points)</option>
                {ATTACK_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            )}

            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] text-muted-foreground/60">Confidence</span>
                <span className="text-[13px] text-foreground/60 font-mono">{(confidence * 100).toFixed(0)}%</span>
              </div>
              <input type="range" min={0} max={100} value={confidence * 100}
                onChange={(e) => setConfidence(Number(e.target.value) / 100)}
                className="w-full accent-emerald-500" />
            </div>

            <button
              onClick={handleSubmit}
              disabled={!verdict || submitting}
              className="w-full rounded-xl px-5 py-3 text-[14px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              {submitting ? "Submitting..." : "Submit Verdict"}
            </button>

            <p className="text-[10px] text-muted-foreground/30 text-center">
              Tools used: {toolsUsed.size}/{scenario.available_tools.length}
            </p>
          </div>
        </>
      ) : (
        /* Results */
        <div className="space-y-4 animate-fade-in">
          <div className={cn(
            "rounded-2xl p-8 text-center",
            result.is_correct ? "bg-emerald-500/10 border border-emerald-500/20" : "bg-rose-500/10 border border-rose-500/20"
          )}>
            <p className={cn("text-3xl font-bold", result.is_correct ? "text-emerald-400" : "text-rose-400")}>
              {result.is_correct ? "Correct!" : "Incorrect"}
            </p>
            <p className="text-[15px] text-foreground/60 mt-2">
              {result.was_malicious
                ? `This was a real attack: ${result.attack_name}`
                : "This was a legitimate, safe update."}
            </p>
            <p className="text-[13px] text-muted-foreground/50 mt-1 font-mono">
              {result.score > 0 ? `+${result.score}` : result.score} points
            </p>
          </div>

          {/* Player stats */}
          <div className="flex gap-4 rounded-xl glass p-4 text-[12px] text-muted-foreground/50">
            <span>Level {result.player_level}: <span className="text-foreground/70">{result.player_title}</span></span>
            <span>Score: <span className="text-foreground/70 font-mono">{result.player_total_score}</span></span>
            <span>Streak: <span className="text-foreground/70 font-mono">{result.player_streak}</span></span>
            {result.player_detection_rate && (
              <span>Detection: <span className="text-foreground/70 font-mono">{(result.player_detection_rate * 100).toFixed(0)}%</span></span>
            )}
          </div>

          {/* CVE info */}
          {(result.real_cve || result.real_cvss) && (
            <div className="flex gap-4 text-[12px] text-muted-foreground/50">
              {result.real_cve && <span>CVE: <span className="text-foreground/60 font-mono">{result.real_cve}</span></span>}
              {result.real_cvss && <span>CVSS: <span className="text-foreground/60 font-mono">{result.real_cvss}</span></span>}
            </div>
          )}

          {/* Postmortem */}
          {result.postmortem && (
            <div className="rounded-2xl glass p-6">
              <p className="text-[11px] text-muted-foreground/60 uppercase tracking-wider font-medium mb-3">Post-Mortem</p>
              <p className="text-[13px] text-foreground/60 leading-relaxed">{result.postmortem}</p>
            </div>
          )}

          <div className="flex gap-3">
            <Link href="/sentinel" className="flex-1 rounded-xl glass px-4 py-3 text-center text-[13px] text-foreground/60 hover:bg-foreground/[0.03] transition-all">
              Back to Queue
            </Link>
            <Link href="/sentinel" className="flex-1 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-4 py-3 text-center text-[13px] font-medium hover:bg-emerald-500/20 transition-all">
              Next Package
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

/** Renders the visual inspection data for each tool */
function ToolRenderer({ tool, data }: { tool: string; data: any }) {
  switch (tool) {
    case "identity":
      return (
        <div className="space-y-3">
          <div className="flex items-center gap-4">
            <div className="h-14 w-14 rounded-xl bg-foreground/[0.04] flex items-center justify-center text-2xl font-bold text-foreground/30">
              {(data.publisher || "?")[0].toUpperCase()}
            </div>
            <div>
              <p className="text-[14px] font-medium text-foreground/80">{data.publisher || "Unknown"}</p>
              <p className="text-[11px] text-muted-foreground/50">Member since {data.publisher_since || "unknown"}</p>
              <div className="flex gap-2 mt-1">
                <span className={cn("text-[10px] px-1.5 py-0.5 rounded border",
                  data.is_usual_publisher ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" : "text-rose-400 bg-rose-500/10 border-rose-500/20"
                )}>
                  {data.is_usual_publisher ? "Usual publisher" : "NOT the usual publisher"}
                </span>
                <span className="text-[10px] px-1.5 py-0.5 rounded border border-foreground/10 text-muted-foreground/50">
                  Trust: {((data.trust_score || 0) * 100).toFixed(0)}%
                </span>
                {data.account_age_days && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded border border-foreground/10 text-muted-foreground/50">
                    {data.account_age_days}d old
                  </span>
                )}
              </div>
            </div>
          </div>
          {data.flags?.length > 0 && (
            <div className="space-y-1 mt-2">
              {data.flags.map((f: string, i: number) => (
                <div key={i} className="flex items-start gap-2 text-[12px] text-amber-400/70">
                  <span className="text-amber-400 mt-0.5 shrink-0">!</span>
                  <span>{f}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      );

    case "timing":
      return (
        <div className="space-y-3">
          {data.release_history && (
            <div className="space-y-2">
              <p className="text-[11px] text-muted-foreground/40 uppercase">Release Timeline</p>
              <div className="flex items-end gap-1 h-16">
                {data.release_history.map((r: any, i: number) => {
                  const gap = r.gap_days || 0;
                  const height = Math.min(Math.max(gap / 10, 4), 64);
                  const isAnomaly = gap > 365 || gap === 0;
                  return (
                    <div key={i} className="flex flex-col items-center gap-1">
                      <div
                        className={cn("w-8 rounded-t transition-all", isAnomaly ? "bg-amber-500/40" : "bg-foreground/15")}
                        style={{ height: `${height}px` }}
                        title={`${r.version} — ${r.date} (${gap}d gap)`}
                      />
                      <span className="text-[8px] text-muted-foreground/30 font-mono truncate w-12 text-center">{r.version}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
          <div className="flex gap-2">
            <span className={cn("text-[10px] px-2 py-0.5 rounded border",
              data.cadence_normal ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" : "text-amber-400 bg-amber-500/10 border-amber-500/20"
            )}>
              {data.cadence_normal ? "Normal cadence" : "Abnormal cadence"}
            </span>
          </div>
          {data.flags?.length > 0 && (
            <div className="space-y-1">
              {data.flags.map((f: string, i: number) => (
                <div key={i} className="flex items-start gap-2 text-[12px] text-amber-400/70">
                  <span className="text-amber-400 mt-0.5 shrink-0">!</span><span>{f}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      );

    case "shape":
      return (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-[10px] text-muted-foreground/40 uppercase mb-1">Dependencies Added</p>
              {data.deps_added?.length > 0 ? data.deps_added.map((d: string, i: number) => (
                <div key={i} className="text-[12px] text-emerald-400/70 font-mono">+ {d}</div>
              )) : <p className="text-[11px] text-muted-foreground/30">None</p>}
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground/40 uppercase mb-1">Dependencies Removed</p>
              {data.deps_removed?.length > 0 ? data.deps_removed.map((d: string, i: number) => (
                <div key={i} className="text-[12px] text-rose-400/70 font-mono">- {d}</div>
              )) : <p className="text-[11px] text-muted-foreground/30">None</p>}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-[10px] text-muted-foreground/40 uppercase mb-1">Files Added</p>
              {data.files_added?.length > 0 ? data.files_added.map((f: string, i: number) => (
                <div key={i} className="text-[12px] text-emerald-400/70 font-mono">+ {f}</div>
              )) : <p className="text-[11px] text-muted-foreground/30">None</p>}
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground/40 uppercase mb-1">Files Removed</p>
              {data.files_removed?.length > 0 ? data.files_removed.map((f: string, i: number) => (
                <div key={i} className="text-[12px] text-rose-400/70 font-mono">- {f}</div>
              )) : <p className="text-[11px] text-muted-foreground/30">None</p>}
            </div>
          </div>
          {data.flags?.length > 0 && (
            <div className="space-y-1">
              {data.flags.map((f: string, i: number) => (
                <div key={i} className="flex items-start gap-2 text-[12px] text-amber-400/70">
                  <span className="text-amber-400 mt-0.5 shrink-0">!</span><span>{f}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      );

    case "behavior":
      return (
        <div className="space-y-3">
          <p className="text-[11px] text-muted-foreground/40 uppercase">Behavioral Analysis</p>
          {data.categories && (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {Object.entries(data.categories).map(([cat, level]) => (
                <div key={cat} className="flex items-center gap-2 text-[12px]">
                  <div className={cn("h-2.5 w-2.5 rounded-full",
                    level === "green" ? "bg-emerald-500" : level === "yellow" ? "bg-amber-500" : "bg-rose-500"
                  )} />
                  <span className="text-foreground/60 capitalize">{cat.replace(/_/g, " ")}</span>
                </div>
              ))}
            </div>
          )}
          {data.flags?.length > 0 && (
            <div className="space-y-1 mt-2">
              {data.flags.map((f: string, i: number) => (
                <div key={i} className="flex items-start gap-2 text-[12px] text-rose-400/70">
                  <span className="text-rose-400 mt-0.5 shrink-0">!</span><span>{f}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      );

    case "flow":
      return (
        <div className="space-y-3">
          <p className="text-[11px] text-muted-foreground/40 uppercase">Data Flow Analysis</p>
          {data.outbound_connections?.length > 0 ? (
            <div className="space-y-2">
              <p className="text-[10px] text-muted-foreground/40">Outbound Connections</p>
              {data.outbound_connections.map((c: any, i: number) => (
                <div key={i} className="flex items-center gap-2 text-[12px]">
                  <div className="h-2 w-2 rounded-full bg-rose-500 animate-pulse" />
                  <span className="text-foreground/60 font-mono">{c.domain}</span>
                  <span className="text-muted-foreground/30 text-[10px]">({c.type})</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-[11px] text-muted-foreground/30">No outbound connections detected</p>
          )}
          {data.data_reads?.length > 0 && (
            <div className="space-y-1">
              <p className="text-[10px] text-muted-foreground/40">Data Accessed</p>
              <div className="flex flex-wrap gap-1">
                {data.data_reads.map((d: string, i: number) => (
                  <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-foreground/[0.04] text-foreground/50 border border-foreground/10">{d}</span>
                ))}
              </div>
            </div>
          )}
          {data.flags?.length > 0 && (
            <div className="space-y-1 mt-2">
              {data.flags.map((f: string, i: number) => (
                <div key={i} className="flex items-start gap-2 text-[12px] text-rose-400/70">
                  <span className="text-rose-400 mt-0.5 shrink-0">!</span><span>{f}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      );

    case "context":
      return (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-[10px] text-muted-foreground/40 uppercase mb-1">Package Claims To Be</p>
              <p className="text-[13px] text-foreground/60">{data.description || "No description"}</p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground/40 uppercase mb-1">Update Actually Does</p>
              <p className="text-[13px] text-foreground/60">{data.update_summary || "Unknown"}</p>
            </div>
          </div>
          {data.mismatch_score !== undefined && (
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] text-muted-foreground/40 uppercase">Claim vs Reality Mismatch</span>
                <span className={cn("text-[12px] font-mono font-medium",
                  data.mismatch_score > 0.7 ? "text-rose-400" : data.mismatch_score > 0.3 ? "text-amber-400" : "text-emerald-400"
                )}>
                  {(data.mismatch_score * 100).toFixed(0)}%
                </span>
              </div>
              <div className="h-2 rounded-full bg-foreground/[0.05] overflow-hidden">
                <div className={cn("h-full rounded-full",
                  data.mismatch_score > 0.7 ? "bg-rose-500/50" : data.mismatch_score > 0.3 ? "bg-amber-500/50" : "bg-emerald-500/50"
                )} style={{ width: `${data.mismatch_score * 100}%` }} />
              </div>
            </div>
          )}
          {data.flags?.length > 0 && (
            <div className="space-y-1">
              {data.flags.map((f: string, i: number) => (
                <div key={i} className="flex items-start gap-2 text-[12px] text-amber-400/70">
                  <span className="text-amber-400 mt-0.5 shrink-0">!</span><span>{f}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      );

    default:
      return <pre className="text-[11px] text-foreground/40 font-mono">{JSON.stringify(data, null, 2)}</pre>;
  }
}
