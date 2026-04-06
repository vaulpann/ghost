"""Generate real Sentinel scenarios by querying actual registries.

For each historical attack, this script:
1. Queries the real registry (npm/PyPI) for package metadata
2. Fetches real version history, publisher info, dependency trees
3. Builds the 6-dimension game data from REAL evidence
4. Stores in the sentinel_scenarios table
"""

import asyncio
import json
import logging
from datetime import datetime

import httpx

from app.database import async_session, engine
from app.models.sentinel import SentinelScenario
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)


async def fetch_npm_data(package_name: str) -> dict:
    """Fetch real npm registry data for a package."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Full package metadata
        resp = await client.get(f"https://registry.npmjs.org/{package_name}")
        if resp.status_code != 200:
            return {"error": f"npm {resp.status_code}"}
        data = resp.json()

        # Version history
        times = data.get("time", {})
        versions = []
        sorted_versions = sorted(
            [(v, t) for v, t in times.items() if v not in ("created", "modified")],
            key=lambda x: x[1]
        )

        prev_date = None
        for ver, ts in sorted_versions[-20:]:  # Last 20 versions
            date = ts[:10]
            gap = None
            if prev_date:
                try:
                    d1 = datetime.fromisoformat(prev_date)
                    d2 = datetime.fromisoformat(date)
                    gap = (d2 - d1).days
                except Exception:
                    pass
            versions.append({"version": ver, "date": date, "gap_days": gap})
            prev_date = date

        # Maintainers
        maintainers = data.get("maintainers", [])

        # Latest version deps
        latest_ver = data.get("dist-tags", {}).get("latest", "")
        latest_data = data.get("versions", {}).get(latest_ver, {})
        deps = list(latest_data.get("dependencies", {}).keys())
        dev_deps = list(latest_data.get("devDependencies", {}).keys())
        scripts = latest_data.get("scripts", {})
        has_install_scripts = any(k in scripts for k in ("preinstall", "postinstall", "install", "prepare"))

        # Download count
        try:
            dl_resp = await client.get(f"https://api.npmjs.org/downloads/point/last-week/{package_name}")
            weekly_downloads = dl_resp.json().get("downloads", 0) if dl_resp.status_code == 200 else None
        except Exception:
            weekly_downloads = None

        return {
            "name": package_name,
            "description": data.get("description", ""),
            "latest_version": latest_ver,
            "maintainers": maintainers,
            "version_history": versions,
            "dependencies": deps,
            "dev_dependencies": dev_deps,
            "has_install_scripts": has_install_scripts,
            "install_scripts": {k: v for k, v in scripts.items() if k in ("preinstall", "postinstall", "install", "prepare")},
            "weekly_downloads": weekly_downloads,
            "repository": data.get("repository", {}),
            "license": data.get("license", ""),
            "homepage": data.get("homepage", ""),
        }


async def fetch_pypi_data(package_name: str) -> dict:
    """Fetch real PyPI registry data for a package."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"https://pypi.org/pypi/{package_name}/json")
        if resp.status_code != 200:
            return {"error": f"pypi {resp.status_code}"}
        data = resp.json()
        info = data.get("info", {})

        # Version history from releases
        releases = data.get("releases", {})
        versions = []
        prev_date = None
        for ver in sorted(releases.keys(), key=lambda v: releases[v][0]["upload_time_iso_8601"] if releases[v] else "9999")[-20:]:
            if not releases[ver]:
                continue
            date = releases[ver][0].get("upload_time_iso_8601", "")[:10]
            gap = None
            if prev_date and date:
                try:
                    d1 = datetime.fromisoformat(prev_date)
                    d2 = datetime.fromisoformat(date)
                    gap = (d2 - d1).days
                except Exception:
                    pass
            versions.append({"version": ver, "date": date, "gap_days": gap})
            prev_date = date

        return {
            "name": package_name,
            "description": info.get("summary", ""),
            "latest_version": info.get("version", ""),
            "author": info.get("author", ""),
            "author_email": info.get("author_email", ""),
            "version_history": versions,
            "requires_dist": info.get("requires_dist", []) or [],
            "project_urls": info.get("project_urls", {}),
            "license": info.get("license", ""),
            "homepage": info.get("home_page", ""),
        }


