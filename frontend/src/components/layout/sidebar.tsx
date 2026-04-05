"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useTheme } from "@/components/layout/theme-provider";

const navigation = [
  { name: "Overview", href: "/", icon: "O" },
  { name: "Watchlist", href: "/packages", icon: "W" },
  { name: "Vulns", href: "/vulnerabilities", icon: "!" },
  { name: "Analyses", href: "/analyses", icon: "A" },
];

const socials = [
  {
    name: "FrontierSec",
    href: "https://join.slack.com/t/frontiersec/shared_invite/zt-3s0tfehvr-Qjqa1w8ITe7O7zZcd_23ag",
    icon: (
      <svg viewBox="0 0 24 24" className="w-4 h-4 fill-current">
        <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zm1.271 0a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zm0 1.271a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zm10.124 2.521a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.52 2.521h-2.522V8.834zm-1.268 0a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.167 0a2.528 2.528 0 0 1 2.523 2.522v6.312zm-2.523 10.124a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.167 24a2.527 2.527 0 0 1-2.52-2.52v-2.523h2.52zm0-1.268a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.167a2.528 2.528 0 0 1-2.52 2.523h-6.313z" />
      </svg>
    ),
  },
  {
    name: "@pjvann",
    href: "https://x.com/pjvann",
    icon: (
      <svg viewBox="0 0 24 24" className="w-3.5 h-3.5 fill-current">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
      </svg>
    ),
  },
  {
    name: "@vaulpann",
    href: "https://github.com/vaulpann",
    icon: (
      <svg viewBox="0 0 24 24" className="w-4 h-4 fill-current">
        <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
      </svg>
    ),
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();

  const sidebarContent = (
    <>
      {/* Logo */}
      <div className="flex h-14 sm:h-16 items-center justify-between px-4 sm:px-5">
        <div className="flex items-center gap-2.5">
          <img src="/ghost-logo.png" alt="Versatility Labs" className="h-7 w-7 sm:h-8 sm:w-8" />
          <div>
            <h1 className="text-[15px] font-semibold tracking-tight">Ghost</h1>
            <p className="text-[10px] text-muted-foreground/70 tracking-wider uppercase">Supply Chain Intel</p>
          </div>
        </div>
        {/* Close button on mobile */}
        <button
          onClick={() => setMobileOpen(false)}
          className="md:hidden p-1 text-muted-foreground/70 hover:text-foreground/60"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 pt-4 space-y-0.5">
        {navigation.map((item) => {
          const isActive =
            item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link
              key={item.name}
              href={item.href}
              onClick={() => setMobileOpen(false)}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-[13px] font-medium transition-all duration-200",
                isActive
                  ? "bg-foreground/[0.07] text-foreground"
                  : "text-muted-foreground hover:text-foreground/70 hover:bg-foreground/[0.03]"
              )}
            >
              <span
                className={cn(
                  "flex h-6 w-6 items-center justify-center rounded-md text-[11px] font-semibold transition-colors",
                  isActive
                    ? "bg-emerald-500/20 text-emerald-400"
                    : "bg-foreground/[0.04] text-muted-foreground/70"
                )}
              >
                {item.icon}
              </span>
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Social links */}
      <div className="px-3 pb-4 space-y-1">
        <div className="border-t border-[hsl(var(--sidebar-border))] pt-4 mb-2" />
        <a
          href={socials[0].href}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-[12px] text-emerald-400/70 hover:text-emerald-400 bg-emerald-500/[0.06] hover:bg-emerald-500/10 border border-emerald-500/10 transition-all"
        >
          {socials[0].icon}
          <span className="flex-1">FrontierSec</span>
          <span className="text-[9px] uppercase tracking-widest text-emerald-400/50 font-medium">Get Alerts</span>
        </a>
        {socials.slice(1).map((s) => (
          <a
            key={s.name}
            href={s.href}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2.5 rounded-lg px-3 py-1.5 text-[12px] text-muted-foreground/70 hover:text-foreground/60 transition-colors"
          >
            {s.icon}
            <span>{s.name}</span>
          </a>
        ))}
        <a
          href="mailto:paul@validia.ai?subject=Ghost%20—%20Package%20Request"
          className="flex items-center gap-2.5 rounded-lg px-3 py-1.5 text-[12px] text-muted-foreground/70 hover:text-foreground/60 transition-colors"
        >
          <svg viewBox="0 0 24 24" className="w-3.5 h-3.5 fill-current">
            <path d="M1.5 8.67v8.58a3 3 0 003 3h15a3 3 0 003-3V8.67l-8.928 5.493a3 3 0 01-3.144 0L1.5 8.67z" />
            <path d="M22.5 6.908V6.75a3 3 0 00-3-3h-15a3 3 0 00-3 3v.158l9.714 5.978a1.5 1.5 0 001.572 0L22.5 6.908z" />
          </svg>
          <span className="flex-1">Suggest a package</span>
        </a>
        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className="flex items-center gap-2.5 rounded-lg px-3 py-1.5 text-[12px] text-muted-foreground hover:text-foreground/60 transition-colors w-full"
        >
          {theme === "dark" ? (
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" />
            </svg>
          ) : (
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z" />
            </svg>
          )}
          <span>{theme === "dark" ? "Light mode" : "Dark mode"}</span>
        </button>
        <p className="px-3 pt-3 text-[10px] text-muted-foreground/30">v0.1.0</p>
      </div>
    </>
  );

  return (
    <>
      {/* Mobile header bar */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-40 flex h-14 items-center gap-3 border-b border-[hsl(var(--sidebar-border))] bg-[hsl(var(--sidebar-bg))] px-4">
        <button
          onClick={() => setMobileOpen(true)}
          className="p-1 text-foreground/50 hover:text-foreground/80"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <img src="/ghost-logo.png" alt="Versatility Labs" className="h-6 w-6" />
        <span className="text-[14px] font-semibold">Ghost</span>
      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="md:hidden fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar — desktop: always visible, mobile: slide in */}
      <div
        className={cn(
          "flex flex-col border-r border-[hsl(var(--sidebar-border))] bg-[hsl(var(--sidebar-bg))] z-50",
          // Desktop
          "hidden md:flex md:w-60",
          // Mobile: overlay drawer
          mobileOpen && "!flex fixed inset-y-0 left-0 w-64"
        )}
      >
        {sidebarContent}
      </div>

      {/* Spacer for mobile header */}
      <div className="md:hidden h-14 shrink-0" />
    </>
  );
}
