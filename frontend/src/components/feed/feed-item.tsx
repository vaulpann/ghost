import Link from "next/link";
import type { FeedItem as FeedItemType } from "@/lib/types";
import { timeAgo } from "@/lib/utils";
import { RiskBadge } from "@/components/analysis/risk-badge";
import { RegistryBadge } from "@/components/analysis/registry-badge";

interface FeedItemProps {
  item: FeedItemType;
  index?: number;
}

export function FeedItem({ item, index = 0 }: FeedItemProps) {
  return (
    <Link
      href={`/analyses/${item.id}`}
      className="group flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 rounded-xl glass glass-hover p-4 animate-fade-in"
      style={{ animationDelay: `${index * 0.03}s` }}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 sm:gap-2.5 mb-1 sm:mb-1.5 flex-wrap">
          <span className="font-medium text-[13px] text-white/90 group-hover:text-white transition-colors">
            {item.package_name}
          </span>
          <RegistryBadge registry={item.package_registry} />
          <span className="text-[11px] text-white/20 font-mono">{item.version_string}</span>
        </div>
        <p className="text-[12px] text-white/35 truncate leading-relaxed">
          {item.summary || `Version ${item.version_string} analyzed`}
        </p>
      </div>

      <div className="flex items-center gap-3 sm:gap-4 shrink-0">
        {item.finding_count > 0 && (
          <span className="text-[11px] text-white/25 tabular-nums">
            {item.finding_count} finding{item.finding_count !== 1 ? "s" : ""}
          </span>
        )}
        <RiskBadge level={item.risk_level} score={item.risk_score} />
        <span className="text-[11px] text-white/20 w-14 text-right tabular-nums">
          {timeAgo(item.created_at)}
        </span>
      </div>
    </Link>
  );
}