async def analyze_version_diff(package_name: str, registry: str, version_from: str, version_to: str) -> dict:
    """Download two versions of a package, diff them, and extract real shape/behavior/flow data."""
    import os
    import re
    import tempfile
    import tarfile
    import zipfile
    import shutil
    import difflib
    from pathlib import Path

    result = {
        "deps_added": [], "deps_removed": [],
        "files_added": [], "files_removed": [], "files_modified": [],
        "behavior_signals": {},
        "network_refs": [], "data_access": [],
        "diff_stats": {"files_changed": 0, "insertions": 0, "deletions": 0},
    }

    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        try:
            old_dir = Path(tempfile.mkdtemp(prefix=f"ghost-old-{package_name}-"))
            new_dir = Path(tempfile.mkdtemp(prefix=f"ghost-new-{package_name}-"))

            if registry == "npm":
                # Get tarball URLs for both versions
                old_url = f"https://registry.npmjs.org/{package_name}/-/{package_name}-{version_from}.tgz"
                new_url = f"https://registry.npmjs.org/{package_name}/-/{package_name}-{version_to}.tgz"

                for url, dest in [(old_url, old_dir), (new_url, new_dir)]:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        logger.warning("  Failed to download %s: %s", url, resp.status_code)
                        continue
                    archive = dest / "pkg.tgz"
                    archive.write_bytes(resp.content)
                    with tarfile.open(archive, "r:gz") as tar:
                        safe = [m for m in tar.getmembers() if not m.name.startswith("/") and ".." not in m.name]
                        tar.extractall(dest, members=safe)
                    archive.unlink()

            elif registry == "pypi":
                for ver, dest in [(version_from, old_dir), (version_to, new_dir)]:
                    resp = await client.get(f"https://pypi.org/pypi/{package_name}/{ver}/json")
                    if resp.status_code != 200:
                        continue
                    urls = resp.json().get("urls", [])
                    sdist = next((u for u in urls if u.get("packagetype") == "sdist"), None)
                    if not sdist:
                        continue
                    dl = await client.get(sdist["url"])
                    archive = dest / "pkg.tar.gz"
                    archive.write_bytes(dl.content)
                    with tarfile.open(archive, "r:gz") as tar:
                        safe = [m for m in tar.getmembers() if not m.name.startswith("/") and ".." not in m.name]
                        tar.extractall(dest, members=safe)
                    archive.unlink()

            # Find the actual source dirs (npm extracts to package/, pypi to name-version/)
            def find_src(d: Path) -> Path:
                subdirs = [x for x in d.iterdir() if x.is_dir()]
                return subdirs[0] if len(subdirs) == 1 else d

            old_src = find_src(old_dir)
            new_src = find_src(new_dir)

            # Collect all files
            old_files = set()
            new_files = set()
            for root, _, files in os.walk(old_src):
                for f in files:
                    old_files.add(os.path.relpath(os.path.join(root, f), old_src))
            for root, _, files in os.walk(new_src):
                for f in files:
                    new_files.add(os.path.relpath(os.path.join(root, f), new_src))

            result["files_added"] = sorted(list(new_files - old_files))[:20]
            result["files_removed"] = sorted(list(old_files - new_files))[:20]

            # Analyze package.json / setup.py diffs for dependency changes
            if registry == "npm":
                old_pkg = _read_json(old_src / "package.json")
                new_pkg = _read_json(new_src / "package.json")
                if old_pkg and new_pkg:
                    old_deps = set(old_pkg.get("dependencies", {}).keys())
                    new_deps = set(new_pkg.get("dependencies", {}).keys())
                    result["deps_added"] = sorted(list(new_deps - old_deps))
                    result["deps_removed"] = sorted(list(old_deps - new_deps))

                    # Check install scripts
                    old_scripts = set(old_pkg.get("scripts", {}).keys())
                    new_scripts = set(new_pkg.get("scripts", {}).keys())
                    install_keys = {"preinstall", "postinstall", "install", "prepare"}
                    new_install = (new_scripts & install_keys) - (old_scripts & install_keys)
                    if new_install:
                        result["behavior_signals"]["new_install_scripts"] = list(new_install)

            # Scan new/modified files for behavioral signals
            patterns = {
                "network": re.compile(r'\b(fetch\(|http\.request|https\.request|XMLHttpRequest|net\.connect|urllib\.request|requests\.get|curl|wget)\b'),
                "process_exec": re.compile(r'\b(child_process|subprocess|os\.system|os\.popen|exec\(|spawn\(|execSync)\b'),
                "eval_exec": re.compile(r'\b(eval\s*\(|new\s+Function\s*\(|exec\s*\()\b'),
                "base64": re.compile(r'(Buffer\.from\([^)]*base64|atob\s*\(|b64decode|base64\.decode)'),
                "env_access": re.compile(r'(process\.env|os\.environ|os\.getenv)\s*[\[.(]'),
                "sensitive_paths": re.compile(r'(/etc/passwd|\.ssh/|\.aws/|\.npmrc|\.pypirc|\.gitconfig|\.bash_history)'),
                "crypto": re.compile(r'(crypto\.create|hashlib|hmac\.new|AES|aes256|encrypt|decrypt)'),
                "geolocation": re.compile(r'(geolocation|geoip|ip.*location|ipinfo|ipgeolocation)'),
                "dns_exfil": re.compile(r'(dns\.lookup|dns\.resolve|\.h4ck\.|dnsquery)'),
            }

            url_pattern = re.compile(r'https?://[^\s"\'>\)]+')
            behavior = {"compute": "green", "file_io": "green", "network": "green", "install_scripts": "green", "crypto": "green"}
            network_refs = set()
            data_access = set()

            # Only scan files that are new or modified
            check_files = result["files_added"] + [f for f in new_files & old_files if f.endswith(('.js', '.ts', '.py', '.sh', '.json', '.yml', '.yaml'))]

            for rel_path in check_files[:50]:  # Cap at 50 files
                fpath = new_src / rel_path
                if not fpath.exists() or not fpath.is_file():
                    continue
                try:
                    content = fpath.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue

                for signal_name, pattern in patterns.items():
                    if pattern.search(content):
                        if signal_name == "network":
                            behavior["network"] = "red"
                        elif signal_name == "process_exec":
                            behavior["file_io"] = "red"
                        elif signal_name == "eval_exec":
                            behavior["compute"] = "red"
                        elif signal_name == "crypto":
                            behavior["crypto"] = "yellow"
                        elif signal_name == "env_access":
                            data_access.add("environment variables")
                        elif signal_name == "sensitive_paths":
                            data_access.add("sensitive file paths")
                        elif signal_name == "base64":
                            behavior["crypto"] = "red"
                        elif signal_name == "geolocation":
                            behavior["network"] = "red"

                # Extract URLs
                for url_match in url_pattern.findall(content):
                    domain = url_match.split("/")[2] if len(url_match.split("/")) > 2 else url_match
                    if domain not in ("registry.npmjs.org", "pypi.org", "github.com", "nodejs.org", "npmjs.com"):
                        network_refs.add(domain)

            if result.get("behavior_signals", {}).get("new_install_scripts"):
                behavior["install_scripts"] = "red"

            result["behavior"] = behavior
            result["network_refs"] = sorted(list(network_refs))[:10]
            result["data_access"] = sorted(list(data_access))

            # Count diff stats
            modified = 0
            insertions = 0
            deletions = 0
            for f in new_files & old_files:
                old_f = old_src / f
                new_f = new_src / f
                try:
                    old_lines = old_f.read_text(errors="replace").splitlines()
                    new_lines = new_f.read_text(errors="replace").splitlines()
                    if old_lines != new_lines:
                        modified += 1
                        diff = list(difflib.unified_diff(old_lines, new_lines))
                        insertions += sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
                        deletions += sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
                except Exception:
                    pass

            result["files_modified"] = [f"({modified} files modified)"]
            result["diff_stats"] = {"files_changed": modified + len(result["files_added"]) + len(result["files_removed"]), "insertions": insertions, "deletions": deletions}

        except Exception as e:
            logger.error("  Diff analysis failed: %s", e)
        finally:
            shutil.rmtree(old_dir, ignore_errors=True)
            shutil.rmtree(new_dir, ignore_errors=True)

    return result


