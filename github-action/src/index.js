#!/usr/bin/env node

/**
 * Ghost Supply Chain Scanner — GitHub Action
 *
 * Scans project dependencies for supply chain threats using the Ghost API.
 * Uses only Node.js built-in modules (no npm install required).
 */

const fs = require("fs");
const path = require("path");
const https = require("https");
const http = require("http");
const { execSync } = require("child_process");

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const API_URL = process.env.GHOST_API_URL || "https://ghost-api-495743911277.us-central1.run.app";
const FAIL_ON = (process.env.GHOST_FAIL_ON || "critical").toLowerCase();
const GITHUB_TOKEN = process.env.GITHUB_TOKEN || "";
const GITHUB_REPOSITORY = process.env.GITHUB_REPOSITORY || "";
const GITHUB_EVENT_NAME = process.env.GITHUB_EVENT_NAME || "";
const GITHUB_STEP_SUMMARY = process.env.GITHUB_STEP_SUMMARY || "";
const GITHUB_WORKSPACE = process.env.GITHUB_WORKSPACE || process.cwd();

const SEVERITY_ORDER = { critical: 4, high: 3, medium: 2, low: 1, none: 0 };
const COMMENT_MARKER = "<!-- ghost-supply-chain-scan -->";
const MAX_LOCKFILE_DEPTH = 3;

// ---------------------------------------------------------------------------
// Logging helpers
// ---------------------------------------------------------------------------

function info(msg) {
  console.log(`\x1b[34m[ghost]\x1b[0m ${msg}`);
}

function warn(msg) {
  console.log(`::warning::${msg}`);
}

function error(msg) {
  console.log(`::error::${msg}`);
}

// ---------------------------------------------------------------------------
// HTTP helper — works with both http and https, follows redirects
// ---------------------------------------------------------------------------

function request(url, options = {}, body = null) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const lib = parsed.protocol === "https:" ? https : http;

    const req = lib.request(
      url,
      {
        method: options.method || "GET",
        headers: options.headers || {},
        timeout: 60000,
      },
      (res) => {
        // Follow redirects
        if ([301, 302, 307, 308].includes(res.statusCode) && res.headers.location) {
          return resolve(request(res.headers.location, options, body));
        }

        let data = "";
        res.on("data", (chunk) => (data += chunk));
        res.on("end", () => resolve({ status: res.statusCode, body: data, headers: res.headers }));
      }
    );

    req.on("error", reject);
    req.on("timeout", () => {
      req.destroy();
      reject(new Error("Request timed out"));
    });

    if (body) req.write(body);
    req.end();
  });
}

// ---------------------------------------------------------------------------
// Lock file discovery
// ---------------------------------------------------------------------------

const LOCKFILE_MAP = {
  "package-lock.json": "npm",
  "yarn.lock": "yarn",
  "pnpm-lock.yaml": "pnpm",
  "requirements.txt": "python",
  "Pipfile.lock": "python",
  "poetry.lock": "python",
};

/**
 * Recursively find lock files up to MAX_LOCKFILE_DEPTH.
 */
function findLockFiles(root, depth = 0) {
  const results = [];
  if (depth > MAX_LOCKFILE_DEPTH) return results;

  let entries;
  try {
    entries = fs.readdirSync(root, { withFileTypes: true });
  } catch {
    return results;
  }

  for (const entry of entries) {
    if (entry.name.startsWith(".") || entry.name === "node_modules" || entry.name === "__pycache__") {
      continue;
    }

    const fullPath = path.join(root, entry.name);

    if (entry.isFile() && LOCKFILE_MAP[entry.name]) {
      results.push({
        path: fullPath,
        relativePath: path.relative(root === GITHUB_WORKSPACE ? root : GITHUB_WORKSPACE, fullPath),
        type: LOCKFILE_MAP[entry.name],
        filename: entry.name,
      });
    }

    if (entry.isDirectory()) {
      results.push(...findLockFiles(fullPath, depth + 1));
    }
  }

  return results;
}

// ---------------------------------------------------------------------------
// Dependency parsers
// ---------------------------------------------------------------------------

