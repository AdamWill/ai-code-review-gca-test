"""Advanced tests for LocalGitClient to improve coverage."""

from __future__ import annotations

import shutil
from unittest.mock import Mock, patch

import pytest

from ai_code_review.models.config import Config, PlatformProvider
from ai_code_review.utils.platform_exceptions import GitLocalError
from tests.conftest import create_gitpython_mock

# Check if Git is available for integration tests
GIT_AVAILABLE = shutil.which("git") is not None

# Mock GitPython completely to avoid git binary requirement in CI
with patch.dict("sys.modules", {"git": create_gitpython_mock()}):
    from ai_code_review.core.local_git_client import LocalGitClient


@pytest.fixture
def local_config() -> Config:
    """Create test config for local mode."""
    # Mock Config creation completely to avoid pydantic-settings environment interference
    config = Mock(spec=Config)
    config.platform_provider = PlatformProvider.LOCAL
    config.dry_run = False
    config.ai_api_key = "test-key"
    config.max_files = 10
    config.max_chars = 1000
    config.target_branch = "main"
    config.exclude_patterns = [
        "*.lock",
        "package-lock.json",
        "yarn.lock",
        "node_modules/**",
    ]
    config.language_hint = None
    config.enable_project_context = True
    config.project_context_file = ".ai_review/project.md"
    return config


@pytest.fixture
def local_client(local_config: Config) -> LocalGitClient:
    """Create LocalGitClient instance."""
    return LocalGitClient(local_config)


class TestLocalGitClientAdvanced:
    """Advanced test cases for LocalGitClient to improve coverage."""

    def test_repo_property_cached(self, local_client: LocalGitClient) -> None:
        """Test repo property caching - hits line 52."""
        # Set up cached repo
        mock_repo = Mock()
        local_client._repo = mock_repo

        # Second access should return cached
        repo = local_client.repo
        assert repo == mock_repo

    @patch("ai_code_review.core.local_git_client.asyncio.to_thread")
    async def test_get_local_diffs_new_file(
        self, mock_to_thread: Mock, local_client: LocalGitClient
    ) -> None:
        """Test _get_local_diffs with new file - hits lines 196-203."""
        # Mock diff item for new file
        mock_diff = Mock()
        mock_diff.b_path = "new_file.py"
        mock_diff.a_path = None  # New file
        mock_diff.change_type = "A"  # Added

        # Mock repository
        mock_repo = Mock()
        mock_repo.working_dir = "/test/repo"
        local_client._repo = mock_repo

        mock_to_thread.side_effect = [
            [mock_diff],  # diff_index
            "def new_function():\n    pass",  # diff content
        ]

        result = await local_client._get_local_diffs("base123")

        assert len(result) == 1
        assert result[0].file_path == "new_file.py"
        assert result[0].new_file is True
        assert result[0].deleted_file is False

    @patch("ai_code_review.core.local_git_client.asyncio.to_thread")
    async def test_get_local_diffs_deleted_file(
        self, mock_to_thread: Mock, local_client: LocalGitClient
    ) -> None:
        """Test _get_local_diffs with deleted file - hits lines 196-203."""
        # Mock diff item for deleted file
        mock_diff = Mock()
        mock_diff.b_path = None  # Deleted file
        mock_diff.a_path = "deleted_file.py"
        mock_diff.change_type = "D"  # Deleted

        # Mock repository
        mock_repo = Mock()
        mock_repo.working_dir = "/test/repo"
        local_client._repo = mock_repo

        mock_to_thread.side_effect = [
            [mock_diff],  # diff_index
            "- def old_function():\n-     pass",  # diff content
        ]

        result = await local_client._get_local_diffs("base123")

        assert len(result) == 1
        assert result[0].file_path == "deleted_file.py"
        assert result[0].new_file is False
        assert result[0].deleted_file is True

    @patch("ai_code_review.core.local_git_client.asyncio.to_thread")
    async def test_get_local_diffs_error_handling(
        self, mock_to_thread: Mock, local_client: LocalGitClient
    ) -> None:
        """Test _get_local_diffs error handling - hits lines 223."""
        from git import GitCommandError

        # Mock repository
        mock_repo = Mock()
        local_client._repo = mock_repo

        # Mock GitCommandError
        git_error = GitCommandError("diff", 1, "fatal: bad revision")
        mock_to_thread.side_effect = git_error

        with pytest.raises(GitLocalError, match="Failed to get local diffs"):
            await local_client._get_local_diffs("bad_base")

    @patch("ai_code_review.core.local_git_client.asyncio.to_thread")
    async def test_get_local_commits_error_handling(
        self, mock_to_thread: Mock, local_client: LocalGitClient
    ) -> None:
        """Test _get_local_commits error handling - hits lines 232-233."""
        from git import GitCommandError

        # Mock repository
        mock_repo = Mock()
        local_client._repo = mock_repo

        # Mock GitCommandError
        git_error = GitCommandError("log", 1, "fatal: bad revision")
        mock_to_thread.side_effect = git_error

        with pytest.raises(GitLocalError, match="Failed to get local commits"):
            await local_client._get_local_commits("bad_base")

    async def test_post_review_always_raises(
        self, local_client: LocalGitClient
    ) -> None:
        """Test post_review always raises GitLocalError - hits lines 267."""
        with pytest.raises(
            GitLocalError, match="Posting reviews is not supported in local mode"
        ):
            await local_client.post_review("local", 0, "Test review")

    async def test_simple_coverage_boost(self, local_client: LocalGitClient) -> None:
        """Test simple methods to boost coverage."""
        # Test set_target_branch again to ensure it's covered
        local_client.set_target_branch("develop")
        assert local_client._target_branch == "develop"

        # Test get_platform_name
        assert local_client.get_platform_name() == "local"