def _read_json(path) -> dict | None:
    try:
        import json as j
        return j.loads(path.read_text())
    except Exception:
        return None


def build_identity(registry_data: dict, overrides: dict = {}) -> dict:
    """Build Identity dimension from real registry data."""
    if "maintainers" in registry_data:
        # npm
        m = registry_data["maintainers"]
        publisher = m[0]["name"] if m else "unknown"
        return {
            "publisher": overrides.get("publisher", publisher),
            "publisher_since": overrides.get("publisher_since", "unknown"),
            "is_usual_publisher": overrides.get("is_usual_publisher", True),
            "account_age_days": overrides.get("account_age_days"),
            "previous_packages": overrides.get("previous_packages"),
            "trust_score": overrides.get("trust_score", 0.8),
            "maintainer_count": len(m),
            "all_maintainers": [x.get("name", "") for x in m],
            "flags": overrides.get("flags", []),
        }
    else:
        # pypi
        return {
            "publisher": overrides.get("publisher", registry_data.get("author", "unknown")),
            "publisher_since": overrides.get("publisher_since", "unknown"),
            "is_usual_publisher": overrides.get("is_usual_publisher", True),
            "account_age_days": overrides.get("account_age_days"),
            "trust_score": overrides.get("trust_score", 0.8),
            "flags": overrides.get("flags", []),
        }


