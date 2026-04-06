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

  if (loading) return <div className="min-h-screen flex items-center justify-center" style={{ background: "#fff" }}><p style={{ color: "#999" }}>Loading...</p></div>;

  return (
    <div style={{ maxWidth: 520, margin: "0 auto", padding: "40px 20px", fontFamily: "'nyt-karnakcondensed', Georgia, serif" }}>
      {/* Header */}
      <div style={{ textAlign: "center", marginBottom: 32, borderBottom: "1px solid #e0e0e0", paddingBottom: 20 }}>
        <h1 style={{ fontSize: 36, fontWeight: 700, letterSpacing: -1, margin: 0, fontFamily: "'nyt-karnakcondensed', Georgia, serif" }}>
          Sentinel
        </h1>
        <p style={{ fontSize: 14, color: "#787878", marginTop: 8, fontFamily: "-apple-system, BlinkMacSystemFont, sans-serif" }}>
          Inspect software packages. Find the threat.
        </p>
      </div>

      {/* Stats bar */}
      {player && player.total_inspections > 0 && (
        <div style={{ display: "flex", justifyContent: "center", gap: 32, marginBottom: 28, padding: "12px 0", borderBottom: "1px solid #e0e0e0" }}>
          {[
            { label: "Score", value: player.total_score },
            { label: "Streak", value: player.streak },
            { label: "Detection", value: player.detection_rate ? `${(player.detection_rate * 100).toFixed(0)}%` : "—" },
          ].map((s) => (
            <div key={s.label} style={{ textAlign: "center", fontFamily: "-apple-system, BlinkMacSystemFont, sans-serif" }}>
              <div style={{ fontSize: 22, fontWeight: 700, color: "#1a1a2e" }}>{s.value}</div>
              <div style={{ fontSize: 11, color: "#999", textTransform: "uppercase", letterSpacing: 1 }}>{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Scenarios */}
      <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
        {scenarios.map((s) => (
          <Link
            key={s.id}
            href={`/sentinel/inspect/${s.id}`}
            style={{
              display: "flex", alignItems: "center", gap: 14,
              padding: "16px 12px",
              borderBottom: "1px solid #f0f0f0",
              textDecoration: "none", color: "inherit",
              fontFamily: "-apple-system, BlinkMacSystemFont, sans-serif",
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
        ))}
      </div>

      {scenarios.length === 0 && (
        <p style={{ textAlign: "center", padding: 40, color: "#bbb" }}>No scenarios available.</p>
      )}

      <div style={{ textAlign: "center", marginTop: 40, paddingTop: 20, borderTop: "1px solid #e0e0e0" }}>
        <p style={{ fontSize: 11, color: "#bbb", fontFamily: "-apple-system, sans-serif" }}>
          Powered by <a href="https://ghost.validia.ai" style={{ color: "#999" }}>Ghost</a> · Validia
        </p>
      </div>
    </div>
  );
}
