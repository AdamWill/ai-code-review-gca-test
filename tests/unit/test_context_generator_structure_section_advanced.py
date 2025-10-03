"""Advanced tests for StructureSection to improve coverage."""

from __future__ import annotations

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


class TestStructureSectionAdvanced(GitTestMixin):
    """Advanced tests for StructureSection to improve coverage."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        self._cleanup_git_mocks()

    def test_get_git_files_success(self) -> None:
        """Test _get_git_files with successful git command - hits lines 53-66."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create files
            (project_path / "file1.py").write_text("# File 1")
            (project_path / "file2.py").write_text("# File 2")

            # Create git repo
            self._create_fast_git_repo(project_path, ["file1.py", "file2.py"])

            config = Config(
                gitlab_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)

            # Mock successful git_utils call
            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                mock_git.return_value = [Path("file1.py"), Path("file2.py")]

                files = section._get_git_files(project_path)

                assert len(files) == 2
                assert Path("file1.py") in files
                assert Path("file2.py") in files

    def test_get_git_files_error(self) -> None:
        """Test _get_git_files with git command error - hits lines 65-66."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            config = Config(
                gitlab_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)

            # Mock failed git_utils call
            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                mock_git.return_value = []

                files = section._get_git_files(project_path)

                assert files == []

    def test_get_git_files_empty_output(self) -> None:
        """Test _get_git_files with empty git output - hits line 63."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            config = Config(
                gitlab_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)

            # Mock git_utils with empty output
            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                mock_git.return_value = []

                files = section._get_git_files(project_path)

                assert files == []

    def test_generate_directory_tree_with_complex_structure(self) -> None:
        """Test directory tree generation with complex structure - hits lines 87-112."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create complex structure
            (project_path / "README.md").write_text("# Test")
            (project_path / "pyproject.toml").write_text("[project]\nname='test'")
            (project_path / "Dockerfile").write_text("FROM python:3.9")

            # Multiple source directories
            for dir_name in ["src", "tests", "docs", "scripts"]:
                dir_path = project_path / dir_name
                dir_path.mkdir()
                (dir_path / f"{dir_name}_file.py").write_text(f"# {dir_name} file")

            self._create_fast_git_repo(project_path)

            config = Config(
                gitlab_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)

            facts = {
                "project_info": {"path": str(project_path)},
                "file_structure": {
                    "source_dirs": ["src", "tests", "docs", "scripts"],
                    "root_files": ["README.md", "pyproject.toml", "Dockerfile"],
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
            assert "src/" in tree
            assert "tests/" in tree
            assert "docs/" in tree
            assert "scripts/" in tree
            assert "README.md" in tree
            assert "pyproject.toml" in tree
            assert "Dockerfile" in tree

    def test_get_generic_dir_structure_with_files(self) -> None:
        """Test _get_generic_dir_structure with files - hits lines 114-193."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create src directory with files
            src_dir = project_path / "src"
            src_dir.mkdir()
            (src_dir / "main.py").write_text("def main(): pass")
            (src_dir / "utils.py").write_text("def util(): pass")
            (src_dir / "__init__.py").write_text("")
            (src_dir / "config.json").write_text("{}")

            # Create subdirectory
            subdir = src_dir / "models"
            subdir.mkdir()
            (subdir / "user.py").write_text("class User: pass")

            self._create_fast_git_repo(
                project_path,
                [
                    "src/main.py",
                    "src/utils.py",
                    "src/__init__.py",
                    "src/config.json",
                    "src/models/user.py",
                ],
            )

            config = Config(
                gitlab_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)
            section.project_path = project_path

            # Mock git files in dir (used by the new recursive method)
            with patch.object(section, "_get_git_files_in_dir") as mock_git_in_dir:
                # Mock the return value for the src directory
                mock_git_in_dir.return_value = (
                    [  # files
                        project_path / "src" / "main.py",
                        project_path / "src" / "utils.py",
                        project_path / "src" / "__init__.py",
                        project_path / "src" / "config.json",
                    ],
                    [  # directories
                        project_path / "src" / "models"
                    ],
                )

                lines = section._get_generic_dir_structure("src", False)

                assert isinstance(lines, list)
                assert len(lines) > 0
                # Should contain files and subdirectories
                content = "\n".join(lines)
                assert "models/" in content
                assert "main.py" in content

    def test_should_explore_subdir(self) -> None:
        """Test _should_explore_subdir method - hits lines 195-230."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)
        section = StructureSection(analyzer)

        # Test important subdirectories (based on actual implementation)
        assert section._should_explore_subdir("jobs") is True
        assert section._should_explore_subdir("models") is True
        assert section._should_explore_subdir("views") is True
        assert section._should_explore_subdir("controllers") is True
        assert section._should_explore_subdir("services") is True
        assert section._should_explore_subdir("utils") is True
        assert section._should_explore_subdir("helpers") is True
        assert section._should_explore_subdir("lib") is True
        assert section._should_explore_subdir("core") is True
        assert section._should_explore_subdir("api") is True
        assert section._should_explore_subdir("components") is True

        # Test directories that should not be explored
        assert section._should_explore_subdir("__pycache__") is False
        assert section._should_explore_subdir(".git") is False
        assert section._should_explore_subdir("node_modules") is False

    def test_get_subdir_items(self) -> None:
        """Test _get_subdir_items method - hits lines 235-249."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create subdirectory with files
            subdir = project_path / "models"
            subdir.mkdir()
            (subdir / "user.py").write_text("class User: pass")
            (subdir / "product.py").write_text("class Product: pass")
            (subdir / "__init__.py").write_text("")
            (subdir / "base.py").write_text("class Base: pass")

            config = Config(
                gitlab_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)

            # Mock get_tracked_files to return the files we created
            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                mock_git.return_value = [
                    subdir / "user.py",
                    subdir / "product.py",
                    subdir / "__init__.py",
                    subdir / "base.py",
                ]
                items = section._get_subdir_items(subdir, 10)

            assert isinstance(items, list)
            assert len(items) > 0
            # Should contain Python files
            assert "user.py" in items
            assert "product.py" in items
            assert "__init__.py" in items

    def test_create_structure_prompt(self) -> None:
        """Test _create_structure_prompt method - hits lines 389+."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)
        section = StructureSection(analyzer)

        facts = {
            "project_info": {
                "name": "test-project",
                "type": "python",
            },
            "file_structure": {
                "source_dirs": ["src", "tests"],
                "root_files": ["README.md"],
            },
        }
        code_samples = {"entry_point": "def main(): pass"}
        structure_tree = ".\n├── src/\n└── README.md"

        prompt = section._create_structure_prompt(facts, code_samples, structure_tree)

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        # The prompt contains the structure tree and code samples
        assert structure_tree in prompt
        assert "def main(): pass" in prompt

    def test_get_key_items_in_dir(self) -> None:
        """Test _get_key_items_in_dir method - hits lines 330+."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create various files
            (project_path / "main.py").write_text("def main(): pass")
            (project_path / "config.json").write_text("{}")
            (project_path / "README.md").write_text("# Test")
            (project_path / "requirements.txt").write_text("requests")
            (project_path / "__init__.py").write_text("")

            config = Config(
                gitlab_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)

            # Mock get_tracked_files to return the files we created
            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                mock_git.return_value = [
                    project_path / "main.py",
                    project_path / "config.json",
                    project_path / "README.md",
                    project_path / "requirements.txt",
                    project_path / "__init__.py",
                ]
                items = section._get_key_items_in_dir(project_path)

            assert isinstance(items, list)
            assert len(items) > 0

    def test_get_files_in_subdir(self) -> None:
        """Test _get_files_in_subdir method - hits lines 370+."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create subdirectory with files
            subdir = project_path / "models"
            subdir.mkdir()
            (subdir / "user.py").write_text("class User: pass")
            (subdir / "product.py").write_text("class Product: pass")
            (subdir / "__init__.py").write_text("")

            config = Config(
                gitlab_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)

            # Mock get_tracked_files to return the files we created
            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                mock_git.return_value = [
                    subdir / "user.py",
                    subdir / "product.py",
                    subdir / "__init__.py",
                ]
                files = section._get_files_in_subdir(subdir)

            assert isinstance(files, list)
            assert len(files) > 0
            # Should contain Python files (with formatting)
            files_content = " ".join(files)
            assert "user.py" in files_content
            assert "product.py" in files_content

    def test_looks_like_main_module(self) -> None:
        """Test _looks_like_main_module method - hits lines 232+."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)
        section = StructureSection(analyzer)

        # Test directories that should be skipped
        assert section._looks_like_main_module("__pycache__") is False
        assert section._looks_like_main_module(".git") is False
        assert section._looks_like_main_module("node_modules") is False
        assert section._looks_like_main_module("venv") is False
        assert section._looks_like_main_module(".venv") is False
        assert section._looks_like_main_module("dist") is False
        assert section._looks_like_main_module("build") is False

        # Test directories that could be main modules
        assert section._looks_like_main_module("my_app") is True
        assert section._looks_like_main_module("project_core") is True

    def test_generate_directory_tree_no_project_path(self) -> None:
        """Test directory tree generation without project path - hits fallback."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)
        section = StructureSection(analyzer)

        facts = {
            "project_info": {},  # No path
            "file_structure": {
                "source_dirs": ["src"],
                "root_files": ["README.md"],
            },
        }

        # Mock git_utils to avoid real Git calls
        with patch(
            "context_generator.sections.structure_section.get_tracked_files"
        ) as mock_git:
            mock_git.return_value = [Path("src/main.py"), Path("README.md")]
            tree = section._generate_directory_tree(facts)

        assert isinstance(tree, str)
        assert "src/" in tree
        assert "README.md" in tree

    def test_get_generic_dir_structure_no_project_path(self) -> None:
        """Test _get_generic_dir_structure without project path - hits lines 121."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)
        section = StructureSection(analyzer)
        # Don't set project_path to test fallback

        with patch.object(section, "_get_git_files") as mock_git:
            mock_git.return_value = []

            lines = section._get_generic_dir_structure("src", False)

            assert isinstance(lines, list)

    @pytest.mark.asyncio
    async def test_generate_content_with_llm_error(self) -> None:
        """Test content generation when LLM fails - hits error handling."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            config = Config(
                gitlab_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)

            # Mock LLM to raise an error
            with patch.object(analyzer, "call_llm") as mock_llm:
                mock_llm.side_effect = Exception("LLM Error")

                facts = {
                    "project_info": {"path": str(project_path)},
                    "file_structure": {"source_dirs": [], "root_files": []},
                }
                code_samples = {}

                # Should handle error gracefully
                with pytest.raises(Exception, match="LLM Error"):
                    await section.generate_content(facts, code_samples)
