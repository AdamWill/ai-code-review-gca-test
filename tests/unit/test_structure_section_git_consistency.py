"""Test Git consistency in StructureSection.

This test verifies that StructureSection only uses Git tracked files,
addressing the filesystem vs Git inconsistency identified in code review.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

from ai_code_review.models.config import Config
from context_generator.core.llm_analyzer import SpecializedLLMAnalyzer
from context_generator.sections.structure_section import StructureSection


class TestStructureSectionGitConsistency:
    """Test that StructureSection consistently uses only Git tracked files."""

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

            # Mock get_tracked_files to return only tracked files
            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                mock_git.return_value = tracked_files

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
        """Test that Git files are cached properly to avoid multiple calls."""
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

            tracked_files = [subdir / "main.py", subdir / "config.py"]
            for file_path in tracked_files:
                file_path.write_text("# content")

            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                mock_git.return_value = tracked_files

                # Call multiple methods that should use the same cached Git files
                section._get_subdir_items(subdir, 10)
                section._get_key_items_in_dir(subdir)
                section._get_files_in_subdir(subdir)

                # get_tracked_files should only be called once due to caching
                assert mock_git.call_count == 1

    def test_project_path_auto_detection(self) -> None:
        """Test that project_path is auto-detected when not set."""
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

            # Don't set project_path manually - let it auto-detect
            tracked_files = [subdir / "main.py"]
            for file_path in tracked_files:
                file_path.write_text("# content")

            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                mock_git.return_value = tracked_files

                # This should trigger auto-detection of project_path
                items = section._get_subdir_items(subdir, 10)

                # Should have auto-detected and set project_path
                assert hasattr(section, "project_path")
                assert section.project_path is not None
                assert "main.py" in " ".join(items)
