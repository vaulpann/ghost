import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "Ghost Resolver — Can you spot the supply chain attack?";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          background: "#fafafa",
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "80px",
          fontFamily: "system-ui, sans-serif",
          position: "relative",
        }}
      >
        {/* Top accent */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: "5px",
            background: "#1e3a5f",
          }}
        />

        {/* Ghost branding */}
        <div style={{ display: "flex", alignItems: "center", gap: "14px", marginBottom: "36px" }}>
          <div
            style={{
              width: "48px",
              height: "48px",
              borderRadius: "12px",
              background: "#1e3a5f",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "24px",
              fontWeight: 800,
              color: "#fff",
            }}
          >
            G
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span style={{ fontSize: "28px", fontWeight: 700, color: "#111", letterSpacing: "-0.5px" }}>
              Ghost Resolver
            </span>
            <span style={{ fontSize: "13px", fontWeight: 500, color: "#999", letterSpacing: "3px", textTransform: "uppercase" as const }}>
              Supply Chain Security
            </span>
          </div>
        </div>

        {/* Main headline */}
        <h1
          style={{
            fontSize: "56px",
            fontWeight: 800,
            color: "#111",
            lineHeight: 1.1,
            margin: 0,
            maxWidth: "800px",
            letterSpacing: "-1.5px",
          }}
        >
          Can you spot the supply chain attack?
        </h1>

        {/* Subtitle */}
        <p
          style={{
            fontSize: "22px",
            fontWeight: 400,
            color: "#888",
            lineHeight: 1.5,
            maxWidth: "650px",
            marginTop: "20px",
          }}
        >
          Real packages. Real diffs. Review the evidence and make your call — safe or compromised?
        </p>

        {/* Tags */}
        <div
          style={{
            display: "flex",
            gap: "12px",
            marginTop: "40px",
          }}
        >
          {["npm", "PyPI", "GitHub"].map((tag) => (
            <div
              key={tag}
              style={{
                padding: "8px 20px",
                borderRadius: "100px",
                background: "#fff",
                border: "1px solid #e0e0e0",
                fontSize: "15px",
                fontWeight: 600,
                color: "#555",
              }}
            >
              {tag}
            </div>
          ))}
          <div
            style={{
              padding: "8px 20px",
              borderRadius: "100px",
              background: "#1e3a5f",
              fontSize: "15px",
              fontWeight: 600,
              color: "#fff",
            }}
          >
            Play Free
          </div>
        </div>

        {/* URL */}
        <span
          style={{
            position: "absolute",
            bottom: "36px",
            right: "80px",
            fontSize: "16px",
            color: "#ccc",
          }}
        >
          ghost.validia.ai
        </span>
      </div>
    ),
    { ...size }
  );
}
