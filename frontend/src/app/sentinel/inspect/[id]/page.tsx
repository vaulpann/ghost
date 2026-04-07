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

const ACCENT = "#1e3a5f"; // dark blue accent for all evidence

const EVIDENCE = [
  { key: "identity", label: "Identity", img: "/sentinel-identity.jpg", color: ACCENT },
  { key: "timing", label: "Timeline", img: "/sentinel-timeline.jpg", color: ACCENT },
  { key: "shape", label: "Structure", img: "/sentinel-structure.jpg", color: ACCENT },
  { key: "behavior", label: "Behavior", img: "/sentinel-behavior.jpg", color: ACCENT },
  { key: "flow", label: "Data Flow", img: "/sentinel-dataflow.jpg", color: ACCENT },
  { key: "context", label: "Context", img: "/sentinel-context.jpg", color: ACCENT },
];

// No grid — tiles are positioned in a rotating circle

const NARRATIVES: Record<string, (d: any) => string> = {
  identity: (d) => {
    const name = d.publisher || "Unknown";
    const usual = d.is_usual_publisher;
    const age = d.account_age_days;
    const pkgs = d.previous_packages;
    const trust = ((d.trust_score || 0) * 100).toFixed(0);
    const maintainers = d.all_maintainers?.join(", ") || name;
    let t = usual
      ? `${name} is the regular maintainer of this package and has been the consistent publisher across versions.`
      : `${name} is NOT the usual publisher of this package. This is a different account than who normally releases updates, which warrants attention.`;
    if (age) t += ` Their account was created ${age} days ago.`;
    if (pkgs != null) t += ` They have published ${pkgs} other packages on the registry.`;
    t += ` Current trust assessment: ${trust}%.`;
    if (d.maintainer_count && d.maintainer_count > 1) t += ` The project has ${d.maintainer_count} listed maintainers: ${maintainers}.`;
    if (d.flags?.length) t += "\n\n" + d.flags.map((f: string) => `• ${f}`).join("\n");
    return t;
  },
  timing: (d) => {
    const h = d.release_history || [];
    const normal = d.cadence_normal;
    let t = `This package has ${h.length} recorded releases in its version history. `;
    if (h.length > 0) {
      const latest = h[h.length - 1];
      t += `The latest version (${latest.version}) was published on ${latest.date}`;
      if (latest.gap_days != null) t += `, which was ${latest.gap_days} days after the previous release`;
      t += ". ";
      const longGaps = h.filter((r: any) => r.gap_days && r.gap_days > 180);
      if (longGaps.length > 0) t += `There ${longGaps.length === 1 ? "is" : "are"} ${longGaps.length} gap${longGaps.length > 1 ? "s" : ""} longer than 6 months in the release history. `;
      const sameDay = h.filter((r: any) => r.gap_days === 0);
      if (sameDay.length > 1) t += `${sameDay.length} versions were published on the same day. `;
    }
    t += normal ? "Overall, the release cadence appears consistent with normal development activity." : "The release pattern shows notable irregularities that may warrant further review.";
    if (d.flags?.length) t += "\n\n" + d.flags.map((f: string) => `• ${f}`).join("\n");
    return t;
  },
  shape: (d) => {
    const da = d.deps_added || []; const dr = d.deps_removed || [];
    const fa = d.files_added || []; const fr = d.files_removed || [];
    const s = d.diff_stats || {};
    let t = "";
    if (s.files_changed) t += `This update touches ${s.files_changed} files with ${s.insertions || 0} insertions and ${s.deletions || 0} deletions. `;
    if (da.length) t += `New dependencies were introduced: ${da.join(", ")}. This is notable because new dependencies expand the supply chain surface. `;
    if (dr.length) t += `Dependencies removed: ${dr.join(", ")}. `;
    if (fa.length > 0 && fa.length <= 5) t += `New files added: ${fa.join(", ")}. `;
    else if (fa.length > 5) t += `${fa.length} new files were added to the package. `;
    if (fr.length > 0 && fr.length <= 5) t += `Files removed: ${fr.join(", ")}. `;
    else if (fr.length > 5) t += `${fr.length} files were removed from the package. `;
    if (!t) t = "The structural footprint of this update is minimal — no significant dependency or file changes detected.";
    if (d.flags?.length) t += "\n\n" + d.flags.map((f: string) => `• ${f}`).join("\n");
    return t;
  },
  behavior: (d) => {
    const cats = d.categories || {};
    const red = Object.entries(cats).filter(([, v]) => v === "red");
    const yellow = Object.entries(cats).filter(([, v]) => v === "yellow");
    const green = Object.entries(cats).filter(([, v]) => v === "green");
    let t = "";
    if (red.length === 0 && yellow.length === 0) {
      t = `All behavioral signals for this update appear normal. The package operates within expected parameters for its category: ${green.map(([k]) => k.replace(/_/g, " ")).join(", ")} — all within expected norms.`;
    } else {
      if (red.length) t += `Suspicious behavioral signals detected in: ${red.map(([k]) => k.replace(/_/g, " ")).join(", ")}. These activities are atypical for this type of package and require careful evaluation. `;
      if (yellow.length) t += `Unusual but potentially legitimate activity observed in: ${yellow.map(([k]) => k.replace(/_/g, " ")).join(", ")}. `;
      if (green.length) t += `Normal activity in: ${green.map(([k]) => k.replace(/_/g, " ")).join(", ")}.`;
    }
    if (d.install_scripts && Object.keys(d.install_scripts).length > 0) {
      t += ` Install lifecycle scripts are present: ${Object.keys(d.install_scripts).join(", ")}.`;
    }
    if (d.flags?.length) t += "\n\n" + d.flags.map((f: string) => `• ${f}`).join("\n");
    return t;
  },
  flow: (d) => {
    const conn = d.outbound_connections || [];
    const reads = d.data_reads || [];
    let t = "";
    if (conn.length === 0 && reads.length === 0) {
      t = "No outbound network connections or sensitive data access patterns were detected in this update. The code does not appear to communicate with external services or read sensitive local data.";
    } else {
      if (conn.length) t += `This update references ${conn.length} external endpoint${conn.length > 1 ? "s" : ""}: ${conn.map((c: any) => `${c.domain} (${c.type})`).join(", ")}. `;
      if (reads.length) t += `The code accesses the following data: ${reads.join(", ")}. `;
      t += "These connections and data access patterns should be evaluated in the context of the package's stated purpose.";
    }
    if (d.flags?.length) t += "\n\n" + d.flags.map((f: string) => `• ${f}`).join("\n");
    return t;
  },
  context: (d) => {
    const desc = d.description || "No description provided by the maintainer";
    const summary = d.update_summary || "The specific changes in this update are not clearly documented";
    const mismatch = d.mismatch_score || 0;
    const dl = d.weekly_downloads;
    let t = `This package describes itself as: "${desc}." `;
    t += `The changes introduced in this update: ${summary}. `;
    if (mismatch > 0.7) {
      t += `There is a significant mismatch (${(mismatch * 100).toFixed(0)}%) between the package's stated purpose and what this update actually introduces. This kind of discrepancy is a strong signal for supply chain compromise.`;
    } else if (mismatch > 0.3) {
      t += `There is a moderate discrepancy (${(mismatch * 100).toFixed(0)}%) between the package's purpose and the nature of these changes. This could be legitimate feature expansion or could indicate suspicious modification.`;
    } else {
      t += `The changes in this update are consistent with the package's stated purpose. No contextual anomalies detected.`;
    }
    if (dl) t += ` This package receives approximately ${dl.toLocaleString()} downloads per week.`;
    if (d.flags?.length) t += "\n\n" + d.flags.map((f: string) => `• ${f}`).join("\n");
    return t;
  },
};

