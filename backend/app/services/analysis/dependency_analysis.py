"""Dependency analysis — detect new deps in diffs, download and investigate their source."""

import json
import logging
import os
import re
from pathlib import Path

from app.services.registry.npm import NpmClient
from app.services.registry.pypi import PyPIClient
from app.utils.tarball import cleanup_temp_dir, create_temp_dir

logger = logging.getLogger(__name__)


class DepInfo:
    """Metadata + source analysis for a single dependency."""

    def __init__(self, name: str, version: str | None, registry: str):
        self.name = name
        self.version = version
        self.registry = registry
        self.weekly_downloads: int | None = None
        self.description: str | None = None
        self.repository_url: str | None = None
        self.publish_age_days: int | None = None
        self.maintainer_count: int | None = None
        self.source_analysis: str | None = None  # Summary of what the code does
        self.suspicious_files: list[dict] = []  # Files with concerning patterns
        self.error: str | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "registry": self.registry,
            "weekly_downloads": self.weekly_downloads,
            "description": self.description,
            "repository_url": self.repository_url,
            "source_analysis": self.source_analysis,
            "suspicious_files": self.suspicious_files,
            "error": self.error,
        }

    def to_prompt_text(self) -> str:
        """Format for inclusion in LLM prompts."""
        lines = [f"### Dependency: {self.name}@{self.version or 'latest'} ({self.registry})"]
        lines.append(f"- Description: {self.description or 'none'}")
        lines.append(f"- Weekly downloads: {self.weekly_downloads:,}" if self.weekly_downloads else "- Weekly downloads: unknown")
        lines.append(f"- Repository: {self.repository_url or 'none'}")

        if self.suspicious_files:
            lines.append(f"- **Suspicious files found: {len(self.suspicious_files)}**")
            for sf in self.suspicious_files[:5]:
                lines.append(f"  - `{sf['file']}`: {sf['reason']}")
                if sf.get("snippet"):
                    lines.append(f"    ```\n    {sf['snippet'][:500]}\n    ```")

        if self.source_analysis:
            lines.append(f"- Source analysis:\n{self.source_analysis}")

        if self.error:
            lines.append(f"- Error during investigation: {self.error}")

        return "\n".join(lines)


def extract_new_dependencies(diff_content: str, registry: str) -> list[dict]:
    """Parse a diff to find newly added dependencies.
    Returns list of {"name": ..., "version": ...} dicts.
    """
    new_deps = []

    if registry in ("npm",):
        new_deps.extend(_extract_npm_deps(diff_content))
    elif registry in ("pypi",):
        new_deps.extend(_extract_pypi_deps(diff_content))

    return new_deps


def _extract_npm_deps(diff_content: str) -> list[dict]:
    """Extract new dependencies from package.json changes in a diff."""
    deps = []
    in_package_json = False
    in_added_block = False

    for line in diff_content.split("\n"):
        if line.startswith("--- a/") or line.startswith("+++ b/"):
            in_package_json = "package.json" in line
            continue

        if not in_package_json:
            continue

        # Look for added lines that look like dependency entries
        if line.startswith("+") and not line.startswith("+++"):
            added = line[1:].strip()
            # Match patterns like: "some-package": "^1.2.3"
            match = re.match(r'"([^"]+)"\s*:\s*"([^"]*)"', added)
            if match:
                name, version = match.groups()
                # Filter out non-dependency fields
                if not any(k in name for k in ["name", "version", "description", "main", "scripts", "license", "author", "repository", "keywords", "engines"]):
                    deps.append({"name": name, "version": version.lstrip("^~>=<")})

    return deps


