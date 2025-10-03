"""Simple tests for LLM analyzer functionality."""

from __future__ import annotations

from ai_code_review.models.config import Config
from context_generator.core.llm_analyzer import SpecializedLLMAnalyzer


class TestSpecializedLLMAnalyzerSimple:
    """Simple tests for SpecializedLLMAnalyzer functionality."""

    def test_init_ollama(self) -> None:
        """Test initialization with Ollama provider."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            ai_model="llama3.2",
        )

        analyzer = SpecializedLLMAnalyzer(config)
        assert analyzer.config == config
        assert analyzer._provider is not None

    def test_get_system_prompt(self) -> None:
        """Test _get_system_prompt method."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            ai_model="llama3.2",
        )

        analyzer = SpecializedLLMAnalyzer(config)
        prompt = analyzer._get_system_prompt()

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "code review" in prompt.lower()

    def test_generate_dry_run_response_overview(self) -> None:
        """Test _generate_dry_run_response for overview section."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            ai_model="llama3.2",
        )

        analyzer = SpecializedLLMAnalyzer(config)
        response = analyzer._generate_dry_run_response(
            "overview", "Analyze this project"
        )

        assert isinstance(response, str)
        assert len(response) > 0

    def test_generate_dry_run_response_structure(self) -> None:
        """Test _generate_dry_run_response for structure section."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            ai_model="llama3.2",
        )

        analyzer = SpecializedLLMAnalyzer(config)
        response = analyzer._generate_dry_run_response("structure", "Analyze structure")

        assert isinstance(response, str)
        assert len(response) > 0

    def test_generate_dry_run_response_tech_stack(self) -> None:
        """Test _generate_dry_run_response for tech_stack section."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            ai_model="llama3.2",
        )

        analyzer = SpecializedLLMAnalyzer(config)
        response = analyzer._generate_dry_run_response(
            "tech_stack", "Analyze tech stack"
        )

        assert isinstance(response, str)
        assert len(response) > 0

    def test_generate_dry_run_response_review_focus(self) -> None:
        """Test _generate_dry_run_response for review_focus section."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            ai_model="llama3.2",
        )

        analyzer = SpecializedLLMAnalyzer(config)
        response = analyzer._generate_dry_run_response(
            "review_focus", "Analyze review focus"
        )

        assert isinstance(response, str)
        assert len(response) > 0

    def test_generate_dry_run_response_default(self) -> None:
        """Test _generate_dry_run_response for unknown section."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            ai_model="llama3.2",
        )

        analyzer = SpecializedLLMAnalyzer(config)
        response = analyzer._generate_dry_run_response("unknown", "Analyze something")

        assert isinstance(response, str)
        assert len(response) > 0
