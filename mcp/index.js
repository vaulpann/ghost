#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

// Default to the public Ghost API. Override with GHOST_API_URL for self-hosted instances.
const GHOST_API = process.env.GHOST_API_URL || "http://localhost:8000";

async function ghostFetch(path) {
  const res = await fetch(`${GHOST_API}${path}`);
  if (!res.ok) throw new Error(`Ghost API error: ${res.status}`);
  return res.json();
}

const server = new McpServer({
  name: "ghost",
  version: "0.1.0",
});

// Tool 1: Check if a specific package has any recent security findings
server.tool(
  "check_package",
  "Check a package for recent supply chain security threats. Use this BEFORE adding any dependency to your project.",
  {
    name: z.string().describe("Package name (e.g., 'axios', 'requests', 'lodash')"),
    registry: z.enum(["npm", "pypi", "github"]).optional().describe("Package registry. Defaults to searching all."),
  },
  async ({ name, registry }) => {
    // Search for the package
    const params = new URLSearchParams({ search: name, per_page: "5" });
    if (registry) params.set("registry", registry);
    const packages = await ghostFetch(`/api/v1/packages?${params}`);

    const match = packages.items.find(
      (p) => p.name === name || p.name.endsWith(`/${name}`)
    );

    if (!match) {
      return {
        content: [
          {
            type: "text",
            text: `Package "${name}" is not currently monitored by Ghost. It may still be safe — Ghost monitors the top 500+ most critical packages. Visit ghost.validia.ai for the full watchlist.`,
          },
        ],
      };
    }

    // Get versions and check for analyses
    const versions = await ghostFetch(`/api/v1/packages/${match.id}/versions`);

    if (versions.items.length === 0) {
      return {
        content: [
          {
            type: "text",
            text: `✅ **${match.name}** (${match.registry}) — v${match.latest_known_version}\nMonitored by Ghost. No version changes detected yet. Currently considered safe.`,
          },
        ],
      };
    }

    // Get the latest analysis
    const latestVersion = versions.items[0];
    if (!latestVersion.has_analysis) {
      return {
        content: [
          {
            type: "text",
            text: `✅ **${match.name}** (${match.registry}) — v${match.latest_known_version}\nMonitored by Ghost. Latest version pending analysis.`,
          },
        ],
      };
    }

    const riskScore = latestVersion.risk_score || 0;
    const riskLevel = latestVersion.risk_level || "none";

    let emoji = "✅";
    let status = "Safe";
    if (riskScore >= 7) { emoji = "🚨"; status = "CRITICAL THREAT"; }
    else if (riskScore >= 4) { emoji = "⚠️"; status = "SUSPICIOUS — review before using"; }
    else if (riskScore >= 2.5) { emoji = "🔍"; status = "Minor concern — probably fine"; }

    return {
      content: [
        {
          type: "text",
          text: `${emoji} **${match.name}** (${match.registry}) — v${match.latest_known_version}\nRisk: ${riskScore.toFixed(1)}/10 (${riskLevel}) — ${status}\nLast checked: ${match.last_checked_at || "unknown"}\nDetails: https://ghost.validia.ai/analyses`,
        },
      ],
    };
  }
);

// Tool 2: Get recent high-risk alerts across all packages
server.tool(
  "get_threat_alerts",
  "Get recent supply chain threat alerts from Ghost. Shows any packages with elevated risk scores.",
  {
    min_score: z.number().optional().describe("Minimum risk score to show (default: 2.5)"),
    limit: z.number().optional().describe("Max results (default: 10)"),
  },
  async ({ min_score = 2.5, limit = 10 }) => {
    const analyses = await ghostFetch(`/api/v1/analyses?per_page=${limit}`);

    const flagged = analyses.items.filter(
      (a) => (a.risk_score || 0) >= min_score
    );

    if (flagged.length === 0) {
      const stats = await ghostFetch("/api/v1/stats");
      return {
        content: [
          {
            type: "text",
            text: `✅ No active threats detected.\nGhost is monitoring ${stats.total_packages} packages across npm, PyPI, and GitHub.\n${stats.total_analyses} analyses completed. All clear.`,
          },
        ],
      };
    }

    const lines = flagged.map((a) => {
      const score = (a.risk_score || 0).toFixed(1);
      let emoji = "🔍";
      if (a.risk_score >= 7) emoji = "🚨";
      else if (a.risk_score >= 4) emoji = "⚠️";
      return `${emoji} **${a.package_name}** (${a.package_registry}) — ${score}/10\n   ${a.version_string} — ${a.summary || "No summary"}`;
    });

    return {
      content: [
        {
          type: "text",
          text: `Found ${flagged.length} package(s) with elevated risk:\n\n${lines.join("\n\n")}\n\nDetails: https://ghost.validia.ai`,
        },
      ],
    };
  }
);

