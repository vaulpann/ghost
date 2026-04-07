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

function getCompleted(): Record<string, any> {
  if (typeof window === "undefined") return {};
  try { return JSON.parse(localStorage.getItem("ghost-completed") || "{}"); }
  catch { return {}; }
}

const ACCENT = "#1e3a5f";

const EVIDENCE = [
  { key: "identity", label: "Identity", img: "/sentinel-identity.jpg", color: ACCENT },
  { key: "timing", label: "Timeline", img: "/sentinel-timeline.jpg", color: ACCENT },
  { key: "shape", label: "Structure", img: "/sentinel-structure.jpg", color: ACCENT },
  { key: "behavior", label: "Behavior", img: "/sentinel-behavior.jpg", color: ACCENT },
  { key: "flow", label: "Data Flow", img: "/sentinel-dataflow.jpg", color: ACCENT },
  { key: "context", label: "Context", img: "/sentinel-context.jpg", color: ACCENT },
];

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

const ADVANCED_CONTEXT: Record<string, (d: any) => { label: string; content: string }[]> = {
  identity: (d) => {
    const sections: { label: string; content: string }[] = [];
    if (d.all_maintainers?.length) sections.push({ label: "Full Maintainer List", content: d.all_maintainers.join(", ") });
    if (d.email) sections.push({ label: "Publisher Email", content: d.email });
    if (d.npm_2fa_enabled !== undefined) sections.push({ label: "2FA Status", content: d.npm_2fa_enabled ? "Enabled" : "Not enabled" });
    if (d.github_profile) sections.push({ label: "GitHub Profile", content: JSON.stringify(d.github_profile, null, 2) });
    if (d.ownership_history?.length) sections.push({ label: "Ownership Changes", content: d.ownership_history.map((h: any) => `${h.date}: ${h.from} → ${h.to}`).join("\n") });
    return sections;
  },
  timing: (d) => {
    const sections: { label: string; content: string }[] = [];
    const h = d.release_history || [];
    if (h.length > 0) {
      const table = h.map((r: any) => `${r.version}  ${r.date}${r.gap_days != null ? `  (+${r.gap_days}d)` : ""}`).join("\n");
      sections.push({ label: "Full Version History", content: table });
    }
    if (d.publish_hour !== undefined) sections.push({ label: "Publish Time (UTC)", content: `Published at hour ${d.publish_hour} UTC` });
    if (d.day_of_week) sections.push({ label: "Day of Week", content: d.day_of_week });
    return sections;
  },
  shape: (d) => {
    const sections: { label: string; content: string }[] = [];
    const fa = d.files_added || [];
    const fr = d.files_removed || [];
    const fm = d.files_modified || [];
    if (fa.length) sections.push({ label: "Files Added", content: fa.join("\n") });
    if (fr.length) sections.push({ label: "Files Removed", content: fr.join("\n") });
    if (fm.length) sections.push({ label: "Files Modified", content: fm.join("\n") });
    if (d.deps_added?.length) sections.push({ label: "Dependencies Added", content: d.deps_added.join("\n") });
    if (d.deps_removed?.length) sections.push({ label: "Dependencies Removed", content: d.deps_removed.join("\n") });
    if (d.diff_sample) sections.push({ label: "Code Diff Sample", content: d.diff_sample });
    if (d.size_before && d.size_after) sections.push({ label: "Package Size", content: `${d.size_before} → ${d.size_after} bytes` });
    return sections;
  },
  behavior: (d) => {
    const sections: { label: string; content: string }[] = [];
    if (d.install_scripts && Object.keys(d.install_scripts).length) {
      sections.push({ label: "Install Scripts", content: Object.entries(d.install_scripts).map(([k, v]) => `${k}: ${v}`).join("\n") });
    }
    if (d.suspicious_patterns?.length) sections.push({ label: "Suspicious Code Patterns", content: d.suspicious_patterns.map((p: any) => `${p.file}:${p.line} — ${p.pattern}\n${p.snippet || ""}`).join("\n\n") });
    if (d.obfuscation_signals?.length) sections.push({ label: "Obfuscation Signals", content: d.obfuscation_signals.join("\n") });
    const cats = d.categories || {};
    if (Object.keys(cats).length) sections.push({ label: "Category Breakdown", content: Object.entries(cats).map(([k, v]) => `${k.replace(/_/g, " ")}: ${v}`).join("\n") });
    return sections;
  },
  flow: (d) => {
    const sections: { label: string; content: string }[] = [];
    const conn = d.outbound_connections || [];
    if (conn.length) sections.push({ label: "Outbound Connections", content: conn.map((c: any) => `${c.type}: ${c.domain}${c.url ? ` (${c.url})` : ""}${c.file ? ` — in ${c.file}` : ""}`).join("\n") });
    if (d.data_reads?.length) sections.push({ label: "Data Access", content: d.data_reads.join("\n") });
    if (d.env_access?.length) sections.push({ label: "Environment Variables Read", content: d.env_access.join("\n") });
    if (d.crypto_usage?.length) sections.push({ label: "Crypto/Encoding Usage", content: d.crypto_usage.join("\n") });
    return sections;
  },
  context: (d) => {
    const sections: { label: string; content: string }[] = [];
    if (d.description) sections.push({ label: "Package Description", content: d.description });
    if (d.update_summary) sections.push({ label: "Update Summary", content: d.update_summary });
    if (d.readme_snippet) sections.push({ label: "README Excerpt", content: d.readme_snippet });
    if (d.license) sections.push({ label: "License", content: d.license });
    if (d.repository_url) sections.push({ label: "Repository", content: d.repository_url });
    if (d.weekly_downloads) sections.push({ label: "Weekly Downloads", content: d.weekly_downloads.toLocaleString() });
    if (d.dependents_count) sections.push({ label: "Dependent Packages", content: d.dependents_count.toLocaleString() });
    return sections;
  },
};