def _extract_pypi_deps(diff_content: str) -> list[dict]:
    """Extract new dependencies from setup.py/pyproject.toml/requirements changes."""
    deps = []
    in_dep_file = False

    dep_files = ("setup.py", "setup.cfg", "pyproject.toml", "requirements")

    for line in diff_content.split("\n"):
        if line.startswith("--- a/") or line.startswith("+++ b/"):
            in_dep_file = any(f in line for f in dep_files)
            continue

        if not in_dep_file:
            continue

        if line.startswith("+") and not line.startswith("+++"):
            added = line[1:].strip()
            # Match: package>=1.0.0, package==1.0, package~=1.0, or just package
            match = re.match(r'^["\']?([a-zA-Z0-9_-]+)(?:\[.*\])?(?:[><=~!]+(.+?))?["\']?,?\s*$', added)
            if match:
                name = match.group(1)
                version = match.group(2)
                # Filter noise
                if len(name) > 1 and name not in ("python", "install_requires", "dependencies", "requires"):
                    deps.append({"name": name, "version": version})

    return deps


# Patterns that are suspicious in dependency source code
SUSPICIOUS_PATTERNS = [
    (r'\b(fetch|http\.request|https\.request|XMLHttpRequest|net\.connect)\b', "network_call", "Makes outbound network requests"),
    (r'\b(child_process|subprocess|os\.system|os\.popen|exec\(|spawn\()\b', "process_exec", "Executes shell commands or spawns processes"),
    (r'\b(eval\(|new\s+Function\(|Function\()\b', "dynamic_exec", "Dynamic code execution (eval/Function)"),
    (r'(Buffer\.from\(.+base64|atob\(|btoa\(|fromCharCode)', "obfuscation", "Base64/encoding operations suggesting obfuscation"),
    (r'(process\.env|os\.environ)', "env_access", "Reads environment variables"),
    (r'(\/etc\/passwd|\.ssh\/|\.aws\/|\.npmrc|\.pypirc)', "sensitive_path", "Accesses sensitive file paths"),
    (r'(postinstall|preinstall|install)\s*["\']?\s*:', "install_script", "Defines install lifecycle scripts"),
    (r'(stratum\+tcp|mining|miner|coinhive)', "crypto_mining", "Cryptocurrency mining indicators"),
    (r'(dns\.lookup|dns\.resolve|socket\.connect)', "dns_network", "DNS/socket operations"),
    (r'(\.exe|\.dll|\.so|\.dylib|\.wasm)\b', "binary_ref", "References to binary/native files"),
]


async def investigate_dependencies(
    new_deps: list[dict],
    registry: str,
) -> list[DepInfo]:
    """Download and analyze source code of new dependencies."""
    results = []

    for dep in new_deps[:10]:  # Cap at 10 to avoid runaway costs
        info = DepInfo(name=dep["name"], version=dep.get("version"), registry=registry)
        try:
            if registry == "npm":
                await _investigate_npm_dep(info)
            elif registry == "pypi":
                await _investigate_pypi_dep(info)
        except Exception as e:
            info.error = str(e)
            logger.error("Failed to investigate dependency %s: %s", dep["name"], e)

        results.append(info)

    return results


async def _investigate_npm_dep(info: DepInfo) -> None:
    """Download and scan an npm package."""
    client = NpmClient()

    # Fetch metadata
    try:
        metadata = await client.get_package_metadata(info.name)
        info.description = metadata.description
        info.repository_url = metadata.repository_url
        info.weekly_downloads = metadata.weekly_downloads
    except Exception:
        pass  # Package might not exist

    # Download and scan source
    tmp = create_temp_dir(prefix=f"ghost-dep-{info.name}-")
    try:
        version = info.version or "latest"
        try:
            extracted = await client.download_version(info.name, version, str(tmp / "src"))
        except Exception:
            # Try latest if specific version fails
            latest = await client.get_latest_version(info.name)
            info.version = latest.version
            extracted = await client.download_version(info.name, latest.version, str(tmp / "src"))

        info.suspicious_files = _scan_directory(Path(extracted))
        info.source_analysis = _summarize_source(Path(extracted))
    finally:
        cleanup_temp_dir(tmp)


