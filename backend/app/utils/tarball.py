import logging
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


async def download_file(url: str, dest: Path, headers: dict | None = None) -> Path:
    """Download a file from a URL to a destination path."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(url, headers=headers or {}, follow_redirects=True)
        response.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(response.content)
    return dest


def extract_tarball(tarball_path: Path, dest_dir: Path) -> Path:
    """Extract a .tar.gz or .tgz file, returning the path to extracted contents."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tarball_path, "r:gz") as tar:
        # Security: prevent path traversal
        for member in tar.getmembers():
            if member.name.startswith("/") or ".." in member.name:
                raise ValueError(f"Unsafe path in tarball: {member.name}")
        tar.extractall(dest_dir, filter="data")

    # npm tarballs extract to a 'package/' subdirectory — unwrap if present
    subdirs = list(dest_dir.iterdir())
    if len(subdirs) == 1 and subdirs[0].is_dir():
        return subdirs[0]
    return dest_dir


def extract_wheel(wheel_path: Path, dest_dir: Path) -> Path:
    """Extract a .whl (zip) file."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(wheel_path, "r") as zf:
        for name in zf.namelist():
            if name.startswith("/") or ".." in name:
                raise ValueError(f"Unsafe path in wheel: {name}")
        zf.extractall(dest_dir)
    return dest_dir


def create_temp_dir(prefix: str = "ghost-") -> Path:
    """Create a temporary directory that the caller is responsible for cleaning up."""
    return Path(tempfile.mkdtemp(prefix=prefix))


def cleanup_temp_dir(path: Path) -> None:
    """Remove a temporary directory."""
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
