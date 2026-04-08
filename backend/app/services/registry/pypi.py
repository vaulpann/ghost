import logging
from datetime import datetime
from pathlib import Path

import httpx

from app.services.registry.base import PackageMetadata, RegistryClient, VersionInfo
from app.utils.tarball import (
    cleanup_temp_dir,
    create_temp_dir,
    download_file,
    extract_tarball,
    extract_wheel,
)

logger = logging.getLogger(__name__)

PYPI_API = "https://pypi.org/pypi"


class PyPIClient(RegistryClient):
    def __init__(self):
        self._client = httpx.AsyncClient(timeout=30.0)

    async def get_latest_version(self, package_name: str) -> VersionInfo:
        url = f"{PYPI_API}/{package_name}/json"
        resp = await self._client.get(url)
        resp.raise_for_status()
        data = resp.json()

        version = data["info"]["version"]
        urls = data.get("urls", [])
        tarball_url, sha256 = self._find_best_download(urls)

        return VersionInfo(
            version=version,
            tarball_url=tarball_url,
            sha256_digest=sha256,
        )

    async def get_version_info(self, package_name: str, version: str) -> VersionInfo:
        url = f"{PYPI_API}/{package_name}/{version}/json"
        resp = await self._client.get(url)
        resp.raise_for_status()
        data = resp.json()

        urls = data.get("urls", [])
        tarball_url, sha256 = self._find_best_download(urls)

        published_at = None
        if urls:
            upload_time = urls[0].get("upload_time_iso_8601")
            if upload_time:
                published_at = datetime.fromisoformat(upload_time.replace("Z", "+00:00"))

        return VersionInfo(
            version=version,
            published_at=published_at,
            tarball_url=tarball_url,
            sha256_digest=sha256,
        )

    async def get_package_metadata(self, package_name: str) -> PackageMetadata:
        url = f"{PYPI_API}/{package_name}/json"
        resp = await self._client.get(url)
        resp.raise_for_status()
        data = resp.json()
        info = data["info"]

        repo_url = (
            info.get("project_urls", {}).get("Repository")
            or info.get("project_urls", {}).get("Source")
            or info.get("project_urls", {}).get("Homepage")
            or info.get("home_page")
        )

        downloads = await self._get_weekly_downloads(package_name)

        return PackageMetadata(
            name=package_name,
            description=info.get("summary"),
            repository_url=repo_url,
            weekly_downloads=downloads,
            latest_version=info.get("version"),
        )

    async def _get_weekly_downloads(self, package_name: str) -> int | None:
        """Fetch weekly download count from pypistats.org API."""
        try:
            url = f"https://pypistats.org/api/packages/{package_name}/recent"
            resp = await self._client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", {}).get("last_week")
        except Exception:
            pass
        return None

    async def download_version(self, package_name: str, version: str, dest_dir: str) -> str:
        info = await self.get_version_info(package_name, version)
        if not info.tarball_url:
            raise ValueError(f"No download URL for {package_name}=={version}")

        tmp = create_temp_dir(prefix=f"ghost-pypi-{package_name}-{version}-")
        try:
            is_wheel = info.tarball_url.endswith(".whl")
            suffix = ".whl" if is_wheel else ".tar.gz"
            archive_path = tmp / f"package{suffix}"
            await download_file(info.tarball_url, archive_path)

            extract_dir = Path(dest_dir)
            extract_dir.mkdir(parents=True, exist_ok=True)

            if is_wheel:
                return str(extract_wheel(archive_path, extract_dir))
            else:
                return str(extract_tarball(archive_path, extract_dir))
        finally:
            cleanup_temp_dir(tmp)

    def _find_best_download(self, urls: list[dict]) -> tuple[str | None, str | None]:
        """Prefer sdist for source diffing, fall back to wheel."""
        sdist = next((u for u in urls if u.get("packagetype") == "sdist"), None)
        wheel = next((u for u in urls if u.get("packagetype") == "bdist_wheel"), None)
        best = sdist or wheel
        if best:
            sha256 = best.get("digests", {}).get("sha256")
            return best["url"], sha256
        return None, None
