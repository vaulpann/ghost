import { cn } from "@/lib/utils";

interface RegistryBadgeProps {
  registry: string;
}

const REGISTRY_CONFIG: Record<string, { label: string; color: string }> = {
  npm: { label: "npm", color: "text-red-400/70 bg-red-500/5 border-red-500/10" },
  pypi: { label: "PyPI", color: "text-sky-400/70 bg-sky-500/5 border-sky-500/10" },
  github: { label: "GitHub", color: "text-violet-400/70 bg-violet-500/5 border-violet-500/10" },
};

export function RegistryBadge({ registry }: RegistryBadgeProps) {
  const config = REGISTRY_CONFIG[registry] || { label: registry, color: "text-muted-foreground bg-foreground/5 border-border" };

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-1.5 py-0.5 text-[10px] font-mono font-medium tracking-wider",
        config.color
      )}
    >
      {config.label}
    </span>
  );
}
