import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/sidebar";
import { ThemeProvider } from "@/components/layout/theme-provider";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Ghost Resolver | Can you spot the supply chain attack?",
  description:
    "A daily challenge that gamifies supply chain threat detection. Real packages, real diffs, real npm and PyPI data. Review 6 dimensions of evidence and make the call: safe or compromised?",
  metadataBase: new URL("https://ghost.validia.ai"),
  icons: {
    icon: "/favicon.png",
    apple: "/favicon.png",
  },
  openGraph: {
    title: "Ghost Resolver | Can you spot the supply chain attack?",
    description:
      "A daily challenge gamifying supply chain security. Real packages, real diffs. Review the evidence and make the call.",
    url: "https://ghost.validia.ai",
    siteName: "Ghost Resolver",
    locale: "en_US",
    type: "website",
    images: [
      {
        url: "/opengraph-image",
        width: 1200,
        height: 630,
        alt: "Ghost Resolver - Can you spot the supply chain attack?",
        type: "image/png",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Ghost Resolver | Can you spot the supply chain attack?",
    description:
      "A daily supply chain security challenge. Real packages, real diffs. Can you tell safe updates from compromised ones?",
    creator: "@pjvann",
    site: "@pjvann",
    images: ["/opengraph-image"],
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
  other: {
    // LinkedIn-specific
    "linkedin:card": "summary_large_image",
    // Force cache refresh
    "og:updated_time": new Date().toISOString(),
  },
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