def build_timing(registry_data: dict, overrides: dict = {}) -> dict:
    """Build Timing dimension from real version history."""
    versions = registry_data.get("version_history", [])
    # Detect anomalies
    flags = list(overrides.get("flags", []))
    cadence_normal = True

    for v in versions:
        gap = v.get("gap_days")
        ver = v.get("version", "")
        if gap is not None and gap > 365:
            cadence_normal = False
        if gap == 0 and len(versions) > 1:
            cadence_normal = False
        # Weird version strings
        if any(s in ver.lower() for s in ["liberty", "6.6.6", "beta", "rc"]):
            if "liberty" in ver.lower() or "6.6.6" in ver:
                cadence_normal = False

    if "cadence_normal" in overrides:
        cadence_normal = overrides["cadence_normal"]

    return {
        "release_history": versions[-15:],  # Last 15
        "cadence_normal": cadence_normal,
        "flags": flags,
    }


def build_shape(registry_data: dict, diff_data: dict, overrides: dict = {}) -> dict:
    """Build Shape dimension from REAL diff data."""
    # Merge real diff data with any overrides
    deps_added = diff_data.get("deps_added", []) or overrides.get("deps_added", [])
    deps_removed = diff_data.get("deps_removed", []) or overrides.get("deps_removed", [])
    files_added = diff_data.get("files_added", []) or overrides.get("files_added", [])
    files_removed = diff_data.get("files_removed", []) or overrides.get("files_removed", [])

    flags = list(overrides.get("flags", []))
    # Auto-detect flags from real data
    if deps_added:
        flags.append(f"New dependencies added: {', '.join(deps_added[:5])}")
    if files_added and any(f.endswith(('.sh', '.bat', '.exe', '.dll')) for f in files_added):
        flags.append("New script/binary files added")
    if files_removed and len(files_removed) > 10:
        flags.append(f"{len(files_removed)} files removed")

    stats = diff_data.get("diff_stats", {})

    return {
        "deps_added": deps_added,
        "deps_removed": deps_removed,
        "files_added": files_added[:15],
        "files_removed": files_removed[:15],
        "files_modified": diff_data.get("files_modified", []),
        "total_dependencies": len(registry_data.get("dependencies", registry_data.get("requires_dist", []))),
        "diff_stats": stats,
        "flags": flags,
    }


