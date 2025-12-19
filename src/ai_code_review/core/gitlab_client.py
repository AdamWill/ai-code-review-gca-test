"""GitLab API client for fetching merge request data."""

from __future__ import annotations

import asyncio
import ssl
import time
from datetime import datetime
from typing import Any

import gitlab
import httpx
import structlog
from gitlab.v4.objects import Project, ProjectMergeRequest

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
from ai_code_review.utils.platform_exceptions import GitLabAPIError
from ai_code_review.utils.ssl_utils import SSLCertificateManager

logger = structlog.get_logger(__name__)


class GitLabClient(BasePlatformClient):
    """Client for GitLab API operations."""

    def __init__(self, config: Config) -> None:
        """Initialize GitLab client."""
        super().__init__(config)
        self._gitlab_client: gitlab.Gitlab | None = None
        self._ssl_manager = SSLCertificateManager(config.ssl_cert_cache_dir)
        self._ssl_cert_path: str | None = None
        self._ssl_initialized: bool = False

    async def _initialize_ssl_certificate(self) -> None:
        """Initialize SSL certificate, downloading if needed."""
        if self._ssl_initialized:
            return

        try:
            self._ssl_cert_path = await self._ssl_manager.get_certificate_path(
                cert_url=self.config.ssl_cert_url,
                cert_path=self.config.ssl_cert_path,
            )
            if self._ssl_cert_path:
                logger.info("SSL certificate initialized", path=self._ssl_cert_path)
        except Exception as e:
            logger.warning(
                "Failed to setup SSL certificate, falling back to ssl_verify setting",
                error=str(e),
                ssl_verify=self.config.ssl_verify,
            )
            self._ssl_cert_path = None

        self._ssl_initialized = True

    async def get_authenticated_username(self) -> str:
        """Get GitLab username with caching.

        Returns:
            GitLab username of the authenticated user

        Raises:
            GitLabAPIError: If getting user fails
        """
        if self._authenticated_username is not None:
            return self._authenticated_username

        # Initialize SSL before making API calls
        await self._initialize_ssl_certificate()

        if self.config.dry_run:
            self._authenticated_username = "ai-code-review-bot-dry-run"
            return self._authenticated_username

        try:
            # Define sync function to run in thread
            def _get_user_sync() -> str:
                gl_client = self.gitlab_client
                gl_client.auth()
                current_user = gl_client.user
                if current_user is None:
                    raise GitLabAPIError(
                        "Failed to get authenticated user: user is None", None
                    )
                # CurrentUser has username attribute
                username: str = current_user.username
                return username

            # Run blocking calls in separate thread
            self._authenticated_username = await asyncio.to_thread(_get_user_sync)
            logger.info(
                "Authenticated as GitLab user", username=self._authenticated_username
            )
            return self._authenticated_username

        except gitlab.GitlabError as e:
            raise GitLabAPIError(
                f"Failed to get authenticated user: {e}",
                getattr(e, "response_code", None),
            ) from e

    @property
    def gitlab_client(self) -> gitlab.Gitlab:
        """Get or create GitLab client instance.

        Note: If ssl_cert_url is configured, ensure _initialize_ssl_certificate()
        is called first in your async method to set up SSL properly.
        """
        if self._gitlab_client is None:
            # Defensive check: warn if SSL URL is configured but not initialized
            if self.config.ssl_cert_url and not self._ssl_initialized:
                logger.warning(
                    "SSL certificate URL configured but not initialized. "
                    "Call _initialize_ssl_certificate() first in async methods.",
                    ssl_cert_url=self.config.ssl_cert_url,
                )

            # Configure SSL verification
            ssl_verify: bool | str = self.config.ssl_verify

            # Handle ssl_cert_path immediately (synchronous)
            if self.config.ssl_cert_path:
                ssl_verify = self.config.ssl_cert_path
                logger.info(
                    "Using SSL certificate path", path=self.config.ssl_cert_path
                )
            # Use cached certificate path from async download if available
            elif self._ssl_cert_path:
                ssl_verify = self._ssl_cert_path

            self._gitlab_client = gitlab.Gitlab(
                url=self.config.get_effective_server_url(),
                private_token=self.config.get_platform_token(),
                ssl_verify=ssl_verify,
            )
        return self._gitlab_client

    async def get_pull_request_data(
        self, project_id: str, pr_number: int
    ) -> PullRequestData:
        """Fetch complete merge request data including diffs.

        Args:
            project_id: GitLab project ID or path (e.g., 'group/project')
            pr_number: Merge request IID

        Returns:
            Complete merge request data with diffs

        Raises:
            GitLabAPIError: If API call fails
        """
        # Initialize SSL certificate before making API calls
        await self._initialize_ssl_certificate()
        if self.config.dry_run:
            # Return mock data for dry run
            return self._create_mock_pr_data(project_id, pr_number)

        try:
            # Get project
            project: Project = self.gitlab_client.projects.get(project_id)

            # Get merge request
            merge_request: ProjectMergeRequest = project.mergerequests.get(pr_number)

            # Create PR info (mapping GitLab MR to platform-agnostic model)
            pr_info = PullRequestInfo(
                id=merge_request.id,
                number=merge_request.iid,  # GitLab uses iid as the "number"
                title=merge_request.title,
                description=merge_request.description,
                source_branch=merge_request.source_branch,
                target_branch=merge_request.target_branch,
                author=merge_request.author["username"],
                state=merge_request.state,
                web_url=merge_request.web_url,
                draft=getattr(merge_request, "draft", False),  # GitLab draft status
            )

            # Get diffs, commits, and discussions
            diffs = await self._fetch_merge_request_diffs(merge_request)
            commits = await self._fetch_merge_request_commits(merge_request)
            reviews, comments = await self._fetch_merge_request_discussions(
                merge_request
            )

            return PullRequestData(
                info=pr_info,
                diffs=diffs,
                commits=commits,
                reviews=reviews,
                comments=comments,
            )

        except gitlab.GitlabError as e:
            raise GitLabAPIError(
                f"Failed to fetch MR data: {e}", getattr(e, "response_code", None)
            ) from e
        except Exception as e:
            raise GitLabAPIError(f"Unexpected error: {e}") from e

    def _build_auth_headers(self) -> dict[str, str]:
        """Build authentication headers for HTTP requests.

        Returns:
            Dictionary with authentication headers
        """
        return {
            "PRIVATE-TOKEN": self.config.get_platform_token(),
        }

    def _get_ssl_context(self) -> ssl.SSLContext | bool:
        """Get SSL context for HTTP requests.

        Returns:
            SSL context if certificate is configured, bool otherwise
        """
        ssl_verify: bool | str = self.config.ssl_verify

        # Use cached certificate path from async download if available
        if self._ssl_cert_path:
            ssl_verify = self._ssl_cert_path
        elif self.config.ssl_cert_path:
            ssl_verify = self.config.ssl_cert_path

        # Create SSL context
        if isinstance(ssl_verify, str):
            ssl_context = ssl.create_default_context()
            ssl_context.load_verify_locations(ssl_verify)
            return ssl_context
        elif not ssl_verify:
            return False
        else:
            return True

    async def _fetch_and_parse_diff_with_prefiltering(
        self,
        diff_url: str,
        headers: dict[str, str],
        ssl_context: ssl.SSLContext | bool,
    ) -> list[PullRequestDiff]:
        """Fetch and parse diff with pre-filtering to minimize memory usage.

        This method downloads the diff in chunks and pre-filters files
        based on exclude patterns and binary detection, avoiding parsing
        content that will be discarded.

        Args:
            diff_url: URL to download diff from
            headers: HTTP headers for authentication
            ssl_context: SSL context for HTTPS

        Returns:
            List of PullRequestDiff objects for included files
        """
        diffs: list[PullRequestDiff] = []
        start_time = time.time()

        try:
            timeout = httpx.Timeout(self.config.diff_download_timeout)
            async with httpx.AsyncClient(verify=ssl_context, timeout=timeout) as client:
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

                    # Process in 16KB chunks using aiter_text for proper multi-byte handling
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

    async def _fetch_merge_request_diffs(
        self, merge_request: ProjectMergeRequest
    ) -> list[PullRequestDiff]:
        """Fetch diffs for a merge request.

        Attempts to fetch complete diff via .diff URL first for maximum
        coverage (includes large files), with automatic fallback to API
        method if HTTP fetch fails.

        Args:
            merge_request: GitLab merge request object

        Returns:
            List of diffs for the merge request
        """
        # Try HTTP .diff URL with streaming pre-filter (includes large files)
        try:
            # Use web_url from MR object to avoid blocking API call
            diff_url = f"{merge_request.web_url}.diff"
            headers = self._build_auth_headers()
            ssl_context = self._get_ssl_context()

            diffs = await self._fetch_and_parse_diff_with_prefiltering(
                diff_url, headers, ssl_context
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
        return await self._fetch_merge_request_diffs_via_api(merge_request)

    async def _fetch_merge_request_diffs_via_api(
        self, merge_request: ProjectMergeRequest
    ) -> list[PullRequestDiff]:
        """Fetch diffs for a merge request via GitLab API.

        This is the original implementation, kept as a fallback method
        when HTTP .diff URL fetching fails.

        Args:
            merge_request: GitLab merge request object

        Returns:
            List of diffs from API
        """
        diffs: list[PullRequestDiff] = []
        excluded_files: list[str] = []
        excluded_chars = 0

        try:
            # Get changes from the MR
            changes_response = merge_request.changes()

            # Handle both dict and Response types
            if hasattr(changes_response, "get"):
                changes_data = changes_response
            else:
                # If it's a Response object, convert to dict
                changes_data = (
                    changes_response.json() if hasattr(changes_response, "json") else {}
                )

            # Track files skipped due to missing diff content (common for large lockfiles)
            skipped_no_diff = []

            for change in changes_data.get("changes", []):
                file_path = change["new_path"] or change["old_path"]
                diff_content = change.get("diff", "")

                # Skip binary files or files without diffs
                if not diff_content:
                    skipped_no_diff.append(file_path)
                    continue

                # Check if file should be excluded from AI review
                if self._should_exclude_file(file_path):
                    excluded_files.append(file_path)
                    excluded_chars += len(diff_content)
                    continue  # Skip excluded files

                # Create diff object
                diff = PullRequestDiff(
                    file_path=file_path,
                    new_file=change["new_file"],
                    renamed_file=change["renamed_file"],
                    deleted_file=change["deleted_file"],
                    diff=change["diff"],
                )

                diffs.append(diff)

                # Check limits
                if len(diffs) >= self.config.max_files:
                    break

            # Log filtering and skipping statistics
            logger = structlog.get_logger()

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
                    "Files skipped - no diff content from GitLab API",
                    skipped_files=len(skipped_no_diff),
                    reason="GitLab omits diff content for large files (e.g., lockfiles)",
                    examples=skipped_no_diff[:3],  # Show first 3 examples
                )

            return self._apply_content_limits(diffs)

        except gitlab.GitlabError as e:
            raise GitLabAPIError(
                f"Failed to fetch diffs: {e}", getattr(e, "response_code", None)
            ) from e

    async def _fetch_merge_request_commits(
        self, merge_request: ProjectMergeRequest
    ) -> list[PullRequestCommit]:
        """Fetch commits for a merge request."""
        commits: list[PullRequestCommit] = []

        try:
            # Get commits from the MR
            mr_commits = merge_request.commits()

            for commit_data in mr_commits:
                commit = PullRequestCommit(
                    id=commit_data.id,
                    title=commit_data.title,
                    message=commit_data.message,
                    author_name=commit_data.author_name,
                    author_email=commit_data.author_email,
                    committed_date=commit_data.committed_date,
                    short_id=commit_data.short_id,
                )
                commits.append(commit)

            return commits

        except Exception as e:
            raise GitLabAPIError(
                f"Failed to fetch commits: {e}", getattr(e, "response_code", None)
            ) from e

    async def _fetch_merge_request_discussions(
        self, merge_request: ProjectMergeRequest
    ) -> tuple[list[Review], list[ReviewComment]]:
        """Fetch ALL discussions and notes for a merge request.

        GitLab uses discussions (threads) which contain notes (comments).
        We map these to Review/ReviewComment for platform consistency.

        Important: Fetches all discussions, including resolved ones,
        to detect previously invalidated suggestions.

        Args:
            merge_request: GitLab ProjectMergeRequest object

        Returns:
            Tuple of (reviews_list, all_comments)
        """

        def _fetch_discussions_sync() -> tuple[int, list[ReviewComment]]:
            """Run blocking GitLab API calls in thread.

            Fetches up to max_comments_to_fetch most recent discussions to avoid
            performance issues on PRs with hundreds of comments.
            """
            all_comments_sync = []
            # Limit discussions to fetch (GitLab orders by updated_at desc by default)
            max_discussions = self.config.max_comments_to_fetch
            discussions = merge_request.discussions.list(
                per_page=max_discussions, page=1
            )

            for discussion in discussions:
                notes = discussion.attributes.get("notes", [])

                for note in notes:
                    # Skip system-generated notes (e.g., "changed title", "merged", etc.)
                    if note.get("system", False):
                        continue

                    comment_obj = ReviewComment(
                        id=note["id"],
                        author=note["author"][
                            "username"
                        ],  # Use username for consistency
                        body=note["body"],
                        created_at=note["created_at"],
                        updated_at=note.get("updated_at"),
                        is_system=False,  # Already filtered out
                        resolved=note.get("resolved", False),
                    )

                    # Add position information if it's a diff note
                    if note.get("position"):
                        pos = note["position"]
                        comment_obj.path = pos.get("new_path") or pos.get("old_path")
                        comment_obj.line = pos.get("new_line") or pos.get("old_line")

                    all_comments_sync.append(comment_obj)

            return len(discussions), all_comments_sync

        try:
            # Run blocking calls in separate thread
            discussions_count, all_comments = await asyncio.to_thread(
                _fetch_discussions_sync
            )

            logger.info(
                "Fetched MR discussions",
                discussions=discussions_count,
                comments=len(all_comments),
                max_fetched=self.config.max_comments_to_fetch,
            )

            # GitLab doesn't have explicit "reviews", return empty list for consistency
            reviews_list: list[Review] = []

            return reviews_list, all_comments

        except gitlab.GitlabError as e:
            logger.warning("Failed to fetch discussions", error=str(e))
            return [], []

    def _create_mock_pr_data(self, project_id: str, pr_number: int) -> PullRequestData:
        """Create mock merge request data for dry run mode."""
        mock_info = PullRequestInfo(
            id=12345,
            number=pr_number,
            title=f"Mock MR {pr_number} for project {project_id}",
            description="Mock merge request for testing",
            source_branch="feature/mock-branch",
            target_branch="main",
            author="mock_user",
            state="opened",
            web_url=f"{self.config.gitlab_url}/mock/project/-/merge_requests/{pr_number}",
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

        mock_reviews: list[Review] = []

        mock_comments = [
            ReviewComment(
                id=1,
                author="ai-code-review-bot-dry-run",
                body="Previous AI review comment (mock)",
                created_at="2024-01-01T10:00:00Z",
                resolved=False,
            ),
            ReviewComment(
                id=2,
                author="mock_user",
                body="Thanks for the review! I've addressed the concerns about error handling.",
                created_at="2024-01-01T11:00:00Z",
                resolved=True,
            ),
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
        """Post review as a discussion thread on the merge request.

        Args:
            project_id: GitLab project ID or path (e.g., 'group/project')
            pr_number: Merge request IID
            review_content: The markdown content of the review to post

        Returns:
            Response containing thread information

        Raises:
            GitLabAPIError: If posting fails
        """
        # Initialize SSL certificate before making API calls
        await self._initialize_ssl_certificate()
        if self.config.dry_run:
            # Return mock data for dry run
            return self._create_mock_thread_data(project_id, pr_number, review_content)

        try:
            # Get project
            project: Project = self.gitlab_client.projects.get(project_id)

            # Get merge request
            merge_request: ProjectMergeRequest = project.mergerequests.get(pr_number)

            # Resolve previous AI review threads
            await self._resolve_previous_ai_threads(project, merge_request)

            # Create clean thread title (GitLab already shows timestamp)
            thread_title = "🤖 AI Code Review"

            # Create thread with just title (short message that stays visible when resolved)
            thread_starter = f"# {thread_title}\n\n✅ **AI analysis complete** - Review details below"

            # Create the discussion thread on the MR
            discussion = merge_request.discussions.create({"body": thread_starter})

            # Add the full review content as a reply within the thread
            # This will be collapsed when the thread is resolved
            discussion.notes.create({"body": review_content})

            # Return thread information
            return PostReviewResponse(
                id=str(discussion.id),
                url=f"{self.config.gitlab_url}/-/merge_requests/{pr_number}#note_{discussion.id}",
                created_at=getattr(
                    discussion, "created_at", datetime.now().isoformat()
                ),
                author="AI Code Review",
            )

        except gitlab.GitlabError as e:
            raise GitLabAPIError(
                f"Failed to post review thread to GitLab: {e}",
                getattr(e, "response_code", None),
            ) from e
        except Exception as e:
            raise GitLabAPIError(f"Unexpected error posting review thread: {e}") from e

    def _create_mock_thread_data(
        self, project_id: str, pr_number: int, review_content: str
    ) -> PostReviewResponse:
        """Create mock thread data for dry run mode."""
        return PostReviewResponse(
            id="mock_thread_123",
            url=f"{self.config.gitlab_url}/mock/project/-/merge_requests/{pr_number}#note_mock_123",
            created_at=datetime.now().isoformat(),
            author="AI Code Review (DRY RUN)",
            content_preview="🤖 AI Code Review - ✅ AI analysis complete (DRY RUN)",
        )

    async def _resolve_previous_ai_threads(
        self, project: Project, merge_request: ProjectMergeRequest
    ) -> None:
        """Find and resolve previous AI review threads to keep the MR clean.

        Args:
            project: GitLab project object
            merge_request: GitLab merge request object
        """
        logger = structlog.get_logger()

        try:
            # Get all discussions for this MR
            discussions = merge_request.discussions.list(all=True)

            # Find discussions created by AI review bot
            ai_threads = []
            for discussion in discussions:
                # Check if this is an AI review thread
                notes = getattr(discussion, "attributes", {}).get("notes", [])
                if notes and self._is_ai_review_thread(notes[0]):
                    ai_threads.append(discussion)

            # Resolve previous AI threads
            for thread in ai_threads:
                try:
                    # Mark thread as resolved
                    thread.resolved = True
                    thread.save()

                    logger.info(
                        "Resolved previous AI review thread",
                        thread_id=thread.id,
                        project_id=project.id,
                        mr_iid=merge_request.iid,
                    )
                except Exception as e:
                    # Don't fail the whole operation if we can't resolve a thread
                    logger.warning(
                        "Failed to resolve previous AI thread",
                        thread_id=thread.id,
                        error=str(e),
                    )

        except Exception as e:
            # Don't fail the whole review posting if thread resolution fails
            logger.warning(
                "Failed to resolve previous AI threads",
                error=str(e),
                project_id=project.id,
                mr_iid=merge_request.iid,
            )

    def _is_ai_review_thread(self, note_data: dict[str, Any]) -> bool:
        """Check if a thread note was created by AI Code Review.

        Args:
            note_data: Dictionary containing note information

        Returns:
            True if this appears to be an AI review thread
        """
        body = note_data.get("body", "")

        # Look for AI review markers in the thread body
        ai_markers = [
            "🤖 AI Code Review",
            "# AI Code Review",
            "## AI Code Review",
            "AI-powered code analysis",
            "<!-- AI Code Review Bot -->",
        ]

        return any(marker in body for marker in ai_markers)

    def get_platform_name(self) -> str:
        """Get the name of the platform."""
        return "gitlab"

    def format_project_url(self, project_id: str) -> str:
        """Format the project URL for GitLab."""
        return f"{self.config.gitlab_url}/{project_id}"
