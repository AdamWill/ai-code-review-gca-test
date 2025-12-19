"""GitHub API client for fetching pull request data."""

from __future__ import annotations

import asyncio
import time

import httpx
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
    Review,
    ReviewComment,
)
from ai_code_review.utils.diff_parser import FilteringStreamingDiffParser
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

    async def get_authenticated_username(self) -> str:
        """Get GitHub username with caching.

        Returns:
            GitHub username (login) of the authenticated user

        Raises:
            GitHubAPIError: If getting user fails
        """
        if self._authenticated_username is not None:
            return self._authenticated_username

        if self.config.dry_run:
            self._authenticated_username = "ai-code-review-bot-dry-run"
            return self._authenticated_username

        try:
            # Get authenticated user using thread pool for blocking call
            user = await asyncio.to_thread(self.github_client.get_user)
            self._authenticated_username = user.login
            logger.info(
                "Authenticated as GitHub user", username=self._authenticated_username
            )
            return self._authenticated_username

        except GithubException as e:
            raise GitHubAPIError(f"Failed to get authenticated user: {e}") from e

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

            # Get diffs, commits, and reviews
            diffs = await self._fetch_pull_request_diffs(pull_request)
            commits = await self._fetch_pull_request_commits(pull_request)
            reviews, comments = await self._fetch_pull_request_reviews_and_comments(
                pull_request
            )

            return PullRequestData(
                info=pr_info,
                diffs=diffs,
                commits=commits,
                reviews=reviews,
                comments=comments,
            )

        except GithubException as e:
            # GitHub library specific exceptions
            raise GitHubAPIError(f"Failed to fetch PR data: {e}") from e
        except Exception as e:
            # Catch any other unexpected errors (should be rare)
            raise GitHubAPIError(f"Unexpected error fetching PR data: {e}") from e

    def _build_diff_url(self, project_id: str, pr_number: int) -> str:
        """Build URL for complete diff download.

        Args:
            project_id: GitHub repository path (owner/repo)
            pr_number: Pull request number

        Returns:
            URL to download complete diff
        """
        base_url = self.config.get_effective_server_url()

        # Handle GitHub Enterprise vs GitHub.com
        # Check for exact github.com or api.github.com (not subdomains like github.company.com)
        is_github_com = (
            base_url.startswith("https://github.com/")
            or base_url.startswith("https://api.github.com/")
            or base_url == "https://github.com"
            or base_url == "https://api.github.com"
        )

        if is_github_com:
            # GitHub.com: use public URL
            return f"https://github.com/{project_id}/pull/{pr_number}.diff"
        else:
            # GitHub Enterprise: extract base domain from API URL
            # API URL format: https://github.company.com/api/v3
            api_base = base_url.replace("/api/v3", "").replace("/api", "")
            return f"{api_base}/{project_id}/pull/{pr_number}.diff"

    def _build_auth_headers(self) -> dict[str, str]:
        """Build authentication headers for HTTP requests.

        Returns:
            Dictionary with authentication headers
        """
        return {
            "Authorization": f"token {self.config.get_platform_token()}",
            "Accept": "text/plain",
        }

    async def _fetch_and_parse_diff_with_prefiltering(
        self, diff_url: str, headers: dict[str, str]
    ) -> list[PullRequestDiff]:
        """Fetch and parse diff with pre-filtering to minimize memory usage.

        This method downloads the diff in chunks and pre-filters files
        based on exclude patterns and binary detection, avoiding parsing
        content that will be discarded.

        Args:
            diff_url: URL to download diff from
            headers: HTTP headers for authentication

        Returns:
            List of PullRequestDiff objects for included files
        """
        diffs: list[PullRequestDiff] = []
        start_time = time.time()

        try:
            timeout = httpx.Timeout(self.config.diff_download_timeout)
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("GET", diff_url, headers=headers) as response:
                    if response.status_code != 200:
                        logger.warning(
                            "Failed to fetch complete diff via HTTP",
                            status=response.status_code,
                            url=diff_url,
                        )
                        return []

                    # Create parser with exclusion filter
                    parser = FilteringStreamingDiffParser(
                        should_exclude=self._should_exclude_file
                    )

                    # Use aiter_text for proper multi-byte character handling
                    async for chunk_text in response.aiter_text(chunk_size=16384):
                        # Parse chunk and get any complete file diffs
                        for diff in parser.feed(chunk_text):
                            diffs.append(diff)

                            # Stop early if we hit file limit
                            if len(diffs) >= self.config.max_files:
                                logger.info(
                                    "Reached max_files limit during streaming",
                                    max_files=self.config.max_files,
                                )
                                # Get stats before returning
                                stats = parser.get_statistics()
                                self._log_filtering_stats(
                                    stats, time.time() - start_time
                                )
                                return self._apply_content_limits(diffs)

                    # Flush any remaining content
                    for diff in parser.finalize():
                        diffs.append(diff)
                        if len(diffs) >= self.config.max_files:
                            break

                    # Log detailed statistics
                    stats = parser.get_statistics()
                    self._log_filtering_stats(stats, time.time() - start_time)

                    return self._apply_content_limits(diffs)

        except (TimeoutError, httpx.TimeoutException):
            logger.warning(
                "Timeout fetching complete diff via HTTP",
                url=diff_url,
                timeout=self.config.diff_download_timeout,
            )
            return []
        except Exception as e:
            logger.warning(
                "Error fetching complete diff via HTTP, will fallback to API",
                error=str(e),
                url=diff_url,
            )
            return []

    def _log_filtering_stats(
        self, stats: dict[str, int | float], processing_time: float
    ) -> None:
        """Log detailed filtering statistics.

        Args:
            stats: Statistics dictionary from parser
            processing_time: Time taken to process in seconds
        """
        logger.info(
            "Diff streaming with pre-filtering completed",
            total_files=stats["total_files"],
            included_files=stats["included_files"],
            filtered_files=stats["filtered_files"],
            binary_files=stats["binary_files"],
            mb_processed=round(stats.get("mb_processed", 0), 2),
            mb_skipped=round(stats.get("mb_skipped", 0), 2),
            filter_ratio=f"{stats.get('filter_ratio', 0) * 100:.1f}%",
            processing_time_sec=round(processing_time, 2),
        )

    async def _fetch_pull_request_diffs(
        self, pull_request: PullRequest
    ) -> list[PullRequestDiff]:
        """Fetch diffs for a pull request.

        Attempts to fetch complete diff via .diff URL first for maximum
        coverage (includes large files), with automatic fallback to API
        method if HTTP fetch fails.

        Args:
            pull_request: GitHub pull request object

        Returns:
            List of diffs for the pull request
        """
        # Extract owner/repo from PR
        project_id = pull_request.base.repo.full_name

        # Try HTTP .diff URL with streaming pre-filter (includes large files)
        try:
            diff_url = self._build_diff_url(project_id, pull_request.number)
            headers = self._build_auth_headers()

            diffs = await self._fetch_and_parse_diff_with_prefiltering(
                diff_url, headers
            )

            if diffs:
                logger.info(
                    "Successfully fetched diffs via HTTP .diff URL",
                    files=len(diffs),
                    method="http",
                )
                return diffs
        except Exception as e:
            logger.info(
                "HTTP diff fetch failed, falling back to API",
                error=str(e),
            )

        # Fallback to API method
        logger.info("Using API method for diff fetching", method="api")
        return await self._fetch_pull_request_diffs_via_api(pull_request)

    async def _fetch_pull_request_diffs_via_api(
        self, pull_request: PullRequest
    ) -> list[PullRequestDiff]:
        """Fetch diffs for a pull request via GitHub API.

        This is the original implementation, kept as a fallback method
        when HTTP .diff URL fetching fails.

        Args:
            pull_request: GitHub pull request object

        Returns:
            List of diffs from API
        """
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

    async def _fetch_pull_request_reviews_and_comments(
        self, pull_request: PullRequest
    ) -> tuple[list[Review], list[ReviewComment]]:
        """Fetch ALL reviews and comments (resolved and unresolved).

        Important: Fetches all comments, not just open/unresolved ones,
        to detect previously invalidated suggestions.

        Args:
            pull_request: GitHub PullRequest object

        Returns:
            Tuple of (reviews_list, all_comments)
        """

        def _fetch_all_sync() -> tuple[list[Review], list[ReviewComment]]:
            """Fetch and iterate over paginated lists in thread.

            Limits total comments fetched to max_comments_to_fetch to avoid
            performance issues on PRs with hundreds of comments.
            """
            from itertools import islice

            reviews_list_sync = []
            all_comments_sync = []
            max_to_fetch = self.config.max_comments_to_fetch
            comments_fetched = 0

            # Get recent reviews - iteration happens in thread
            reviews = pull_request.get_reviews()
            for review in islice(reviews, max_to_fetch):
                reviews_list_sync.append(
                    Review(
                        id=review.id,
                        author=review.user.login,
                        state=review.state,
                        body=review.body or "",
                        submitted_at=review.submitted_at.isoformat(),
                    )
                )

            # Get recent review comments (code-level) - iteration in thread
            review_comments = pull_request.get_review_comments()
            for comment in islice(review_comments, max_to_fetch - comments_fetched):
                # Skip comments from bots (GitHub Actions, etc.)
                if comment.user.type == "Bot":
                    continue

                all_comments_sync.append(
                    ReviewComment(
                        id=comment.id,
                        author=comment.user.login,
                        body=comment.body,
                        created_at=comment.created_at.isoformat(),
                        updated_at=comment.updated_at.isoformat()
                        if comment.updated_at
                        else None,
                        path=comment.path,
                        line=comment.line,
                        in_reply_to_id=comment.in_reply_to_id,
                        is_system=False,
                        # Note: GitHub doesn't expose resolved status directly
                    )
                )
                comments_fetched += 1
                if comments_fetched >= max_to_fetch:
                    break

            # Get recent issue comments (general PR comments) - iteration in thread
            if comments_fetched < max_to_fetch:
                issue_comments = pull_request.get_issue_comments()
                for issue_comment in islice(
                    issue_comments, max_to_fetch - comments_fetched
                ):
                    # Skip comments from bots (GitHub Actions, etc.)
                    if issue_comment.user.type == "Bot":
                        continue

                    all_comments_sync.append(
                        ReviewComment(
                            id=issue_comment.id,
                            author=issue_comment.user.login,
                            body=issue_comment.body,
                            created_at=issue_comment.created_at.isoformat(),
                            updated_at=issue_comment.updated_at.isoformat()
                            if issue_comment.updated_at
                            else None,
                            is_system=False,
                        )
                    )
                    comments_fetched += 1
                    if comments_fetched >= max_to_fetch:
                        break

            return reviews_list_sync, all_comments_sync

        try:
            # Run all blocking operations (including pagination) in thread
            reviews_list, all_comments = await asyncio.to_thread(_fetch_all_sync)

            logger.info(
                "Fetched PR reviews and comments",
                reviews=len(reviews_list),
                comments=len(all_comments),
                max_fetched=self.config.max_comments_to_fetch,
            )

            return reviews_list, all_comments

        except GithubException as e:
            logger.warning("Failed to fetch reviews/comments", error=str(e))
            return [], []

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

        mock_reviews = [
            Review(
                id=1,
                author="ai-code-review-bot-dry-run",
                state="COMMENTED",
                body="Previous AI review (mock)",
                submitted_at="2024-01-01T10:00:00Z",
            )
        ]

        mock_comments = [
            ReviewComment(
                id=1,
                author="mock_user",
                body="Thanks for the review! I've addressed the concerns about error handling.",
                created_at="2024-01-01T11:00:00Z",
                in_reply_to_id=1,
            )
        ]

        return PullRequestData(
            info=mock_info,
            diffs=mock_diffs,
            commits=mock_commits,
            reviews=mock_reviews,
            comments=mock_comments,
        )

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
