"""Tests for GitHub client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from github import GithubException

from ai_code_review.core.github_client import GitHubClient
from ai_code_review.models.config import AIProvider, Config, PlatformProvider
from ai_code_review.models.platform import PullRequestData, PullRequestDiff
from ai_code_review.utils.platform_exceptions import GitHubAPIError
from tests.conftest import mock_httpx_client


@pytest.fixture
def test_config(monkeypatch) -> Config:
    """Test configuration for GitHub isolated from environment variables."""
    # Clear CI environment variables that might interfere
    monkeypatch.delenv("CI_SERVER_URL", raising=False)
    monkeypatch.delenv("GITHUB_SERVER_URL", raising=False)
    monkeypatch.delenv("CI_PROJECT_PATH", raising=False)
    monkeypatch.delenv("CI_MERGE_REQUEST_IID", raising=False)

    return Config(
        platform_provider=PlatformProvider.GITHUB,
        github_token="ghp_test_token",
        github_url="https://api.github.com",
        ai_provider=AIProvider.OLLAMA,  # Use Ollama to avoid API key requirement
        ai_model="qwen2.5-coder:7b",
        dry_run=False,
    )


@pytest.fixture
def dry_run_config() -> Config:
    """Dry run configuration for GitHub."""
    return Config(
        platform_provider=PlatformProvider.GITHUB,
        github_token="ghp_test_token",
        ai_provider=AIProvider.OLLAMA,
        ai_model="qwen2.5-coder:7b",
        dry_run=True,
    )


class TestGitHubClient:
    """Test GitHub client functionality."""

    def test_client_initialization(self, test_config: Config) -> None:
        """Test GitHub client initialization."""
        client = GitHubClient(test_config)

        assert client.config == test_config
        assert client._github_client is None

    def test_github_client_property(self, test_config: Config) -> None:
        """Test GitHub client property creates instance."""
        client = GitHubClient(test_config)

        with (
            patch("ai_code_review.core.github_client.Github") as mock_github,
            patch("ai_code_review.core.github_client.Auth") as mock_auth,
        ):
            mock_auth_token = MagicMock()
            mock_auth.Token.return_value = mock_auth_token

            _ = client.github_client

            mock_auth.Token.assert_called_once_with(test_config.github_token)
            mock_github.assert_called_once_with(
                auth=mock_auth_token,
                base_url=test_config.get_effective_server_url(),
            )

    def test_get_platform_name(self, test_config: Config) -> None:
        """Test get platform name."""
        client = GitHubClient(test_config)
        assert client.get_platform_name() == "github"

    def test_format_project_url(self, test_config: Config) -> None:
        """Test format project URL."""
        client = GitHubClient(test_config)
        url = client.format_project_url("owner/repo")
        assert url == "https://github.com/owner/repo"

    @pytest.mark.asyncio
    async def test_get_pull_request_data_dry_run(self, dry_run_config: Config) -> None:
        """Test get pull request data in dry run mode."""
        client = GitHubClient(dry_run_config)

        result = await client.get_pull_request_data("owner/repo", 123)

        assert isinstance(result, PullRequestData)
        assert result.info.number == 123
        assert result.info.title == "Mock PR 123 for project owner/repo"
        assert result.info.state == "open"
        assert "owner/repo" in result.info.web_url
        assert len(result.diffs) > 0
        assert len(result.commits) > 0

    @pytest.mark.asyncio
    async def test_post_review_dry_run(self, dry_run_config: Config) -> None:
        """Test post review in dry run mode."""
        client = GitHubClient(dry_run_config)

        response = await client.post_review("owner/repo", 123, "Test review content")

        assert response.id == "mock_comment_123"
        assert "owner/repo" in response.url
        assert "pull/123" in response.url
        assert response.author == "AI Code Review (DRY RUN)"
        assert response.content_preview == "Test review content"

    @pytest.mark.asyncio
    async def test_get_pull_request_data_api_call(self, test_config: Config) -> None:
        """Test get pull request data with mocked API call."""
        client = GitHubClient(test_config)

        # Mock GitHub API objects
        mock_user = MagicMock()
        mock_user.login = "test_author"

        mock_head = MagicMock()
        mock_head.ref = "feature/test"

        mock_base = MagicMock()
        mock_base.ref = "main"

        mock_pr = MagicMock()
        mock_pr.id = 12345
        mock_pr.number = 123
        mock_pr.title = "Test PR"
        mock_pr.body = "Test description"
        mock_pr.head = mock_head
        mock_pr.base = mock_base
        mock_pr.user = mock_user
        mock_pr.state = "open"
        mock_pr.html_url = "https://github.com/owner/repo/pull/123"

        # Mock file objects
        mock_file = MagicMock()
        mock_file.filename = "test.py"
        mock_file.status = "modified"
        mock_file.patch = (
            "@@ -1,3 +1,3 @@\n def test():\n-    return 'old'\n+    return 'new'"
        )

        mock_pr.get_files.return_value = [mock_file]

        # Mock commit objects
        mock_commit_data = MagicMock()
        mock_commit_data.sha = "abc123456789"
        mock_commit_data.commit.message = "Test commit\n\nTest commit description"
        mock_commit_data.commit.author.name = "Test Author"
        mock_commit_data.commit.author.email = "test@example.com"
        mock_commit_data.commit.author.date.isoformat.return_value = (
            "2024-01-01T12:00:00Z"
        )

        mock_pr.get_commits.return_value = [mock_commit_data]

        # Mock GitHub client and repository
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr

        with patch.object(client, "_github_client") as mock_github_client:
            mock_github_client.get_repo.return_value = mock_repo

            result = await client.get_pull_request_data("owner/repo", 123)

            assert isinstance(result, PullRequestData)
            assert result.info.number == 123
            assert result.info.title == "Test PR"
            assert result.info.description == "Test description"
            assert result.info.source_branch == "feature/test"
            assert result.info.target_branch == "main"
            assert result.info.author == "test_author"
            assert result.info.state == "open"
            assert len(result.diffs) == 1
            assert result.diffs[0].file_path == "test.py"
            assert len(result.commits) == 1
            assert result.commits[0].title == "Test commit"

    @pytest.mark.asyncio
    async def test_post_review_api_call(self, test_config: Config) -> None:
        """Test post review with mocked API call."""
        client = GitHubClient(test_config)
        review_content = "## AI Code Review\n\nThis is a test review."

        # Mock GitHub API objects
        mock_comment = MagicMock()
        mock_comment.id = 789
        mock_comment.html_url = (
            "https://github.com/owner/repo/pull/123#issuecomment-789"
        )
        mock_comment.created_at.isoformat.return_value = "2024-01-01T12:00:00Z"
        mock_comment.user.login = "github-actions[bot]"

        mock_pr = MagicMock()
        mock_pr.create_issue_comment.return_value = mock_comment

        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr

        with patch.object(client, "_github_client") as mock_github_client:
            mock_github_client.get_repo.return_value = mock_repo

            result = await client.post_review("owner/repo", 123, review_content)

            # Verify API calls
            mock_github_client.get_repo.assert_called_once_with("owner/repo")
            mock_repo.get_pull.assert_called_once_with(123)
            mock_pr.create_issue_comment.assert_called_once_with(review_content)

            # Verify return data
            assert result.id == "789"
            assert (
                result.url == "https://github.com/owner/repo/pull/123#issuecomment-789"
            )
            assert result.created_at == "2024-01-01T12:00:00Z"
            assert result.author == "github-actions[bot]"

    @pytest.mark.asyncio
    async def test_post_review_github_error(self, test_config: Config) -> None:
        """Test review posting with GitHub API error."""
        client = GitHubClient(test_config)
        review_content = "## AI Code Review\n\nThis is a test review."

        with patch.object(client, "_github_client") as mock_github_client:
            mock_github_client.get_repo.side_effect = GithubException(
                status=500, data="GitHub API Error"
            )

            with pytest.raises(GitHubAPIError) as exc_info:
                await client.post_review("owner/repo", 123, review_content)

            assert "Failed to post review to GitHub" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_pull_request_diffs_success(self, test_config: Config) -> None:
        """Test fetching PR diffs successfully."""
        client = GitHubClient(test_config)

        # Mock file objects
        mock_file1 = MagicMock()
        mock_file1.filename = "src/test.py"
        mock_file1.status = "modified"
        mock_file1.patch = (
            "@@ -1,3 +1,3 @@\n def test():\n-    return 'old'\n+    return 'new'"
        )

        mock_file2 = MagicMock()
        mock_file2.filename = "src/new_file.py"
        mock_file2.status = "added"
        mock_file2.patch = "@@ -0,0 +1,5 @@\n+def new_function():\n+    return 'new'"

        mock_pr = MagicMock()
        mock_pr.get_files.return_value = [mock_file1, mock_file2]

        diffs = await client._fetch_pull_request_diffs(mock_pr)

        assert len(diffs) == 2
        assert diffs[0].file_path == "src/test.py"
        assert diffs[0].new_file is False
        assert diffs[1].file_path == "src/new_file.py"
        assert diffs[1].new_file is True

    @pytest.mark.asyncio
    async def test_fetch_pull_request_commits_success(
        self, test_config: Config
    ) -> None:
        """Test fetching PR commits successfully."""
        client = GitHubClient(test_config)

        # Mock commit objects
        mock_commit = MagicMock()
        mock_commit.sha = "abc123456789"
        mock_commit.commit.message = "Test commit\n\nTest description"
        mock_commit.commit.author.name = "Test Author"
        mock_commit.commit.author.email = "test@example.com"
        mock_commit.commit.author.date.isoformat.return_value = "2024-01-01T12:00:00Z"

        mock_pr = MagicMock()
        mock_pr.get_commits.return_value = [mock_commit]

        commits = await client._fetch_pull_request_commits(mock_pr)

        assert len(commits) == 1
        assert commits[0].id == "abc123456789"
        assert commits[0].message == "Test commit\n\nTest description"
        assert commits[0].author_name == "Test Author"
        assert commits[0].author_email == "test@example.com"
        assert commits[0].committed_date == "2024-01-01T12:00:00Z"

    @pytest.mark.asyncio
    async def test_get_pull_request_data_github_error(
        self, test_config: Config
    ) -> None:
        """Test GitHub API error handling in get_pull_request_data."""
        client = GitHubClient(test_config)

        with patch.object(client, "_github_client") as mock_github_client:
            mock_github_client.get_repo.side_effect = GithubException(
                status=429, data="GitHub rate limit exceeded"
            )

            with pytest.raises(GitHubAPIError) as exc_info:
                await client.get_pull_request_data("owner/repo", 123)

            assert "Failed to fetch PR data" in str(exc_info.value)
            assert "GitHub rate limit exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_commits_github_error(self, test_config: Config) -> None:
        """Test GitHub API error handling in fetch commits."""
        client = GitHubClient(test_config)

        mock_pr = MagicMock()
        mock_pr.get_commits.side_effect = GithubException(
            status=500, data="Internal server error"
        )

        with pytest.raises(GitHubAPIError) as exc_info:
            await client._fetch_pull_request_commits(mock_pr)

        assert "Failed to fetch commits" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_diffs_with_binary_files(self, test_config: Config) -> None:
        """Test handling of binary files (no patch content)."""
        client = GitHubClient(test_config)

        # Mock files - some with patch, some without (binary)
        mock_file1 = MagicMock()
        mock_file1.filename = "src/code.py"
        mock_file1.status = "modified"
        mock_file1.patch = "@@ -1,3 +1,3 @@\n-old\n+new"

        mock_binary_file = MagicMock()
        mock_binary_file.filename = "image.png"
        mock_binary_file.status = "added"
        mock_binary_file.patch = None  # Binary files have no patch

        mock_pr = MagicMock()
        mock_pr.get_files.return_value = [mock_file1, mock_binary_file]

        diffs = await client._fetch_pull_request_diffs(mock_pr)

        # Should only include file with patch content
        assert len(diffs) == 1
        assert diffs[0].file_path == "src/code.py"

    @pytest.mark.asyncio
    async def test_fetch_diffs_with_excluded_files(self, test_config: Config) -> None:
        """Test file exclusion logic."""
        # Add exclude patterns to config
        test_config.exclude_patterns = ["*.log", "package-lock.json"]
        client = GitHubClient(test_config)

        # Mock files - some should be excluded
        mock_file1 = MagicMock()
        mock_file1.filename = "src/code.py"
        mock_file1.status = "modified"
        mock_file1.patch = "@@ -1,3 +1,3 @@\n-old\n+new"

        mock_excluded_file = MagicMock()
        mock_excluded_file.filename = "debug.log"
        mock_excluded_file.status = "modified"
        mock_excluded_file.patch = "@@ -1,3 +1,3 @@\n-old log\n+new log"

        mock_pr = MagicMock()
        mock_pr.get_files.return_value = [mock_file1, mock_excluded_file]

        diffs = await client._fetch_pull_request_diffs(mock_pr)

        # Should only include non-excluded file
        assert len(diffs) == 1
        assert diffs[0].file_path == "src/code.py"

    @pytest.mark.asyncio
    async def test_fetch_diffs_max_files_limit(self, test_config: Config) -> None:
        """Test max files limit enforcement."""
        # Set low limit for testing
        test_config.max_files = 2
        client = GitHubClient(test_config)

        # Mock 3 files - should only process 2
        mock_files = []
        for i in range(3):
            mock_file = MagicMock()
            mock_file.filename = f"file{i}.py"
            mock_file.status = "modified"
            mock_file.patch = f"@@ -1,3 +1,3 @@\n-old{i}\n+new{i}"
            mock_files.append(mock_file)

        mock_pr = MagicMock()
        mock_pr.get_files.return_value = mock_files

        diffs = await client._fetch_pull_request_diffs(mock_pr)

        # Should stop at max_files limit
        assert len(diffs) == 2
        assert diffs[0].file_path == "file0.py"
        assert diffs[1].file_path == "file1.py"

    @pytest.mark.asyncio
    async def test_fetch_diffs_github_error(self, test_config: Config) -> None:
        """Test GitHub API error handling in fetch diffs."""
        client = GitHubClient(test_config)

        mock_pr = MagicMock()
        mock_pr.get_files.side_effect = GithubException(
            status=403, data="Forbidden access"
        )

        with pytest.raises(GitHubAPIError) as exc_info:
            await client._fetch_pull_request_diffs(mock_pr)

        assert "Failed to fetch diffs" in str(exc_info.value)


class TestGitHubClientAuthentication:
    """Test authentication-related methods."""

    @pytest.mark.asyncio
    async def test_get_authenticated_username_cached(self, test_config: Config) -> None:
        """Test that authenticated username is cached."""
        client = GitHubClient(test_config)
        client._authenticated_username = "cached-user"

        username = await client.get_authenticated_username()

        assert username == "cached-user"

    @pytest.mark.asyncio
    async def test_get_authenticated_username_dry_run(
        self, test_config: Config
    ) -> None:
        """Test authenticated username in dry-run mode."""
        test_config.dry_run = True
        client = GitHubClient(test_config)

        username = await client.get_authenticated_username()

        assert username == "ai-code-review-bot-dry-run"
        assert client._authenticated_username == "ai-code-review-bot-dry-run"

    @pytest.mark.asyncio
    async def test_get_authenticated_username_from_api(
        self, test_config: Config
    ) -> None:
        """Test getting authenticated username from GitHub API."""
        test_config.dry_run = False
        client = GitHubClient(test_config)

        # Mock GitHub user
        mock_user = MagicMock()
        mock_user.login = "github-user"
        client.github_client.get_user = MagicMock(return_value=mock_user)

        username = await client.get_authenticated_username()

        assert username == "github-user"
        assert client._authenticated_username == "github-user"

    @pytest.mark.asyncio
    async def test_get_authenticated_username_api_error(
        self, test_config: Config
    ) -> None:
        """Test handling of GitHub API error when getting username."""
        from ai_code_review.utils.platform_exceptions import GitHubAPIError

        test_config.dry_run = False
        client = GitHubClient(test_config)

        # Mock GitHub API error
        client.github_client.get_user = MagicMock(
            side_effect=GithubException(401, "Unauthorized")
        )

        with pytest.raises(GitHubAPIError, match="Failed to get authenticated user"):
            await client.get_authenticated_username()


class TestGitHubClientHTTPDiffFetching:
    """Test HTTP .diff URL fetching functionality."""

    def test_build_diff_url_github_com(self, test_config: Config) -> None:
        """Test building diff URL for GitHub.com."""
        client = GitHubClient(test_config)

        url = client._build_diff_url("owner/repo", 123)

        assert url == "https://github.com/owner/repo/pull/123.diff"

    def test_build_diff_url_github_enterprise(self, monkeypatch) -> None:
        """Test building diff URL for GitHub Enterprise."""
        # Clear CI environment variables that might interfere
        monkeypatch.delenv("CI_SERVER_URL", raising=False)
        monkeypatch.delenv("GITHUB_SERVER_URL", raising=False)

        config = Config(
            platform_provider=PlatformProvider.GITHUB,
            github_token="ghp_test_token",
            github_url="https://github.company.com/api/v3",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
        )
        client = GitHubClient(config)

        url = client._build_diff_url("owner/repo", 456)

        # GitHub Enterprise: API URL https://github.company.com/api/v3
        # After removing /api/v3 and /api: https://github.company.com
        assert url == "https://github.company.com/owner/repo/pull/456.diff"

    def test_build_auth_headers(self, test_config: Config) -> None:
        """Test building authentication headers."""
        client = GitHubClient(test_config)

        headers = client._build_auth_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == "token ghp_test_token"
        assert headers["Accept"] == "text/plain"

    @pytest.mark.asyncio
    async def test_fetch_complete_diff_via_http_success(
        self, test_config: Config
    ) -> None:
        """Test successful HTTP diff fetching."""
        client = GitHubClient(test_config)

        # Mock diff content
        diff_content = """diff --git a/file.py b/file.py
