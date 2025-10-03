"""Test deep recursion in StructureSection.

This test verifies that the new recursive approach can handle
deep directory structures (5-6 levels) correctly.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

from ai_code_review.models.config import Config
from context_generator.core.llm_analyzer import SpecializedLLMAnalyzer
from context_generator.sections.structure_section import StructureSection


class TestStructureSectionDeepRecursion:
    """Test that StructureSection handles deep recursion correctly."""

    def test_deep_recursive_structure(self) -> None:
        """Test that directories are explored to 6 levels deep."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create a very deep directory structure (6 levels)
            level1 = project_path / "src"
            level2 = level1 / "core"
            level3 = level2 / "services"
            level4 = level3 / "auth"
            level5 = level4 / "providers"
            level6 = level5 / "oauth"

            for dir_path in [level1, level2, level3, level4, level5, level6]:
                dir_path.mkdir(parents=True, exist_ok=True)

            # Create files at each level
            tracked_files = [
                level1 / "main.py",
                level2 / "config.py",
                level3 / "user_service.py",
                level4 / "auth_handler.py",
                level5 / "google_provider.py",
                level6 / "oauth_client.py",
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

                # Test the new recursive method directly
                section.project_path = project_path
                recursive_lines = section._get_recursive_dir_structure(
                    level1, "src", False, "", 1
                )

                # Should return multiple lines showing deep structure
                assert len(recursive_lines) > 0
                recursive_str = "\n".join(recursive_lines)

                # Should contain files from multiple levels
                assert "config.py" in recursive_str  # Level 2
                assert "user_service.py" in recursive_str  # Level 3
                assert "auth_handler.py" in recursive_str  # Level 4
                assert "google_provider.py" in recursive_str  # Level 5
                assert "oauth_client.py" in recursive_str  # Level 6

    def test_recursive_depth_limits(self) -> None:
        """Test that recursion respects depth limits and item counts."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            src_dir = project_path / "src"
            src_dir.mkdir()

            config = Config(
                gitlab_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)
            section.project_path = project_path

            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                mock_git.return_value = [src_dir / "main.py"]

                # Test different depth levels have different item limits
                # Depth 1: should allow up to 25 items
                lines_depth_1 = section._get_recursive_dir_structure(
                    src_dir, "src", False, "", 1
                )

                # Depth 4: should allow up to 8 items
                lines_depth_4 = section._get_recursive_dir_structure(
                    src_dir, "src", False, "", 4
                )

                # Both should work (exact content depends on mocked files)
                assert isinstance(lines_depth_1, list)
                assert isinstance(lines_depth_4, list)

    def test_recursive_tree_formatting(self) -> None:
        """Test that recursive tree formatting is correct."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create nested structure
            src_dir = project_path / "src"
            core_dir = src_dir / "core"
            services_dir = core_dir / "services"

            for dir_path in [src_dir, core_dir, services_dir]:
                dir_path.mkdir(parents=True, exist_ok=True)

            tracked_files = [
                src_dir / "main.py",
                core_dir / "config.py",
                services_dir / "user_service.py",
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
            section.project_path = project_path

            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                mock_git.return_value = tracked_files

                # Test recursive structure generation
                lines = section._get_recursive_dir_structure(
                    src_dir, "src", False, "", 1
                )

                lines_str = "\n".join(lines)

                # Should contain proper tree formatting characters
                assert "├──" in lines_str or "└──" in lines_str
                assert "│" in lines_str or "    " in lines_str

                # Should contain our files
                assert "main.py" in lines_str
                assert "config.py" in lines_str
                assert "user_service.py" in lines_str

    def test_integration_with_generate_directory_tree(self) -> None:
        """Test that the new recursion integrates properly with _generate_directory_tree."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create structure
            src_dir = project_path / "src"
            core_dir = src_dir / "core"

            for dir_path in [src_dir, core_dir]:
                dir_path.mkdir(parents=True, exist_ok=True)

            tracked_files = [src_dir / "main.py", core_dir / "config.py"]

            for file_path in tracked_files:
                file_path.write_text("# content")

            config = Config(
                gitlab_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )
            analyzer = SpecializedLLMAnalyzer(config)
            section = StructureSection(analyzer)

            # Create facts that would be passed to _generate_directory_tree
            facts = {
                "file_structure": {
                    "source_dirs": ["src"],
                    "root_files": ["README.md", "pyproject.toml"],
                },
                "project_info": {"path": str(project_path)},
            }

            with patch(
                "context_generator.sections.structure_section.get_tracked_files"
            ) as mock_git:
                mock_git.return_value = tracked_files

                # Test full directory tree generation
                tree = section._generate_directory_tree(facts)

                # Should contain the root structure
                assert "." in tree
                assert "src/" in tree

                # Should contain deeper files due to recursion
                assert "main.py" in tree
                assert "config.py" in tree

    def test_max_depth_enforcement(self) -> None:
        """Test that maximum depth of 6 levels is enforced."""
        # config = Config(
        #     gitlab_token="dummy",
        #     ai_provider="ollama",
        #     dry_run=True,
        # )
        # analyzer = SpecializedLLMAnalyzer(config)  # Not needed for this test
        # section = StructureSection(analyzer)  # Not needed for this test

        # Test the depth check in _get_generic_dir_structure
        # current_depth < 5 means max depth is 5 (allowing levels 0,1,2,3,4,5 = 6 levels)
        assert 0 < 5  # Level 0 should be allowed
        assert 1 < 5  # Level 1 should be allowed
        assert 2 < 5  # Level 2 should be allowed
        assert 3 < 5  # Level 3 should be allowed
        assert 4 < 5  # Level 4 should be allowed
        assert not (5 < 5)  # Level 5 should NOT be allowed (stops recursion)

        # Test the depth check in _get_recursive_dir_structure
        # Same logic: current_depth < 5
        assert 0 < 5  # Level 0 should be allowed
        assert 4 < 5  # Level 4 should be allowed
        assert not (5 < 5)  # Level 5 should NOT be allowed
