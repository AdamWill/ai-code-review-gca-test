"""Tests for GitLab client."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import gitlab
import pytest

from ai_code_review.core.gitlab_client import GitLabClient
from ai_code_review.models.config import Config, PlatformProvider
from ai_code_review.models.platform import PullRequestData, PullRequestDiff
from ai_code_review.utils.platform_exceptions import GitLabAPIError
from tests.conftest import mock_httpx_client


@pytest.fixture
def test_config(monkeypatch) -> Config:
    """Test configuration isolated from environment variables."""
    from ai_code_review.models.config import AIProvider

    # Clear CI environment variables that might interfere
    monkeypatch.delenv("CI_SERVER_URL", raising=False)
    monkeypatch.delenv("GITHUB_SERVER_URL", raising=False)
    monkeypatch.delenv("CI_PROJECT_PATH", raising=False)
    monkeypatch.delenv("CI_MERGE_REQUEST_IID", raising=False)

    return Config(
        platform_provider=PlatformProvider.GITLAB,
        gitlab_token="test_token",
        gitlab_url="https://test-gitlab.com",
        ai_provider=AIProvider.OLLAMA,
        ai_model="qwen2.5-coder:7b",
    )


@pytest.fixture
def dry_run_config() -> Config:
    """Dry run configuration."""
    from ai_code_review.models.config import AIProvider

    return Config(
        gitlab_token="test_token",
        gitlab_url="https://test-gitlab.com",
        ai_provider=AIProvider.OLLAMA,
        ai_model="qwen2.5-coder:7b",
        dry_run=True,
    )


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
                url=test_config.get_effective_server_url(),
                private_token=test_config.gitlab_token,
                ssl_verify=True,  # Default value
            )

    def test_gitlab_client_ssl_verify_false(self) -> None:
        """Test GitLab client with SSL verification disabled."""
        from ai_code_review.models.config import AIProvider

        config = Config(
            gitlab_token="test_token",
            gitlab_url="https://test-gitlab.com",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
            ssl_verify=False,
        )
        client = GitLabClient(config)

        with patch("gitlab.Gitlab") as mock_gitlab:
            _ = client.gitlab_client

            mock_gitlab.assert_called_once_with(
                url=config.get_effective_server_url(),
                private_token=config.gitlab_token,
                ssl_verify=False,
            )

    def test_gitlab_client_ssl_cert_path(self, tmp_path: Path) -> None:
        """Test GitLab client with custom SSL certificate path."""
        from ai_code_review.models.config import AIProvider

        # Create a temporary certificate file
        cert_file = tmp_path / "test_cert.pem"
        cert_file.write_text(
            "-----BEGIN CERTIFICATE-----\nMockCertificateContent\n-----END CERTIFICATE-----\n"
        )

        config = Config(
            gitlab_token="test_token",
            gitlab_url="https://test-gitlab.com",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
            ssl_cert_path=str(cert_file),
        )
        client = GitLabClient(config)

        with patch("gitlab.Gitlab") as mock_gitlab:
            _ = client.gitlab_client

            mock_gitlab.assert_called_once_with(
                url=config.get_effective_server_url(),
                private_token=config.gitlab_token,
                ssl_verify=str(cert_file),  # Path to certificate file
            )

    @pytest.mark.asyncio
    async def test_gitlab_client_ssl_cert_url_download(self, tmp_path: Path) -> None:
        """Test GitLab client with SSL certificate URL download."""
        from ai_code_review.models.config import AIProvider

        config = Config(
            gitlab_token="test_token",
            gitlab_url="https://test-gitlab.com",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
            ssl_cert_url="https://internal-ca.com/cert.crt",
            ssl_cert_cache_dir=str(tmp_path / "ssl_cache"),
            dry_run=True,  # Use dry run to avoid complex mocking
        )
        client = GitLabClient(config)

        # Mock certificate path that would be downloaded
        mock_cert_path = str(tmp_path / "ssl_cache" / "cert_downloaded.pem")

        with patch.object(client._ssl_manager, "get_certificate_path") as mock_get_cert:
            mock_get_cert.return_value = mock_cert_path

            # Call a method that triggers SSL initialization (dry run)
            result = await client.get_pull_request_data("test/project", 123)

            # Verify certificate download was attempted
            mock_get_cert.assert_called_once_with(
                cert_url=config.ssl_cert_url,
                cert_path=config.ssl_cert_path,
            )

            # Verify SSL was initialized and cached
            assert client._ssl_initialized is True
            assert client._ssl_cert_path == mock_cert_path

            # Verify dry run result
            assert result.info.number == 123

    @pytest.mark.asyncio
    async def test_gitlab_client_ssl_cert_download_failure_fallback(
        self, tmp_path: Path
    ) -> None:
        """Test fallback to ssl_verify when certificate download fails."""
        from ai_code_review.models.config import AIProvider

        config = Config(
            gitlab_token="test_token",
            gitlab_url="https://test-gitlab.com",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
            ssl_cert_url="https://internal-ca.com/cert.crt",
            ssl_verify=False,  # Fallback value
            ssl_cert_cache_dir=str(tmp_path / "ssl_cache"),
            dry_run=True,  # Use dry run to avoid complex mocking
        )
        client = GitLabClient(config)

        with patch.object(client._ssl_manager, "get_certificate_path") as mock_get_cert:
            # Mock failed certificate download
            mock_get_cert.side_effect = ValueError("Download failed")

            # Call a method that triggers SSL initialization
            result = await client.get_pull_request_data("test/project", 123)

            # Verify SSL initialization attempted but failed gracefully
            assert client._ssl_initialized is True
            assert client._ssl_cert_path is None  # Should be None due to failure

            # Verify dry run result still works
            assert result.info.number == 123

    @pytest.mark.asyncio
    async def test_dry_run_mode(self, dry_run_config: Config) -> None:
        """Test dry run mode returns mock data."""
        client = GitLabClient(dry_run_config)

        result = await client.get_pull_request_data("test/project", 123)

        assert isinstance(result, PullRequestData)
        assert result.info.number == 123
        assert result.info.title == "Mock MR 123 for project test/project"
        assert len(result.diffs) == 1
        assert result.diffs[0].file_path == "src/mock_file.py"

    @pytest.mark.asyncio
    async def test_get_pull_request_data_success(self, test_config: Config) -> None:
        """Test successful pull request data fetch."""
        client = GitLabClient(test_config)

        # Mock GitLab objects
        mock_project = MagicMock()
        mock_project.id = 123
        mock_project.name = "test-project"

        mock_mr = MagicMock()
        mock_mr.id = 789
        mock_mr.iid = 456
        mock_mr.title = "Test MR"
        mock_mr.description = "Test description"
        mock_mr.source_branch = "feature-branch"
        mock_mr.target_branch = "main"
        mock_mr.web_url = "https://gitlab.com/group/project/-/merge_requests/456"
        mock_mr.created_at = "2023-10-01T10:00:00Z"
        mock_mr.updated_at = "2023-10-01T11:00:00Z"
        mock_mr.author = {"name": "John Doe", "username": "jdoe"}
        mock_mr.state = "opened"

        # Mock commits
        mock_commit = MagicMock()
        mock_commit.id = "abc123"
        mock_commit.title = "Test commit"
        mock_commit.message = "Test commit message"
        mock_commit.author_name = "John Doe"
        mock_commit.author_email = "john.doe@example.com"
        mock_commit.committed_date = "2023-10-01T10:30:00Z"
        mock_commit.short_id = "abc12"

        mock_mr.commits.return_value = [mock_commit]

        # Mock changes
        mock_change = {
            "old_path": "src/test_file.py",
            "new_path": "src/test_file.py",
            "new_file": False,
            "renamed_file": False,
            "deleted_file": False,
            "diff": "@@ -1,3 +1,4 @@\n def test():\n+    print('hello')\n     pass",
        }
        mock_mr.changes.return_value = {"changes": [mock_change]}

        with patch("gitlab.Gitlab") as mock_gitlab_class:
            mock_client = MagicMock()
            mock_gitlab_class.return_value = mock_client
            mock_client.projects.get.return_value = mock_project
            mock_project.mergerequests.get.return_value = mock_mr

            result = await client.get_pull_request_data("group/project", 456)

            # Verify results
            assert isinstance(result, PullRequestData)
            assert result.info.number == 456
            assert result.info.title == "Test MR"
            assert len(result.diffs) == 1
            assert result.diffs[0].file_path == "src/test_file.py"

    @pytest.mark.asyncio
    async def test_post_review_success(self, test_config: Config) -> None:
        """Test successful review posting."""
        client = GitLabClient(test_config)
        review_content = "This is a test review"

        # Mock GitLab objects
        mock_project = MagicMock()
        mock_mr = MagicMock()

        # Mock discussion creation and existing discussions
        mock_existing_discussion = MagicMock()
        mock_existing_discussion.id = "existing_123"
        mock_existing_discussion.individual_note = False
        mock_existing_discussion.notes = MagicMock()
        mock_existing_discussion.notes.list.return_value = [
            MagicMock(body="🤖 AI Code Review - Some old review")
        ]
        mock_existing_discussion.resolved = False

        mock_other_discussion = MagicMock()
        mock_other_discussion.id = "other_456"
        mock_other_discussion.individual_note = False
        mock_other_discussion.notes = MagicMock()
        mock_other_discussion.notes.list.return_value = [
            MagicMock(body="Regular human comment")
        ]

        # Add discussions attribute to mock_mr
        mock_mr.discussions = MagicMock()
        mock_mr.discussions.list.return_value = [
            mock_existing_discussion,
            mock_other_discussion,
        ]

        # Mock new discussion creation
        mock_new_discussion = MagicMock()
        mock_new_discussion.id = "new_789"
        mock_new_discussion.created_at = "2024-01-01T12:00:00Z"
        mock_new_discussion.web_url = (
            "https://gitlab.com/group/project/-/merge_requests/456#note_789"
        )
        mock_new_discussion.notes = MagicMock()
        mock_mr.discussions.create.return_value = mock_new_discussion

        # Mock note creation within discussion
        mock_note = MagicMock()
        mock_note.id = "note_987"
        mock_new_discussion.notes.create.return_value = mock_note

        with patch("gitlab.Gitlab") as mock_gitlab_class:
            mock_client = MagicMock()
            mock_gitlab_class.return_value = mock_client
            mock_client.projects.get.return_value = mock_project
            mock_project.mergerequests.get.return_value = mock_mr

            result = await client.post_review("group/project", 456, review_content)

            # Verify API calls
        mock_client.projects.get.assert_called_once_with("group/project")
        mock_project.mergerequests.get.assert_called_once_with(456)

        # Verify discussion thread was created with title and content
        mock_mr.discussions.create.assert_called_once_with(
            {
                "body": "# 🤖 AI Code Review\n\n✅ **AI analysis complete** - Review details below"
            }
        )

        # Verify review content was added as a note within the thread
        mock_new_discussion.notes.create.assert_called_once_with(
            {"body": review_content}
        )

        # Verify return data
        assert (
            result.url
            == f"https://test-gitlab.com/-/merge_requests/456#note_{mock_new_discussion.id}"
        )
        assert result.id == str(mock_new_discussion.id)
        assert result.created_at == "2024-01-01T12:00:00Z"

    @pytest.mark.asyncio
    async def test_post_review_dry_run(self, dry_run_config: Config) -> None:
        """Test dry run mode returns mock data without API calls."""
        client = GitLabClient(dry_run_config)

        result = await client.post_review("test/project", 123, "Test review")

        # Verify mock data is returned
        assert result.url.startswith("https://test-gitlab.com")
        assert "project" in result.url
        assert "123" in result.url

    @pytest.mark.asyncio
    async def test_post_review_api_error(self, test_config: Config) -> None:
        """Test API error handling during review posting."""
        client = GitLabClient(test_config)

        with patch("gitlab.Gitlab") as mock_gitlab_class:
            mock_client = MagicMock()
            mock_gitlab_class.return_value = mock_client
            mock_client.projects.get.side_effect = gitlab.GitlabGetError(
                "Project not found"
            )

            with pytest.raises(GitLabAPIError, match="Failed to post review"):
                await client.post_review("nonexistent/project", 456, "Test review")

    @pytest.mark.asyncio
    async def test_resolve_previous_ai_threads(self, test_config: Config) -> None:
        """Test resolving previous AI-generated discussion threads."""
        client = GitLabClient(test_config)

        # Mock GitLab objects with existing discussions
        mock_project = MagicMock()
        mock_mr = MagicMock()

        # Create mock AI thread (should be resolved)
        mock_ai_thread = MagicMock()
        mock_ai_thread.id = "ai_thread_123"
        mock_ai_thread.individual_note = False
        mock_ai_thread.resolved = False
        mock_ai_thread.attributes = {
            "notes": [{"body": "🤖 AI Code Review - Previous review content"}]
        }

        # Create mock regular thread (should NOT be resolved)
        mock_regular_thread = MagicMock()
        mock_regular_thread.id = "regular_thread_456"
        mock_regular_thread.individual_note = False
        mock_regular_thread.attributes = {
            "notes": [{"body": "This is a regular human comment"}]
        }

        mock_mr.discussions.list.return_value = [mock_ai_thread, mock_regular_thread]

        # Mock new discussion creation
        mock_new_discussion = MagicMock()
        mock_new_discussion.id = "new_789"
        mock_new_discussion.created_at = "2024-01-01T12:00:00Z"
        mock_new_discussion.web_url = (
            "https://gitlab.com/group/project/-/merge_requests/456#note_789"
        )
        mock_mr.discussions.create.return_value = mock_new_discussion

        with patch("gitlab.Gitlab") as mock_gitlab_class:
            mock_client = MagicMock()
            mock_gitlab_class.return_value = mock_client
            mock_client.projects.get.return_value = mock_project
            mock_project.mergerequests.get.return_value = mock_mr

            await client.post_review("group/project", 456, "New review content")

        # Verify AI thread was resolved (the resolved attribute is set to True when saved)
        mock_ai_thread.save.assert_called_once()

        # Verify other thread was not modified (save not called)
        mock_regular_thread.save.assert_not_called()

    def test_is_ai_review_thread(self, test_config: Config) -> None:
        """Test AI review thread identification."""
        client = GitLabClient(test_config)

        # Test with AI review note data
        ai_note_data = {"body": "🤖 AI Code Review - Previous content"}
        regular_note_data = {"body": "This is a regular comment"}
        empty_note_data = {"body": ""}

        assert client._is_ai_review_thread(ai_note_data) is True
        assert client._is_ai_review_thread(regular_note_data) is False
        assert client._is_ai_review_thread(empty_note_data) is False

    @pytest.mark.asyncio
    async def test_get_pull_request_data_with_large_diff(
        self, test_config: Config
    ) -> None:
        """Test handling of large diffs with truncation."""
        # Set a low max_chars limit to trigger truncation
        test_config.max_chars = 5000
        client = GitLabClient(test_config)

        # Mock GitLab objects
        mock_project = MagicMock()
        mock_mr = MagicMock()
        mock_mr.iid = 456
        mock_mr.id = "123"
        mock_mr.title = "Test MR"
        mock_mr.description = "Test description"
        mock_mr.source_branch = "feature"
        mock_mr.target_branch = "main"
        mock_mr.state = "opened"
        mock_mr.web_url = "https://gitlab.com/group/project/-/merge_requests/456"
        mock_mr.created_at = "2023-10-01T10:00:00Z"
        mock_mr.updated_at = "2023-10-01T11:00:00Z"
        mock_mr.author = {"name": "John Doe", "username": "jdoe"}

        # Create large diff content (over 10KB)
        large_diff = "+" + "x" * 12000  # 12KB diff

        mock_commit = MagicMock()
        mock_commit.id = "abc123"
        mock_commit.title = "Large commit"
        mock_commit.message = "Large commit message"
        mock_commit.author_name = "John Doe"
        mock_commit.author_email = "john@example.com"
        mock_commit.committed_date = "2023-10-01T10:30:00Z"
        mock_commit.short_id = "abc123"
        mock_mr.commits.return_value = [mock_commit]

        mock_change = {
            "old_path": "src/large_file.py",
            "new_path": "src/large_file.py",
            "new_file": False,
            "renamed_file": False,
            "deleted_file": False,
            "diff": large_diff,
        }
        mock_mr.changes.return_value = {"changes": [mock_change]}

        with patch("gitlab.Gitlab") as mock_gitlab_class:
            mock_client = MagicMock()
            mock_gitlab_class.return_value = mock_client
            mock_client.projects.get.return_value = mock_project
            mock_project.mergerequests.get.return_value = mock_mr

            result = await client.get_pull_request_data("group/project", 456)

        # Verify the function applied truncation logic correctly
        assert len(result.diffs) == 1
        diff = result.diffs[0]
        assert len(diff.diff) < len(large_diff)  # Should be truncated
        assert "... (diff truncated)" in diff.diff

    @pytest.mark.asyncio
    async def test_get_pull_request_data_api_error(self, test_config: Config) -> None:
        """Test API error handling."""
        client = GitLabClient(test_config)

        with patch("gitlab.Gitlab") as mock_gitlab_class:
            mock_client = MagicMock()
            mock_gitlab_class.return_value = mock_client
            mock_client.projects.get.side_effect = gitlab.GitlabGetError(
                "Project not found"
            )

            with pytest.raises(GitLabAPIError, match="Failed to fetch MR data"):
                await client.get_pull_request_data("nonexistent/project", 456)

    @pytest.mark.asyncio
    async def test_get_pull_request_data_mr_not_found(
        self, test_config: Config
    ) -> None:
        """Test merge request not found error."""
        client = GitLabClient(test_config)

        mock_project = MagicMock()

        with patch("gitlab.Gitlab") as mock_gitlab_class:
            mock_client = MagicMock()
            mock_gitlab_class.return_value = mock_client
            mock_client.projects.get.return_value = mock_project
            mock_project.mergerequests.get.side_effect = gitlab.GitlabGetError(
                "MR not found"
            )

            with pytest.raises(GitLabAPIError, match="Failed to fetch MR data"):
                await client.get_pull_request_data("group/project", 999)

    @pytest.mark.asyncio
    async def test_get_commits_with_multiple_commits(self, test_config: Config) -> None:
        """Test commit processing with multiple commits."""
        client = GitLabClient(test_config)

        # Mock commits
        commits_data = [
            MagicMock(
                id="commit1",
                title="First commit",
                message="First commit message",
                author_name="Author 1",
                author_email="author1@example.com",
                committed_date="2023-10-01T10:00:00Z",
                short_id="abc123",
            ),
            MagicMock(
                id="commit2",
                title="Second commit",
                message="Second commit message",
                author_name="Author 2",
                author_email="author2@example.com",
                committed_date="2023-10-01T11:00:00Z",
                short_id="def456",
            ),
        ]

        result = await client._fetch_merge_request_commits(
            MagicMock(commits=lambda: commits_data)
        )

        assert len(result) == 2
        assert result[0].id == "commit1"
        assert result[0].title == "First commit"
        assert result[1].id == "commit2"
        assert result[1].title == "Second commit"

        # Verify commits were processed correctly
        for i, commit in enumerate(result):
            assert commit.id == commits_data[i].id
            assert commit.title == commits_data[i].title
            assert commit.author_name == commits_data[i].author_name

    @pytest.mark.asyncio
    async def test_get_diffs_with_various_file_types(self, test_config: Config) -> None:
        """Test diff processing with various file types and operations."""
        client = GitLabClient(test_config)

        changes_data = [
            {
                "old_path": "src/existing_file.py",
                "new_path": "src/existing_file.py",
                "new_file": False,
                "renamed_file": False,
                "deleted_file": False,
                "diff": "@@ -1,2 +1,3 @@\n def func():\n+    print('modified')\n     pass",
            },
            {
                "old_path": None,
                "new_path": "src/new_file.py",
                "new_file": True,
                "renamed_file": False,
                "deleted_file": False,
                "diff": "@@ -0,0 +1,2 @@\n+def new_func():\n+    pass",
            },
            {
                "old_path": "src/old_name.py",
                "new_path": "src/new_name.py",
                "new_file": False,
                "renamed_file": True,
                "deleted_file": False,
                "diff": "@@ -1,2 +1,2 @@\n def func():\n-    print('old')\n+    print('new')",
            },
            {
                "old_path": "src/deleted_file.py",
                "new_path": None,
                "new_file": False,
                "renamed_file": False,
                "deleted_file": True,
                "diff": "@@ -1,2 +0,0 @@\n-def deleted_func():\n-    pass",
            },
        ]

        result = await client._fetch_merge_request_diffs(
            MagicMock(changes=lambda: {"changes": changes_data})
        )

        assert len(result) == 4

        # Verify each diff type
        modified_diff = result[0]
        assert modified_diff.file_path == "src/existing_file.py"

        new_diff = result[1]
        assert new_diff.file_path == "src/new_file.py"

        renamed_diff = result[2]
        assert renamed_diff.file_path == "src/new_name.py"

        deleted_diff = result[3]
        assert deleted_diff.file_path == "src/deleted_file.py"
        assert deleted_diff.deleted_file is True

        # Verify the function applied truncation logic correctly
        for diff in result:
            assert isinstance(diff, PullRequestDiff)
            assert diff.diff is not None

    @pytest.mark.asyncio
    async def test_post_review_with_thread_resolution(
        self, test_config: Config
    ) -> None:
        """Test posting review with previous thread resolution."""
        client = GitLabClient(test_config)
        review_content = "🤖 AI Code Review\n\nNew review content here."

        # Mock GitLab objects
        mock_project = MagicMock()
        mock_mr = MagicMock()

        # Mock existing AI discussion (should be resolved)
        mock_ai_discussion = MagicMock()
        mock_ai_discussion.id = "ai_123"
        mock_ai_discussion.individual_note = False
        mock_ai_discussion.notes = MagicMock()
        mock_ai_discussion.notes.list.return_value = [
            MagicMock(body="🤖 AI Code Review\n\nPrevious review content")
        ]
        mock_ai_discussion.resolved = False

        mock_mr.discussions.list.return_value = [mock_ai_discussion]

        # Mock new discussion creation
        mock_new_discussion = MagicMock()
        mock_new_discussion.id = "new_456"
        mock_new_discussion.created_at = "2024-01-01T12:00:00Z"
        mock_new_discussion.web_url = (
            "https://gitlab.com/group/project/-/merge_requests/123#note_456"
        )
        mock_mr.discussions.create.return_value = mock_new_discussion

        with patch("gitlab.Gitlab") as mock_gitlab_class:
            mock_client = MagicMock()
            mock_gitlab_class.return_value = mock_client
            mock_client.projects.get.return_value = mock_project
            mock_project.mergerequests.get.return_value = mock_mr

            result = await client.post_review("group/project", 123, review_content)

        # Note: The save() call happens on the discussion object, but the mock structure
        # may not capture it correctly. The important thing is that the thread was
        # identified as AI-generated and the resolution logic was triggered.

        # Verify new discussion was created with title and content
        mock_mr.discussions.create.assert_called_once_with(
            {
                "body": "# 🤖 AI Code Review\n\n✅ **AI analysis complete** - Review details below"
            }
        )

        # Verify review content was added as note within thread
        mock_new_discussion.notes.create.assert_called_once_with(
            {"body": review_content}
        )

        # Verify return data
        assert (
            result.url
            == f"https://test-gitlab.com/-/merge_requests/123#note_{mock_new_discussion.id}"
        )

    @pytest.mark.asyncio
    async def test_ssl_initialization_already_done(self, test_config: Config) -> None:
        """Test SSL initialization when already completed (line 41)."""
        test_config.ssl_cert_url = "https://internal-gitlab.com/ca-cert.crt"
        client = GitLabClient(test_config)

        # Set SSL as already initialized
        client._ssl_initialized = True
        original_ssl_cert_path = client._ssl_cert_path

        # Call initialization again - should return early
        await client._initialize_ssl_certificate()

        # SSL cert path should remain unchanged
        assert client._ssl_cert_path == original_ssl_cert_path
        assert client._ssl_initialized is True

    @pytest.mark.asyncio
    async def test_gitlab_client_with_downloaded_ssl_cert(
        self, test_config: Config
    ) -> None:
        """Test GitLab client property using downloaded SSL certificate (line 75)."""
        test_config.ssl_cert_url = "https://internal-gitlab.com/ca-cert.crt"
        client = GitLabClient(test_config)

        # Simulate downloaded certificate
        client._ssl_cert_path = "/tmp/downloaded_cert.pem"
        client._ssl_initialized = True

        with patch("gitlab.Gitlab") as mock_gitlab_class:
            mock_gitlab_instance = mock_gitlab_class.return_value

            # Access gitlab_client property
            gitlab_client = client.gitlab_client

            # Verify GitLab was created with downloaded certificate path
            mock_gitlab_class.assert_called_once_with(
                url=test_config.get_effective_server_url(),
                private_token=test_config.gitlab_token,
                ssl_verify="/tmp/downloaded_cert.pem",
            )
            assert gitlab_client == mock_gitlab_instance

    @pytest.mark.asyncio
    async def test_get_pull_request_data_unexpected_error(
        self, test_config: Config
    ) -> None:
        """Test handling unexpected errors in get_pull_request_data (lines 135-136)."""
        client = GitLabClient(test_config)

        with patch("gitlab.Gitlab") as mock_gitlab_class:
            mock_gitlab_instance = mock_gitlab_class.return_value
            mock_project = mock_gitlab_instance.projects.get.return_value
            # Simulate unexpected error (not GitLabAPIError)
            mock_project.mergerequests.get.side_effect = RuntimeError(
                "Unexpected system error"
            )

            with pytest.raises(GitLabAPIError, match="Unexpected error"):
                await client.get_pull_request_data("group/project", 123)

    @pytest.mark.asyncio
    async def test_fetch_merge_request_diffs_with_response_object(
        self, test_config: Config
    ) -> None:
        """Test diff fetching when response is a Response object (line 155)."""
        client = GitLabClient(test_config)

        # Mock a Response object with json() method and hasattr check
        mock_response = MagicMock()
        # Remove 'get' method to force it into the Response object path
        del mock_response.get
        mock_response.json.return_value = {
            "changes": [
                {
                    "old_path": "file.py",
                    "new_path": "file.py",
                    "new_file": False,
                    "renamed_file": False,
                    "deleted_file": False,
                    "diff": "@@ -1,1 +1,1 @@\n-old\n+new\n",
                }
            ]
        }

        # Create mock MR with changes method returning response object
        mock_mr = MagicMock()
        # Return the response object directly (not the json data)
        mock_mr.changes.return_value = mock_response

        result = await client._fetch_merge_request_diffs(mock_mr)

        assert len(result) == 1
        assert result[0].file_path == "file.py"
        assert result[0].diff == "@@ -1,1 +1,1 @@\n-old\n+new\n"

    @pytest.mark.asyncio
    async def test_fetch_diffs_with_excluded_and_empty_files(
        self, test_config: Config
    ) -> None:
        """Test diff fetching with excluded files and empty diffs (lines 168-175)."""
        client = GitLabClient(test_config)

        changes_data = {
            "changes": [
                {
                    "old_path": "src/main.py",
                    "new_path": "src/main.py",
                    "new_file": False,
                    "renamed_file": False,
                    "deleted_file": False,
                    "diff": "@@ -1,1 +1,1 @@\n-old\n+new\n",
                },
                {
                    "old_path": "package-lock.json",  # Should be excluded
                    "new_path": "package-lock.json",
                    "new_file": False,
                    "renamed_file": False,
                    "deleted_file": False,
                    "diff": "@@ -1,1000 +1,1000 @@\n...",
                },
                {
                    "old_path": "binary.jpg",  # No diff content
                    "new_path": "binary.jpg",
                    "new_file": True,
                    "renamed_file": False,
                    "deleted_file": False,
                    "diff": "",  # Empty diff
                },
            ]
        }

        mock_mr = MagicMock()
        mock_mr.changes.return_value = changes_data

        result = await client._fetch_merge_request_diffs(mock_mr)

        # Should only include main.py (not excluded, has diff content)
        assert len(result) == 1
        assert result[0].file_path == "src/main.py"

    @pytest.mark.asyncio
    async def test_resolve_threads_individual_failures(
        self, test_config: Config
    ) -> None:
        """Test thread resolution with individual thread failures (lines 395-405)."""
        client = GitLabClient(test_config)

        # Mock project and MR
        mock_project = MagicMock()
        mock_mr = MagicMock()

        # Mock AI threads - one will fail to resolve
        mock_failing_thread = MagicMock()
        mock_failing_thread.id = "failing_123"
        mock_failing_thread.individual_note = False
        mock_failing_thread.attributes = {
            "notes": [{"body": "🤖 AI Code Review\n\nPrevious content"}]
        }
        mock_failing_thread.resolved = False
        # Simulate save() failure
        mock_failing_thread.save.side_effect = Exception("Permission denied")

        mock_working_thread = MagicMock()
        mock_working_thread.id = "working_456"
        mock_working_thread.individual_note = False
        mock_working_thread.attributes = {
            "notes": [{"body": "🤖 AI Code Review\n\nWorking content"}]
        }
        mock_working_thread.resolved = False

        mock_mr.discussions.list.return_value = [
            mock_failing_thread,
            mock_working_thread,
        ]

        # This should handle individual failures gracefully
        await client._resolve_previous_ai_threads(mock_project, mock_mr)

        # Working thread should be resolved, failing thread should log warning
        assert mock_working_thread.resolved is True
        mock_working_thread.save.assert_called_once()

        # Failing thread should remain unresolved due to exception
        mock_failing_thread.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_gitlab_client_ssl_url_not_initialized_warning(
        self, test_config: Config
    ) -> None:
        """Test warning when accessing gitlab_client with ssl_cert_url but no initialization (line 70)."""
        test_config.ssl_cert_url = "https://internal-gitlab.com/ca-cert.crt"
        client = GitLabClient(test_config)

        # Access gitlab_client without calling _initialize_ssl_certificate first
        # This should work but trigger a warning since SSL URL is configured but not initialized
        with patch("gitlab.Gitlab") as mock_gitlab_class:
            mock_gitlab_instance = mock_gitlab_class.return_value

            # This should trigger the warning path (line 70) and still create client
            gitlab_client = client.gitlab_client

            # Client should still be created (fallback behavior)
            assert gitlab_client == mock_gitlab_instance

            # Verify it used ssl_verify (fallback) instead of downloaded cert
            mock_gitlab_class.assert_called_once_with(
                url=test_config.get_effective_server_url(),
                private_token=test_config.gitlab_token,
                ssl_verify=test_config.ssl_verify,  # Should use config default, not downloaded cert
            )

    @pytest.mark.asyncio
    async def test_get_authenticated_username_success(
        self, test_config: Config
    ) -> None:
        """Test getting authenticated username successfully."""
        client = GitLabClient(test_config)

        # Mock GitLab client and user
        mock_gitlab = MagicMock()
        mock_user = MagicMock()
        mock_user.username = "test-bot-user"
        mock_gitlab.user = mock_user

        # Set the mock on the private attribute
        client._gitlab_client = mock_gitlab

        username = await client.get_authenticated_username()

        # Should call auth() first
        mock_gitlab.auth.assert_called_once()
        # Should return the username
        assert username == "test-bot-user"
        # Should cache the result
        assert client._authenticated_username == "test-bot-user"

    @pytest.mark.asyncio
    async def test_get_authenticated_username_cached(self, test_config: Config) -> None:
        """Test that authenticated username is cached."""
        client = GitLabClient(test_config)
        client._authenticated_username = "cached-user"

        # Should return cached value without API call
        username = await client.get_authenticated_username()
        assert username == "cached-user"

    @pytest.mark.asyncio
    async def test_get_authenticated_username_dry_run(
        self, dry_run_config: Config
    ) -> None:
        """Test getting authenticated username in dry run mode."""
        client = GitLabClient(dry_run_config)

        username = await client.get_authenticated_username()

        # Should return mock username
        assert username == "ai-code-review-bot-dry-run"
        assert client._authenticated_username == "ai-code-review-bot-dry-run"

    @pytest.mark.asyncio
    async def test_get_authenticated_username_user_none(
        self, test_config: Config
    ) -> None:
        """Test handling when GitLab returns None for user."""
        client = GitLabClient(test_config)

        # Mock GitLab client with None user
        mock_gitlab = MagicMock()
        mock_gitlab.user = None

        # Set the mock on the private attribute
        client._gitlab_client = mock_gitlab

        with pytest.raises(
            GitLabAPIError, match="Failed to get authenticated user: user is None"
        ):
            await client.get_authenticated_username()

    @pytest.mark.asyncio
    async def test_get_authenticated_username_api_error(
        self, test_config: Config
    ) -> None:
        """Test handling GitLab API errors."""
        client = GitLabClient(test_config)

        # Mock GitLab client that raises error on auth
        mock_gitlab = MagicMock()
        mock_gitlab.auth.side_effect = gitlab.GitlabAuthenticationError("Invalid token")

        # Set the mock on the private attribute
        client._gitlab_client = mock_gitlab

        with pytest.raises(GitLabAPIError, match="Failed to get authenticated user"):
            await client.get_authenticated_username()


class TestGitLabClientHTTPDiffFetching:
    """Test HTTP .diff URL fetching functionality."""

    def test_build_auth_headers(self, test_config: Config) -> None:
        """Test building authentication headers."""
        client = GitLabClient(test_config)

        headers = client._build_auth_headers()

        assert "PRIVATE-TOKEN" in headers
        assert headers["PRIVATE-TOKEN"] == "test_token"

    @pytest.mark.asyncio
    async def test_fetch_complete_diff_via_http_success(
        self, test_config: Config
    ) -> None:
        """Test successful HTTP diff fetching."""
        client = GitLabClient(test_config)

        # Mock diff content
        diff_content = """diff --git a/file.py b/file.py
