"use client";

import { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getSentinelScenario, submitVerdict } from "@/lib/api";
import { cn } from "@/lib/utils";

function getSessionId(): string {
  if (typeof window === "undefined") return "ssr";
  let id = localStorage.getItem("ghost-session-id");
  if (!id) { id = crypto.randomUUID(); localStorage.setItem("ghost-session-id", id); }
  return id;
}

const TOOLS = [
  { key: "identity", label: "ID Badge", emoji: "🪪" },
  { key: "timing", label: "Timeline", emoji: "⏱️" },
  { key: "shape", label: "X-Ray", emoji: "🔬" },
  { key: "behavior", label: "Cargo", emoji: "📦" },
  { key: "flow", label: "Tracker", emoji: "📡" },
  { key: "context", label: "Context", emoji: "🔎" },
];

const ATTACK_TYPES = [
  "Account Hijack", "Maintainer Takeover", "Dependency Confusion",
  "Maintainer Sabotage", "CI/CD Poisoning", "Build System Compromise",
  "Social Engineering", "Domain Takeover", "Typosquatting", "Worm",
];

export default function InspectPage() {
  const params = useParams();
  const router = useRouter();
  const [scenario, setScenario] = useState<any>(null);
  const [activeTool, setActiveTool] = useState("identity");
  const [verdict, setVerdict] = useState<string | null>(null);
  const [attackGuess, setAttackGuess] = useState("");
  const [confidence, setConfidence] = useState(70);
  const [toolsChecked, setToolsChecked] = useState<Set<string>>(new Set());
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
      } catch (e) { console.error(e); }
      finally { setLoading(false); }
    }
    load();
  }, [params.id]);

  const selectTool = (key: string) => {
    setActiveTool(key);
    setToolsChecked(prev => new Set(Array.from(prev).concat(key)));
  };

  const handleSubmit = async () => {
    if (!verdict || !scenario) return;
    setSubmitting(true);
    try {
      const res = await submitVerdict(scenario.id, {
        session_id: getSessionId(),
        verdict,
        confidence: confidence / 100,
        attack_type_guess: verdict !== "safe" ? attackGuess.toLowerCase().replace(/ /g, "_") : null,
        evidence_notes: { tools_checked: Array.from(toolsChecked) },
        time_taken_secs: (Date.now() - startTime.current) / 1000,
        tools_used: Array.from(toolsChecked),
      });
      setResult(res);
    } catch (e: any) {
      if (e.message?.includes("409")) alert("Already inspected this one.");
      else console.error(e);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading || !scenario) {
    return <div className="min-h-screen flex items-center justify-center"><div className="text-muted-foreground/50">Loading...</div></div>;
  }

  // --- RESULTS VIEW ---
  if (result) {
    return (
      <div className="max-w-xl mx-auto py-8 px-4 space-y-6">
        {/* Result banner */}
        <div className={cn(
          "rounded-2xl p-8 text-center border",
          result.is_correct ? "bg-emerald-500/5 border-emerald-500/20" : "bg-rose-500/5 border-rose-500/20"
        )}>
          <div className="text-4xl mb-2">{result.is_correct ? "✅" : "❌"}</div>
          <p className={cn("text-2xl font-bold", result.is_correct ? "text-emerald-400" : "text-rose-400")}>
            {result.is_correct ? "Correct" : "Incorrect"}
          </p>
          <p className="text-foreground/50 text-[14px] mt-2">
            {result.was_malicious
              ? `This was a real attack: ${result.attack_name}`
              : "This was a legitimate update — no threat."}
          </p>
          <div className="mt-4 flex justify-center gap-6 text-[13px]">
            <span className="text-foreground/60 font-mono">{result.score > 0 ? "+" : ""}{result.score} pts</span>
            <span className="text-muted-foreground/40">Streak: {result.player_streak}</span>
            <span className="text-muted-foreground/40">Score: {result.player_total_score}</span>
          </div>
        </div>

        {/* CVE */}
        {(result.real_cve || result.real_cvss) && (
          <div className="flex gap-4 justify-center text-[12px] text-muted-foreground/50">
            {result.real_cve && <span className="font-mono">{result.real_cve}</span>}
            {result.real_cvss && <span>CVSS {result.real_cvss}</span>}
          </div>
        )}

        {/* Postmortem */}
        {result.postmortem && (
          <div className="rounded-2xl bg-foreground/[0.02] border border-foreground/[0.05] p-6">
            <p className="text-[10px] text-muted-foreground/40 uppercase tracking-wider font-medium mb-3">What Happened</p>
            <p className="text-[14px] text-foreground/60 leading-relaxed">{result.postmortem}</p>
          </div>
        )}

        {/* Next */}
        <div className="flex gap-3">
          <Link href="/sentinel" className="flex-1 rounded-xl bg-foreground/[0.03] border border-foreground/[0.06] px-4 py-3 text-center text-[14px] text-foreground/60 hover:bg-foreground/[0.06] transition-all">
            Back
          </Link>
          <Link href="/sentinel" className="flex-1 rounded-xl bg-emerald-500/10 border border-emerald-500/20 px-4 py-3 text-center text-[14px] font-medium text-emerald-400 hover:bg-emerald-500/20 transition-all">
            Next Package →
          </Link>
        </div>
      </div>
    );
  }

  // --- INSPECTION VIEW ---
  return (
    <div className="max-w-2xl mx-auto py-6 px-4 space-y-4">
      {/* Package header */}
      <div className="flex items-center justify-between">
        <Link href="/sentinel" className="text-[12px] text-muted-foreground/40 hover:text-foreground/50 transition-colors">← Back</Link>
        <span className="text-[11px] text-muted-foreground/30">{Array.from(toolsChecked).length}/6 tools checked</span>
      </div>

      <div className="text-center py-2">
        <p className="text-[12px] text-muted-foreground/40 font-mono">{scenario.registry}</p>
        <h2 className="text-2xl font-bold text-foreground/90 mt-1">{scenario.package_name}</h2>
        <p className="text-[14px] text-muted-foreground/50 font-mono mt-1">{scenario.version_from || "?"} → {scenario.version_to || "?"}</p>
      </div>

      {/* Tool tabs */}
      <div className="flex gap-1 p-1 rounded-xl bg-foreground/[0.03] overflow-x-auto">
        {TOOLS.map((t) => {
          const isActive = activeTool === t.key;
          const isChecked = toolsChecked.has(t.key);
          return (
            <button
              key={t.key}
              onClick={() => selectTool(t.key)}
              className={cn(
                "flex items-center gap-1.5 px-3 py-2 rounded-lg text-[12px] font-medium whitespace-nowrap transition-all",
                isActive ? "bg-foreground/[0.08] text-foreground shadow-sm" :
                isChecked ? "text-foreground/50" : "text-muted-foreground/40 hover:text-foreground/50"
              )}
            >
              <span>{t.emoji}</span>
              <span>{t.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tool content */}
      <div className="rounded-2xl bg-foreground/[0.02] border border-foreground/[0.05] p-5 min-h-[200px]">
        {scenario.tools[activeTool] ? (
          <ToolPanel tool={activeTool} data={scenario.tools[activeTool]} />
        ) : (
          <p className="text-muted-foreground/30 text-center py-8">No data available</p>
        )}
      </div>

      {/* Verdict */}
      <div className="space-y-3 pt-2">
        <div className="flex gap-2">
          {[
            { v: "safe", label: "✅ Safe", bg: "hover:bg-emerald-500/10 hover:border-emerald-500/20", active: "bg-emerald-500/10 border-emerald-500/30 text-emerald-400" },
            { v: "suspicious", label: "⚠️ Suspicious", bg: "hover:bg-amber-500/10 hover:border-amber-500/20", active: "bg-amber-500/10 border-amber-500/30 text-amber-400" },
            { v: "malicious", label: "🚨 Malicious", bg: "hover:bg-rose-500/10 hover:border-rose-500/20", active: "bg-rose-500/10 border-rose-500/30 text-rose-400" },
          ].map((o) => (
            <button
              key={o.v}
              onClick={() => setVerdict(o.v)}
              className={cn(
                "flex-1 rounded-xl px-3 py-3 text-[13px] font-medium border border-foreground/[0.06] transition-all",
                verdict === o.v ? o.active : cn("text-foreground/50", o.bg)
              )}
            >
              {o.label}
            </button>
          ))}
        </div>

        {verdict && verdict !== "safe" && (
          <select
            value={attackGuess}
            onChange={(e) => setAttackGuess(e.target.value)}
            className="w-full rounded-xl bg-foreground/[0.02] border border-foreground/[0.06] px-4 py-2.5 text-[13px] text-foreground/60 focus:outline-none"
          >
            <option value="">Attack type? (bonus points)</option>
            {ATTACK_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        )}

        <div className="flex items-center gap-3">
          <span className="text-[11px] text-muted-foreground/40 w-16">Confidence</span>
          <input type="range" min={10} max={100} value={confidence}
            onChange={(e) => setConfidence(Number(e.target.value))}
            className="flex-1 accent-emerald-500" />
          <span className="text-[12px] text-foreground/50 font-mono w-10 text-right">{confidence}%</span>
        </div>

        <button
          onClick={handleSubmit}
          disabled={!verdict || submitting}
          className="w-full rounded-xl px-4 py-3 text-[14px] font-medium bg-foreground/[0.06] border border-foreground/[0.08] text-foreground/70 hover:bg-foreground/[0.1] disabled:opacity-30 disabled:cursor-not-allowed transition-all"
        >
          {submitting ? "Submitting..." : "Submit Verdict"}
        </button>
      </div>
    </div>
  );
}

// === TOOL PANELS === //

function ToolPanel({ tool, data }: { tool: string; data: any }) {
  const flags = data.flags || [];
  const hasFlags = flags.length > 0;

  return (
    <div className="space-y-4">
      {tool === "identity" && <IdentityPanel data={data} />}
      {tool === "timing" && <TimingPanel data={data} />}
      {tool === "shape" && <ShapePanel data={data} />}
      {tool === "behavior" && <BehaviorPanel data={data} />}
      {tool === "flow" && <FlowPanel data={data} />}
      {tool === "context" && <ContextPanel data={data} />}

      {hasFlags && (
        <div className="pt-3 border-t border-foreground/[0.04] space-y-1.5">
          {flags.map((f: string, i: number) => (
            <div key={i} className="flex items-start gap-2 text-[12px] text-amber-400/80">
              <span className="mt-0.5 shrink-0">⚠</span>
              <span>{f}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function IdentityPanel({ data }: { data: any }) {
  return (
    <div className="flex items-start gap-4">
      <div className="h-12 w-12 rounded-full bg-foreground/[0.06] flex items-center justify-center text-xl font-bold text-foreground/30">
        {(data.publisher || "?")[0].toUpperCase()}
      </div>
      <div className="flex-1 space-y-2">
        <div>
          <p className="text-[15px] font-medium text-foreground/80">{data.publisher || "Unknown"}</p>
          <p className="text-[12px] text-muted-foreground/40">Since {data.publisher_since || "unknown"}</p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <Chip ok={data.is_usual_publisher}>{data.is_usual_publisher ? "Usual publisher" : "Different publisher"}</Chip>
          <Chip ok={(data.trust_score || 0) > 0.5}>Trust: {((data.trust_score || 0) * 100).toFixed(0)}%</Chip>
          {data.account_age_days != null && <Chip ok={data.account_age_days > 365}>Account: {data.account_age_days}d</Chip>}
          {data.previous_packages != null && <Chip ok={data.previous_packages > 5}>{data.previous_packages} packages</Chip>}
        </div>
      </div>
    </div>
  );
}

function TimingPanel({ data }: { data: any }) {
  const history = data.release_history || [];
  return (
    <div className="space-y-3">
      <div className="flex items-end gap-1 h-20 px-2">
        {history.map((r: any, i: number) => {
          const gap = r.gap_days || 0;
          const h = Math.min(Math.max(gap / 5, 8), 80);
          const bad = gap > 365 || gap === 0 || (r.version || "").includes("liberty") || (r.version || "").includes("6.6.6");
          return (
            <div key={i} className="flex flex-col items-center gap-1 flex-1">
              <div className={cn("w-full max-w-10 rounded-t", bad ? "bg-amber-500/50" : "bg-foreground/15")} style={{ height: `${h}px` }} />
              <span className="text-[9px] text-muted-foreground/30 font-mono truncate max-w-14 text-center">{r.version}</span>
            </div>
          );
        })}
      </div>
      <Chip ok={data.cadence_normal}>{data.cadence_normal ? "Normal release cadence" : "Abnormal release pattern"}</Chip>
    </div>
  );
}

function ShapePanel({ data }: { data: any }) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <div>
        <p className="text-[10px] text-muted-foreground/40 uppercase mb-1.5">Deps Added</p>
        {(data.deps_added || []).length > 0
          ? data.deps_added.map((d: string, i: number) => <div key={i} className="text-[12px] text-emerald-400/70 font-mono">+ {d}</div>)
          : <p className="text-[11px] text-muted-foreground/25">None</p>}
      </div>
      <div>
        <p className="text-[10px] text-muted-foreground/40 uppercase mb-1.5">Deps Removed</p>
        {(data.deps_removed || []).length > 0
          ? data.deps_removed.map((d: string, i: number) => <div key={i} className="text-[12px] text-rose-400/70 font-mono">- {d}</div>)
          : <p className="text-[11px] text-muted-foreground/25">None</p>}
      </div>
      <div>
        <p className="text-[10px] text-muted-foreground/40 uppercase mb-1.5">Files Added</p>
        {(data.files_added || []).length > 0
          ? data.files_added.map((f: string, i: number) => <div key={i} className="text-[12px] text-emerald-400/70 font-mono">+ {f}</div>)
          : <p className="text-[11px] text-muted-foreground/25">None</p>}
      </div>
      <div>
        <p className="text-[10px] text-muted-foreground/40 uppercase mb-1.5">Files Removed</p>
        {(data.files_removed || []).length > 0
          ? data.files_removed.map((f: string, i: number) => <div key={i} className="text-[12px] text-rose-400/70 font-mono">- {f}</div>)
          : <p className="text-[11px] text-muted-foreground/25">None</p>}
      </div>
    </div>
  );
}

function BehaviorPanel({ data }: { data: any }) {
  const cats = data.categories || {};
  return (
    <div className="space-y-3">
      <p className="text-[10px] text-muted-foreground/40 uppercase">Behavioral Scan</p>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {Object.entries(cats).map(([cat, level]) => (
          <div key={cat} className="flex items-center gap-2">
            <div className={cn("h-3 w-3 rounded-full",
              level === "green" ? "bg-emerald-500" : level === "yellow" ? "bg-amber-500" : "bg-rose-500"
            )} />
            <span className="text-[12px] text-foreground/60 capitalize">{cat.replace(/_/g, " ")}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function FlowPanel({ data }: { data: any }) {
  const connections = data.outbound_connections || [];
  const reads = data.data_reads || [];
  return (
    <div className="space-y-3">
      <div>
        <p className="text-[10px] text-muted-foreground/40 uppercase mb-1.5">Outbound Connections</p>
        {connections.length > 0 ? connections.map((c: any, i: number) => (
          <div key={i} className="flex items-center gap-2 text-[12px] mb-1">
            <div className="h-2 w-2 rounded-full bg-rose-500 animate-pulse" />
            <span className="text-foreground/60 font-mono">{c.domain}</span>
            <span className="text-muted-foreground/30 text-[10px]">{c.type}</span>
          </div>
        )) : <p className="text-[11px] text-muted-foreground/25">None detected</p>}
      </div>
      {reads.length > 0 && (
        <div>
          <p className="text-[10px] text-muted-foreground/40 uppercase mb-1.5">Data Accessed</p>
          <div className="flex flex-wrap gap-1">
            {reads.map((r: string, i: number) => (
              <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-foreground/[0.04] text-foreground/50 border border-foreground/[0.06]">{r}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ContextPanel({ data }: { data: any }) {
  const mismatch = data.mismatch_score || 0;
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-[10px] text-muted-foreground/40 uppercase mb-1">Claims to be</p>
          <p className="text-[13px] text-foreground/60">{data.description || "N/A"}</p>
        </div>
        <div>
          <p className="text-[10px] text-muted-foreground/40 uppercase mb-1">Actually does</p>
          <p className="text-[13px] text-foreground/60">{data.update_summary || "N/A"}</p>
        </div>
      </div>
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] text-muted-foreground/40 uppercase">Mismatch</span>
          <span className={cn("text-[12px] font-mono",
            mismatch > 0.7 ? "text-rose-400" : mismatch > 0.3 ? "text-amber-400" : "text-emerald-400"
          )}>{(mismatch * 100).toFixed(0)}%</span>
        </div>
        <div className="h-2 rounded-full bg-foreground/[0.05] overflow-hidden">
          <div className={cn("h-full rounded-full transition-all",
            mismatch > 0.7 ? "bg-rose-500/50" : mismatch > 0.3 ? "bg-amber-500/50" : "bg-emerald-500/50"
          )} style={{ width: `${mismatch * 100}%` }} />
        </div>
      </div>
    </div>
  );
}

function Chip({ ok, children }: { ok: boolean; children: React.ReactNode }) {
  return (
    <span className={cn(
      "text-[10px] px-2 py-0.5 rounded-full border font-medium",
      ok ? "text-emerald-400/80 bg-emerald-500/5 border-emerald-500/15" : "text-amber-400/80 bg-amber-500/5 border-amber-500/15"
    )}>
      {children}
    </span>
  );
}
