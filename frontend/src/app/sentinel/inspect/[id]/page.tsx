"use client";

import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getSentinelScenario, submitVerdict } from "@/lib/api";

function getSessionId(): string {
  if (typeof window === "undefined") return "ssr";
  let id = localStorage.getItem("ghost-session-id");
  if (!id) { id = crypto.randomUUID(); localStorage.setItem("ghost-session-id", id); }
  return id;
}

const TOOLS = [
  { key: "identity", label: "ID Badge", icon: "🪪" },
  { key: "timing", label: "Timeline", icon: "📅" },
  { key: "shape", label: "X-Ray", icon: "🔬" },
  { key: "behavior", label: "Cargo", icon: "📦" },
  { key: "flow", label: "Tracker", icon: "📡" },
  { key: "context", label: "Context", icon: "🔎" },
];

const S: Record<string, React.CSSProperties> = {
  page: { maxWidth: 580, margin: "0 auto", padding: "24px 16px", fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", minHeight: "100vh" },
  h1: { fontSize: 28, fontWeight: 700, textAlign: "center" as const, fontFamily: "Georgia, serif", letterSpacing: -0.5, color: "#1a1a2e", margin: 0 },
  mono: { fontFamily: "'SF Mono', Menlo, monospace" },
  subtitle: { fontSize: 13, color: "#888", textAlign: "center" as const, marginTop: 4 },
  toolBar: { display: "flex", gap: 4, padding: 4, background: "#f5f5f5", borderRadius: 12, marginBottom: 16, overflowX: "auto" as const },
  toolBtn: { flex: 1, padding: "10px 6px", borderRadius: 8, border: "none", cursor: "pointer", fontSize: 12, fontWeight: 600, textAlign: "center" as const, transition: "all 0.15s", display: "flex", flexDirection: "column" as const, alignItems: "center", gap: 2 },
  panel: { border: "1px solid #e8e8e8", borderRadius: 12, padding: 20, marginBottom: 16, background: "#fff" },
  flag: { display: "flex", alignItems: "flex-start", gap: 8, padding: "8px 12px", background: "#fff8e1", borderRadius: 8, marginTop: 8, fontSize: 13, color: "#b8860b" },
  verdictBtn: { flex: 1, padding: "14px 8px", borderRadius: 10, border: "2px solid #e0e0e0", cursor: "pointer", fontSize: 14, fontWeight: 600, textAlign: "center" as const, transition: "all 0.15s", background: "#fff" },
  submitBtn: { width: "100%", padding: "14px", borderRadius: 10, border: "2px solid #1a1a2e", background: "#1a1a2e", color: "#fff", fontSize: 14, fontWeight: 600, cursor: "pointer", transition: "all 0.15s" },
  tag: { display: "inline-block", padding: "3px 8px", borderRadius: 6, fontSize: 11, fontWeight: 600, marginRight: 4 },
};

export default function InspectPage() {
  const params = useParams();
  const [scenario, setScenario] = useState<any>(null);
  const [activeTool, setActiveTool] = useState("identity");
  const [verdict, setVerdict] = useState<string | null>(null);
  const [attackGuess, setAttackGuess] = useState("");
  const [confidence, setConfidence] = useState(70);
  const [toolsChecked, setToolsChecked] = useState<Set<string>>(new Set(["identity"]));
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
        session_id: getSessionId(), verdict, confidence: confidence / 100,
        attack_type_guess: verdict !== "safe" ? attackGuess.toLowerCase().replace(/ /g, "_") : null,
        evidence_notes: { tools_checked: Array.from(toolsChecked) },
        time_taken_secs: (Date.now() - startTime.current) / 1000,
        tools_used: Array.from(toolsChecked),
      });
      setResult(res);
    } catch (e: any) {
      if (e.message?.includes("409")) alert("Already inspected this one.");
    } finally { setSubmitting(false); }
  };

  if (loading || !scenario) return <div style={{ ...S.page, display: "flex", alignItems: "center", justifyContent: "center" }}><p style={{ color: "#999" }}>Loading...</p></div>;

  // === RESULTS ===
  if (result) {
    return (
      <div style={S.page}>
        <div style={{ textAlign: "center", padding: "40px 0 20px" }}>
          <div style={{ fontSize: 48, marginBottom: 8 }}>{result.is_correct ? "✅" : "❌"}</div>
          <h2 style={{ ...S.h1, fontSize: 24, color: result.is_correct ? "#2e7d32" : "#c62828" }}>
            {result.is_correct ? "Correct!" : "Incorrect"}
          </h2>
          <p style={{ fontSize: 15, color: "#666", marginTop: 8 }}>
            {result.was_malicious ? `This was: ${result.attack_name}` : "This was a legitimate update."}
          </p>
          <p style={{ fontSize: 20, fontWeight: 700, color: "#1a1a2e", marginTop: 12 }}>
            {result.score > 0 ? "+" : ""}{result.score} pts
          </p>
        </div>

        {(result.real_cve || result.real_cvss) && (
          <div style={{ display: "flex", justifyContent: "center", gap: 16, marginBottom: 16, fontSize: 13, color: "#888" }}>
            {result.real_cve && <span style={S.mono}>{result.real_cve}</span>}
            {result.real_cvss && <span>CVSS {result.real_cvss}</span>}
          </div>
        )}

        {result.postmortem && (
          <div style={{ ...S.panel, background: "#fafafa" }}>
            <p style={{ fontSize: 11, color: "#999", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8, fontWeight: 600 }}>What Happened</p>
            <p style={{ fontSize: 14, color: "#444", lineHeight: 1.6 }}>{result.postmortem}</p>
          </div>
        )}

        <div style={{ display: "flex", gap: 8, marginTop: 20 }}>
          <Link href="/sentinel" style={{ ...S.verdictBtn, textDecoration: "none", color: "#666" }}>Back</Link>
          <Link href="/sentinel" style={{ ...S.submitBtn, textDecoration: "none", textAlign: "center", display: "block" }}>Next Package →</Link>
        </div>
      </div>
    );
  }

  // === INSPECTION ===
  return (
    <div style={S.page}>
      {/* Back + Progress */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Link href="/sentinel" style={{ fontSize: 13, color: "#888", textDecoration: "none" }}>← Back</Link>
        <span style={{ fontSize: 12, color: "#bbb" }}>{toolsChecked.size}/6 tools</span>
      </div>

      {/* Package header */}
      <div style={{ textAlign: "center", marginBottom: 20 }}>
        <p style={{ fontSize: 12, color: "#aaa", textTransform: "uppercase", letterSpacing: 1, margin: 0 }}>{scenario.registry}</p>
        <h1 style={S.h1}>{scenario.package_name}</h1>
        <p style={{ ...S.subtitle, ...S.mono }}>{scenario.version_from || "?"} → {scenario.version_to || "?"}</p>
      </div>

      {/* Tool tabs */}
      <div style={S.toolBar}>
        {TOOLS.map((t) => {
          const active = activeTool === t.key;
          const checked = toolsChecked.has(t.key);
          return (
            <button
              key={t.key}
              onClick={() => selectTool(t.key)}
              style={{
                ...S.toolBtn,
                background: active ? "#fff" : "transparent",
                boxShadow: active ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
                color: active ? "#1a1a2e" : checked ? "#666" : "#aaa",
              }}
            >
              <span style={{ fontSize: 18 }}>{t.icon}</span>
              <span>{t.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tool panel */}
      <div style={S.panel}>
        {scenario.tools[activeTool] ? (
          <ToolPanel tool={activeTool} data={scenario.tools[activeTool]} />
        ) : (
          <p style={{ color: "#ccc", textAlign: "center", padding: 20 }}>No data available for this tool.</p>
        )}
      </div>

      {/* Verdict */}
      <div style={{ ...S.panel, border: "2px solid #e0e0e0" }}>
        <p style={{ fontSize: 11, color: "#999", textTransform: "uppercase", letterSpacing: 1, marginBottom: 12, fontWeight: 600 }}>Your Verdict</p>

        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          {[
            { v: "safe", label: "✅ Safe", border: "#4caf50", bg: "#e8f5e9" },
            { v: "suspicious", label: "⚠️ Flag", border: "#ff9800", bg: "#fff8e1" },
            { v: "malicious", label: "🚨 Malicious", border: "#f44336", bg: "#fce4ec" },
          ].map((o) => (
            <button key={o.v} onClick={() => setVerdict(o.v)} style={{
              ...S.verdictBtn,
              borderColor: verdict === o.v ? o.border : "#e0e0e0",
              background: verdict === o.v ? o.bg : "#fff",
              color: verdict === o.v ? o.border : "#666",
            }}>
              {o.label}
            </button>
          ))}
        </div>

        {verdict && verdict !== "safe" && (
          <select value={attackGuess} onChange={(e) => setAttackGuess(e.target.value)}
            style={{ width: "100%", padding: "10px 12px", borderRadius: 8, border: "1px solid #e0e0e0", fontSize: 13, marginBottom: 12, color: "#666", background: "#fafafa" }}>
            <option value="">Attack type? (bonus points)</option>
            {["Account Hijack", "Maintainer Takeover", "Dependency Confusion", "Maintainer Sabotage", "CI/CD Poisoning", "Build Compromise", "Social Engineering", "Domain Takeover", "Typosquatting", "Worm"].map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        )}

        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
          <span style={{ fontSize: 12, color: "#999", width: 70 }}>Confidence</span>
          <input type="range" min={10} max={100} value={confidence} onChange={(e) => setConfidence(Number(e.target.value))}
            style={{ flex: 1, accentColor: "#1a1a2e" }} />
          <span style={{ ...S.mono, fontSize: 13, color: "#666", width: 36, textAlign: "right" }}>{confidence}%</span>
        </div>

        <button onClick={handleSubmit} disabled={!verdict || submitting}
          style={{ ...S.submitBtn, opacity: !verdict || submitting ? 0.4 : 1, cursor: !verdict || submitting ? "default" : "pointer" }}>
          {submitting ? "Submitting..." : "Submit Verdict"}
        </button>
      </div>
    </div>
  );
}

// === TOOL PANELS === //

function ToolPanel({ tool, data }: { tool: string; data: any }) {
  return (
    <div>
      {tool === "identity" && <IdentityPanel data={data} />}
      {tool === "timing" && <TimingPanel data={data} />}
      {tool === "shape" && <ShapePanel data={data} />}
      {tool === "behavior" && <BehaviorPanel data={data} />}
      {tool === "flow" && <FlowPanel data={data} />}
      {tool === "context" && <ContextPanel data={data} />}
      <Flags flags={data.flags} />
    </div>
  );
}

function Flags({ flags }: { flags?: string[] }) {
  if (!flags || flags.length === 0) return null;
  return (
    <div style={{ marginTop: 12 }}>
      {flags.map((f, i) => (
        <div key={i} style={S.flag}>
          <span>⚠️</span>
          <span>{f}</span>
        </div>
      ))}
    </div>
  );
}

// --- ID BADGE: looks like a real profile card ---
function IdentityPanel({ data }: { data: any }) {
  const trust = (data.trust_score || 0) * 100;
  const trustColor = trust > 70 ? "#4caf50" : trust > 40 ? "#ff9800" : "#f44336";
  return (
    <div>
      {/* Profile card */}
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 16 }}>
        <div style={{
          width: 56, height: 56, borderRadius: "50%",
          background: `linear-gradient(135deg, ${trustColor}22, ${trustColor}44)`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 24, fontWeight: 700, color: trustColor,
          border: `2px solid ${trustColor}44`,
        }}>
          {(data.publisher || "?")[0].toUpperCase()}
        </div>
        <div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#1a1a2e" }}>{data.publisher || "Unknown"}</div>
          <div style={{ fontSize: 13, color: "#888" }}>Member since {data.publisher_since || "unknown"}</div>
        </div>
      </div>

      {/* Stats row */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <Tag ok={data.is_usual_publisher}>{data.is_usual_publisher ? "✓ Usual publisher" : "✗ Different publisher"}</Tag>
        <Tag ok={trust > 60}>Trust: {trust.toFixed(0)}%</Tag>
        {data.account_age_days != null && <Tag ok={data.account_age_days > 365}>{data.account_age_days}d account</Tag>}
        {data.previous_packages != null && <Tag ok={data.previous_packages > 5}>{data.previous_packages} packages</Tag>}
        {data.maintainer_count != null && <Tag ok={true}>{data.maintainer_count} maintainer{data.maintainer_count !== 1 ? "s" : ""}</Tag>}
      </div>

      {/* Maintainer list */}
      {data.all_maintainers && data.all_maintainers.length > 0 && (
        <div style={{ fontSize: 12, color: "#999" }}>
          Team: {data.all_maintainers.join(", ")}
        </div>
      )}
    </div>
  );
}

// --- TIMELINE: release heartbeat ---
function TimingPanel({ data }: { data: any }) {
  const history = data.release_history || [];
  const maxGap = Math.max(...history.map((r: any) => r.gap_days || 0), 30);
  return (
    <div>
      <p style={{ fontSize: 12, color: "#999", textTransform: "uppercase", letterSpacing: 1, marginBottom: 12 }}>Release History</p>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 3, height: 80, padding: "0 4px" }}>
        {history.map((r: any, i: number) => {
          const gap = r.gap_days || 0;
          const h = Math.max((gap / maxGap) * 70, 6);
          const bad = gap > 365 || gap === 0;
          return (
            <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
              <div style={{
                width: "100%", maxWidth: 28, height: h, borderRadius: 4,
                background: bad ? "#ffd54f" : "#e0e0e0",
                transition: "all 0.3s",
              }} title={`${r.version} — ${r.date} (${gap}d gap)`} />
              <span style={{ fontSize: 8, color: "#bbb", fontFamily: "monospace", whiteSpace: "nowrap", overflow: "hidden", maxWidth: 40, textOverflow: "ellipsis" }}>
                {r.version}
              </span>
            </div>
          );
        })}
      </div>
      <div style={{ marginTop: 12 }}>
        <Tag ok={data.cadence_normal}>{data.cadence_normal ? "✓ Normal cadence" : "✗ Abnormal release pattern"}</Tag>
      </div>
    </div>
  );
}

// --- X-RAY: dependency/file changes ---
function ShapePanel({ data }: { data: any }) {
  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 12 }}>
        <div>
          <p style={{ fontSize: 11, color: "#999", textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>Dependencies Added</p>
          {(data.deps_added || []).length > 0
            ? data.deps_added.map((d: string, i: number) => <div key={i} style={{ fontSize: 13, color: "#2e7d32", fontFamily: "monospace", padding: "2px 0" }}>+ {d}</div>)
            : <p style={{ fontSize: 12, color: "#ccc" }}>None</p>}
        </div>
        <div>
          <p style={{ fontSize: 11, color: "#999", textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>Dependencies Removed</p>
          {(data.deps_removed || []).length > 0
            ? data.deps_removed.map((d: string, i: number) => <div key={i} style={{ fontSize: 13, color: "#c62828", fontFamily: "monospace", padding: "2px 0" }}>- {d}</div>)
            : <p style={{ fontSize: 12, color: "#ccc" }}>None</p>}
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div>
          <p style={{ fontSize: 11, color: "#999", textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>Files Added</p>
          {(data.files_added || []).length > 0
            ? data.files_added.slice(0, 8).map((f: string, i: number) => <div key={i} style={{ fontSize: 12, color: "#2e7d32", fontFamily: "monospace", padding: "1px 0", wordBreak: "break-all" }}>+ {f}</div>)
            : <p style={{ fontSize: 12, color: "#ccc" }}>None</p>}
          {(data.files_added || []).length > 8 && <p style={{ fontSize: 11, color: "#aaa" }}>+{data.files_added.length - 8} more</p>}
        </div>
        <div>
          <p style={{ fontSize: 11, color: "#999", textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>Files Removed</p>
          {(data.files_removed || []).length > 0
            ? data.files_removed.slice(0, 8).map((f: string, i: number) => <div key={i} style={{ fontSize: 12, color: "#c62828", fontFamily: "monospace", padding: "1px 0", wordBreak: "break-all" }}>- {f}</div>)
            : <p style={{ fontSize: 12, color: "#ccc" }}>None</p>}
          {(data.files_removed || []).length > 8 && <p style={{ fontSize: 11, color: "#aaa" }}>+{data.files_removed.length - 8} more</p>}
        </div>
      </div>
      {data.diff_stats && (
        <div style={{ display: "flex", gap: 16, marginTop: 12, fontSize: 12, color: "#888" }}>
          <span>{data.diff_stats.files_changed || 0} files changed</span>
          <span style={{ color: "#2e7d32" }}>+{data.diff_stats.insertions || 0}</span>
          <span style={{ color: "#c62828" }}>-{data.diff_stats.deletions || 0}</span>
        </div>
      )}
    </div>
  );
}

// --- CARGO: behavioral nutrition label ---
function BehaviorPanel({ data }: { data: any }) {
  const cats = data.categories || {};
  const colorMap: Record<string, { bg: string; text: string; label: string }> = {
    green: { bg: "#e8f5e9", text: "#2e7d32", label: "Expected" },
    yellow: { bg: "#fff8e1", text: "#f57f17", label: "Unusual" },
    red: { bg: "#fce4ec", text: "#c62828", label: "Suspicious" },
  };
  return (
    <div>
      <p style={{ fontSize: 11, color: "#999", textTransform: "uppercase", letterSpacing: 1, marginBottom: 12 }}>Behavioral Scan</p>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {Object.entries(cats).map(([cat, level]) => {
          const c = colorMap[level as string] || colorMap.green;
          return (
            <div key={cat} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 12px", borderRadius: 8, background: c.bg }}>
              <span style={{ fontSize: 13, fontWeight: 500, color: "#444", textTransform: "capitalize" }}>{cat.replace(/_/g, " ")}</span>
              <span style={{ fontSize: 11, fontWeight: 700, color: c.text }}>{c.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// --- FLIGHT TRACKER: connections map ---
function FlowPanel({ data }: { data: any }) {
  const connections = data.outbound_connections || [];
  const reads = data.data_reads || [];
  return (
    <div>
      <p style={{ fontSize: 11, color: "#999", textTransform: "uppercase", letterSpacing: 1, marginBottom: 12 }}>Outbound Connections</p>
      {connections.length > 0 ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {connections.map((c: any, i: number) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 12px", borderRadius: 8, background: "#fce4ec" }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#f44336", animation: "pulse 2s infinite" }} />
              <span style={{ fontSize: 13, fontFamily: "monospace", color: "#c62828" }}>{c.domain}</span>
              <span style={{ fontSize: 11, color: "#999", marginLeft: "auto" }}>{c.type}</span>
            </div>
          ))}
        </div>
      ) : (
        <p style={{ fontSize: 13, color: "#ccc", padding: "12px 0" }}>No outbound connections detected</p>
      )}

      {reads.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <p style={{ fontSize: 11, color: "#999", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>Data Accessed</p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {reads.map((r: string, i: number) => (
              <span key={i} style={{ ...S.tag, background: "#fff3e0", color: "#e65100" }}>{r}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// --- CONTEXT: claim vs reality ---
function ContextPanel({ data }: { data: any }) {
  const mismatch = data.mismatch_score || 0;
  const mColor = mismatch > 0.7 ? "#f44336" : mismatch > 0.3 ? "#ff9800" : "#4caf50";
  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
        <div>
          <p style={{ fontSize: 11, color: "#999", textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>Claims to be</p>
          <p style={{ fontSize: 14, color: "#444", lineHeight: 1.5 }}>{data.description || "No description"}</p>
        </div>
        <div>
          <p style={{ fontSize: 11, color: "#999", textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>Actually does</p>
          <p style={{ fontSize: 14, color: "#444", lineHeight: 1.5 }}>{data.update_summary || "Unknown"}</p>
        </div>
      </div>

      {/* Mismatch meter */}
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
          <span style={{ fontSize: 11, color: "#999", textTransform: "uppercase", letterSpacing: 1 }}>Mismatch</span>
          <span style={{ fontSize: 14, fontWeight: 700, color: mColor }}>{(mismatch * 100).toFixed(0)}%</span>
        </div>
        <div style={{ height: 8, borderRadius: 4, background: "#f0f0f0", overflow: "hidden" }}>
          <div style={{ height: "100%", width: `${mismatch * 100}%`, borderRadius: 4, background: mColor, transition: "width 0.5s" }} />
        </div>
      </div>

      {data.weekly_downloads && (
        <p style={{ fontSize: 12, color: "#aaa", marginTop: 12 }}>
          {data.weekly_downloads.toLocaleString()} weekly downloads
        </p>
      )}
    </div>
  );
}

// --- Shared tag component ---
function Tag({ ok, children }: { ok: boolean; children: React.ReactNode }) {
  return (
    <span style={{
      ...S.tag,
      background: ok ? "#e8f5e9" : "#fff8e1",
      color: ok ? "#2e7d32" : "#b8860b",
      border: `1px solid ${ok ? "#c8e6c9" : "#ffe082"}`,
    }}>
      {children}
    </span>
  );
}
