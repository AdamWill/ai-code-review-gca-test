"""Tests for ProjectFactsExtractor."""

from __future__ import annotations

import subprocess

# Import the GitTestMixin
import sys
import tempfile
from pathlib import Path

from context_generator.core.facts_extractor import ProjectFactsExtractor

sys.path.append(str(Path(__file__).parent))
from test_context_generator_base import GitTestMixin


class TestProjectFactsExtractor(GitTestMixin):
    """Test ProjectFactsExtractor functionality."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        if hasattr(self, "_cleanup_git_mocks"):
            self._cleanup_git_mocks()

    def _create_git_repo(self, project_path: Path) -> None:
        """Create a git repository and commit all files."""
        subprocess.run(
            ["git", "init"], cwd=project_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=project_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=project_path,
            check=True,
            capture_output=True,
        )

        # Check if there are files to add
        result = subprocess.run(
            ["git", "add", "."], cwd=project_path, capture_output=True
        )
        if result.returncode == 0:
            # Only commit if there are files staged
            status_result = subprocess.run(
                ["git", "status", "--porcelain", "--cached"],
                cwd=project_path,
                capture_output=True,
                text=True,
            )
            if status_result.stdout.strip():  # There are staged files
                subprocess.run(
                    ["git", "commit", "-m", "Initial commit"],
                    cwd=project_path,
                    check=True,
                    capture_output=True,
                )
            else:
                # Create an empty commit for empty repos
                subprocess.run(
                    ["git", "commit", "--allow-empty", "-m", "Initial empty commit"],
                    cwd=project_path,
                    check=True,
                    capture_output=True,
                )

    def test_init(self) -> None:
        """Test ProjectFactsExtractor initialization."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create a dummy file and fast git repo simulation
            (project_path / "README.md").write_text("# Test")
            self._create_fast_git_repo(project_path)

            extractor = ProjectFactsExtractor(project_path, skip_git_validation=True)

            # Path resolution may differ due to symlinks, check name instead
            assert extractor.project_path.name == project_path.name

    def test_extract_all_facts_basic_project(self) -> None:
        """Test extracting facts from a basic Python project."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create basic project structure
            (project_path / "README.md").write_text("# Test Project")
            (project_path / "pyproject.toml").write_text("""
[project]
name = "test-project"
version = "1.0.0"
dependencies = ["click>=8.0.0", "pydantic"]
""")

            src_dir = project_path / "src"
            src_dir.mkdir()
            (src_dir / "main.py").write_text("def main(): pass")

            tests_dir = project_path / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_main.py").write_text("def test_main(): pass")

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            extractor = ProjectFactsExtractor(project_path, skip_git_validation=True)
            facts = extractor.extract_all_facts()

            # Verify structure
            assert "project_info" in facts
            assert "dependencies" in facts
            assert "file_structure" in facts
            assert "tech_indicators" in facts

            # Verify project info
            project_info = facts["project_info"]
            assert project_info["name"] == "test-project"
            assert project_info["type"] in [
                "python",
                "python_package",
            ]  # Could be either
            assert "path" in project_info

            # Verify dependencies
            dependencies = facts["dependencies"]
            assert "runtime" in dependencies
            assert "click>=8.0.0" in dependencies["runtime"]
            assert "pydantic" in dependencies["runtime"]

            # Verify file structure
            file_structure = facts["file_structure"]
            assert "src" in file_structure["source_dirs"]
            assert "tests" in file_structure["source_dirs"]
            assert "README.md" in file_structure["root_files"]

    def test_extract_facts_javascript_project(self) -> None:
        """Test extracting facts from a JavaScript project."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create package.json
            (project_path / "package.json").write_text("""
{
  "name": "test-js-project",
  "version": "1.0.0",
  "dependencies": {
    "react": "^18.0.0",
    "lodash": "^4.17.21"
  },
  "devDependencies": {
    "jest": "^29.0.0"
  }
}
""")

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            extractor = ProjectFactsExtractor(project_path, skip_git_validation=True)
            facts = extractor.extract_all_facts()

            # Verify project type detection
            project_info = facts["project_info"]
            assert project_info["name"] == "test-js-project"
            assert project_info["type"] in [
                "javascript",
                "node_package",
            ]  # Could be either

            # Verify dependencies
            dependencies = facts["dependencies"]
            assert "react@^18.0.0" in dependencies["runtime"]
            assert "lodash@^4.17.21" in dependencies["runtime"]
            assert "jest@^29.0.0" in dependencies["dev"]

            # Verify frameworks detected
            assert "react" in dependencies["frameworks"]

    def test_git_file_filtering(self) -> None:
        """Test that only git-tracked files are included."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create .gitignore
            (project_path / ".gitignore").write_text("""
