"""Simple focused tests for LocalGitClient to improve coverage."""

from __future__ import annotations

import shutil
from unittest.mock import Mock, patch

import pytest

from ai_code_review.models.config import Config, PlatformProvider
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


class TestLocalGitClientSimple:
    """Simple focused test cases for LocalGitClient to improve coverage."""

    def test_repo_property_cached_access(self, local_client: LocalGitClient) -> None:
        """Test repo property when already cached - hits line 52."""
        # Set up cached repo
        mock_repo = Mock()
        mock_repo.working_dir = "/test/repo"
        local_client._repo = mock_repo

        # Access should return cached repo
        repo = local_client.repo
        assert repo == mock_repo

    @patch("ai_code_review.core.local_git_client.asyncio.to_thread")
    async def test_get_current_user_fallback(
        self, mock_to_thread: Mock, local_client: LocalGitClient
    ) -> None:
        """Test _get_current_user fallback behavior - hits lines 163-188."""
        # Mock repository
        mock_repo = Mock()
        local_client._repo = mock_repo

        # Mock the config reader chain to fail
        mock_config = Mock()
        mock_config.get_value.side_effect = Exception("No config")
        mock_repo.config_reader.return_value = mock_config

        result = await local_client._get_current_user()

        # Should return fallback (actual implementation returns "local-user")
        assert result == "local-user"

    @patch("ai_code_review.core.local_git_client.asyncio.to_thread")
    async def test_get_current_user_success(
        self, mock_to_thread: Mock, local_client: LocalGitClient
    ) -> None:
        """Test _get_current_user success - hits lines 155-162."""
        # Mock repository
        mock_repo = Mock()
        local_client._repo = mock_repo

        # Mock the config reader chain to succeed
        mock_config = Mock()
        mock_config.get_value.side_effect = ["John Doe", "john@example.com"]
        mock_repo.config_reader.return_value = mock_config

        result = await local_client._get_current_user()

        # Should return just the name (actual implementation behavior)
        assert result == "John Doe"

    @patch("ai_code_review.core.local_git_client.asyncio.to_thread")
    async def test_check_target_branch_status_debug_log(
        self, mock_to_thread: Mock, local_client: LocalGitClient
    ) -> None:
        """Test _check_target_branch_status debug logging - hits lines 276-277."""
        # Mock repository
        mock_repo = Mock()
        mock_repo.references = []  # Empty references to trigger exception
        local_client._repo = mock_repo

        # This should log debug message and not raise
        await local_client._check_target_branch_status()

        # Should complete without error (debug logging path)

    @patch("ai_code_review.core.local_git_client.asyncio.to_thread")
    async def test_get_merge_base_fallback_path(
        self, mock_to_thread: Mock, local_client: LocalGitClient
    ) -> None:
        """Test _get_merge_base fallback to local branch - hits lines 130-145."""
        # Mock repository with no origin references
        mock_repo = Mock()
        mock_references = []  # No origin/main reference
        mock_repo.references = mock_references
        local_client._repo = mock_repo

        # Mock merge_base to return a result
        mock_commit = Mock()
        mock_commit.hexsha = "abc123def456"
        mock_to_thread.return_value = [mock_commit]

        # Mock _check_target_branch_status to succeed
        with patch.object(local_client, "_check_target_branch_status"):
            result = await local_client._get_merge_base()

            assert result == "abc123def456"

    @patch("ai_code_review.core.local_git_client.asyncio.to_thread")
    async def test_get_merge_base_no_common_ancestor(
        self, mock_to_thread: Mock, local_client: LocalGitClient
    ) -> None:
        """Test _get_merge_base with no common ancestor - hits lines 140-145."""
        # Mock repository
        mock_repo = Mock()
        mock_repo.references = []
        local_client._repo = mock_repo

        # Mock merge_base to return empty list (no common ancestor)
        mock_to_thread.return_value = []

        # Mock target commit
        mock_commit = Mock()
        mock_commit.hexsha = "target123"
        mock_repo.commit.return_value = mock_commit

        # Mock _check_target_branch_status to succeed
        with patch.object(local_client, "_check_target_branch_status"):
            result = await local_client._get_merge_base()

            assert result == "target123"

    @patch("ai_code_review.core.local_git_client.asyncio.to_thread")
    async def test_get_local_diffs_binary_file_skip(
        self, mock_to_thread: Mock, local_client: LocalGitClient
    ) -> None:
        """Test _get_local_diffs skipping binary files - hits lines 192."""
        # Mock diff item for binary file
        mock_diff = Mock()
        mock_diff.b_path = "image.png"
        mock_diff.a_path = "image.png"
        mock_diff.change_type = "M"

        # Mock repository
        mock_repo = Mock()
        mock_repo.working_dir = "/test/repo"
        local_client._repo = mock_repo

        # Mock diff content to be None (binary file)
        mock_to_thread.side_effect = [
            [mock_diff],  # diff_index
            None,  # diff content is None for binary
        ]

        result = await local_client._get_local_diffs("base123")

        # Should skip binary file
        assert result == []

    @patch("ai_code_review.core.local_git_client.asyncio.to_thread")
    async def test_get_local_diffs_renamed_file(
        self, mock_to_thread: Mock, local_client: LocalGitClient
    ) -> None:
        """Test _get_local_diffs with renamed file - hits lines 196-203."""
        # Mock diff item for renamed file
        mock_diff = Mock()
        mock_diff.b_path = "new_name.py"
        mock_diff.a_path = "old_name.py"
        mock_diff.change_type = "R"  # Renamed

        # Mock repository
        mock_repo = Mock()
        mock_repo.working_dir = "/test/repo"
        local_client._repo = mock_repo

        mock_to_thread.side_effect = [
            [mock_diff],  # diff_index
            "renamed file content",  # diff content
        ]

        result = await local_client._get_local_diffs("base123")

        assert len(result) == 1
        assert result[0].file_path == "new_name.py"
        assert result[0].new_file is False
        assert result[0].deleted_file is False

    async def test_format_project_url_with_valid_working_dir(
        self, local_client: LocalGitClient
    ) -> None:
        """Test format_project_url with valid working_dir."""
        # Mock the internal _repo with valid working_dir
        mock_repo = Mock()
        mock_repo.working_dir = "/test/repo"
        local_client._repo = mock_repo

        result = local_client.format_project_url("local")

        # Should format correctly
        assert result == "file:///test/repo"
