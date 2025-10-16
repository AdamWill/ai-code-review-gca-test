"""Context7 section for external library documentation integration."""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from context_generator.constants import CONTEXT7_IMPORTANT_LIBRARIES
from context_generator.models import Context7Config
from context_generator.providers.context7_provider import Context7Provider
from context_generator.sections.base_section import BaseSection

logger = structlog.get_logger(__name__)


class Context7Section(BaseSection):
    """Generate library documentation insights using Context7."""

    def __init__(self, llm_analyzer: Any, context7_config: Context7Config) -> None:
        """Initialize Context7 section.

        Args:
            llm_analyzer: LLM analyzer for generating insights
            context7_config: Context7 configuration
        """
        super().__init__("context7", required=False)
        self.llm_analyzer = llm_analyzer
        self.context7_config = context7_config
        self.context7_provider = Context7Provider(
            timeout_seconds=context7_config.timeout_seconds,
            api_key=context7_config.api_key,
        )

    async def generate_content(
        self, facts: dict[str, Any], code_samples: dict[str, str]
    ) -> str:
        """Generate Context7 documentation content.

        Args:
            facts: Project facts including dependencies
            code_samples: Code samples (not used in this section)

        Returns:
            Generated content with library documentation insights
        """
        # Check if Context7 is enabled
        if not self.context7_config.enabled:
            logger.debug("Context7 disabled, skipping section")
            return ""

        # Extract dependencies and detected languages from facts
        dependencies = self._extract_dependencies(facts)
        detected_languages = self._extract_project_languages(facts)

        # Determine which libraries to fetch documentation for
        # Note: CI/CD documentation is handled separately by CIDocsSection
        target_libraries = self._select_target_libraries(dependencies)

        if not target_libraries:
            logger.debug("No target libraries selected, skipping Context7 section")
            return ""

        # Fetch documentation for target libraries with language context
        library_docs = await self._fetch_library_documentation_with_language_context(
            target_libraries, detected_languages
        )
        if not library_docs:
            logger.info(
                "Context7 section skipped - no documentation available. "
                "This may be due to missing CONTEXT7_API_KEY or network issues. "
                "See docs/context7-integration.md for setup instructions."
            )
            return ""

        # Generate LLM analysis with the documentation
        prompt = self._create_context7_prompt(facts, library_docs)
        result = await self.llm_analyzer.call_llm(prompt, self.get_template_key())

        logger.info("Context7 LLM analysis completed", result_length=len(str(result)))

        # Add validation note to help reviewers identify potential issues
        validation_note = f"\n\n*Note: Documentation fetched for {len(library_docs)} libraries: {', '.join(library_docs.keys())}. If any documentation seems irrelevant to this project, please verify the library selection logic.*"

        return str(result) + validation_note

    def _extract_project_languages(self, facts: dict[str, Any]) -> list[str]:
        """Extract detected languages from project facts.

        Args:
            facts: Project facts from facts extractor

        Returns:
            List of detected programming languages
        """
        tech_indicators = facts.get("tech_indicators", {})
        languages = tech_indicators.get("languages", [])

        # Ensure we return a list of strings
        if not isinstance(languages, list):
            languages = []

        # Filter to ensure all items are strings
        string_languages = [lang for lang in languages if isinstance(lang, str)]

        logger.debug("Detected project languages", languages=string_languages)
        return string_languages

    def _extract_dependencies(self, facts: dict[str, Any]) -> list[str]:
        """Extract dependencies from project facts.

        Args:
            facts: Project facts

        Returns:
            List of dependency names
        """
        dependencies = []

        # Extract from dependencies facts
        deps_info = facts.get("dependencies", {})

        # Get dependencies from various sources
        deps_sources = [
            deps_info.get("runtime", []),
            deps_info.get("dev", []),
            deps_info.get("frameworks", []),
            deps_info.get("testing", []),
        ]

        for deps in deps_sources:
            if isinstance(deps, list):
                dependencies.extend(deps)
            elif isinstance(deps, dict):
                dependencies.extend(deps.keys())

        # Clean up dependency names (remove version specifiers)
        clean_dependencies = []
        for dep in dependencies:
            if isinstance(dep, str):
                # Remove version specifiers like >=1.0.0, ==2.1.0, etc.
                clean_name = (
                    dep.split(">=")[0]
                    .split("==")[0]
                    .split("~=")[0]
                    .split("<")[0]
                    .split(">")[0]
                    .strip()
                )
                if clean_name and clean_name not in clean_dependencies:
                    clean_dependencies.append(clean_name)

        logger.debug(
            "Extracted dependencies",
            count=len(clean_dependencies),
            dependencies=clean_dependencies[:10],
        )
        return clean_dependencies

    def _select_target_libraries(self, dependencies: list[str]) -> list[str]:
        """Select which libraries to fetch documentation for.

        Args:
            dependencies: All project dependencies

        Returns:
            List of libraries to fetch documentation for
        """
        target_libraries = []

        # If priority libraries are configured, use only those that are in dependencies
        if self.context7_config.priority_libraries:
            for lib in self.context7_config.priority_libraries:
                if lib in dependencies:
                    target_libraries.append(lib)
        else:
            # Only select libraries that are ACTUALLY in the project dependencies
            # This prevents fetching irrelevant documentation
            # Only add libraries that are both important AND in project dependencies
            for dep in dependencies:
                if dep.lower() in CONTEXT7_IMPORTANT_LIBRARIES:
                    target_libraries.append(dep)

        # Limit to reasonable number to avoid excessive API calls
        # Use configurable max_libraries from Context7Config
        max_libraries = self.context7_config.max_libraries
        target_libraries = target_libraries[:max_libraries]

        logger.info(
            "Selected target libraries",
            count=len(target_libraries),
            libraries=target_libraries,
        )
        return target_libraries

    async def _fetch_library_documentation(
        self, libraries: list[str]
    ) -> dict[str, str]:
        """Fetch documentation for multiple libraries in parallel.

        Args:
            libraries: List of library names to fetch docs for

        Returns:
            Dictionary mapping library names to their documentation
        """
        logger.info("Fetching library documentation", libraries=libraries)

        # Create tasks for parallel execution
        tasks = []
        for library in libraries:
            task = self._fetch_single_library_docs(library)
            tasks.append(task)

        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect successful results
        library_docs = {}
        for library, result in zip(libraries, results, strict=True):
            if isinstance(result, str) and result:
                library_docs[library] = result
            elif isinstance(result, Exception):
                logger.warning(
                    "Failed to fetch docs for library",
                    library=library,
                    error=str(result),
                )

        logger.info(
            "Documentation fetched",
            successful_count=len(library_docs),
            total_count=len(libraries),
        )
        return library_docs

    async def _fetch_library_documentation_with_language_context(
        self,
        libraries: list[str],
        detected_languages: list[str],
    ) -> dict[str, str]:
        """Fetch documentation for multiple libraries using language context for better accuracy.

        Args:
            libraries: List of library names to fetch docs for
            detected_languages: List of detected project languages

        Returns:
            Dictionary mapping library names to their documentation
        """
        logger.info(
            "Fetching library documentation with language context",
            libraries=libraries,
            detected_languages=detected_languages,
        )

        # Create tasks for parallel execution with language-aware search
        tasks = []
        for library in libraries:
            task = self._fetch_single_library_docs_with_language_context(
                library, detected_languages
            )
            tasks.append(task)

        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect successful results
        library_docs = {}
        for library, result in zip(libraries, results, strict=True):
            if isinstance(result, str):
                library_docs[library] = result
            elif isinstance(result, Exception):
                logger.warning(
                    "Failed to fetch docs for library with language context",
                    library=library,
                    error=str(result),
                )

        logger.info(
            "Documentation fetched with language context",
            successful_count=len(library_docs),
            total_count=len(libraries),
        )
        return library_docs

    async def _fetch_single_library_docs_with_language_context(
        self, library: str, detected_languages: list[str]
    ) -> str | None:
        """Fetch documentation for a single library using language context for better selection.

        Args:
            library: Library name
            detected_languages: List of detected project languages

        Returns:
            Documentation content or None if failed
        """
        try:
            # Create language-aware search query for regular libraries
            search_query = self._create_language_aware_search_query(
                library, detected_languages
            )

            # Use the language-aware query for better library resolution
            library_id = await self.context7_provider.resolve_library_id(search_query)
            if not library_id:
                # Fallback to original library name if language-aware search fails
                library_id = await self.context7_provider.resolve_library_id(library)

            if not library_id:
                return None

            docs = await self.context7_provider.get_library_docs(
                library_id=library_id,
                max_tokens=self.context7_config.max_tokens_per_library,
            )
            return docs
        except Exception as e:
            logger.warning(
                "Error fetching docs for library with language context",
                library=library,
                error=str(e),
            )
            return None

    def _create_language_aware_search_query(
        self, library: str, detected_languages: list[str]
    ) -> str:
        """Create a search query that includes language context for better accuracy.

        Args:
            library: Library name
            detected_languages: List of detected project languages

        Returns:
            Language-aware search query
        """
        if not detected_languages:
            return library

        # Map common language names to search terms
        language_mapping = {
            "Python": "python",
            "JavaScript/TypeScript": "javascript",
            "Go": "go",
            "Java": "java",
            "Rust": "rust",
            "Ruby": "ruby",
            "PHP": "php",
            "C": "c",
            "C++": "cpp",
        }

        # Use the first detected language for the search query
        primary_language = detected_languages[0]
        search_term = language_mapping.get(primary_language, primary_language.lower())

        # Create language-aware query
        search_query = f"{library} {search_term}"

        logger.debug(
            "Created language-aware search query",
            library=library,
            primary_language=primary_language,
            search_query=search_query,
        )

        return search_query

    async def _fetch_single_library_docs(self, library: str) -> str | None:
        """Fetch documentation for a single library.

        Args:
            library: Library name

        Returns:
            Documentation content or None if failed
        """
        try:
            docs = await self.context7_provider.get_library_documentation(
                library_name=library,
                max_tokens=self.context7_config.max_tokens_per_library,
            )
            return docs
        except Exception as e:
            logger.warning(
                "Error fetching docs for library", library=library, error=str(e)
            )
            return None

    def _create_context7_prompt(
        self,
        facts: dict[str, Any],
        library_docs: dict[str, str],
    ) -> str:
        """Create prompt for LLM analysis with Context7 documentation.

        Args:
            facts: Project facts
            library_docs: Documentation for libraries

        Returns:
            Formatted prompt for LLM
        """
        project_name = facts.get("project_info", {}).get("name", "Unknown Project")
        project_type = facts.get("project_info", {}).get("type", "Unknown")

        # Build documentation section
        docs_section = ""
        for library, docs in library_docs.items():
            docs_section += f"\n### {library} Documentation\n\n{docs}\n"

        prompt = f"""Analyze the following project's use of external libraries based on official documentation.

**Project Information:**
- Name: {project_name}
- Type: {project_type}

**Available Library Documentation:**
{docs_section}

**Analysis Instructions:**
1. **API Usage Patterns**: Identify how the project should optimally use these libraries based on the official documentation
2. **Best Practices**: Highlight recommended patterns, configurations, and usage guidelines from the documentation
3. **Common Pitfalls**: Note potential issues or anti-patterns to avoid based on the library documentation
4. **Integration Recommendations**: Suggest how these libraries should work together effectively
5. **Configuration Guidelines**: Recommend optimal configuration based on documented best practices

**Focus Areas:**
- Correct API usage according to official documentation
- Performance optimization recommendations from the docs
- Security considerations mentioned in the documentation
- Compatibility and version considerations
- Testing approaches recommended by the library maintainers

Provide actionable insights that will help during code review to ensure the project follows documented best practices for these libraries."""

        return prompt

    def get_template_key(self) -> str:
        """Get template key for Context7 section."""
        return "context7_analysis"

    def is_available(self, facts: dict[str, Any]) -> bool:
        """Check if this section should be included.

        Args:
            facts: Project facts

        Returns:
            True if Context7 is enabled and dependencies are available
        """
        if not self.context7_config.enabled:
            return False

        dependencies = self._extract_dependencies(facts)
        target_libraries = self._select_target_libraries(dependencies)

        return len(target_libraries) > 0