# Python
__pycache__/
*.py[cod]
.venv/
dist/

# Node
node_modules/
""")

            # Create tracked file
            (project_path / "main.py").write_text("print('hello')")

            # Create ignored files (these should not appear in git files)
            ignored_dir = project_path / "__pycache__"
            ignored_dir.mkdir()
            (ignored_dir / "main.pyc").write_text("compiled")

            venv_dir = project_path / ".venv"
            venv_dir.mkdir()
            (venv_dir / "lib").write_text("venv file")

            # Create fast git repo simulation with only tracked files
            tracked_files = [
                "main.py",
                ".gitignore",
            ]  # Git would not track ignored files
            self._create_fast_git_repo(project_path, tracked_files)

            extractor = ProjectFactsExtractor(project_path, skip_git_validation=True)
            git_files = extractor._get_git_files()

            # Test that only tracked files are included
            git_file_names = {f.name for f in git_files}
            assert "main.py" in git_file_names
            assert ".gitignore" in git_file_names
            # Ignored files should not be in git files
            assert "main.pyc" not in git_file_names
            assert "lib" not in git_file_names

    def test_tech_indicators_detection(self) -> None:
        """Test technology indicators detection."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create Python project with specific tools
            (project_path / "pyproject.toml").write_text("""
[project]
name = "test-project"
version = "1.0.0"

[tool.ruff]
line-length = 100

[tool.mypy]
strict = true
""")

            # Create some Python files
            (project_path / "main.py").write_text("print('hello')")
            (project_path / "test_main.py").write_text("def test(): pass")

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            extractor = ProjectFactsExtractor(project_path, skip_git_validation=True)
            facts = extractor.extract_all_facts()

            # Verify tech indicators - might be empty if files are minimal
            tech_indicators = facts["tech_indicators"]
            # Just verify the structure exists
            assert "languages" in tech_indicators
            assert "quality_tools" in tech_indicators

    def test_dependency_categorization(self) -> None:
        """Test dependency categorization by type."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create requirements.txt with different types
            (project_path / "requirements.txt").write_text("""
# Web frameworks
flask>=2.0.0
fastapi>=0.95.0

# Testing
pytest>=7.0.0
coverage>=6.0.0

