"""Ghost Security Agent — agentic analysis using OpenAI Agents SDK."""

import difflib
import json
import logging
import os
import re
from pathlib import Path

from agents import Agent, Runner, function_tool
from pydantic import BaseModel, Field

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
    """Look up a package's metadata on npm or PyPI. Returns description, weekly downloads, repository URL, and latest version."""
    if registry == "npm":
        client = NpmClient()
        try:
            meta = await client.get_package_metadata(package_name)
            latest = await client.get_latest_version(package_name)
            downloads = meta.weekly_downloads
            dl_status = ""
            if downloads is not None:
                if downloads < 100:
                    dl_status = " *** EXTREMELY LOW — likely malicious or typosquat ***"
                elif downloads < 1000:
                    dl_status = " *** VERY LOW — suspicious ***"
                elif downloads < 10000:
                    dl_status = " (low)"
            return json.dumps({
                "name": package_name, "registry": "npm",
                "description": meta.description,
                "weekly_downloads": f"{downloads:,}{dl_status}" if downloads else "unknown",
                "repository": meta.repository_url or "NONE",
                "latest_version": latest.version,
            })
        except Exception as e:
            return json.dumps({"error": f"Package '{package_name}' not found on npm: {e}"})
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
            return json.dumps({"error": f"Package '{package_name}' not found on PyPI: {e}"})
    return json.dumps({"error": f"Unsupported registry: {registry}"})


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
   - Use `lookup_package_info` to check the dependency's download count and metadata
   - If it looks suspicious (low downloads, no repo, weird name), use `download_and_list_files` to get its source
   - Use `read_file_content` to inspect its install scripts, entry points, and suspicious files
   - Use `scan_for_suspicious_patterns` on any concerning files
   - If it's a version bump, use `diff_package_versions` to see what changed IN THAT DEPENDENCY
3. **Follow the chain**. If a dependency added OTHER dependencies, investigate those too.
4. **For the parent package diff**, focus on: install script changes, new network calls, obfuscated code, credential access.

## WHAT IS ROUTINE (score 0.0):
- Dockerfile changes, CI/CD configs, Makefile, build scripts
- Documentation, tests, README, CHANGELOG
- Dependency updates to well-known packages (>100K weekly downloads)
- Version metadata changes, copyright updates
- Linter configs, type annotations, refactoring
- Lock file changes (package-lock.json, go.sum, yarn.lock)
- Go module updates to standard libraries (golang.org, google.golang.org)

## WHAT IS ACTUALLY DANGEROUS (score 5.0+):
- New dependency with <1K downloads → investigate its source code
- Dependency version bump where the new version adds network calls, process execution, or obfuscated code
- Install scripts (postinstall, preinstall) that download and execute external binaries
- Code that collects system info AND sends it to an external URL
- Obfuscated payloads being decoded and executed
- Typosquatting: dependency name similar to a popular package

## SCORING:
- 0.0: Routine. Docs, tests, CI, Dockerfiles, well-known dep updates.
- 0.1-2.0: Clean. Normal code changes, nothing concerning.
- 2.1-4.0: Minor concern. Worth noting but probably fine.
- 4.1-6.0: Suspicious. New unknown dep or concerning code pattern. Manual review needed.
- 6.1-8.0: Likely malicious. Multiple red flags, suspicious dep with bad source code.
- 8.1-10.0: Active attack. Confirmed data exfiltration, RAT, backdoor, credential theft.

## IMPORTANT:
- Use your tools. Don't guess. If a dependency changed, LOOK AT IT.
- A dependency with <1K downloads that makes network calls is a HUGE red flag.
- Install scripts that curl/wget and execute are CRITICAL.
- Well-known packages (react, lodash, boto3, etc.) getting version bumps are routine.
- You MUST investigate dependency changes. This is where real attacks hide."""


security_agent = Agent(
    name="Ghost Security Agent",
    instructions=AGENT_INSTRUCTIONS,
    tools=[
        lookup_package_info,
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
