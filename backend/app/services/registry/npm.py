import logging
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import httpx

from app.services.registry.base import PackageMetadata, RegistryClient, VersionInfo
from app.utils.tarball import cleanup_temp_dir, create_temp_dir, download_file, extract_tarball

logger = logging.getLogger(__name__)

NPM_REGISTRY = "https://registry.npmjs.org"


def _encode_package_name(package_name: str) -> str:
    return quote(package_name, safe="")


class NpmClient(RegistryClient):
    def __init__(self):
        self._client = httpx.AsyncClient(timeout=30.0)

    async def get_latest_version(self, package_name: str) -> VersionInfo:
        """Lightweight check — only fetches dist-tags and the latest version metadata."""
        encoded_name = _encode_package_name(package_name)
        url = f"{NPM_REGISTRY}/{encoded_name}"
        resp = await self._client.get(
            url, headers={"Accept": "application/vnd.npm.install-v1+json"}
        )
        resp.raise_for_status()
        data = resp.json()

        latest = data.get("dist-tags", {}).get("latest", "")
        version_data = data.get("versions", {}).get(latest, {})
        dist = version_data.get("dist", {})

        return VersionInfo(
            version=latest,
            tarball_url=dist.get("tarball"),
            sha256_digest=dist.get("shasum"),
        )

    async def get_version_info(self, package_name: str, version: str) -> VersionInfo:
        encoded_name = _encode_package_name(package_name)
        url = f"{NPM_REGISTRY}/{encoded_name}/{quote(version, safe='')}"
        resp = await self._client.get(url)
        resp.raise_for_status()
        data = resp.json()
        dist = data.get("dist", {})

        published_at = None
        time_data = data.get("time", {})
        if version in time_data:
            published_at = datetime.fromisoformat(time_data[version].replace("Z", "+00:00"))

        return VersionInfo(
            version=version,
            published_at=published_at,
            tarball_url=dist.get("tarball"),
            sha256_digest=dist.get("shasum"),
        )

    async def get_package_metadata(self, package_name: str) -> PackageMetadata:
        encoded_name = _encode_package_name(package_name)
        url = f"{NPM_REGISTRY}/{encoded_name}"
        resp = await self._client.get(url)
        resp.raise_for_status()
        data = resp.json()

        repo_url = None
        repo = data.get("repository")
        if isinstance(repo, dict):
            repo_url = repo.get("url", "")
            if repo_url.startswith("git+"):
                repo_url = repo_url[4:]
            if repo_url.endswith(".git"):
                repo_url = repo_url[:-4]

        # Get download counts from npm API
        downloads = await self._get_weekly_downloads(package_name)

        return PackageMetadata(
            name=package_name,
            description=data.get("description"),
            repository_url=repo_url,
            weekly_downloads=downloads,
            latest_version=data.get("dist-tags", {}).get("latest"),
        )

    async def download_version(self, package_name: str, version: str, dest_dir: str) -> str:
        info = await self.get_version_info(package_name, version)
        if not info.tarball_url:
            raise ValueError(f"No tarball URL for {package_name}@{version}")

        safe_name = package_name.replace("/", "_")
        tmp = create_temp_dir(prefix=f"ghost-npm-{safe_name}-{version}-")
        try:
            tarball_path = tmp / "package.tgz"
            await download_file(info.tarball_url, tarball_path)
            extract_dir = Path(dest_dir)
            extract_dir.mkdir(parents=True, exist_ok=True)
            extracted = extract_tarball(tarball_path, extract_dir)
            return str(extracted)
        finally:
            cleanup_temp_dir(tmp)

    async def _get_weekly_downloads(self, package_name: str) -> int | None:
        try:
            encoded_name = _encode_package_name(package_name)
            url = f"https://api.npmjs.org/downloads/point/last-week/{encoded_name}"
            resp = await self._client.get(url)
            if resp.status_code == 200:
                return resp.json().get("downloads")
        except Exception:
            pass
        return None
