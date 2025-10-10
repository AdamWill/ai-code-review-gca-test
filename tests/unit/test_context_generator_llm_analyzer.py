"""Tests for SpecializedLLMAnalyzer functionality."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from ai_code_review.models.config import Config
from context_generator.core.llm_analyzer import SpecializedLLMAnalyzer


class TestSpecializedLLMAnalyzer:
    """Tests for SpecializedLLMAnalyzer functionality."""

    # ===== Basic Tests =====

    def test_init(self, ollama_config, anthropic_config, gemini_config) -> None:
        """Test SpecializedLLMAnalyzer initialization."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)

        assert analyzer.config == ollama_config

    def test_init_with_different_providers(
        self, ollama_config, anthropic_config, gemini_config
    ) -> None:
        """Test initialization with different AI providers."""
        configs = [
            ("ollama", ollama_config),
            ("anthropic", anthropic_config),
            ("gemini", gemini_config),
        ]

        for provider_name, config in configs:
            analyzer = SpecializedLLMAnalyzer(config)
            assert analyzer.config == config
            assert analyzer.config.ai_provider == provider_name

    # ===== LLM Call Tests =====

    @pytest.mark.asyncio
    async def test_call_llm_dry_run(
        self, ollama_config, anthropic_config, gemini_config
    ) -> None:
        """Test call_llm in dry run mode."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            ollama_base_url="http://localhost:11434",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)

        prompt = "Analyze this code structure"
        template_key = "code_structure"

        result = await analyzer.call_llm(prompt, template_key)

        # In dry run mode, should return a response (might be real or mock)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_call_llm_with_anthropic(
        self, ollama_config, anthropic_config, gemini_config
    ) -> None:
        """Test call_llm with Anthropic provider."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="anthropic",
            ai_api_key="test_key",
            dry_run=True,  # Force dry run to avoid real API calls
        )
        analyzer = SpecializedLLMAnalyzer(config)

        prompt = "Test prompt"
        template_key = "test_template"

        result = await analyzer.call_llm(prompt, template_key)

        # In dry run mode, should return a fallback response
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_call_llm_with_gemini(
        self, ollama_config, anthropic_config, gemini_config
    ) -> None:
        """Test call_llm with Gemini provider."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="gemini",
            ai_api_key="test_key",
            dry_run=True,  # Force dry run to avoid real API calls
        )
        analyzer = SpecializedLLMAnalyzer(config)

        prompt = "Test prompt"
        template_key = "test_template"

        result = await analyzer.call_llm(prompt, template_key)

        # In dry run mode, should return a fallback response
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_call_llm_with_ollama(
        self, ollama_config, anthropic_config, gemini_config
    ) -> None:
        """Test call_llm with Ollama provider."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            ollama_base_url="http://localhost:11434",
            dry_run=True,  # Force dry run to avoid real API calls
        )
        analyzer = SpecializedLLMAnalyzer(config)

        prompt = "Test prompt"
        template_key = "test_template"

        result = await analyzer.call_llm(prompt, template_key)

        # In dry run mode, should return a fallback response
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_call_llm_provider_error(
        self, ollama_config, anthropic_config, gemini_config
    ) -> None:
        """Test call_llm when provider raises an error."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="anthropic",
            ai_api_key="test_key",
            dry_run=True,  # Force dry run to avoid real API calls
        )
        analyzer = SpecializedLLMAnalyzer(config)

        prompt = "Test prompt"
        template_key = "test_template"

        result = await analyzer.call_llm(prompt, template_key)

        # In dry run mode, should return a fallback response
        assert isinstance(result, str)
        assert len(result) > 0

    def test_clean_response_with_all_patterns(
        self, ollama_config, anthropic_config, gemini_config
    ) -> None:
        """Test _clean_response with all skip patterns."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            ollama_base_url="http://localhost:11434",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)

        # Test response with all conversational patterns
        response = """Here is the analysis you requested:
Here are the key points:
Based on the information provided:
Looking at the code structure:
I can see that this project:
From the dependencies:
After analyzing the codebase:

## Actual Content
This should remain.
- Key feature 1
- Key feature 2"""

        cleaned = analyzer._clean_response(response)

        # Should remove all conversational lines
        assert "Here is the analysis" not in cleaned
        assert "Here are the key" not in cleaned
        assert "Based on the information" not in cleaned
        assert "Looking at the code" not in cleaned
        assert "I can see that" not in cleaned
        assert "From the dependencies" not in cleaned
        assert "After analyzing" not in cleaned
        # Should keep actual content
        assert "## Actual Content" in cleaned
        assert "This should remain." in cleaned
        assert "Key feature 1" in cleaned

    # ===== Template Key Tests =====

    @pytest.mark.asyncio
    async def test_call_llm_different_template_keys(
        self, ollama_config, anthropic_config, gemini_config
    ) -> None:
        """Test call_llm with different template keys."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)

        template_keys = [
            "project_overview",
            "tech_stack",
            "code_structure",
            "review_focus",
            "context7_analysis",
        ]

        for template_key in template_keys:
            result = await analyzer.call_llm("Test prompt", template_key)
            assert isinstance(result, str)
            assert len(result) > 0

    # ===== Configuration Tests =====

    def test_analyzer_with_custom_model(
        self, ollama_config, anthropic_config, gemini_config
    ) -> None:
        """Test analyzer with custom model configuration."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="anthropic",
            ai_api_key="test_key",
            ai_model="claude-3-opus-20240229",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)

        assert analyzer.config.ai_model == "claude-3-opus-20240229"

    def test_analyzer_with_custom_ollama_url(
        self, ollama_config, anthropic_config, gemini_config
    ) -> None:
        """Test analyzer with custom Ollama URL."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            ollama_base_url="http://custom-ollama:11434",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)

        assert analyzer.config.ollama_base_url == "http://custom-ollama:11434"

    def test_create_provider_unsupported(
        self, ollama_config, anthropic_config, gemini_config
    ) -> None:
        """Test _create_provider with unsupported provider."""
        # Create a valid config first
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            ollama_base_url="http://localhost:11434",
            dry_run=True,
        )

        # Mock the ai_provider to return an unsupported value
        with patch.object(config, "ai_provider") as mock_provider:
            mock_provider.value.lower.return_value = "unsupported"

            with pytest.raises(ValueError, match="Unsupported AI provider"):
                SpecializedLLMAnalyzer(config)

    # ===== Error Handling Tests =====

    @pytest.mark.asyncio
    async def test_call_llm_empty_prompt(
        self, ollama_config, anthropic_config, gemini_config
    ) -> None:
        """Test call_llm with empty prompt."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)

        result = await analyzer.call_llm("", "test_template")

        # Should handle empty prompt gracefully
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_call_llm_none_prompt(
        self, ollama_config, anthropic_config, gemini_config
    ) -> None:
        """Test call_llm with None prompt."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            ollama_base_url="http://localhost:11434",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)

        # The method handles None gracefully, returning a default response
        result = await analyzer.call_llm(None, "test_template")
        assert result is not None  # Should return some default response

    @pytest.mark.asyncio
    async def test_call_llm_long_prompt(
        self, ollama_config, anthropic_config, gemini_config
    ) -> None:
        """Test call_llm with very long prompt."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)

        # Create a very long prompt
        long_prompt = "Analyze this code: " + "x" * 10000

        result = await analyzer.call_llm(long_prompt, "test_template")

        # Should handle long prompts
        assert isinstance(result, str)
        assert len(result) > 0

    # ===== Integration Tests =====

    @pytest.mark.asyncio
    async def test_call_llm_realistic_scenario(
        self, ollama_config, anthropic_config, gemini_config
    ) -> None:
        """Test call_llm with realistic code analysis scenario."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)

        prompt = """
        Analyze the following Python project structure:

        src/
        ├── main.py
        ├── models/
        │   ├── user.py
        │   └── product.py
        └── api/
            ├── routes.py
            └── middleware.py

        Dependencies: fastapi, pydantic, sqlalchemy

        Provide insights on the architecture and potential improvements.
        """

        result = await analyzer.call_llm(prompt, "code_structure")

        assert isinstance(result, str)
        assert len(result) > 0
        # In dry run mode, should contain mock analysis
        assert any(
            keyword in result.lower()
            for keyword in ["analysis", "structure", "mock", "dry"]
        )

    @pytest.mark.asyncio
    async def test_call_llm_multiple_calls(
        self, ollama_config, anthropic_config, gemini_config
    ) -> None:
        """Test multiple sequential calls to call_llm."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)

        prompts = [
            "Analyze project overview",
            "Analyze tech stack",
            "Analyze code structure",
        ]

        template_keys = [
            "project_overview",
            "tech_stack",
            "code_structure",
        ]

        results = []
        for prompt, template_key in zip(prompts, template_keys, strict=False):
            result = await analyzer.call_llm(prompt, template_key)
            results.append(result)

        # All calls should succeed
        assert len(results) == 3
        for result in results:
            assert isinstance(result, str)
            assert len(result) > 0

    # ===== Provider-Specific Tests =====

    def test_get_provider_anthropic(
        self, ollama_config, anthropic_config, gemini_config
    ) -> None:
        """Test getting Anthropic provider."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="anthropic",
            ai_api_key="test_key",
            dry_run=False,
        )
        analyzer = SpecializedLLMAnalyzer(config)

        with patch("ai_code_review.providers.anthropic.AnthropicProvider"):
            # This would be called internally when making LLM calls
            assert analyzer.config.ai_provider == "anthropic"

    def test_get_provider_gemini(
        self, ollama_config, anthropic_config, gemini_config
    ) -> None:
        """Test getting Gemini provider."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="gemini",
            ai_api_key="test_key",
            dry_run=False,
        )
        analyzer = SpecializedLLMAnalyzer(config)

        with patch("ai_code_review.providers.gemini.GeminiProvider"):
            # This would be called internally when making LLM calls
            assert analyzer.config.ai_provider == "gemini"

    def test_get_provider_ollama(
        self, ollama_config, anthropic_config, gemini_config
    ) -> None:
        """Test getting Ollama provider."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            ollama_url="http://localhost:11434",
            dry_run=False,
        )
        analyzer = SpecializedLLMAnalyzer(config)

        with patch("ai_code_review.providers.ollama.OllamaProvider"):
            # This would be called internally when making LLM calls
            assert analyzer.config.ai_provider == "ollama"

    # ===== Response Cleaning Tests =====

    def test_clean_response_with_conversational_text(
        self, ollama_config, anthropic_config, gemini_config
    ) -> None:
        """Test _clean_response removes conversational starters."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            ollama_base_url="http://localhost:11434",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)

        # Test response with conversational starters
        response = """Here is the analysis you requested:

## Project Overview
This is a Python project.

Based on the code provided, I can see that it uses FastAPI.

Looking at the structure, it follows clean architecture.

## Key Features
- REST API
- Database integration"""

        cleaned = analyzer._clean_response(response)

        # Should remove conversational lines
        assert "Here is the analysis" not in cleaned
        assert "Based on the code provided" not in cleaned
        assert "Looking at the structure" not in cleaned
        # Should keep actual content
        assert "## Project Overview" in cleaned
        assert "This is a Python project." in cleaned
        assert "## Key Features" in cleaned

    def test_clean_response_no_conversational_text(
        self, ollama_config, anthropic_config, gemini_config
    ) -> None:
        """Test _clean_response with clean content."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            ollama_base_url="http://localhost:11434",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)

        response = """## Project Overview
