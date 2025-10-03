"""Context generator for AI code review - Independent utility."""

from context_generator.constants import (
    DEPENDENCY_FILE_PATTERNS,
    GO_FRAMEWORKS,
    GO_TESTING_TOOLS,
    IMPORTANT_EXTENSIONS,
    IMPORTANT_FILES_NO_EXT,
    IMPORTANT_ROOT_FILES,
    JAVA_FRAMEWORKS,
    JAVA_TESTING_TOOLS,
    JAVASCRIPT_FRAMEWORKS,
    JAVASCRIPT_TESTING_TOOLS,
    LANGUAGE_EXTENSIONS,
    PRIORITY_PYTHON_FILES,
    PYTHON_FRAMEWORKS,
    PYTHON_TESTING_TOOLS,
    RUBY_FRAMEWORKS,
    RUBY_TESTING_TOOLS,
    RUST_FRAMEWORKS,
    RUST_TESTING_TOOLS,
)
from context_generator.core.code_extractor import CodeSampleExtractor
from context_generator.core.context_builder import ContextBuilder
from context_generator.core.facts_extractor import ProjectFactsExtractor
from context_generator.models import ContextResult

__all__ = [
    "ContextBuilder",
    "ProjectFactsExtractor",
    "CodeSampleExtractor",
    "ContextResult",
    "DEPENDENCY_FILE_PATTERNS",
    "GO_FRAMEWORKS",
    "GO_TESTING_TOOLS",
    "IMPORTANT_EXTENSIONS",
    "IMPORTANT_FILES_NO_EXT",
    "IMPORTANT_ROOT_FILES",
    "JAVA_FRAMEWORKS",
    "JAVA_TESTING_TOOLS",
    "JAVASCRIPT_FRAMEWORKS",
    "JAVASCRIPT_TESTING_TOOLS",
    "LANGUAGE_EXTENSIONS",
    "PRIORITY_PYTHON_FILES",
    "PYTHON_FRAMEWORKS",
    "PYTHON_TESTING_TOOLS",
    "RUBY_FRAMEWORKS",
    "RUBY_TESTING_TOOLS",
    "RUST_FRAMEWORKS",
    "RUST_TESTING_TOOLS",
]
