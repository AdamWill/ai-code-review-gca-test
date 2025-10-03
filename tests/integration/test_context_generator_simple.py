"""Simple integration tests for context generator."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from click.testing import CliRunner

from context_generator.cli import generate_context


class GitTestMixin:
    """Mixin class providing git repository utilities for tests."""

    def _create_git_repo(self, project_path: Path) -> None:
        """Create a git repository and commit all files."""
        # Initialize repo with config in one go
        subprocess.run(
            ["git", "init", "-q"], cwd=project_path, check=True, capture_output=True
        )

        # Set config in batch
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=project_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=project_path,
            check=True,
            capture_output=True,
        )

        # Add and commit in one operation if files exist
        add_result = subprocess.run(
            ["git", "add", "."], cwd=project_path, capture_output=True
        )

        if add_result.returncode == 0:
            # Try to commit, fall back to empty commit if needed
            commit_result = subprocess.run(
                ["git", "commit", "-q", "-m", "Initial commit"],
                cwd=project_path,
                capture_output=True,
            )
            if commit_result.returncode != 0:
                # Create empty commit if no files to commit
                subprocess.run(
                    [
                        "git",
                        "commit",
                        "-q",
                        "--allow-empty",
                        "-m",
                        "Initial empty commit",
                    ],
                    cwd=project_path,
                    check=True,
                    capture_output=True,
                )

    def _create_fast_git_repo(
        self, project_path: Path, files: list[str] | None = None
    ) -> None:
        """Create a minimal git repo simulation for fast testing."""
        from unittest.mock import patch

        # For integration tests, we don't need to create a .git directory
        # The ContextBuilder will auto-detect this and use skip_git_validation=True

        # If files list provided, use those, otherwise scan directory for actual files
        if files is None:
            files = []
            for f in project_path.rglob("*"):
                if f.is_file():
                    try:
                        rel_path = f.relative_to(project_path)
                        files.append(str(rel_path))
                    except ValueError:
                        continue

        # Simple mock that returns the provided files
        def mock_get_tracked_files(path):
            return [Path(f) for f in files] if files else []

        # Apply comprehensive mocks to all possible import paths
        patchers = [
            # Core git utils
            patch(
                "context_generator.utils.git_utils.get_tracked_files",
                side_effect=mock_get_tracked_files,
            ),
            patch(
                "context_generator.utils.git_utils.is_git_repository",
                return_value=True,
            ),
            # Direct imports in extractors
            patch(
                "context_generator.core.facts_extractor.get_tracked_files",
                side_effect=mock_get_tracked_files,
            ),
            patch(
                "context_generator.core.facts_extractor.is_git_repository",
                return_value=True,
            ),
            patch(
                "context_generator.core.code_extractor.get_tracked_files",
                side_effect=mock_get_tracked_files,
            ),
            patch(
                "context_generator.core.code_extractor.is_git_repository",
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


class TestContextGeneratorIntegration(GitTestMixin):
    """Simple integration tests for context generator."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        self._cleanup_git_mocks()

    def test_dry_run_basic_project(self) -> None:
        """Test dry run with a basic project."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create minimal project
            (tmp_path / "README.md").write_text("# Test Project")
            (tmp_path / "pyproject.toml").write_text("""
[project]
name = "test-project"
version = "1.0.0"
dependencies = ["click"]
""")

            # Create fast git repo simulation for integration test
            # We can use the fast version since the CLI will use skip_git_validation internally
            self._create_fast_git_repo(tmp_path, ["README.md", "pyproject.toml"])

            # Test dry run with output in temp directory
            output_file = tmp_path / ".ai_review" / "project.md"
            result = self.runner.invoke(
                generate_context,
                [
                    str(tmp_path),
                    "--output",
                    str(output_file),
                    "--dry-run",
                    "--provider",
                    "ollama",
                ],
            )

            # Should work in dry run mode
            assert result.exit_code == 0
            assert "Dry Run Mode" in result.output
            assert "Context generation completed" in result.output

    def test_help_command(self) -> None:
        """Test help command works."""
        result = self.runner.invoke(generate_context, ["--help"])
        assert result.exit_code == 0
        assert "Generate intelligent project context" in result.output