// Tool 3: Get Ghost monitoring stats
server.tool(
  "ghost_status",
  "Get Ghost supply chain monitoring status — how many packages are monitored, total analyses, and current threat level.",
  {},
  async () => {
    const stats = await ghostFetch("/api/v1/stats");
    return {
      content: [
        {
          type: "text",
          text: `Ghost Supply Chain Monitor\n\nPackages monitored: ${stats.total_packages}\nTotal analyses: ${stats.total_analyses}\nAnalyses today: ${stats.analyses_today}\nFlagged (score ≥ 2.5): ${stats.flagged_count}\nCritical (score ≥ 5.0): ${stats.critical_count}\nAvg risk score: ${stats.avg_risk_score?.toFixed(2) || "0.00"}\n\nVulnerability Scans: ${stats.total_vulnerability_scans || 0}\nConfirmed Vulnerabilities: ${stats.total_vulnerabilities || 0}\nCritical/High Vulns: ${stats.critical_vulnerabilities || 0}\n\nDashboard: https://ghost.validia.ai`,
        },
      ],
    };
  }
);

// Tool 4: Check vulnerabilities for a package
server.tool(
  "check_vulnerabilities",
  "Check if a package has any known vulnerabilities discovered by Ghost's deep codebase audit (RCE, SQLi, XSS, SSRF, etc). Use this BEFORE adding dependencies to catch known vulns.",
  {
    name: z.string().describe("Package name (e.g., 'axios', 'requests', 'lodash')"),
    registry: z.enum(["npm", "pypi", "github"]).optional().describe("Package registry"),
    severity: z.enum(["critical", "high", "medium", "low"]).optional().describe("Minimum severity"),
  },
  async ({ name, registry, severity }) => {
    const params = new URLSearchParams({ per_page: "20" });
    if (severity) params.set("severity", severity);

    // First find the package
    const searchParams = new URLSearchParams({ search: name, per_page: "5" });
    if (registry) searchParams.set("registry", registry);
    const packages = await ghostFetch(`/api/v1/packages?${searchParams}`);
    const match = packages.items.find((p) => p.name === name || p.name.endsWith(`/${name}`));

    if (!match) {
      return { content: [{ type: "text", text: `Package "${name}" is not monitored by Ghost.` }] };
    }

    // Get vulnerabilities for this package
    const vulns = await ghostFetch(`/api/v1/packages/${match.id}/vulnerabilities`);

    if (!vulns || vulns.length === 0) {
      return {
        content: [{
          type: "text",
          text: `✅ **${match.name}** (${match.registry}) — No known vulnerabilities.\nMonitored by Ghost with deep codebase auditing.`,
        }],
      };
    }

    const filtered = severity ? vulns.filter((v) => v.severity === severity) : vulns;
    const lines = filtered.slice(0, 10).map((v) => {
      let emoji = "🔍";
      if (v.severity === "critical") emoji = "🚨";
      else if (v.severity === "high") emoji = "⚠️";
      return `${emoji} **[${v.severity.toUpperCase()}]** ${v.title}\n   ${v.category}${v.cwe_id ? ` (${v.cwe_id})` : ""} — ${v.file_path || "unknown file"}${v.cvss_score ? ` — CVSS ${v.cvss_score.toFixed(1)}` : ""}${v.poc_code ? " — PoC available" : ""}`;
    });

    return {
      content: [{
        type: "text",
        text: `Found ${filtered.length} vulnerability(s) in **${match.name}** (${match.registry}):\n\n${lines.join("\n\n")}\n\nDetails: https://ghost.validia.ai/vulnerabilities`,
      }],
    };
  }
);

// Tool 5: Get vulnerability detail with PoC
server.tool(
  "get_vulnerability_detail",
  "Get full details of a specific vulnerability including proof-of-concept exploit code. Use after check_vulnerabilities to get the full picture.",
  {
    vulnerability_id: z.string().describe("Vulnerability UUID from check_vulnerabilities"),
  },
  async ({ vulnerability_id }) => {
    try {
      const vuln = await ghostFetch(`/api/v1/vulnerabilities/${vulnerability_id}`);
      const parts = [
        `**${vuln.title}** [${vuln.severity.toUpperCase()}]`,
        `Package: ${vuln.package_name} (${vuln.package_registry})`,
        `Category: ${vuln.category}${vuln.subcategory ? ` / ${vuln.subcategory}` : ""}`,
        vuln.cwe_id ? `CWE: ${vuln.cwe_id}` : null,
        vuln.cvss_score ? `CVSS: ${vuln.cvss_score.toFixed(1)}` : null,
        `Confidence: ${(vuln.confidence * 100).toFixed(0)}%`,
        "",
        `**Description:** ${vuln.description}`,
      ];

      if (vuln.file_path) parts.push(`\n**Location:** \`${vuln.file_path}\` L${vuln.line_start || "?"}–${vuln.line_end || "?"}`);
      if (vuln.code_snippet) parts.push(`\n**Vulnerable Code:**\n\`\`\`\n${vuln.code_snippet}\n\`\`\``);
      if (vuln.attack_vector) parts.push(`\n**Attack Vector:** ${vuln.attack_vector}`);
      if (vuln.impact) parts.push(`\n**Impact:** ${vuln.impact}`);
      if (vuln.poc_code) parts.push(`\n**Proof of Concept:**\n${vuln.poc_description || ""}\n\`\`\`\n${vuln.poc_code}\n\`\`\``);
      if (vuln.remediation) parts.push(`\n**Remediation:** ${vuln.remediation}`);

      return { content: [{ type: "text", text: parts.filter(Boolean).join("\n") }] };
    } catch (e) {
      return { content: [{ type: "text", text: `Vulnerability not found: ${vulnerability_id}` }] };
    }
  }
);

// Start
const transport = new StdioServerTransport();
await server.connect(transport);
