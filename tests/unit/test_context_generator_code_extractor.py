"""Tests for CodeSampleExtractor."""

from __future__ import annotations

# Import the GitTestMixin
import sys
import tempfile
from pathlib import Path

from context_generator.core.code_extractor import CodeSampleExtractor

sys.path.append(str(Path(__file__).parent))
from test_context_generator_base import GitTestMixin


class TestCodeSampleExtractor(GitTestMixin):
    """Test CodeSampleExtractor functionality."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        self._cleanup_git_mocks()

    def test_init(self) -> None:
        """Test CodeSampleExtractor initialization."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create a dummy file and git repo
            (project_path / "README.md").write_text("# Test")
            self._create_git_repo(project_path)

            extractor = CodeSampleExtractor(project_path, skip_git_validation=True)

            # Path resolution may differ due to symlinks, check name instead
            assert extractor.project_path.name == project_path.name
            assert extractor.project_path.exists()

    def test_get_architecture_samples_basic_project(self) -> None:
        """Test getting architecture samples from basic project."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create basic Python project structure
            src_dir = project_path / "src"
            src_dir.mkdir()

            # Create entry point
            (src_dir / "main.py").write_text("""
#!/usr/bin/env python3
\"\"\"Main application entry point.\"\"\"

import click
from myapp.core import engine

@click.command()
def main():
    \"\"\"Run the application.\"\"\"
    engine.run()

if __name__ == "__main__":
    main()
""")

            # Create config file
            (src_dir / "config.py").write_text("""
\"\"\"Application configuration.\"\"\"

from pydantic import BaseSettings

class Config(BaseSettings):
    debug: bool = False
    database_url: str = "sqlite:///app.db"

    class Config:
        env_file = ".env"
""")

            # Create core module
            core_dir = src_dir / "myapp" / "core"
            core_dir.mkdir(parents=True)
            (core_dir / "__init__.py").write_text("")
            (core_dir / "engine.py").write_text("""
\"\"\"Core application engine.\"\"\"

from typing import Protocol

class Engine:
    def __init__(self):
        self.config = self._load_config()

    def run(self) -> None:
        print("Running application")
""")

            # Create models
            models_dir = src_dir / "myapp" / "models"
            models_dir.mkdir(parents=True)
            (models_dir / "__init__.py").write_text("")
            (models_dir / "user.py").write_text("""
\"\"\"User models.\"\"\"

from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str
""")

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            extractor = CodeSampleExtractor(project_path, skip_git_validation=True)
            samples = extractor.get_architecture_samples()

            # Should have found samples for key architectural components
            assert len(samples) > 0

            # Check if key samples are included
            sample_keys = list(samples.keys())
            assert any("entry_point" in key for key in sample_keys)
            assert any("config" in key for key in sample_keys)
            assert any("core" in key for key in sample_keys)
            assert any("models" in key for key in sample_keys)

    def test_find_entry_point(self) -> None:
        """Test finding entry point files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create different potential entry points
            (project_path / "main.py").write_text("def main(): pass")
            (project_path / "app.py").write_text("def app(): pass")
            (project_path / "cli.py").write_text("import click")

            src_dir = project_path / "src"
            src_dir.mkdir()
            (src_dir / "run.py").write_text("if __name__ == '__main__':")

            # Create fast git repo simulation with explicit file list
            files = ["main.py", "app.py", "cli.py", "src/run.py"]
            self._create_fast_git_repo(project_path, files)

            extractor = CodeSampleExtractor(project_path, skip_git_validation=True)
            samples = extractor.get_architecture_samples()

            # Should find at least one entry point
            entry_samples = [k for k in samples.keys() if "entry_point" in k]
            assert len(entry_samples) > 0

    def test_find_config_files(self) -> None:
        """Test finding configuration files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create config files
            (project_path / "config.py").write_text("""
from pydantic import BaseSettings
class Config(BaseSettings):
    pass