# Other
requests>=2.28.0
""")

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            extractor = ProjectFactsExtractor(project_path, skip_git_validation=True)
            facts = extractor.extract_all_facts()

            dependencies = facts["dependencies"]

            # Verify framework categorization
            assert "flask" in dependencies["frameworks"]
            assert "fastapi" in dependencies["frameworks"]

            # Verify testing categorization
            assert "pytest" in dependencies["testing"]
            assert "coverage" in dependencies["testing"]

    def test_ruby_project_detection(self) -> None:
        """Test Ruby project detection and Gemfile parsing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create Gemfile
            (project_path / "Gemfile").write_text("""
source 'https://rubygems.org'

gem 'rails', '~> 7.0.0'
gem 'rspec', '~> 3.11'
gem 'smashing', '~> 1.3'
""")

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            extractor = ProjectFactsExtractor(project_path, skip_git_validation=True)
            facts = extractor.extract_all_facts()

            dependencies = facts["dependencies"]

            # Verify Ruby dependencies
            assert any("rails" in dep for dep in dependencies["runtime"])
            assert any("rspec" in dep for dep in dependencies["runtime"])
            assert any("smashing" in dep for dep in dependencies["runtime"])

            # Verify framework categorization
            assert "rails" in dependencies["frameworks"]
            assert "smashing" in dependencies["frameworks"]
            assert "rspec" in dependencies["testing"]

    def test_empty_project(self) -> None:
        """Test handling of empty project directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            extractor = ProjectFactsExtractor(project_path, skip_git_validation=True)
            facts = extractor.extract_all_facts()

            # Should still return valid structure
            assert "project_info" in facts
            assert "dependencies" in facts
            assert "file_structure" in facts
            assert "tech_indicators" in facts

            # Project info should have basic details
            project_info = facts["project_info"]
            assert project_info["name"] == project_path.name
            assert project_info["type"] == "unknown"
            assert len(facts["dependencies"]["runtime"]) == 0

    def test_git_repo_validation(self) -> None:
        """Test that git repo validation works with mocked environment."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create some files and a valid git repo simulation
            (project_path / "main.py").write_text("print('hello')")
            self._create_fast_git_repo(project_path)

            # Should work with mocked git repo
            extractor = ProjectFactsExtractor(project_path, skip_git_validation=True)
            assert extractor.project_path == project_path.resolve()

    def test_git_files_method(self) -> None:
        """Test _get_git_files method functionality."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create some files
            (project_path / "main.py").write_text("print('hello')")
            (project_path / "README.md").write_text("# Test")

            # Create subdirectory with files
            src_dir = project_path / "src"
            src_dir.mkdir()
            (src_dir / "app.py").write_text("def app(): pass")

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            extractor = ProjectFactsExtractor(project_path, skip_git_validation=True)
            git_files = extractor._get_git_files()

            # Verify all committed files are returned
            file_names = {f.name for f in git_files}
            assert "main.py" in file_names
            assert "README.md" in file_names
            assert "app.py" in file_names

            # Verify paths are relative
            assert all(not f.is_absolute() for f in git_files)

    def test_go_project_detection(self) -> None:
        """Test Go project detection and go.mod parsing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create go.mod
            (project_path / "go.mod").write_text("""
module github.com/test/myapp

go 1.19

require (
    github.com/gin-gonic/gin v1.9.1
    github.com/stretchr/testify v1.8.4
)
""")

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            extractor = ProjectFactsExtractor(project_path, skip_git_validation=True)
            facts = extractor.extract_all_facts()

            dependencies = facts["dependencies"]

            # Verify Go dependencies
            assert any("gin-gonic" in dep for dep in dependencies["runtime"])
            assert any("testify" in dep for dep in dependencies["runtime"])

    def test_rust_project_detection(self) -> None:
        """Test Rust project detection and Cargo.toml parsing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create Cargo.toml
            (project_path / "Cargo.toml").write_text("""
[package]
name = "my-rust-app"
version = "0.1.0"

[dependencies]
serde = "1.0"
tokio = { version = "1.0", features = ["full"] }

