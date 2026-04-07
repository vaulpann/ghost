"use client";

import { useEffect } from "react";

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Clear any cached dark mode preference
    localStorage.removeItem("ghost-theme");
    document.documentElement.classList.remove("dark");
  }, []);

  return <>{children}</>;
}