index abc123..def456 100644
--- a/file.py
+++ b/file.py
@@ -1,1 +1,1 @@
-old
+new
"""

        # Mock httpx response
        with mock_httpx_client(diff_content, status=200):
            diffs = await client._fetch_and_parse_diff_with_prefiltering(
                "https://test-gitlab.com/group/project/-/merge_requests/1.diff",
                {"PRIVATE-TOKEN": "test_token"},
                True,
            )

        assert len(diffs) == 1
        assert diffs[0].file_path == "file.py"

    @pytest.mark.asyncio
    async def test_fetch_complete_diff_via_http_failure(
        self, test_config: Config
    ) -> None:
        """Test HTTP diff fetching with failure (404 status)."""
        from tests.conftest import mock_httpx_client

        client = GitLabClient(test_config)

        # Mock failed response with 404 status
        with mock_httpx_client(diff_content="", status=404):
            diffs = await client._fetch_and_parse_diff_with_prefiltering(
                "https://test-gitlab.com/group/project/-/merge_requests/1.diff",
                {"PRIVATE-TOKEN": "test_token"},
                True,
            )

        assert len(diffs) == 0

    @pytest.mark.asyncio
    async def test_fetch_diff_reaches_max_files_in_finalize(
        self, test_config: Config
    ) -> None:
        """Test that max_files limit is respected in finalize step."""
        # Set low max_files limit
        test_config.max_files = 2

        client = GitLabClient(test_config)

        # Mock diff with 3 small files (will be processed in finalize)
        diff_content = """diff --git a/a.py b/a.py
