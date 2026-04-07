import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Resolver — Supply Chain Security Game",
  description: "Can you spot the supply chain attack?",
};

export default function SentinelLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
      <div style={{ background: "hsl(0 0% 98%)", color: "#111", minHeight: "100vh", fontFamily: "'Inter Tight', -apple-system, sans-serif" }}>
        {children}
      </div>
    </>
  );
}
