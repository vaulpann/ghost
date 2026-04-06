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

// 6 evidence tiles with labels and placeholder icons
const EVIDENCE = [
  { key: "identity", label: "Identity", short: "ID", color: "#6366f1" },
  { key: "timing", label: "Timeline", short: "TL", color: "#0ea5e9" },
  { key: "shape", label: "Structure", short: "ST", color: "#10b981" },
  { key: "behavior", label: "Behavior", short: "BH", color: "#f59e0b" },
  { key: "flow", label: "Data Flow", short: "DF", color: "#ef4444" },
  { key: "context", label: "Context", short: "CX", color: "#8b5cf6" },
];

// Orbital positions for 6 items in a circle (top, top-right, bot-right, bot, bot-left, top-left)
const ORBIT_POSITIONS = [
  { top: "5%", left: "50%", transform: "translate(-50%, 0)" },
  { top: "22%", left: "82%", transform: "translate(-50%, -50%)" },
  { top: "68%", left: "82%", transform: "translate(-50%, -50%)" },
  { top: "88%", left: "50%", transform: "translate(-50%, -100%)" },
  { top: "68%", left: "18%", transform: "translate(-50%, -50%)" },
  { top: "22%", left: "18%", transform: "translate(-50%, -50%)" },
];

// Placeholder narratives — will be replaced by agent-generated content
const PLACEHOLDER_NARRATIVES: Record<string, (data: any) => string> = {
  identity: (d) => {
    const name = d.publisher || "Unknown";
    const age = d.account_age_days;
    const pkgs = d.previous_packages;
    const usual = d.is_usual_publisher;
    const trust = ((d.trust_score || 0) * 100).toFixed(0);
    let text = `The publisher "${name}" `;
    if (usual) {
      text += `is the regular maintainer of this package. `;
    } else {
      text += `is NOT the usual publisher of this package — this is a different account than who normally releases updates. `;
    }
    if (age) text += `Their account is ${age} days old. `;
    if (pkgs != null) text += `They have published ${pkgs} other packages on the registry. `;
    text += `Trust assessment: ${trust}%.`;
    if (d.maintainer_count) text += ` There ${d.maintainer_count === 1 ? "is 1 maintainer" : `are ${d.maintainer_count} maintainers`} on this project.`;
    if (d.flags?.length) text += "\n\n" + d.flags.join("\n");
    return text;
  },
  timing: (d) => {
    const history = d.release_history || [];
    const normal = d.cadence_normal;
    let text = `This package has ${history.length} recorded releases. `;
    if (history.length > 0) {
      const latest = history[history.length - 1];
      text += `The most recent version (${latest.version}) was published on ${latest.date}. `;
      if (latest.gap_days != null) {
        text += `There was a ${latest.gap_days}-day gap since the previous release. `;
      }
    }
    text += normal ? "The release cadence appears normal." : "The release pattern shows anomalies.";
    if (d.flags?.length) text += "\n\n" + d.flags.join("\n");
    return text;
  },
  shape: (d) => {
    const added = d.deps_added || [];
    const removed = d.deps_removed || [];
    const filesA = d.files_added || [];
    const filesR = d.files_removed || [];
    const stats = d.diff_stats || {};
    let text = "";
    if (stats.files_changed) text += `${stats.files_changed} files were changed in this update. `;
    if (stats.insertions) text += `${stats.insertions} lines added, ${stats.deletions || 0} lines removed. `;
    if (added.length) text += `New dependencies added: ${added.join(", ")}. `;
    if (removed.length) text += `Dependencies removed: ${removed.join(", ")}. `;
    if (filesA.length) text += `${filesA.length} new file${filesA.length > 1 ? "s" : ""} added${filesA.length <= 3 ? ": " + filesA.join(", ") : ""}. `;
    if (filesR.length) text += `${filesR.length} file${filesR.length > 1 ? "s" : ""} removed. `;
    if (!text) text = "No significant structural changes detected.";
    if (d.flags?.length) text += "\n\n" + d.flags.join("\n");
    return text;
  },
  behavior: (d) => {
    const cats = d.categories || {};
    const suspicious = Object.entries(cats).filter(([, v]) => v === "red");
    const unusual = Object.entries(cats).filter(([, v]) => v === "yellow");
    let text = "";
    if (suspicious.length === 0 && unusual.length === 0) {
      text = "All behavioral signals appear normal for this type of package. No suspicious runtime activity detected.";
    } else {
      if (suspicious.length) {
        text += `Suspicious activity detected in: ${suspicious.map(([k]) => k.replace(/_/g, " ")).join(", ")}. `;
      }
      if (unusual.length) {
        text += `Unusual but potentially legitimate activity in: ${unusual.map(([k]) => k.replace(/_/g, " ")).join(", ")}. `;
      }
    }
    if (d.flags?.length) text += "\n\n" + d.flags.join("\n");
    return text;
  },
  flow: (d) => {
    const connections = d.outbound_connections || [];
    const reads = d.data_reads || [];
    let text = "";
    if (connections.length === 0 && reads.length === 0) {
      text = "No outbound network connections or sensitive data access detected in this update.";
    } else {
      if (connections.length) {
        text += `This update references ${connections.length} external endpoint${connections.length > 1 ? "s" : ""}: ${connections.map((c: any) => c.domain).join(", ")}. `;
      }
      if (reads.length) {
        text += `The code accesses: ${reads.join(", ")}. `;
      }
    }
    if (d.flags?.length) text += "\n\n" + d.flags.join("\n");
    return text;
  },
  context: (d) => {
    const desc = d.description || "No description available";
    const summary = d.update_summary || "Unknown changes";
    const mismatch = d.mismatch_score || 0;
    const downloads = d.weekly_downloads;
    let text = `This package describes itself as: "${desc}." `;
    text += `This update: ${summary}. `;
    if (mismatch > 0.7) {
      text += `There is a significant mismatch (${(mismatch * 100).toFixed(0)}%) between what this package claims to do and what this update actually introduces.`;
    } else if (mismatch > 0.3) {
      text += `There is a moderate discrepancy (${(mismatch * 100).toFixed(0)}%) between the package's stated purpose and the changes in this update.`;
    } else {
      text += `The changes align with the package's stated purpose.`;
    }
    if (downloads) text += ` This package has ${downloads.toLocaleString()} weekly downloads.`;
    if (d.flags?.length) text += "\n\n" + d.flags.join("\n");
    return text;
  },
};

