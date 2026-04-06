import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sentinel — Supply Chain Security Game",
  description: "Can you spot the supply chain attack?",
};

export default function SentinelLayout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ background: "#f7f7f7", color: "#111", minHeight: "100vh", position: "relative" }}>
      {children}
    </div>
  );
}