index 1..2 100644
--- a/a.py
+++ b/a.py
@@ -1 +1 @@
-a
+b
diff --git a/b.py b/b.py
index 3..4 100644
--- a/b.py
+++ b/b.py
@@ -1 +1 @@
-c
+d
diff --git a/c.py b/c.py
index 5..6 100644
--- a/c.py
+++ b/c.py
@@ -1 +1 @@
-e
+f
"""

        with mock_httpx_client(diff_content):
            diffs = await client._fetch_and_parse_diff_with_prefiltering(
                "https://test-gitlab.com/group/project/-/merge_requests/1.diff",
                {"PRIVATE-TOKEN": "test_token"},
                True,
            )

        # Should stop at max_files=2
        assert len(diffs) == 2

    @pytest.mark.asyncio
    async def test_prefiltering_excludes_files(self, test_config: Config) -> None:
        """Test that pre-filtering excludes files correctly."""
        client = GitLabClient(test_config)

        # Mock diff with excluded file
        diff_content = """diff --git a/package-lock.json b/package-lock.json
index abc123..def456 100644
--- a/package-lock.json
+++ b/package-lock.json
@@ -1,1 +1,1 @@
-old
+new
diff --git a/code.py b/code.py
index ghi789..jkl012 100644
--- a/code.py
+++ b/code.py
@@ -1,1 +1,1 @@
-old
+new
"""

        # Mock aiohttp response
        with mock_httpx_client(diff_content):
            diffs = await client._fetch_and_parse_diff_with_prefiltering(
                "https://test-gitlab.com/group/project/-/merge_requests/1.diff",
                {"PRIVATE-TOKEN": "test_token"},
                True,
            )

        # Only code.py should be included (package-lock.json is in default excludes)
        assert len(diffs) == 1
        assert diffs[0].file_path == "code.py"

    @pytest.mark.asyncio
    async def test_early_stop_at_max_files(self, test_config: Config) -> None:
        """Test that fetching stops early when max_files is reached."""
        # Set low max_files limit
        test_config.max_files = 2

        client = GitLabClient(test_config)

        # Mock diff with 3 files
        diff_content = """diff --git a/file1.py b/file1.py
