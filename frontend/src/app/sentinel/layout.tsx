import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sentinel — Supply Chain Security Game",
  description: "Can you spot the supply chain attack? Inspect packages, find threats, protect the ecosystem.",
};

export default function SentinelLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="!bg-white !text-[#1a1a2e] min-h-screen" style={{ background: "#fff", color: "#1a1a2e" }}>
      {children}
    </div>
  );
}
