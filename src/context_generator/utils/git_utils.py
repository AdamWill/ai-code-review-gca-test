"""Secure Git utilities for context generator."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404 - Controlled usage with security measures
from pathlib import Path


class SecureGitRunner:
    """Secure wrapper for Git operations with input validation."""

    def __init__(self) -> None:
        """Initialize Git runner with security checks."""
        self._git_path = self._find_git_executable()

    def _find_git_executable(self) -> str:
        """Find Git executable path securely."""
        git_path = shutil.which("git")
        if not git_path:
            raise RuntimeError(
                "Git executable not found in PATH. "
                "Please install Git and ensure it's available in your system PATH. "
                "The context generator requires Git to analyze tracked files."
            )
        return git_path

    def _validate_path(self, path: Path) -> None:
        """Validate that the path is safe to use."""
        if not path.exists():
            raise ValueError(f"Path does not exist: {path}")

        # Resolve to absolute path to prevent path traversal
        resolved_path = path.resolve()

        # Basic security check - ensure it's not trying to escape
        if ".." in str(resolved_path):
            raise ValueError(f"Invalid path detected: {path}")

    def is_git_repository(self, project_path: Path) -> bool:
        """Check if directory is a Git repository securely."""
        try:
            self._validate_path(project_path)

            # Use absolute path for Git executable  # nosec B607 - Using validated path
            result = subprocess.run(  # nosec B603 - Controlled input validation
                [self._git_path, "rev-parse", "--git-dir"],
                cwd=project_path,
                capture_output=True,
                check=True,
                timeout=10,  # Add timeout for security
            )
            return result.returncode == 0
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            ValueError,
            Exception,
        ):
            return False

    def get_tracked_files(self, project_path: Path) -> list[Path]:
        """Get Git tracked files securely."""
        self._validate_path(project_path)

        try:
            # Use absolute path for Git executable  # nosec B607 - Using validated path
            result = subprocess.run(  # nosec B603 - Controlled input validation
                [self._git_path, "ls-files"],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=True,
                timeout=30,  # Add timeout for security
            )

            if not result.stdout.strip():
                return []

            files = result.stdout.strip().split("\n")
            # Validate each file path
            validated_files = []
            for file_str in files:
                if file_str and not file_str.startswith(
                    ".."
                ):  # Basic path traversal check
                    validated_files.append(Path(file_str))

            return validated_files

        except subprocess.CalledProcessError as e:
            if e.returncode == 128:  # Git error code for "not a git repository"
                raise RuntimeError(
                    f"'{project_path}' is not a Git repository. "
                    "The context generator requires a Git repository to ensure "
                    "consistent file listing that matches what reviewers see in "
                    "remote repositories (GitHub/GitLab). Please run 'git init' "
                    "and commit your files, or run this tool from within a Git repository."
                ) from e
            else:
                raise RuntimeError(
                    f"Git command failed with exit code {e.returncode}: {e.stderr.decode() if e.stderr else 'Unknown error'}"
                ) from e
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(
                f"Git command timed out after {e.timeout} seconds. "
                "This might indicate a very large repository or system issues."
            ) from e

    def get_tracked_symlinks(self, project_path: Path) -> dict[Path, Path]:
        """Get Git tracked symlinks and their targets.

        Uses git ls-tree to reliably detect symlinks (mode 120000).

        Returns:
            Dictionary mapping symlink Path to target Path.
            Returns empty dict if not a git repository (symlinks are optional).
        """
        self._validate_path(project_path)

        try:
            # Use git ls-tree to get symlinks (mode 120000)
            result = subprocess.run(  # nosec B603 - Controlled input validation
                [self._git_path, "ls-tree", "-r", "HEAD"],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )

            if not result.stdout.strip():
                return {}

            symlinks = {}
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                # Parse git ls-tree output: <mode> <type> <hash>\t<path>
                parts = line.split(maxsplit=3)
                if len(parts) < 4:
                    continue

                mode = parts[0]
                # 120000 is the mode for symlinks in git
                if mode == "120000":
                    # The path is after a tab character
                    if "\t" in line:
                        symlink_path = line.split("\t", 1)[1]
                        if symlink_path and not symlink_path.startswith(".."):
                            # Read the symlink target from filesystem
                            full_path = project_path / symlink_path
                            if full_path.exists() and full_path.is_symlink():
                                try:
                                    target = full_path.readlink()
                                    symlinks[Path(symlink_path)] = target
                                except (OSError, ValueError):
                                    # If we can't read the symlink, skip it
                                    continue

            return symlinks

        except subprocess.CalledProcessError as e:
            # If not a git repository, just return empty dict (symlinks are optional)
            if e.returncode == 128:
                return {}
            else:
                raise RuntimeError(
                    f"Git command failed with exit code {e.returncode}"
                ) from e
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(
                f"Git command timed out after {e.timeout} seconds."
            ) from e


# Global instance for reuse
_git_runner: SecureGitRunner | None = None


def get_git_runner() -> SecureGitRunner:
    """Get shared Git runner instance."""
    global _git_runner
    if _git_runner is None:
        _git_runner = SecureGitRunner()
    return _git_runner


def is_git_repository(project_path: Path) -> bool:
    """Check if directory is a Git repository."""
    return get_git_runner().is_git_repository(project_path)


def get_tracked_files(project_path: Path) -> list[Path]:
    """Get Git tracked files."""
    return get_git_runner().get_tracked_files(project_path)


def get_tracked_symlinks(project_path: Path) -> dict[Path, Path]:
    """Get Git tracked symlinks and their targets."""
    return get_git_runner().get_tracked_symlinks(project_path)