function parseNpmLockfile(content) {
  const deps = [];
  try {
    const lock = JSON.parse(content);

    // npm v2+ lockfile format (lockfileVersion >= 2) uses "packages"
    if (lock.packages) {
      for (const [pkgPath, info] of Object.entries(lock.packages)) {
        if (!pkgPath) continue; // skip the root entry ""
        // pkgPath looks like "node_modules/lodash" or "node_modules/@scope/pkg"
        const name = pkgPath.replace(/^.*node_modules\//, "");
        if (name && info.version) {
          deps.push({ name, version: info.version, ecosystem: "npm" });
        }
      }
    }

    // npm v1 lockfile format uses "dependencies"
    if (deps.length === 0 && lock.dependencies) {
      const walk = (depMap) => {
        for (const [name, info] of Object.entries(depMap)) {
          if (info.version) {
            deps.push({ name, version: info.version, ecosystem: "npm" });
          }
          if (info.dependencies) walk(info.dependencies);
        }
      };
      walk(lock.dependencies);
    }
  } catch (e) {
    warn(`Failed to parse package-lock.json: ${e.message}`);
  }
  return deps;
}

function parseYarnLock(content) {
  const deps = [];
  try {
    // Match patterns like: "lodash@^4.17.0": or lodash@^4.17.0:
    // Followed by a line with "  version "4.17.21""
    const blockRegex = /^"?(.+?)@[^"]*"?:\s*\n\s+version\s+"?([^"\n]+)"?/gm;
    let match;
    while ((match = blockRegex.exec(content)) !== null) {
      const name = match[1];
      const version = match[2];
      if (name && version) {
        deps.push({ name, version, ecosystem: "npm" });
      }
    }
  } catch (e) {
    warn(`Failed to parse yarn.lock: ${e.message}`);
  }
  return deps;
}

function parsePnpmLock(content) {
  const deps = [];
  try {
    // pnpm-lock.yaml has entries like:
    //   /lodash@4.17.21:
    // or in newer format:
    //   lodash@4.17.21:
    const regex = /^\s*\/?(@?[^@\s]+)@(\d[^\s:]*)\s*:/gm;
    let match;
    while ((match = regex.exec(content)) !== null) {
      deps.push({ name: match[1], version: match[2], ecosystem: "npm" });
    }
  } catch (e) {
    warn(`Failed to parse pnpm-lock.yaml: ${e.message}`);
  }
  return deps;
}

function parseRequirementsTxt(content) {
  const deps = [];
  try {
    for (const line of content.split("\n")) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#") || trimmed.startsWith("-")) continue;

      // Match: package==1.0.0 or package>=1.0.0 etc.
      const match = trimmed.match(/^([a-zA-Z0-9._-]+)\s*[=<>!~]=?\s*([a-zA-Z0-9._*-]+)/);
      if (match) {
        deps.push({ name: match[1].toLowerCase(), version: match[2], ecosystem: "pypi" });
      } else {
        // Just a package name, no version pinned
        const nameMatch = trimmed.match(/^([a-zA-Z0-9._-]+)/);
        if (nameMatch) {
          deps.push({ name: nameMatch[1].toLowerCase(), version: "latest", ecosystem: "pypi" });
        }
      }
    }
  } catch (e) {
    warn(`Failed to parse requirements.txt: ${e.message}`);
  }
  return deps;
}

function parsePipfileLock(content) {
  const deps = [];
  try {
    const lock = JSON.parse(content);
    for (const section of ["default", "develop"]) {
      const packages = lock[section] || {};
      for (const [name, info] of Object.entries(packages)) {
        const version = (info.version || "").replace(/^==/, "");
        deps.push({ name: name.toLowerCase(), version: version || "unknown", ecosystem: "pypi" });
      }
    }
  } catch (e) {
    warn(`Failed to parse Pipfile.lock: ${e.message}`);
  }
  return deps;
}

function parsePoetryLock(content) {
  const deps = [];
  try {
    // Parse [[package]] sections
    const packageBlocks = content.split(/\[\[package\]\]/);
    for (const block of packageBlocks) {
      const nameMatch = block.match(/^name\s*=\s*"([^"]+)"/m);
      const versionMatch = block.match(/^version\s*=\s*"([^"]+)"/m);
      if (nameMatch && versionMatch) {
        deps.push({
          name: nameMatch[1].toLowerCase(),
          version: versionMatch[1],
          ecosystem: "pypi",
        });
      }
    }
  } catch (e) {
    warn(`Failed to parse poetry.lock: ${e.message}`);
  }
  return deps;
}

