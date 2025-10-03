"""Simple tests for StructureSection."""

from __future__ import annotations

# Import the GitTestMixin
import sys
import tempfile
import warnings
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_code_review.models.config import Config
from context_generator.core.llm_analyzer import SpecializedLLMAnalyzer
from context_generator.sections.structure_section import StructureSection

sys.path.append(str(Path(__file__).parent))
from test_context_generator_base import GitTestMixin

# Suppress RuntimeWarning about unawaited coroutines from async mocks
warnings.filterwarnings(
    "ignore", message=".*coroutine.*was never awaited.*", category=RuntimeWarning
)


class TestStructureSectionSimple(GitTestMixin):
    """Simple tests for StructureSection functionality."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        self._cleanup_git_mocks()

    def test_init(self) -> None:
        """Test StructureSection initialization."""
        config = Config(
            gitlab_token="dummy",
            github_token="dummy",
            ai_provider="ollama",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)
        section = StructureSection(analyzer)

        assert section.name == "structure"
        assert section.llm_analyzer == analyzer

    @pytest.mark.asyncio
    async def test_generate_content_basic(self) -> None:
        """Test basic content generation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create basic project structure
            (project_path / "README.md").write_text("# Test")
            (project_path / "pyproject.toml").write_text("[project]\nname='test'")

            src_dir = project_path / "src"
            src_dir.mkdir()
            (src_dir / "main.py").write_text("def main(): pass")

            tests_dir = project_path / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_main.py").write_text("def test(): pass")

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            config = Config(
                gitlab_token="dummy",
                github_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)
            section.project_path = project_path  # Set project path for git operations

            facts = {
                "project_info": {
                    "name": "test-project",
                    "type": "python",
                    "path": str(project_path),
                },
                "file_structure": {
                    "source_dirs": ["src", "tests"],
                    "root_files": ["README.md", "pyproject.toml"],
                },
            }
            code_samples = {"entry_point": "def main(): pass"}

            # Mock git_utils to avoid real Git calls
            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                mock_git.return_value = [
                    Path("src/main.py"),
                    Path("tests/test_main.py"),
                ]
                result = await section.generate_content(facts, code_samples)

        assert isinstance(result, str)
        assert len(result) > 0
        assert "Project Organization" in result

    def test_generate_directory_tree_basic(self) -> None:
        """Test directory tree generation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create basic project structure
            (project_path / "README.md").write_text("# Test")
            (project_path / "pyproject.toml").write_text("[project]\nname='test'")

            src_dir = project_path / "src"
            src_dir.mkdir()
            (src_dir / "main.py").write_text("def main(): pass")

            tests_dir = project_path / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_main.py").write_text("def test(): pass")

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            config = Config(
                gitlab_token="dummy",
                github_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)
            section.project_path = project_path  # Set project path for git operations

            facts = {
                "project_info": {"path": str(project_path)},
                "file_structure": {
                    "source_dirs": ["src", "tests"],
                    "root_files": ["README.md", "pyproject.toml"],
                },
            }

            # Mock git_utils to avoid real Git calls
            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                mock_git.return_value = [
                    Path("src/main.py"),
                    Path("tests/test_main.py"),
                ]
                tree = section._generate_directory_tree(facts)

        assert isinstance(tree, str)
        assert "README.md" in tree
        assert "src" in tree
        assert "tests" in tree

    def test_get_template_key(self) -> None:
        """Test template key retrieval."""
        config = Config(
            gitlab_token="dummy",
            github_token="dummy",
            ai_provider="ollama",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)
        section = StructureSection(analyzer)

        assert section.get_template_key() == "code_structure"

    def test_get_dependencies(self) -> None:
        """Test dependencies list."""
        config = Config(
            gitlab_token="dummy",
            github_token="dummy",
            ai_provider="ollama",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)
        section = StructureSection(analyzer)

        deps = section.get_dependencies()
        assert isinstance(deps, list)
        assert "file_structure" in deps
        assert "project_info" in deps

    @pytest.mark.asyncio
    async def test_generate_content_with_empty_facts(self) -> None:
        """Test content generation with minimal facts."""
        config = Config(
            gitlab_token="dummy",
            github_token="dummy",
            ai_provider="ollama",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)
        section = StructureSection(analyzer)

        facts = {
            "project_info": {
                "name": "empty-project",
                "type": "unknown",
                "path": "/tmp",
            },
            "file_structure": {"source_dirs": [], "root_files": []},
        }
        code_samples = {}

        result = await section.generate_content(facts, code_samples)

        assert isinstance(result, str)
        assert len(result) > 0
