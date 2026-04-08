"""POST /api/v1/scan — analyze dependencies for supply chain threats."""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import settings
from app.services.registry.npm import NpmClient, NPM_REGISTRY
from app.services.registry.pypi import PyPIClient, PYPI_API

logger = logging.getLogger(__name__)

router = APIRouter(tags=["scan"])

# ---------------------------------------------------------------------------
# Rate limiting — in-memory, keyed by repository, 10 scans/day
# ---------------------------------------------------------------------------

_rate_limits: dict[str, list[float]] = {}  # repo -> list of timestamps
RATE_LIMIT_MAX = 10
RATE_LIMIT_WINDOW = 86_400  # 24 hours


def _check_rate_limit(repository: str) -> None:
    now = time.time()
    timestamps = _rate_limits.get(repository, [])
    # Prune old entries
    timestamps = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
    if len(timestamps) >= RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded for {repository}: {RATE_LIMIT_MAX} scans per day",
        )
    timestamps.append(now)
    _rate_limits[repository] = timestamps


# ---------------------------------------------------------------------------
# Top popular package names — used for typosquat detection
# ---------------------------------------------------------------------------

TOP_NPM_PACKAGES = {
    "lodash", "chalk", "react", "express", "debug", "tslib", "commander",
    "axios", "glob", "semver", "uuid", "mkdirp", "minimist", "moment",
    "webpack", "typescript", "yargs", "underscore", "async", "request",
    "next", "vue", "angular", "jquery", "dotenv", "cors", "body-parser",
    "fs-extra", "rimraf", "inquirer", "rxjs", "eslint", "prettier",
    "babel-core", "mocha", "jest", "eslint-plugin-react", "nodemon",
    "socket.io", "mongoose", "redis", "pg", "mysql2", "sharp", "puppeteer",
    "passport", "jsonwebtoken", "bcrypt", "helmet", "morgan",
}

TOP_PYPI_PACKAGES = {
    "requests", "numpy", "pandas", "boto3", "setuptools", "pip", "wheel",
    "urllib3", "certifi", "idna", "charset-normalizer", "pyyaml", "typing-extensions",
    "six", "python-dateutil", "packaging", "cryptography", "jinja2", "markupsafe",
    "click", "flask", "django", "pillow", "scipy", "matplotlib", "sqlalchemy",
    "pydantic", "fastapi", "uvicorn", "httpx", "aiohttp", "pytest", "coverage",
    "black", "ruff", "mypy", "celery", "redis", "psycopg2", "gunicorn",
    "beautifulsoup4", "lxml", "scrapy", "tqdm", "rich", "pygments", "paramiko",
    "grpcio", "protobuf", "transformers",
}

# No skip threshold — even popular packages get compromised (ua-parser-js, event-stream, coa)


# ---------------------------------------------------------------------------
# Levenshtein distance (simple DP implementation)
# ---------------------------------------------------------------------------

def _levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        return _levenshtein(b, a)
    if len(b) == 0:
        return len(a)

    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            cost = 0 if ca == cb else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[-1]


def _is_typosquat(name: str, registry: str) -> str | None:
    """Return the popular package name this looks like, or None."""
    popular = TOP_NPM_PACKAGES if registry == "npm" else TOP_PYPI_PACKAGES
    lower = name.lower()
    for pkg in popular:
        if lower == pkg:
            return None  # exact match = it IS the popular package
        if _levenshtein(lower, pkg) <= 2:
            return pkg
    return None


