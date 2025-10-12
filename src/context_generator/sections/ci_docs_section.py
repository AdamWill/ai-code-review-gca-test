"""CI/CD Documentation Section for generating CI/CD context."""

from __future__ import annotations

from typing import Any

import structlog

from context_generator.models import CIDocsConfig
from context_generator.providers.ci_docs_provider import CIDocsProvider
from context_generator.sections.base_section import BaseSection
from context_generator.utils.helpers import extract_ci_system

logger = structlog.get_logger(__name__)


class CIDocsSection(BaseSection):
    """Section for generating CI/CD documentation context."""

    def __init__(self, llm_analyzer: Any, config: CIDocsConfig) -> None:
        """Initialize the CI docs section.

        Args:
            llm_analyzer: The LLM analyzer instance
            config: Configuration for CI documentation
        """
        super().__init__("ci_docs")
        self.llm_analyzer = llm_analyzer
        self.config = config
        self.provider = CIDocsProvider(config)

    def get_template_key(self) -> str:
        """Get the template key for this section.

        Returns:
            Template key for CI docs section
        """
        return "ci_docs_analysis"

    async def generate_content(
        self, facts: dict[str, Any], code_samples: dict[str, str]
    ) -> str:
        """Generate CI/CD documentation content.

        Args:
            facts: Project facts
            code_samples: Code samples (not used for CI docs)

        Returns:
            Generated CI/CD documentation content
        """
        logger.info(
            f"CI docs section generate_content called, enabled={self.config.enabled}"
        )

        if not self.config.enabled:
            logger.info("CI docs section disabled, returning empty string")
            return ""

        # Extract CI system from facts
        ci_system = extract_ci_system(facts)
        logger.info(f"Extracted CI system: {ci_system}")

        if not ci_system:
            logger.info("No CI system detected, returning empty string")
            return ""

        try:
            # Fetch official documentation
            docs = await self.provider.fetch_ci_documentation(ci_system)
            if not docs:
                logger.warning(f"No documentation fetched for {ci_system}")
                return ""

            # Generate real content with LLM
            logger.info("Generating CI docs content with LLM")
            llm_content = await self._generate_ci_docs_content(ci_system, docs)
            if llm_content:
                logger.info(f"Generated LLM content: {len(llm_content)} chars")
                return llm_content
            else:
                # Fallback if LLM generation fails
                logger.warning("LLM generation failed, using fallback content")
                fallback_content = self._generate_fallback_content(ci_system, docs)
                logger.info(
                    f"Generated fallback content: {len(fallback_content)} chars"
                )
                return fallback_content

        except Exception as e:
            logger.error(f"Error generating CI docs content: {e}")
            return ""

    async def _generate_ci_docs_content(
        self, ci_system: str, docs: dict[str, str]
    ) -> str | None:
        """Generate CI documentation content using LLM.

        Args:
            ci_system: The CI system name
            docs: Dictionary of documentation content by type

        Returns:
            Generated CI documentation content or None if generation fails
        """
        # Create prompt for LLM
        prompt = self._create_ci_docs_prompt(ci_system, docs)

        # Use the LLM analyzer (respects the configured provider)
        try:
            result = await self.llm_analyzer.call_llm(prompt, "ci_docs_analysis")
            return str(result)
        except Exception as e:
            logger.error(f"Error generating CI docs with LLM: {e}")
            # Return None to trigger fallback
            return None

    def _create_ci_docs_prompt(self, ci_system: str, docs: dict[str, str]) -> str:
        """Create prompt for LLM to generate CI documentation content.

        Args:
            ci_system: The CI system name
            docs: Dictionary of documentation content by type

        Returns:
            Prompt for the LLM
        """
        prompt = f"""You are an expert in {ci_system} CI/CD systems. Analyze the official documentation below and create a comprehensive CI/CD Configuration Guide for code reviewers.

**CRITICAL REQUIREMENTS:**
- Extract SPECIFIC YAML syntax, keywords, and configuration examples
- Focus on PRACTICAL information for code reviews
- Include COMMON MISTAKES and how to avoid them
- Provide ACTIONABLE insights for reviewers

**Documentation provided:**
"""

        # Include relevant portions of each documentation type
        for doc_type, content in docs.items():
            # Limit content to avoid token limits, but include key sections
            preview_length = self.config.prompt_content_preview_length
            content_preview = (
                content[:preview_length] if len(content) > preview_length else content
            )
            prompt += f"\n**{doc_type.upper()} DOCUMENTATION:**\n{content_preview}\n"

        prompt += f"""

**Your task:**
Create a focused "CI/CD Recent Changes & Critical Updates" guide for {ci_system} that highlights information LLMs need for accurate code reviews:

## 1. Recent Changes & New Features (Last 2-3 Years)
- **CRITICAL**: Focus on NEW keywords, syntax, or features introduced recently
- Highlight improvements that LLMs might not know about
- Include version-specific changes that affect configuration
- New capabilities that replace older approaches

## 2. Deprecated & Removed Features
- **CRITICAL**: List features that are deprecated, removed, or no longer recommended
- Show what has been replaced and how to migrate
- Highlight syntax that no longer works or is discouraged
- Version-specific deprecations and removal timelines

## 3. Security Updates & Vulnerabilities
- Recent security-related changes in {ci_system}
- New security features or requirements
- Common security misconfigurations to watch for
- Changes in secret management or permissions

## 4. Breaking Changes & Migration Issues
- Configuration changes that break existing setups
- Common migration problems and solutions
- Syntax changes that cause failures
- Environment or dependency changes

## 5. Common Configuration Errors
- **CRITICAL**: Specific mistakes that cause pipeline failures
- Syntax errors that are easy to miss
- Configuration patterns that don't work as expected
- Troubleshooting common issues

**IMPORTANT**:
- **PRIORITIZE RECENT CHANGES**: Focus on information from the last 2-3 years that LLMs might not know
- **SKIP BASIC SYNTAX**: Don't explain basic YAML syntax or well-known features
- **HIGHLIGHT DEPRECATIONS**: Emphasize what no longer works or is discouraged
- **INCLUDE MIGRATION PATHS**: Show how to update old configurations
- **FOCUS ON FAILURES**: Highlight what causes pipelines to break
- Use ONLY information from the provided documentation
- Include specific YAML examples for new/deprecated features
- Aim for approximately 2000-2500 words total (highly focused on recent changes)

Format as clean markdown that can be directly included in a project context file.
"""

        return prompt

    def _generate_fallback_content(self, ci_system: str, docs: dict[str, str]) -> str:
        """Generate fallback content when LLM is not available.

        Args:
            ci_system: The CI system name
            docs: Dictionary of documentation content by type

        Returns:
            Fallback CI documentation content
        """
        content = f"### CI/CD Configuration Guide - {ci_system.upper()}\n\n"
        content += f"This project uses **{ci_system}** for continuous integration and deployment.\n\n"

        content += "#### Available Documentation\n\n"
        for doc_type, doc_content in docs.items():
            content += f"**{doc_type.title()}**: {len(doc_content)} characters of official documentation\n"

        content += "\n#### Key Information\n\n"
        content += (
            "- Official documentation has been fetched and is available for reference\n"
        )
        content += (
            "- Review CI/CD configuration files for compliance with best practices\n"
        )
        content += "- Check for proper use of variables, stages, and job dependencies\n"

        return content
