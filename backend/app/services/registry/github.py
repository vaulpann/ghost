import logging
from datetime import datetime
from pathlib import Path

import httpx

from app.config import settings
from app.services.registry.base import PackageMetadata, RegistryClient, VersionInfo
from app.utils.tarball import cleanup_temp_dir, create_temp_dir, download_file, extract_tarball

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


class GitHubClient(RegistryClient):
    def __init__(self):
        headers = {"Accept": "application/vnd.github+json"}
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"
        self._client = httpx.AsyncClient(timeout=30.0, headers=headers)

    async def get_latest_version(self, package_name: str) -> VersionInfo:
        """package_name should be 'owner/repo' format."""
        url = f"{GITHUB_API}/repos/{package_name}/releases/latest"
        resp = await self._client.get(url)
        resp.raise_for_status()
        data = resp.json()

        published_at = None
        if data.get("published_at"):
            published_at = datetime.fromisoformat(
                data["published_at"].replace("Z", "+00:00")
            )

        return VersionInfo(
            version=data["tag_name"],
            published_at=published_at,
            tarball_url=data.get("tarball_url"),
        )

    async def get_version_info(self, package_name: str, version: str) -> VersionInfo:
        url = f"{GITHUB_API}/repos/{package_name}/releases/tags/{version}"
        resp = await self._client.get(url)
        resp.raise_for_status()
        data = resp.json()

        published_at = None
        if data.get("published_at"):
            published_at = datetime.fromisoformat(
                data["published_at"].replace("Z", "+00:00")
            )

        return VersionInfo(
            version=data["tag_name"],
            published_at=published_at,
            tarball_url=data.get("tarball_url"),
        )

    async def get_package_metadata(self, package_name: str) -> PackageMetadata:
        url = f"{GITHUB_API}/repos/{package_name}"
        resp = await self._client.get(url)
        resp.raise_for_status()
        data = resp.json()

        return PackageMetadata(
            name=package_name,
            description=data.get("description"),
            repository_url=data.get("html_url"),
            weekly_downloads=data.get("stargazers_count"),  # stars as a proxy
            latest_version=None,
        )

    async def download_version(self, package_name: str, version: str, dest_dir: str) -> str:
        url = f"{GITHUB_API}/repos/{package_name}/tarball/{version}"
        tmp = create_temp_dir(prefix=f"ghost-gh-{package_name.replace('/', '-')}-{version}-")
        try:
            tarball_path = tmp / "release.tar.gz"
            headers = dict(self._client.headers)
            await download_file(url, tarball_path, headers=headers)

            extract_dir = Path(dest_dir)
            extract_dir.mkdir(parents=True, exist_ok=True)
            extracted = extract_tarball(tarball_path, extract_dir)
            return str(extracted)
        finally:
            cleanup_temp_dir(tmp)

    async def get_compare_diff(self, package_name: str, old_tag: str, new_tag: str) -> str | None:
        """Use GitHub compare API to get diff directly (preferred over tarball diffing)."""
        url = f"{GITHUB_API}/repos/{package_name}/compare/{old_tag}...{new_tag}"
        resp = await self._client.get(
            url, headers={"Accept": "application/vnd.github.diff"}
        )
        if resp.status_code == 200:
            return resp.text
        return None