const PARSERS = {
  "package-lock.json": parseNpmLockfile,
  "yarn.lock": parseYarnLock,
  "pnpm-lock.yaml": parsePnpmLock,
  "requirements.txt": parseRequirementsTxt,
  "Pipfile.lock": parsePipfileLock,
  "poetry.lock": parsePoetryLock,
};

// ---------------------------------------------------------------------------
// Git diff — detect new / changed dependencies
// ---------------------------------------------------------------------------

function getBaseBranch() {
  // PR events set GITHUB_BASE_REF
  const baseRef = process.env.GITHUB_BASE_REF || "";
  if (baseRef) return `origin/${baseRef}`;
  return null;
}

/**
 * Parse a git diff of a lockfile to find added dependency names.
 */
function parseAddedFromDiff(diff, lockfileName) {
  const added = new Set();

  const addedLines = diff
    .split("\n")
    .filter((l) => l.startsWith("+") && !l.startsWith("+++"));

  for (const line of addedLines) {
    const content = line.slice(1); // remove the leading "+"

    if (lockfileName === "package-lock.json") {
      // Look for "node_modules/pkg": or "pkg":
      const m = content.match(/"(?:node_modules\/)?(@?[^"]+)"\s*:/);
      if (m) added.add(m[1]);
    } else if (lockfileName === "yarn.lock") {
      const m = content.match(/^"?(.+?)@/);
      if (m) added.add(m[1]);
    } else if (lockfileName === "pnpm-lock.yaml") {
      const m = content.match(/^\s*\/?(@?[^@\s]+)@/);
      if (m) added.add(m[1]);
    } else if (lockfileName === "requirements.txt") {
      const m = content.match(/^([a-zA-Z0-9._-]+)/);
      if (m) added.add(m[1].toLowerCase());
    } else if (lockfileName === "Pipfile.lock") {
      const m = content.match(/"([a-zA-Z0-9._-]+)"\s*:/);
      if (m) added.add(m[1].toLowerCase());
    } else if (lockfileName === "poetry.lock") {
      const m = content.match(/^name\s*=\s*"([^"]+)"/);
      if (m) added.add(m[1].toLowerCase());
    }
  }

  return added;
}

function detectNewDeps(lockfile, deps) {
  const baseBranch = getBaseBranch();
  if (!baseBranch) return deps; // Not a PR — treat all deps as relevant

  try {
    // Make sure we have the base branch ref
    try {
      execSync(`git fetch origin ${process.env.GITHUB_BASE_REF || "main"} --depth=1`, {
        cwd: GITHUB_WORKSPACE,
        stdio: "pipe",
      });
    } catch {
      // May already be fetched
    }

    const diff = execSync(`git diff ${baseBranch} -- "${lockfile.relativePath}"`, {
      cwd: GITHUB_WORKSPACE,
      encoding: "utf-8",
      maxBuffer: 50 * 1024 * 1024, // 50MB for big lockfiles
    });

    if (!diff.trim()) return deps; // No changes to this lockfile

    const addedNames = parseAddedFromDiff(diff, lockfile.filename);
    return deps.map((d) => ({
      ...d,
      is_new: addedNames.has(d.name),
    }));
  } catch (e) {
    info(`Could not diff against base branch: ${e.message}`);
    return deps;
  }
}

// ---------------------------------------------------------------------------
// Ghost API call
// ---------------------------------------------------------------------------