def build_behavior(registry_data: dict, diff_data: dict, overrides: dict = {}) -> dict:
    """Build Behavior dimension from REAL static analysis of the diff."""
    # Start with real behavior detected from the diff
    categories = diff_data.get("behavior", {
        "compute": "green", "file_io": "green", "network": "green",
        "install_scripts": "green", "crypto": "green",
    })
    # Apply overrides (attack-specific signals the real scan might miss on old versions)
    if overrides.get("categories"):
        categories.update(overrides["categories"])

    flags = list(overrides.get("flags", []))
    # Auto-generate flags from real signals
    if categories.get("network") == "red" and not any("network" in f.lower() for f in flags):
        flags.append("Network calls detected in package code")
    if categories.get("install_scripts") == "red" and not any("install" in f.lower() for f in flags):
        flags.append("Install lifecycle scripts detected")
    if diff_data.get("behavior_signals", {}).get("new_install_scripts"):
        scripts = diff_data["behavior_signals"]["new_install_scripts"]
        flags.append(f"New install scripts: {', '.join(scripts)}")

    return {
        "categories": categories,
        "install_scripts": registry_data.get("install_scripts", {}),
        "flags": flags,
    }


def build_flow(diff_data: dict, overrides: dict = {}) -> dict:
    """Build Flow dimension from REAL network analysis of the diff."""
    # Real network references found in the code
    real_connections = [{"domain": d, "type": "code_reference"} for d in diff_data.get("network_refs", [])]
    # Merge with override connections (known C2/exfil domains from the attack)
    override_connections = overrides.get("outbound_connections", [])

    all_connections = override_connections + [c for c in real_connections if c["domain"] not in [o["domain"] for o in override_connections]]

    data_reads = list(set(diff_data.get("data_access", []) + overrides.get("data_reads", [])))

    flags = list(overrides.get("flags", []))
    if real_connections and not flags:
        flags.append(f"{len(real_connections)} external domain(s) referenced in code")

    return {
        "outbound_connections": all_connections[:10],
        "data_reads": data_reads,
        "flags": flags,
    }


def build_context(registry_data: dict, diff_data: dict, overrides: dict = {}) -> dict:
    """Build Context dimension from REAL package description vs actual changes."""
    description = registry_data.get("description", "")
    update_summary = overrides.get("update_summary", "")

    # Auto-generate update summary from real diff data if not overridden
    if not update_summary:
        stats = diff_data.get("diff_stats", {})
        parts = []
        if diff_data.get("deps_added"):
            parts.append(f"Added deps: {', '.join(diff_data['deps_added'][:3])}")
        if diff_data.get("files_added"):
            parts.append(f"{len(diff_data['files_added'])} new files")
        if stats.get("files_changed"):
            parts.append(f"{stats['files_changed']} files changed")
        update_summary = "; ".join(parts) if parts else "Minor changes"

    mismatch = overrides.get("mismatch_score", 0.0)
    # Auto-calculate mismatch if not overridden
    if mismatch == 0.0:
        behavior = diff_data.get("behavior", {})
        red_count = sum(1 for v in behavior.values() if v == "red")
        if red_count >= 2:
            mismatch = 0.7
        elif red_count == 1:
            mismatch = 0.4

    return {
        "description": description,
        "update_summary": update_summary,
        "mismatch_score": mismatch,
        "weekly_downloads": registry_data.get("weekly_downloads"),
        "license": registry_data.get("license", ""),
        "repository": str(registry_data.get("repository", "")),
        "flags": overrides.get("flags", []),
    }


# === ATTACK DEFINITIONS ===
# Each attack has overrides for the signals that the player needs to spot
# Everything else comes from the REAL registry data

