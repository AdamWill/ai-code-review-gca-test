"""Tests for Context7Section."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from context_generator.core.llm_analyzer import SpecializedLLMAnalyzer
from context_generator.models import Context7Config
from context_generator.sections.context7_section import Context7Section


class TestContext7Section:
    """Test Context7Section functionality."""

    # ===== Basic Tests =====

    def test_init(self, ollama_config) -> None:
        """Test Context7Section initialization."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config(enabled=True, max_tokens_per_library=1500)

        section = Context7Section(analyzer, context7_config)

        assert section.name == "context7"
        assert section.required is False
        assert section.llm_analyzer == analyzer
        assert section.context7_config == context7_config
        assert (
            section.context7_provider.timeout_seconds == context7_config.timeout_seconds
        )

    def test_get_template_key(self, ollama_config) -> None:
        """Test get_template_key method."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config()

        section = Context7Section(analyzer, context7_config)

        assert section.get_template_key() == "context7_analysis"

    def test_is_available_disabled(self, ollama_config) -> None:
        """Test is_available when Context7 is disabled."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config(enabled=False)

        section = Context7Section(analyzer, context7_config)

        facts = {"dependencies": {"runtime": ["fastapi"]}}
        assert section.is_available(facts) is False

    def test_is_available_no_target_libraries(self, ollama_config) -> None:
        """Test is_available when no target libraries are found."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config(enabled=True, priority_libraries=["unknown"])

        section = Context7Section(analyzer, context7_config)

        facts = {"dependencies": {"runtime": ["requests"]}}
        assert section.is_available(facts) is False

    def test_is_available_with_target_libraries(self, ollama_config) -> None:
        """Test is_available when target libraries are found."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config(enabled=True, priority_libraries=["fastapi"])

        section = Context7Section(analyzer, context7_config)

        facts = {"dependencies": {"runtime": ["fastapi", "pydantic"]}}
        assert section.is_available(facts) is True

    # ===== Content Generation Tests =====

    @pytest.mark.asyncio
    async def test_generate_content_disabled(self, ollama_config) -> None:
        """Test content generation when Context7 is disabled."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config(enabled=False)

        section = Context7Section(analyzer, context7_config)

        result = await section.generate_content({}, {})

        assert result == ""

    @pytest.mark.asyncio
    async def test_generate_content_no_dependencies(self, ollama_config) -> None:
        """Test content generation when no dependencies are found."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config(enabled=True)

        section = Context7Section(analyzer, context7_config)

        facts = {"dependencies": {}}
        result = await section.generate_content(facts, {})

        assert result == ""

    @pytest.mark.asyncio
    async def test_generate_content_no_target_libraries(self, ollama_config) -> None:
        """Test content generation when no target libraries are selected."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config(
            enabled=True, priority_libraries=["unknown-lib"]
        )

        section = Context7Section(analyzer, context7_config)

        facts = {"dependencies": {"runtime": ["requests", "click"]}}
        result = await section.generate_content(facts, {})

        assert result == ""

    @pytest.mark.asyncio
    async def test_generate_content_success(self, ollama_config) -> None:
        """Test successful content generation."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config(enabled=True, priority_libraries=["fastapi"])

        section = Context7Section(analyzer, context7_config)

        facts = {
            "dependencies": {"runtime": ["fastapi", "pydantic"]},
            "project_info": {"name": "test-project", "type": "web_api"},
            "tech_indicators": {"languages": ["Python"]},
        }

        mock_docs = {"fastapi": "FastAPI is a modern web framework..."}
        mock_llm_result = "Analysis of FastAPI usage..."

        with patch.object(
            section, "_extract_dependencies", return_value=["fastapi", "pydantic"]
        ):
            with patch.object(
                section, "_extract_project_languages", return_value=["Python"]
            ):
                with patch.object(
                    section, "_select_target_libraries", return_value=["fastapi"]
                ):
                    with patch.object(
                        section,
                        "_fetch_library_documentation_with_language_context",
                        return_value=mock_docs,
                    ):
                        with patch.object(
                            analyzer, "call_llm", return_value=mock_llm_result
                        ):
                            result = await section.generate_content(facts, {})

                            # Result now includes validation note
                            expected_result = (
                                mock_llm_result
                                + "\n\n*Note: Documentation fetched for 1 libraries: fastapi. If any documentation seems irrelevant to this project, please verify the library selection logic.*"
                            )
                            assert result == expected_result

    @pytest.mark.asyncio
    async def test_generate_content_no_documentation(self, ollama_config) -> None:
        """Test content generation when no documentation is fetched."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config(enabled=True, priority_libraries=["fastapi"])

        section = Context7Section(analyzer, context7_config)

        facts = {
            "dependencies": {"runtime": ["fastapi"]},
            "tech_indicators": {"languages": ["Python"]},
        }

        with patch.object(section, "_extract_dependencies", return_value=["fastapi"]):
            with patch.object(
                section, "_extract_project_languages", return_value=["Python"]
            ):
                with patch.object(
                    section, "_select_target_libraries", return_value=["fastapi"]
                ):
                    with patch.object(
                        section,
                        "_fetch_library_documentation_with_language_context",
                        return_value={},
                    ):
                        result = await section.generate_content(facts, {})

                        assert result == ""

    # ===== Dependency Extraction Tests =====

    def test_extract_dependencies_basic(self, ollama_config) -> None:
        """Test basic dependency extraction."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config()

        section = Context7Section(analyzer, context7_config)

        facts = {
            "dependencies": {
                "runtime": ["fastapi>=0.95.0", "pydantic==1.10.0"],
                "dev": ["pytest>=7.0.0"],
                "frameworks": ["django"],
                "testing": ["coverage"],
            }
        }

        dependencies = section._extract_dependencies(facts)

        assert "fastapi" in dependencies
        assert "pydantic" in dependencies
        assert "pytest" in dependencies
        assert "django" in dependencies
        assert "coverage" in dependencies

    def test_extract_dependencies_empty(self, ollama_config) -> None:
        """Test dependency extraction with empty facts."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config()

        section = Context7Section(analyzer, context7_config)

        facts = {"dependencies": {}}
        dependencies = section._extract_dependencies(facts)

        assert dependencies == []

    def test_extract_dependencies_version_cleaning(self, ollama_config) -> None:
        """Test that version specifiers are cleaned from dependencies."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config()

        section = Context7Section(analyzer, context7_config)

        facts = {
            "dependencies": {
                "runtime": [
                    "fastapi>=0.95.0",
                    "pydantic==1.10.0",
                    "requests~=2.28.0",
                    "click<8.0.0",
                    "uvicorn>0.18.0",
                ]
            }
        }

        dependencies = section._extract_dependencies(facts)

        assert "fastapi" in dependencies
        assert "pydantic" in dependencies
        assert "requests" in dependencies
        assert "click" in dependencies
        assert "uvicorn" in dependencies
        # Should not contain version specifiers
        assert "fastapi>=0.95.0" not in dependencies

    def test_extract_dependencies_dict_format(self, ollama_config) -> None:
        """Test dependency extraction when dependencies are in dict format."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config()

        section = Context7Section(analyzer, context7_config)

        facts = {
            "dependencies": {
                "runtime": {"fastapi": ">=0.95.0", "pydantic": "==1.10.0"},
                "dev": {"pytest": ">=7.0.0"},
            }
        }

        dependencies = section._extract_dependencies(facts)

        assert "fastapi" in dependencies
        assert "pydantic" in dependencies
        assert "pytest" in dependencies

    # ===== Library Selection Tests =====

    def test_select_target_libraries_priority_libraries(self, ollama_config) -> None:
        """Test library selection with priority libraries."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config(
            enabled=True, priority_libraries=["fastapi", "django", "unknown"]
        )

        section = Context7Section(analyzer, context7_config)

        dependencies = ["fastapi", "pydantic", "requests", "django"]
        target_libraries = section._select_target_libraries(dependencies)

        # Should only include priority libraries that are in dependencies
        assert "fastapi" in target_libraries
        assert "django" in target_libraries
        assert "unknown" not in target_libraries  # Not in dependencies
        assert "pydantic" not in target_libraries  # Not in priority list

    def test_select_target_libraries_important_libraries(self, ollama_config) -> None:
        """Test library selection with important libraries when no priority set."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config(enabled=True, priority_libraries=[])

        section = Context7Section(analyzer, context7_config)

        dependencies = ["fastapi", "django", "pytest", "requests", "unknown-lib"]
        target_libraries = section._select_target_libraries(dependencies)

        # Should include important libraries from the predefined list
        # Note: Limited to max_libraries (3), so may not include all
        assert "fastapi" in target_libraries
        assert "django" in target_libraries
        assert "pytest" in target_libraries
        assert "unknown-lib" not in target_libraries  # Not in important list
        # requests may or may not be included due to the limit of 3

    def test_select_target_libraries_max_limit(self, ollama_config) -> None:
        """Test that library selection respects maximum limit."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config(enabled=True, priority_libraries=[])

        section = Context7Section(analyzer, context7_config)

        # Create many important dependencies
        dependencies = [
            "fastapi",
            "django",
            "flask",
            "pytest",
            "requests",
            "sqlalchemy",
            "pydantic",
            "aiohttp",
            "celery",
        ]
        target_libraries = section._select_target_libraries(dependencies)

        # Should be limited to max_libraries (3)
        assert len(target_libraries) <= 3

    def test_select_target_libraries_empty_dependencies(self, ollama_config) -> None:
        """Test library selection with empty dependencies."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config(enabled=True)

        section = Context7Section(analyzer, context7_config)

        dependencies = []
        target_libraries = section._select_target_libraries(dependencies)

        assert target_libraries == []

    # ===== Language Detection Tests =====

    def test_extract_project_languages_with_languages(self, ollama_config) -> None:
        """Test extracting project languages when languages are present."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config()

        section = Context7Section(analyzer, context7_config)

        facts = {
            "tech_indicators": {"languages": ["Python", "JavaScript", "TypeScript"]}
        }

        languages = section._extract_project_languages(facts)

        assert languages == ["Python", "JavaScript", "TypeScript"]

    def test_extract_project_languages_no_tech_indicators(self, ollama_config) -> None:
        """Test extracting project languages when no tech_indicators."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config()

        section = Context7Section(analyzer, context7_config)

        facts = {}

        languages = section._extract_project_languages(facts)

        assert languages == []

    def test_extract_project_languages_no_languages(self, ollama_config) -> None:
        """Test extracting project languages when no languages key."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config()

        section = Context7Section(analyzer, context7_config)

        facts = {"tech_indicators": {}}

        languages = section._extract_project_languages(facts)

        assert languages == []

    def test_extract_project_languages_non_list_languages(self, ollama_config) -> None:
        """Test extracting project languages when languages is not a list."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config()

        section = Context7Section(analyzer, context7_config)

        facts = {"tech_indicators": {"languages": "Python"}}

        languages = section._extract_project_languages(facts)

        assert languages == []

    def test_extract_project_languages_mixed_types(self, ollama_config) -> None:
        """Test extracting project languages with mixed types in list."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config()

        section = Context7Section(analyzer, context7_config)

        facts = {
            "tech_indicators": {
                "languages": ["Python", 123, "JavaScript", None, "TypeScript"]
            }
        }

        languages = section._extract_project_languages(facts)

        # Should filter out non-strings
        assert languages == ["Python", "JavaScript", "TypeScript"]

    # ===== Language-Aware Search Tests =====

    def test_create_language_aware_search_query_with_languages(
        self, ollama_config
    ) -> None:
        """Test creating language-aware search query with detected languages."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config()

        section = Context7Section(analyzer, context7_config)

        query = section._create_language_aware_search_query("fastapi", ["Python"])

        assert query == "fastapi python"

    def test_create_language_aware_search_query_no_languages(
        self, ollama_config
    ) -> None:
        """Test creating language-aware search query with no detected languages."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config()

        section = Context7Section(analyzer, context7_config)

        query = section._create_language_aware_search_query("fastapi", [])

        assert query == "fastapi"

    def test_create_language_aware_search_query_unknown_language(
        self, ollama_config
    ) -> None:
        """Test creating language-aware search query with unknown language."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config()

        section = Context7Section(analyzer, context7_config)

        query = section._create_language_aware_search_query("fastapi", ["UnknownLang"])

        assert query == "fastapi unknownlang"

    def test_create_language_aware_search_query_mapped_language(
        self, ollama_config
    ) -> None:
        """Test creating language-aware search query with mapped language."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config()

        section = Context7Section(analyzer, context7_config)

        # Test various mapped languages
        query_js = section._create_language_aware_search_query("react", ["JavaScript"])
        assert query_js == "react javascript"

        query_ts = section._create_language_aware_search_query(
            "angular", ["TypeScript"]
        )
        assert query_ts == "angular typescript"

        query_java = section._create_language_aware_search_query("spring", ["Java"])
        assert query_java == "spring java"

    # ===== Documentation Fetching Tests =====

    @pytest.mark.asyncio
    async def test_fetch_library_documentation_with_language_context_success(
        self, ollama_config
    ) -> None:
        """Test successful documentation fetching with language context."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config()

        section = Context7Section(analyzer, context7_config)

        libraries = ["fastapi", "pydantic"]
        detected_languages = ["Python"]

        with patch.object(
            section,
            "_fetch_single_library_docs_with_language_context",
            side_effect=["FastAPI docs", "Pydantic docs"],
        ):
            result = await section._fetch_library_documentation_with_language_context(
                libraries, detected_languages
            )

            assert result == {"fastapi": "FastAPI docs", "pydantic": "Pydantic docs"}

    @pytest.mark.asyncio
    async def test_fetch_library_documentation_with_language_context_partial_failure(
        self, ollama_config
    ) -> None:
        """Test documentation fetching with some failures."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config()

        section = Context7Section(analyzer, context7_config)

        libraries = ["fastapi", "unknown"]
        detected_languages = ["Python"]

        with patch.object(
            section,
            "_fetch_single_library_docs_with_language_context",
            side_effect=["FastAPI docs", Exception("Library not found")],
        ):
            result = await section._fetch_library_documentation_with_language_context(
                libraries, detected_languages
            )

            assert result == {"fastapi": "FastAPI docs"}

    @pytest.mark.asyncio
    async def test_fetch_single_library_docs_with_language_context_success(
        self, ollama_config
    ) -> None:
        """Test successful single library documentation fetching."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config()

        section = Context7Section(analyzer, context7_config)

        with patch.object(
            section.context7_provider,
            "resolve_library_id",
            return_value="/fastapi/fastapi",
        ):
            with patch.object(
                section.context7_provider,
                "get_library_docs",
                return_value="FastAPI docs",
            ):
                result = await section._fetch_single_library_docs_with_language_context(
                    "fastapi", ["Python"]
                )

                assert result == "FastAPI docs"

    @pytest.mark.asyncio
    async def test_fetch_single_library_docs_with_language_context_fallback(
        self, ollama_config
    ) -> None:
        """Test single library documentation fetching with fallback."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config()

        section = Context7Section(analyzer, context7_config)

        # First call (with language context) returns None, second call (fallback) succeeds
        with patch.object(
            section.context7_provider,
            "resolve_library_id",
            side_effect=[None, "/fastapi/fastapi"],
        ):
            with patch.object(
                section.context7_provider,
                "get_library_docs",
                return_value="FastAPI docs",
            ):
                result = await section._fetch_single_library_docs_with_language_context(
                    "fastapi", ["Python"]
                )

                assert result == "FastAPI docs"

    @pytest.mark.asyncio
    async def test_fetch_single_library_docs_with_language_context_no_library_id(
        self, ollama_config
    ) -> None:
        """Test single library documentation fetching when no library ID found."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config()

        section = Context7Section(analyzer, context7_config)

        with patch.object(
            section.context7_provider, "resolve_library_id", return_value=None
        ):
            result = await section._fetch_single_library_docs_with_language_context(
                "unknown", ["Python"]
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_fetch_single_library_docs_with_language_context_exception(
        self, ollama_config
    ) -> None:
        """Test single library documentation fetching with exception."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config()

        section = Context7Section(analyzer, context7_config)

        with patch.object(
            section.context7_provider,
            "resolve_library_id",
            side_effect=Exception("Network error"),
        ):
            result = await section._fetch_single_library_docs_with_language_context(
                "fastapi", ["Python"]
            )

            assert result is None

    # ===== Prompt Creation Tests =====

    def test_create_context7_prompt(self, ollama_config) -> None:
        """Test Context7 prompt creation."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config()

        section = Context7Section(analyzer, context7_config)

        facts = {
            "project_info": {"name": "test-project", "type": "web_api"},
        }
        library_docs = {
            "fastapi": "FastAPI is a modern web framework...",
            "pydantic": "Pydantic provides data validation...",
        }

        prompt = section._create_context7_prompt(facts, library_docs)

        assert "test-project" in prompt
        assert "web_api" in prompt
        assert "FastAPI is a modern web framework..." in prompt
        assert "Pydantic provides data validation..." in prompt
        assert "fastapi Documentation" in prompt
        assert "pydantic Documentation" in prompt

    def test_create_context7_prompt_missing_project_info(self, ollama_config) -> None:
        """Test Context7 prompt creation with missing project info."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config()

        section = Context7Section(analyzer, context7_config)

        facts = {}
        library_docs = {"fastapi": "FastAPI documentation"}

        prompt = section._create_context7_prompt(facts, library_docs)

        assert "Unknown Project" in prompt
        assert "Unknown" in prompt
        assert "FastAPI documentation" in prompt

    # ===== Integration Tests =====

    @pytest.mark.asyncio
    async def test_generate_content_with_language_context_integration(
        self, ollama_config
    ) -> None:
        """Test end-to-end content generation with language context."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config(enabled=True, priority_libraries=["fastapi"])

        section = Context7Section(analyzer, context7_config)

        facts = {
            "dependencies": {"runtime": ["fastapi", "pydantic"]},
            "project_info": {"name": "test-project", "type": "web_api"},
            "tech_indicators": {"languages": ["Python"]},
        }

        mock_llm_result = "FastAPI analysis with language context..."

        # Mock the entire flow
        with patch.object(
            section.context7_provider,
            "resolve_library_id",
            return_value="/fastapi/fastapi",
        ):
            with patch.object(
                section.context7_provider,
                "get_library_docs",
                return_value="FastAPI docs",
            ):
                with patch.object(analyzer, "call_llm", return_value=mock_llm_result):
                    result = await section.generate_content(facts, {})

                    # Should include the LLM result and validation note
                    assert mock_llm_result in result

    def test_select_target_libraries_configurable_max_limit(
        self, ollama_config
    ) -> None:
        """Test that target library selection respects configurable max limit."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        # Configure max_libraries to 5
        context7_config = Context7Config(enabled=True, max_libraries=5)

        section = Context7Section(analyzer, context7_config)

        dependencies = ["fastapi", "django", "flask", "pydantic", "requests", "numpy"]
        target_libraries = section._select_target_libraries(dependencies)

        # Should be limited to 5 libraries (configured)
        assert len(target_libraries) <= 5
        # Should prioritize important libraries
        assert all(lib in dependencies for lib in target_libraries)

    def test_select_target_libraries_uses_constants(self, ollama_config) -> None:
        """Test that target library selection uses constants from constants.py."""
        analyzer = SpecializedLLMAnalyzer(ollama_config)
        context7_config = Context7Config(enabled=True)

        section = Context7Section(analyzer, context7_config)

        # Test with a mix of important and non-important libraries
        dependencies = [
            "fastapi",
            "unknown-lib",
            "django",
            "another-unknown",
            "pydantic",
        ]
        target_libraries = section._select_target_libraries(dependencies)

        # Should only include libraries that are in CONTEXT7_IMPORTANT_LIBRARIES
        expected_libraries = ["fastapi", "django", "pydantic"]
        assert set(target_libraries) == set(expected_libraries)
        # Should not include unknown libraries
        assert "unknown-lib" not in target_libraries
        assert "another-unknown" not in target_libraries
