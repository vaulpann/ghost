#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const GHOST_API = process.env.GHOST_API_URL || "https://ghost-api-495743911277.us-central1.run.app";

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
          text: `Ghost Supply Chain Monitor\n\nPackages monitored: ${stats.total_packages}\nTotal analyses: ${stats.total_analyses}\nAnalyses today: ${stats.analyses_today}\nFlagged (score ≥ 2.5): ${stats.flagged_count}\nCritical (score ≥ 5.0): ${stats.critical_count}\nAvg risk score: ${stats.avg_risk_score?.toFixed(2) || "0.00"}\n\nDashboard: https://ghost.validia.ai`,
        },
      ],
    };
  }
);

// Start
const transport = new StdioServerTransport();
await server.connect(transport);