ATTACKS = [
    {
        "package": "colors", "registry": "npm",
        "difficulty": "tutorial", "is_malicious": True,
        "attack_name": "colors.js Maintainer Sabotage",
        "attack_type": "maintainer_sabotage",
        "version_from": "1.4.0", "version_to": "1.4.44-liberty-2",
        "real_cve": None, "real_cvss": None,
        "identity_overrides": {},
        "timing_overrides": {"flags": ["Version string 'liberty-2' is highly unusual", "Large gap before this release"]},
        "shape_overrides": {"files_added": ["american-flag.js"], "flags": ["New file with non-standard name"]},
        "behavior_overrides": {"categories": {"compute": "green", "file_io": "green", "network": "green", "install_scripts": "green", "infinite_loop": "red", "console_output": "red"}, "flags": ["Infinite loop detected", "Endless console output"]},
        "flow_overrides": {},
        "context_overrides": {"update_summary": "Added 'american-flag' module with infinite loop printing 'LIBERTY' text", "mismatch_score": 0.95, "flags": ["Color utility adding infinite loop with no functional purpose"]},
        "postmortem": "Developer Marak Squires deliberately sabotaged colors.js to protest corporations using open source without contributing back. Version 1.4.44-liberty-2 contained an infinite loop. The version string itself was a signal of protest.",
    },
    {
        "package": "ua-parser-js", "registry": "npm",
        "difficulty": "easy", "is_malicious": True,
        "attack_name": "ua-parser-js Account Takeover",
        "attack_type": "account_hijack",
        "version_from": "0.7.28", "version_to": "0.7.29",
        "real_cve": None, "real_cvss": 9.8,
        "identity_overrides": {"flags": ["Publisher's email was flooded with spam around time of publish"]},
        "timing_overrides": {"cadence_normal": False, "flags": ["Three versions across different major lines published simultaneously (0.7.29, 0.8.0, 1.0.0)"]},
        "shape_overrides": {"files_added": ["preinstall.sh", "preinstall.bat"], "flags": ["New preinstall scripts added for Linux and Windows"]},
        "behavior_overrides": {"categories": {"compute": "green", "file_io": "green", "network": "red", "install_scripts": "red", "binary_download": "red"}, "flags": ["Preinstall script downloads platform-specific binaries", "XMRig cryptominer deployed", "Credential-stealing trojan on Windows"]},
        "flow_overrides": {"outbound_connections": [{"domain": "citationsherbe.at", "type": "binary_download"}, {"domain": "pool.supportxmr.com", "type": "mining_pool"}], "data_reads": ["browser cookies", "passwords", "SSH keys"], "flags": ["Downloads from unknown domain", "Connects to Monero mining pool"]},
        "context_overrides": {"update_summary": "Added preinstall scripts that download and execute platform-specific binaries", "mismatch_score": 0.98, "flags": ["User-agent parser downloading binaries and mining cryptocurrency"]},
        "postmortem": "Attackers compromised the npm account of ua-parser-js maintainer (likely via credentials purchased on a Russian forum). Three malicious versions across different major lines were published simultaneously — an unusual timing signal. The preinstall scripts deployed cryptominers and credential stealers. Reverted within ~4 hours.",
    },
    {
        "package": "event-stream", "registry": "npm",
        "difficulty": "medium", "is_malicious": True,
        "attack_name": "event-stream / flatmap-stream",
        "attack_type": "maintainer_takeover",
        "version_from": "3.3.6", "version_to": "4.0.0",
        "real_cve": None, "real_cvss": None,
        "identity_overrides": {"publisher": "right9ctrl", "is_usual_publisher": False, "account_age_days": 60, "previous_packages": 1, "trust_score": 0.2, "flags": ["NEW maintainer — not the original author", "Account only 60 days old", "Original maintainer transferred ownership"]},
        "timing_overrides": {"cadence_normal": False, "flags": ["3+ year gap then new version from new maintainer"]},
        "shape_overrides": {"deps_added": ["flatmap-stream"], "flags": ["New dependency 'flatmap-stream' — only ever had 1 version published", "npm version differs from GitHub source"]},
        "behavior_overrides": {"categories": {"compute": "green", "file_io": "green", "network": "yellow", "install_scripts": "green", "crypto": "red", "obfuscation": "red"}, "flags": ["flatmap-stream contains encrypted payload", "AES-256 decryption with hardcoded key", "Targets BitPay Copay wallet private keys"]},
        "flow_overrides": {"outbound_connections": [{"domain": "copayapi.host", "type": "data_exfiltration"}], "data_reads": ["Bitcoin wallet private keys", "package.json description"], "flags": ["Exfiltrates wallet keys", "Uses package.json description as decryption key"]},
        "context_overrides": {"update_summary": "New maintainer added flatmap-stream dependency with encrypted payload targeting Bitcoin wallets", "mismatch_score": 0.9, "flags": ["Stream utility adding cryptocurrency-targeting encrypted code"]},
        "postmortem": "Attacker 'right9ctrl' social engineered the transfer of event-stream from its original maintainer. The added flatmap-stream dependency contained an encrypted payload that ONLY activated in BitPay's Copay wallet build environment, using the app's package.json description as the AES decryption key. Undetected for 2+ months.",
    },
    {
        "package": "node-ipc", "registry": "npm",
        "difficulty": "easy", "is_malicious": True,
        "attack_name": "node-ipc Protestware",
        "attack_type": "maintainer_sabotage",
        "version_from": "10.1.0", "version_to": "10.1.1",
        "real_cve": "CVE-2022-23812", "real_cvss": 9.8,
        "identity_overrides": {},
        "timing_overrides": {"flags": ["Patch version — should be a minor bugfix"]},
        "shape_overrides": {"deps_added": ["peacenotwar"], "flags": ["New dependency with political name in a utility library"]},
        "behavior_overrides": {"categories": {"compute": "green", "file_io": "red", "network": "yellow", "install_scripts": "green", "geolocation": "red"}, "flags": ["IP geolocation check added", "File overwrite operations targeting Russian/Belarusian IPs", "Replaces file contents with ❤️"]},
        "flow_overrides": {"outbound_connections": [{"domain": "api.ipgeolocation.io", "type": "geolocation_lookup"}], "data_reads": ["IP address", "filesystem paths"], "flags": ["Geolocation API call to determine user's country"]},
        "context_overrides": {"update_summary": "Added IP geolocation check; overwrites files with ❤️ for Russian/Belarusian users", "mismatch_score": 0.95, "flags": ["IPC library checking geolocation and overwriting files"]},
        "postmortem": "Developer added geopolitically-targeted destructive code protesting the Russian invasion of Ukraine. The code overwrote arbitrary files with a heart emoji for users with Russian or Belarusian IPs. node-ipc is a transitive dep of vue-cli, giving it massive blast radius. Undetected for 8 days.",
    },
    # Benign scenarios with real data
    {
        "package": "lodash", "registry": "npm",
        "difficulty": "easy", "is_malicious": False,
        "attack_name": None, "attack_type": None,
        "version_from": "4.17.20", "version_to": "4.17.21",
        "real_cve": None, "real_cvss": None,
        "identity_overrides": {},
        "timing_overrides": {},
        "shape_overrides": {"flags": ["Security patch for prototype pollution in _.set and _.get"]},
        "behavior_overrides": {"categories": {"compute": "green", "file_io": "green", "network": "green", "install_scripts": "green"}},
        "flow_overrides": {},
        "context_overrides": {"update_summary": "Security patch fixing prototype pollution in object path methods", "mismatch_score": 0.0},
        "postmortem": "Legitimate security patch from the original, trusted maintainer. No anomalies in any dimension.",
    },
    {
        "package": "express", "registry": "npm",
        "difficulty": "medium", "is_malicious": False,
        "attack_name": None, "attack_type": None,
        "version_from": "4.18.2", "version_to": "4.19.0",
        "real_cve": None, "real_cvss": None,
        "identity_overrides": {},
        "timing_overrides": {},
        "shape_overrides": {},
        "behavior_overrides": {"categories": {"compute": "green", "file_io": "green", "network": "green", "install_scripts": "green"}},
        "flow_overrides": {},
        "context_overrides": {"update_summary": "Minor version update with dependency bumps and bug fixes", "mismatch_score": 0.0},
        "postmortem": "Routine minor version update from the established Express team. Normal release cadence, no anomalies.",
    },
    {
        "package": "axios", "registry": "npm",
        "difficulty": "easy", "is_malicious": False,
        "attack_name": None, "attack_type": None,
        "version_from": "1.6.0", "version_to": "1.6.1",
        "real_cve": None, "real_cvss": None,
        "identity_overrides": {},
        "timing_overrides": {},
        "shape_overrides": {},
        "behavior_overrides": {"categories": {"compute": "green", "file_io": "green", "network": "green", "install_scripts": "green"}},
        "flow_overrides": {},
        "context_overrides": {"update_summary": "Bug fix for proxy handling regression", "mismatch_score": 0.0},
        "postmortem": "Routine bug fix from the regular maintainer. No anomalies in any dimension.",
    },
    {
        "package": "requests", "registry": "pypi",
        "difficulty": "easy", "is_malicious": False,
        "attack_name": None, "attack_type": None,
        "version_from": "2.31.0", "version_to": "2.32.0",
        "real_cve": None, "real_cvss": None,
        "identity_overrides": {},
        "timing_overrides": {},
        "shape_overrides": {},
        "behavior_overrides": {"categories": {"compute": "green", "file_io": "green", "network": "green", "install_scripts": "green"}},
        "flow_overrides": {},
        "context_overrides": {"update_summary": "Minor version update with security fixes and dependency updates", "mismatch_score": 0.0},
        "postmortem": "Routine update from the established maintainer team. HTTP library making HTTP calls is expected behavior.",
    },
]