async function callGhostScan(dependencies) {
  const context = GITHUB_EVENT_NAME === "pull_request" ? "pr" : "push";

  // Map ecosystem names to registry names and ensure correct fields
  const mapped = dependencies.map((d) => ({
    name: d.name,
    version: d.version || null,
    registry: d.ecosystem === "python" ? "pypi" : "npm",
    is_new: d.is_new || false,
  }));

  const payload = JSON.stringify({
    dependencies: mapped,
    repository: GITHUB_REPOSITORY,
    context,
  });

  info(`Sending ${dependencies.length} dependencies to Ghost API...`);

  try {
    const res = await request(`${API_URL}/api/v1/scan`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "User-Agent": "ghost-github-action/1.0",
      },
    }, payload);

    if (res.status >= 200 && res.status < 300) {
      return JSON.parse(res.body);
    }

    // If the /scan endpoint doesn't exist yet, fall back to individual lookups
    if (res.status === 404 || res.status === 405) {
      info("Scan endpoint not available, falling back to individual package lookups...");
      return await fallbackPackageLookup(dependencies);
    }

    warn(`Ghost API returned status ${res.status}: ${res.body.slice(0, 200)}`);
    return await fallbackPackageLookup(dependencies);
  } catch (e) {
    warn(`Ghost API request failed: ${e.message}. Falling back to individual lookups.`);
    return await fallbackPackageLookup(dependencies);
  }
}

/**
 * Fallback: look up each package individually via the existing /api/v1/packages endpoint.
 */
async function fallbackPackageLookup(dependencies) {
  const findings = [];
  const checked = [];

  // Only check new deps or a sample to avoid hammering the API
  const toCheck = dependencies.filter((d) => d.is_new);
  const sample = toCheck.length > 0 ? toCheck : dependencies.slice(0, 50);

  for (const dep of sample) {
    try {
      const registry = dep.ecosystem === "pypi" ? "pypi" : "npm";
      const params = new URLSearchParams({ search: dep.name, registry, per_page: "1" });
      const res = await request(`${API_URL}/api/v1/packages?${params}`, {
        headers: { "User-Agent": "ghost-github-action/1.0" },
      });

      if (res.status === 200) {
        const data = JSON.parse(res.body);
        const match = data.items?.find(
          (p) => p.name === dep.name || p.name.endsWith(`/${dep.name}`)
        );

        if (match) {
          // Get versions for this package
          const vRes = await request(`${API_URL}/api/v1/packages/${match.id}/versions?per_page=1`, {
            headers: { "User-Agent": "ghost-github-action/1.0" },
          });

          if (vRes.status === 200) {
            const versions = JSON.parse(vRes.body);
            const latest = versions.items?.[0];

            if (latest && latest.risk_score && latest.risk_score > 30) {
              const riskLevel =
                latest.risk_score >= 80 ? "critical" :
                latest.risk_score >= 60 ? "high" :
                latest.risk_score >= 40 ? "medium" : "low";

              findings.push({
                package: dep.name,
                version: dep.version,
                risk_level: riskLevel,
                risk_score: latest.risk_score,
                summary: latest.risk_summary || `Risk score: ${latest.risk_score}`,
                is_new: dep.is_new || false,
              });
            }
          }
        }

        checked.push(dep.name);
      }
    } catch {
      // Skip individual failures
    }
  }

  return {
    findings,
    total_checked: checked.length,
    total_clean: checked.length - findings.length,
  };
}

// ---------------------------------------------------------------------------
// Output formatting
// ---------------------------------------------------------------------------

function riskEmoji(level) {
  switch (level) {
    case "critical": return "\u{1F534}";  // red circle
    case "high": return "\u{1F7E0}";      // orange circle
    case "medium": return "\u{1F7E1}";    // yellow circle
    case "low": return "\u{1F535}";        // blue circle
    default: return "\u26AA";              // white circle
  }
}

function riskLabel(level) {
  return level.charAt(0).toUpperCase() + level.slice(1);
}

