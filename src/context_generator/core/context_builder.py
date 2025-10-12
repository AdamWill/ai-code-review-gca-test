"""Main context builder orchestrator."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import structlog

from ai_code_review.models.config import Config
from context_generator.core.code_extractor import CodeSampleExtractor
from context_generator.core.facts_extractor import ProjectFactsExtractor
from context_generator.core.llm_analyzer import SpecializedLLMAnalyzer
from context_generator.models import CIDocsConfig, Context7Config, ContextResult
from context_generator.sections import (
    BaseSection,
    Context7Section,
    OverviewSection,
    ReviewFocusSection,
    SectionRegistry,
    StructureSection,
    TechStackSection,
)
from context_generator.sections.ci_docs_section import CIDocsSection
from context_generator.templates.template_engine import TemplateEngine

logger = structlog.get_logger(__name__)


class ContextBuilder:
    """Main orchestrator for context generation with specialized sections."""

    def __init__(
        self,
        project_path: Path,
        config: Config,
        skip_git_validation: bool = False,
        context7_config: Context7Config | None = None,
        ci_docs_config: CIDocsConfig | None = None,
    ) -> None:
        """Initialize context builder."""
        self.project_path = project_path
        self.config = config
        self.context7_config = context7_config or Context7Config()
        self.ci_docs_config = ci_docs_config or CIDocsConfig()

        # skip_git_validation should only be True when explicitly passed (for testing)

        # Core components
        self.facts_extractor = ProjectFactsExtractor(project_path, skip_git_validation)
        self.code_extractor = CodeSampleExtractor(project_path, skip_git_validation)
        self.llm_analyzer = SpecializedLLMAnalyzer(config)
        self.template_engine = TemplateEngine()

        # Section registry
        self.section_registry = SectionRegistry()
        self._register_core_sections()

    def _register_core_sections(self) -> None:
        """Register the core sections for context generation."""
        # Section 1: Overview (no code samples - just facts)
        self.section_registry.register(OverviewSection(self.llm_analyzer))

        # Section 2: Tech Stack (no code samples - dependency analysis)
        self.section_registry.register(TechStackSection(self.llm_analyzer))

        # Section 3: Structure (with code samples - architectural patterns)
        self.section_registry.register(StructureSection(self.llm_analyzer))

        # Section 4: Review Focus (with code samples - specific recommendations)
        self.section_registry.register(ReviewFocusSection(self.llm_analyzer))

        # Section 5: Context7 (optional - external library documentation)
        self.section_registry.register(
            Context7Section(self.llm_analyzer, self.context7_config)
        )

        # Section 6: CI Docs (optional - official CI/CD documentation)
        self.section_registry.register(
            CIDocsSection(self.llm_analyzer, self.ci_docs_config)
        )

        logger.info(
            "Registered core sections",
            section_count=len(self.section_registry.sections),
        )

    async def generate_context(
        self, output_path: Path | None = None, target_sections: list[str] | None = None
    ) -> ContextResult:
        """Generate complete project context with specialized LLM calls."""
        logger.info(
            "Starting context generation",
            project=self.project_path.name,
            provider=self.config.ai_provider.value,
            target_sections=target_sections,
        )

        # Extract project facts and code samples
        facts = self.facts_extractor.extract_all_facts()
        code_samples = self.code_extractor.get_architecture_samples()

        logger.debug(
            "Extracted project data",
            facts_keys=list(facts.keys()),
            code_samples_count=len(code_samples),
        )

        # Generate all available sections (or only target sections)
        if target_sections:
            section_content = await self._generate_target_sections(
                facts, code_samples, target_sections
            )
        else:
            section_content = await self._generate_all_sections(facts, code_samples)

        # Render final context using template (with manual section preservation)
        context_content = self.template_engine.render_context(
            section_content, facts, output_path
        )

        # Create ContextResult
        result = ContextResult.create(
            project_path=self.project_path,
            project_name=self.project_path.name,
            context_content=context_content,
            ai_provider=self.config.ai_provider.value,
            ai_model=self.config.ai_model,
        )

        logger.info(
            "Context generation completed",
            sections_generated=len(section_content),
            context_length=len(context_content),
        )

        return result

    async def _generate_all_sections(
        self, facts: dict[str, Any], code_samples: dict[str, str]
    ) -> dict[str, str]:
        """Generate content for all available sections."""
        available_sections = self.section_registry.get_available_sections(facts)
        logger.info(
            "Generating all sections",
            available_sections=[section.name for section in available_sections],
            total_sections=len(available_sections),
        )
        return await self._execute_section_generation(
            available_sections, facts, code_samples
        )

    async def _execute_section_generation(
        self,
        sections_to_generate: list[BaseSection],
        facts: dict[str, Any],
        code_samples: dict[str, str],
    ) -> dict[str, str]:
        """Execute section generation with parallel optimization."""
        section_content = {}

        # Group sections by whether they need code samples
        no_code_sections: list[BaseSection] = []  # Overview, TechStack
        with_code_sections: list[BaseSection] = []  # Structure, ReviewFocus

        for section in sections_to_generate:
            if section.name in ["overview", "tech_stack"]:
                no_code_sections.append(section)
                logger.debug(
                    "Queued section (no code samples needed)", section=section.name
                )
            else:
                with_code_sections.append(section)
                logger.debug(
                    "Queued section (code samples needed)", section=section.name
                )

        # Parallel execution in two groups to optimize LLM calls
        try:
            # First: Generate sections that don't need code samples
            if no_code_sections:
                no_code_tasks = [
                    section.generate_content(facts, {}) for section in no_code_sections
                ]
                no_code_results = await asyncio.gather(*no_code_tasks)

                for section, content in zip(
                    no_code_sections,
                    no_code_results,
                    strict=True,
                ):
                    section_content[section.get_template_key()] = content

            # Second: Generate sections that need code samples
            if with_code_sections:
                with_code_tasks = [
                    section.generate_content(facts, code_samples)
                    for section in with_code_sections
                ]
                with_code_results = await asyncio.gather(*with_code_tasks)

                for section, content in zip(
                    with_code_sections,
                    with_code_results,
                    strict=True,
                ):
                    section_content[section.get_template_key()] = content

        except Exception as e:
            logger.error("Section generation failed", error=str(e))
            # Try to generate required sections individually
            section_content = await self._generate_sections_individually(
                sections_to_generate, facts, code_samples
            )

        return section_content

    async def _generate_sections_individually(
        self,
        sections: list[BaseSection],
        facts: dict[str, Any],
        code_samples: dict[str, str],
    ) -> dict[str, str]:
        """Fallback: generate sections one by one if parallel fails."""
        section_content = {}

        for section in sections:
            try:
                if section.name in ["overview", "tech_stack"]:
                    content = await section.generate_content(facts, {})
                else:
                    content = await section.generate_content(facts, code_samples)

                section_content[section.get_template_key()] = content

                logger.debug(f"Generated section: {section.name}")

            except Exception as e:
                logger.error(f"Failed to generate section {section.name}", error=str(e))

                if section.required:
                    # Provide fallback content for required sections
                    section_content[section.get_template_key()] = (
                        f"*{section.name.title()} section unavailable due to generation error*"
                    )

        return section_content

    async def _generate_target_sections(
        self,
        facts: dict[str, Any],
        code_samples: dict[str, str],
        target_sections: list[str],
    ) -> dict[str, str]:
        """Generate content for only the specified sections."""
        available_sections = self.section_registry.get_available_sections(facts)

        # Filter sections to only the requested ones
        target_section_objects = []
        for section in available_sections:
            if section.get_template_key() in target_sections:
                target_section_objects.append(section)

        return await self._execute_section_generation(
            target_section_objects, facts, code_samples
        )

    def get_generation_summary(self) -> dict[str, Any]:
        """Get summary of generation configuration for logging."""
        return {
            "project_name": self.project_path.name,
            "ai_provider": self.config.ai_provider.value,
            "ai_model": self.config.ai_model,
            "sections_registered": len(self.section_registry.sections),
            "dry_run": self.config.dry_run,
        }