async def main():
    logger.info("=== Generating Real Sentinel Scenarios ===")

    async with async_session() as db:
        # Clear existing
        await db.execute(text("DELETE FROM sentinel_verdicts"))
        await db.execute(text("DELETE FROM sentinel_players"))
        await db.execute(text("DELETE FROM sentinel_scenarios"))
        await db.commit()

        for attack in ATTACKS:
            pkg = attack["package"]
            reg = attack["registry"]
            logger.info("Fetching real data for %s (%s)...", pkg, reg)

            # Fetch REAL registry data
            if reg == "npm":
                registry_data = await fetch_npm_data(pkg)
            elif reg == "pypi":
                registry_data = await fetch_pypi_data(pkg)
            else:
                registry_data = {"description": "", "version_history": []}

            if "error" in registry_data:
                logger.warning("  Failed to fetch %s: %s", pkg, registry_data["error"])
                continue

            # Download BOTH versions and diff them for real shape/behavior/flow data
            diff_data = {}
            v_from = attack.get("version_from")
            v_to = attack.get("version_to")
            if v_from and v_to:
                logger.info("  Diffing %s → %s...", v_from, v_to)
                diff_data = await analyze_version_diff(pkg, reg, v_from, v_to)
                stats = diff_data.get("diff_stats", {})
                logger.info("  Diff: %d files changed, +%d -%d",
                            stats.get("files_changed", 0), stats.get("insertions", 0), stats.get("deletions", 0))

            # Build ALL 6 dimensions from REAL data + real diff + attack overrides
            identity = build_identity(registry_data, attack.get("identity_overrides", {}))
            timing = build_timing(registry_data, attack.get("timing_overrides", {}))
            shape = build_shape(registry_data, diff_data, attack.get("shape_overrides", {}))
            behavior = build_behavior(registry_data, diff_data, attack.get("behavior_overrides", {}))
            flow = build_flow(diff_data, attack.get("flow_overrides", {}))
            context = build_context(registry_data, diff_data, attack.get("context_overrides", {}))

            scenario = SentinelScenario(
                source="historical",
                difficulty=attack["difficulty"],
                is_malicious=attack["is_malicious"],
                attack_name=attack.get("attack_name"),
                attack_type=attack.get("attack_type"),
                package_name=pkg,
                registry=reg,
                version_from=attack.get("version_from"),
                version_to=attack.get("version_to"),
                identity_data=identity,
                timing_data=timing,
                shape_data=shape,
                behavior_data=behavior,
                flow_data=flow,
                context_data=context,
                postmortem=attack.get("postmortem"),
                real_cve=attack.get("real_cve"),
                real_cvss=attack.get("real_cvss"),
            )
            db.add(scenario)
            logger.info("  ✓ %s [%s] — %s",
                        pkg, attack["difficulty"],
                        attack.get("attack_name") or "BENIGN")

        await db.commit()

    logger.info("=== Done: %d scenarios with real registry data ===", len(ATTACKS))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
