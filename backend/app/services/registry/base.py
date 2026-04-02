from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel


class VersionInfo(BaseModel):
    version: str
    published_at: datetime | None = None
    tarball_url: str | None = None
    sha256_digest: str | None = None


class PackageMetadata(BaseModel):
    name: str
    description: str | None = None
    repository_url: str | None = None
    weekly_downloads: int | None = None
    latest_version: str | None = None


class RegistryClient(ABC):
    @abstractmethod
    async def get_latest_version(self, package_name: str) -> VersionInfo:
        """Fetch the latest version info for a package."""
        ...

    @abstractmethod
    async def get_version_info(self, package_name: str, version: str) -> VersionInfo:
        """Fetch info for a specific version."""
        ...

    @abstractmethod
    async def get_package_metadata(self, package_name: str) -> PackageMetadata:
        """Fetch package metadata (description, downloads, etc.)."""
        ...

    @abstractmethod
    async def download_version(self, package_name: str, version: str, dest_dir: str) -> str:
        """Download and extract a specific version. Returns path to extracted directory."""
        ...