function AdvancedDetails({ evidenceKey, data }: { evidenceKey: string; data: any }) {
  const sections = ADVANCED_CONTEXT[evidenceKey]?.(data) || [];
  if (sections.length === 0) return null;

  return (
    <details style={{ marginTop: 20, fontSize: 12 }}>
      <summary style={{
        cursor: "pointer", userSelect: "none",
        display: "inline-flex", alignItems: "center", gap: 6,
        color: "#1e3a5f", fontWeight: 600, fontSize: 12,
      }}>
        <span style={{
          fontSize: 9, padding: "2px 6px", borderRadius: 4,
          background: "#1e3a5f", color: "#fff", fontWeight: 700,
          letterSpacing: 0.5, textTransform: "uppercase",
        }}>Advanced</span>
        Detailed context
      </summary>
      <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 14 }}>
        {sections.map((s, i) => (
          <div key={i}>
            <p style={{ fontSize: 11, fontWeight: 600, color: "#999", textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>{s.label}</p>
            <pre style={{
              fontSize: 12, color: "#444", fontFamily: "monospace",
              background: "#f8f8f8", padding: 10, borderRadius: 8,
              overflowX: "auto", whiteSpace: "pre-wrap", margin: 0,
              border: "1px solid #f0f0f0", lineHeight: 1.6,
            }}>{s.content}</pre>
          </div>
        ))}
      </div>
    </details>
  );
}

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
  const [isMobile, setIsMobile] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const startTime = useRef(Date.now());

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  useEffect(() => {
    // If already completed, show saved result immediately
    const allCompleted = getCompleted();
    const saved = allCompleted[params.id as string];
    if (saved) setResult(saved);

    // Auto-show help if user hasn't completed any challenges yet
    if (Object.keys(allCompleted).length === 0) {
      setShowHelp(true);
    }

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
      // Save completion to localStorage so the list page can show results
      try {
        const completed = JSON.parse(localStorage.getItem("ghost-completed") || "{}");
        completed[scenario.id] = { verdict, confidence, ...res };
        localStorage.setItem("ghost-completed", JSON.stringify(completed));
      } catch {}
    } catch (e: any) {
      // If 409 (already submitted), show result from localStorage or a fallback
      if (e.message?.includes("409")) {
        const saved = getCompleted()[scenario.id];
        if (saved) {
          setResult(saved);
        } else {
          // No saved result — fake a minimal one so we don't get stuck
          setResult({ is_correct: false, score: 0, was_malicious: false, verdict, postmortem: "You already submitted a verdict for this puzzle." });
          try {
            const completed = JSON.parse(localStorage.getItem("ghost-completed") || "{}");
            completed[scenario.id] = { verdict, confidence, is_correct: false, score: 0, was_malicious: false, postmortem: "You already submitted a verdict for this puzzle." };
            localStorage.setItem("ghost-completed", JSON.stringify(completed));
          } catch {}
        }
      } else {
        console.error("Submit failed:", e);
      }
    } finally { setSubmitting(false); }
  };

  if (loading || !scenario) {
    return <div style={{ height: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <p style={{ color: "#999" }}>Loading...</p>
    </div>;
  }

  // === RESULTS ===
  if (result) {
    const shareText = result.is_correct
      ? `I correctly identified ${scenario.package_name} on Ghost Resolver. Can you spot the supply chain attack?`
      : `I got tricked by ${scenario.package_name} on Ghost Resolver. Can you spot the supply chain attack?`;
    const shareUrl = `https://x.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent("https://ghost.validia.ai")}`;

    return (
      <div style={{ minHeight: "calc(100vh - 56px)", display: "flex", alignItems: "center", justifyContent: "center", padding: isMobile ? 16 : 20 }}>
        <div style={{ maxWidth: 440, width: "100%", textAlign: "center" }}>
          {/* Verdict */}
          <div style={{
            display: "inline-flex", alignItems: "center", gap: 8,
            padding: "6px 16px", borderRadius: 100, marginBottom: 20,
            background: result.is_correct ? "#f0fdf4" : "#fef2f2",
            border: `1px solid ${result.is_correct ? "#bbf7d0" : "#fecaca"}`,
          }}>
            <span style={{
              width: 8, height: 8, borderRadius: "50%",
              background: result.is_correct ? "#16a34a" : "#dc2626",
            }} />
            <span style={{ fontSize: 13, fontWeight: 600, color: result.is_correct ? "#16a34a" : "#dc2626" }}>
              {result.is_correct ? "Correct" : "Incorrect"}
            </span>
          </div>

          {/* Package name */}
          <h2 style={{ fontSize: isMobile ? 28 : 36, fontWeight: 800, color: "#111", margin: "0 0 4px", lineHeight: 1.1 }}>
            {scenario.package_name}
          </h2>
          <p style={{ fontSize: 14, color: "#bbb", fontFamily: "monospace", marginBottom: 24 }}>
            {scenario.version_from} → {scenario.version_to}
          </p>

          {/* Score */}
          <p style={{ fontSize: 15, fontWeight: 600, color: "#555", marginBottom: 24 }}>
            {result.score > 0 ? "+" : ""}{result.score} points
          </p>

          {/* What happened */}
          <div style={{
            textAlign: "left", borderRadius: 14, padding: isMobile ? 16 : 20, marginBottom: 24,
            background: "#fafafa", border: "1px solid #f0f0f0",
          }}>
            <p style={{ fontSize: 11, color: "#bbb", textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 8, fontWeight: 600 }}>
              {result.was_malicious ? "Attack Details" : "Verdict"}
            </p>
            <p style={{ fontSize: 14, color: "#444", lineHeight: 1.75, margin: 0 }}>
              {result.was_malicious
                ? result.attack_name || "This was a malicious package."
                : "This was a legitimate, safe update. No threats detected."}
            </p>
            {result.postmortem && (
              <p style={{ fontSize: 13, color: "#888", lineHeight: 1.75, marginTop: 10, marginBottom: 0 }}>
                {result.postmortem}
              </p>
            )}
          </div>

          {/* Actions */}
          <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
            <Link href="/" style={{
              flex: 1, maxWidth: 180, padding: "13px 0", background: "#111", color: "#fff",
              borderRadius: 10, textDecoration: "none", fontSize: 14, fontWeight: 600,
              textAlign: "center",
            }}>
              Next
            </Link>
            <a href={shareUrl} target="_blank" rel="noopener noreferrer" style={{
              flex: 1, maxWidth: 180, padding: "13px 0",
              background: "#fff", color: "#111",
              borderRadius: 10, textDecoration: "none", fontSize: 14, fontWeight: 600,
              border: "1px solid #e0e0e0", textAlign: "center",
              display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
            }}>
              <svg viewBox="0 0 24 24" style={{ width: 14, height: 14, fill: "currentColor" }}>
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
              </svg>
              Share
            </a>
          </div>
        </div>
      </div>
    );
  }

  // === MOBILE INSPECTION ===
  if (isMobile) {
    return (
      <div style={{ minHeight: "calc(100vh - 56px)", display: "flex", flexDirection: "column" }}>
        {/* Header */}
        <div style={{ padding: "12px 16px", borderBottom: "1px solid #f0f0f0" }}>
          <Link href="/" style={{
            display: "inline-flex", alignItems: "center", gap: 6,
            fontSize: 13, color: "#999", textDecoration: "none", marginBottom: 8,
          }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
            Resolver
          </Link>
          <h1 style={{ fontSize: 24, fontWeight: 800, color: "#111", margin: 0, lineHeight: 1.1 }}>
            {scenario.package_name}
          </h1>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 4 }}>
            <span style={{ fontSize: 14, color: "rgba(17,17,17,0.3)", fontWeight: 500 }}>
              {scenario.version_from} → {scenario.version_to}
            </span>
            <span style={{ fontSize: 11, color: "#bbb", fontWeight: 500, letterSpacing: 1 }}>
              {scenario.registry.toUpperCase()}
            </span>
          </div>
        </div>

        {/* Evidence grid */}
        <div style={{ padding: "16px", flex: 1 }}>
          <div style={{
            display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10,
          }}>
            {EVIDENCE.map((ev) => (
              <button
                key={ev.key}
                onClick={() => openEvidence(ev.key)}
                style={{
                  aspectRatio: "1", borderRadius: 16, overflow: "hidden",
                  border: activeEvidence === ev.key ? `3px solid ${ev.color}` : viewed.has(ev.key) ? "2px solid #ddd" : "2px solid #e8e8e8",
                  cursor: "pointer", position: "relative",
                  transition: "all 0.2s",
                  boxShadow: activeEvidence === ev.key ? `0 4px 20px ${ev.color}25` : "0 1px 4px rgba(0,0,0,0.04)",
                }}
              >
                <img
                  src={ev.img} alt={ev.label}
                  style={{
                    width: "100%", height: "100%", objectFit: "cover",
                    filter: activeEvidence === ev.key ? "brightness(0.7)" : viewed.has(ev.key) ? "brightness(0.85) saturate(0.8)" : "brightness(0.9) saturate(0.5)",
                    transition: "all 0.3s",
                  }}
                />
                <div style={{
                  position: "absolute", bottom: 0, left: 0, right: 0,
                  padding: "6px 8px",
                  background: "linear-gradient(transparent, rgba(0,0,0,0.6))",
                }}>
                  <span style={{ fontSize: 11, fontWeight: 700, color: "#fff", letterSpacing: 0.3 }}>
                    {ev.label}
                  </span>
                </div>
                {viewed.has(ev.key) && activeEvidence !== ev.key && (
                  <div style={{
                    position: "absolute", top: 6, right: 6,
                    width: 18, height: 18, borderRadius: "50%",
                    background: ev.color, display: "flex", alignItems: "center", justifyContent: "center",
                  }}>
                    <span style={{ color: "#fff", fontSize: 10, fontWeight: 700 }}>✓</span>
                  </div>
                )}
              </button>
            ))}
          </div>

          {/* Vote button */}
          <button
            onClick={() => { setActiveEvidence(null); setShowVote(true); }}
            style={{
              width: "100%", marginTop: 16, padding: "16px",
              borderRadius: 14, border: "2px solid #e0e0e0",
              background: "#fff", cursor: "pointer",
              display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
              transition: "all 0.2s",
            }}
          >
            <span style={{ fontSize: 14, fontWeight: 700, color: "#888", letterSpacing: 1.5 }}>VOTE</span>
            <span style={{ fontSize: 12, color: "#ccc" }}>{viewed.size}/6</span>
          </button>
        </div>

        {/* Mobile evidence panel — full screen overlay from bottom */}
        {activeEvidence && scenario.tools[activeEvidence] && (
          <div style={{
            position: "fixed", inset: 0, zIndex: 50,
            display: "flex", flexDirection: "column",
          }}>
            {/* Backdrop */}
            <div
              onClick={() => setActiveEvidence(null)}
              style={{ flex: "0 0 auto", height: 60, background: "rgba(0,0,0,0.4)" }}
            />
            {/* Panel */}
            <div style={{
              flex: 1, background: "#fff",
              borderRadius: "20px 20px 0 0",
              padding: "20px 16px", overflowY: "auto",
              animation: "slideUp 0.25s ease-out",
            }}>
              {/* Handle bar */}
              <div style={{ display: "flex", justifyContent: "center", marginBottom: 16 }}>
                <div style={{ width: 36, height: 4, borderRadius: 2, background: "#ddd" }} />
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <div style={{ width: 10, height: 10, borderRadius: 3, background: EVIDENCE.find(e => e.key === activeEvidence)?.color }} />
                  <span style={{ fontSize: 13, fontWeight: 700, color: "#111", textTransform: "uppercase", letterSpacing: 1.5 }}>
                    {EVIDENCE.find(e => e.key === activeEvidence)?.label}
                  </span>
                </div>
                <button onClick={() => setActiveEvidence(null)} style={{
                  background: "none", border: "none", cursor: "pointer", fontSize: 22, color: "#ccc", lineHeight: 1, padding: 4,
                }}>×</button>
              </div>

              <p style={{ fontSize: 14, color: "#333", lineHeight: 1.85, whiteSpace: "pre-line" }}>
                {NARRATIVES[activeEvidence]?.(scenario.tools[activeEvidence]) || "No data available."}
              </p>

              <AdvancedDetails evidenceKey={activeEvidence} data={scenario.tools[activeEvidence]} />

              <details style={{ marginTop: 20, fontSize: 12 }}>
                <summary style={{ cursor: "pointer", color: "#aaa", userSelect: "none" }}>View raw evidence</summary>
                <pre style={{ marginTop: 8, fontSize: 11, color: "#888", fontFamily: "monospace", background: "#fafafa", padding: 12, borderRadius: 8, overflowX: "auto", whiteSpace: "pre-wrap" }}>
                  {JSON.stringify(scenario.tools[activeEvidence], null, 2)}
                </pre>
              </details>

              {/* Bottom padding for safe area */}
              <div style={{ height: 40 }} />
            </div>
          </div>
        )}

        {/* Mobile vote panel — full screen overlay from bottom */}
        {showVote && !activeEvidence && (
          <div style={{
            position: "fixed", inset: 0, zIndex: 50,
            display: "flex", flexDirection: "column",
          }}>
            <div
              onClick={() => setShowVote(false)}
              style={{ flex: "0 0 auto", height: 100, background: "rgba(0,0,0,0.4)" }}
            />
            <div style={{
              flex: 1, background: "#fff",
              borderRadius: "20px 20px 0 0",
              padding: "20px 16px", display: "flex", flexDirection: "column",
              animation: "slideUp 0.25s ease-out",
            }}>
              <div style={{ display: "flex", justifyContent: "center", marginBottom: 16 }}>
                <div style={{ width: 36, height: 4, borderRadius: 2, background: "#ddd" }} />
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
                <span style={{ fontSize: 13, fontWeight: 700, textTransform: "uppercase", letterSpacing: 1.5, color: "#111" }}>Your Verdict</span>
                <button onClick={() => setShowVote(false)} style={{ background: "none", border: "none", cursor: "pointer", fontSize: 22, color: "#ccc", padding: 4 }}>×</button>
              </div>

              <div style={{ display: "flex", gap: 8, marginBottom: 18 }}>
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
                  fontSize: 13, color: "#444", resize: "none", height: 80, marginBottom: 14,
                  fontFamily: "'Inter Tight', sans-serif", boxSizing: "border-box",
                }}
              />

              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 18 }}>
                <span style={{ fontSize: 12, color: "#aaa", whiteSpace: "nowrap" }}>Confidence</span>
                <input type="range" min={10} max={100} value={confidence} onChange={(e) => setConfidence(Number(e.target.value))}
                  style={{ flex: 1, accentColor: "#111" }} />
                <span style={{ fontSize: 13, fontFamily: "monospace", color: "#666", width: 32 }}>{confidence}%</span>
              </div>

              <div style={{ marginTop: "auto", paddingBottom: 20 }}>
                <button onClick={handleSubmit} disabled={!verdict || submitting} style={{
                  width: "100%", padding: 16, borderRadius: 12, border: "none",
                  background: !verdict || submitting ? "#eee" : "#111",
                  color: !verdict || submitting ? "#bbb" : "#fff",
                  fontSize: 16, fontWeight: 700, cursor: !verdict || submitting ? "default" : "pointer",
                  transition: "all 0.15s",
                }}>
                  {submitting ? "Submitting..." : "Submit"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Help button */}
        <button
          onClick={() => setShowHelp(true)}
          style={{
            position: "fixed", bottom: 20, right: 20, zIndex: 40,
            width: 44, height: 44, borderRadius: "50%",
            background: "#fff", border: "1px solid #e0e0e0",
            boxShadow: "0 2px 12px rgba(0,0,0,0.08)",
            cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 18, fontWeight: 700, color: "#999",
          }}
        >?</button>

        {/* Help overlay */}
        {showHelp && <HelpOverlay onClose={() => setShowHelp(false)} isMobile={true} />}

        <style>{`
          @keyframes slideUp {
            from { transform: translateY(100%); }
            to { transform: translateY(0); }
          }
        `}</style>
      </div>
    );
  }

  // === DESKTOP INSPECTION ===
  return (
    <div style={{ height: "calc(100vh - 56px)", position: "relative", overflow: "hidden" }}>

      {/* Back button */}
      <Link href="/" style={{
        position: "absolute", top: 24, left: 28, zIndex: 20,
        display: "inline-flex", alignItems: "center", gap: 6,
        fontSize: 13, color: "#999", textDecoration: "none",
        transition: "color 0.15s",
      }}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M19 12H5M12 19l-7-7 7-7" />
        </svg>
        Resolver
      </Link>

      {/* Lower-left: Package info */}
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
            const angle = (i * 60) - 90;
            const rad = angle * (Math.PI / 180);
            const radius = 185;
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
                <div style={{ animation: "orbitCounterSpin 60s linear infinite" }}>
                  <EvidenceTile ev={ev}
                    active={activeEvidence === ev.key} viewed={viewed.has(ev.key)}
                    onClick={() => openEvidence(ev.key)} />
                </div>
              </div>
            );
          })}
        </div>

        {/* Center VOTE button */}
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

          <AdvancedDetails evidenceKey={activeEvidence} data={scenario.tools[activeEvidence]} />

          <details style={{ marginTop: 24, fontSize: 12 }}>
            <summary style={{ cursor: "pointer", color: "#aaa", userSelect: "none" }}>View raw evidence</summary>
            <pre style={{ marginTop: 8, fontSize: 11, color: "#888", fontFamily: "monospace", background: "#fafafa", padding: 12, borderRadius: 8, overflowX: "auto", whiteSpace: "pre-wrap" }}>
              {JSON.stringify(scenario.tools[activeEvidence], null, 2)}
            </pre>
          </details>
        </div>
      )}

      {/* Vote panel */}
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

      {/* Help button */}
      <button
        onClick={() => setShowHelp(true)}
        style={{
          position: "absolute", bottom: 28, right: 28, zIndex: 20,
          width: 44, height: 44, borderRadius: "50%",
          background: "#fff", border: "1px solid #e0e0e0",
          boxShadow: "0 2px 12px rgba(0,0,0,0.08)",
          cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 18, fontWeight: 700, color: "#999",
        }}
      >?</button>

      {/* Help overlay */}
      {showHelp && <HelpOverlay onClose={() => setShowHelp(false)} isMobile={false} />}

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
      <img
        src={ev.img}
        alt={ev.label}
        style={{
          width: "100%", height: "100%", objectFit: "cover",
          filter: active ? "brightness(0.7)" : viewed ? "brightness(0.85) saturate(0.8)" : "brightness(0.9) saturate(0.5)",
          transition: "all 0.3s",
        }}
      />
      <div style={{
        position: "absolute", bottom: 0, left: 0, right: 0,
        padding: "8px 10px",
        background: "linear-gradient(transparent, rgba(0,0,0,0.6))",
      }}>
        <span style={{ fontSize: 12, fontWeight: 700, color: "#fff", letterSpacing: 0.5 }}>
          {ev.label}
        </span>
      </div>
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

