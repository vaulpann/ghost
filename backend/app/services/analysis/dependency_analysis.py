"""Dependency analysis — detect new/changed deps in diffs, download and investigate their source."""

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
    def __init__(self, name: str, version: str | None, registry: str, change: str = "added", old_version: str | None = None):
        self.name = name
        self.version = version
        self.registry = registry
        self.change = change  # "added" or "updated"
        self.old_version = old_version
        self.weekly_downloads: int | None = None
        self.description: str | None = None
        self.repository_url: str | None = None
        self.source_analysis: str | None = None
        self.suspicious_files: list[dict] = []
        self.error: str | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name, "version": self.version, "registry": self.registry,
            "weekly_downloads": self.weekly_downloads, "description": self.description,
            "repository_url": self.repository_url, "source_analysis": self.source_analysis,
            "suspicious_files": self.suspicious_files, "error": self.error,
        }

    def to_prompt_text(self) -> str:
        if self.change == "updated":
            lines = [f"### UPDATED dependency: {self.name} {self.old_version} → {self.version} ({self.registry})"]
        else:
            lines = [f"### NEW dependency: {self.name}@{self.version or 'latest'} ({self.registry})"]
        lines.append(f"- Description: {self.description or 'NONE - no description available'}")
        if self.weekly_downloads is not None:
            if self.weekly_downloads < 1000:
                lines.append(f"- **Weekly downloads: {self.weekly_downloads:,} (VERY LOW — potential typosquat or malicious package)**")
            elif self.weekly_downloads < 10000:
                lines.append(f"- Weekly downloads: {self.weekly_downloads:,} (low)")
            else:
                lines.append(f"- Weekly downloads: {self.weekly_downloads:,}")
        else:
            lines.append("- Weekly downloads: **unknown** (could not determine — treat with caution)")
        lines.append(f"- Repository: {self.repository_url or '**NONE — no source repo listed**'}")

        if self.suspicious_files:
            lines.append(f"\n**SUSPICIOUS PATTERNS FOUND IN SOURCE CODE ({len(self.suspicious_files)} matches):**")
            for sf in self.suspicious_files[:10]:
                lines.append(f"- `{sf['file']}` — **{sf['reason']}** (matched {sf.get('match_count', 1)}x)")
                if sf.get("snippet"):
                    lines.append(f"  ```\n  {sf['snippet'][:300]}\n  ```")
        else:
            lines.append("- Source code scan: no suspicious patterns detected")

        if self.source_analysis:
            lines.append(f"- Package structure: {self.source_analysis}")

        if self.error:
            lines.append(f"- **Investigation error: {self.error}** (package may not exist on registry)")

        return "\n".join(lines)


def extract_new_dependencies(diff_content: str, registry: str) -> list[dict]:
    """Parse a diff to find newly added OR version-changed dependencies across all ecosystems.
    Catches both new deps AND version bumps (e.g., crypto-js 4.2.0 → 4.2.1).
    """
    new_deps = []

    if registry == "npm":
        new_deps.extend(_extract_npm_deps(diff_content))
    elif registry == "pypi":
        new_deps.extend(_extract_pypi_deps(diff_content))
    elif registry == "github":
        new_deps.extend(_extract_npm_deps(diff_content))
        new_deps.extend(_extract_pypi_deps(diff_content))
        new_deps.extend(_extract_go_deps(diff_content))
        new_deps.extend(_extract_cargo_deps(diff_content))

    # Deduplicate
    seen = set()
    deduped = []
    for d in new_deps:
        key = f"{d['name']}:{d.get('version', '')}"
        if key not in seen:
            seen.add(key)
            deduped.append(d)

    if deduped:
        logger.info("Extracted %d new dependencies from diff", len(deduped))
    return deduped


