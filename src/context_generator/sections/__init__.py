"""Section implementations for context generation."""

from context_generator.sections.base_section import BaseSection, SectionRegistry
from context_generator.sections.context7_section import Context7Section
from context_generator.sections.overview_section import OverviewSection
from context_generator.sections.review_section import ReviewFocusSection
from context_generator.sections.structure_section import StructureSection
from context_generator.sections.tech_stack_section import TechStackSection

__all__ = [
    "BaseSection",
    "SectionRegistry",
    "OverviewSection",
    "TechStackSection",
    "StructureSection",
    "ReviewFocusSection",
    "Context7Section",
]
