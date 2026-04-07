"""Ghost Security Agent — agentic analysis using OpenAI Agents SDK."""

import difflib
import json
import logging
import os
import re
from pathlib import Path

from agents import Agent, Runner, function_tool
from pydantic import BaseModel, Field

from app.services.registry.github import GitHubClient
from app.services.registry.npm import NpmClient
from app.services.registry.pypi import PyPIClient
from app.utils.tarball import cleanup_temp_dir, create_temp_dir

logger = logging.getLogger(__name__)

_temp_dirs: list[Path] = []


def _track_temp(path: Path) -> Path:
    _temp_dirs.append(path)
    return path


def _cleanup_all_temps():
    for p in _temp_dirs:
        cleanup_temp_dir(p)
    _temp_dirs.clear()


# ─── TOOLS ──────────────────────────────────────────────────────────────────

@function_tool
async def lookup_package_info(package_name: str, registry: str) -> str:
    """Look up a package's metadata on npm or PyPI. Returns description, weekly downloads, repository URL, and latest version. IMPORTANT: Only use for packages from package.json (npm) or requirements.txt/pyproject.toml (PyPI). Do NOT use for Go modules, Rust crates, or GitHub releases."""
    # Reject names that look like Go modules, Rust crates, or GitHub repos
    if "/" in package_name and registry == "npm" and not package_name.startswith("@"):
        return json.dumps({"error": f"'{package_name}' looks like a Go module or GitHub path, not an npm package. Use lookup_github_repo instead.", "IMPORTANT": "Do NOT score this as suspicious. It is not an npm package."})
    if "/" in package_name and registry == "pypi":
        return json.dumps({"error": f"'{package_name}' looks like a GitHub path, not a PyPI package. Use lookup_github_repo instead.", "IMPORTANT": "Do NOT score this as suspicious. It is not a PyPI package."})
    if any(package_name.startswith(p) for p in ("golang.org/", "google.golang.org/", "github.com/", "go.", "k8s.io/")):
        return json.dumps({"error": f"'{package_name}' is a Go module, not an npm/PyPI package. Cannot look up. Score 0.0 for this dependency.", "IMPORTANT": "Do NOT penalize — this is a Go module."})

    if registry == "npm":
        client = NpmClient()
        try:
            meta = await client.get_package_metadata(package_name)
            latest = await client.get_latest_version(package_name)
            downloads = meta.weekly_downloads
            dl_status = ""
            if downloads is not None:
                if downloads < 100:
                    dl_status = " *** EXTREMELY LOW — likely typosquat. VERIFY you have the correct package name before scoring. ***"
                elif downloads < 1000:
                    dl_status = " *** VERY LOW — verify this is the correct package name ***"
                elif downloads < 10000:
                    dl_status = " (low)"
            return json.dumps({
                "name": meta.name if hasattr(meta, 'name') and meta.name else package_name,
                "registry": "npm",
                "description": meta.description,
                "weekly_downloads": f"{downloads:,}{dl_status}" if downloads else "unknown",
                "repository": meta.repository_url or "NONE",
                "latest_version": latest.version,
            })
        except Exception as e:
            return json.dumps({"error": f"Package '{package_name}' not found on npm: {e}", "IMPORTANT": "If the package doesn't exist on npm, you may have the wrong name or wrong registry. Do NOT score a non-existent package as suspicious."})
    elif registry == "pypi":
        client = PyPIClient()
        try:
            meta = await client.get_package_metadata(package_name)
            latest = await client.get_latest_version(package_name)
            return json.dumps({
                "name": package_name, "registry": "pypi",
                "description": meta.description,
                "repository": meta.repository_url or "NONE",
                "latest_version": latest.version,
            })
        except Exception as e:
            return json.dumps({"error": f"Package '{package_name}' not found on PyPI: {e}", "IMPORTANT": "If the package doesn't exist on PyPI, you may have the wrong name or wrong registry. Do NOT score a non-existent package as suspicious."})
    return json.dumps({"error": f"Unsupported registry: {registry}. Only 'npm' and 'pypi' are supported."})


