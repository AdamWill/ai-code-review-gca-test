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


class MockLLM:
    """Mock LLM for testing."""

    def __call__(self, *args, **kwargs) -> str:
        """Mock LLM call."""
        return "Mock review response"
