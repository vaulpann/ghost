import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/sidebar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Ghost — Supply Chain Threat Intelligence",
  description:
    "Real-time LLM-powered analysis of npm, PyPI, and GitHub package releases. Detect supply chain attacks — malicious dependencies, obfuscated code, and backdoors — before they spread.",
  metadataBase: new URL("https://ghost.validia.ai"),
  icons: {
    icon: "/favicon.png",
    apple: "/favicon.png",
  },
  openGraph: {
    title: "Ghost — Supply Chain Threat Intelligence",
    description:
      "Real-time LLM-powered analysis of npm, PyPI, and GitHub package releases. Detect supply chain attacks before they spread.",
    url: "https://ghost.validia.ai",
    siteName: "Ghost",
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Ghost — Supply Chain Threat Intelligence",
    description:
      "Real-time LLM-powered analysis of npm, PyPI, and GitHub package releases. Detect supply chain attacks before they spread.",
    creator: "@pjvann",
    site: "@pjvann",
  },
  robots: {
    index: true,
    follow: true,
  },
  keywords: [
    "supply chain security",
    "npm security",
    "pypi security",
    "package analysis",
    "dependency scanning",
    "software supply chain",
    "threat intelligence",
    "malicious packages",
    "typosquatting detection",
    "open source security",
  ],
  authors: [{ name: "Paul Vann", url: "https://x.com/pjvann" }],
  creator: "Validia",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <div className="flex flex-col md:flex-row h-screen overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-y-auto">
            <div className="px-4 py-4 sm:px-6 sm:py-6 md:px-8 md:py-8 h-full">{children}</div>
          </main>
        </div>
      </body>
    </html>
  );
}
