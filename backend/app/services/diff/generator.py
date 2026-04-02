import logging
from pathlib import Path

from app.services.registry import GitHubClient, NpmClient, PyPIClient
from app.utils.diff_utils import generate_unified_diff
from app.utils.tarball import cleanup_temp_dir, create_temp_dir

logger = logging.getLogger(__name__)

CLIENTS = {
    "npm": NpmClient,
    "pypi": PyPIClient,
    "github": GitHubClient,
}


async def generate_diff(
    registry: str,
    package_name: str,
    old_version: str,
    new_version: str,
) -> tuple[str, int, int]:
    """Generate a diff between two versions of a package.
    Returns: (diff_content, diff_size_bytes, diff_file_count)
    """
    if registry == "github":
        client = GitHubClient()
        diff = await client.get_compare_diff(package_name, old_version, new_version)
        if diff:
            file_count = diff.count("\ndiff --git")
            return diff, len(diff.encode()), max(file_count, 1)

    client_cls = CLIENTS.get(registry)
    if not client_cls:
        raise ValueError(f"Unknown registry: {registry}")

    client = client_cls()
    old_dir = create_temp_dir(prefix="ghost-old-")
    new_dir = create_temp_dir(prefix="ghost-new-")

    try:
        old_path = await client.download_version(package_name, old_version, str(old_dir))
        new_path = await client.download_version(package_name, new_version, str(new_dir))

        diff = generate_unified_diff(Path(old_path), Path(new_path))
        file_count = diff.count("\n--- a/")
        return diff, len(diff.encode()), max(file_count, 1) if diff else 0

    finally:
        cleanup_temp_dir(old_dir)
        cleanup_temp_dir(new_dir)