def _extract_npm_deps(diff_content: str) -> list[dict]:
    """Extract new AND version-changed deps from package.json changes."""
    added_deps = {}  # name -> version (from + lines)
    removed_deps = {}  # name -> version (from - lines)
    in_package_json = False

    skip_fields = {
        "name", "version", "description", "main", "module", "types", "typings",
        "scripts", "license", "author", "repository", "keywords", "engines",
        "homepage", "bugs", "files", "bin", "man", "directories", "private",
        "publishConfig", "workspaces", "type", "exports", "sideEffects",
    }

    for line in diff_content.split("\n"):
        if line.startswith("+++ b/") or line.startswith("--- a/"):
            in_package_json = "package.json" in line
            continue

        if not in_package_json:
            continue

        if line.startswith("+") and not line.startswith("+++"):
            match = re.match(r'\s*"([^"]+)"\s*:\s*"([^"]*)"', line[1:])
            if match:
                name, version = match.groups()
                if name not in skip_fields and not name.startswith("//"):
                    added_deps[name] = version.lstrip("^~>=<")

        elif line.startswith("-") and not line.startswith("---"):
            match = re.match(r'\s*"([^"]+)"\s*:\s*"([^"]*)"', line[1:])
            if match:
                name, version = match.groups()
                if name not in skip_fields:
                    removed_deps[name] = version.lstrip("^~>=<")

    deps = []
    for name, version in added_deps.items():
        old_version = removed_deps.get(name)
        if old_version is None:
            # Brand new dependency
            deps.append({"name": name, "version": version, "registry": "npm", "change": "added"})
        elif old_version != version:
            # Version changed
            deps.append({"name": name, "version": version, "old_version": old_version, "registry": "npm", "change": "updated"})
        # If same version, it's just a diff artifact — skip

    return deps


def _extract_pypi_deps(diff_content: str) -> list[dict]:
    """Extract new AND version-changed deps from Python dependency files."""
    added_deps = {}
    removed_deps = {}
    dep_files = ("setup.py", "setup.cfg", "pyproject.toml", "requirements.txt", "requirements/", "Pipfile")
    in_dep_file = False

    skip = {"python", "install_requires", "dependencies", "requires", "python_requires",
            "setup_requires", "tests_require", "extras_require", "build-system"}

    dep_pattern = re.compile(r'^["\']?([a-zA-Z][a-zA-Z0-9._-]+)(?:\[.*?\])?(?:\s*([><=~!]+)\s*(.+?))?["\']?,?\s*(?:#.*)?$')

    for line in diff_content.split("\n"):
        if line.startswith("+++ b/") or line.startswith("--- a/"):
            in_dep_file = any(f in line for f in dep_files)
            continue

        if not in_dep_file:
            continue

        for prefix, store in [("+", added_deps), ("-", removed_deps)]:
            if line.startswith(prefix) and not line.startswith(prefix * 3):
                content = line[1:].strip()
                if not content or content.startswith("#") or content.startswith("["):
                    continue
                match = dep_pattern.match(content)
                if match:
                    name = match.group(1).strip()
                    version = match.group(3).strip() if match.group(3) else None
                    if name.lower() not in skip and len(name) > 1:
                        store[name] = version

    deps = []
    for name, version in added_deps.items():
        old_version = removed_deps.get(name)
        if old_version is None:
            deps.append({"name": name, "version": version, "registry": "pypi", "change": "added"})
        elif old_version != version:
            deps.append({"name": name, "version": version, "old_version": old_version, "registry": "pypi", "change": "updated"})

    return deps


