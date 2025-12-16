"""Review engine that orchestrates GitLab and AI providers."""

from __future__ import annotations

import logging
import re
from typing import Any

import click
import structlog

from ai_code_review.models.config import AIProvider, Config, PlatformProvider
from ai_code_review.models.platform import (
    PlatformClientInterface,
    PostReviewResponse,
    PullRequestData,
)
from ai_code_review.models.review import CodeReview, ReviewResult, ReviewSummary
from ai_code_review.providers.base import BaseAIProvider
from ai_code_review.providers.ollama import OllamaProvider
from ai_code_review.utils.constants import (
    AUTO_BIG_DIFFS_THRESHOLD_CHARS,
    CHARS_TO_TOKENS_RATIO,
    SYSTEM_PROMPT_ESTIMATED_CHARS,
    SYSTEM_PROMPT_ESTIMATED_TOKENS,
)
from ai_code_review.utils.exceptions import AIProviderError, ReviewSkippedError
from ai_code_review.utils.prompts import (
    _format_commit_messages,
    _format_reviews_and_comments,
    create_review_chain,
    create_synthesis_chain,
)

logger = structlog.get_logger(__name__)


class ReviewEngine:
    """Engine that coordinates platform clients and AI providers to generate code reviews."""

    def __init__(self, config: Config) -> None:
        """Initialize review engine."""
        self.config = config
        self.platform_client = self._create_platform_client(config)
        self.ai_provider = self._create_ai_provider()

        # Setup logging
        logging.getLogger().setLevel(getattr(logging, config.log_level))

        # Silence noisy third-party loggers in INFO mode
        if config.log_level.upper() == "INFO":
            logging.getLogger("httpx").setLevel(logging.WARNING)
            logging.getLogger("urllib3").setLevel(logging.WARNING)

    def _create_platform_client(self, config: Config) -> PlatformClientInterface:
        """Create platform client instance based on configuration."""
        if config.platform_provider == PlatformProvider.GITLAB:
            from ai_code_review.core.gitlab_client import GitLabClient

            return GitLabClient(config)
        elif config.platform_provider == PlatformProvider.GITHUB:
            from ai_code_review.core.github_client import GitHubClient

            return GitHubClient(config)
        elif config.platform_provider == PlatformProvider.LOCAL:
            from ai_code_review.core.local_git_client import LocalGitClient

            return LocalGitClient(config)
        else:
            raise AIProviderError(
                f"Platform provider '{config.platform_provider}' not supported",
                config.platform_provider.value,
            )

    def _create_ai_provider(self, model_override: str | None = None) -> BaseAIProvider:
        """Create AI provider instance based on configuration.

        Args:
            model_override: Optional model name to override config.ai_model.
                          Useful for creating providers with different models
                          (e.g., fast synthesis model vs main review model).

        Returns:
            BaseAIProvider instance configured for the specified model
        """
        # Use config copy if model override is provided to avoid mutation
        config_to_use = self.config
        if model_override:
            config_to_use = self.config.model_copy(update={"ai_model": model_override})

        if config_to_use.ai_provider == AIProvider.OLLAMA:
            return OllamaProvider(config_to_use)
        elif config_to_use.ai_provider == AIProvider.GEMINI:
            from ai_code_review.providers.gemini import GeminiProvider

            return GeminiProvider(config_to_use)
        elif config_to_use.ai_provider == AIProvider.ANTHROPIC:
            from ai_code_review.providers.anthropic import AnthropicProvider

            return AnthropicProvider(config_to_use)

        # TODO: Implement other providers (OpenAI) in future iterations
        raise AIProviderError(
            f"AI provider '{config_to_use.ai_provider}' not yet implemented",
            config_to_use.ai_provider.value,
        )

    def should_skip_review(
        self, pr_data: PullRequestData
    ) -> tuple[bool, str | None, str | None]:
        """Check if review should be skipped based on multiple criteria.

        Args:
            pr_data: Pull/merge request data containing info and diffs

        Returns:
            Tuple of (should_skip, reason_category, trigger_details)
            - should_skip: True if review should be skipped
            - reason_category: Category of skip reason (keyword, pattern, bot_author, documentation_only)
            - trigger_details: Specific trigger that caused the skip
        """
        if not self.config.skip_review.enabled:
            return False, None, None

        pr_info = pr_data.info

        # 1. Check explicit keywords in title + description
        text_to_check = f"{pr_info.title} {pr_info.description or ''}".lower()
        for keyword in self.config.skip_review.keywords:
            if keyword.lower() in text_to_check:
                return True, "keyword", keyword

        # 2. Check dependency/automation patterns in title (if enabled)
        if self.config.skip_review.skip_dependency_updates:
            title = pr_info.title
            for pattern in self.config.skip_review.patterns:
                try:
                    if re.match(pattern, title, re.IGNORECASE):
                        return True, "pattern", pattern
                except re.error:
                    # Skip invalid patterns (should be caught in validation)
                    logger.warning("Invalid regex pattern skipped", pattern=pattern)
                    continue

        # 2.5. Check documentation patterns in title (if documentation skipping enabled)
        if self.config.skip_review.skip_documentation_only:
            title = pr_info.title
            for pattern in self.config.skip_review.documentation_patterns:
                try:
                    if re.match(pattern, title, re.IGNORECASE):
                        return True, "documentation_pattern", pattern
                except re.error:
                    logger.warning(
                        "Invalid documentation pattern skipped", pattern=pattern
                    )
                    continue

        # 3. Check bot authors (if bot author detection enabled)
        if self.config.skip_review.skip_bot_authors:
            author = pr_info.author.lower()
            for bot_author in self.config.skip_review.bot_authors:
                if bot_author.lower() in author:
                    return True, "bot_author", bot_author

        # 4. Check if draft PR/MR (if enabled)
        if self.config.skip_review.skip_draft_prs:
            if pr_data.info.draft:
                return True, "draft", "pull/merge request is in draft mode"

        # 5. Check if documentation-only changes (if enabled)
        if self.config.skip_review.skip_documentation_only:
            if self._is_documentation_only_change(pr_data):
                return True, "documentation_only", "all files are documentation"

        return False, None, None

    def _is_documentation_only_change(self, pr_data: PullRequestData) -> bool:
        """Detect if changes are documentation-only.

        Args:
            pr_data: Pull/merge request data containing file diffs

        Returns:
            True if all changed files are documentation files
        """
        if not pr_data.diffs:
            return False

        import os

        doc_extensions = {".md", ".txt", ".rst", ".adoc", ".wiki"}
        doc_dirs = {"docs/", "doc/", ".github/"}
        # Check against filename stems to be more specific
        doc_filenames = {"readme", "changelog", "contributing", "license"}

        for diff in pr_data.diffs:
            path_lower = diff.file_path.lower()
            filename_stem = os.path.splitext(os.path.basename(path_lower))[0]

            has_doc_extension = any(path_lower.endswith(ext) for ext in doc_extensions)
            is_in_doc_dir = any(path_lower.startswith(d) for d in doc_dirs)
            # Use exact match for standalone doc files to avoid false positives
            is_doc_file = filename_stem in doc_filenames

            if not (has_doc_extension or is_in_doc_dir or is_doc_file):
                return False  # Found non-documentation file

        return True  # All files are documentation

    async def generate_review(self, project_id: str | int, mr_iid: int) -> ReviewResult:
        """Generate comprehensive code review with summary in a single LLM call.

        This method always generates both review and summary efficiently using
        a unified prompt to minimize costs and improve consistency.
        """
        logger.info(
            "Starting review generation",
            project_id=project_id,
            mr_iid=mr_iid,
            provider=self.config.ai_provider.value,
            model=self.config.get_ai_model(),
            dry_run=self.config.dry_run,
        )

        try:
            # Step 1: Fetch PR/MR data from platform
            pr_data = await self.platform_client.get_pull_request_data(
                str(project_id), mr_iid
            )

            logger.info(
                "PR/MR data fetched successfully",
                file_count=pr_data.file_count,
                commit_count=pr_data.commit_count,
                total_chars=pr_data.total_chars,
                pr_title=pr_data.info.title,
                platform=self.platform_client.get_platform_name(),
            )

            # Step 1.5: Check if review should be skipped
            should_skip, skip_reason, skip_trigger = self.should_skip_review(pr_data)
            if should_skip:
                # Type safety: if should_skip is True, reason and trigger must not be None
                if skip_reason is None:
                    raise ValueError(
                        "Skip reason cannot be None when should_skip is True"
                    )
                if skip_trigger is None:
                    raise ValueError(
                        "Skip trigger cannot be None when should_skip is True"
                    )

                logger.info(
                    "Review skipped automatically",
                    reason=skip_reason,
                    trigger=skip_trigger,
                    pr_title=pr_data.info.title,
                    author=pr_data.info.author,
                    project_id=project_id,
                    mr_iid=mr_iid,
                )

                # Raise exception to be handled at CLI level for proper exit code
                skip_message = f"Review skipped due to {skip_reason}: {skip_trigger}"
                raise ReviewSkippedError(skip_message, skip_reason, skip_trigger)

            # Calculate project context once for both dry-run and normal execution
            project_context = self._get_project_context(pr_data)
            project_context_chars = len(project_context) if project_context else 0
            system_prompt_chars = SYSTEM_PROMPT_ESTIMATED_CHARS

            # Step 2: Generate review using AI (single call)
            if self.config.dry_run:
                logger.info("DRY RUN: Generating mock review")

                # Even in dry-run, analyze the diff for token estimation with adaptive context
                diff_content = self._format_diffs_for_ai(pr_data)
                original_total_chars = sum(len(diff.diff) for diff in pr_data.diffs)

                # Calculate context parameters using helper method
                manual_big_diffs = self.config.big_diffs
                total_content_chars, context_window_size, auto_big_diffs = (
                    self._calculate_context_parameters(
                        original_total_chars,
                        project_context_chars,
                        system_prompt_chars,
                        manual_big_diffs,
                    )
                )

                estimated_input_tokens = int(
                    len(diff_content) / CHARS_TO_TOKENS_RATIO
                )  # Real ratio from codebase analysis
                estimated_prompt_tokens = 500  # Rough estimate for prompt template
                total_estimated_tokens = (
                    estimated_input_tokens + estimated_prompt_tokens
                )

                logger.info(
                    "DRY RUN: Token analysis",
                    original_diff_length=original_total_chars,
                    processed_diff_length=len(diff_content),
                    context_window_size=context_window_size,
                    manual_big_diffs=manual_big_diffs,
                    auto_big_diffs_activated=auto_big_diffs,
                    estimated_input_tokens=estimated_input_tokens,
                    estimated_prompt_tokens=estimated_prompt_tokens,
                    total_estimated_tokens=total_estimated_tokens,
                    tokens_usage_percent=round(
                        (total_estimated_tokens / context_window_size) * 100, 1
                    ),
                    truncated=False,  # No truncation with new approach
                )

                review = self._create_mock_review()
                summary = self._create_mock_summary(pr_data)
            else:
                review, summary = await self._generate_review_response(
                    pr_data, project_context, project_context_chars, system_prompt_chars
                )

            result = ReviewResult(review=review, summary=summary)

            logger.info("Review generation completed successfully")

            return result

        except ReviewSkippedError:
            # Re-raise skip errors without modification - they should be handled at CLI level
            raise
        except Exception as e:
            logger.error(
                "Review generation failed",
                error=str(e),
                project_id=project_id,
                mr_iid=mr_iid,
            )
            raise AIProviderError(
                f"Failed to generate review: {e}", "review_engine"
            ) from e

    def _calculate_context_parameters(
        self,
        original_total_chars: int,
        project_context_chars: int,
        system_prompt_chars: int,
        manual_big_diffs: bool = False,
    ) -> tuple[int, int, bool]:
        """Calculate context parameters for diff processing.

        Args:
            original_total_chars: Total characters in original diff content
            project_context_chars: Characters in project context
            system_prompt_chars: Characters in system prompt
            manual_big_diffs: Whether big_diffs was manually enabled

        Returns:
            Tuple of (total_content_chars, context_window_size, auto_big_diffs)
        """
        # Calculate total content size
        total_content_chars = (
            original_total_chars + project_context_chars + system_prompt_chars
        )

        # Use adaptive context size based on total content size
        context_window_size = getattr(
            self.ai_provider,
            "get_adaptive_context_size",
            lambda x, y=0, z=SYSTEM_PROMPT_ESTIMATED_CHARS: 16384,
        )(original_total_chars, project_context_chars, system_prompt_chars)

        # Detect if big-diffs was auto-activated
        auto_big_diffs = (
            total_content_chars > AUTO_BIG_DIFFS_THRESHOLD_CHARS
            and not manual_big_diffs
        )

        return total_content_chars, context_window_size, auto_big_diffs

    def _create_llm_for_synthesis(self, model_name: str) -> Any:
        """Create LLM instance for synthesis phase.

        Uses same provider but typically a faster/cheaper model.

        Args:
            model_name: Name of the model to use for synthesis

        Returns:
            LLM client instance configured for synthesis
        """
        # Use _create_ai_provider with model override to avoid duplication
        synthesis_provider = self._create_ai_provider(model_override=model_name)

        # Check availability
        if not synthesis_provider.is_available():
            raise AIProviderError(
                f"{synthesis_provider.provider_name} is not available",
                synthesis_provider.provider_name,
            )

        return synthesis_provider.client

    async def _generate_review_response(
        self,
        pr_data: PullRequestData,
        project_context: str,
        project_context_chars: int,
        system_prompt_chars: int,
    ) -> tuple[CodeReview, ReviewSummary]:
        """Generate review response using two-phase synthesis (optional).

        Phase 1 (if enabled): Synthesize comments with fast model
        Phase 2: Generate review with synthesis as context
        """
        # Check AI provider availability
        if not self.ai_provider.is_available():
            raise AIProviderError(
                f"{self.ai_provider.provider_name} is not available",
                self.ai_provider.provider_name,
            )

        try:
            review_synthesis = None

            # Phase 1: Synthesize review context if enabled and comments exist
            if (
                self.config.enable_review_context
                and self.config.enable_review_synthesis
                and (pr_data.reviews or pr_data.comments)
            ):
                logger.info("Phase 1: Synthesizing review context with fast model")

                # Get bot username for identifying AI reviews
                bot_username = await self.platform_client.get_authenticated_username()

                # Create synthesis chain with fast model
                synthesis_model_name = self.config.get_synthesis_model()
                synthesis_llm = self._create_llm_for_synthesis(synthesis_model_name)
                synthesis_chain = create_synthesis_chain(synthesis_llm)

                # Generate synthesis
                try:
                    review_synthesis = await synthesis_chain.ainvoke(
                        {
                            "pr_description": pr_data.info.description
                            or "No description provided",
                            "commit_messages": _format_commit_messages(pr_data),
                            "reviews_and_comments": _format_reviews_and_comments(
                                pr_data, bot_username
                            ),
                        }
                    )

                    logger.info(
                        "Review synthesis complete",
                        synthesis_length=len(review_synthesis),
                        reviews_count=len(pr_data.reviews),
                        comments_count=len(pr_data.comments),
                    )

                    # Display synthesis output for transparency
                    # This helps users understand what context is being provided
                    # to the main review LLM, making the tool's behavior more transparent
                    click.echo("\n" + "=" * 80)
                    click.echo("🔍 SYNTHESIS OUTPUT (Phase 1)")
                    click.echo("=" * 80)
                    click.echo(review_synthesis)
                    click.echo("=" * 80 + "\n")
                except Exception as e:
                    logger.warning("Failed to generate review synthesis", error=str(e))
                    review_synthesis = None
            else:
                # Log why synthesis was skipped
                if not self.config.enable_review_context:
                    logger.debug(
                        "Skipping review context - disabled in config",
                        enable_review_context=False,
                    )
                elif not self.config.enable_review_synthesis:
                    logger.debug(
                        "Skipping review synthesis - disabled in config",
                        enable_review_synthesis=False,
                    )
                elif not (pr_data.reviews or pr_data.comments):
                    logger.info(
                        "Skipping review synthesis - no previous reviews or comments",
                        reviews_count=0,
                        comments_count=0,
                    )

            # Phase 2: Generate main review with synthesis (if available)
            logger.info("Generating main review")

            # Create review chain (uses unified prompt with config-based format)
            review_chain = create_review_chain(self.ai_provider.client, self.config)

            # Prepare input data
            diff_content = self._format_diffs_for_ai(pr_data)

            # Log diff processing info with adaptive context window
            original_total_chars = sum(len(diff.diff) for diff in pr_data.diffs)

            # Calculate context parameters using helper method
            manual_big_diffs = getattr(self.config, "big_diffs", False)
            total_content_chars, context_window_size, auto_big_diffs = (
                self._calculate_context_parameters(
                    original_total_chars,
                    project_context_chars,
                    system_prompt_chars,
                    manual_big_diffs,
                )
            )

            # Estimate tokens using real codebase analysis
            try:
                estimated_diff_tokens = int(len(diff_content) / CHARS_TO_TOKENS_RATIO)
                estimated_project_context_tokens = int(
                    project_context_chars / CHARS_TO_TOKENS_RATIO
                )
                estimated_system_prompt_tokens = int(
                    system_prompt_chars / CHARS_TO_TOKENS_RATIO
                )
                total_estimated_tokens = (
                    estimated_diff_tokens
                    + estimated_project_context_tokens
                    + estimated_system_prompt_tokens
                )
            except (ZeroDivisionError, ValueError) as e:
                logger.warning("Failed to calculate token estimates", error=str(e))
                estimated_diff_tokens = 0
                estimated_project_context_tokens = 0
                estimated_system_prompt_tokens = SYSTEM_PROMPT_ESTIMATED_TOKENS
                total_estimated_tokens = SYSTEM_PROMPT_ESTIMATED_TOKENS

            logger.debug(
                "Invoking AI for review",
                original_diff_length=original_total_chars,
                project_context_length=project_context_chars,
                system_prompt_length=system_prompt_chars,
                total_content_length=total_content_chars,
                processed_diff_length=len(diff_content),
                context_window_size=context_window_size,
                manual_big_diffs=manual_big_diffs,
                auto_big_diffs_activated=auto_big_diffs,
                estimated_diff_tokens=estimated_diff_tokens,
                estimated_project_context_tokens=estimated_project_context_tokens,
                estimated_system_prompt_tokens=estimated_system_prompt_tokens,
                total_estimated_tokens=total_estimated_tokens,
                tokens_usage_percent=round(
                    (total_estimated_tokens / context_window_size) * 100, 1
                ),
                truncated=False,  # No truncation with new approach
            )

            # Update client with adaptive context size for this specific call
            if hasattr(self.ai_provider.client, "num_ctx"):
                original_num_ctx = self.ai_provider.client.num_ctx
                self.ai_provider.client.num_ctx = context_window_size

            try:
                review_response = await review_chain.ainvoke(
                    {
                        "diff": diff_content,
                        "language": self.config.language_hint,
                        "context": project_context,
                        "review_synthesis": review_synthesis,  # Can be None if disabled/failed
                    }
                )
            finally:
                # Restore original context size
                if hasattr(self.ai_provider.client, "num_ctx"):
                    self.ai_provider.client.num_ctx = original_num_ctx

            # Use the LLM response directly - it's already properly structured
            review = CodeReview(
                general_feedback=review_response,
                file_reviews=[],  # MVP: simplified structure
                overall_assessment="AI Review Generated",
                priority_issues=[],
                minor_suggestions=[],
            )

            # Always create summary (using basic PR/MR metadata for now)
            # TODO: Extract from structured AI response in future
            summary = ReviewSummary(
                title=pr_data.info.title,
                key_changes=[],  # TODO: Extract from structured response in future
                modules_affected=[],  # TODO: Extract from file analysis
                user_impact="To be determined",
                technical_impact="Included in detailed review above",
                risk_level="Medium",  # TODO: Extract from AI assessment
                risk_justification="Automated assessment pending detailed analysis",
            )

            return review, summary

        except Exception as e:
            raise AIProviderError(
                f"Failed to generate review with {self.ai_provider.provider_name}: {e}",
                self.ai_provider.provider_name,
            ) from e

    def _format_diffs_for_ai(self, pr_data: PullRequestData) -> str:
        """Format PR/MR diffs for AI processing - no truncation, relying on 16K context window."""
        formatted_diffs = []

        # Use platform-appropriate terminology
        request_type = (
            "Pull Request"
            if self.platform_client.get_platform_name() == "github"
            else "Merge Request"
        )

        formatted_diffs.append(f"# {request_type}: {pr_data.info.title}")
        formatted_diffs.append(f"**Author:** {pr_data.info.author}")
        formatted_diffs.append(
            f"**Source:** {pr_data.info.source_branch} → {pr_data.info.target_branch}"
        )

        if pr_data.info.description:
            formatted_diffs.append(f"**Description:** {pr_data.info.description}")

        formatted_diffs.append("")
        formatted_diffs.append("## File Changes")

        for diff in pr_data.diffs:
            formatted_diffs.append(f"\n### {diff.file_path}")

            if diff.new_file:
                formatted_diffs.append("*(New file)*")
            elif diff.deleted_file:
                formatted_diffs.append("*(Deleted file)*")
            elif diff.renamed_file:
                formatted_diffs.append("*(Renamed file)*")

            formatted_diffs.append("```diff")
            formatted_diffs.append(diff.diff)
            formatted_diffs.append("```")

        return "\n".join(formatted_diffs)

    def _get_project_context(self, pr_data: PullRequestData | None = None) -> str:
        """Get project context for AI review."""
        context_parts = []

        if self.config.language_hint:
            context_parts.append(f"Primary Language: {self.config.language_hint}")

        # Load contexts if enabled
        if self.config.enable_project_context:
            # Priority 1: Team/organization context (if configured)
            if self.config.team_context_file:
                logger.info(
                    "Loading team/organization context",
                    source=self.config.team_context_file,
                )
                team_context = self._load_context_from_source(
                    self.config.team_context_file
                )
                if team_context:
                    logger.info(
                        "Team/organization context loaded successfully",
                        content_length=len(team_context),
                    )
                    context_parts.append("\n**Team/Organization Context:**")
                    context_parts.append(team_context)
                else:
                    logger.warning(
                        "Team/organization context could not be loaded",
                        source=self.config.team_context_file,
                    )

            # Priority 2: Project context
            project_context_content = self._load_project_context_file()
            if project_context_content:
                logger.info(
                    "Project context loaded successfully",
                    content_length=len(project_context_content),
                )
                context_parts.append("\n**Project Context:**")
                context_parts.append(project_context_content)

        # Add commit context for better understanding
        if pr_data and pr_data.commits:
            context_parts.append("\n**Commit History:**")
            for commit in pr_data.commits:
                commit_info = f"- `{commit.short_id}` {commit.title}"
                if commit.message != commit.title:
                    # Add full message if it has more details beyond the title
                    commit_info += f"\n  {commit.message.strip()}"
                context_parts.append(commit_info)

        result = (
            "\n".join(context_parts)
            if context_parts
            else "No additional project context available."
        )

        # Log summary of loaded contexts
        if context_parts:
            context_types = []
            if self.config.team_context_file and any(
                "Team/Organization Context" in part for part in context_parts
            ):
                context_types.append("team")
            if any("Project Context" in part for part in context_parts):
                context_types.append("project")
            if pr_data and pr_data.commits:
                context_types.append(f"{len(pr_data.commits)} commits")

            logger.info(
                "Context prepared for AI review",
                contexts=", ".join(context_types),
                total_chars=len(result),
            )

        return result

    def _load_project_context_file(self) -> str | None:
        """Load project context from configured project context file.

        Returns:
            The content of the file if it exists and is readable, None otherwise
        """
        import os.path

        context_file_path = self.config.project_context_file

        try:
            if os.path.isfile(context_file_path):
                with open(context_file_path, encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        logger.debug(
                            "Loaded project context",
                            file_path=context_file_path,
                            content_length=len(content),
                        )
                        return content
                    else:
                        logger.debug(
                            "Project context file exists but is empty",
                            file_path=context_file_path,
                        )
                        return None
            else:
                logger.debug(
                    "Project context file not found", file_path=context_file_path
                )
                return None
        except Exception as e:
            logger.warning(
                "Failed to load project context file",
                file_path=context_file_path,
                error=str(e),
            )
            return None

    def _load_context_from_source(self, source: str) -> str | None:
        """Load context from local file or remote URL.

        Args:
            source: Local file path or HTTP(S) URL

        Returns:
            Content if successful, None otherwise
        """
        if source.startswith(("http://", "https://")):
            return self._load_remote_context(source)
        else:
            return self._load_local_context(source)

    def _load_local_context(self, file_path: str) -> str | None:
        """Load context from local file.

        Args:
            file_path: Path to local context file

        Returns:
            Content if successful, None otherwise
        """
        import os.path

        try:
            if os.path.isfile(file_path):
                with open(file_path, encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        logger.debug(
                            "Loaded local context",
                            file_path=file_path,
                            content_length=len(content),
                        )
                        return content
                    return None
            else:
                logger.debug("Context file not found", file_path=file_path)
                return None
        except Exception as e:
            logger.warning(
                "Failed to load local context file",
                file_path=file_path,
                error=str(e),
            )
            return None

    def _load_remote_context(self, url: str) -> str | None:
        """Load context from remote URL (no caching, always downloads).

        Args:
            url: HTTP(S) URL to context file

        Returns:
            Content if successful, None otherwise
        """
        import httpx

        try:
            # Use same timeout as configured for API calls
            timeout = self.config.http_timeout

            # Use SSL verification settings from config
            verify: bool | str = self.config.ssl_verify
            if self.config.ssl_cert_path:
                verify = self.config.ssl_cert_path

            response = httpx.get(url, timeout=timeout, verify=verify)
            response.raise_for_status()

            content = response.text.strip()
            if content:
                logger.info(
                    "Loaded remote context",
                    url=url,
                    content_length=len(content),
                )
                return content
            else:
                logger.warning("Remote context file is empty", url=url)
                return None

        except httpx.TimeoutException:
            logger.warning("Timeout loading remote context", url=url, timeout=timeout)
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(
                "Failed to fetch remote context",
                url=url,
                status=e.response.status_code,
            )
            return None
        except Exception as e:
            logger.warning("Error loading remote context", url=url, error=str(e))
            return None

    def _create_mock_review(self) -> CodeReview:
        """Create mock review for dry-run mode."""
        # Check if local mode
        local_mode = (
            hasattr(self.config, "platform_provider")
            and self.config.platform_provider.value == "local"
        )

        # Use appropriate header and summary format
        if local_mode:
            header = "## Local Code Review"
            summary_content = """### ✅ Summary

**Overall Assessment:** [MOCK] Good code quality for testing

**Priority Issues:**
- [MOCK] No critical issues identified

**Minor Suggestions:**
- [MOCK] Consider adding more comprehensive tests"""
        else:
            header = "## AI Code Review"
            summary_content = """### ✅ Summary
- **Overall Assessment:** [MOCK] Good code quality for testing
- **Priority Issues:** [MOCK] No critical issues identified
- **Minor Suggestions:** [MOCK] Consider adding more comprehensive tests"""

        # Build content parts to avoid duplication
        parts = [header]

        if self.config.include_mr_summary and not local_mode:
            parts.append("""### 📋 MR Summary
[DRY RUN] Mock merge request for testing purposes.

- **Key Changes:** Mock code modifications for testing
- **Impact:** Testing environment only, no production impact
- **Risk Level:** Low - Mock changes for development testing""")

        if local_mode:
            parts.append("""### 🔍 Code Analysis

[DRY RUN] Mock code analysis generated. This would be replaced with actual AI feedback in real execution.

### 📂 File Reviews

**📄 `example.py`** - Mock file review
- **Review:** [MOCK] Example review feedback
- **Suggestion:** [MOCK] Example improvement suggestion""")
        else:
            parts.append("""### Detailed Code Review

[DRY RUN] Mock code review generated. This would be replaced with actual AI feedback in real execution.""")

        # Combine all parts with common summary
        main_content = "\n\n".join(parts)
        mock_content = f"{main_content}\n\n{summary_content}"

        return CodeReview(
            general_feedback=mock_content,
            file_reviews=[],
            overall_assessment="Mock assessment for testing purposes",
            priority_issues=["[MOCK] Example priority issue"],
            minor_suggestions=["[MOCK] Example minor suggestion"],
        )

    def _create_mock_summary(self, pr_data: PullRequestData) -> ReviewSummary:
        """Create mock summary for dry-run mode."""
        return ReviewSummary(
            title=f"[DRY RUN] {pr_data.info.title}",
            key_changes=["Mock change 1", "Mock change 2"],
            modules_affected=["mock_module"],
            user_impact="[MOCK] No user-facing changes identified",
            technical_impact="[MOCK] Minor technical improvements",
            risk_level="Low",
            risk_justification="[MOCK] Changes appear safe for testing",
        )

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on all components."""
        logger.info("Performing health check")

        health_status = {
            "config": {"status": "healthy", "provider": self.config.ai_provider.value},
            "ai_provider": {},
        }

        # Check AI provider
        try:
            if hasattr(self.ai_provider, "health_check"):
                health_status["ai_provider"] = await self.ai_provider.health_check()
            else:
                health_status["ai_provider"] = {
                    "status": "healthy"
                    if self.ai_provider.is_available()
                    else "unavailable",
                    "available": str(self.ai_provider.is_available()),
                }
        except Exception as e:
            health_status["ai_provider"] = {
                "status": "error",
                "error": str(e),
            }

        # Overall status
        all_healthy = all(
            component.get("status") == "healthy"
            for component in health_status.values()
            if isinstance(component, dict)
        )

        health_status["overall"] = {"status": "healthy" if all_healthy else "unhealthy"}

        overall_status = health_status["overall"]["status"]
        logger.info("Health check completed", overall_status=overall_status)

        return health_status

    async def post_review_to_platform(
        self,
        project_id: str,
        pr_number: int,
        review_result: ReviewResult,
    ) -> PostReviewResponse:
        """Post generated review as a comment to the platform (GitLab/GitHub).

        Args:
            project_id: Platform-specific project identifier
            pr_number: Pull/merge request number
            review_result: The review result to post

        Returns:
            PostReviewResponse containing comment information

        Raises:
            PlatformAPIError: If posting fails
        """
        platform_name = self.platform_client.get_platform_name()
        logger.info(
            f"Posting review to {platform_name}",
            project_id=project_id,
            pr_number=pr_number,
            platform=platform_name,
            dry_run=self.config.dry_run,
        )

        # Format review content as markdown
        review_content = review_result.to_markdown()

        # Add footer with metadata
        footer = self._create_review_footer()
        full_content = f"{review_content}\n\n{footer}"

        # Post to platform (handles dry-run internally)
        response = await self.platform_client.post_review(
            project_id, pr_number, full_content
        )

        logger.info(
            "Review posted successfully",
            note_id=response.id,
            note_url=response.url,
            platform=platform_name,
            dry_run=self.config.dry_run,
        )

        return response

    def _create_review_footer(self) -> str:
        """Create footer with review metadata."""
        platform_name = self.platform_client.get_platform_name().title()
        footer_parts = [
            "---",
            "🤖 **AI Code Review** | Generated with [ai-code-review](https://gitlab.com/redhat/edge/ci-cd/ai-code-review)",
            f"**Platform:** {platform_name} | **AI Provider:** {self.config.ai_provider.value} | **Model:** {self.config.get_ai_model()}",
        ]

        if self.config.dry_run:
            footer_parts.append("**Mode:** DRY RUN - No actual changes were analyzed")

        return "\n".join(footer_parts)

    # Legacy method for backward compatibility
    async def post_review_to_gitlab(
        self,
        project_id: str | int,
        mr_iid: int,
        review_result: ReviewResult,
    ) -> PostReviewResponse:
        """Legacy method for backward compatibility. Use post_review_to_platform instead."""
        return await self.post_review_to_platform(
            str(project_id), mr_iid, review_result
        )
