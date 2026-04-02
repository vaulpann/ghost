import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "Ghost — Supply Chain Threat Intelligence";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          background: "linear-gradient(135deg, #050505 0%, #0a1a0f 50%, #050505 100%)",
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "80px",
          fontFamily: "system-ui, sans-serif",
        }}
      >
        {/* Top accent line */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: "4px",
            background: "linear-gradient(90deg, transparent, #22c55e, transparent)",
          }}
        />

        {/* Ghost text as logo stand-in */}
        <div style={{ display: "flex", alignItems: "center", gap: "20px", marginBottom: "40px" }}>
          <div
            style={{
              width: "64px",
              height: "64px",
              borderRadius: "16px",
              background: "linear-gradient(135deg, #22c55e, #16a34a)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "32px",
              fontWeight: 800,
              color: "#000",
            }}
          >
            G
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span style={{ fontSize: "48px", fontWeight: 700, color: "#fff", letterSpacing: "-1px" }}>
              Ghost
            </span>
            <span style={{ fontSize: "16px", fontWeight: 500, color: "rgba(255,255,255,0.3)", letterSpacing: "4px", textTransform: "uppercase" as const }}>
              Supply Chain Intel
            </span>
          </div>
        </div>

        {/* Tagline */}
        <p
          style={{
            fontSize: "28px",
            fontWeight: 400,
            color: "rgba(255,255,255,0.5)",
            lineHeight: 1.5,
            maxWidth: "700px",
          }}
        >
          Real-time LLM-powered threat detection for npm, PyPI, and GitHub packages.
          Catch supply chain attacks before they spread.
        </p>

        {/* Stats bar */}
        <div
          style={{
            display: "flex",
            gap: "48px",
            marginTop: "48px",
            paddingTop: "32px",
            borderTop: "1px solid rgba(255,255,255,0.06)",
          }}
        >
          {[
            { label: "Packages Monitored", value: "100+" },
            { label: "Registries", value: "npm / PyPI / GitHub" },
            { label: "Detection Speed", value: "< 60s" },
          ].map((stat) => (
            <div key={stat.label} style={{ display: "flex", flexDirection: "column" }}>
              <span style={{ fontSize: "24px", fontWeight: 600, color: "#22c55e" }}>{stat.value}</span>
              <span style={{ fontSize: "14px", color: "rgba(255,255,255,0.25)", marginTop: "4px" }}>
                {stat.label}
              </span>
            </div>
          ))}
        </div>

        {/* URL */}
        <span
          style={{
            position: "absolute",
            bottom: "40px",
            right: "80px",
            fontSize: "16px",
            color: "rgba(255,255,255,0.15)",
          }}
        >
          ghost.validia.ai
        </span>
      </div>
    ),
    { ...size }
  );
}