def _dedupe_reasons(reasons: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for reason in reasons:
        normalized = reason.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _reason_is_metadata_only(reason: str) -> bool:
    lowered = reason.lower()
    metadata_markers = (
        "weekly downloads",
        "download count",
        "repository url",
        "repository",
        "source repository",
        "maintainer",
        "created ",
        "canonical name",
        "not found on",
        "version '",
        "transparency",
        "trustworthiness",
        "similar to popular package",
        "typosquat",
    )
    return any(marker in lowered for marker in metadata_markers)


def _reason_is_install_script_only(reason: str) -> bool:
    lowered = reason.lower()
    return "install lifecycle scripts" in lowered or "install scripts" in lowered


def _reason_is_weak_signal(reason: str) -> bool:
    lowered = reason.lower()
    weak_markers = (
        "single maintainer",
        "maintainer may indicate potential risk",
        "new dependency with a single maintainer",
    )
    return any(marker in lowered for marker in weak_markers)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class Dependency(BaseModel):
    name: str
    version: str | None = None
    previous_version: str | None = None
    registry: str  # "npm" or "pypi"
    is_new: bool = False


class ScanRequest(BaseModel):
    dependencies: list[Dependency]
    repository: str
    context: str = "pr"  # "pr" or "push"


class Finding(BaseModel):
    package: str
    registry: str
    version: str | None
    previous_version: str | None = None
    risk: str  # "critical", "high", "medium", "low"
    reasons: list[str]
    recommendation: str
    registry_url: str | None = None  # Link to verify the actual package
    weekly_downloads: int | None = None


class ScanSummary(BaseModel):
    total_deps: int
    checked: int
    flagged: int
    clean: int


class ScanResponse(BaseModel):
    findings: list[Finding]
    summary: ScanSummary
    scan_id: str


# ---------------------------------------------------------------------------
# Registry helpers — extend metadata with install scripts / creation time
# ---------------------------------------------------------------------------

async def _npm_extended_metadata(client: httpx.AsyncClient, name: str, version: str | None) -> dict:
    """Fetch full npm package JSON for install script and age checks."""
    meta: dict = {
        "has_install_scripts": False,
        "created_at": None,
        "maintainer_count": 0,
    }
    try:
        url = f"{NPM_REGISTRY}/{name}"
        resp = await client.get(url)
        if resp.status_code != 200:
            return meta
        data = resp.json()

        # Creation time
        time_data = data.get("time", {})
        created_str = time_data.get("created")
        if created_str:
            meta["created_at"] = datetime.fromisoformat(created_str.replace("Z", "+00:00"))

        # Maintainer count
        maintainers = data.get("maintainers", [])
        meta["maintainer_count"] = len(maintainers)

        # Install scripts — check the target version (or latest)
        v = version or data.get("dist-tags", {}).get("latest")
        version_data = data.get("versions", {}).get(v, {})
        scripts = version_data.get("scripts", {})
        install_scripts = {"preinstall", "install", "postinstall", "preuninstall", "postuninstall"}
        meta["has_install_scripts"] = bool(install_scripts & set(scripts.keys()))
    except Exception:
        logger.debug("Failed to fetch extended npm metadata for %s", name, exc_info=True)
    return meta


async def _pypi_extended_metadata(client: httpx.AsyncClient, name: str) -> dict:
    """Fetch PyPI JSON for age and maintainer info."""
    meta: dict = {
        "has_install_scripts": False,  # can't easily detect from PyPI JSON
        "created_at": None,
        "maintainer_count": 0,
    }
    try:
        url = f"{PYPI_API}/{name}/json"
        resp = await client.get(url)
        if resp.status_code != 200:
            return meta
        data = resp.json()

        # Earliest release date as proxy for creation time
        releases = data.get("releases", {})
        earliest = None
        for files in releases.values():
            for f in files:
                upload = f.get("upload_time_iso_8601")
                if upload:
                    dt = datetime.fromisoformat(upload.replace("Z", "+00:00"))
                    if earliest is None or dt < earliest:
                        earliest = dt
        meta["created_at"] = earliest

        info = data.get("info", {})
        # Count author + maintainer as a rough proxy
        count = 0
        if info.get("author"):
            count += 1
        if info.get("maintainer"):
            count += 1
        meta["maintainer_count"] = max(count, 1)
    except Exception:
        logger.debug("Failed to fetch extended pypi metadata for %s", name, exc_info=True)
    return meta


# ---------------------------------------------------------------------------
# Phase 1: Heuristic checks
# ---------------------------------------------------------------------------

async def _verify_package_name(
    dep: Dependency,
    http_client: httpx.AsyncClient,
) -> tuple[bool, str | None, dict]:
    """Verify the package actually exists on the claimed registry.
    Returns (exists, canonical_name). Catches wrong-registry lookups."""
    meta: dict = {}
    try:
        if dep.registry == "npm":
            # npm scoped packages start with @
            if "/" in dep.name and not dep.name.startswith("@"):
                return False, f"'{dep.name}' looks like a path, not an npm package", meta
            resp = await http_client.get(f"{NPM_REGISTRY}/{dep.name}")
            if resp.status_code == 404:
                return False, f"Package '{dep.name}' not found on npm", meta
            if resp.status_code == 200:
                data = resp.json()
                requested_version = dep.version
                available_versions = data.get("versions", {})
                if requested_version and requested_version != "latest":
                    meta["version_exists"] = requested_version in available_versions
                return True, data.get("name", dep.name), meta
        elif dep.registry == "pypi":
            if "/" in dep.name:
                return False, f"'{dep.name}' looks like a path, not a PyPI package", meta
            resp = await http_client.get(f"{PYPI_API}/{dep.name}/json")
            if resp.status_code == 404:
                return False, f"Package '{dep.name}' not found on PyPI", meta
            if resp.status_code == 200:
                data = resp.json()
                requested_version = dep.version
                releases = data.get("releases", {})
                if requested_version and requested_version != "latest":
                    meta["version_exists"] = requested_version in releases
                return True, data.get("info", {}).get("name", dep.name), meta
    except Exception:
        pass
    return True, None, meta  # Can't verify, assume ok


async def _heuristic_check(
    dep: Dependency,
    npm_client: NpmClient,
    pypi_client: PyPIClient,
    http_client: httpx.AsyncClient,
) -> tuple[list[str], dict, bool]:
    """Return (reasons_flagged, metadata_dict, needs_ai).
    Empty reasons = clean. needs_ai = True means send to Phase 2."""
    reasons: list[str] = []
    meta: dict = {}
    needs_ai = False

    # Step 1: Verify the package actually exists with this name on this registry
    exists, canonical_name, verification_meta = await _verify_package_name(dep, http_client)
    if not exists:
        return [canonical_name or f"Package '{dep.name}' not found on {dep.registry}"], meta, False
    meta.update(verification_meta)

    # If canonical name differs from what was sent, note it
    if canonical_name and canonical_name != dep.name:
        meta["canonical_name"] = canonical_name
        reasons.append(f"Registry canonical name is '{canonical_name}', not '{dep.name}'")
        needs_ai = True

    if meta.get("version_exists") is False:
        return [f"Requested version '{dep.version}' was not found on {dep.registry}"], meta, False

    try:
        # Step 2: Fetch metadata
        if dep.registry == "npm":
            lookup_name = canonical_name or dep.name
            pkg_meta = await npm_client.get_package_metadata(lookup_name)
            ext = await _npm_extended_metadata(http_client, lookup_name, dep.version)
        else:
            lookup_name = canonical_name or dep.name
            pkg_meta = await pypi_client.get_package_metadata(lookup_name)
            ext = await _pypi_extended_metadata(http_client, lookup_name)

        downloads = pkg_meta.weekly_downloads
        meta.update({
            "weekly_downloads": downloads,
            "repository_url": pkg_meta.repository_url,
            "description": pkg_meta.description,
            "canonical_name": canonical_name or dep.name,
            **ext,
        })

        # --- Checks for ALL packages (popular or not) ---

        # Install scripts are always worth flagging
        if ext.get("has_install_scripts"):
            reasons.append("Contains install lifecycle scripts (preinstall/postinstall)")
            needs_ai = True

        # New dependency being added deserves AI review regardless of popularity
        if dep.is_new:
            needs_ai = True

        # --- Additional flags for less-known packages ---

        if downloads is not None and downloads < 1000:
            reasons.append(f"Only {downloads:,} weekly downloads")
            needs_ai = True

        # New package (< 30 days old)
        created_at = ext.get("created_at")
        if created_at:
            age_days = (datetime.now(timezone.utc) - created_at).days
            if age_days < 30:
                reasons.append(f"Package created {age_days} day{'s' if age_days != 1 else ''} ago")
                needs_ai = True

        # No repository URL
        if not pkg_meta.repository_url:
            reasons.append("No source repository URL listed")

        # Single maintainer with low downloads
        if ext.get("maintainer_count", 0) <= 1 and downloads is not None and downloads < 5000:
            reasons.append("Single maintainer with low download count")
            needs_ai = True

        # Typosquat check
        similar_to = _is_typosquat(dep.name, dep.registry)
        if similar_to:
            reasons.append(f"Name is suspiciously similar to popular package '{similar_to}'")
            needs_ai = True

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            reasons.append("Package not found on registry")
        else:
            logger.warning("Registry error checking %s: %s", dep.name, exc)
    except Exception:
        logger.warning("Error during heuristic check for %s", dep.name, exc_info=True)

    return reasons, meta, needs_ai


# ---------------------------------------------------------------------------
# Phase 2: AI deep-dive (flagged deps only)
# ---------------------------------------------------------------------------

async def _get_version_diff(dep: Dependency, meta: dict) -> str | None:
    """Download and diff two versions of a package. Returns the diff text or None."""
    if not dep.version:
        return None

    # We need a "previous version" to diff against.
    # For the version field "X.Y.Z", try to find the prior version from registry data.
    # If dep has previous_version set, use that. Otherwise try to infer.
    prev_version = dep.previous_version if hasattr(dep, 'previous_version') and dep.previous_version else None

    if not prev_version:
        # Try to get version list from registry and find the one before this
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if dep.registry == "npm":
                    resp = await client.get(f"{NPM_REGISTRY}/{dep.name}")
                    if resp.status_code == 200:
                        data = resp.json()
                        times = data.get("time", {})
                        sorted_versions = sorted(
                            [(v, t) for v, t in times.items() if v not in ("created", "modified")],
                            key=lambda x: x[1]
                        )
                        version_list = [v for v, _ in sorted_versions]
                        if dep.version in version_list:
                            idx = version_list.index(dep.version)
                            if idx > 0:
                                prev_version = version_list[idx - 1]
                elif dep.registry == "pypi":
                    resp = await client.get(f"{PYPI_API}/{dep.name}/json")
                    if resp.status_code == 200:
                        data = resp.json()
                        releases = data.get("releases", {})
                        # Sort by upload time of first file in each release
                        version_times = []
                        for v, files in releases.items():
                            if files:
                                version_times.append((v, files[0].get("upload_time_iso_8601", "")))
                        version_times.sort(key=lambda x: x[1])
                        version_list = [v for v, _ in version_times]
                        if dep.version in version_list:
                            idx = version_list.index(dep.version)
                            if idx > 0:
                                prev_version = version_list[idx - 1]
        except Exception:
            logger.debug("Could not determine previous version for %s", dep.name)

    if not prev_version:
        return None

    # Use the existing diff tool
    from app.services.analysis.agent import diff_package_versions
    try:
        result_json = await diff_package_versions(dep.name, prev_version, dep.version, dep.registry)
        result = json.loads(result_json)
        if "error" in result:
            return None
        diff_text = result.get("diff", "")
        if not diff_text or diff_text == "No source code changes detected.":
            return None
        # Cap at 15K chars for the AI prompt
        if len(diff_text) > 15000:
            diff_text = diff_text[:15000] + "\n\n[... truncated ...]"
        return diff_text
    except Exception:
        logger.debug("Version diff failed for %s", dep.name, exc_info=True)
        return None


async def _inspect_new_package(dep: Dependency) -> str | None:
    """Download a new dependency and inspect its key files for suspicious code.
    Returns a summary of the package contents or None on failure."""
    from app.services.analysis.agent import download_and_list_files, read_file_content, scan_for_suspicious_patterns
    from app.utils.tarball import create_temp_dir, cleanup_temp_dir

    try:
        result_json = await download_and_list_files(dep.name, dep.version or "latest", dep.registry)
        result = json.loads(result_json)
        if "error" in result:
            return None

        extracted_path = result.get("extracted_path", "")
        files = result.get("files", [])
        install_scripts = result.get("install_scripts", "none")

        # Prioritize files to inspect: install scripts, entry points, and small JS/PY files
        priority_files = []
        for file_info in files:
            rel_path = file_info["path"] if isinstance(file_info, dict) else str(file_info)
            name_lower = rel_path.lower()
            # Install hooks, entry points, setup files
            if any(k in name_lower for k in [
                "preinstall", "postinstall", "install.js", "install.sh",
                "setup.py", "setup.cfg", "pyproject.toml", "__init__.py",
                "index.js", "index.mjs", "main.js", "cli.js",
                "bin/", ".bin/",
            ]):
                priority_files.insert(0, rel_path)  # High priority at front
            # Source files (cap at reasonable number)
            elif name_lower.endswith((".js", ".mjs", ".cjs", ".py", ".sh", ".bat")):
                priority_files.append(rel_path)

        # Read up to 8 key files
        file_contents = []
        scan_results = []
        for fpath in priority_files[:8]:
            full_path = f"{extracted_path}/{fpath}" if not fpath.startswith(extracted_path) else fpath
            content = read_file_content(full_path, max_lines=150)
            if content and "error" not in content:
                file_contents.append(f"--- {fpath} ---\n{content}")
                # Run pattern scan on suspicious-looking files
                if any(k in fpath.lower() for k in ["install", "setup", "index", "main", "cli", "bin"]):
                    scan = scan_for_suspicious_patterns(full_path)
                    if scan and "error" not in scan:
                        scan_data = json.loads(scan) if isinstance(scan, str) else scan
                        findings = scan_data.get("findings", [])
                        if isinstance(findings, list) and findings:
                            scan_results.append(f"Patterns in {fpath}: {json.dumps(scan_data.get('findings', []))}")

        if not file_contents:
            return None

        summary_parts = [
            f"Package: {dep.name}@{dep.version or 'latest'} ({dep.registry})",
            f"Total files: {result.get('total_files', '?')}",
            f"Install scripts: {install_scripts}",
            "",
            "KEY FILE CONTENTS:",
            "\n\n".join(file_contents),
        ]

        if scan_results:
            summary_parts.append("\nPATTERN SCAN RESULTS:")
            summary_parts.extend(scan_results)

        full_summary = "\n".join(summary_parts)
        # Cap at 15K
        if len(full_summary) > 15000:
            full_summary = full_summary[:15000] + "\n\n[... truncated ...]"

        return full_summary

    except Exception:
        logger.debug("Failed to inspect new package %s", dep.name, exc_info=True)
        return None


async def _ai_analyze(
    dep: Dependency,
    reasons: list[str],
    meta: dict,
) -> tuple[str, list[str], str]:
    """Analyze a dependency using OpenAI with actual code inspection.

    For version changes: downloads both versions, diffs the code.
    For new deps: downloads the package, inspects key files.

    Returns (risk_level, updated_reasons, recommendation).
    """
    if not settings.openai_api_key:
        risk = "high" if len(reasons) >= 3 else "medium"
        return risk, reasons, "Review this dependency manually before merging"

    # Get actual code to analyze
    diff_text = None
    source_inspection = None

    if dep.is_new:
        # New dependency — download and inspect the actual source
        source_inspection = await _inspect_new_package(dep)
    # Always try version diff (for version changes, or even for new deps if we can find a prior version)
    if not source_inspection:
        diff_text = await _get_version_diff(dep, meta)

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    downloads = meta.get('weekly_downloads')
    dl_context = ""
    if downloads and downloads > 100000:
        dl_context = (
            f"\nPopularity context: This package has approximately {downloads:,} weekly downloads. "
            "Popularity is relevant context, but it is NOT evidence of compromise by itself and it is NOT evidence of safety by itself."
        )

    code_section = ""
    if source_inspection:
        code_section = f"""

SOURCE CODE INSPECTION (key files from this package):
```
{source_inspection}
```

Analyze the actual source code above. Look for:
- Install scripts (preinstall/postinstall) that download or execute anything
- Obfuscated code (base64, hex encoding, eval, Function constructor)
- Outbound network calls to hardcoded URLs/IPs
- Credential/token/key/cookie access patterns
- File I/O that reads sensitive paths (.ssh, .npmrc, .env, /etc/passwd)
- Code that doesn't match the package's stated purpose
- Minified/packed code that hides functionality"""
    elif diff_text:
        code_section = f"""

VERSION DIFF (what actually changed in the code):
```
{diff_text}
```

Analyze the actual code changes above. Look for:
- New install scripts (preinstall/postinstall) that download or execute anything
- Obfuscated code (base64, hex encoding, eval, Function constructor)
- New outbound network calls to hardcoded URLs/IPs
- Credential/token/key access patterns
- New file I/O that reads sensitive paths (.ssh, .npmrc, .env)
- Code that doesn't match the package's stated purpose"""
    else:
        code_section = "\n(Could not retrieve source code or version diff — evaluate based on metadata only)"

    prompt = f"""You are a supply-chain security analyst. Analyze this dependency for signs of compromise or malicious behavior.

Package: {dep.name}
Registry: {dep.registry}
Version: {dep.version or "latest"}
Previous version: {dep.previous_version or "none"}
Is new dependency: {dep.is_new}
{dl_context}

Heuristic flags:
{chr(10).join(f"- {r}" for r in reasons) if reasons else "- New dependency added (reviewing for safety)"}

Metadata:
- Canonical registry name: {meta.get('canonical_name', dep.name)}
- Weekly downloads: {downloads if downloads else 'unknown'}
- Repository URL: {meta.get('repository_url', 'none')}
- Description: {meta.get('description', 'none')}
- Has install scripts: {meta.get('has_install_scripts', False)}
- Maintainer count: {meta.get('maintainer_count', 'unknown')}
{code_section}

Be precise and conservative:
- HIGH or CRITICAL requires concrete suspicious code behavior or a strongly suspicious diff/source artifact.
- Metadata alone (missing repo URL, low maintainer count, new package, popularity, low downloads) is not enough for HIGH or CRITICAL.
- If the code diff/source looks like normal development or normal package bootstrap code, rate LOW even if some metadata is imperfect.
- For popular legitimate packages, do not over-escalate without concrete code evidence.
- Install scripts alone are common in build tools and binary-distribution packages like esbuild, sharp, and similar packages. Without suspicious domains, obfuscation, credential access, or unexpected behavior, keep them LOW.
- A single maintainer by itself is a weak signal and should not be surfaced as a meaningful concern for established packages unless combined with stronger validated evidence.
- Cite the specific code behavior when you claim meaningful risk.

Respond in this exact JSON format (no markdown, no backticks):
{{"risk": "critical|high|medium|low", "has_concrete_evidence": true, "additional_concerns": ["specific findings from code analysis, or empty if clean"], "recommendation": "one sentence"}}"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500,
        )
        content = response.choices[0].message.content.strip()
        result = json.loads(content)

        risk = result.get("risk", "medium")
        if risk not in ("critical", "high", "medium", "low"):
            risk = "medium"
        has_concrete_evidence = bool(result.get("has_concrete_evidence"))

        if risk in ("critical", "high") and not has_concrete_evidence:
            risk = "medium" if reasons else "low"

        additional = result.get("additional_concerns", [])
        if additional:
            reasons = reasons + [c for c in additional if c]
        reasons = _dedupe_reasons(reasons)

        if risk == "medium" and not has_concrete_evidence and reasons and all(
            _reason_is_metadata_only(reason) or _reason_is_install_script_only(reason)
            for reason in reasons
        ):
            risk = "low"

        recommendation = result.get("recommendation", "Review this dependency before merging")
        return risk, reasons, recommendation

    except Exception:
        logger.warning("AI analysis failed for %s, falling back to heuristic scoring", dep.name, exc_info=True)
        risk = "high" if len(reasons) >= 3 else "medium"
        return risk, reasons, "Review this dependency manually before merging"


# ---------------------------------------------------------------------------
# Main endpoint
# ---------------------------------------------------------------------------

@router.post("/scan", response_model=ScanResponse)
async def scan_dependencies(req: ScanRequest):
    """Analyze a list of dependencies for supply chain threats.

    Phase 1 runs heuristic checks on all deps (fast).
    Phase 2 sends flagged deps to GPT-4o-mini for deeper analysis (slow, but rare).
    """
    _check_rate_limit(req.repository)

    scan_id = str(uuid.uuid4())
    npm_client = NpmClient()
    pypi_client = PyPIClient()

    findings: list[Finding] = []
    checked = 0

    # Phase 1 — heuristic checks (parallel)
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        tasks = [
            _heuristic_check(dep, npm_client, pypi_client, http_client)
            for dep in req.dependencies
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    needs_ai: list[tuple[Dependency, list[str], dict]] = []
    heuristic_only: list[tuple[Dependency, list[str], dict]] = []

    for dep, result in zip(req.dependencies, results):
        checked += 1
        if isinstance(result, Exception):
            logger.warning("Heuristic check failed for %s: %s", dep.name, result)
            continue
        reasons, meta, send_to_ai = result
        if send_to_ai:
            needs_ai.append((dep, reasons, meta))
        elif reasons:
            heuristic_only.append((dep, reasons, meta))

    def _registry_url(dep: Dependency) -> str:
        if dep.registry == "npm":
            return f"https://www.npmjs.com/package/{dep.name}"
        return f"https://pypi.org/project/{dep.name}/"

    # Heuristic-only findings (not serious enough for AI)
    for dep, reasons, meta in heuristic_only:
        reasons = _dedupe_reasons(reasons)
        if not reasons:
            continue
        findings.append(Finding(
            package=dep.name,
            registry=dep.registry,
            version=dep.version,
            previous_version=dep.previous_version,
            risk="low",
            reasons=reasons,
            recommendation="No action required, noted for awareness",
            registry_url=_registry_url(dep),
            weekly_downloads=meta.get("weekly_downloads"),
        ))

    # Phase 2 — AI deep-dive on flagged deps (parallel)
    if needs_ai:
        ai_tasks = [
            _ai_analyze(dep, reasons, meta)
            for dep, reasons, meta in needs_ai
        ]
        ai_results = await asyncio.gather(*ai_tasks, return_exceptions=True)

        for (dep, reasons, meta), ai_result in zip(needs_ai, ai_results):
            if isinstance(ai_result, Exception):
                logger.warning("AI analysis failed for %s: %s", dep.name, ai_result)
                risk, final_reasons, recommendation = (
                    "medium", reasons, "Review this dependency manually"
                )
            else:
                risk, final_reasons, recommendation = ai_result

            final_reasons = _dedupe_reasons(final_reasons)
            if risk == "low" and not final_reasons:
                continue
            if risk == "low" and final_reasons and all(
                _reason_is_weak_signal(reason) for reason in final_reasons
            ):
                continue

            findings.append(Finding(
                package=dep.name,
                registry=dep.registry,
                version=dep.version,
                previous_version=dep.previous_version,
                risk=risk,
                reasons=final_reasons,
                recommendation=recommendation,
                registry_url=_registry_url(dep),
                weekly_downloads=meta.get("weekly_downloads"),
            ))

    # Sort findings by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    findings.sort(key=lambda f: severity_order.get(f.risk, 4))

    return ScanResponse(
        findings=findings,
        summary=ScanSummary(
            total_deps=len(req.dependencies),
            checked=checked,
            flagged=len(findings),
            clean=checked - len(findings),
        ),
        scan_id=scan_id,
    )
