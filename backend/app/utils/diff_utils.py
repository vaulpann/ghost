import difflib
import os
from pathlib import Path


def generate_unified_diff(old_dir: Path, new_dir: Path) -> str:
    """Generate a unified diff between two extracted package directories."""
    diff_parts: list[str] = []
    all_files: set[str] = set()

    for root, _, files in os.walk(old_dir):
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), old_dir)
            all_files.add(rel)

    for root, _, files in os.walk(new_dir):
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), new_dir)
            all_files.add(rel)

    # Prioritize security-sensitive files
    all_files_sorted = sorted(all_files, key=_file_priority)

    for rel_path in all_files_sorted:
        old_file = old_dir / rel_path
        new_file = new_dir / rel_path

        old_lines = _read_file_safe(old_file)
        new_lines = _read_file_safe(new_file)

        if old_lines == new_lines:
            continue

        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{rel_path}",
            tofile=f"b/{rel_path}",
            lineterm="",
        )
        diff_text = "\n".join(diff)
        if diff_text:
            diff_parts.append(diff_text)

    return "\n\n".join(diff_parts)


def _read_file_safe(path: Path) -> list[str]:
    """Read a file, returning empty list if it doesn't exist or is binary."""
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read().splitlines()
    except (OSError, UnicodeDecodeError):
        return ["[binary file]"]


def _file_priority(rel_path: str) -> tuple[int, str]:
    """Priority ordering: lower = checked first in triage.
    Install scripts and configs get highest priority (lowest number).
    """
    name = os.path.basename(rel_path).lower()
    path_lower = rel_path.lower()

    # Install scripts — highest priority
    install_scripts = {
        "setup.py", "setup.cfg", "pyproject.toml", "configure",
        "makefile", "cmakelists.txt", ".npmrc", "install.js",
    }
    if name in install_scripts:
        return (0, rel_path)

    # package.json (contains scripts section)
    if name == "package.json":
        return (0, rel_path)

    # Entry points
    entry_points = {"__init__.py", "index.js", "main.js", "index.ts", "main.ts", "mod.rs"}
    if name in entry_points:
        return (1, rel_path)

    # bin/ directory
    if "bin/" in path_lower:
        return (1, rel_path)

    # Lock files / dependency manifests
    lock_files = {
        "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
        "requirements.txt", "poetry.lock", "cargo.lock", "gemfile.lock",
    }
    if name in lock_files:
        return (2, rel_path)

    # CI/CD configs
    if ".github/" in path_lower or name in {".travis.yml", ".circleci", "jenkinsfile"}:
        return (3, rel_path)

    # Source files
    if any(name.endswith(ext) for ext in (".js", ".ts", ".py", ".rb", ".rs", ".go", ".java")):
        return (4, rel_path)

    # Everything else
    return (5, rel_path)


def truncate_diff_for_triage(diff: str, max_tokens: int = 8000) -> str:
    """Truncate diff to roughly max_tokens for the triage pass.
    Approximation: 1 token ≈ 4 chars.
    """
    max_chars = max_tokens * 4
    if len(diff) <= max_chars:
        return diff
    return diff[:max_chars] + "\n\n[... diff truncated for triage pass ...]"