def _extract_go_deps(diff_content: str) -> list[dict]:
    """Extract new AND version-changed deps from go.mod."""
    added_deps = {}
    removed_deps = {}
    in_go_mod = False

    for line in diff_content.split("\n"):
        if line.startswith("+++ b/") or line.startswith("--- a/"):
            in_go_mod = "go.mod" in line
            continue

        if not in_go_mod:
            continue

        for prefix, store in [("+", added_deps), ("-", removed_deps)]:
            if line.startswith(prefix) and not line.startswith(prefix * 3):
                match = re.match(r'^\s*(\S+)\s+(v[\d.]+\S*)', line[1:])
                if match and "/" in match.group(1):
                    store[match.group(1)] = match.group(2)

    deps = []
    for name, version in added_deps.items():
        old_version = removed_deps.get(name)
        if old_version is None:
            deps.append({"name": name, "version": version, "registry": "go", "change": "added"})
        elif old_version != version:
            deps.append({"name": name, "version": version, "old_version": old_version, "registry": "go", "change": "updated"})

    return deps


def _extract_cargo_deps(diff_content: str) -> list[dict]:
    """Extract new AND version-changed deps from Cargo.toml."""
    added_deps = {}
    removed_deps = {}
    in_cargo = False
    skip = {"name", "version", "edition", "authors", "description", "license", "repository", "readme", "workspace", "members"}

    for line in diff_content.split("\n"):
        if line.startswith("+++ b/") or line.startswith("--- a/"):
            in_cargo = "Cargo.toml" in line
            continue

        if not in_cargo:
            continue

        for prefix, store in [("+", added_deps), ("-", removed_deps)]:
            if line.startswith(prefix) and not line.startswith(prefix * 3):
                match = re.match(r'^([a-zA-Z][a-zA-Z0-9_-]+)\s*=\s*"([^"]*)"', line[1:].strip())
                if match and match.group(1) not in skip:
                    store[match.group(1)] = match.group(2)

    deps = []
    for name, version in added_deps.items():
        old_version = removed_deps.get(name)
        if old_version is None:
            deps.append({"name": name, "version": version, "registry": "cargo", "change": "added"})
        elif old_version != version:
            deps.append({"name": name, "version": version, "old_version": old_version, "registry": "cargo", "change": "updated"})

    return deps


# Patterns that are actually suspicious (not normal build patterns)
SUSPICIOUS_PATTERNS = [
    (r'\b(https?://[^\s"\'>\)]+)', "outbound_url", "Contains hardcoded URLs"),
    (r'\b(child_process|subprocess|os\.system|os\.popen)\b', "process_exec", "Can execute shell commands"),
    (r'\b(eval\s*\(|new\s+Function\s*\(|exec\s*\(|compile\s*\()', "dynamic_exec", "Dynamic code execution"),
    (r'(Buffer\.from\([^)]+,\s*["\']base64|atob\s*\(|b64decode|base64\.decode)', "base64_decode", "Decodes base64 data at runtime"),
    (r'(process\.env|os\.environ|os\.getenv)\s*[\[.(]', "env_read", "Reads environment variables"),
    (r'(/etc/passwd|\.ssh/|\.aws/|\.npmrc|\.pypirc|\.netrc|\.docker/config)', "sensitive_path", "Accesses sensitive file paths"),
    (r'(preinstall|postinstall)\s*["\']?\s*:', "install_hook", "Has install lifecycle hooks"),
    (r'(dns\.lookup|dns\.resolve|net\.connect|net\.createConnection)', "network_raw", "Raw network/DNS operations"),
    (r'(crypto\.create|hashlib|hmac\.new)', "crypto_ops", "Cryptographic operations (may be legitimate)"),
]


async def investigate_dependencies(
    new_deps: list[dict],
    registry: str,
) -> list[DepInfo]:
    """Download and analyze source code of new AND updated dependencies."""
    results = []

    for dep in new_deps[:10]:
        dep_registry = dep.get("registry", registry)
        info = DepInfo(
            name=dep["name"],
            version=dep.get("version"),
            registry=dep_registry,
            change=dep.get("change", "added"),
            old_version=dep.get("old_version"),
        )
        try:
            if dep_registry == "npm":
                await _investigate_npm_dep(info)
            elif dep_registry == "pypi":
                await _investigate_pypi_dep(info)
            elif dep_registry in ("go", "cargo"):
                # Can't download go/cargo deps directly, just note them
                info.source_analysis = f"{dep_registry} dependency — source not analyzed (registry not supported yet)"
            else:
                info.source_analysis = "Unknown registry — source not analyzed"
        except Exception as e:
            info.error = str(e)
            logger.error("Failed to investigate dependency %s: %s", dep["name"], e)

        results.append(info)

    return results