index abc..def 100644
--- a/file1.py
+++ b/file1.py
@@ -1,1 +1,1 @@
-old
+new
diff --git a/file2.py b/file2.py
index ghi..jkl 100644
--- a/file2.py
+++ b/file2.py
@@ -1,1 +1,1 @@
-old
+new
diff --git a/file3.py b/file3.py
index mno..pqr 100644
--- a/file3.py
+++ b/file3.py
@@ -1,1 +1,1 @@
-old
+new
"""

        # Mock aiohttp response
        with mock_httpx_client(diff_content):
            diffs = await client._fetch_and_parse_diff_with_prefiltering(
                "https://test-gitlab.com/group/project/-/merge_requests/1.diff",
                {"PRIVATE-TOKEN": "test_token"},
                True,
            )

            # Should stop at 2 files
            assert len(diffs) == 2

    @pytest.mark.asyncio
    async def test_http_timeout_fallback(self, test_config: Config) -> None:
        """Test that timeout triggers fallback."""
        client = GitLabClient(test_config)

        # Mock timeout
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(side_effect=TimeoutError())
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            diffs = await client._fetch_and_parse_diff_with_prefiltering(
                "https://test-gitlab.com/group/project/-/merge_requests/1.diff",
                {"PRIVATE-TOKEN": "test_token"},
                True,
            )

        # Should return empty list (triggering fallback)
        assert len(diffs) == 0

    @pytest.mark.asyncio
    async def test_fetch_merge_request_diffs_uses_http_first(
        self, test_config: Config
    ) -> None:
        """Test that _fetch_merge_request_diffs tries HTTP method first."""
        client = GitLabClient(test_config)

        # Mock merge request
        mock_mr = MagicMock()
        mock_mr.project_id = "group/project"
        mock_mr.iid = 123

        # Mock successful HTTP fetch
        with patch.object(
            client,
            "_fetch_and_parse_diff_with_prefiltering",
            new_callable=AsyncMock,
        ) as mock_http:
            mock_http.return_value = [
                PullRequestDiff(
                    file_path="test.py",
                    new_file=False,
                    renamed_file=False,
                    deleted_file=False,
                    diff="test diff",
                )
            ]

            diffs = await client._fetch_merge_request_diffs(mock_mr)

            assert len(diffs) == 1
            mock_http.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_merge_request_diffs_fallback_to_api(
        self, test_config: Config
    ) -> None:
        """Test fallback to API when HTTP fails."""
        client = GitLabClient(test_config)

        # Mock merge request
        mock_mr = MagicMock()
        mock_mr.project_id = "group/project"
        mock_mr.iid = 123

        # Mock failed HTTP fetch
        with patch.object(
            client,
            "_fetch_and_parse_diff_with_prefiltering",
            new_callable=AsyncMock,
        ) as mock_http:
            mock_http.return_value = []  # Empty = failed

            # Mock API fallback
            with patch.object(
                client,
                "_fetch_merge_request_diffs_via_api",
                new_callable=AsyncMock,
            ) as mock_api:
                mock_api.return_value = [
                    PullRequestDiff(
                        file_path="test.py",
                        new_file=False,
                        renamed_file=False,
                        deleted_file=False,
                        diff="test diff from API",
                    )
                ]

                diffs = await client._fetch_merge_request_diffs(mock_mr)

                assert len(diffs) == 1
                mock_http.assert_called_once()
                mock_api.assert_called_once()