index abc123..def456 100644
--- a/file.py
+++ b/file.py
@@ -1,1 +1,1 @@
-old
+new
"""

        # Mock aiohttp response
        with mock_httpx_client(diff_content):
            diffs = await client._fetch_and_parse_diff_with_prefiltering(
                "https://github.com/owner/repo/pull/1.diff",
                {"Authorization": "token ghp_test_token", "Accept": "text/plain"},
            )

        assert len(diffs) == 1
        assert diffs[0].file_path == "file.py"

    @pytest.mark.asyncio
    async def test_fetch_diff_http_non_200_response(self, test_config: Config) -> None:
        """Test HTTP diff fetching with non-200 response."""
        client = GitHubClient(test_config)

        # Mock failed response (404)
        with mock_httpx_client("", status=404):
            diffs = await client._fetch_and_parse_diff_with_prefiltering(
                "https://github.com/owner/repo/pull/1.diff",
                {"Authorization": "token ghp_test_token"},
            )

        # Should return empty list on non-200 status
        assert len(diffs) == 0

    @pytest.mark.asyncio
    async def test_fetch_complete_diff_via_http_failure(
        self, test_config: Config
    ) -> None:
        """Test HTTP diff fetching with failure (404 status)."""
        from tests.conftest import mock_httpx_client

        client = GitHubClient(test_config)

        # Mock failed response with 404 status
        with mock_httpx_client(diff_content="", status=404):
            diffs = await client._fetch_and_parse_diff_with_prefiltering(
                "https://github.com/owner/repo/pull/1.diff",
                {"Authorization": "token ghp_test_token", "Accept": "text/plain"},
            )

        assert len(diffs) == 0

    @pytest.mark.asyncio
    async def test_prefiltering_statistics(self, test_config: Config) -> None:
        """Test that pre-filtering generates correct statistics."""
        client = GitHubClient(test_config)

        # Mock diff with binary and excluded files
        diff_content = """diff --git a/image.png b/image.png
