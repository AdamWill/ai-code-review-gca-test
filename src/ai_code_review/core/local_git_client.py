"""Local Git client for analyzing local repository changes."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import structlog
from git import GitCommandError, InvalidGitRepositoryError, Repo

from ai_code_review.core.base_platform_client import BasePlatformClient
from ai_code_review.models.config import Config
from ai_code_review.models.platform import (
    PostReviewResponse,
    PullRequestCommit,
    PullRequestData,
    PullRequestDiff,
    PullRequestInfo,
)
from ai_code_review.utils.diff_parser import BINARY_EXTENSIONS
from ai_code_review.utils.platform_exceptions import GitLocalError

logger = structlog.get_logger(__name__)


class LocalGitClient(BasePlatformClient):
    """Client for local git repository operations."""

    def __init__(self, config: Config) -> None:
        """Initialize local git client."""
        super().__init__(config)
        self._repo: Repo | None = None
        self._target_branch: str = "main"  # Default, can be configured

    @property
    def repo(self) -> Repo:
        """Get or initialize Git repository."""
        if self._repo is None:
            try:
                # Try to find the repository root from current directory
                current_path = Path.cwd()
                self._repo = Repo(current_path, search_parent_directories=True)
                logger.debug(
                    "Initialized git repository",
                    repo_path=self._repo.working_dir,
                    current_dir=str(current_path),
                )
            except InvalidGitRepositoryError as e:
                raise GitLocalError(
                    "Not in a git repository. Please run from within a git repository."
                ) from e
        return self._repo

    def set_target_branch(self, target_branch: str) -> None:
        """Set the target branch for comparison."""
        self._target_branch = target_branch

    async def get_authenticated_username(self) -> str:
        """Get Git username for local mode.

        Returns:
            Git config user.name or 'local-user' as fallback

        Raises:
            GitLocalError: If git operations fail
        """
        if self._authenticated_username is not None:
            return self._authenticated_username

        try:
            # Get username from git config
            username = await self._get_current_user()
            self._authenticated_username = username
            logger.info("Authenticated as local Git user", username=username)
            return self._authenticated_username

        except Exception as e:
            # Fallback to generic username
            logger.warning("Failed to get Git user, using fallback", error=str(e))
            self._authenticated_username = "local-user"
            return self._authenticated_username

    async def get_pull_request_data(
        self, project_id: str, pr_number: int
    ) -> PullRequestData:
        """Fetch local git changes as if they were a pull request.

        Args:
            project_id: Ignored for local mode (can be "local")
            pr_number: Ignored for local mode (can be 0)

        Returns:
            Complete pull request data with local diffs and commits

        Raises:
            GitLocalError: If git operations fail
        """
        if self.config.dry_run:
            # Return mock data for dry run
            return self._create_mock_pr_data(project_id, pr_number)

        try:
            # Get current branch
            current_branch = await self._get_current_branch()

            # Get merge base with target branch
            merge_base = await self._get_merge_base()

            # Create PR info simulating local changes
            pr_info = PullRequestInfo(
                id=0,  # Not applicable for local
                number=0,  # Not applicable for local
                title=f"Local changes on {current_branch}",
                description=f"Local code review comparing {current_branch} against {self._target_branch}",
                source_branch=current_branch,
                target_branch=self._target_branch,
                author=await self._get_current_user(),
                state="local",
                web_url=f"file://{Path(self.repo.working_dir)}",
            )

            # Get diffs and commits
            diffs = await self._get_local_diffs(merge_base)
            commits = await self._get_local_commits(merge_base)

            return PullRequestData(info=pr_info, diffs=diffs, commits=commits)

        except GitCommandError as e:
            raise GitLocalError(f"Git command failed: {e}") from e
        except Exception as e:
            raise GitLocalError(
                f"Unexpected error accessing local repository: {e}"
            ) from e

    async def _get_current_branch(self) -> str:
        """Get the current branch name."""
        try:
            return await asyncio.to_thread(lambda: self.repo.active_branch.name)
        except (TypeError, GitCommandError) as e:
            # Fallback for detached HEAD
            logger.debug("Detached HEAD detected, using commit hash", error=str(e))
            return await asyncio.to_thread(lambda: self.repo.head.commit.hexsha[:8])
        except Exception as e:
            raise GitLocalError(f"Failed to get current branch: {e}") from e

    async def _get_merge_base(self) -> str:
        """Get the merge base between current branch and target branch."""
        try:
            # Check if local target branch is out of date with remote
            await self._check_target_branch_status()

            # Try with origin/target_branch first
            target_ref = f"origin/{self._target_branch}"
            if target_ref in [ref.name for ref in self.repo.references]:
                merge_base = await asyncio.to_thread(
                    self.repo.merge_base, self.repo.head.commit, target_ref
                )
            else:
                # Fallback to local target branch
                merge_base = await asyncio.to_thread(
                    self.repo.merge_base, self.repo.head.commit, self._target_branch
                )

            if merge_base:
                return merge_base[0].hexsha
            else:
                # No common ancestor, use target branch HEAD
                logger.warning(f"No merge base found, using {self._target_branch} HEAD")
                target_commit = self.repo.commit(self._target_branch)
                return target_commit.hexsha

        except Exception as e:
            raise GitLocalError(
                f"Could not find merge base with {self._target_branch}. "
                f"Make sure the target branch exists locally or as origin/{self._target_branch}"
            ) from e

    async def _check_target_branch_status(self) -> None:
        """Check if local target branch is out of date with remote and warn user."""
        try:
            local_target = self._target_branch
            remote_target = f"origin/{self._target_branch}"

            # Check if both exist
            ref_names = [ref.name for ref in self.repo.references]
            if local_target in ref_names and remote_target in ref_names:
                # Get commit hashes
                local_commit = await asyncio.to_thread(
                    lambda: self.repo.commit(local_target).hexsha
                )
                remote_commit = await asyncio.to_thread(
                    lambda: self.repo.commit(remote_target).hexsha
                )

                # Warn if local is behind remote
                if local_commit != remote_commit:
                    # Check if local is behind (remote is ahead)
                    merge_base_result = await asyncio.to_thread(
                        self.repo.merge_base, local_commit, remote_commit
                    )
                    if (
                        merge_base_result
                        and merge_base_result[0].hexsha == local_commit
                    ):
                        logger.warning(
                            "Local target branch appears to be behind remote",
                            local_branch=local_target,
                            remote_branch=remote_target,
                            suggestion=f"Consider running: git pull origin {self._target_branch}",
                        )
        except Exception as e:
            # Don't fail the entire operation if this check fails
            logger.debug("Could not check target branch status", error=str(e))

    def _get_diff_content(self, diff_item: Any) -> str:
        """Get diff content as unified diff string with proper headers.

        GitPython's diff_item.diff property returns the patch content (from @@ onwards).
        We need to construct a complete unified diff format for the AI to understand.
        """
        # Get the actual diff content (patch from @@ onwards)
        diff_bytes = diff_item.diff

        # Handle None case explicitly (e.g., binary files, empty diffs)
        if diff_bytes is None:
            return ""

        # Convert bytes to string if necessary
        if isinstance(diff_bytes, bytes):
            patch_content = diff_bytes.decode("utf-8", errors="replace")
        else:
            patch_content = str(diff_bytes) if diff_bytes else ""

        if not patch_content:
            return ""

        # Construct complete unified diff format with headers
        # This helps the AI understand the context better
        a_path = diff_item.a_path or diff_item.b_path
        b_path = diff_item.b_path or diff_item.a_path

        diff_lines = []

        # Add diff header
        diff_lines.append(f"diff --git a/{a_path} b/{b_path}")

        # Add file mode indicators
        if diff_item.change_type == "A":  # New file
            diff_lines.append(f"new file mode {diff_item.b_mode or '100644'}")
        elif diff_item.change_type == "D":  # Deleted file
            diff_lines.append(f"deleted file mode {diff_item.a_mode or '100644'}")
        elif diff_item.change_type == "R":  # Renamed
            diff_lines.append(f"rename from {a_path}")
            diff_lines.append(f"rename to {b_path}")

        # Add --- and +++ lines
        diff_lines.append(f"--- a/{a_path}")
        diff_lines.append(f"+++ b/{b_path}")

        # Add the actual patch content
        diff_lines.append(patch_content)

        full_diff = "\n".join(diff_lines)

        # Log first diff for debugging (only once)
        if not hasattr(self, "_logged_first_diff"):
            self._logged_first_diff = True
            logger.debug(
                "Sample diff content from GitPython",
                file_path=b_path,
                diff_length=len(full_diff),
                patch_length=len(patch_content),
                first_200_chars=full_diff[:200],
            )

        return full_diff

    async def _get_current_user(self) -> str:
        """Get current git user name."""
        try:
            config_reader = self.repo.config_reader()
            try:
                return str(config_reader.get_value("user", "name", "unknown"))
            finally:
                config_reader.release()
        except Exception:
            return "local-user"

    def _is_binary_file(self, file_path: str) -> bool:
        """Check if file is binary based on extension.

        Args:
            file_path: Path of the file to check

        Returns:
            True if file appears to be binary
        """
        file_path_lower = file_path.lower()
        # BINARY_EXTENSIONS is already a tuple for efficient checking
        return file_path_lower.endswith(BINARY_EXTENSIONS)

    async def _get_local_diffs(self, base_commit: str) -> list[PullRequestDiff]:
        """Get diffs between base commit and current HEAD with pre-filtering.

        Pre-filters binary files and excluded patterns before reading diff
        content from disk, improving efficiency.

        Args:
            base_commit: Base commit SHA to compare against

        Returns:
            List of diffs for files that pass filters
        """
        diffs: list[PullRequestDiff] = []
        excluded_files: list[str] = []
        excluded_chars = 0
        binary_files: list[str] = []

        try:
            # Get the diff between base and current HEAD
            diff_index = await asyncio.to_thread(
                self.repo.commit(base_commit).diff, self.repo.head.commit
            )

            skipped_no_diff = []

            for diff_item in diff_index:
                # Get file path (handle renames)
                file_path = diff_item.b_path or diff_item.a_path
                if not file_path:
                    continue

                # PRE-FILTER: Skip binary files before reading content
                if self._is_binary_file(file_path):
                    binary_files.append(file_path)
                    continue

                # PRE-FILTER: Skip excluded patterns before reading content
                if self._should_exclude_file(file_path):
                    excluded_files.append(file_path)
                    continue

                # NOW read the actual diff content (only for files we'll use)
                diff_content = await asyncio.to_thread(
                    self._get_diff_content, diff_item
                )

                # Skip files without diffs
                if not diff_content or diff_content.strip() == "":
                    skipped_no_diff.append(file_path)
                    continue

                # Track excluded chars for statistics
                excluded_chars += (
                    len(diff_content) if file_path in excluded_files else 0
                )

                # Create diff object
                diff = PullRequestDiff(
                    file_path=file_path,
                    new_file=diff_item.change_type == "A",  # Added
                    renamed_file=diff_item.change_type == "R",  # Renamed
                    deleted_file=diff_item.change_type == "D",  # Deleted
                    diff=diff_content,
                )

                diffs.append(diff)

                # Check limits
                if len(diffs) >= self.config.max_files:
                    break

            # Log filtering and skipping statistics
            if excluded_files:
                logger.info(
                    "Files excluded from local review",
                    excluded_files=len(excluded_files),
                    excluded_chars=excluded_chars,
                    included_files=len(diffs),
                    examples=excluded_files[:3],
                )

            if binary_files:
                logger.info(
                    "Binary files skipped",
                    binary_files=len(binary_files),
                    reason="Binary files detected by extension",
                    examples=binary_files[:3],
                )

            if skipped_no_diff:
                logger.info(
                    "Files skipped - no diff content",
                    skipped_files=len(skipped_no_diff),
                    reason="Files with no changes",
                    examples=skipped_no_diff[:3],
                )

            return self._apply_content_limits(diffs)

        except Exception as e:
            raise GitLocalError(f"Failed to get local diffs: {e}") from e

    async def _get_local_commits(self, base_commit: str) -> list[PullRequestCommit]:
        """Get commits between base commit and current HEAD."""
        commits: list[PullRequestCommit] = []

        try:
            # Get commits from base to HEAD
            commit_range = f"{base_commit}..HEAD"
            repo_commits = list(
                await asyncio.to_thread(self.repo.iter_commits, commit_range)
            )

            for git_commit in repo_commits:
                commit = PullRequestCommit(
                    id=git_commit.hexsha,
                    title=str(git_commit.summary),
                    message=str(git_commit.message),
                    author_name=str(git_commit.author.name or "unknown"),
                    author_email=str(git_commit.author.email or "unknown@example.com"),
                    committed_date=git_commit.committed_datetime.isoformat(),
                    short_id=git_commit.hexsha[:8],
                )
                commits.append(commit)

            return commits

        except Exception as e:
            raise GitLocalError(f"Failed to get local commits: {e}") from e

    async def post_review(
        self, project_id: str, pr_number: int, review_content: str
    ) -> PostReviewResponse:
        """Post review is not applicable for local mode.

        Args:
            project_id: Ignored for local mode
            pr_number: Ignored for local mode
            review_content: The review content (would be saved to file or displayed)

        Returns:
            Mock response indicating local review was completed

        Raises:
            GitLocalError: Always, as posting is not supported in local mode
        """
        raise GitLocalError(
            "Posting reviews is not supported in local mode. "
            "Use --output-file to save the review or view it in terminal."
        )

    def get_platform_name(self) -> str:
        """Get the platform name."""
        return "local"

    def format_project_url(self, project_id: str) -> str:
        """Format the project URL for local repositories."""
        return f"file://{Path(self.repo.working_dir)}"

    def _create_mock_pr_data(self, project_id: str, pr_number: int) -> PullRequestData:
        """Create mock PR data for dry run mode."""
        pr_info = PullRequestInfo(
            id=0,
            number=0,
            title="Mock Local Review",
            description="Dry run mode - no actual git operations performed",
            source_branch="mock-branch",
            target_branch="main",
            author="mock-user",
            state="local",
            web_url="file://mock-repo",
        )

        mock_diff = PullRequestDiff(
            file_path="example.py",
            new_file=False,
            renamed_file=False,
            deleted_file=False,
            diff="""@@ -1,3 +1,4 @@
 def example_function():
+    # Mock change for dry run
     print("Hello, world!")
     return True""",
        )

        mock_commit = PullRequestCommit(
            id="abcd1234",
            title="Mock commit for dry run",
            message="Mock commit for dry run",
            author_name="mock-user",
            author_email="mock@example.com",
            committed_date="2024-01-01T00:00:00+00:00",
            short_id="abcd123",
        )

        return PullRequestData(
            info=pr_info,
            diffs=[mock_diff],
            commits=[mock_commit],
        )
