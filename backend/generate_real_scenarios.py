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


def build_shape(registry_data: dict, overrides: dict = {}) -> dict:
    """Build Shape dimension from dependency data."""
    return {
        "deps_added": overrides.get("deps_added", []),
        "deps_removed": overrides.get("deps_removed", []),
        "files_added": overrides.get("files_added", []),
        "files_removed": overrides.get("files_removed", []),
        "total_dependencies": len(registry_data.get("dependencies", registry_data.get("requires_dist", []))),
        "flags": overrides.get("flags", []),
    }


def build_behavior(registry_data: dict, overrides: dict = {}) -> dict:
    """Build Behavior dimension."""
    categories = overrides.get("categories", {
        "compute": "green",
        "file_io": "green",
        "network": "green",
        "install_scripts": "red" if registry_data.get("has_install_scripts") else "green",
        "crypto": "green",
    })
    return {
        "categories": categories,
        "install_scripts": registry_data.get("install_scripts", {}),
        "flags": overrides.get("flags", []),
    }


def build_flow(overrides: dict = {}) -> dict:
    """Build Flow dimension."""
    return {
        "outbound_connections": overrides.get("outbound_connections", []),
        "data_reads": overrides.get("data_reads", []),
        "flags": overrides.get("flags", []),
    }


def build_context(registry_data: dict, overrides: dict = {}) -> dict:
    """Build Context dimension."""
    return {
        "description": registry_data.get("description", ""),
        "update_summary": overrides.get("update_summary", ""),
        "mismatch_score": overrides.get("mismatch_score", 0.0),
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

            # Build 6 dimensions from REAL data + attack-specific overrides
            identity = build_identity(registry_data, attack.get("identity_overrides", {}))
            timing = build_timing(registry_data, attack.get("timing_overrides", {}))
            shape = build_shape(registry_data, attack.get("shape_overrides", {}))
            behavior = build_behavior(registry_data, attack.get("behavior_overrides", {}))
            flow = build_flow(attack.get("flow_overrides", {}))
            context = build_context(registry_data, attack.get("context_overrides", {}))

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