function buildSummary(scanResult, totalDeps) {
  const { findings = [], total_checked = 0, total_clean = 0 } = scanResult;
  const lines = [];

  if (findings.length === 0) {
    lines.push("## \u2705 Ghost Supply Chain Scan");
    lines.push("");
    lines.push(`**No issues found** in ${totalDeps} dependencies`);
    lines.push("");
    lines.push(`${total_checked} dependencies checked, all clean.`);
  } else {
    lines.push("## \u{1F50D} Ghost Supply Chain Scan");
    lines.push("");
    lines.push(`**${findings.length} issue${findings.length !== 1 ? "s" : ""} found** in ${totalDeps} dependencies`);
    lines.push("");
    lines.push("| Package | Version | Risk | Issue |");
    lines.push("|---------|---------|------|-------|");

    for (const f of findings) {
      const emoji = riskEmoji(f.risk_level);
      lines.push(`| ${f.package} | ${f.version} | ${emoji} ${riskLabel(f.risk_level)} | ${f.summary} |`);
    }

    lines.push("");
    lines.push("<details><summary>Full scan details</summary>");
    lines.push("");
    lines.push(`${total_checked} dependencies checked, ${total_clean} clean, ${findings.length} flagged`);
    lines.push("</details>");
  }

  lines.push("");
  lines.push("---");
  lines.push("*Powered by [Ghost](https://ghost.validia.ai) \u2014 Supply Chain Threat Intelligence*");

  return lines.join("\n");
}

// ---------------------------------------------------------------------------
// GitHub Actions summary + PR comment
// ---------------------------------------------------------------------------

function writeSummary(markdown) {
  if (GITHUB_STEP_SUMMARY) {
    try {
      fs.appendFileSync(GITHUB_STEP_SUMMARY, markdown + "\n");
      info("Wrote GitHub Actions step summary.");
    } catch (e) {
      warn(`Failed to write step summary: ${e.message}`);
    }
  }
}

async function getPRNumber() {
  // Try GITHUB_EVENT_PATH first
  const eventPath = process.env.GITHUB_EVENT_PATH;
  if (eventPath) {
    try {
      const event = JSON.parse(fs.readFileSync(eventPath, "utf-8"));
      if (event.pull_request?.number) return event.pull_request.number;
      if (event.number) return event.number;
    } catch {
      // fall through
    }
  }
  return null;
}

async function postOrUpdatePRComment(markdown) {
  if (!GITHUB_TOKEN || !GITHUB_REPOSITORY) {
    info("No token or repository context — skipping PR comment.");
    return;
  }

  const prNumber = await getPRNumber();
  if (!prNumber) {
    info("Not a PR context — skipping PR comment.");
    return;
  }

  const [owner, repo] = GITHUB_REPOSITORY.split("/");
  const apiBase = "https://api.github.com";
  const commentBody = `${COMMENT_MARKER}\n${markdown}`;

  const headers = {
    Authorization: `token ${GITHUB_TOKEN}`,
    Accept: "application/vnd.github.v3+json",
    "User-Agent": "ghost-github-action/1.0",
    "Content-Type": "application/json",
  };

  // Look for an existing Ghost comment to update
  try {
    const listRes = await request(
      `${apiBase}/repos/${owner}/${repo}/issues/${prNumber}/comments?per_page=100`,
      { headers }
    );

    if (listRes.status === 200) {
      const comments = JSON.parse(listRes.body);
      const existing = comments.find((c) => c.body && c.body.includes(COMMENT_MARKER));

      if (existing) {
        // Update existing comment
        const updateRes = await request(
          `${apiBase}/repos/${owner}/${repo}/issues/comments/${existing.id}`,
          { method: "PATCH", headers },
          JSON.stringify({ body: commentBody })
        );
        if (updateRes.status === 200) {
          info("Updated existing PR comment.");
          return;
        }
      }
    }
  } catch (e) {
    info(`Could not check for existing comments: ${e.message}`);
  }

  // Create new comment
  try {
    const createRes = await request(
      `${apiBase}/repos/${owner}/${repo}/issues/${prNumber}/comments`,
      { method: "POST", headers },
      JSON.stringify({ body: commentBody })
    );

    if (createRes.status === 201) {
      info("Posted PR comment.");
    } else {
      warn(`Failed to post PR comment: ${createRes.status} ${createRes.body.slice(0, 200)}`);
    }
  } catch (e) {
    warn(`Failed to post PR comment: ${e.message}`);
  }
}

