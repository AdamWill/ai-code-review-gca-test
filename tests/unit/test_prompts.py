"""Unit tests for prompt generation functions."""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from ai_code_review.models.config import AIProvider, Config, PlatformProvider
from ai_code_review.utils.prompts import (
    create_review_chain,
    create_review_prompt,
    create_system_prompt,
)


class TestPromptGeneration:
    """Test suite for prompt generation functions."""

    def test_create_system_prompt_default(self) -> None:
        """Test creating default system prompt with MR summary."""
        prompt = create_system_prompt()

        assert "## AI Code Review" in prompt
        assert "### 📋 MR Summary" in prompt
        assert "expert senior software engineer" in prompt
        assert "CRITICAL FORMAT REQUIREMENTS" in prompt

    def test_create_system_prompt_no_mr_summary(self) -> None:
        """Test creating system prompt without MR summary."""
        prompt = create_system_prompt(include_mr_summary=False)

        assert "## AI Code Review" in prompt
        assert "### 📋 MR Summary" not in prompt
        assert "### Detailed Code Review" in prompt

    def test_create_system_prompt_local_mode(self) -> None:
        """Test creating system prompt for local mode."""
        prompt = create_system_prompt(local_mode=True)

        assert "## Local Code Review" in prompt
        assert "### 🔍 Code Analysis" in prompt
        assert "### 📋 MR Summary" not in prompt
        assert "### 📂 File Reviews" in prompt

    def test_create_review_prompt_default(self) -> None:
        """Test creating default review prompt template."""
        template = create_review_prompt()

        assert isinstance(template, ChatPromptTemplate)
        # The template should have system and user messages
        assert len(template.messages) >= 1

    def test_create_review_prompt_local_mode(self) -> None:
        """Test creating review prompt template for local mode."""
        template = create_review_prompt(local_mode=True)

        assert isinstance(template, ChatPromptTemplate)
        # Should use local format example

    def test_create_review_prompt_compact_mode(self) -> None:
        """Test creating compact review prompt template."""
        template = create_review_prompt(include_mr_summary=False)

        assert isinstance(template, ChatPromptTemplate)

    def test_create_review_chain_normal_config(self) -> None:
        """Test creating review chain with normal configuration."""
        # Mock LLM
        mock_llm = MockLLM()

        # Create config for GitLab
        config = Config(
            platform_provider=PlatformProvider.GITLAB,
            ai_provider=AIProvider.OLLAMA,
            gitlab_token="test_token",
        )

        chain = create_review_chain(mock_llm, config)

        # Should be a valid chain object
        assert chain is not None

    def test_create_review_chain_local_config(self) -> None:
        """Test creating review chain with local configuration."""
        # Mock LLM
        mock_llm = MockLLM()

        # Create config for LOCAL
        config = Config(
            platform_provider=PlatformProvider.LOCAL,
            ai_provider=AIProvider.OLLAMA,
        )

        chain = create_review_chain(mock_llm, config)

        # Should be a valid chain object
        assert chain is not None

    def test_system_prompt_includes_local_sections(self) -> None:
        """Test that local mode includes the correct sections."""
        prompt = create_system_prompt(local_mode=True)

        # Should have local-specific sections
        assert "### 🔍 Code Analysis" in prompt
        assert "### 📂 File Reviews" in prompt
        assert "### ✅ Summary" in prompt

        # Should NOT have MR-specific sections
        assert "### 📋 MR Summary" not in prompt
        assert "### Detailed Code Review" not in prompt

    def test_system_prompt_different_formats(self) -> None:
        """Test that different modes produce different prompts."""
        full_prompt = create_system_prompt(include_mr_summary=True, local_mode=False)
        compact_prompt = create_system_prompt(
            include_mr_summary=False, local_mode=False
        )
        local_prompt = create_system_prompt(include_mr_summary=True, local_mode=True)

        # All should be different
        assert full_prompt != compact_prompt
        assert full_prompt != local_prompt
        assert compact_prompt != local_prompt

        # Local should always exclude MR summary regardless of flag
        assert "### 📋 MR Summary" not in local_prompt

    def test_extract_diff_content(self) -> None:
        """Test _extract_diff_content function."""
        from ai_code_review.utils.prompts import _extract_diff_content

        test_input = {"diff": "+ new code\n- old code"}
        result = _extract_diff_content(test_input)

        assert result == "+ new code\n- old code"

    def test_create_language_hint_section_with_language(self) -> None:
        """Test _create_language_hint_section with language provided."""
        from ai_code_review.utils.prompts import _create_language_hint_section

        test_input = {"language": "Python"}
        result = _create_language_hint_section(test_input)

        assert result == "**Primary Language:** Python"

    def test_create_language_hint_section_no_language(self) -> None:
        """Test _create_language_hint_section without language."""
        from ai_code_review.utils.prompts import _create_language_hint_section

        test_input = {}
        result = _create_language_hint_section(test_input)

        assert result == ""

    def test_create_project_context_section_with_context(self) -> None:
        """Test _create_project_context_section with context provided."""
        from ai_code_review.utils.prompts import _create_project_context_section

        test_input = {"context": "This is a Django web application"}
        result = _create_project_context_section(test_input)

        expected_result = """## Project Context & Guidelines

This is a Django web application

IMPORTANT: Apply the above project guidelines and conventions systematically when reviewing the code changes below. Follow the specific patterns, requirements, checklists, and best practices outlined in the context. Reference these guidelines directly in your review and ensure compliance with the established project standards."""
        assert result == expected_result

    def test_create_project_context_section_no_context(self) -> None:
        """Test _create_project_context_section without context."""
        from ai_code_review.utils.prompts import _create_project_context_section

        test_input = {}
        result = _create_project_context_section(test_input)

        assert result == ""

    def test_create_project_context_section_empty_context(self) -> None:
        """Test _create_project_context_section with empty/whitespace context."""
        from ai_code_review.utils.prompts import _create_project_context_section

        test_input = {"context": "   "}
        result = _create_project_context_section(test_input)

        assert result == ""


class MockLLM:
    """Mock LLM for testing."""

    def __call__(self, *args, **kwargs) -> str:
        """Mock LLM call."""
        return "Mock review response"
