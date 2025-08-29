"""Tests for GitLab client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import gitlab
import pytest

from ai_code_review.core.gitlab_client import GitLabClient
from ai_code_review.models.config import Config
from ai_code_review.models.gitlab import MergeRequestData, MergeRequestDiff
from ai_code_review.utils.exceptions import GitLabAPIError


@pytest.fixture
def test_config() -> Config:
    """Test configuration."""
    return Config(
        gitlab_token="test_token", gitlab_url="https://test-gitlab.com", dry_run=False
    )


@pytest.fixture
def dry_run_config() -> Config:
    """Dry run configuration."""
    return Config(gitlab_token="test_token", dry_run=True)


class TestGitLabClient:
    """Test GitLab client functionality."""

    def test_client_initialization(self, test_config: Config) -> None:
        """Test GitLab client initialization."""
        client = GitLabClient(test_config)

        assert client.config == test_config
        assert client._gitlab_client is None

    def test_gitlab_client_property(self, test_config: Config) -> None:
        """Test GitLab client property creates instance."""
        client = GitLabClient(test_config)

        with patch("gitlab.Gitlab") as mock_gitlab:
            _ = client.gitlab_client

            mock_gitlab.assert_called_once_with(
                url=test_config.gitlab_url, private_token=test_config.gitlab_token
            )

    @pytest.mark.asyncio
    async def test_dry_run_mode(self, dry_run_config: Config) -> None:
        """Test dry run mode returns mock data."""
        client = GitLabClient(dry_run_config)

        result = await client.get_merge_request_data("test/project", 123)

        assert isinstance(result, MergeRequestData)
        assert result.info.iid == 123
        assert result.info.title == "Mock MR 123 for project test/project"
        assert len(result.diffs) == 1
        assert result.diffs[0].file_path == "src/mock_file.py"

    @pytest.mark.asyncio
    async def test_get_merge_request_data_success(self, test_config: Config) -> None:
        """Test successful MR data fetch."""
        client = GitLabClient(test_config)

        # Mock GitLab objects
        mock_project = MagicMock()
        mock_mr = MagicMock()
        mock_mr.id = 789
        mock_mr.iid = 123
        mock_mr.title = "Test MR"
        mock_mr.description = "Test description"
        mock_mr.source_branch = "feature"
        mock_mr.target_branch = "main"
        mock_mr.author = {"name": "test_user"}
        mock_mr.state = "opened"
        mock_mr.web_url = "https://test-gitlab.com/test/project/-/merge_requests/123"

        # Mock changes
        mock_mr.changes.return_value = {
            "changes": [
                {
                    "old_path": "src/test.py",
                    "new_path": "src/test.py",
                    "new_file": False,
                    "renamed_file": False,
                    "deleted_file": False,
                    "diff": "@@ -1,1 +1,1 @@\n-old\n+new",
                }
            ]
        }

        # Setup mocks by patching the private attribute
        with patch.object(client, "_gitlab_client", mock_client := MagicMock()):
            mock_client.projects.get.return_value = mock_project
            mock_project.mergerequests.get.return_value = mock_mr

            result = await client.get_merge_request_data("test/project", 123)

            # Verify results
            assert isinstance(result, MergeRequestData)
            assert result.info.iid == 123
            assert result.info.title == "Test MR"
            assert result.info.author == "test_user"
            assert len(result.diffs) == 1
            assert result.diffs[0].file_path == "src/test.py"
            assert "@@ -1,1 +1,1 @@" in result.diffs[0].diff

    @pytest.mark.asyncio
    async def test_gitlab_api_error_handling(self, test_config: Config) -> None:
        """Test GitLab API error handling."""
        client = GitLabClient(test_config)

        with patch.object(client, "_gitlab_client", mock_client := MagicMock()):
            mock_client.projects.get.side_effect = gitlab.GitlabError(
                "Project not found"
            )

            with pytest.raises(GitLabAPIError, match="Failed to fetch MR data"):
                await client.get_merge_request_data("nonexistent/project", 123)

    def test_content_limits_basic_functionality(self, test_config: Config) -> None:
        """Test basic content limits functionality."""
        client = GitLabClient(test_config)

        # Test with diffs under the limit
        diffs = [
            MergeRequestDiff(file_path="file1.py", diff="small diff"),
            MergeRequestDiff(file_path="file2.py", diff="another small diff"),
        ]

        limited = client._apply_content_limits(diffs)

        # Should keep all diffs when under limit
        assert len(limited) == 2
        assert limited[0].file_path == "file1.py"
        assert limited[1].file_path == "file2.py"
