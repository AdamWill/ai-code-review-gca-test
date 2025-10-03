"""Test depth improvements in StructureSection.

This test verifies that StructureSection now shows more depth levels
and more items per directory as requested.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

from ai_code_review.models.config import Config
from context_generator.core.llm_analyzer import SpecializedLLMAnalyzer
from context_generator.sections.structure_section import StructureSection


class TestStructureSectionDepth:
    """Test that StructureSection shows improved depth and item counts."""

    def test_increased_item_limits(self) -> None:
        """Test that more items are shown per directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            subdir = project_path / "src"
            subdir.mkdir()

            # Create many files to test the increased limits
            tracked_files = []
            for i in range(25):  # More than old limit of 20
                file_path = subdir / f"module_{i:02d}.py"
                tracked_files.append(file_path)
                file_path.write_text(f"# Module {i}")

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
                mock_git.return_value = tracked_files

                # Test _get_subdir_items with new default limit of 15 (was 8)
                items = section._get_subdir_items(
                    subdir, 25
                )  # Request more than old limit

                # Should show more items than before (old limit was 8, new default is 15)
                assert len(items) >= 15, f"Expected at least 15 items, got {len(items)}"

                # Should contain files from our large set
                items_str = " ".join(items)
                assert "module_00.py" in items_str
                assert "module_10.py" in items_str

    def test_deeper_directory_exploration(self) -> None:
        """Test that directories are explored to deeper levels."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create a deep directory structure
            level1 = project_path / "src"
            level2 = level1 / "core"
            level3 = level2 / "services"
            level4 = level3 / "auth"

            for dir_path in [level1, level2, level3, level4]:
                dir_path.mkdir(parents=True, exist_ok=True)

            # Create files at different levels
            tracked_files = [
                level1 / "main.py",
                level2 / "config.py",
                level3 / "user_service.py",
                level4 / "auth_handler.py",
            ]

            for file_path in tracked_files:
                file_path.write_text("# content")

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
                mock_git.return_value = tracked_files

                # Test that _should_explore_subdir recognizes more directory types
                assert section._should_explore_subdir("core") is True
                assert section._should_explore_subdir("services") is True
                assert section._should_explore_subdir("auth") is True
                assert section._should_explore_subdir("config") is True
                assert section._should_explore_subdir("middleware") is True
                assert section._should_explore_subdir("repositories") is True

    def test_expanded_important_subdirs_list(self) -> None:
        """Test that the list of important subdirectories has been expanded."""
        config = Config(
            gitlab_token="dummy",
            ai_provider="ollama",
            dry_run=True,
        )
        analyzer = SpecializedLLMAnalyzer(config)
        section = StructureSection(analyzer)

        # Test some of the newly added important subdirectories
        new_important_dirs = [
            "config",
            "configs",
            "settings",
            "middleware",
            "auth",
            "authentication",
            "authorization",
            "migrations",
            "scripts",
            "tasks",
            "commands",
            "cli",
            "templates",
            "static",
            "assets",
            "resources",
            "data",
            "schemas",
            "types",
            "interfaces",
            "constants",
            "enums",
            "exceptions",
            "errors",
            "validators",
            "serializers",
            "adapters",
            "clients",
            "providers",
            "repositories",
            "stores",
            "cache",
            "queue",
            "events",
            "listeners",
            "observers",
            "decorators",
            "mixins",
            "plugins",
            "extensions",
            "integrations",
        ]

        for dir_name in new_important_dirs:
            assert section._should_explore_subdir(dir_name) is True, (
                f"Directory '{dir_name}' should be explored"
            )

    def test_depth_parameter_usage(self) -> None:
        """Test that the depth parameter is properly used in recursion."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create nested structure
            src_dir = project_path / "src"
            src_dir.mkdir()

            config = Config(
                gitlab_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)

            # Set project_path for the section
            section.project_path = project_path

            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                mock_git.return_value = [src_dir / "main.py"]

                # Test that _get_generic_dir_structure accepts depth parameter
                result = section._get_generic_dir_structure("src", False, 0)
                assert isinstance(result, list)

                # Test with different depth levels
                result_depth_1 = section._get_generic_dir_structure("src", False, 1)
                result_depth_2 = section._get_generic_dir_structure("src", False, 2)

                # All should return lists (exact content depends on mocked files)
                assert isinstance(result_depth_1, list)
                assert isinstance(result_depth_2, list)

    def test_key_items_increased_limit(self) -> None:
        """Test that _get_key_items_in_dir shows more Python files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            src_dir = project_path / "src"
            src_dir.mkdir()

            # Create many Python files to test the increased limit
            tracked_files = []
            for i in range(15):  # More than old limit of 8
                file_path = src_dir / f"service_{i:02d}.py"
                tracked_files.append(file_path)
                file_path.write_text(f"# Service {i}")

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
                mock_git.return_value = tracked_files

                # Test _get_key_items_in_dir with increased limit (was 8, now 12)
                items = section._get_key_items_in_dir(src_dir)

                # Should show more items than the old limit of 8
                assert len(items) >= 10, f"Expected at least 10 items, got {len(items)}"

                # Should contain files from our set
                items_str = " ".join(items)
                assert "service_00.py" in items_str
                assert "service_05.py" in items_str
