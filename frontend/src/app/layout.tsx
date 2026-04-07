import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/sidebar";
import { ThemeProvider } from "@/components/layout/theme-provider";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Ghost Resolver — Can you spot the supply chain attack?",
  description:
    "Real packages. Real diffs. Inspect the evidence and decide — safe or compromised? A daily challenge that gamifies supply chain threat detection across npm, PyPI, and GitHub.",
  metadataBase: new URL("https://ghost.validia.ai"),
  icons: {
    icon: "/favicon.png",
    apple: "/favicon.png",
  },
  openGraph: {
    title: "Ghost Resolver — Can you spot the supply chain attack?",
    description:
      "Real packages. Real diffs. Inspect the evidence and make your call. A daily challenge gamifying supply chain security for developers.",
    url: "https://ghost.validia.ai",
    siteName: "Ghost",
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Ghost Resolver — Can you spot the supply chain attack?",
    description:
      "Real packages. Real diffs. A daily supply chain security challenge. Can you tell safe updates from compromised ones?",
    creator: "@pjvann",
    site: "@pjvann",
  },
  robots: {
    index: true,
    follow: true,
  },
  keywords: [
    "supply chain security",
    "supply chain security game",
    "npm security",
    "pypi security",
    "package analysis",
    "dependency scanning",
    "software supply chain",
    "threat intelligence",
    "malicious packages",
    "typosquatting detection",
    "open source security",
    "security challenge",
    "ctf",
    "gamified security",
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
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <ThemeProvider>
          <div className="flex flex-col md:flex-row h-screen overflow-hidden">
            <Sidebar />
            <main className="flex-1 overflow-y-auto">
              <div className="px-4 py-4 sm:px-6 sm:py-6 md:px-8 md:py-8 h-full">{children}</div>
            </main>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