const ATTACK_TYPES = [
  "Account Hijack", "Maintainer Takeover", "Dependency Confusion",
  "Maintainer Sabotage", "CI/CD Poisoning", "Build Compromise",
  "Social Engineering", "Domain Takeover", "Typosquatting", "Worm",
];

export default function InspectPage() {
  const params = useParams();
  const [scenario, setScenario] = useState<any>(null);
  const [activeEvidence, setActiveEvidence] = useState<string | null>(null);
  const [verdict, setVerdict] = useState<string | null>(null);
  const [attackGuess, setAttackGuess] = useState("");
  const [confidence, setConfidence] = useState(70);
  const [reasoning, setReasoning] = useState("");
  const [viewed, setViewed] = useState<Set<string>>(new Set());
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

  const openEvidence = (key: string) => {
    setActiveEvidence(activeEvidence === key ? null : key);
    setViewed(prev => new Set(Array.from(prev).concat(key)));
  };

  const handleSubmit = async () => {
    if (!verdict || !scenario) return;
    setSubmitting(true);
    try {
      const res = await submitVerdict(scenario.id, {
        session_id: getSessionId(), verdict, confidence: confidence / 100,
        attack_type_guess: verdict !== "safe" ? attackGuess.toLowerCase().replace(/ /g, "_") : null,
        evidence_notes: { tools_checked: Array.from(viewed), reasoning },
        time_taken_secs: (Date.now() - startTime.current) / 1000,
        tools_used: Array.from(viewed),
      });
      setResult(res);
    } catch (e: any) {
      if (e.message?.includes("409")) alert("Already inspected.");
    } finally { setSubmitting(false); }
  };

  if (loading || !scenario) {
    return <div style={{ height: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#f7f7f7" }}>
      <p style={{ color: "#999", fontFamily: "sans-serif" }}>Loading...</p>
    </div>;
  }

  // === RESULTS ===
  if (result) {
    return (
      <div style={{ height: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#f7f7f7", fontFamily: "-apple-system, BlinkMacSystemFont, sans-serif" }}>
        <div style={{ maxWidth: 480, textAlign: "center", padding: 40 }}>
          <div style={{ fontSize: 64, marginBottom: 16 }}>{result.is_correct ? "Correct" : "Wrong"}</div>
          <h2 style={{ fontSize: 28, fontWeight: 700, color: result.is_correct ? "#16a34a" : "#dc2626", fontFamily: "Georgia, serif", marginBottom: 8 }}>
            {result.score > 0 ? "+" : ""}{result.score} points
          </h2>
          <p style={{ fontSize: 15, color: "#666", lineHeight: 1.6, marginBottom: 24 }}>
            {result.was_malicious ? result.attack_name : "This was a legitimate, safe update."}
          </p>
          {result.postmortem && (
            <div style={{ textAlign: "left", background: "#fff", borderRadius: 12, padding: 24, marginBottom: 24, border: "1px solid #e5e5e5" }}>
              <p style={{ fontSize: 11, color: "#999", textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 8 }}>Post-Mortem</p>
              <p style={{ fontSize: 14, color: "#444", lineHeight: 1.7 }}>{result.postmortem}</p>
            </div>
          )}
          <Link href="/sentinel" style={{
            display: "inline-block", padding: "12px 32px", background: "#111", color: "#fff",
            borderRadius: 8, textDecoration: "none", fontSize: 14, fontWeight: 600,
          }}>
            Next Package
          </Link>
        </div>
      </div>
    );
  }

  // === INSPECTION — ORBITAL LAYOUT ===
  return (
    <div style={{ height: "calc(100vh - 56px)", position: "relative", overflow: "hidden", fontFamily: "-apple-system, BlinkMacSystemFont, sans-serif" }}>

      {/* Lower-left: Package info */}
      <div style={{ position: "absolute", bottom: 40, left: 40, zIndex: 10 }}>
        <h1 style={{ fontSize: 32, fontWeight: 700, fontFamily: "Georgia, serif", color: "#111", margin: 0, lineHeight: 1.2 }}>
          {scenario.package_name}
        </h1>
        <p style={{ fontSize: 16, color: "#666", fontFamily: "monospace", marginTop: 4 }}>
          {scenario.version_from} → {scenario.version_to}
        </p>
        <p style={{ fontSize: 12, color: "#bbb", marginTop: 2 }}>
          Puzzle #{scenario.id.slice(0, 4).toUpperCase()} · {scenario.registry}
        </p>
      </div>

      {/* Center: Orbital evidence tiles */}
      <div style={{
        position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)",
        width: 420, height: 420,
      }}>
        {EVIDENCE.map((ev, i) => {
          const pos = ORBIT_POSITIONS[i];
          const isActive = activeEvidence === ev.key;
          const isViewed = viewed.has(ev.key);
          return (
            <button
              key={ev.key}
              onClick={() => openEvidence(ev.key)}
              style={{
                position: "absolute", ...pos,
                width: isActive ? 80 : 72, height: isActive ? 80 : 72,
                borderRadius: 20,
                background: isActive ? ev.color : isViewed ? "#fff" : "#f0f0f0",
                border: isActive ? `2px solid ${ev.color}` : isViewed ? "2px solid #ddd" : "2px solid #e8e8e8",
                cursor: "pointer",
                display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
                gap: 2,
                transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
                boxShadow: isActive ? `0 8px 30px ${ev.color}33` : isViewed ? "0 2px 8px rgba(0,0,0,0.06)" : "none",
                zIndex: isActive ? 20 : 10,
              }}
            >
              <span style={{
                fontSize: 14, fontWeight: 700, letterSpacing: 0.5,
                color: isActive ? "#fff" : isViewed ? "#888" : "#bbb",
              }}>
                {ev.short}
              </span>
              <span style={{
                fontSize: 9, fontWeight: 500,
                color: isActive ? "rgba(255,255,255,0.8)" : isViewed ? "#aaa" : "#ccc",
              }}>
                {ev.label}
              </span>
            </button>
          );
        })}

        {/* Center action area — verdict or prompt */}
        {!activeEvidence && (
          <div style={{
            position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)",
            textAlign: "center", width: 200,
          }}>
            {viewed.size === 0 ? (
              <p style={{ fontSize: 14, color: "#bbb" }}>Click evidence to begin investigation</p>
            ) : (
              <p style={{ fontSize: 13, color: "#999" }}>{viewed.size}/6 examined</p>
            )}
          </div>
        )}
      </div>

      {/* Evidence detail panel — slides in from right when evidence is selected */}
      {activeEvidence && scenario.tools[activeEvidence] && (
        <div style={{
          position: "absolute", top: 0, right: 0, bottom: 0, width: "min(480px, 45vw)",
          background: "#fff", borderLeft: "1px solid #e8e8e8",
          padding: "32px 28px", overflowY: "auto",
          animation: "slideIn 0.3s ease-out",
          zIndex: 30,
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
            <div>
              <div style={{
                display: "inline-block", width: 10, height: 10, borderRadius: 3,
                background: EVIDENCE.find(e => e.key === activeEvidence)?.color,
                marginRight: 8,
              }} />
              <span style={{ fontSize: 13, fontWeight: 600, color: "#111", textTransform: "uppercase", letterSpacing: 1 }}>
                {EVIDENCE.find(e => e.key === activeEvidence)?.label}
              </span>
            </div>
            <button onClick={() => setActiveEvidence(null)} style={{
              background: "none", border: "none", cursor: "pointer", fontSize: 20, color: "#ccc", padding: 4,
            }}>
              ×
            </button>
          </div>

          {/* Narrative content */}
          <p style={{ fontSize: 15, color: "#333", lineHeight: 1.8, whiteSpace: "pre-line" }}>
            {PLACEHOLDER_NARRATIVES[activeEvidence]?.(scenario.tools[activeEvidence]) || "No data available."}
          </p>

          {/* Raw evidence link for technical users */}
          <details style={{ marginTop: 24, fontSize: 12, color: "#999" }}>
            <summary style={{ cursor: "pointer", userSelect: "none" }}>View raw evidence</summary>
            <pre style={{ marginTop: 8, fontSize: 11, color: "#888", fontFamily: "monospace", background: "#fafafa", padding: 12, borderRadius: 8, overflowX: "auto", whiteSpace: "pre-wrap" }}>
              {JSON.stringify(scenario.tools[activeEvidence], null, 2)}
            </pre>
          </details>
        </div>
      )}

      {/* Bottom-right: Verdict panel */}
      <div style={{
        position: "absolute", bottom: 32, right: 32, width: "min(340px, 35vw)",
        zIndex: 10,
      }}>
        <div style={{ background: "#fff", borderRadius: 16, border: "1px solid #e5e5e5", padding: 24, boxShadow: "0 4px 20px rgba(0,0,0,0.04)" }}>
          <p style={{ fontSize: 11, color: "#999", textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 12, fontWeight: 600 }}>
            Your Verdict
          </p>

          <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
            {[
              { v: "safe", label: "Safe", color: "#16a34a", bg: "#f0fdf4" },
              { v: "suspicious", label: "Flag", color: "#d97706", bg: "#fffbeb" },
              { v: "malicious", label: "Malicious", color: "#dc2626", bg: "#fef2f2" },
            ].map((o) => (
              <button key={o.v} onClick={() => setVerdict(o.v)} style={{
                flex: 1, padding: "10px 4px", borderRadius: 8, fontSize: 13, fontWeight: 600,
                border: verdict === o.v ? `2px solid ${o.color}` : "2px solid #e5e5e5",
                background: verdict === o.v ? o.bg : "#fff",
                color: verdict === o.v ? o.color : "#888",
                cursor: "pointer", transition: "all 0.15s",
              }}>
                {o.label}
              </button>
            ))}
          </div>

          {verdict && verdict !== "safe" && (
            <select value={attackGuess} onChange={(e) => setAttackGuess(e.target.value)} style={{
              width: "100%", padding: "8px 10px", borderRadius: 6, border: "1px solid #e5e5e5",
              fontSize: 12, color: "#666", marginBottom: 8, background: "#fafafa",
            }}>
              <option value="">Attack type? (bonus)</option>
              {ATTACK_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          )}

          <textarea
            value={reasoning}
            onChange={(e) => setReasoning(e.target.value)}
            placeholder="What did you notice? (optional)"
            style={{
              width: "100%", padding: "8px 10px", borderRadius: 6, border: "1px solid #e5e5e5",
              fontSize: 12, color: "#444", resize: "none", height: 48, marginBottom: 8,
              fontFamily: "-apple-system, sans-serif",
            }}
          />

          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12, fontSize: 12, color: "#999" }}>
            <span>Confidence</span>
            <input type="range" min={10} max={100} value={confidence} onChange={(e) => setConfidence(Number(e.target.value))}
              style={{ flex: 1, accentColor: "#111" }} />
            <span style={{ fontFamily: "monospace", color: "#666" }}>{confidence}%</span>
          </div>

          <button onClick={handleSubmit} disabled={!verdict || submitting} style={{
            width: "100%", padding: 12, borderRadius: 8, border: "none",
            background: !verdict || submitting ? "#e5e5e5" : "#111",
            color: !verdict || submitting ? "#aaa" : "#fff",
            fontSize: 14, fontWeight: 600, cursor: !verdict || submitting ? "default" : "pointer",
            transition: "all 0.15s",
          }}>
            {submitting ? "Submitting..." : "Submit"}
          </button>
        </div>
      </div>

      {/* Top-right: progress */}
      <div style={{ position: "absolute", top: 16, right: 24, fontSize: 12, color: "#bbb" }}>
        {viewed.size}/6 evidence viewed
      </div>

      {/* CSS animation for slide-in */}
      <style>{`
        @keyframes slideIn {
          from { transform: translateX(100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
