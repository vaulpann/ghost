"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getVulnerabilities } from "@/lib/api";
import type { Vulnerability } from "@/lib/types";
import { RegistryBadge } from "@/components/analysis/registry-badge";
import { RiskBadge } from "@/components/analysis/risk-badge";
import { cn, timeAgo } from "@/lib/utils";

const PER_PAGE = 20;

export default function VulnerabilitiesPage() {
  const [vulns, setVulns] = useState<Vulnerability[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");

  useEffect(() => { setPage(1); }, [severityFilter, categoryFilter]);

  useEffect(() => {
    async function load() {
      try {
        const params = new URLSearchParams();
        if (severityFilter) params.set("severity", severityFilter);
        if (categoryFilter) params.set("category", categoryFilter);
        params.set("page", String(page));
        params.set("per_page", String(PER_PAGE));
        const data = await getVulnerabilities(params.toString());
        setVulns(data.items);
        setTotal(data.total);
      } catch (e) {
        console.error("Failed to fetch vulnerabilities:", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [severityFilter, categoryFilter, page]);

  const totalPages = Math.ceil(total / PER_PAGE);

  return (
    <div className="space-y-6">
      <div className="animate-fade-in">
        <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight gradient-text">Vulnerabilities</h1>
        <p className="text-xs sm:text-sm text-muted-foreground/70 mt-1">{total} confirmed vulnerabilities discovered</p>
      </div>

      {/* Filters */}
      <div className="flex gap-3 animate-fade-in animate-fade-in-delay-1">
        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="rounded-xl glass border-0 bg-foreground/[0.03] px-4 py-2.5 text-[13px] text-foreground/60 focus:outline-none focus:ring-1 focus:ring-ring/20 appearance-none cursor-pointer"
        >
          <option value="">All severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="rounded-xl glass border-0 bg-foreground/[0.03] px-4 py-2.5 text-[13px] text-foreground/60 focus:outline-none focus:ring-1 focus:ring-ring/20 appearance-none cursor-pointer"
        >
          <option value="">All categories</option>
          <option value="rce">RCE</option>
          <option value="sql_injection">SQL Injection</option>
          <option value="command_injection">Command Injection</option>
          <option value="xss">XSS</option>
          <option value="ssrf">SSRF</option>
          <option value="path_traversal">Path Traversal</option>
          <option value="deserialization">Deserialization</option>
          <option value="authentication">Authentication</option>
          <option value="privilege_escalation">Privilege Escalation</option>
          <option value="idor">IDOR</option>
          <option value="xxe">XXE</option>
          <option value="csrf">CSRF</option>
          <option value="open_redirect">Open Redirect</option>
          <option value="race_condition">Race Condition</option>
          <option value="exposed_secrets">Exposed Secrets</option>
        </select>
      </div>

      {/* List */}
      <div className="space-y-2 animate-fade-in animate-fade-in-delay-2">
        {vulns.map((v, i) => (
          <Link
            key={v.id}
            href={`/vulnerabilities/${v.id}`}
            className="group flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 rounded-xl glass glass-hover p-4 animate-fade-in"
            style={{ animationDelay: `${i * 0.03}s` }}
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2.5 mb-1.5 flex-wrap">
                <RiskBadge level={v.severity} size="sm" />
                <span className="font-medium text-[13px] text-foreground/80 group-hover:text-foreground transition-colors">
                  {v.title}
                </span>
              </div>
              <div className="flex items-center gap-2 text-[12px] text-muted-foreground/70">
                <span>{v.package_name}</span>
                {v.package_registry && <RegistryBadge registry={v.package_registry} />}
                {v.cwe_id && <span className="font-mono text-muted-foreground/50">{v.cwe_id}</span>}
                <span className="text-muted-foreground/50">{v.category}{v.subcategory ? ` / ${v.subcategory}` : ""}</span>
              </div>
            </div>
            <div className="flex items-center gap-4 shrink-0">
              {v.cvss_score && (
                <span className={cn(
                  "text-[12px] font-mono font-medium",
                  v.cvss_score >= 9 ? "text-red-400" : v.cvss_score >= 7 ? "text-orange-400" : "text-yellow-400"
                )}>
                  CVSS {v.cvss_score.toFixed(1)}
                </span>
              )}
              {v.poc_code && (
                <span className="text-[10px] text-emerald-400/60 font-mono uppercase">PoC</span>
              )}
              <span className="text-[11px] text-muted-foreground/50 tabular-nums">
                {(v.confidence * 100).toFixed(0)}%
              </span>
              <span className="text-[11px] text-muted-foreground/50 w-14 text-right tabular-nums">
                {timeAgo(v.created_at)}
              </span>
            </div>
          </Link>
        ))}
        {vulns.length === 0 && !loading && (
          <div className="rounded-2xl glass p-12 text-center text-muted-foreground/50 text-sm">
            No vulnerabilities found. Scans will populate this page as they complete.
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between animate-fade-in">
          <p className="text-[12px] text-muted-foreground/50 tabular-nums">
            {(page - 1) * PER_PAGE + 1}–{Math.min(page * PER_PAGE, total)} of {total}
          </p>
          <div className="flex items-center gap-1">
            <button onClick={() => setPage(1)} disabled={page === 1} className="px-2.5 py-1.5 rounded-lg text-[12px] text-muted-foreground/70 hover:text-foreground/60 hover:bg-foreground/[0.03] disabled:opacity-20 disabled:cursor-not-allowed transition-all">First</button>
            <button onClick={() => setPage(page - 1)} disabled={page === 1} className="px-2.5 py-1.5 rounded-lg text-[12px] text-muted-foreground/70 hover:text-foreground/60 hover:bg-foreground/[0.03] disabled:opacity-20 disabled:cursor-not-allowed transition-all">Prev</button>
            <button onClick={() => setPage(page + 1)} disabled={page === totalPages} className="px-2.5 py-1.5 rounded-lg text-[12px] text-muted-foreground/70 hover:text-foreground/60 hover:bg-foreground/[0.03] disabled:opacity-20 disabled:cursor-not-allowed transition-all">Next</button>
            <button onClick={() => setPage(totalPages)} disabled={page === totalPages} className="px-2.5 py-1.5 rounded-lg text-[12px] text-muted-foreground/70 hover:text-foreground/60 hover:bg-foreground/[0.03] disabled:opacity-20 disabled:cursor-not-allowed transition-all">Last</button>
          </div>
        </div>
      )}
    </div>
  );
}
