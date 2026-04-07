"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getSentinelScenarios, getSentinelPlayer } from "@/lib/api";

function getSessionId(): string {
  if (typeof window === "undefined") return "ssr";
  let id = localStorage.getItem("ghost-session-id");
  if (!id) { id = crypto.randomUUID(); localStorage.setItem("ghost-session-id", id); }
  return id;
}

function ScenarioRow({ s }: { s: any }) {
  return (
    <Link
      href={`/sentinel/inspect/${s.id}`}
      style={{
        display: "flex", alignItems: "center", gap: 14,
        padding: "14px 0",
        borderBottom: "1px solid #f0f0f0",
        textDecoration: "none", color: "inherit",
        fontFamily: "'Inter Tight', -apple-system, sans-serif",
      }}
    >
      <div style={{
        width: 36, height: 36, borderRadius: 8,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 14, fontWeight: 700,
        background: s.difficulty === "tutorial" ? "#e8f5e9" : s.difficulty === "easy" ? "#e3f2fd" : s.difficulty === "medium" ? "#fff8e1" : s.difficulty === "hard" ? "#fff3e0" : "#fce4ec",
        color: s.difficulty === "tutorial" ? "#2e7d32" : s.difficulty === "easy" ? "#1565c0" : s.difficulty === "medium" ? "#f57f17" : s.difficulty === "hard" ? "#e65100" : "#c62828",
      }}>
        {s.difficulty[0].toUpperCase()}
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 15, fontWeight: 600, color: "#1a1a2e" }}>
          {s.package_name}
          <span style={{ fontSize: 12, fontWeight: 400, color: "#aaa", marginLeft: 6 }}>{s.registry}</span>
        </div>
        <div style={{ fontSize: 13, color: "#888", fontFamily: "monospace", marginTop: 2 }}>
          {s.version_from || "?"} → {s.version_to || "?"}
        </div>
      </div>
      <div style={{ fontSize: 12, color: "#bbb" }}>
        {s.total_inspections > 0 ? `${s.total_inspections} played` : "New"}
      </div>
      <svg width="8" height="14" viewBox="0 0 8 14" fill="none" style={{ opacity: 0.3 }}>
        <path d="M1 1l6 6-6 6" stroke="#1a1a2e" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </Link>
  );
}

export default function SentinelPage() {
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [player, setPlayer] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [scenData, playerData] = await Promise.all([
          getSentinelScenarios("per_page=50"),
          getSentinelPlayer(getSessionId()).catch(() => null),
        ]);
        setScenarios(scenData.items);
        setPlayer(playerData);
      } catch (e) { console.error(e); }
      finally { setLoading(false); }
    }
    load();
  }, []);

  if (loading) return <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}><p style={{ color: "#999" }}>Loading...</p></div>;

  const daily = scenarios.length > 0 ? scenarios[0] : null;
  const open = scenarios.slice(1);

  return (
    <div style={{ fontFamily: "'Inter Tight', -apple-system, sans-serif" }}>
      {/* Header */}
      <div style={{ borderBottom: "1px solid #eee", padding: "24px 0 20px", marginBottom: 0 }}>
        <div style={{ maxWidth: 640, margin: "0 auto", padding: "0 20px" }}>
          <h1 style={{ fontSize: 28, fontWeight: 700, letterSpacing: -0.5, margin: 0, color: "#111" }}>
            Sentinel
          </h1>
          <p style={{ fontSize: 14, color: "#888", marginTop: 4 }}>
            Inspect packages. Spot supply chain threats.
          </p>
        </div>
      </div>

      <div style={{ maxWidth: 640, margin: "0 auto", padding: "0 20px" }}>
        {/* Stats */}
        {player && player.total_inspections > 0 && (
          <div style={{ display: "flex", gap: 32, padding: "20px 0", borderBottom: "1px solid #f0f0f0" }}>
            {[
              { label: "Score", value: player.total_score },
              { label: "Streak", value: player.streak },
              { label: "Detection", value: player.detection_rate ? `${(player.detection_rate * 100).toFixed(0)}%` : "—" },
              { label: "Inspected", value: player.total_inspections },
            ].map((s) => (
              <div key={s.label}>
                <div style={{ fontSize: 20, fontWeight: 700, color: "#111" }}>{s.value}</div>
                <div style={{ fontSize: 11, color: "#aaa", textTransform: "uppercase", letterSpacing: 1, marginTop: 2 }}>{s.label}</div>
              </div>
            ))}
          </div>
        )}

        {/* Daily */}
        {daily && (
          <div style={{ marginTop: 28 }}>
            <h2 style={{ fontSize: 13, fontWeight: 700, color: "#111", textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 12 }}>
              Daily
            </h2>
            <Link
              href={`/sentinel/inspect/${daily.id}`}
              style={{
                display: "block", textDecoration: "none", color: "inherit",
                border: "1px solid #e8e8e8", borderRadius: 16, padding: 20,
                background: "#fff",
                transition: "border-color 0.15s, box-shadow 0.15s",
              }}
              onMouseOver={(e) => { e.currentTarget.style.borderColor = "#ccc"; e.currentTarget.style.boxShadow = "0 4px 16px rgba(0,0,0,0.04)"; }}
              onMouseOut={(e) => { e.currentTarget.style.borderColor = "#e8e8e8"; e.currentTarget.style.boxShadow = "none"; }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: "#111" }}>
                    {daily.package_name}
                    <span style={{ fontSize: 13, fontWeight: 400, color: "#aaa", marginLeft: 8 }}>{daily.registry}</span>
                  </div>
                  <div style={{ fontSize: 14, color: "#888", fontFamily: "monospace", marginTop: 4 }}>
                    {daily.version_from || "?"} → {daily.version_to || "?"}
                  </div>
                </div>
                <div style={{
                  padding: "8px 16px", borderRadius: 8,
                  background: "#1e3a5f", color: "#fff",
                  fontSize: 13, fontWeight: 600,
                }}>
                  Play
                </div>
              </div>
              {daily.total_inspections > 0 && (
                <div style={{ fontSize: 12, color: "#bbb", marginTop: 10 }}>
                  {daily.total_inspections} inspections completed
                </div>
              )}
            </Link>
          </div>
        )}

        {/* Open Puzzles */}
        {open.length > 0 && (
          <div style={{ marginTop: 36 }}>
            <h2 style={{ fontSize: 13, fontWeight: 700, color: "#111", textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 8 }}>
              Open Puzzles
            </h2>
            <div>
              {open.map((s) => (
                <ScenarioRow key={s.id} s={s} />
              ))}
            </div>
          </div>
        )}

        {scenarios.length === 0 && (
          <p style={{ textAlign: "center", padding: 60, color: "#bbb" }}>No scenarios available.</p>
        )}

        {/* Footer */}
        <div style={{ textAlign: "center", marginTop: 48, paddingTop: 20, paddingBottom: 20, borderTop: "1px solid #f0f0f0" }}>
          <p style={{ fontSize: 11, color: "#ccc" }}>
            Powered by <a href="https://ghost.validia.ai" style={{ color: "#aaa", textDecoration: "underline" }}>Ghost</a> · Validia
          </p>
        </div>
      </div>
    </div>
  );
}