async def _investigate_pypi_dep(info: DepInfo) -> None:
    """Download and scan a PyPI package."""
    client = PyPIClient()

    try:
        metadata = await client.get_package_metadata(info.name)
        info.description = metadata.description
        info.repository_url = metadata.repository_url
    except Exception:
        pass

    tmp = create_temp_dir(prefix=f"ghost-dep-{info.name}-")
    try:
        version = info.version or "latest"
        try:
            extracted = await client.download_version(info.name, version, str(tmp / "src"))
        except Exception:
            latest = await client.get_latest_version(info.name)
            info.version = latest.version
            extracted = await client.download_version(info.name, latest.version, str(tmp / "src"))

        info.suspicious_files = _scan_directory(Path(extracted))
        info.source_analysis = _summarize_source(Path(extracted))
    finally:
        cleanup_temp_dir(tmp)


def _scan_directory(path: Path) -> list[dict]:
    """Scan all source files for suspicious patterns."""
    findings = []

    for root, _, files in os.walk(path):
        for fname in files:
            fpath = Path(root) / fname
            rel_path = str(fpath.relative_to(path))

            # Check for suspicious file types
            if any(fname.endswith(ext) for ext in (".exe", ".dll", ".so", ".dylib", ".wasm")):
                findings.append({
                    "file": rel_path,
                    "reason": f"Binary file: {fname}",
                    "pattern": "binary_addition",
                    "snippet": None,
                })
                continue

            # Scan text files
            if not any(fname.endswith(ext) for ext in (".js", ".ts", ".py", ".rb", ".json", ".yml", ".yaml", ".cfg", ".toml", ".sh")):
                continue

            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            for pattern, category, reason in SUSPICIOUS_PATTERNS:
                matches = list(re.finditer(pattern, content))
                if matches:
                    # Get context around first match
                    m = matches[0]
                    start = max(0, m.start() - 100)
                    end = min(len(content), m.end() + 100)
                    snippet = content[start:end].strip()

                    findings.append({
                        "file": rel_path,
                        "reason": reason,
                        "pattern": category,
                        "snippet": snippet,
                        "match_count": len(matches),
                    })

    return findings


def _summarize_source(path: Path) -> str:
    """Generate a brief summary of what's in the package source."""
    stats = {"files": 0, "total_lines": 0, "languages": set()}
    install_scripts = []
    entry_points = []

    ext_to_lang = {
        ".js": "JavaScript", ".ts": "TypeScript", ".py": "Python",
        ".rb": "Ruby", ".go": "Go", ".rs": "Rust",
    }

    for root, _, files in os.walk(path):
        for fname in files:
            fpath = Path(root) / fname
            stats["files"] += 1

            ext = fpath.suffix
            if ext in ext_to_lang:
                stats["languages"].add(ext_to_lang[ext])

            try:
                lines = fpath.read_text(encoding="utf-8", errors="replace").count("\n")
                stats["total_lines"] += lines
            except Exception:
                pass

            # Check for install scripts
            if fname in ("setup.py", "postinstall.js", "preinstall.js", "install.js"):
                install_scripts.append(fname)

            # Check for package.json scripts
            if fname == "package.json":
                try:
                    pkg = json.loads(fpath.read_text())
                    scripts = pkg.get("scripts", {})
                    for key in ("preinstall", "postinstall", "install", "prepare"):
                        if key in scripts:
                            install_scripts.append(f"package.json:{key} = {scripts[key]}")
                except Exception:
                    pass

    parts = [
        f"{stats['files']} files, ~{stats['total_lines']} lines",
        f"Languages: {', '.join(stats['languages']) or 'unknown'}",
    ]
    if install_scripts:
        parts.append(f"**Install scripts: {', '.join(install_scripts)}**")
    else:
        parts.append("No install scripts detected")

    return "; ".join(parts)
