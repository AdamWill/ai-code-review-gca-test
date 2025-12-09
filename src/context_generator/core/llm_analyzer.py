"""Specialized LLM analyzer for focused context generation."""

from __future__ import annotations

from typing import Any

import structlog
from langchain_core.messages import HumanMessage, SystemMessage

from ai_code_review.models.config import Config
from ai_code_review.providers.anthropic import AnthropicProvider
from ai_code_review.providers.gemini import GeminiProvider
from ai_code_review.providers.ollama import OllamaProvider

logger = structlog.get_logger(__name__)

# Type alias for LangChain AIMessage.content
# See: https://api.python.langchain.com/en/latest/messages/langchain_core.messages.ai.AIMessage.html
MessageContent = str | list[str | dict[str, Any]]


class SpecializedLLMAnalyzer:
    """Handles multiple specialized LLM calls with focused prompts."""

    def __init__(self, config: Config) -> None:
        """Initialize LLM analyzer."""
        self.config = config
        self._provider = self._create_provider()

    def _create_provider(
        self,
    ) -> AnthropicProvider | GeminiProvider | OllamaProvider:
        """Create appropriate AI provider based on config."""
        ai_provider = self.config.ai_provider.value.lower()

        if ai_provider == "anthropic":
            return AnthropicProvider(self.config)
        elif ai_provider == "gemini":
            return GeminiProvider(self.config)
        elif ai_provider == "ollama":
            return OllamaProvider(self.config)
        else:
            raise ValueError(f"Unsupported AI provider: {self.config.ai_provider}")

    async def call_llm(self, prompt: str, section_key: str = "") -> str:
        """Make single focused LLM call with consistent system prompt."""
        if self.config.dry_run:
            return self._generate_dry_run_response(section_key, prompt)

        try:
            messages = [
                SystemMessage(content=self._get_system_prompt()),
                HumanMessage(content=prompt),
            ]

            response = await self._provider.client.ainvoke(messages)
            # Handle different response content types from various LLM providers
            content = self._extract_content_from_response(response.content)

            logger.debug(
                "LLM call completed successfully",
                provider=self._provider.provider_name,
                prompt_length=len(prompt),
                response_length=len(content),
            )

            return content

        except Exception as e:
            logger.error(
                "LLM call failed", error=str(e), provider=self._provider.provider_name
            )
            return self._generate_fallback_response(prompt)

    def _get_system_prompt(self) -> str:
        """Consistent system prompt for all context generation calls."""
        return """You are an expert software architect creating project context for AI code reviewers.

Your role is to analyze project information and provide focused insights that help code reviewers understand:
- What the project does and how it works
- Key technologies and architectural patterns
- Important files and components
- Specific areas to focus on during code review

CRITICAL RULES:
1. Follow the EXACT format requested in each prompt
2. Be specific and factual, never generic or vague
3. Base all conclusions on the actual data provided
4. Focus on information that helps understand code changes
5. Return ONLY the requested content, no conversational text or explanations
6. If you see actual code samples, analyze them for real patterns
7. Prioritize information that affects code review quality

Your output will be used by AI systems reviewing code changes, so accuracy and relevance are essential."""

    def _extract_content_from_response(self, content: MessageContent) -> str:
        """Extract text content from various LLM response formats.

        Different LLM providers and versions return content in different formats:
        - Simple string: "text content"
        - List of content blocks: [{'type': 'text', 'text': '...', 'extras': {...}}]
        - List of strings: ['part1', 'part2']

        This method normalizes all formats to a clean string.

        Args:
            content: Raw content from LLM AIMessage.content (str or list)

        Returns:
            Extracted and cleaned text content
        """
        # Most common case: simple string response
        if isinstance(content, str):
            return self._clean_response(content)

        # Handle list of content blocks (e.g., from newer langchain-google-genai)
        # content is list[str | dict[str, Any]] at this point
        text_parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                text_parts.append(block)
            else:
                # block is dict[str, Any] - extract text field (Gemini format)
                if "text" in block:
                    text_parts.append(str(block["text"]))
                # Fallback: try to get 'content' field
                elif "content" in block:
                    text_parts.append(str(block["content"]))
                else:
                    # Unknown dict format, skip extras/metadata
                    logger.debug(
                        "Skipping unknown dict block",
                        keys=list(block.keys()),
                    )

        combined_text = "\n".join(text_parts)
        return self._clean_response(combined_text)

    def _clean_response(self, content: str) -> str:
        """Clean LLM response of unwanted conversational text."""
        # Remove common conversational starters
        content = content.strip()

        # Remove lines that start with conversational phrases
        lines = content.split("\n")
        cleaned_lines = []

        skip_patterns = [
            "Here is",
            "Here are",
            "Based on the",
            "Looking at",
            "I can see",
            "From the",
            "After analyzing",
        ]

        for line in lines:
            line_stripped = line.strip()

            # Skip conversational opening lines
            if any(line_stripped.startswith(pattern) for pattern in skip_patterns):
                continue

            cleaned_lines.append(line)

        return "\n".join(cleaned_lines).strip()

    def _generate_dry_run_response(self, section_key: str, prompt: str) -> str:
        """Generate mock response for dry run mode based on section key."""
        # Use section key for precise matching instead of prompt content
        if section_key == "project_overview":
            return """**Purpose:** Code review and analysis tool using AI providers
**Type:** Command-line application
**Domain:** Software development and code quality
**Key Dependencies:** langchain, pydantic, click, aiohttp"""

        elif section_key == "tech_stack":
            return """### Core Technologies
- **Primary Language:** Python 3.12+
- **Framework/Runtime:** AsyncIO-based CLI application
- **Architecture Pattern:** Clean Architecture with provider pattern

### Key Dependencies (for Context7 & API Understanding)
- **langchain>=0.2.0** - LLM orchestration and provider abstraction
- **pydantic>=2.5.0** - Data validation and configuration management
- **click>=8.1.0** - Command-line interface framework
- **aiohttp>=3.9.0** - Async HTTP client for API communication

### Development Tools & CI/CD
- **Testing:** pytest with coverage requirements (75%+)
- **Code Quality:** ruff (linting/formatting), mypy (strict type checking)
- **Build/Package:** uv (modern Python package manager)
- **CI/CD:** GitLab CI with automated quality gates and container builds"""

        elif section_key == "code_structure":
            return """### Architecture Patterns
**Code Organization:** The project follows a Layered Architecture with clear separation of concerns. It uses a pluggable provider pattern for external services.
**Key Components:**
- **CLI (`cli.py`):** The presentation layer, built with `click`. It handles user input, configuration loading, and initializes the core engine.
- **ReviewEngine (`review_engine.py`):** The core application logic. It orchestrates interactions between platform clients and AI providers to perform code reviews.
- **Configuration (`models/config.py`):** A centralized configuration model using Pydantic's `BaseSettings` for type-safe settings management from environment variables.
- **Platform Clients (`core/*_client.py`):** A set of classes implementing a common interface (`PlatformClientInterface`) to interact with different code hosting platforms (GitLab, GitHub, local Git). This is a Strategy pattern.
- **AI Providers (`providers/*.py`):** Pluggable modules for different AI services (e.g., `OllamaProvider`), inheriting from a `BaseAIProvider`. This is also a Strategy pattern.
**Entry Points:** The primary entry point is the command-line interface defined in `src/ai_code_review/cli.py`. The application flow is initiated by a user running the CLI command, which instantiates and runs the `ReviewEngine`.

### Important Files for Review Context
- **`src/ai_code_review/core/review_engine.py`** - This is the central orchestrator of the application. Understanding this file is critical to grasp how configuration, platform clients, and AI providers are integrated to produce a code review.
- **`src/ai_code_review/models/config.py`** - All application behavior is driven by settings defined and validated in this file. Reviewers must be aware of these configuration options to understand the context and impact of code changes.
- **`src/ai_code_review/utils/prompts.py`** - (Inferred from imports) This file likely contains the core AI prompts. The structure and content of these prompts directly determine the quality and nature of the AI-generated review, making it a critical file for review.
- **`src/ai_code_review/cli.py`** - As the main entry point, this file defines the user-facing API of the tool. Changes here affect how the application is invoked and how initial parameters are passed to the `ReviewEngine`.

### Development Conventions
- **Naming:** The code follows PEP 8 standards, using `PascalCase` for classes (`ReviewEngine`, `Config`) and `snake_case` for functions and variables (`_resolve_project_params`). Internal helper methods are prefixed with a single underscore.
- **Module Structure:** Code is organized into distinct packages based on functionality (`core`, `models`, `providers`, `utils`). This promotes low coupling and high cohesion. For example, all data models are in `models`, and all external AI integrations are in `providers`.
- **Configuration:** Configuration is handled centrally via `pydantic_settings.BaseSettings` in `src/ai_code_review/models/config.py`. This provides strong typing, validation, and loading from environment variables.
- **Testing:** The presence of a top-level `tests` directory indicates that tests are kept separate from the application source code, a standard convention in Python projects."""

        elif section_key == "review_focus":
            return """- **Async Correctness** - Verify no blocking operations in async contexts
- **Provider Pattern Consistency** - Check uniform behavior across AI providers
- **Configuration Validation** - Ensure proper environment and API key handling
- **Error Handling** - Verify graceful degradation when external services fail
- **Token Usage Awareness** - Monitor cost implications of LLM API calls"""

        else:
            return f"*Dry run mode - mock response for section: {section_key}*"

    def _generate_fallback_response(self, prompt: str) -> str:
        """Generate basic fallback when LLM fails."""
        return """*LLM analysis unavailable - using fallback mode*

This section could not be generated due to AI provider issues.
Basic project information is available in other sections."""