export default function InspectPage() {
  const params = useParams();
  const [scenario, setScenario] = useState<any>(null);
  const [activeEvidence, setActiveEvidence] = useState<string | null>(null);
  const [showVote, setShowVote] = useState(false);
  const [verdict, setVerdict] = useState<string | null>(null);
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
    setShowVote(false);
    setViewed(prev => new Set(Array.from(prev).concat(key)));
  };

  const handleSubmit = async () => {
    if (!verdict || !scenario) return;
    setSubmitting(true);
    try {
      const res = await submitVerdict(scenario.id, {
        session_id: getSessionId(), verdict, confidence: confidence / 100,
        attack_type_guess: null,
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
    return <div style={{ height: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <p style={{ color: "#999" }}>Loading...</p>
    </div>;
  }

  // === RESULTS ===
  if (result) {
    return (
      <div style={{ height: "calc(100vh - 56px)", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ maxWidth: 480, textAlign: "center", padding: 40 }}>
          <h2 style={{ fontSize: 48, fontWeight: 800, color: result.is_correct ? "#16a34a" : "#dc2626", marginBottom: 4 }}>
            {result.is_correct ? "Correct" : "Wrong"}
          </h2>
          <p style={{ fontSize: 24, fontWeight: 700, color: "#111", marginBottom: 16 }}>
            {result.score > 0 ? "+" : ""}{result.score} points
          </p>
          <p style={{ fontSize: 15, color: "#666", lineHeight: 1.7, marginBottom: 24 }}>
            {result.was_malicious ? result.attack_name : "This was a legitimate, safe update."}
          </p>
          {result.postmortem && (
            <div style={{ textAlign: "left", background: "#fff", borderRadius: 16, padding: 24, marginBottom: 24, border: "1px solid #eee" }}>
              <p style={{ fontSize: 11, color: "#aaa", textTransform: "uppercase", letterSpacing: 2, marginBottom: 8, fontWeight: 600 }}>What happened</p>
              <p style={{ fontSize: 14, color: "#444", lineHeight: 1.8 }}>{result.postmortem}</p>
            </div>
          )}
          <Link href="/sentinel" style={{
            display: "inline-block", padding: "14px 40px", background: "#111", color: "#fff",
            borderRadius: 10, textDecoration: "none", fontSize: 15, fontWeight: 600,
          }}>
            Next Package
          </Link>
        </div>
      </div>
    );
  }

  // === INSPECTION ===
  return (
    <div style={{ height: "calc(100vh - 56px)", position: "relative", overflow: "hidden" }}>

      {/* Lower-left: Package info (with blur effect below) */}
      <div style={{ position: "absolute", bottom: 40, left: 40, zIndex: 20 }}>
        <h1 style={{ fontSize: 42, fontWeight: 800, color: "#111", margin: 0, lineHeight: 1.1 }}>
          {scenario.package_name}
        </h1>
        <p style={{ fontSize: 22, fontWeight: 500, color: "rgba(17,17,17,0.25)", margin: 0, marginTop: -4, filter: "blur(0.5px)" }}>
          {scenario.version_from} → {scenario.version_to}
        </p>
        <p style={{ fontSize: 12, color: "#bbb", marginTop: 6, fontWeight: 500, letterSpacing: 1 }}>
          PUZZLE #{scenario.id.slice(0, 4).toUpperCase()} · {scenario.registry.toUpperCase()}
        </p>
      </div>

      {/* Rotating circle of evidence tiles */}
      <div className="orbit-container" style={{
        position: "absolute", top: "50%", left: "50%",
        transform: "translate(-50%, -50%)",
        width: 440, height: 440,
      }}>
        {/* Slow rotating ring */}
        <div className="orbit-ring" style={{
          position: "absolute", inset: 0,
          animation: "orbitSpin 60s linear infinite",
        }}>
          {EVIDENCE.map((ev, i) => {
            const angle = (i * 60) - 90; // 6 items, 60° apart, start from top
            const rad = angle * (Math.PI / 180);
            const radius = 185; // distance from center
            const x = Math.cos(rad) * radius;
            const y = Math.sin(rad) * radius;
            return (
              <div
                key={ev.key}
                style={{
                  position: "absolute",
                  left: "50%", top: "50%",
                  transform: `translate(calc(-50% + ${x}px), calc(-50% + ${y}px))`,
                }}
              >
                {/* Counter-rotate so tiles stay upright */}
                <div style={{ animation: "orbitCounterSpin 60s linear infinite" }}>
                  <EvidenceTile ev={ev}
                    active={activeEvidence === ev.key} viewed={viewed.has(ev.key)}
                    onClick={() => openEvidence(ev.key)} />
                </div>
              </div>
            );
          })}
        </div>

        {/* Center VOTE button (does not rotate) */}
        <button
          onClick={() => { setActiveEvidence(null); setShowVote(true); }}
          style={{
            position: "absolute", top: "50%", left: "50%",
            transform: "translate(-50%, -50%)",
            width: 110, height: 110, borderRadius: 28,
            background: showVote ? "#111" : "#fff",
            border: "2px solid #e0e0e0",
            cursor: "pointer", display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center", gap: 4,
            transition: "all 0.3s",
            boxShadow: showVote ? "0 8px 30px rgba(0,0,0,0.12)" : "0 2px 12px rgba(0,0,0,0.06)",
            zIndex: 5,
          }}
        >
          <span style={{ fontSize: 13, fontWeight: 700, color: showVote ? "#fff" : "#888", letterSpacing: 1.5 }}>VOTE</span>
          <span style={{ fontSize: 10, color: showVote ? "rgba(255,255,255,0.6)" : "#ccc" }}>
            {viewed.size}/6
          </span>
        </button>
      </div>

      {/* Evidence detail panel — slides from right */}
      {activeEvidence && scenario.tools[activeEvidence] && (
        <div style={{
          position: "absolute", top: 0, right: 0, bottom: 0, width: "min(460px, 42vw)",
          background: "#fff", borderLeft: "1px solid #eee",
          padding: "36px 28px", overflowY: "auto",
          animation: "slideIn 0.25s ease-out", zIndex: 30,
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ width: 12, height: 12, borderRadius: 4, background: EVIDENCE.find(e => e.key === activeEvidence)?.color }} />
              <span style={{ fontSize: 14, fontWeight: 700, color: "#111", textTransform: "uppercase", letterSpacing: 1.5 }}>
                {EVIDENCE.find(e => e.key === activeEvidence)?.label}
              </span>
            </div>
            <button onClick={() => setActiveEvidence(null)} style={{
              background: "none", border: "none", cursor: "pointer", fontSize: 24, color: "#ccc", lineHeight: 1,
            }}>×</button>
          </div>

          <p style={{ fontSize: 15, color: "#333", lineHeight: 1.9, whiteSpace: "pre-line" }}>
            {NARRATIVES[activeEvidence]?.(scenario.tools[activeEvidence]) || "No data available."}
          </p>

          <details style={{ marginTop: 28, fontSize: 12 }}>
            <summary style={{ cursor: "pointer", color: "#aaa", userSelect: "none" }}>View raw evidence</summary>
            <pre style={{ marginTop: 8, fontSize: 11, color: "#888", fontFamily: "monospace", background: "#fafafa", padding: 12, borderRadius: 8, overflowX: "auto", whiteSpace: "pre-wrap" }}>
              {JSON.stringify(scenario.tools[activeEvidence], null, 2)}
            </pre>
          </details>
        </div>
      )}

      {/* Vote panel — shows when center is clicked */}
      {showVote && !activeEvidence && (
        <div style={{
          position: "absolute", top: 0, right: 0, bottom: 0, width: "min(380px, 38vw)",
          background: "#fff", borderLeft: "1px solid #eee",
          padding: "36px 28px", animation: "slideIn 0.25s ease-out", zIndex: 30,
          display: "flex", flexDirection: "column",
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 28 }}>
            <span style={{ fontSize: 14, fontWeight: 700, textTransform: "uppercase", letterSpacing: 1.5, color: "#111" }}>Your Verdict</span>
            <button onClick={() => setShowVote(false)} style={{ background: "none", border: "none", cursor: "pointer", fontSize: 24, color: "#ccc" }}>×</button>
          </div>

          <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
            {[
              { v: "safe", label: "Safe", c: "#16a34a", bg: "#f0fdf4" },
              { v: "suspicious", label: "Flag", c: "#d97706", bg: "#fffbeb" },
              { v: "malicious", label: "Malicious", c: "#dc2626", bg: "#fef2f2" },
            ].map((o) => (
              <button key={o.v} onClick={() => setVerdict(o.v)} style={{
                flex: 1, padding: "14px 4px", borderRadius: 10, fontSize: 14, fontWeight: 700,
                border: verdict === o.v ? `2px solid ${o.c}` : "2px solid #eee",
                background: verdict === o.v ? o.bg : "#fff",
                color: verdict === o.v ? o.c : "#999",
                cursor: "pointer", transition: "all 0.15s",
              }}>{o.label}</button>
            ))}
          </div>

          <textarea
            value={reasoning}
            onChange={(e) => setReasoning(e.target.value)}
            placeholder="What did you notice? (optional)"
            style={{
              width: "100%", padding: 12, borderRadius: 10, border: "1px solid #eee",
              fontSize: 13, color: "#444", resize: "none", height: 80, marginBottom: 16,
              fontFamily: "'Inter Tight', sans-serif",
            }}
          />

          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
            <span style={{ fontSize: 12, color: "#aaa", whiteSpace: "nowrap" }}>Confidence</span>
            <input type="range" min={10} max={100} value={confidence} onChange={(e) => setConfidence(Number(e.target.value))}
              style={{ flex: 1, accentColor: "#111" }} />
            <span style={{ fontSize: 13, fontFamily: "monospace", color: "#666", width: 32 }}>{confidence}%</span>
          </div>

          <div style={{ marginTop: "auto" }}>
            <button onClick={handleSubmit} disabled={!verdict || submitting} style={{
              width: "100%", padding: 14, borderRadius: 10, border: "none",
              background: !verdict || submitting ? "#eee" : "#111",
              color: !verdict || submitting ? "#bbb" : "#fff",
              fontSize: 15, fontWeight: 700, cursor: !verdict || submitting ? "default" : "pointer",
              transition: "all 0.15s",
            }}>
              {submitting ? "Submitting..." : "Submit"}
            </button>
          </div>
        </div>
      )}

      <style>{`
        @keyframes slideIn {
          from { transform: translateX(100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
        @keyframes orbitSpin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes orbitCounterSpin {
          from { transform: rotate(0deg); }
          to { transform: rotate(-360deg); }
        }
      `}</style>
    </div>
  );
}

function EvidenceTile({ ev, active, viewed, onClick }: {
  ev: typeof EVIDENCE[0];
  active: boolean; viewed: boolean; onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        width: 110, height: 110, borderRadius: 24, overflow: "hidden",
        border: active ? `3px solid ${ev.color}` : viewed ? "2px solid #ddd" : "2px solid #e8e8e8",
        cursor: "pointer", position: "relative",
        transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
        boxShadow: active ? `0 8px 30px ${ev.color}25` : "0 2px 8px rgba(0,0,0,0.04)",
        transform: active ? "scale(1.05)" : "scale(1)",
      }}
    >
      {/* Background image */}
      <img
        src={ev.img}
        alt={ev.label}
        style={{
          width: "100%", height: "100%", objectFit: "cover",
          filter: active ? "brightness(0.7)" : viewed ? "brightness(0.85) saturate(0.8)" : "brightness(0.9) saturate(0.5)",
          transition: "all 0.3s",
        }}
      />
      {/* Label overlay */}
      <div style={{
        position: "absolute", bottom: 0, left: 0, right: 0,
        padding: "8px 10px",
        background: "linear-gradient(transparent, rgba(0,0,0,0.6))",
      }}>
        <span style={{ fontSize: 12, fontWeight: 700, color: "#fff", letterSpacing: 0.5 }}>
          {ev.label}
        </span>
      </div>
      {/* Viewed checkmark */}
      {viewed && !active && (
        <div style={{
          position: "absolute", top: 8, right: 8,
          width: 20, height: 20, borderRadius: "50%",
          background: ev.color, display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <span style={{ color: "#fff", fontSize: 12, fontWeight: 700 }}>✓</span>
        </div>
      )}
    </button>
  );
}
