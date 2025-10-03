"""Extensible section framework for context generation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class BaseSection(ABC):
    """Abstract base class for context sections."""

    def __init__(self, name: str, required: bool = True) -> None:
        """Initialize section.

        Args:
            name: Section identifier
            required: Whether section is required for valid context
        """
        self.name = name
        self.required = required

    @abstractmethod
    async def generate_content(
        self, facts: dict[str, Any], code_samples: dict[str, str]
    ) -> str:
        """Generate section content.

        Args:
            facts: Project facts from facts extractor
            code_samples: Code samples from code extractor

        Returns:
            Formatted section content
        """
        pass

    @abstractmethod
    def get_template_key(self) -> str:
        """Get template placeholder key for this section."""
        pass

    def is_available(self, facts: dict[str, Any]) -> bool:
        """Check if section can be generated with available facts.

        Args:
            facts: Available project facts

        Returns:
            True if section can be generated
        """
        return True

    def get_dependencies(self) -> list[str]:
        """Get list of required fact keys for this section.

        Returns:
            List of required keys from facts dict
        """
        return []


class SectionRegistry:
    """Registry for managing context sections."""

    def __init__(self) -> None:
        """Initialize section registry."""
        self.sections: list[BaseSection] = []

    def register(self, section: BaseSection) -> None:
        """Register a section.

        Args:
            section: Section to register
        """
        self.sections.append(section)
        logger.debug(f"Registered section: {section.name}")

    def get_available_sections(self, facts: dict[str, Any]) -> list[BaseSection]:
        """Get sections that can be generated with available facts.

        Args:
            facts: Available project facts

        Returns:
            List of available sections
        """
        available = []
        for section in self.sections:
            if section.is_available(facts):
                available.append(section)
            elif section.required:
                logger.warning(f"Required section {section.name} not available")

        return available

    def get_required_sections(self) -> list[BaseSection]:
        """Get all required sections.

        Returns:
            List of required sections
        """
        return [s for s in self.sections if s.required]

    def get_optional_sections(self) -> list[BaseSection]:
        """Get all optional sections.

        Returns:
            List of optional sections
        """
        return [s for s in self.sections if not s.required]
