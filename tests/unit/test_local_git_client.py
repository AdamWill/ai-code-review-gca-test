"""Tests for LocalGitClient."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from ai_code_review.core.local_git_client import LocalGitClient
from ai_code_review.models.config import Config, PlatformProvider
from ai_code_review.models.platform import (
    PullRequestData,
)
from ai_code_review.utils.platform_exceptions import GitLocalError


@pytest.fixture
def local_config() -> Config:
    """Create test config for local mode."""
    return Config(
        platform_provider=PlatformProvider.LOCAL,
        dry_run=False,
        ai_api_key="test-key",
        max_files=10,
        max_chars=1000,
    )


@pytest.fixture
def local_client(local_config: Config) -> LocalGitClient:
    """Create LocalGitClient instance."""
    return LocalGitClient(local_config)


class TestLocalGitClient:
    """Test cases for LocalGitClient."""

    async def test_dry_run_mode(self, local_config: Config) -> None:
        """Test that dry run returns mock data."""
        local_config.dry_run = True
        client = LocalGitClient(local_config)

        result = await client.get_pull_request_data("local", 0)

        assert isinstance(result, PullRequestData)
        assert result.info.title == "Mock Local Review"
        assert result.info.state == "local"
        assert len(result.diffs) == 1
        assert len(result.commits) == 1

    async def test_post_review_raises_error(self, local_client: LocalGitClient) -> None:
        """Test that post_review raises appropriate error."""
        with pytest.raises(GitLocalError, match="Posting reviews is not supported"):
            await local_client.post_review("local", 0, "test review")

    @pytest.mark.asyncio
    async def test_get_platform_name(self, local_client: LocalGitClient) -> None:
        """Test platform name."""
        assert local_client.get_platform_name() == "local"

    @pytest.mark.asyncio
    async def test_set_target_branch(self, local_client: LocalGitClient) -> None:
        """Test setting target branch."""
        local_client.set_target_branch("develop")
        assert local_client._target_branch == "develop"

    @patch("ai_code_review.core.local_git_client.Repo")
    async def test_get_current_branch(
        self, mock_repo_class: Mock, local_client: LocalGitClient
    ) -> None:
        """Test getting current branch name."""
        # Mock repository and branch
        mock_repo = Mock()
        mock_branch = Mock()
        mock_branch.name = "feature-branch"
        mock_repo.active_branch = mock_branch
        mock_repo_class.return_value = mock_repo

        # Force recreation of repo property
        local_client._repo = None

        result = await local_client._get_current_branch()

        assert result == "feature-branch"

    @patch("ai_code_review.core.local_git_client.Repo")
    async def test_get_current_branch_detached_head(
        self, mock_repo_class: Mock, local_client: LocalGitClient
    ) -> None:
        """Test getting current branch in detached HEAD state."""
        # Mock repository in detached HEAD state
        mock_repo = Mock()
        # Configure the active_branch property to raise TypeError when accessed
        mock_active_branch = Mock()

        # Use a property mock to simulate the detached HEAD exception
        from unittest.mock import PropertyMock

        type(mock_active_branch).name = PropertyMock(
            side_effect=TypeError("detached HEAD")
        )

        mock_repo.active_branch = mock_active_branch
        mock_commit = Mock()
        mock_commit.hexsha = "abcd1234567890abcd1234567890"
        mock_repo.head.commit = mock_commit
        mock_repo_class.return_value = mock_repo

        # Force recreation of repo property
        local_client._repo = None

        result = await local_client._get_current_branch()

        assert result == "abcd1234"  # Should be first 8 chars

    @patch("ai_code_review.core.local_git_client.Repo")
    async def test_get_merge_base_with_origin(
        self, mock_repo_class: Mock, local_client: LocalGitClient
    ) -> None:
        """Test getting merge base with origin/main."""
        # Mock repository setup
        mock_repo = Mock()
        mock_commit = Mock()
        mock_commit.hexsha = "base123456789"
        mock_repo.merge_base.return_value = [mock_commit]

        # Mock references to include origin/main
        mock_ref = Mock()
        mock_ref.name = "origin/main"
        mock_repo.references = [mock_ref]

        mock_repo_class.return_value = mock_repo
        local_client._repo = None

        result = await local_client._get_merge_base()

        assert result == "base123456789"

    @patch("ai_code_review.core.local_git_client.Repo")
    async def test_invalid_git_repository(
        self, mock_repo_class: Mock, local_client: LocalGitClient
    ) -> None:
        """Test handling of invalid git repository."""
        from git import InvalidGitRepositoryError

        mock_repo_class.side_effect = InvalidGitRepositoryError("Not a git repo")

        # Force recreation of repo property
        local_client._repo = None

        with pytest.raises(GitLocalError, match="Not in a git repository"):
            _ = local_client.repo

    @patch("ai_code_review.core.local_git_client.Repo")
    @pytest.mark.asyncio
    async def test_format_project_url(
        self, mock_repo_class: Mock, local_client: LocalGitClient
    ) -> None:
        """Test formatting project URL for local repositories."""
        mock_repo = Mock()
        mock_repo.working_dir = "/path/to/repo"
        mock_repo_class.return_value = mock_repo
        local_client._repo = None

        result = local_client.format_project_url("local")

        assert result == "file:///path/to/repo"

    @patch("ai_code_review.core.local_git_client.Repo")
    async def test_get_current_user(
        self, mock_repo_class: Mock, local_client: LocalGitClient
    ) -> None:
        """Test getting current git user."""
        # Mock repository and config
        mock_repo = Mock()
        mock_config_reader = Mock()
        mock_config_reader.get_value.return_value = "Test User"
        mock_repo.config_reader.return_value = mock_config_reader
        mock_repo_class.return_value = mock_repo

        local_client._repo = None

        result = await local_client._get_current_user()

        assert result == "Test User"
        mock_config_reader.release.assert_called_once()

    @patch("ai_code_review.core.local_git_client.Repo")
    async def test_get_current_user_fallback(
        self, mock_repo_class: Mock, local_client: LocalGitClient
    ) -> None:
        """Test fallback when git user is not configured."""
        # Mock repository that raises exception
        mock_repo = Mock()
        mock_repo.config_reader.side_effect = Exception("No config")
        mock_repo_class.return_value = mock_repo

        local_client._repo = None

        result = await local_client._get_current_user()

        assert result == "local-user"

    @patch("ai_code_review.core.local_git_client.Repo")
    async def test_create_mock_pr_data(
        self, mock_repo_class: Mock, local_client: LocalGitClient
    ) -> None:
        """Test creating mock PR data."""
        result = local_client._create_mock_pr_data("local", 0)

        assert isinstance(result, PullRequestData)
        assert result.info.title == "Mock Local Review"
        assert result.info.state == "local"
        assert len(result.diffs) == 1
        assert len(result.commits) == 1
        assert result.diffs[0].file_path == "example.py"
        assert result.commits[0].title == "Mock commit for dry run"