@function_tool
async def lookup_github_repo(owner_repo: str) -> str:
    """Look up a GitHub repository's metadata. Use for dependencies that come from GitHub releases (not npm/PyPI). Provide in 'owner/repo' format (e.g., 'containernetworking/plugins'). Returns stars, description, latest release, open issues, and recent commit activity."""
    client = GitHubClient()
    try:
        # Get repo metadata
        meta = await client.get_package_metadata(owner_repo)

        # Get latest release
        latest_release = None
        try:
            latest = await client.get_latest_version(owner_repo)
            latest_release = latest.version
        except Exception:
            pass

        # Get recent commits to check activity
        import httpx
        from app.config import settings
        headers = {"Accept": "application/vnd.github+json"}
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"

        async with httpx.AsyncClient(timeout=15.0, headers=headers) as http:
            # Check recent commits
            commits_resp = await http.get(f"https://api.github.com/repos/{owner_repo}/commits?per_page=5")
            recent_commits = []
            if commits_resp.status_code == 200:
                for c in commits_resp.json()[:5]:
                    recent_commits.append({
                        "sha": c["sha"][:8],
                        "message": c["commit"]["message"].split("\n")[0][:100],
                        "date": c["commit"]["committer"]["date"],
                        "author": c["commit"]["author"]["name"],
                    })

            # Check open issues count
            repo_resp = await http.get(f"https://api.github.com/repos/{owner_repo}")
            open_issues = None
            archived = False
            if repo_resp.status_code == 200:
                repo_data = repo_resp.json()
                open_issues = repo_data.get("open_issues_count")
                archived = repo_data.get("archived", False)

        return json.dumps({
            "repo": owner_repo,
            "description": meta.description,
            "stars": meta.weekly_downloads,  # stars stored here
            "repository_url": meta.repository_url,
            "latest_release": latest_release or "no releases",
            "archived": archived,
            "open_issues": open_issues,
            "recent_commits": recent_commits,
            "assessment": "ARCHIVED — no longer maintained, higher risk" if archived else "active" if recent_commits else "unknown activity",
        })
    except Exception as e:
        return json.dumps({"error": f"Could not look up GitHub repo '{owner_repo}': {e}"})


