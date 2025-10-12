"""Tests for CI documentation section."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from context_generator.models import CIDocsConfig
from context_generator.sections.ci_docs_section import CIDocsSection
from context_generator.utils.helpers import extract_ci_system


class TestCIDocsSection:
    """Test CIDocsSection functionality."""

    @pytest.fixture
    def config(self) -> CIDocsConfig:
        """Create test configuration."""
        return CIDocsConfig(enabled=True, timeout_seconds=30, max_content_length=100000)

    @pytest.fixture
    def llm_analyzer(self) -> MagicMock:
        """Create mock LLM analyzer."""
        analyzer = MagicMock()
        analyzer.call_llm = AsyncMock(return_value="Generated CI documentation")
        return analyzer

    @pytest.fixture
    def section(self, llm_analyzer: MagicMock, config: CIDocsConfig) -> CIDocsSection:
        """Create section instance."""
        return CIDocsSection(llm_analyzer, config)

    def test_init(
        self, section: CIDocsSection, llm_analyzer: MagicMock, config: CIDocsConfig
    ) -> None:
        """Test section initialization."""
        assert section.llm_analyzer == llm_analyzer
        assert section.config == config
        assert section.provider is not None
        assert section.name == "ci_docs"

    def test_get_template_key(self, section: CIDocsSection) -> None:
        """Test template key."""
        assert section.get_template_key() == "ci_docs_analysis"

    @pytest.mark.asyncio
    async def test_generate_content_disabled(
        self, section: CIDocsSection, llm_analyzer: MagicMock
    ) -> None:
        """Test content generation when disabled."""
        section.config.enabled = False
        facts = {"tech_indicators": {"ci_cd": ["gitlab-ci"]}}

        result = await section.generate_content(facts, {})

        assert result == ""
        llm_analyzer.call_llm.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_content_no_ci_system(
        self, section: CIDocsSection, llm_analyzer: MagicMock
    ) -> None:
        """Test content generation when no CI system detected."""
        facts: dict[str, Any] = {"tech_indicators": {"ci_cd": []}}

        result = await section.generate_content(facts, {})

        assert result == ""
        llm_analyzer.call_llm.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_content_success(self, section: CIDocsSection) -> None:
        """Test successful content generation."""
        facts = {"tech_indicators": {"ci_cd": ["gitlab-ci"]}}

        mock_docs = {
            "yaml": "# YAML documentation",
            "variables": "# Variables documentation",
        }

        with patch.object(
            section.provider, "fetch_ci_documentation", return_value=mock_docs
        ):
            result = await section.generate_content(facts, {})

            assert result != ""
            assert isinstance(result, str)
            # Should have called the LLM
            section.llm_analyzer.call_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_content_no_docs_fetched(
        self, section: CIDocsSection, llm_analyzer: MagicMock
    ) -> None:
        """Test when no documentation is fetched."""
        facts = {"tech_indicators": {"ci_cd": ["gitlab-ci"]}}

        with patch.object(section.provider, "fetch_ci_documentation", return_value={}):
            result = await section.generate_content(facts, {})

            assert result == ""
            llm_analyzer.call_llm.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_content_llm_failure_uses_fallback(
        self, section: CIDocsSection
    ) -> None:
        """Test fallback content when LLM fails."""
        facts = {"tech_indicators": {"ci_cd": ["gitlab-ci"]}}
        mock_docs = {"yaml": "# YAML documentation"}

        # Make LLM fail
        section.llm_analyzer.call_llm.side_effect = Exception("LLM error")

        with patch.object(
            section.provider, "fetch_ci_documentation", return_value=mock_docs
        ):
            result = await section.generate_content(facts, {})

            # Should return fallback content
            assert result != ""
            assert "gitlab-ci" in result.lower()
            # Fallback content contains "Configuration Guide"
            assert "configuration guide" in result.lower()

    def test_extract_ci_system_gitlab(self, section: CIDocsSection) -> None:
        """Test extracting GitLab CI system."""
        facts = {"tech_indicators": {"ci_cd": ["gitlab-ci"]}}

        result = extract_ci_system(facts)

        assert result == "gitlab-ci"

    def test_extract_ci_system_github(self, section: CIDocsSection) -> None:
        """Test extracting GitHub Actions system."""
        facts = {"tech_indicators": {"ci_cd": ["github-actions"]}}

        result = extract_ci_system(facts)

        assert result == "github-actions"

    def test_extract_ci_system_none(self, section: CIDocsSection) -> None:
        """Test when no CI system is detected."""
        facts: dict[str, Any] = {"tech_indicators": {"ci_cd": []}}

        result = extract_ci_system(facts)

        assert result is None

    def test_extract_ci_system_no_tech_indicators(self, section: CIDocsSection) -> None:
        """Test when tech_indicators missing."""
        facts: dict[str, Any] = {}

        result = extract_ci_system(facts)

        assert result is None

    def test_extract_ci_system_first_only(self, section: CIDocsSection) -> None:
        """Test that only first CI system is returned."""
        facts = {"tech_indicators": {"ci_cd": ["gitlab-ci", "github-actions"]}}

        result = extract_ci_system(facts)

        assert result == "gitlab-ci"

    @pytest.mark.asyncio
    async def test_generate_ci_docs_content_success(
        self, section: CIDocsSection
    ) -> None:
        """Test LLM content generation."""
        docs = {"yaml": "# Documentation"}

        result = await section._generate_ci_docs_content("gitlab-ci", docs)

        assert result == "Generated CI documentation"
        section.llm_analyzer.call_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_ci_docs_content_llm_error(
        self, section: CIDocsSection
    ) -> None:
        """Test LLM error handling."""
        docs = {"yaml": "# Documentation"}
        section.llm_analyzer.call_llm.side_effect = Exception("LLM error")

        result = await section._generate_ci_docs_content("gitlab-ci", docs)

        assert result is None

    def test_create_ci_docs_prompt(self, section: CIDocsSection) -> None:
        """Test prompt creation."""
        docs = {
            "yaml": "# YAML syntax documentation",
            "variables": "# Variables documentation",
        }

        prompt = section._create_ci_docs_prompt("gitlab-ci", docs)

        assert "gitlab-ci" in prompt
        assert "YAML" in prompt.upper()
        assert "variables" in prompt.lower()
        assert "Configuration Guide" in prompt

    def test_generate_fallback_content(self, section: CIDocsSection) -> None:
        """Test fallback content generation."""
        docs = {
            "yaml": "x" * 1000,
            "variables": "y" * 500,
        }

        result = section._generate_fallback_content("gitlab-ci", docs)

        assert "gitlab-ci" in result.lower()
        assert "configuration guide" in result.lower()
        assert "yaml" in result.lower()
        assert "1000" in result  # Length of yaml content

    def test_has_generate_content_method(self, section: CIDocsSection) -> None:
        """Test that section has generate_content method."""
        # Verify the section implements the base interface
        assert hasattr(section, "generate_content")
        assert callable(section.generate_content)