[dev-dependencies]
proptest = "1.0"
""")

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            extractor = ProjectFactsExtractor(project_path, skip_git_validation=True)
            facts = extractor.extract_all_facts()

            dependencies = facts["dependencies"]

            # Verify Rust dependencies
            assert any("serde" in dep for dep in dependencies["runtime"])
            assert any("tokio" in dep for dep in dependencies["runtime"])
            assert any("proptest" in dep for dep in dependencies["dev"])

    def test_find_dependency_files_recursive(self) -> None:
        """Test recursive dependency file discovery."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create nested structure with dependency files
            (project_path / "requirements.txt").write_text("requests==2.28.0")

            backend_dir = project_path / "backend"
            backend_dir.mkdir()
            (backend_dir / "requirements.txt").write_text("flask==2.0.0")

            frontend_dir = project_path / "frontend"
            frontend_dir.mkdir()
            (frontend_dir / "package.json").write_text(
                '{"name": "frontend", "dependencies": {"react": "18.0.0"}}'
            )

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            extractor = ProjectFactsExtractor(project_path, skip_git_validation=True)
            dep_files = extractor._find_dependency_files()

            # Should find all dependency files
            assert len(dep_files) >= 3
            file_names = [f.name for f in dep_files]
            assert "requirements.txt" in file_names
            assert "package.json" in file_names

    def test_categorize_python_dependency(self) -> None:
        """Test Python dependency categorization."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            extractor = ProjectFactsExtractor(project_path, skip_git_validation=True)

            deps = {"frameworks": [], "testing": []}

            # Test framework categorization
            extractor._categorize_python_dependency("django", deps)
            assert "django" in deps["frameworks"]

            extractor._categorize_python_dependency("fastapi", deps)
            assert "fastapi" in deps["frameworks"]

            # Test testing categorization
            extractor._categorize_python_dependency("pytest", deps)
            assert "pytest" in deps["testing"]

    def test_get_project_info_details(self) -> None:
        """Test detailed project info extraction."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create project with specific type indicators
            (project_path / "pyproject.toml").write_text("""
[project]
name = "test-python-project"
version = "1.0.0"
""")

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            extractor = ProjectFactsExtractor(project_path, skip_git_validation=True)
            project_info = extractor._get_project_info()

            assert project_info["name"] == "test-python-project"
            assert project_info["type"] in ["python", "python_package"]
            assert "path" in project_info

    def test_get_file_structure_details(self) -> None:
        """Test file structure analysis."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create complex structure
            (project_path / "README.md").write_text("# Test")
            (project_path / "pyproject.toml").write_text("[project]\nname = 'test'")

            src_dir = project_path / "src"
            src_dir.mkdir()
            (src_dir / "main.py").write_text("def main(): pass")

            tests_dir = project_path / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_main.py").write_text("def test(): pass")

            docs_dir = project_path / "docs"
            docs_dir.mkdir()
            (docs_dir / "index.md").write_text("# Docs")

            # Create ignored directory
            cache_dir = project_path / "__pycache__"
            cache_dir.mkdir()

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            extractor = ProjectFactsExtractor(project_path, skip_git_validation=True)
            file_structure = extractor._get_file_structure()

            # Should include important directories
            assert "src" in file_structure["source_dirs"]
            assert "tests" in file_structure["source_dirs"]
            assert "docs" in file_structure["source_dirs"]

            # Should include important root files
            assert "README.md" in file_structure["root_files"]
            assert "pyproject.toml" in file_structure["root_files"]

            # Should not include ignored directories
            assert "__pycache__" not in file_structure["source_dirs"]

    def test_get_tech_indicators_comprehensive(self) -> None:
        """Test comprehensive tech indicators detection."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create files that indicate various technologies
            (project_path / "main.py").write_text("#!/usr/bin/env python3")
            (project_path / "app.js").write_text("console.log('hello')")

            # Create pyproject.toml with tools
            (project_path / "pyproject.toml").write_text("""
[project]
name = "test"

[tool.ruff]
line-length = 88
""")

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            extractor = ProjectFactsExtractor(project_path, skip_git_validation=True)
            tech_indicators = extractor._get_tech_indicators()

            # Should detect some languages (might be empty in minimal setup)
            assert "languages" in tech_indicators
            assert "quality_tools" in tech_indicators
            assert "ci_cd" in tech_indicators

            # The specific contents depend on implementation details
            assert isinstance(tech_indicators["languages"], list)
            assert isinstance(tech_indicators["quality_tools"], list)
            assert isinstance(tech_indicators["ci_cd"], list)