@function_tool
async def download_and_list_files(package_name: str, version: str, registry: str) -> str:
    """Download a specific version of a package and list all its files. Identifies install scripts, entry points, and binary files."""
    tmp = _track_temp(create_temp_dir(prefix=f"ghost-agent-{package_name}-{version}-"))
    try:
        if registry == "npm":
            client = NpmClient()
            extracted = await client.download_version(package_name, version, str(tmp / "src"))
        elif registry == "pypi":
            client = PyPIClient()
            extracted = await client.download_version(package_name, version, str(tmp / "src"))
        else:
            return json.dumps({"error": f"Unsupported registry: {registry}"})

        root = Path(extracted)
        files, install_scripts, binaries = [], [], []
        total_lines = 0

        for fpath in sorted(root.rglob("*")):
            if not fpath.is_file():
                continue
            rel = str(fpath.relative_to(root))
            files.append({"path": rel, "size": fpath.stat().st_size})
            fname = fpath.name

            if fname in ("setup.py", "postinstall.js", "preinstall.js", "install.js"):
                install_scripts.append(rel)
            if fname == "package.json":
                try:
                    pkg = json.loads(fpath.read_text())
                    for hook in ("preinstall", "postinstall", "install", "prepare"):
                        if hook in pkg.get("scripts", {}):
                            install_scripts.append(f"{rel} → scripts.{hook}: {pkg['scripts'][hook]}")
                except Exception:
                    pass
            if fname == "setup.py":
                try:
                    if "cmdclass" in fpath.read_text():
                        install_scripts.append(f"{rel} → has custom cmdclass")
                except Exception:
                    pass
            if any(fname.endswith(ext) for ext in (".exe", ".dll", ".so", ".dylib", ".wasm", ".node")):
                binaries.append(rel)
            if any(fname.endswith(ext) for ext in (".js", ".ts", ".py", ".mjs", ".cjs")):
                try:
                    total_lines += fpath.read_text(errors="replace").count("\n")
                except Exception:
                    pass

        return json.dumps({
            "package": f"{package_name}@{version}", "extracted_path": str(root),
            "total_files": len(files), "total_source_lines": total_lines,
            "files": files[:100],
            "install_scripts": install_scripts or "none",
            "binary_files": binaries or "none",
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@function_tool
def read_file_content(file_path: str, max_lines: int = 200) -> str:
    """Read the content of a file from a downloaded package. Provide the full path returned by download_and_list_files."""
    try:
        path = Path(file_path)
        if not path.exists():
            return json.dumps({"error": f"File not found: {file_path}"})
        content = path.read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")
        if len(lines) > max_lines:
            return f"[showing first {max_lines} of {len(lines)} lines]\n" + "\n".join(lines[:max_lines])
        return content
    except Exception as e:
        return json.dumps({"error": str(e)})


@function_tool
async def diff_package_versions(package_name: str, old_version: str, new_version: str, registry: str) -> str:
    """Download two versions of a package and produce a unified diff. Use this to see what changed between dependency versions."""
    old_dir = _track_temp(create_temp_dir(prefix=f"ghost-old-{package_name}-"))
    new_dir = _track_temp(create_temp_dir(prefix=f"ghost-new-{package_name}-"))
    try:
        if registry == "npm":
            client = NpmClient()
        elif registry == "pypi":
            client = PyPIClient()
        else:
            return json.dumps({"error": f"Unsupported registry: {registry}"})

        old_path = Path(await client.download_version(package_name, old_version, str(old_dir)))
        new_path = Path(await client.download_version(package_name, new_version, str(new_dir)))

        diff_parts = []
        all_files = set()
        for root, _, files in os.walk(old_path):
            for f in files:
                all_files.add(os.path.relpath(os.path.join(root, f), old_path))
        for root, _, files in os.walk(new_path):
            for f in files:
                all_files.add(os.path.relpath(os.path.join(root, f), new_path))

        for rel in sorted(all_files):
            try:
                old_lines = (old_path / rel).read_text(errors="replace").splitlines() if (old_path / rel).exists() else []
                new_lines = (new_path / rel).read_text(errors="replace").splitlines() if (new_path / rel).exists() else []
            except Exception:
                continue
            if old_lines == new_lines:
                continue
            diff = "\n".join(difflib.unified_diff(old_lines, new_lines, fromfile=f"a/{rel}", tofile=f"b/{rel}", lineterm=""))
            if diff:
                diff_parts.append(diff)

        full_diff = "\n\n".join(diff_parts)
        if len(full_diff) > 50000:
            full_diff = full_diff[:50000] + "\n\n[... truncated at 50KB ...]"

        return json.dumps({
            "package": package_name, "old_version": old_version, "new_version": new_version,
            "diff_files_changed": len(diff_parts),
            "diff": full_diff or "No source code changes detected.",
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@function_tool
def scan_for_suspicious_patterns(file_path: str) -> str:
    """Scan a source file for suspicious security patterns. Provide the full path from a downloaded package."""
    patterns = [
        (r'\b(fetch\(|http\.request|https\.request|XMLHttpRequest|net\.connect|urllib\.request)', "NETWORK", "Outbound network request"),
        (r'\b(child_process|subprocess|os\.system|os\.popen|exec\(|spawn\()', "PROCESS_EXEC", "Process/shell execution"),
        (r'\b(eval\s*\(|new\s+Function\s*\(|compile\s*\()', "DYNAMIC_EXEC", "Dynamic code execution"),
        (r'(Buffer\.from\([^)]+base64|atob\s*\(|b64decode|base64\.b64decode)', "BASE64_DECODE", "Runtime base64 decoding"),
        (r'(process\.env|os\.environ|os\.getenv)\s*[\[.(]', "ENV_READ", "Environment variable access"),
        (r'(/etc/passwd|\.ssh/|\.aws/|\.npmrc|\.pypirc|\.netrc)', "SENSITIVE_PATH", "Sensitive file path access"),
        (r'(preinstall|postinstall)\s*["\']?\s*:', "INSTALL_HOOK", "Install lifecycle hook"),
        (r'(dns\.lookup|dns\.resolve|net\.createConnection|socket\.connect)', "RAW_NETWORK", "Raw network/DNS operation"),
        (r'(wget\s|curl\s|requests\.get|urllib\.urlopen)', "HTTP_FETCH", "HTTP download operation"),
    ]
    try:
        path = Path(file_path)
        if not path.exists():
            return json.dumps({"error": f"File not found: {file_path}"})
        content = path.read_text(encoding="utf-8", errors="replace")
        findings = []
        for pattern, category, description in patterns:
            matches = list(re.finditer(pattern, content))
            if matches:
                for m in matches[:3]:
                    start, end = max(0, m.start() - 100), min(len(content), m.end() + 100)
                    findings.append({
                        "category": category, "description": description,
                        "line": content[:m.start()].count("\n") + 1,
                        "match": m.group(), "context": content[start:end].strip(),
                    })
        return json.dumps({
            "file": file_path, "total_lines": content.count("\n"),
            "findings": findings or "No suspicious patterns found.",
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


# ─── AGENT ──────────────────────────────────────────────────────────────────

class SecurityFinding(BaseModel):
    category: str = Field(description="e.g. dependency_manipulation, install_script, obfuscation, data_exfiltration, backdoor, credential_theft")
    severity: str = Field(description="info, low, medium, high, or critical")
    title: str = Field(description="Short descriptive title")
    description: str = Field(description="Detailed explanation with evidence")
    confidence: float = Field(description="0.0 to 1.0")


class AnalysisResult(BaseModel):
    risk_score: float = Field(ge=0.0, le=10.0, description="0.0 = routine, 10.0 = active attack")
    risk_level: str = Field(description="none, low, medium, high, or critical")
    summary: str = Field(description="2-3 sentence executive summary")
    detailed_report: str = Field(description="Full Markdown analysis report")
    recommended_action: str = Field(description="no_action, monitor, review_manually, block_update, or alert_immediately")
    findings: list[SecurityFinding] = Field(default_factory=list, description="List of security findings")


AGENT_INSTRUCTIONS = """You are Ghost, an expert supply chain security agent. You analyze package updates to detect supply chain attacks.

## YOUR APPROACH:
You have tools to explore packages. Use them systematically:

1. **First, understand the diff** you're given. Identify what changed.
2. **Check for dependency changes**. If ANY dependency was added or had its version changed:
   - **CRITICAL: Identify the CORRECT registry for each dependency.** Read the diff context carefully:
     - If it's in `package.json` → npm
     - If it's in `requirements.txt`, `setup.py`, `pyproject.toml`, `Pipfile` → PyPI
     - If it's in `go.mod` → Go module (NOT npm or PyPI — you cannot look these up with your tools, just note them)
     - If it's in `Cargo.toml` → Rust crate (NOT npm or PyPI)
     - If it's in a YAML config, shell script, or Dockerfile referencing a GitHub URL → it's a GitHub release, NOT an npm/PyPI package
     - If the diff shows a download URL like `https://github.com/org/repo/releases/download/vX.Y.Z` → it's a GitHub release. Use `lookup_github_repo` to check it.
     - **NEVER look up a Go module, Rust crate, or GitHub-released binary on npm or PyPI.** They are completely different things. A Go dependency called "cni" is NOT the npm package "cni".
   - Use `lookup_package_info` ONLY for npm or pypi dependencies
   - Use `lookup_github_repo` for dependencies sourced from GitHub (Go modules, Rust crates, binary releases, etc.)
   - If it looks suspicious (low downloads, no repo, weird name), use `download_and_list_files` to get its source
   - Use `read_file_content` to inspect its install scripts, entry points, and suspicious files
   - Use `scan_for_suspicious_patterns` on any concerning files
   - If it's a version bump of an npm/pypi package, use `diff_package_versions` to see what changed
3. **Follow the chain**. If a dependency added OTHER dependencies, investigate those too.
4. **For the parent package diff**, focus on: install script changes, new network calls, obfuscated code, credential access.

## DEPENDENCY IDENTIFICATION — READ THE CONTEXT:
The same name can mean completely different things on different registries. Examples:
- "cni" in kubernetes YAML → containernetworking/plugins on GitHub. NOT the npm package "cni".
- "protobuf" in go.mod → google.golang.org/protobuf. NOT the npm package "protobuf".
- "requests" in requirements.txt → PyPI requests. This IS the right registry.
- "axios" in package.json → npm axios. This IS the right registry.

Look at the FILE where the dependency change appears and the surrounding context (URLs, paths, comments) to determine the correct registry. If you're not sure, DO NOT look it up — just note the change and score 0.0.

## WHAT IS ROUTINE (score 0.0 — THE VAST MAJORITY OF UPDATES):
- Dockerfile changes, CI/CD configs, Makefile, build scripts — ALWAYS 0.0
- Documentation, tests, README, CHANGELOG — ALWAYS 0.0
- Dependency updates to well-known packages (>10K weekly downloads) — ALWAYS 0.0
- Version metadata changes, copyright updates — ALWAYS 0.0
- Linter configs, type annotations, refactoring — ALWAYS 0.0
- Lock file changes (package-lock.json, go.sum, yarn.lock) — ALWAYS 0.0
- Go module updates to standard libraries (golang.org, google.golang.org) — ALWAYS 0.0
- New features, bug fixes, performance improvements — 0.0
- Adding env var reads for configuration (not exfiltration) — 0.0
- Internal network calls in packages whose PURPOSE is networking (axios, requests, httpx) — 0.0
- Build tooling, test infrastructure, CI actions version bumps — 0.0

## WHAT WARRANTS INVESTIGATION (score 2.0-4.0):
- New dependency you haven't heard of → use lookup_package_info to check downloads
  - If >10K downloads and has a repo → 0.0, it's fine
  - If 1K-10K downloads → 1.0, note it but it's probably fine
  - If <1K downloads → investigate further with download_and_list_files
- Dependency version bump on a less common package → use diff_package_versions to check what changed

## WHAT IS ACTUALLY DANGEROUS (score 5.0+ — REQUIRES CONCRETE PROOF):
You need EVIDENCE, not suspicion. Specific code doing specific bad things.
- New dependency with <1K downloads AND its source contains install scripts that download/execute external code → 7.0+
- New dependency with <100 downloads AND makes network calls to hardcoded external URLs → 8.0+
- Dependency version bump where the NEW version's diff shows added eval/exec with encoded payloads → 7.0+
- Install scripts that use curl/wget to download binaries and execute them → 8.0+
- Code that BOTH collects credentials/tokens AND sends them to external URLs → 9.0+
- Typosquatting (package name differs by 1-2 chars from a popular package) → 7.0+

## SCORING — BE CONSERVATIVE. Cyber teams ignore tools that cry wolf.
- 0.0: Routine update. This should be 80%+ of all scores.
- 0.1-1.0: Clean code changes. Normal development. No action needed.
- 1.1-2.5: Minor note. Maybe a new dep with moderate downloads. Log it, move on.
- 2.6-4.0: Worth a glance. New dependency that's somewhat unknown. Recommend: monitor.
- 4.1-6.0: Real concern with evidence. You found something concrete in dependency source. Recommend: review_manually.
- 6.1-8.0: Likely attack. Multiple confirmed red flags. Obfuscated code + install hooks + low-download dep. Recommend: block_update.
- 8.1-10.0: Confirmed attack. You found data exfiltration, RAT, credential theft, backdoor. Recommend: alert_immediately.

## CRITICAL SCORING RULES:
- If you cannot point to SPECIFIC malicious code → score MUST be below 4.0
- "This pattern COULD be used for X" is NOT evidence. It's speculation. Score 0.0.
- A package having network calls is not suspicious if networking is its purpose
- A package reading env vars for config is not suspicious — only if it SENDS them somewhere
- Go modules you can't look up on npm/pypi → don't penalize, just note it. Score 0.0-1.0.
- Process execution in build tools, test runners, CLIs is NORMAL. Score 0.0.
- NEVER score above 4.0 without having used your tools to verify

## PACKAGE NAME VERIFICATION — CRITICAL:
When you look up a dependency and get extremely low downloads (<1K), STOP and ask yourself:
1. **Did I use the exact package name from the diff?** Re-read the diff line. Copy the EXACT name.
2. **Am I on the right registry?** Check what file the dependency appears in.
3. **Could this be an internal/scoped package?** Names like @org/pkg or build tool plugins often look unfamiliar.
4. **Is this a Rust/Go/other ecosystem package?** Those CANNOT be looked up on npm/PyPI.
If a well-known project (vite, webpack, babel, etc.) adds a dependency, and your lookup shows <1K downloads,
YOU ALMOST CERTAINLY HAVE THE WRONG PACKAGE NAME. Re-check before scoring.
Popular projects do NOT depend on packages with 5 downloads. That's a sign YOU made an error, not them.

## IMPORTANT:
- Use your tools. Don't guess. If a dependency changed, LOOK AT IT.
- But don't inflate scores based on tool limitations (e.g., can't look up Go modules).
- **NEVER look up a non-npm/non-pypi dependency on npm/pypi.** You will find a different, unrelated package and produce a false positive.
- A dependency with <1K downloads that makes network calls is a red flag — investigate.
- Install scripts that curl/wget and execute are CRITICAL — but only if they download from external sources.
- Well-known packages getting version bumps are routine.
- Version bumps in build config YAML files (dependencies.yaml, .github/workflows) that reference GitHub releases are ALWAYS routine. Score 0.0.
- You MUST investigate dependency changes — but ONLY on the correct registry.
- Your credibility depends on precision. A false positive costs trust. Be accurate."""


security_agent = Agent(
    name="Ghost Security Agent",
    instructions=AGENT_INSTRUCTIONS,
    tools=[
        lookup_package_info,
        lookup_github_repo,
        download_and_list_files,
        read_file_content,
        diff_package_versions,
        scan_for_suspicious_patterns,
    ],
    output_type=AnalysisResult,
    model="gpt-4o",
)


async def run_agent_analysis(
    package_name: str,
    registry: str,
    old_version: str,
    new_version: str,
    diff_content: str,
    weekly_downloads: int | None = None,
) -> tuple[AnalysisResult, dict]:
    """Run the Ghost security agent on a package update."""
    if len(diff_content) > 80000:
        diff_content = diff_content[:80000] + "\n\n[... diff truncated — use tools to explore further ...]"

    prompt = f"""Analyze this package update for supply chain security threats.

**Package**: {package_name}
**Registry**: {registry}
**Version change**: {old_version} → {new_version}
**Weekly downloads**: {f"{weekly_downloads:,}" if weekly_downloads else "unknown"}

## Diff:
```
{diff_content}
```

Investigate this update. If there are ANY dependency additions or version changes, you MUST use your tools to look them up and inspect their source code."""

    try:
        result = await Runner.run(security_agent, prompt)
        metadata = {"model": "gpt-4o"}
        return result.final_output, metadata
    finally:
        _cleanup_all_temps()