function HelpOverlay({ onClose, isMobile }: { onClose: () => void; isMobile: boolean }) {
  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 100,
      display: "flex", alignItems: "center", justifyContent: "center",
    }}>
      <div onClick={onClose} style={{ position: "absolute", inset: 0, background: "rgba(0,0,0,0.4)" }} />
      <div style={{
        position: "relative", background: "#fff", borderRadius: 20,
        padding: isMobile ? "24px 20px" : "32px 28px",
        maxWidth: isMobile ? "calc(100vw - 32px)" : 420,
        width: "100%",
        boxShadow: "0 20px 60px rgba(0,0,0,0.15)",
        animation: "fadeInScale 0.2s ease-out",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <span style={{ fontSize: 15, fontWeight: 700, color: "#111" }}>How to Play</span>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", fontSize: 22, color: "#ccc", padding: 4 }}>×</button>
        </div>
        <div style={{ fontSize: 14, color: "#555", lineHeight: 1.8 }}>
          <p style={{ marginBottom: 12 }}>
            A package update just dropped. Your job: figure out if it's <strong>safe</strong> or <strong>malicious</strong>.
          </p>
          <p style={{ marginBottom: 12 }}>
            Tap the <strong>6 evidence tiles</strong> to inspect different dimensions — who published it, when, what changed in the code, and more.
          </p>
          <p style={{ marginBottom: 12 }}>
            Once you've reviewed the evidence, hit <strong>VOTE</strong> to submit your verdict: Safe, Flag, or Malicious. Set your confidence level and submit.
          </p>
          <p style={{ color: "#999", fontSize: 13 }}>
            Real packages. Real version diffs. Can you spot the supply chain attack?
          </p>
        </div>
        <style>{`
          @keyframes fadeInScale {
            from { transform: scale(0.95); opacity: 0; }
            to { transform: scale(1); opacity: 1; }
          }
        `}</style>
      </div>
    </div>
  );
}
