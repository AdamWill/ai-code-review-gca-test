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
from ai_code_review.utils.prompts import (
    create_review_chain,
    create_summary_chain,
)

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
        """Generate comprehensive code review for a GitLab MR."""
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

            # Step 2: Generate review using AI
            review = await self._generate_code_review(mr_data)

            # Step 3: Generate summary if requested
            summary = None
            if include_summary:
                summary = await self._generate_summary(mr_data)

            result = ReviewResult(review=review, summary=summary)

            logger.info(
                "Review generation completed successfully",
                has_summary=summary is not None,
            )

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

    async def _generate_code_review(self, mr_data: MergeRequestData) -> CodeReview:
        """Generate detailed code review using AI."""
        if self.config.dry_run:
            logger.info("DRY RUN: Generating mock code review")
            return self._create_mock_review()

        # Check AI provider availability
        if not self.ai_provider.is_available():
            raise AIProviderError(
                f"{self.ai_provider.provider_name} is not available",
                self.ai_provider.provider_name,
            )

        try:
            # Create review chain
            review_chain = create_review_chain(self.ai_provider.client)

            # Prepare input data
            diff_content = self._format_diffs_for_ai(mr_data)

            # Generate review
            logger.debug("Invoking AI for code review", diff_length=len(diff_content))

            review_response = await review_chain.ainvoke(
                {
                    "diff": diff_content,
                    "language": self.config.language_hint,
                    "context": self._get_project_context(),
                }
            )

            # For MVP, we'll use general feedback as the main review
            # TODO: Parse structured response into CodeReview model in future iterations
            return CodeReview(
                general_feedback=review_response,
                file_reviews=[],  # MVP: simplified structure
                overall_assessment="AI Review Generated",
                priority_issues=[],
                minor_suggestions=[],
            )

        except Exception as e:
            raise AIProviderError(
                f"Failed to generate review with {self.ai_provider.provider_name}: {e}",
                self.ai_provider.provider_name,
            ) from e

    async def _generate_summary(self, mr_data: MergeRequestData) -> ReviewSummary:
        """Generate executive summary using AI."""
        if self.config.dry_run:
            logger.info("DRY RUN: Generating mock summary")
            return self._create_mock_summary(mr_data)

        try:
            # Create summary chain
            summary_chain = create_summary_chain(self.ai_provider.client)

            # Prepare input data
            diff_content = self._format_diffs_for_ai(mr_data)

            # Generate summary
            logger.debug("Invoking AI for MR summary", diff_length=len(diff_content))

            summary_response = await summary_chain.ainvoke(
                {
                    "diff": diff_content,
                    "context": self._get_project_context(),
                }
            )

            # For MVP, create a basic summary structure
            # TODO: Parse structured response into ReviewSummary model in future iterations
            return ReviewSummary(
                title=mr_data.info.title,
                key_changes=[],
                modules_affected=[],
                user_impact="To be determined",
                technical_impact=summary_response,
                risk_level="Medium",
                risk_justification="Automated assessment pending detailed analysis",
            )

        except Exception as e:
            raise AIProviderError(
                f"Failed to generate summary with {self.ai_provider.provider_name}: {e}",
                self.ai_provider.provider_name,
            ) from e

    def _format_diffs_for_ai(self, mr_data: MergeRequestData) -> str:
        """Format MR diffs for AI processing."""
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

    def _get_project_context(self) -> str:
        """Get project context for AI review."""
        context_parts = []

        if self.config.language_hint:
            context_parts.append(f"Primary Language: {self.config.language_hint}")

        # TODO: Implement project context discovery in future iterations
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
        return CodeReview(
            general_feedback="[DRY RUN] Mock code review generated. This would be replaced with actual AI feedback in real execution.",
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
