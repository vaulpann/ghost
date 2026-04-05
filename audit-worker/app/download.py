"""Download and extract package source code."""

import logging
import os
import shutil
import tarfile
import zipfile
from pathlib import Path

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def download_package_source(
    package_name: str,
    version: str,
    registry: str,
    tarball_url: str | None = None,
) -> tuple[str, int, int]:
    """Download and extract full package source.

    Returns (extracted_path, size_bytes, file_count).
    """
    # Clean package name for directory
    safe_name = package_name.replace("/", "_").replace("@", "")
    dest_dir = Path(settings.audit_dir) / safe_name / version
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Check if already downloaded
    if any(dest_dir.iterdir()):
        size, count = _count_source(dest_dir)
        logger.info("Source already cached at %s (%d files)", dest_dir, count)
        return str(dest_dir), size, count

    # Resolve tarball URL if not provided
    if not tarball_url:
        tarball_url = await _resolve_tarball_url(package_name, version, registry)

    if not tarball_url:
        raise ValueError(f"Could not resolve download URL for {package_name}@{version}")

    # Download
    logger.info("Downloading %s@%s from %s", package_name, version, tarball_url[:80])
    tmp_archive = dest_dir / "_archive"
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        resp = await client.get(tarball_url)
        resp.raise_for_status()
        tmp_archive.write_bytes(resp.content)

    # Extract
    try:
        if tarball_url.endswith(".whl") or tarball_url.endswith(".zip"):
            with zipfile.ZipFile(tmp_archive) as zf:
                for name in zf.namelist():
                    if name.startswith("/") or ".." in name:
                        continue
                    zf.extract(name, dest_dir)
        else:
            with tarfile.open(tmp_archive, "r:*") as tar:
                safe_members = [
                    m for m in tar.getmembers()
                    if not m.name.startswith("/") and ".." not in m.name
                ]
                tar.extractall(dest_dir, members=safe_members)
    finally:
        tmp_archive.unlink(missing_ok=True)

    # Unwrap single subdirectory (common in npm/pypi tarballs)
    subdirs = [d for d in dest_dir.iterdir() if d.is_dir()]
    if len(subdirs) == 1 and not any(dest_dir.iterdir().__next__().is_file() for _ in [0] if (dest_dir / subdirs[0].name).is_dir()):
        # Move contents up
        inner = subdirs[0]
        for item in inner.iterdir():
            shutil.move(str(item), str(dest_dir / item.name))
        inner.rmdir()

    size, count = _count_source(dest_dir)
    logger.info("Extracted %s@%s: %d files, %d bytes", package_name, version, count, size)
    return str(dest_dir), size, count


async def _resolve_tarball_url(package_name: str, version: str, registry: str) -> str | None:
    """Resolve the download URL for a package version."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        if registry == "npm":
            resp = await client.get(f"https://registry.npmjs.org/{package_name}/{version}")
            if resp.status_code == 200:
                return resp.json().get("dist", {}).get("tarball")

        elif registry == "pypi":
            resp = await client.get(f"https://pypi.org/pypi/{package_name}/{version}/json")
            if resp.status_code == 200:
                urls = resp.json().get("urls", [])
                sdist = next((u for u in urls if u.get("packagetype") == "sdist"), None)
                wheel = next((u for u in urls if u.get("packagetype") == "bdist_wheel"), None)
                best = sdist or wheel
                return best["url"] if best else None

        elif registry == "github":
            headers = {}
            from app.config import settings as s
            if hasattr(s, "github_token") and s.github_token:
                headers["Authorization"] = f"Bearer {s.github_token}"
            resp = await client.get(
                f"https://api.github.com/repos/{package_name}/tarball/{version}",
                headers=headers,
                follow_redirects=False,
            )
            if resp.status_code in (301, 302):
                return resp.headers.get("location")
            elif resp.status_code == 200:
                return f"https://api.github.com/repos/{package_name}/tarball/{version}"

    return None


def cleanup_source(package_name: str, version: str) -> None:
    """Remove downloaded source after audit completes."""
    safe_name = package_name.replace("/", "_").replace("@", "")
    dest_dir = Path(settings.audit_dir) / safe_name / version
    if dest_dir.exists():
        shutil.rmtree(dest_dir, ignore_errors=True)
        logger.info("Cleaned up %s", dest_dir)


def _count_source(path: Path) -> tuple[int, int]:
    """Count total size and file count."""
    total_size = 0
    file_count = 0
    for root, _, files in os.walk(path):
        for f in files:
            fpath = Path(root) / f
            total_size += fpath.stat().st_size
            file_count += 1
    return total_size, file_count
