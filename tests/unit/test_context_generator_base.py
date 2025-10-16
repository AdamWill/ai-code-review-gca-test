"""Base test utilities for context generator tests."""

from pathlib import Path
from unittest.mock import patch


class GitTestMixin:
    """Mixin class providing git repository utilities for tests."""

    def _create_git_repo(
        self, project_path: Path, files: list[str] | None = None
    ) -> None:
        """Create a git repository simulation for testing (delegates to fast version)."""
        # For compatibility, delegate to the fast version
        self._create_fast_git_repo(project_path, files)

    def _create_fast_git_repo(
        self, project_path: Path, files: list[str] | None = None
    ) -> None:
        """Create a minimal git repo simulation for fast testing."""
        # Create .git directory to simulate a git repo
        git_dir = project_path / ".git"
        git_dir.mkdir()

        # Create minimal git structure
        (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
        (git_dir / "config").write_text("[core]\n\trepositoryformatversion = 0\n")

        # If files list provided, use those, otherwise scan directory for actual files
        if files is None:
            files = []
            for f in project_path.rglob("*"):
                if f.is_file() and not f.is_relative_to(git_dir):
                    try:
                        rel_path = f.relative_to(project_path)
                        files.append(str(rel_path))
                    except ValueError:
                        # Skip files that can't be made relative
                        continue

        # Create a simple mock that returns the files list
        def mock_get_tracked_files(path):
            # If no files specified, scan the actual directory
            if not files:
                current_files = []
                try:
                    for f in project_path.rglob("*"):
                        if f.is_file() and not f.is_relative_to(git_dir):
                            try:
                                rel_path = f.relative_to(project_path)
                                current_files.append(Path(str(rel_path)))
                            except ValueError:
                                continue
                except Exception:
                    current_files = []
                return current_files
            else:
                # Return the explicitly provided files
                return [Path(f) for f in files]

        # Mock for symlinks - return empty dict by default
        def mock_get_tracked_symlinks(path):
            return {}

        # Apply the mock to multiple modules - make them persistent
        patchers = [
            patch(
                "context_generator.utils.git_utils.get_tracked_files",
                side_effect=mock_get_tracked_files,
            ),
            patch(
                "context_generator.utils.git_utils.get_tracked_symlinks",
                side_effect=mock_get_tracked_symlinks,
            ),
            patch(
                "context_generator.utils.git_utils.is_git_repository",
                return_value=True,
            ),
        ]

        for patcher in patchers:
            patcher.start()

        # Store patchers for cleanup
        if not hasattr(self, "_git_patchers"):
            self._git_patchers = []
        self._git_patchers.extend(patchers)

    def _cleanup_git_mocks(self) -> None:
        """Clean up git mocks."""
        if hasattr(self, "_git_patchers"):
            for patcher in self._git_patchers:
                patcher.stop()
            self._git_patchers.clear()