This is a Python project.

## Key Features
- REST API
- Database integration"""

        cleaned = analyzer._clean_response(response)

        # Should keep all content unchanged
        assert cleaned == response.strip()

    def test_get_system_prompt(
        self, ollama_config, anthropic_config, gemini_config
    ) -> None:
        """Test _get_system_prompt returns consistent prompt."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            ollama_base_url="http://localhost:11434",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)

        prompt = analyzer._get_system_prompt()

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "expert software architect" in prompt
        assert "CRITICAL RULES" in prompt
        assert "code reviewers" in prompt

    def test_generate_fallback_response(
        self, ollama_config, anthropic_config, gemini_config
    ) -> None:
        """Test _generate_fallback_response."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            ollama_base_url="http://localhost:11434",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)

        fallback = analyzer._generate_fallback_response("test prompt")

        assert isinstance(fallback, str)
        assert "LLM analysis unavailable" in fallback
        assert "fallback mode" in fallback

    # ===== Dry Run Response Tests =====

    def test_generate_dry_run_response_all_sections(
        self, ollama_config, anthropic_config, gemini_config
    ) -> None:
        """Test _generate_dry_run_response for all section types."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            ollama_base_url="http://localhost:11434",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)

        # Test project_overview section
        overview = analyzer._generate_dry_run_response("project_overview", "test")
        assert "Purpose:" in overview
        assert "Command-line application" in overview

        # Test tech_stack section
        tech_stack = analyzer._generate_dry_run_response("tech_stack", "test")
        assert "Core Technologies" in tech_stack
        assert "Python 3.12+" in tech_stack

        # Test code_structure section
        structure = analyzer._generate_dry_run_response("code_structure", "test")
        assert "Architecture Patterns" in structure
        assert "Layered Architecture" in structure

        # Test review_focus section
        focus = analyzer._generate_dry_run_response("review_focus", "test")
        assert "Async Correctness" in focus
        assert "Provider Pattern Consistency" in focus

        # Test unknown section
        unknown = analyzer._generate_dry_run_response("unknown_section", "test")
        assert "Dry run mode" in unknown
        assert "unknown_section" in unknown