async def _investigate_npm_dep(info: DepInfo) -> None:
    client = NpmClient()
    try:
        metadata = await client.get_package_metadata(info.name)
        info.description = metadata.description
        info.repository_url = metadata.repository_url
        info.weekly_downloads = metadata.weekly_downloads
    except Exception as e:
        info.error = f"Package not found on npm: {e}"
        return

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


async def _investigate_pypi_dep(info: DepInfo) -> None:
    client = PyPIClient()
    try:
        metadata = await client.get_package_metadata(info.name)
        info.description = metadata.description
        info.repository_url = metadata.repository_url
    except Exception as e:
        info.error = f"Package not found on PyPI: {e}"
        return

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
    findings = []
    for root, _, files in os.walk(path):
        for fname in files:
            fpath = Path(root) / fname
            rel_path = str(fpath.relative_to(path))

            if any(fname.endswith(ext) for ext in (".exe", ".dll", ".so", ".dylib", ".wasm")):
                findings.append({"file": rel_path, "reason": f"Binary file: {fname}", "pattern": "binary_addition", "snippet": None, "match_count": 1})
                continue

            if not any(fname.endswith(ext) for ext in (".js", ".ts", ".py", ".rb", ".json", ".yml", ".yaml", ".cfg", ".toml", ".sh", ".mjs", ".cjs")):
                continue

            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            for pattern, category, reason in SUSPICIOUS_PATTERNS:
                matches = list(re.finditer(pattern, content))
                if matches:
                    m = matches[0]
                    start = max(0, m.start() - 80)
                    end = min(len(content), m.end() + 80)
                    snippet = content[start:end].strip()
                    findings.append({"file": rel_path, "reason": reason, "pattern": category, "snippet": snippet, "match_count": len(matches)})

    return findings


def _summarize_source(path: Path) -> str:
    stats = {"files": 0, "total_lines": 0, "languages": set()}
    install_scripts = []

    ext_to_lang = {".js": "JS", ".ts": "TS", ".py": "Python", ".rb": "Ruby", ".go": "Go", ".rs": "Rust", ".mjs": "JS", ".cjs": "JS"}

    for root, _, files in os.walk(path):
        for fname in files:
            fpath = Path(root) / fname
            stats["files"] += 1
            ext = fpath.suffix
            if ext in ext_to_lang:
                stats["languages"].add(ext_to_lang[ext])
            try:
                stats["total_lines"] += fpath.read_text(encoding="utf-8", errors="replace").count("\n")
            except Exception:
                pass

            if fname == "package.json":
                try:
                    pkg = json.loads(fpath.read_text())
                    for key in ("preinstall", "postinstall", "install", "prepare"):
                        if key in pkg.get("scripts", {}):
                            install_scripts.append(f"**package.json:{key} = {pkg['scripts'][key]}**")
                except Exception:
                    pass
            elif fname in ("setup.py",):
                try:
                    content = fpath.read_text()
                    if "cmdclass" in content:
                        install_scripts.append("**setup.py has custom cmdclass (runs code at install time)**")
                except Exception:
                    pass

    parts = [f"{stats['files']} files, ~{stats['total_lines']} lines"]
    if stats["languages"]:
        parts.append(f"Languages: {', '.join(stats['languages'])}")
    if install_scripts:
        parts.append(f"INSTALL SCRIPTS: {'; '.join(install_scripts)}")
    else:
        parts.append("No install scripts")
    return "; ".join(parts)
