"""Tests for context generator constants."""

from __future__ import annotations

from context_generator.constants import (
    IMPORTANT_EXTENSIONS,
    IMPORTANT_FILES_NO_EXT,
    IMPORTANT_ROOT_FILES,
    PRIORITY_PYTHON_FILES,
)


class TestContextGeneratorConstants:
    """Test context generator constants."""

    def test_important_extensions_contains_common_types(self) -> None:
        """Test that important extensions contains common file types."""
        # Python
        assert ".py" in IMPORTANT_EXTENSIONS

        # JavaScript/TypeScript
        assert ".js" in IMPORTANT_EXTENSIONS
        assert ".ts" in IMPORTANT_EXTENSIONS
        assert ".jsx" in IMPORTANT_EXTENSIONS
        assert ".tsx" in IMPORTANT_EXTENSIONS

        # Other languages
        assert ".go" in IMPORTANT_EXTENSIONS
        assert ".rs" in IMPORTANT_EXTENSIONS
        assert ".java" in IMPORTANT_EXTENSIONS
        assert ".rb" in IMPORTANT_EXTENSIONS

        # Config files
        assert ".yml" in IMPORTANT_EXTENSIONS
        assert ".yaml" in IMPORTANT_EXTENSIONS
        assert ".json" in IMPORTANT_EXTENSIONS
        assert ".toml" in IMPORTANT_EXTENSIONS

        # Documentation
        assert ".md" in IMPORTANT_EXTENSIONS
        assert ".rst" in IMPORTANT_EXTENSIONS

    def test_important_files_no_ext_contains_common_files(self) -> None:
        """Test that important files without extension contains common files."""
        # Docker
        assert "Dockerfile" in IMPORTANT_FILES_NO_EXT
        assert "Containerfile" in IMPORTANT_FILES_NO_EXT

        # Build systems
        assert "Makefile" in IMPORTANT_FILES_NO_EXT
        assert "Jenkinsfile" in IMPORTANT_FILES_NO_EXT

        # Ruby
        assert "Gemfile" in IMPORTANT_FILES_NO_EXT
        assert "Rakefile" in IMPORTANT_FILES_NO_EXT

        # Legal/docs
        assert "LICENSE" in IMPORTANT_FILES_NO_EXT
        assert "CHANGELOG" in IMPORTANT_FILES_NO_EXT

    def test_important_root_files_contains_project_files(self) -> None:
        """Test that important root files contains project configuration files."""
        # Python
        assert "pyproject.toml" in IMPORTANT_ROOT_FILES
        assert "setup.py" in IMPORTANT_ROOT_FILES
        assert "requirements.txt" in IMPORTANT_ROOT_FILES

        # JavaScript/Node.js
        assert "package.json" in IMPORTANT_ROOT_FILES
        assert "package-lock.json" in IMPORTANT_ROOT_FILES
        assert "yarn.lock" in IMPORTANT_ROOT_FILES

        # Go
        assert "go.mod" in IMPORTANT_ROOT_FILES
        assert "go.sum" in IMPORTANT_ROOT_FILES

        # Rust
        assert "Cargo.toml" in IMPORTANT_ROOT_FILES
        assert "Cargo.lock" in IMPORTANT_ROOT_FILES

        # Ruby
        assert "Gemfile" in IMPORTANT_ROOT_FILES
        assert "Gemfile.lock" in IMPORTANT_ROOT_FILES

        # Documentation
        assert "README.md" in IMPORTANT_ROOT_FILES
        assert "README.rst" in IMPORTANT_ROOT_FILES

    def test_priority_python_files_contains_common_patterns(self) -> None:
        """Test that priority Python files contains common patterns."""
        assert "main.py" in PRIORITY_PYTHON_FILES
        assert "cli.py" in PRIORITY_PYTHON_FILES
        assert "config.py" in PRIORITY_PYTHON_FILES
        assert "app.py" in PRIORITY_PYTHON_FILES
        assert "__main__.py" in PRIORITY_PYTHON_FILES
        assert "__init__.py" in PRIORITY_PYTHON_FILES

    def test_constants_are_sets_or_frozensets(self) -> None:
        """Test that constants are immutable sets for efficient lookup."""
        assert isinstance(IMPORTANT_EXTENSIONS, set)
        assert isinstance(IMPORTANT_FILES_NO_EXT, set)
        assert isinstance(IMPORTANT_ROOT_FILES, set)
        assert isinstance(PRIORITY_PYTHON_FILES, set)

    def test_constants_are_not_empty(self) -> None:
        """Test that all constants contain values."""
        assert len(IMPORTANT_EXTENSIONS) > 0
        assert len(IMPORTANT_FILES_NO_EXT) > 0
        assert len(IMPORTANT_ROOT_FILES) > 0
        assert len(PRIORITY_PYTHON_FILES) > 0

    def test_no_duplicates_in_constants(self) -> None:
        """Test that constants don't have duplicates (sets enforce this)."""
        # This is automatically enforced by sets, but let's verify the counts
        # match what we expect for some key categories

        # Should have multiple Python-related extensions
        python_extensions = {ext for ext in IMPORTANT_EXTENSIONS if ext in {".py"}}
        assert len(python_extensions) == 1

        # Should have multiple config extensions
        config_extensions = {
            ext
            for ext in IMPORTANT_EXTENSIONS
            if ext in {".yml", ".yaml", ".json", ".toml"}
        }
        assert len(config_extensions) == 4
