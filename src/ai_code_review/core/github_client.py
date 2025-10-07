"""GitHub API client for fetching pull request data."""

from __future__ import annotations

import asyncio

import structlog
from github import Auth, Github, GithubException
from github.PullRequest import PullRequest
from github.Repository import Repository

from ai_code_review.core.base_platform_client import BasePlatformClient
from ai_code_review.models.config import Config
from ai_code_review.models.platform import (
    PostReviewResponse,
    PullRequestCommit,
    PullRequestData,
    PullRequestDiff,
    PullRequestInfo,
)
from ai_code_review.utils.platform_exceptions import GitHubAPIError

logger = structlog.get_logger(__name__)


class GitHubClient(BasePlatformClient):
    """Client for GitHub API operations."""

    def __init__(self, config: Config) -> None:
        """Initialize GitHub client."""
        super().__init__(config)
        self._github_client: Github | None = None

    @property
    def github_client(self) -> Github:
        """Get or create GitHub client instance."""
        if self._github_client is None:
            self._github_client = Github(
                auth=Auth.Token(self.config.get_platform_token()),
                base_url=self.config.get_effective_server_url(),
            )
        return self._github_client

    async def get_pull_request_data(
        self, project_id: str, pr_number: int
    ) -> PullRequestData:
        """Fetch complete pull request data including diffs.

        Args:
            project_id: GitHub repository path (e.g., 'owner/repo')
            pr_number: Pull request number

        Returns:
            Complete pull request data with diffs

        Raises:
            GitHubAPIError: If API call fails
        """
        if self.config.dry_run:
            # Return mock data for dry run
            return self._create_mock_pr_data(project_id, pr_number)

        try:
            # Get repository using thread pool for blocking call
            repo: Repository = await asyncio.to_thread(
                self.github_client.get_repo, project_id
            )

            # Get pull request using thread pool for blocking call
            pull_request: PullRequest = await asyncio.to_thread(
                repo.get_pull, pr_number
            )

            # Create PR info (mapping GitHub PR to platform-agnostic model)
            pr_info = PullRequestInfo(
                id=pull_request.id,
                number=pull_request.number,
                title=pull_request.title,
                description=pull_request.body,
                source_branch=pull_request.head.ref,
                target_branch=pull_request.base.ref,
                author=pull_request.user.login,
                state=pull_request.state,
                web_url=pull_request.html_url,
                draft=getattr(pull_request, "draft", False),  # GitHub draft status
            )

            # Get diffs and commits
            diffs = await self._fetch_pull_request_diffs(pull_request)
            commits = await self._fetch_pull_request_commits(pull_request)

            return PullRequestData(info=pr_info, diffs=diffs, commits=commits)

        except GithubException as e:
            # GitHub library specific exceptions
            raise GitHubAPIError(f"Failed to fetch PR data: {e}") from e
        except Exception as e:
            # Catch any other unexpected errors (should be rare)
            raise GitHubAPIError(f"Unexpected error fetching PR data: {e}") from e

    async def _fetch_pull_request_diffs(
        self, pull_request: PullRequest
    ) -> list[PullRequestDiff]:
        """Fetch diffs for a pull request."""
        diffs: list[PullRequestDiff] = []
        excluded_files: list[str] = []
        excluded_chars = 0

        try:
            # Get files from the PR using thread pool for blocking call
            files = await asyncio.to_thread(pull_request.get_files)

            # Track files skipped due to missing patch content
            skipped_no_diff = []

            for file in files:
                file_path = file.filename
                patch_content = file.patch or ""

                # Skip binary files or files without patches
                if not patch_content:
                    skipped_no_diff.append(file_path)
                    continue

                # Check if file should be excluded from AI review
                if self._should_exclude_file(file_path):
                    excluded_files.append(file_path)
                    excluded_chars += len(patch_content)
                    continue  # Skip excluded files

                # Create diff object
                diff = PullRequestDiff(
                    file_path=file_path,
                    new_file=file.status == "added",
                    renamed_file=file.status == "renamed",
                    deleted_file=file.status == "removed",
                    diff=patch_content,
                )

                diffs.append(diff)

                # Check limits
                if len(diffs) >= self.config.max_files:
                    break

            # Log filtering and skipping statistics
            if excluded_files:
                logger.info(
                    "Files excluded from AI review",
                    excluded_files=len(excluded_files),
                    excluded_chars=excluded_chars,
                    included_files=len(diffs),
                    examples=excluded_files[:3],  # Show first 3 examples
                )

            if skipped_no_diff:
                logger.info(
                    "Files skipped - no diff content from GitHub API",
                    skipped_files=len(skipped_no_diff),
                    reason="GitHub omits patch content for large files (e.g., binary files)",
                    examples=skipped_no_diff[:3],  # Show first 3 examples
                )

            return self._apply_content_limits(diffs)

        except GithubException as e:
            raise GitHubAPIError(f"Failed to fetch diffs: {e}") from e
        except Exception as e:
            # Catch any other unexpected errors (should be rare)
            raise GitHubAPIError(f"Unexpected error fetching diffs: {e}") from e

    async def _fetch_pull_request_commits(
        self, pull_request: PullRequest
    ) -> list[PullRequestCommit]:
        """Fetch commits for a pull request."""
        commits: list[PullRequestCommit] = []

        try:
            # Get commits from the PR using thread pool for blocking call
            pr_commits = await asyncio.to_thread(pull_request.get_commits)

            for commit_data in pr_commits:
                commit = PullRequestCommit(
                    id=commit_data.sha,
                    title=commit_data.commit.message.split("\n")[
                        0
                    ],  # First line as title
                    message=commit_data.commit.message,
                    author_name=commit_data.commit.author.name or "Unknown",
                    author_email=commit_data.commit.author.email
                    or "unknown@example.com",
                    committed_date=commit_data.commit.author.date.isoformat(),
                    short_id=commit_data.sha[:7],
                )
                commits.append(commit)

            return commits

        except GithubException as e:
            raise GitHubAPIError(f"Failed to fetch commits: {e}") from e
        except Exception as e:
            # Catch any other unexpected errors (should be rare)
            raise GitHubAPIError(f"Unexpected error fetching commits: {e}") from e

    def _create_mock_pr_data(self, project_id: str, pr_number: int) -> PullRequestData:
        """Create mock pull request data for dry run mode."""
        mock_info = PullRequestInfo(
            id=12345,
            number=pr_number,
            title=f"Mock PR {pr_number} for project {project_id}",
            description="Mock pull request for testing",
            source_branch="feature/mock-branch",
            target_branch="main",
            author="mock_user",
            state="open",
            web_url=f"https://github.com/{project_id}/pull/{pr_number}",
        )

        mock_diffs = [
            PullRequestDiff(
                file_path="src/mock_file.py",
                new_file=False,
                diff="@@ -1,3 +1,3 @@\n def mock_function():\n-    return 'old'\n+    return 'new'",
            )
        ]

        mock_commits = [
            PullRequestCommit(
                id="abc123456789",
                title="Add world greeting feature",
                message="Add world greeting feature\n\nImplements the requested greeting functionality to improve user experience.",
                author_name="Mock Author",
                author_email="author@example.com",
                committed_date="2024-01-01T12:00:00Z",
                short_id="abc1234",
            )
        ]

        return PullRequestData(info=mock_info, diffs=mock_diffs, commits=mock_commits)

    async def post_review(
        self, project_id: str, pr_number: int, review_content: str
    ) -> PostReviewResponse:
        """Post review as a comment on the pull request.

        Args:
            project_id: GitHub repository path (e.g., 'owner/repo')
            pr_number: Pull request number
            review_content: The markdown content of the review to post

        Returns:
            Response containing comment information

        Raises:
            GitHubAPIError: If posting fails
        """
        if self.config.dry_run:
            # Return mock data for dry run
            return self._create_mock_note_data(project_id, pr_number, review_content)

        try:
            # Get repository using thread pool for blocking call
            repo: Repository = await asyncio.to_thread(
                self.github_client.get_repo, project_id
            )

            # Get pull request using thread pool for blocking call
            pull_request: PullRequest = await asyncio.to_thread(
                repo.get_pull, pr_number
            )

            # Create the comment on the PR using thread pool for blocking call
            comment = await asyncio.to_thread(
                pull_request.create_issue_comment, review_content
            )

            # Return comment information
            return PostReviewResponse(
                id=str(comment.id),
                url=comment.html_url,
                created_at=comment.created_at.isoformat(),
                author=comment.user.login,
            )

        except GithubException as e:
            raise GitHubAPIError(f"Failed to post review to GitHub: {e}") from e
        except Exception as e:
            # Catch any other unexpected errors (should be rare)
            raise GitHubAPIError(f"Unexpected error posting review: {e}") from e

    def _create_mock_note_data(
        self, project_id: str, pr_number: int, review_content: str
    ) -> PostReviewResponse:
        """Create mock note data for dry run mode."""
        return PostReviewResponse(
            id="mock_comment_123",
            url=f"https://github.com/{project_id}/pull/{pr_number}#issuecomment-mock_123",
            created_at="2024-01-01T12:00:00Z",
            author="AI Code Review (DRY RUN)",
            content_preview=review_content[:100] + "..."
            if len(review_content) > 100
            else review_content,
        )

    def get_platform_name(self) -> str:
        """Get the name of the platform."""
        return "github"

    def format_project_url(self, project_id: str) -> str:
        """Format the project URL for GitHub."""
        return f"https://github.com/{project_id}"