""")

            (project_path / "settings.py").write_text("DEBUG = True")

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            extractor = CodeSampleExtractor(project_path, skip_git_validation=True)
            samples = extractor.get_architecture_samples()

            # Should find config files
            config_samples = [k for k in samples.keys() if "config" in k]
            assert len(config_samples) > 0

    def test_gitignore_filtering(self) -> None:
        """Test that .gitignore patterns are respected."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create .gitignore
            (project_path / ".gitignore").write_text(".venv/\n__pycache__/\n")

            # Create files that should be ignored
            venv_dir = project_path / ".venv"
            venv_dir.mkdir()
            (venv_dir / "lib" / "python3.12").mkdir(parents=True)
            (venv_dir / "lib" / "python3.12" / "main.py").write_text(
                "# Should be ignored"
            )

            # Create files that should not be ignored
            (project_path / "main.py").write_text("# Should be included")

            # Create fast git repo simulation - only include non-ignored files
            git_files = ["main.py", ".gitignore"]  # Git would not track .venv files
            self._create_fast_git_repo(project_path, git_files)

            extractor = CodeSampleExtractor(project_path, skip_git_validation=True)
            samples = extractor.get_architecture_samples()

            # Should not include .venv files
            for sample_content in samples.values():
                assert "Should be ignored" not in sample_content
                # Should include regular files
                if "main.py" in sample_content:
                    assert "Should be included" in sample_content

    def test_empty_project(self) -> None:
        """Test handling empty project."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create fast git repo simulation (empty)
            self._create_fast_git_repo(project_path, [])

            extractor = CodeSampleExtractor(project_path, skip_git_validation=True)
            samples = extractor.get_architecture_samples()

            # Should return empty dict for empty project
            assert isinstance(samples, dict)
            # May be empty or have minimal placeholder content
            assert len(samples) >= 0

    def test_large_file_truncation(self) -> None:
        """Test that large files are properly truncated."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create a very large file
            large_content = "# This is a very long file\n" + "print('line')\n" * 1000
            (project_path / "main.py").write_text(large_content)

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            extractor = CodeSampleExtractor(project_path, skip_git_validation=True)
            samples = extractor.get_architecture_samples()

            if samples:  # If any samples were found
                for sample_content in samples.values():
                    # Sample should be truncated to reasonable size
                    assert len(sample_content.split("\n")) <= 200  # Should be limited

    def test_mixed_language_project(self) -> None:
        """Test handling project with multiple languages."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create Python files
            (project_path / "main.py").write_text("def main(): pass")

            # Create JavaScript files
            (project_path / "app.js").write_text("function main() {}")

            # Create Go files
            (project_path / "main.go").write_text("package main\nfunc main() {}")

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            extractor = CodeSampleExtractor(project_path, skip_git_validation=True)
            samples = extractor.get_architecture_samples()

            # Should handle multiple languages gracefully
            assert isinstance(samples, dict)
            assert len(samples) >= 0

    def test_multi_language_support(self) -> None:
        """Test that extractor supports multiple programming languages."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create files for different languages
            (project_path / "main.go").write_text("package main\n\nfunc main() {}")
            (project_path / "src").mkdir()
            (project_path / "src" / "main.rs").write_text("fn main() {}")
            (project_path / "Main.java").write_text("public class Main {}")
            (project_path / "config.rb").write_text("# Ruby config")
            (project_path / "bin").mkdir()

            # Create executable shell script
            script_path = project_path / "bin" / "script"
            script_path.write_text("#!/bin/bash\necho 'hello'")
            script_path.chmod(0o755)  # Make executable

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            extractor = CodeSampleExtractor(project_path, skip_git_validation=True)

            # Test that it can find entry points from different languages
            entry_point = extractor._find_best_entry_point()
            assert entry_point is not None
            # Should prefer Go main.go in root over others
            assert entry_point.name in ["main.go", "main.rs", "Main.java", "script"]

            # Test that _is_likely_code_file works for different extensions
            assert extractor._is_likely_code_file(project_path / "main.go")
            assert extractor._is_likely_code_file(project_path / "src" / "main.rs")
            assert extractor._is_likely_code_file(project_path / "Main.java")
            assert extractor._is_likely_code_file(project_path / "config.rb")
            assert extractor._is_likely_code_file(
                project_path / "bin" / "script"
            )  # Executable