// ---------------------------------------------------------------------------
// Threshold check
// ---------------------------------------------------------------------------

function shouldFail(findings) {
  if (FAIL_ON === "none") return false;

  const threshold = SEVERITY_ORDER[FAIL_ON] || SEVERITY_ORDER.critical;

  for (const f of findings) {
    const level = SEVERITY_ORDER[f.risk_level] || 0;
    if (level >= threshold) return true;
  }

  return false;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  info("Ghost Supply Chain Scanner starting...");
  info(`API: ${API_URL}`);
  info(`Fail on: ${FAIL_ON}`);
  info(`Repository: ${GITHUB_REPOSITORY}`);
  info(`Event: ${GITHUB_EVENT_NAME}`);

  // 1. Find lock files
  const lockFiles = findLockFiles(GITHUB_WORKSPACE);

  if (lockFiles.length === 0) {
    info("No lock files found. Nothing to scan.");
    writeSummary("## \u2705 Ghost Supply Chain Scan\n\nNo lock files found in this repository.");
    return;
  }

  info(`Found ${lockFiles.length} lock file(s): ${lockFiles.map((l) => l.relativePath).join(", ")}`);

  // 2. Parse all dependencies
  let allDeps = [];

  for (const lockFile of lockFiles) {
    try {
      const content = fs.readFileSync(lockFile.path, "utf-8");
      const parser = PARSERS[lockFile.filename];

      if (!parser) {
        warn(`No parser for ${lockFile.filename}`);
        continue;
      }

      let deps = parser(content);
      info(`Parsed ${deps.length} dependencies from ${lockFile.relativePath}`);

      // 3. Detect new/changed deps
      deps = detectNewDeps(lockFile, deps);

      // Tag deps with source lockfile
      deps = deps.map((d) => ({ ...d, source: lockFile.relativePath }));

      allDeps.push(...deps);
    } catch (e) {
      warn(`Error processing ${lockFile.relativePath}: ${e.message}`);
    }
  }

  // Deduplicate by name+version
  const seen = new Set();
  allDeps = allDeps.filter((d) => {
    const key = `${d.ecosystem}:${d.name}@${d.version}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  info(`Total unique dependencies: ${allDeps.length}`);

  if (allDeps.length === 0) {
    info("No dependencies found to scan.");
    writeSummary("## \u2705 Ghost Supply Chain Scan\n\nNo dependencies found to scan.");
    return;
  }

  const newDeps = allDeps.filter((d) => d.is_new);
  if (newDeps.length > 0) {
    info(`New/changed dependencies: ${newDeps.length} (${newDeps.map((d) => d.name).join(", ")})`);
  }

  // 4. Call Ghost API
  const scanResult = await callGhostScan(allDeps);
  const findings = scanResult.findings || [];

  info(`Scan complete. ${findings.length} issue(s) found.`);

  // 5. Format output
  const summary = buildSummary(scanResult, allDeps.length);
  writeSummary(summary);

  // 6. Post PR comment only if there are findings
  if (findings.length > 0 && GITHUB_EVENT_NAME === "pull_request") {
    await postOrUpdatePRComment(summary);
  }

  // 7. Exit code
  if (shouldFail(findings)) {
    const worst = findings.reduce((a, b) =>
      (SEVERITY_ORDER[b.risk_level] || 0) > (SEVERITY_ORDER[a.risk_level] || 0) ? b : a
    );
    error(
      `Supply chain risk detected: ${findings.length} issue(s), ` +
      `worst severity: ${worst.risk_level}. Failing because fail-on=${FAIL_ON}.`
    );
    process.exit(1);
  }

  info("Scan passed. No issues above threshold.");
}

main().catch((e) => {
  error(`Ghost scanner failed: ${e.message}`);
  console.error(e.stack);
  process.exit(1);
});
