import { cn } from "@/lib/utils";

interface RiskBadgeProps {
  level: string | null;
  score?: number | null;
  size?: "sm" | "md" | "lg";
}

const styles: Record<string, string> = {
  critical: "bg-red-500/10 text-red-400 border-red-500/20 ring-1 ring-red-500/10",
  high: "bg-orange-500/10 text-orange-400 border-orange-500/20 ring-1 ring-orange-500/10",
  medium: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20 ring-1 ring-yellow-500/10",
  low: "bg-blue-500/10 text-blue-400 border-blue-500/20 ring-1 ring-blue-500/10",
  none: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20 ring-1 ring-emerald-500/10",
};

export function RiskBadge({ level, score, size = "md" }: RiskBadgeProps) {
  const label = !level || level === "none" ? "Clean" : level.charAt(0).toUpperCase() + level.slice(1);

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border font-medium tracking-wide",
        styles[level || "none"] || styles.none,
        level === "critical" && "animate-pulse-critical",
        size === "sm" && "px-2 py-0.5 text-[10px]",
        size === "md" && "px-2.5 py-0.5 text-[11px]",
        size === "lg" && "px-3 py-1 text-xs"
      )}
    >
      <span
        className={cn(
          "rounded-full",
          size === "sm" && "h-1 w-1",
          size === "md" && "h-1.5 w-1.5",
          size === "lg" && "h-1.5 w-1.5",
          level === "critical" && "bg-red-400",
          level === "high" && "bg-orange-400",
          level === "medium" && "bg-yellow-400",
          level === "low" && "bg-blue-400",
          (!level || level === "none") && "bg-emerald-400"
        )}
      />
      {label}
      {score !== undefined && score !== null && (
        <span className="font-mono opacity-70">{score.toFixed(1)}</span>
      )}
    </span>
  );
}