new file mode 100644
Binary files /dev/null and b/image.png differ
diff --git a/package-lock.json b/package-lock.json
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
                "https://github.com/owner/repo/pull/1.diff",
                {"Authorization": "token ghp_test_token", "Accept": "text/plain"},
            )

        # Only code.py should be included
        assert len(diffs) == 1
        assert diffs[0].file_path == "code.py"

    @pytest.mark.asyncio
    async def test_fetch_diff_reaches_max_files_during_streaming(
        self, test_config: Config
    ) -> None:
        """Test that streaming stops early when max_files is reached."""
        # Set very low max_files limit
        test_config.max_files = 1

        client = GitHubClient(test_config)

        # Mock diff with 3 files
        diff_content = """diff --git a/file1.py b/file1.py
index abc..def 100644
--- a/file1.py
+++ b/file1.py
@@ -1,1 +1,1 @@
-old1
+new1
diff --git a/file2.py b/file2.py
index ghi..jkl 100644
--- a/file2.py
+++ b/file2.py
@@ -1,1 +1,1 @@
-old2
+new2
diff --git a/file3.py b/file3.py
index mno..pqr 100644
--- a/file3.py
+++ b/file3.py
@@ -1,1 +1,1 @@
-old3
+new3
"""

        with mock_httpx_client(diff_content):
            diffs = await client._fetch_and_parse_diff_with_prefiltering(
                "https://github.com/owner/repo/pull/1.diff",
                {"Authorization": "token ghp_test_token"},
            )

        # Should stop at max_files=1
        assert len(diffs) == 1
        assert diffs[0].file_path == "file1.py"

    @pytest.mark.asyncio
    async def test_fetch_pull_request_diffs_uses_http_first(
        self, test_config: Config
    ) -> None:
        """Test that _fetch_pull_request_diffs tries HTTP method first."""
        client = GitHubClient(test_config)

        # Mock pull request
        mock_pr = MagicMock()
        mock_pr.base.repo.full_name = "owner/repo"
        mock_pr.number = 123

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

            diffs = await client._fetch_pull_request_diffs(mock_pr)

            assert len(diffs) == 1
            mock_http.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_pull_request_diffs_fallback_to_api(
        self, test_config: Config
    ) -> None:
        """Test fallback to API when HTTP fails."""
        client = GitHubClient(test_config)

        # Mock pull request
        mock_pr = MagicMock()
        mock_pr.base.repo.full_name = "owner/repo"
        mock_pr.number = 123

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
                "_fetch_pull_request_diffs_via_api",
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

                diffs = await client._fetch_pull_request_diffs(mock_pr)

                assert len(diffs) == 1
                mock_http.assert_called_once()
                mock_api.assert_called_once()
