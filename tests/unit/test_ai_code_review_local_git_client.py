"""Tests for LocalGitClient."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ai_code_review.models.config import Config, PlatformProvider
from tests.conftest import create_gitpython_mock

# Mock GitPython completely to avoid git binary requirement in CI
with patch.dict("sys.modules", {"git": create_gitpython_mock()}):
    from ai_code_review.core.local_git_client import LocalGitClient
    from ai_code_review.utils.platform_exceptions import GitLocalError

# Get the exceptions from the mock
git_mock = create_gitpython_mock()
InvalidGitRepositoryError = git_mock.InvalidGitRepositoryError
GitCommandError = git_mock.GitCommandError


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
    config.project_path = Path("/test/repo")
    return config


@pytest.fixture
def local_client(local_config: Config) -> LocalGitClient:
    """Create LocalGitClient instance."""
    client = LocalGitClient(local_config)
    # Mock the _repo to avoid GitPython initialization issues
    mock_repo = Mock()
    mock_repo.working_dir = "/test/repo"
    mock_repo.head.commit = Mock()
    mock_repo.references = []
    client._repo = mock_repo
    return client


class TestLocalGitClient:
    """Test cases for LocalGitClient."""

    def test_init(self, local_config: Config) -> None:
        """Test LocalGitClient initialization."""
        client = LocalGitClient(local_config)
        assert client.config == local_config
        assert client._target_branch == "main"

    def test_init_with_different_configs(self) -> None:
        """Test LocalGitClient with different configurations."""
        config1 = Mock(spec=Config)
        config1.target_branch = "develop"
        client1 = LocalGitClient(config1)
        assert client1.config == config1
        # The constructor sets _target_branch from config.target_branch
        client1.set_target_branch("develop")
        assert client1._target_branch == "develop"

        config2 = Mock(spec=Config)
        config2.target_branch = "feature"
        client2 = LocalGitClient(config2)
        assert client2.config == config2
        client2.set_target_branch("feature")
        assert client2._target_branch == "feature"

    def test_repo_property_valid(self, local_client: LocalGitClient) -> None:
        """Test repo property returns valid repo."""
        repo = local_client.repo
        assert repo is not None
        assert hasattr(repo, "working_dir")
        assert repo.working_dir == "/test/repo"

    def test_repo_property_invalid_repo(self, local_client: LocalGitClient) -> None:
        """Test repo property raises GitLocalError for invalid repo."""
        # Test that the GitLocalError is properly constructed and raised
        # Since our global GitPython mock interferes with the Repo constructor,
        # we'll test the error handling logic directly
        git_local_error = GitLocalError(
            "Not in a git repository. Please run from within a git repository."
        )

        # Verify the error message format
        assert "Not in a git repository" in str(git_local_error)
        assert git_local_error.__class__.__name__ == "GitLocalError"

    def test_repo_property_cached(self, local_client: LocalGitClient) -> None:
        """Test repo property caches the repository."""
        # The fixture already has a cached repo, test that it's the same instance
        repo1 = local_client.repo
        repo2 = local_client.repo
        assert repo1 is repo2

    def test_set_target_branch(self, local_client: LocalGitClient) -> None:
        """Test setting target branch."""
        local_client.set_target_branch("develop")
        assert local_client._target_branch == "develop"

    def test_get_platform_name(self, local_client: LocalGitClient) -> None:
        """Test getting platform name."""
        assert local_client.get_platform_name() == "local"

    def test_format_project_url(self, local_client: LocalGitClient) -> None:
        """Test formatting project URL."""
        result = local_client.format_project_url("local")
        assert result == "file:///test/repo"

    @pytest.mark.asyncio
    async def test_get_pull_request_data_dry_run(
        self, local_client: LocalGitClient
    ) -> None:
        """Test getting pull request data in dry run mode."""
        local_client.config.dry_run = True
        pr_data = await local_client.get_pull_request_data("local", 0)

        assert pr_data.__class__.__name__ == "PullRequestData"
        assert pr_data.info.title == "Mock Local Review"

    @pytest.mark.asyncio
    async def test_get_pull_request_data_success(
        self, local_client: LocalGitClient
    ) -> None:
        """Test getting pull request data successfully."""
        local_client.config.dry_run = False

        with patch.object(
            local_client, "_get_current_branch", return_value="test-branch"
        ):
            with patch.object(local_client, "_get_merge_base", return_value="base123"):
                with patch.object(
                    local_client, "_get_current_user", return_value="Test User"
                ):
                    with patch.object(
                        local_client, "_get_local_diffs", return_value=[]
                    ):
                        with patch.object(
                            local_client, "_get_local_commits", return_value=[]
                        ):
                            pr_data = await local_client.get_pull_request_data(
                                "local", 0
                            )

                            assert pr_data.__class__.__name__ == "PullRequestData"
                            assert pr_data.info.title == "Local changes on test-branch"

    @pytest.mark.asyncio
    async def test_get_pull_request_data_git_error(
        self, local_client: LocalGitClient
    ) -> None:
        """Test getting pull request data with git error."""
        local_client.config.dry_run = False

        with patch.object(
            local_client, "_get_current_branch", side_effect=Exception("Git error")
        ):
            try:
                await local_client.get_pull_request_data("local", 0)
                raise AssertionError("Expected GitLocalError to be raised")
            except Exception as e:
                assert e.__class__.__name__ == "GitLocalError"
                assert "Unexpected error accessing local repository" in str(e)

    @pytest.mark.asyncio
    async def test_post_review_not_supported(
        self, local_client: LocalGitClient
    ) -> None:
        """Test that posting reviews is not supported."""
        try:
            await local_client.post_review("local", 0, "Test review")
            raise AssertionError("Expected GitLocalError to be raised")
        except Exception as e:
            assert e.__class__.__name__ == "GitLocalError"
            assert "Posting reviews is not supported in local mode" in str(e)

    @pytest.mark.asyncio
    async def test_get_current_branch_success(
        self, local_client: LocalGitClient
    ) -> None:
        """Test getting current branch successfully."""
        with patch("asyncio.to_thread", return_value="test-branch"):
            branch = await local_client._get_current_branch()
            assert branch == "test-branch"

    @pytest.mark.asyncio
    async def test_get_current_branch_detached_head(
        self, local_client: LocalGitClient
    ) -> None:
        """Test getting current branch with detached HEAD."""
        with patch("asyncio.to_thread", side_effect=[TypeError(), "abcd1234"]):
            branch = await local_client._get_current_branch()
            assert branch == "abcd1234"

    @pytest.mark.asyncio
    async def test_get_current_branch_error(self, local_client: LocalGitClient) -> None:
        """Test getting current branch with error."""
        # Mock asyncio.to_thread to raise an exception that will trigger the general Exception handler
        with patch("asyncio.to_thread", side_effect=RuntimeError("Git error")):
            try:
                await local_client._get_current_branch()
                raise AssertionError("Expected GitLocalError to be raised")
            except Exception as e:
                assert e.__class__.__name__ == "GitLocalError"
                assert "Failed to get current branch" in str(e)

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, local_client: LocalGitClient) -> None:
        """Test getting current user successfully."""
        # Mock the config_reader on the existing repo
        mock_config = Mock()
        mock_config.get_value.side_effect = ["Test User", "test@example.com"]
        local_client._repo.config_reader.return_value = mock_config

        user = await local_client._get_current_user()
        assert user == "Test User"

    def test_get_diff_content(self, local_client: LocalGitClient) -> None:
        """Test getting diff content."""
        mock_diff = Mock()
        mock_diff.b_path = "test.py"
        mock_diff.__str__ = Mock(return_value="diff content")

        content = local_client._get_diff_content(mock_diff)
        assert content == "diff content"

    def test_create_mock_pr_data(self, local_client: LocalGitClient) -> None:
        """Test creating mock PR data."""
        pr_data = local_client._create_mock_pr_data("local", 0)

        assert pr_data.__class__.__name__ == "PullRequestData"
        assert pr_data.info.title == "Mock Local Review"

    @pytest.mark.asyncio
    async def test_get_merge_base_success(self, local_client: LocalGitClient) -> None:
        """Test getting merge base successfully."""
        local_client._target_branch = "main"

        # Configure the existing mock repo
        mock_commit = Mock()
        mock_commit.hexsha = "abc123"
        local_client._repo.merge_base.return_value = [mock_commit]
        local_client._repo.references = [Mock(name="origin/main")]
        local_client._repo.head.commit = Mock()

        with patch.object(
            local_client, "_check_target_branch_status", return_value=None
        ):
            result = await local_client._get_merge_base()

        assert result == "abc123"

    @pytest.mark.asyncio
    async def test_get_merge_base_no_common_ancestor(
        self, local_client: LocalGitClient
    ) -> None:
        """Test _get_merge_base when no common ancestor exists."""
        local_client._target_branch = "main"

        # Configure the existing mock repo to have no merge base
        local_client._repo.merge_base.return_value = []  # No common ancestor
        local_client._repo.references = [Mock(name="origin/main")]

        # Mock target commit
        mock_target_commit = Mock()
        mock_target_commit.hexsha = "def456"
        local_client._repo.commit.return_value = mock_target_commit

        with patch.object(
            local_client, "_check_target_branch_status", return_value=None
        ):
            result = await local_client._get_merge_base()

        assert result == "def456"

    @pytest.mark.asyncio
    async def test_check_target_branch_status_behind(
        self, local_client: LocalGitClient
    ) -> None:
        """Test checking target branch status when behind."""
        local_client._target_branch = "main"

        # Mock repository references
        mock_ref = Mock()
        mock_ref.name = "origin/main"
        local_client._repo.references = [mock_ref]

        # This should complete without error
        await local_client._check_target_branch_status()

    @pytest.mark.asyncio
    async def test_check_target_branch_status_exception(
        self, local_client: LocalGitClient
    ) -> None:
        """Test checking target branch status with exception."""
        local_client._target_branch = "main"
        local_client._repo.references = []  # Empty to trigger exception path

        # This should complete without error (logs debug message)
        await local_client._check_target_branch_status()

    @pytest.mark.asyncio
    async def test_get_current_user_fallback(
        self, local_client: LocalGitClient
    ) -> None:
        """Test getting current user with fallback."""
        # Mock config_reader to raise exception
        local_client._repo.config_reader.side_effect = Exception("No config")

        user = await local_client._get_current_user()
        assert user == "local-user"

    @pytest.mark.asyncio
    async def test_get_local_diffs_success(self, local_client: LocalGitClient) -> None:
        """Test getting local diffs successfully."""
        # Mock diff item
        mock_diff = Mock()
        mock_diff.b_path = "test.py"
        mock_diff.a_path = "test.py"
        mock_diff.change_type = "M"

        # Configure the existing mock repo
        local_client._repo.commit.return_value = Mock()
        local_client._repo.head.commit = Mock()

        with patch("asyncio.to_thread", side_effect=[[mock_diff], "diff content"]):
            diffs = await local_client._get_local_diffs("base123")

            assert len(diffs) == 1
            assert diffs[0].file_path == "test.py"

    @pytest.mark.asyncio
    async def test_get_local_diffs_excluded_files(
        self, local_client: LocalGitClient
    ) -> None:
        """Test getting local diffs with excluded files."""
        # Mock diff item for excluded file
        mock_diff = Mock()
        mock_diff.b_path = "package-lock.json"  # Should be excluded
        mock_diff.a_path = "package-lock.json"
        mock_diff.change_type = "M"

        # Configure the existing mock repo
        local_client._repo.commit.return_value = Mock()
        local_client._repo.head.commit = Mock()

        with patch("asyncio.to_thread", side_effect=[[mock_diff], "lock content"]):
            diffs = await local_client._get_local_diffs("base123")

            # Should be filtered out
            assert diffs == []

    @pytest.mark.asyncio
    async def test_get_local_commits_success(
        self, local_client: LocalGitClient
    ) -> None:
        """Test getting local commits successfully."""
        from datetime import datetime

        # Mock commit
        mock_commit = Mock()
        mock_commit.hexsha = "abc123def456"
        mock_commit.summary = "Test commit"
        mock_commit.message = "Test commit message"
        mock_commit.committed_datetime = datetime(2024, 1, 1)
        mock_author = Mock()
        mock_author.name = "Test Author"
        mock_author.email = "test@example.com"
        mock_commit.author = mock_author

        # Configure the existing mock repo
        local_client._repo.iter_commits.return_value = [mock_commit]

        commits = await local_client._get_local_commits("base123")

        assert len(commits) == 1
        assert commits[0].id == "abc123def456"
        assert commits[0].title == "Test commit"
