"""Review engine that orchestrates GitLab and AI providers."""

from __future__ import annotations

import logging
from typing import Any

import structlog

from ai_code_review.core.gitlab_client import GitLabClient
from ai_code_review.models.config import AIProvider, Config
from ai_code_review.models.gitlab import MergeRequestData
from ai_code_review.models.review import CodeReview, ReviewResult, ReviewSummary
from ai_code_review.providers.base import BaseAIProvider
from ai_code_review.providers.ollama import OllamaProvider
from ai_code_review.utils.exceptions import AIProviderError
from ai_code_review.utils.prompts import create_review_chain

logger = structlog.get_logger(__name__)


class ReviewEngine:
    """Engine that coordinates GitLab and AI providers to generate code reviews."""

    def __init__(self, config: Config) -> None:
        """Initialize review engine."""
        self.config = config
        self.gitlab_client = GitLabClient(config)
        self.ai_provider = self._create_ai_provider()

        # Setup logging
        logging.getLogger().setLevel(getattr(logging, config.log_level))

        # Silence noisy third-party loggers in INFO mode
        if config.log_level.upper() == "INFO":
            logging.getLogger("httpx").setLevel(logging.WARNING)
            logging.getLogger("urllib3").setLevel(logging.WARNING)

    def _create_ai_provider(self) -> BaseAIProvider:
        """Create AI provider instance based on configuration."""
        if self.config.ai_provider == AIProvider.OLLAMA:
            return OllamaProvider(self.config)

        # TODO: Implement other providers in future iterations
        raise AIProviderError(
            f"AI provider '{self.config.ai_provider}' not yet implemented",
            self.config.ai_provider.value,
        )

    async def generate_review(
        self, project_id: str | int, mr_iid: int, include_summary: bool = True
    ) -> ReviewResult:
        """Generate comprehensive code review with summary in a single LLM call.

        This method always generates both review and summary efficiently using
        a unified prompt to minimize costs and improve consistency.
        """
        logger.info(
            "Starting review generation",
            project_id=project_id,
            mr_iid=mr_iid,
            provider=self.config.ai_provider.value,
            model=self.config.ai_model,
            dry_run=self.config.dry_run,
        )

        try:
            # Step 1: Fetch MR data from GitLab
            mr_data = await self.gitlab_client.get_merge_request_data(
                project_id, mr_iid
            )

            logger.info(
                "MR data fetched successfully",
                file_count=mr_data.file_count,
                commit_count=mr_data.commit_count,
                total_chars=mr_data.total_chars,
                mr_title=mr_data.info.title,
            )

            # Step 2: Generate review using AI (single call)
            if self.config.dry_run:
                logger.info("DRY RUN: Generating mock review")

                # Even in dry-run, analyze the diff for token estimation with adaptive context
                diff_content = self._format_diffs_for_ai(mr_data)
                original_total_chars = sum(len(diff.diff) for diff in mr_data.diffs)

                # Use adaptive context size based on diff size
                context_window_size = getattr(
                    self.ai_provider, "get_adaptive_context_size", lambda x: 16384
                )(original_total_chars)

                # Detect if big-diffs was auto-activated
                manual_big_diffs = getattr(self.config, "big_diffs", False)
                auto_big_diffs = original_total_chars > 60000 and not manual_big_diffs

                estimated_input_tokens = int(
                    len(diff_content) / 2.5
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
                summary = (
                    self._create_mock_summary(mr_data) if include_summary else None
                )
            else:
                review, summary = await self._generate_review_response(
                    mr_data, include_summary
                )

            result = ReviewResult(review=review, summary=summary)

            logger.info("Review generation completed successfully")

            return result

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

    async def _generate_review_response(
        self, mr_data: MergeRequestData, include_summary: bool
    ) -> tuple[CodeReview, ReviewSummary | None]:
        """Generate review response using single LLM call."""
        # Check AI provider availability
        if not self.ai_provider.is_available():
            raise AIProviderError(
                f"{self.ai_provider.provider_name} is not available",
                self.ai_provider.provider_name,
            )

        try:
            # Create review chain (uses unified prompt)
            review_chain = create_review_chain(self.ai_provider.client)

            # Prepare input data
            diff_content = self._format_diffs_for_ai(mr_data)

            # Log diff processing info with adaptive context window
            original_total_chars = sum(len(diff.diff) for diff in mr_data.diffs)
            context_window_size = getattr(
                self.ai_provider, "get_adaptive_context_size", lambda x: 16384
            )(original_total_chars)

            # Detect if big-diffs was auto-activated
            manual_big_diffs = getattr(self.config, "big_diffs", False)
            auto_big_diffs = original_total_chars > 60000 and not manual_big_diffs

            # Estimate tokens using real codebase analysis (2.5 chars/token average)
            estimated_input_tokens = int(
                len(diff_content) / 2.5
            )  # Real ratio from codebase analysis
            estimated_prompt_tokens = 500  # Rough estimate for prompt template
            total_estimated_tokens = estimated_input_tokens + estimated_prompt_tokens

            logger.debug(
                "Invoking AI for review",
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

            # Update client with adaptive context size for this specific call
            if hasattr(self.ai_provider.client, "num_ctx"):
                original_num_ctx = self.ai_provider.client.num_ctx
                self.ai_provider.client.num_ctx = context_window_size

            try:
                review_response = await review_chain.ainvoke(
                    {
                        "diff": diff_content,
                        "language": self.config.language_hint,
                        "context": self._get_project_context(mr_data),
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

            # Create summary if requested (using basic MR metadata)
            summary = None
            if include_summary:
                summary = ReviewSummary(
                    title=mr_data.info.title,
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

    def _format_diffs_for_ai(self, mr_data: MergeRequestData) -> str:
        """Format MR diffs for AI processing - no truncation, relying on 16K context window."""
        formatted_diffs = []

        formatted_diffs.append(f"# Merge Request: {mr_data.info.title}")
        formatted_diffs.append(f"**Author:** {mr_data.info.author}")
        formatted_diffs.append(
            f"**Source:** {mr_data.info.source_branch} → {mr_data.info.target_branch}"
        )

        if mr_data.info.description:
            formatted_diffs.append(f"**Description:** {mr_data.info.description}")

        formatted_diffs.append("")
        formatted_diffs.append("## File Changes")

        for diff in mr_data.diffs:
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

    def _get_project_context(self, mr_data: MergeRequestData | None = None) -> str:
        """Get project context for AI review."""
        context_parts = []

        if self.config.language_hint:
            context_parts.append(f"Primary Language: {self.config.language_hint}")

        # Add commit context for better understanding
        if mr_data and mr_data.commits:
            context_parts.append("\n**Commit History:**")
            for commit in mr_data.commits:
                commit_info = f"- `{commit.short_id}` {commit.title}"
                if commit.message != commit.title:
                    # Add full message if it has more details beyond the title
                    commit_info += f"\n  {commit.message.strip()}"
                context_parts.append(commit_info)

        # TODO: Implement additional project context discovery in future iterations
        # - Read .ai_review/project.md
        # - Auto-discover README.md, CONTRIBUTING.md, etc.
        # - Support external context URLs

        return (
            "\n".join(context_parts)
            if context_parts
            else "No additional project context available."
        )

    def _create_mock_review(self) -> CodeReview:
        """Create mock review for dry-run mode."""
        mock_content = """## AI Code Review

### 📋 MR Summary
[DRY RUN] Mock merge request for testing purposes.

- **Key Changes:** Mock code modifications for testing
- **Impact:** Testing environment only, no production impact
- **Risk Level:** Low - Mock changes for development testing

### Detailed Code Review

[DRY RUN] Mock code review generated. This would be replaced with actual AI feedback in real execution.

### ✅ Summary
- **Overall Assessment:** [MOCK] Good code quality for testing
- **Priority Issues:** [MOCK] No critical issues identified
- **Minor Suggestions:** [MOCK] Consider adding more comprehensive tests"""

        return CodeReview(
            general_feedback=mock_content,
            file_reviews=[],
            overall_assessment="Mock assessment for testing purposes",
            priority_issues=["[MOCK] Example priority issue"],
            minor_suggestions=["[MOCK] Example minor suggestion"],
        )

    def _create_mock_summary(self, mr_data: MergeRequestData) -> ReviewSummary:
        """Create mock summary for dry-run mode."""
        return ReviewSummary(
            title=f"[DRY RUN] {mr_data.info.title}",
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

    async def post_review_to_gitlab(
        self,
        project_id: str | int,
        mr_iid: int,
        review_result: ReviewResult,
    ) -> dict[str, str]:
        """Post generated review as a note/comment to GitLab MR.

        Args:
            project_id: GitLab project ID or path (e.g., 'group/project')
            mr_iid: Merge request IID
            review_result: The review result to post

        Returns:
            Dictionary containing note information (id, url, etc.)

        Raises:
            GitLabAPIError: If posting fails
        """
        logger.info(
            "Posting review to GitLab",
            project_id=project_id,
            mr_iid=mr_iid,
            dry_run=self.config.dry_run,
        )

        # Format review content as markdown
        review_content = review_result.to_markdown()

        # Add footer with metadata
        footer = self._create_review_footer()
        full_content = f"{review_content}\n\n{footer}"

        # Post to GitLab (handles dry-run internally)
        note_info = await self.gitlab_client.post_review(
            project_id, mr_iid, full_content
        )

        logger.info(
            "Review posted successfully",
            note_id=note_info["id"],
            note_url=note_info["url"],
            dry_run=self.config.dry_run,
        )

        return note_info

    def _create_review_footer(self) -> str:
        """Create footer with review metadata."""
        footer_parts = [
            "---",
            "🤖 **AI Code Review** | Generated with ai-code-review",
            f"**Provider:** {self.config.ai_provider.value} | **Model:** {self.config.ai_model}",
        ]

        if self.config.dry_run:
            footer_parts.append("**Mode:** DRY RUN - No actual changes were analyzed")

        return "\n".join(footer_parts)
