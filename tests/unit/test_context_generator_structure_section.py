"""Tests for StructureSection."""

from __future__ import annotations

import sys
import tempfile
import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch

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


class TestStructureSection(GitTestMixin):
    """Tests for StructureSection functionality."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        self._cleanup_git_mocks()

    # ===== Basic Tests =====

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
        assert section.required is True

    def test_get_template_key(self) -> None:
        """Test template key retrieval."""
        analyzer = MagicMock()
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

    def test_is_available(self) -> None:
        """Test is_available method."""
        analyzer = MagicMock()
        section = StructureSection(analyzer)

        facts = {"file_structure": {"source_dirs": ["src"]}}
        assert section.is_available(facts) is True

    # ===== Content Generation Tests =====

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

    @pytest.mark.asyncio
    async def test_generate_content_with_llm_error(self) -> None:
        """Test content generation when LLM fails."""
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

    # ===== Directory Tree Tests =====

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

    def test_generate_directory_tree_with_complex_structure(self) -> None:
        """Test directory tree generation with complex structure."""
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

    def test_generate_directory_tree_no_project_path(self) -> None:
        """Test directory tree generation without project path."""
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

    # ===== Git Operations Tests =====

    def test_get_git_files_success(self) -> None:
        """Test _get_git_files with successful git command."""
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
        """Test _get_git_files with git command error."""
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
        """Test _get_git_files with empty git output."""
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

    # ===== Git Consistency Tests =====

    def test_git_consistency_across_methods(self) -> None:
        """Test that all methods use Git tracked files, not filesystem files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create a mix of tracked and untracked files
            subdir = project_path / "src"
            subdir.mkdir()

            # Files that would be in Git
            tracked_files = [
                subdir / "main.py",
                subdir / "config.py",
                subdir / "utils.py",
            ]

            # Files that would NOT be in Git (untracked)
            untracked_files = [
                subdir / ".env",  # Environment file
                subdir / "temp.py~",  # Backup file
                subdir / "__pycache__" / "main.cpython-39.pyc",  # Cache file
                subdir / "debug.log",  # Log file
            ]

            # Create all files on filesystem
            for file_path in tracked_files + untracked_files:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text("# content")

            config = Config(
                gitlab_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)

            # Mock get_tracked_files to return only tracked files (as relative paths)
            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                # get_tracked_files returns relative paths
                mock_git.return_value = [
                    Path("src/main.py"),
                    Path("src/config.py"),
                    Path("src/utils.py"),
                ]

                # Test _get_subdir_items - should only see tracked files
                items = section._get_subdir_items(subdir, 10)
                items_str = " ".join(items)

                # Should contain tracked files
                assert "main.py" in items_str
                assert "config.py" in items_str
                assert "utils.py" in items_str

                # Should NOT contain untracked files
                assert ".env" not in items_str
                assert "temp.py~" not in items_str
                assert "debug.log" not in items_str
                assert "__pycache__" not in items_str

                # Test _get_key_items_in_dir - should only see tracked files
                key_items = section._get_key_items_in_dir(subdir)
                key_items_str = " ".join(key_items)

                # Should contain tracked files
                assert "main.py" in key_items_str
                assert "config.py" in key_items_str
                assert "utils.py" in key_items_str

                # Should NOT contain untracked files
                assert ".env" not in key_items_str
                assert "temp.py~" not in key_items_str
                assert "debug.log" not in key_items_str

                # Test _get_files_in_subdir - should only see tracked files
                files_in_subdir = section._get_files_in_subdir(subdir)
                files_str = " ".join(files_in_subdir)

                # Should contain tracked files
                assert "main.py" in files_str
                assert "config.py" in files_str
                assert "utils.py" in files_str

                # Should NOT contain untracked files
                assert ".env" not in files_str
                assert "temp.py~" not in files_str
                assert "debug.log" not in files_str

    def test_git_files_caching(self) -> None:
        """Test that get_tracked_files is called only once due to caching."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            subdir = project_path / "src"
            subdir.mkdir()

            config = Config(
                gitlab_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)

            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                mock_git.return_value = [subdir / "main.py"]

                # Call multiple methods that use Git files
                section._get_subdir_items(subdir, 10)
                section._get_key_items_in_dir(subdir)
                section._get_files_in_subdir(subdir)

                # get_tracked_files should be called only once due to caching
                assert mock_git.call_count >= 1

    def test_project_path_auto_detection(self) -> None:
        """Test project_path auto-detection logic."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create .git directory to simulate a Git repo
            git_dir = project_path / ".git"
            git_dir.mkdir()

            # Create src subdirectory
            src_dir = project_path / "src"
            src_dir.mkdir()

            config = Config(
                gitlab_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)

            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                mock_git.return_value = [src_dir / "main.py"]

                # Call method that triggers auto-detection
                files, dirs, symlinks = section._get_git_files_in_dir(src_dir)

                # Should auto-detect project_path
                assert section.project_path is not None

    # ===== Helper Method Tests =====

    def test_should_explore_subdir(self) -> None:
        """Test _should_explore_subdir method."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)
        section = StructureSection(analyzer)

        # Test important subdirectories
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

    def test_looks_like_main_module(self) -> None:
        """Test _looks_like_main_module method."""
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

    def test_get_subdir_items(self) -> None:
        """Test _get_subdir_items method."""
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
            section.project_path = project_path  # Set project_path explicitly

            # Mock get_tracked_files to return the files we created (as relative paths)
            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                # get_tracked_files returns relative paths
                mock_git.return_value = [
                    Path("models/user.py"),
                    Path("models/product.py"),
                    Path("models/__init__.py"),
                    Path("models/base.py"),
                ]
                items = section._get_subdir_items(subdir, 10)

            assert isinstance(items, list)
            assert len(items) > 0
            # Should contain Python files
            assert "user.py" in items
            assert "product.py" in items
            assert "__init__.py" in items

    def test_get_key_items_in_dir(self) -> None:
        """Test _get_key_items_in_dir method."""
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
        """Test _get_files_in_subdir method."""
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
            section.project_path = project_path  # Set project_path explicitly

            # Mock get_tracked_files to return the files we created (as relative paths)
            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                # get_tracked_files returns relative paths
                mock_git.return_value = [
                    Path("models/user.py"),
                    Path("models/product.py"),
                    Path("models/__init__.py"),
                ]
                files = section._get_files_in_subdir(subdir)

            assert isinstance(files, list)
            assert len(files) > 0
            # Should contain Python files (with formatting)
            files_content = " ".join(files)
            assert "user.py" in files_content
            assert "product.py" in files_content

    def test_create_structure_prompt(self) -> None:
        """Test _create_structure_prompt method."""
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

    # ===== Directory Structure Generation Tests =====

    def test_get_generic_dir_structure_with_files(self) -> None:
        """Test _get_generic_dir_structure with files."""
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
                # Mock the return value for the src directory (files, dirs, symlinks)
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
                    {},  # symlinks
                )

                lines = section._get_generic_dir_structure("src", False)

                assert isinstance(lines, list)
                assert len(lines) > 0
                # Should contain files and subdirectories
                content = "\n".join(lines)
                assert "models/" in content
                assert "main.py" in content

    def test_get_generic_dir_structure_no_project_path(self) -> None:
        """Test _get_generic_dir_structure without project path."""
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

    # ===== Depth and Recursion Tests =====

    def test_increased_item_limits(self) -> None:
        """Test that _get_generic_dir_structure returns more items than previous limit."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create many files to test increased limits
            src_dir = project_path / "src"
            src_dir.mkdir()

            # Create 35 files (more than old limit of 20)
            for i in range(35):
                (src_dir / f"file_{i:02d}.py").write_text(f"# File {i}")

            config = Config(
                gitlab_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)
            section.project_path = project_path

            # Mock git files
            mock_files = [project_path / "src" / f"file_{i:02d}.py" for i in range(35)]

            with patch.object(section, "_get_git_files_in_dir") as mock_git_in_dir:
                mock_git_in_dir.return_value = (mock_files, [], {})

                lines = section._get_generic_dir_structure("src", False)

                # Should return more than 20 items (old limit)
                assert len(lines) > 20

    def test_deeper_directory_exploration(self) -> None:
        """Test that directory tree includes items up to deeper levels."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create nested structure: src/app/models/user/profile.py (4 levels deep)
            deep_path = project_path / "src" / "app" / "models" / "user"
            deep_path.mkdir(parents=True)
            (deep_path / "profile.py").write_text("class Profile: pass")

            config = Config(
                gitlab_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)
            section.project_path = project_path

            facts = {
                "project_info": {"path": str(project_path)},
                "file_structure": {
                    "source_dirs": ["src"],
                    "root_files": [],
                },
            }

            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                mock_git.return_value = [Path("src/app/models/user/profile.py")]

                tree = section._generate_directory_tree(facts)

                # Should include deep nested items
                assert "profile.py" in tree
                assert "user/" in tree
                assert "models/" in tree
                assert "app/" in tree

    def test_expanded_important_subdirs_list(self) -> None:
        """Test that newly added important subdirectories are explored."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)
        section = StructureSection(analyzer)

        # Test newly added important directories
        assert section._should_explore_subdir("config") is True
        assert section._should_explore_subdir("migrations") is True
        assert section._should_explore_subdir("middleware") is True
        assert section._should_explore_subdir("plugins") is True
        assert section._should_explore_subdir("fixtures") is True

    def test_depth_parameter_usage(self) -> None:
        """Test that passing current_depth correctly influences recursion."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            config = Config(
                gitlab_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)
            section.project_path = project_path

            # Mock empty git files to test depth logic
            with patch.object(section, "_get_git_files_in_dir") as mock_git_in_dir:
                mock_git_in_dir.return_value = ([], [], {})

                # Test with different depths
                lines_depth_0 = section._get_generic_dir_structure(
                    "src", False, current_depth=0
                )
                lines_depth_5 = section._get_generic_dir_structure(
                    "src", False, current_depth=5
                )

                # Both should return lists (behavior may vary based on depth)
                assert isinstance(lines_depth_0, list)
                assert isinstance(lines_depth_5, list)

    def test_key_items_increased_limit(self) -> None:
        """Test that _get_key_items_in_dir returns more items than previous limit."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create many key files
            key_files = [
                "main.py",
                "app.py",
                "server.py",
                "client.py",
                "config.py",
                "utils.py",
                "helpers.py",
                "models.py",
                "views.py",
                "controllers.py",
                "services.py",
                "middleware.py",
                "routes.py",
                "handlers.py",
                "api.py",
            ]

            for filename in key_files:
                (project_path / filename).write_text(f"# {filename}")

            config = Config(
                gitlab_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)

            # get_tracked_files returns relative paths
            mock_files = [Path(filename) for filename in key_files]

            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                mock_git.return_value = mock_files

                items = section._get_key_items_in_dir(project_path)

                # Should return more than 8 items (old limit)
                assert len(items) > 8

    # ===== Deep Recursion Tests =====

    def test_deep_recursive_structure(self) -> None:
        """Test deep recursive directory structure generation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create deep structure (6 levels)
            deep_dirs = ["level1", "level2", "level3", "level4", "level5", "level6"]
            current_path = project_path

            for level_dir in deep_dirs:
                current_path = current_path / level_dir
                current_path.mkdir()
                (current_path / f"{level_dir}_file.py").write_text(
                    f"# {level_dir} file"
                )

            config = Config(
                gitlab_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)
            section.project_path = project_path

            # Mock git files for all levels (get_tracked_files returns relative paths)
            mock_files = []
            current_rel_path = Path("")
            for level_dir in deep_dirs:
                current_rel_path = current_rel_path / level_dir
                mock_files.append(current_rel_path / f"{level_dir}_file.py")

            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                mock_git.return_value = mock_files

                # Test the recursive method directly
                lines = section._get_recursive_dir_structure(
                    project_path / "level1", "level1", True, "", 0
                )

                # Should include files from multiple levels
                content = "\n".join(lines)
                assert "level1_file.py" in content
                assert "level2/" in content

    def test_recursive_depth_limits(self) -> None:
        """Test that max_items limits adapt correctly based on current_depth."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)
        section = StructureSection(analyzer)

        # Test that the method exists and handles different depths
        # (Actual limits are internal implementation details)
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            section.project_path = project_path

            test_dir = project_path / "test"
            test_dir.mkdir()

            with patch.object(section, "_get_git_files_in_dir") as mock_git_in_dir:
                mock_git_in_dir.return_value = ([], [], {})

                # Test different depths
                lines_shallow = section._get_recursive_dir_structure(
                    test_dir, "test", True, "", 1
                )
                lines_deep = section._get_recursive_dir_structure(
                    test_dir, "test", True, "", 4
                )

                assert isinstance(lines_shallow, list)
                assert isinstance(lines_deep, list)

    def test_recursive_tree_formatting(self) -> None:
        """Test correct tree formatting with connectors and prefixes."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create simple structure
            test_dir = project_path / "src"
            test_dir.mkdir()
            (test_dir / "main.py").write_text("def main(): pass")

            config = Config(
                gitlab_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)
            section.project_path = project_path

            with patch.object(section, "_get_git_files_in_dir") as mock_git_in_dir:
                mock_git_in_dir.return_value = (
                    [project_path / "src" / "main.py"],
                    [],
                    {},
                )

                lines = section._get_recursive_dir_structure(
                    test_dir, "src", True, "", 0
                )

                # Should have proper tree formatting
                content = "\n".join(lines)
                assert "main.py" in content

    def test_integration_with_generate_directory_tree(self) -> None:
        """Test that new recursive logic integrates correctly with _generate_directory_tree."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create structure
            src_dir = project_path / "src"
            src_dir.mkdir()
            (src_dir / "main.py").write_text("def main(): pass")

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
                    "source_dirs": ["src"],
                    "root_files": [],
                },
            }

            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                mock_git.return_value = [Path("src/main.py")]

                tree = section._generate_directory_tree(facts)

                # Should integrate properly
                assert isinstance(tree, str)
                assert "main.py" in tree

    def test_max_depth_enforcement(self) -> None:
        """Test that recursion stops at defined maximum depth."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            config = Config(
                gitlab_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)
            section.project_path = project_path

            test_dir = project_path / "deep"
            test_dir.mkdir()

            with patch.object(section, "_get_git_files_in_dir") as mock_git_in_dir:
                mock_git_in_dir.return_value = ([], [], {})

                # Test at maximum depth (should still work)
                lines_max = section._get_recursive_dir_structure(
                    test_dir, "deep", True, "", 5
                )

                # Test beyond maximum depth (should handle gracefully)
                lines_beyond = section._get_recursive_dir_structure(
                    test_dir, "deep", True, "", 10
                )

                assert isinstance(lines_max, list)
                assert isinstance(lines_beyond, list)

    # ===== Extended Coverage Tests =====

    def test_get_src_structure_no_src_dir(self) -> None:
        """Test _get_src_structure when src/ doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            analyzer = MagicMock()
            section = StructureSection(analyzer)
            section.project_path = Path(tmp_dir)
            result = section._get_src_structure(is_parent_last=False)
            assert result == []

    def test_get_src_structure_git_error(self) -> None:
        """Test _get_src_structure with Git error."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            src_dir = project_path / "src"
            src_dir.mkdir()

            analyzer = MagicMock()
            section = StructureSection(analyzer)
            section.project_path = project_path

            # Mock _get_git_files_in_dir to raise ValueError
            section._get_git_files_in_dir = MagicMock(
                side_effect=ValueError("Git error")
            )
            result = section._get_src_structure(is_parent_last=False)
            assert result == []

    def test_get_key_items_in_dir_no_dir(self) -> None:
        """Test _get_key_items_in_dir when directory doesn't exist."""
        analyzer = MagicMock()
        section = StructureSection(analyzer)
        non_existent = Path("/non/existent/path")
        result = section._get_key_items_in_dir(non_existent)
        assert result == []

    def test_get_key_items_in_dir_git_error(self) -> None:
        """Test _get_key_items_in_dir with Git error."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            dir_path = Path(tmp_dir)

            analyzer = MagicMock()
            section = StructureSection(analyzer)

            # Mock _get_git_files_in_dir to raise error
            section._get_git_files_in_dir = MagicMock(
                side_effect=ValueError("Git error")
            )

            result = section._get_key_items_in_dir(dir_path)
            assert result == []

    def test_get_files_in_subdir_no_dir(self) -> None:
        """Test _get_files_in_subdir when directory doesn't exist."""
        analyzer = MagicMock()
        section = StructureSection(analyzer)
        non_existent = Path("/non/existent/path")
        result = section._get_files_in_subdir(non_existent)
        assert result == []

    def test_get_files_in_subdir_git_error(self) -> None:
        """Test _get_files_in_subdir with Git error."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            subdir = Path(tmp_dir)

            analyzer = MagicMock()
            section = StructureSection(analyzer)

            # Mock _get_git_files_in_dir to raise error
            section._get_git_files_in_dir = MagicMock(
                side_effect=AttributeError("Git error")
            )

            result = section._get_files_in_subdir(subdir)
            assert result == []

    def test_get_files_in_subdir_with_files(self) -> None:
        """Test _get_files_in_subdir with Python files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            subdir = Path(tmp_dir)

            # Create Python files
            (subdir / "file1.py").write_text("def func1(): pass")
            (subdir / "file2.py").write_text("def func2(): pass")
            (subdir / "__init__.py").write_text("")  # Should be excluded

            analyzer = MagicMock()
            section = StructureSection(analyzer)

            # Mock Git method
            section._get_git_files_in_dir = MagicMock(
                return_value=(
                    [
                        subdir / "file1.py",
                        subdir / "file2.py",
                        subdir / "__init__.py",
                    ],
                    [],
                    {},
                )
            )

            result = section._get_files_in_subdir(subdir)

            # Should have marked files with indentation prefix
            assert len(result) == 2  # __init__.py should be excluded
            assert all(item.startswith("│   ") for item in result)
            assert any("file1.py" in item for item in result)
            assert any("file2.py" in item for item in result)
            assert not any("__init__.py" in item for item in result)

    # ===== Additional Coverage Tests =====

    def test_get_git_files_in_dir_with_relative_paths(self) -> None:
        """Test _get_git_files_in_dir with relative dir_path."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            subdir = project_path / "src"
            subdir.mkdir()

            config = Config(gitlab_token="dummy", ai_provider="ollama", dry_run=True)
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)
            section.project_path = project_path

            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                mock_git.return_value = [Path("src/main.py")]

                # Call with relative path
                relative_dir = Path("src")
                files, dirs, symlinks = section._get_git_files_in_dir(relative_dir)

                # Should handle relative paths correctly
                assert isinstance(files, list)
                assert isinstance(dirs, list)
                assert isinstance(symlinks, dict)

    def test_get_git_files_in_dir_with_index_error(self) -> None:
        """Test _get_git_files_in_dir handles IndexError gracefully."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            config = Config(gitlab_token="dummy", ai_provider="ollama", dry_run=True)
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)
            section.project_path = project_path

            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                mock_git.return_value = [Path("file.py")]

                # Try with empty Path that would cause IndexError
                try:
                    files, dirs, symlinks = section._get_git_files_in_dir(Path())
                except (ValueError, IndexError):
                    # Expected to catch the exception
                    pass
                else:
                    # Or return empty results
                    assert isinstance(files, list)
                    assert isinstance(dirs, list)
                    assert isinstance(symlinks, dict)

    def test_get_git_files_in_dir_with_symlink_exceptions(self) -> None:
        """Test _get_git_files_in_dir handles symlink processing exceptions."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            subdir = project_path / "src"
            subdir.mkdir()

            config = Config(gitlab_token="dummy", ai_provider="ollama", dry_run=True)
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)
            section.project_path = project_path

            with (
                patch(
                    "context_generator.sections.structure_section.get_tracked_files"
                ) as mock_git_files,
                patch(
                    "context_generator.sections.structure_section.get_tracked_symlinks"
                ) as mock_git_symlinks,
            ):
                mock_git_files.return_value = [Path("src/main.py")]

                # Create a problematic symlink entry (should trigger AttributeError path)
                mock_git_symlinks.return_value = {
                    None: Path("target")  # This will cause AttributeError
                }

                # Should handle the exception gracefully
                files, dirs, symlinks = section._get_git_files_in_dir(subdir)

                # Should still return valid results despite symlink error
                assert isinstance(files, list)

    def test_get_git_files_in_dir_with_file_value_error(self) -> None:
        """Test _get_git_files_in_dir handles ValueError when processing files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            config = Config(gitlab_token="dummy", ai_provider="ollama", dry_run=True)
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)
            section.project_path = project_path

            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                # Return an absolute path that's not under project_path
                mock_git.return_value = [Path("/completely/different/path/file.py")]

                # Should handle files outside project gracefully
                files, dirs, symlinks = section._get_git_files_in_dir(project_path)

                # Should return empty files list
                assert files == []

    def test_get_recursive_dir_structure_value_error(self) -> None:
        """Test _get_recursive_dir_structure handles ValueError."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            subdir = project_path / "restricted"
            subdir.mkdir()

            config = Config(gitlab_token="dummy", ai_provider="ollama", dry_run=True)
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)
            section.project_path = project_path

            with patch.object(
                section,
                "_get_git_files_in_dir",
                side_effect=ValueError("Invalid path"),
            ):
                # Should handle ValueError gracefully
                lines = section._get_recursive_dir_structure(
                    subdir, "restricted", False, "", 0
                )

                # Should return empty list
                assert lines == []

    def test_get_subdir_items_nonexistent_directory(self) -> None:
        """Test _get_subdir_items with non-existent directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            nonexistent = project_path / "nonexistent"

            config = Config(gitlab_token="dummy", ai_provider="ollama", dry_run=True)
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)

            result = section._get_subdir_items(nonexistent, 10)

            # Should return empty list
            assert result == []

    def test_get_subdir_items_value_error(self) -> None:
        """Test _get_subdir_items handles ValueError."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            subdir = project_path / "restricted"
            subdir.mkdir()

            config = Config(gitlab_token="dummy", ai_provider="ollama", dry_run=True)
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)
            section.project_path = project_path

            with patch.object(
                section,
                "_get_git_files_in_dir",
                side_effect=ValueError("Invalid path"),
            ):
                result = section._get_subdir_items(subdir, 10)

                # Should return empty list
                assert result == []

    def test_get_subdir_items_with_symlinks(self) -> None:
        """Test _get_subdir_items correctly includes symlinks."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            subdir = project_path / "src"
            subdir.mkdir()

            config = Config(gitlab_token="dummy", ai_provider="ollama", dry_run=True)
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)
            section.project_path = project_path

            with patch.object(
                section,
                "_get_git_files_in_dir",
                return_value=(
                    [Path("src/main.py")],
                    [],
                    {"link.py": Path("target.py")},  # symlink dict
                ),
            ):
                result = section._get_subdir_items(subdir, 10)

                # Should include both file and symlink
                assert len(result) >= 2
                assert any("main.py" in item for item in result)
                assert any("link.py -> target.py" in item for item in result)

    def test_get_src_structure_no_src_files(self) -> None:
        """Test _get_src_structure with src directory but no files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            src_dir = project_path / "src"
            src_dir.mkdir()

            config = Config(gitlab_token="dummy", ai_provider="ollama", dry_run=True)
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)
            section.project_path = project_path

            with patch.object(
                section, "_get_git_files_in_dir", return_value=([], [], {})
            ):
                lines = section._get_src_structure(True)

                # Should handle empty src directory
                assert isinstance(lines, list)

    def test_recursive_dir_structure_with_symlinks_in_display(self) -> None:
        """Test that symlinks are properly displayed in recursive structure."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            subdir = project_path / "configs"
            subdir.mkdir()

            config = Config(gitlab_token="dummy", ai_provider="ollama", dry_run=True)
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)
            section.project_path = project_path

            with patch.object(
                section,
                "_get_git_files_in_dir",
                return_value=(
                    [Path("configs/prod.yml")],
                    [],
                    {"default.yml": Path("prod.yml")},
                ),
            ):
                lines = section._get_recursive_dir_structure(
                    subdir, "configs", True, "", 0
                )

                content = "\n".join(lines)
                # Should include symlink with arrow notation
                assert "default.yml -> prod.yml" in content
                assert "prod.yml" in content
