"""Project facts extraction focused on code review needs."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

import structlog

from context_generator.constants import (
    DEPENDENCY_FILE_PATTERNS,
    GO_FRAMEWORKS,
    GO_TESTING_TOOLS,
    IMPORTANT_ROOT_FILES,
    JAVA_FRAMEWORKS,
    JAVA_TESTING_TOOLS,
    JAVASCRIPT_FRAMEWORKS,
    JAVASCRIPT_TESTING_TOOLS,
    LANGUAGE_EXTENSIONS,
    PYTHON_FRAMEWORKS,
    PYTHON_TESTING_TOOLS,
    RUBY_FRAMEWORKS,
    RUBY_TESTING_TOOLS,
    RUST_FRAMEWORKS,
    RUST_TESTING_TOOLS,
)
from context_generator.utils.git_utils import get_tracked_files, is_git_repository

logger = structlog.get_logger(__name__)


class ProjectFactsExtractor:
    """Extract facts that matter for code review understanding."""

    def __init__(self, project_path: Path, skip_git_validation: bool = False) -> None:
        """Initialize facts extractor."""
        self.project_path = project_path.resolve()
        self.skip_git_validation = skip_git_validation

        # Verify this is a git repository (unless skipped for testing)
        if not skip_git_validation and not self._is_git_repo():
            raise ValueError(
                f"Project at '{self.project_path}' is not a Git repository. "
                "The context generator requires a Git repository to ensure "
                "consistent file listing that matches what reviewers see in "
                "remote repositories (GitHub/GitLab). Please run 'git init' "
                "and commit your files, or run this tool from within a Git repository."
            )

    def extract_all_facts(self) -> dict[str, Any]:
        """Extract all facts relevant for code review."""
        return {
            "project_info": self._get_project_info(),
            "dependencies": self._get_dependency_info(),
            "file_structure": self._get_file_structure(),
            "tech_indicators": self._get_tech_indicators(),
            "documentation": self._get_key_documentation(),
        }

    def _is_git_repo(self) -> bool:
        """Check if project is a git repository."""
        return is_git_repository(self.project_path)

    def _get_git_files(self) -> list[Path]:
        """Get all tracked files from git."""
        if self.skip_git_validation:
            # In testing mode, scan all files directly
            files = []
            for f in self.project_path.rglob("*"):
                if f.is_file():
                    # Skip hidden directories but allow important dot files in root
                    parts = f.parts
                    rel_path = f.relative_to(self.project_path)

                    # Skip files in hidden directories (like .git, __pycache__)
                    if any(part.startswith(".") and part != f.name for part in parts):
                        continue

                    # Skip common build/cache directories
                    if any(
                        part
                        in ["__pycache__", ".venv", "node_modules", "dist", "build"]
                        for part in parts
                    ):
                        continue

                    try:
                        files.append(rel_path)
                    except ValueError:
                        continue
            logger.debug(
                "Got files (testing mode)",
                count=len(files),
                files=[str(f) for f in files],
            )
            return files
        else:
            # Normal mode - use Git (fail fast if Git is not available)
            return get_tracked_files(self.project_path)

    def _get_project_info(self) -> dict[str, Any]:
        """Get basic project information."""
        info = {
            "name": self.project_path.name,
            "type": "unknown",
            "path": str(
                self.project_path.resolve()
            ),  # Add resolved path for structure generation
        }

        # Try pyproject.toml
        pyproject = self.project_path / "pyproject.toml"
        if pyproject.exists():
            try:
                with open(pyproject, "rb") as f:
                    data = tomllib.load(f)
                    project_data = data.get("project", {})
                    info.update(
                        {
                            "name": project_data.get("name", info["name"]),
                            "description": project_data.get("description"),
                            "type": "python_package",
                            "python_requires": project_data.get("requires-python"),
                        }
                    )
            except Exception as e:
                logger.debug("Failed to parse pyproject.toml", error=str(e))

        # Try package.json
        package_json = self.project_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)
                    info.update(
                        {
                            "name": data.get("name", info["name"]),
                            "description": data.get("description"),
                            "type": "node_package",
                        }
                    )
            except Exception as e:
                logger.debug("Failed to parse package.json", error=str(e))

        return info

    def _get_dependency_info(self) -> dict[str, Any]:
        """Get dependency information crucial for understanding APIs/frameworks."""
        deps: dict[str, list[str]] = {
            "runtime": [],
            "dev": [],
            "frameworks": [],
            "testing": [],
        }

        # Search for dependency files recursively (not just in root)
        dependency_files = self._find_dependency_files()

        for dep_file in dependency_files:
            if dep_file.name == "pyproject.toml":
                self._parse_pyproject_toml(dep_file, deps)
            elif dep_file.name == "requirements.txt":
                self._parse_requirements_txt(dep_file, deps)
            elif dep_file.name == "package.json":
                self._parse_package_json(dep_file, deps)
            elif dep_file.name == "Gemfile":
                self._parse_gemfile(dep_file, deps)
            elif dep_file.name == "go.mod":
                self._parse_go_mod(dep_file, deps)
            elif dep_file.name == "Cargo.toml":
                self._parse_cargo_toml(dep_file, deps)
            elif dep_file.name == "pom.xml":
                self._parse_pom_xml(dep_file, deps)

        return deps

    def _find_dependency_files(self) -> list[Path]:
        """Find all dependency files from git tracked files."""
        dependency_patterns = set(DEPENDENCY_FILE_PATTERNS)
        git_files = self._get_git_files()

        found_files = []

        for file_path in git_files:
            # Check if file matches any dependency pattern
            if file_path.name in dependency_patterns:
                found_files.append(self.project_path / file_path)
            # Also check for pattern matches (like .eslintrc.*)
            for pattern in dependency_patterns:
                if "*" in pattern:
                    import fnmatch

                    if fnmatch.fnmatch(str(file_path), pattern):
                        found_files.append(self.project_path / file_path)
                        break

        return found_files

    def _parse_pyproject_toml(
        self, pyproject_file: Path, deps: dict[str, list[str]]
    ) -> None:
        """Parse pyproject.toml file for dependencies."""
        try:
            with open(pyproject_file, "rb") as f:
                data = tomllib.load(f)
                project_deps = data.get("project", {}).get("dependencies", [])

                for dep in project_deps:
                    # Keep full dependency string with version
                    deps["runtime"].append(dep)

                    # Extract name for categorization
                    dep_name = dep.split(">=")[0].split(">")[0].split("==")[0].strip()
                    self._categorize_python_dependency(dep_name, deps)

                # Development dependencies
                dev_deps = data.get("project", {}).get("optional-dependencies", {})
                for _group_name, group_deps in dev_deps.items():
                    for dep in group_deps:
                        deps["dev"].append(dep)
        except Exception as e:
            logger.debug(f"Failed to parse {pyproject_file}", error=str(e))

    def _parse_requirements_txt(
        self, req_file: Path, deps: dict[str, list[str]]
    ) -> None:
        """Parse requirements.txt file for dependencies."""
        try:
            with open(req_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("-"):
                        deps["runtime"].append(line)
                        # Extract name for categorization
                        dep_name = (
                            line.split(">=")[0].split(">")[0].split("==")[0].strip()
                        )
                        self._categorize_python_dependency(dep_name, deps)
        except Exception as e:
            logger.debug(f"Failed to parse {req_file}", error=str(e))

    def _parse_package_json(
        self, package_file: Path, deps: dict[str, list[str]]
    ) -> None:
        """Parse package.json file for dependencies."""
        try:
            with open(package_file, encoding="utf-8") as f:
                data = json.load(f)

                # Runtime dependencies
                runtime_deps = data.get("dependencies", {})
                for name, version in runtime_deps.items():
                    deps["runtime"].append(f"{name}@{version}")
                    self._categorize_js_dependency(name, deps)

                # Development dependencies
                dev_deps = data.get("devDependencies", {})
                for name, version in dev_deps.items():
                    deps["dev"].append(f"{name}@{version}")
        except Exception as e:
            logger.debug(f"Failed to parse {package_file}", error=str(e))

    def _parse_gemfile(self, gemfile: Path, deps: dict[str, list[str]]) -> None:
        """Parse Gemfile for Ruby dependencies."""
        try:
            with open(gemfile, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("gem "):
                        # Extract gem name and version
                        # gem 'name', 'version' or gem "name", "version"
                        parts = line.split(",")
                        if len(parts) >= 1:
                            gem_part = parts[0].replace("gem ", "").strip()
                            gem_name = gem_part.strip("'\"")

                            if len(parts) > 1:
                                version_part = parts[1].strip().strip("'\"")
                                deps["runtime"].append(f"{gem_name} ({version_part})")
                            else:
                                deps["runtime"].append(gem_name)

                            self._categorize_ruby_dependency(gem_name, deps)
        except Exception as e:
            logger.debug(f"Failed to parse {gemfile}", error=str(e))

    def _parse_go_mod(self, go_mod_file: Path, deps: dict[str, list[str]]) -> None:
        """Parse go.mod file for Go dependencies."""
        try:
            with open(go_mod_file, encoding="utf-8") as f:
                in_require = False
                for line in f:
                    line = line.strip()
                    if line.startswith("require ("):
                        in_require = True
                        continue
                    elif line == ")" and in_require:
                        in_require = False
                        continue
                    elif in_require or line.startswith("require "):
                        if not line.startswith("//") and " " in line:
                            parts = line.replace("require ", "").split()
                            if len(parts) >= 2:
                                module_name = parts[0]
                                deps["runtime"].append(f"{module_name} {parts[1]}")
                                self._categorize_go_dependency(module_name, deps)
        except Exception as e:
            logger.debug(f"Failed to parse {go_mod_file}", error=str(e))

    def _parse_cargo_toml(self, cargo_file: Path, deps: dict[str, list[str]]) -> None:
        """Parse Cargo.toml file for Rust dependencies."""
        try:
            with open(cargo_file, "rb") as f:
                data = tomllib.load(f)

                # Runtime dependencies
                dependencies = data.get("dependencies", {})
                for name, version in dependencies.items():
                    if isinstance(version, str):
                        deps["runtime"].append(f'{name} = "{version}"')
                    else:
                        deps["runtime"].append(name)
                    self._categorize_rust_dependency(name, deps)

                # Development dependencies
                dev_dependencies = data.get("dev-dependencies", {})
                for name, version in dev_dependencies.items():
                    if isinstance(version, str):
                        deps["dev"].append(f'{name} = "{version}"')
                    else:
                        deps["dev"].append(name)
                    self._categorize_rust_dependency(name, deps)
        except Exception as e:
            logger.debug(f"Failed to parse {cargo_file}", error=str(e))

    def _parse_pom_xml(self, pom_file: Path, deps: dict[str, list[str]]) -> None:
        """Parse pom.xml file for Java/Maven dependencies."""
        try:
            from defusedxml import ElementTree as ET

            tree = ET.parse(pom_file)
            root = tree.getroot()

            if root is None:
                return

            # Maven uses namespaces, so we need to handle that
            namespace = ""
            if root.tag.startswith("{"):
                namespace = root.tag.split("}")[0] + "}"

            # Find dependencies section
            dependencies_elem = root.find(f"{namespace}dependencies")
            if dependencies_elem is not None:
                for dep in dependencies_elem.findall(f"{namespace}dependency"):
                    artifact_id_elem = dep.find(f"{namespace}artifactId")
                    version_elem = dep.find(f"{namespace}version")
                    scope_elem = dep.find(f"{namespace}scope")

                    if artifact_id_elem is not None and artifact_id_elem.text:
                        artifact_id = artifact_id_elem.text
                        version = (
                            version_elem.text if version_elem is not None else "unknown"
                        )
                        scope = scope_elem.text if scope_elem is not None else "compile"

                        if scope == "test":
                            deps["dev"].append(f"{artifact_id}:{version}")
                        else:
                            deps["runtime"].append(f"{artifact_id}:{version}")

                        self._categorize_java_dependency(artifact_id, deps)

        except Exception as e:
            logger.debug(f"Failed to parse {pom_file}", error=str(e))

    def _categorize_ruby_dependency(
        self, gem_name: str, deps: dict[str, list[str]]
    ) -> None:
        """Categorize Ruby gems by type."""
        frameworks = RUBY_FRAMEWORKS
        testing = RUBY_TESTING_TOOLS

        if gem_name.lower() in frameworks:
            deps["frameworks"].append(gem_name)
        elif gem_name.lower() in testing:
            deps["testing"].append(gem_name)

    def _categorize_python_dependency(
        self, dep_name: str, deps: dict[str, list[str]]
    ) -> None:
        """Categorize Python dependencies by type."""
        frameworks = PYTHON_FRAMEWORKS
        testing = PYTHON_TESTING_TOOLS

        if dep_name.lower() in frameworks:
            deps["frameworks"].append(dep_name)
        elif dep_name.lower() in testing:
            deps["testing"].append(dep_name)

    def _categorize_js_dependency(
        self, package_name: str, deps: dict[str, list[str]]
    ) -> None:
        """Categorize JavaScript packages by type."""
        frameworks = JAVASCRIPT_FRAMEWORKS
        testing = JAVASCRIPT_TESTING_TOOLS

        if package_name.lower() in frameworks:
            deps["frameworks"].append(package_name)
        elif package_name.lower() in testing:
            deps["testing"].append(package_name)

    def _categorize_go_dependency(
        self, module_name: str, deps: dict[str, list[str]]
    ) -> None:
        """Categorize Go modules by type."""
        frameworks = GO_FRAMEWORKS
        testing = GO_TESTING_TOOLS

        module_lower = module_name.lower()
        if any(fw in module_lower for fw in frameworks):
            deps["frameworks"].append(module_name)
        elif any(test in module_lower for test in testing):
            deps["testing"].append(module_name)

    def _categorize_rust_dependency(
        self, crate_name: str, deps: dict[str, list[str]]
    ) -> None:
        """Categorize Rust crates by type."""
        frameworks = RUST_FRAMEWORKS
        testing = RUST_TESTING_TOOLS

        if crate_name.lower() in frameworks:
            deps["frameworks"].append(crate_name)
        elif crate_name.lower() in testing:
            deps["testing"].append(crate_name)

    def _categorize_java_dependency(
        self, artifact_id: str, deps: dict[str, list[str]]
    ) -> None:
        """Categorize Java/Maven dependencies by type."""
        frameworks = JAVA_FRAMEWORKS
        testing = JAVA_TESTING_TOOLS

        artifact_lower = artifact_id.lower()
        if any(fw in artifact_lower for fw in frameworks):
            deps["frameworks"].append(artifact_id)
        elif any(test in artifact_lower for test in testing):
            deps["testing"].append(artifact_id)

    def _get_file_structure(self) -> dict[str, Any]:
        """Get project structure relevant for understanding code organization."""
        structure: dict[str, Any] = {
            "root_files": [],
            "source_dirs": [],
            "config_files": [],
            "file_counts": {},
        }

        # Get all tracked files from git
        git_files = self._get_git_files()

        # Collect directories and root files from git tracked files
        directories = set()
        root_files = set()

        for file_path in git_files:
            # Check if it's a root file (no parent directories)
            if len(file_path.parts) == 1 and file_path.name in IMPORTANT_ROOT_FILES:
                root_files.add(file_path.name)

            # Collect top-level directories
            if len(file_path.parts) > 1:
                top_dir = file_path.parts[0]
                directories.add(top_dir)

        # Update structure
        structure["root_files"] = sorted(root_files)
        structure["source_dirs"] = sorted(directories)

        # Configuration files
        config_patterns = [
            "pyproject.toml",
            "setup.cfg",
            "tox.ini",
            "pytest.ini",
            "package.json",
            "tsconfig.json",
            "webpack.config.js",
            ".eslintrc.*",
            ".prettierrc.*",
            "ruff.toml",
            ".github/workflows/*.yml",
            ".gitlab-ci.yml",
        ]

        # Configuration files from git tracked files
        config_files = []
        for file_path in git_files:
            file_str = str(file_path)
            for pattern in config_patterns:
                if pattern.endswith("*"):
                    # Handle wildcard patterns like .eslintrc.*
                    base_pattern = pattern[:-1]  # Remove the *
                    if base_pattern in file_str:
                        config_files.append(file_str)
                        break
                elif "*" in pattern:
                    # Handle patterns like .github/workflows/*.yml
                    import fnmatch

                    if fnmatch.fnmatch(file_str, pattern):
                        config_files.append(file_str)
                        break
                else:
                    # Exact match
                    if file_path.name == pattern or file_str == pattern:
                        config_files.append(file_str)
                        break

        structure["config_files"] = sorted(config_files)

        # File type counts (for understanding project scope)
        file_counts: dict[str, int] = {}
        for file_path in git_files:
            ext = file_path.suffix.lstrip(".")
            if ext:  # Only count files with extensions
                file_counts[ext] = file_counts.get(ext, 0) + 1

        structure["file_counts"] = file_counts

        return structure

    def _get_tech_indicators(self) -> dict[str, Any]:
        """Get technology indicators from file presence and structure."""
        indicators: dict[str, list[str]] = {
            "languages": [],
            "frameworks": [],
            "architecture": [],
            "tools": [],
            "ci_cd": [],
            "quality_tools": [],
        }

        # Get all tracked files from git
        git_files = self._get_git_files()

        # Language detection from file extensions
        file_counts: dict[str, int] = {}
        for file_path in git_files:
            ext = file_path.suffix.lstrip(".")
            if ext:
                file_counts[ext] = file_counts.get(ext, 0) + 1

        for ext, count in file_counts.items():
            if count > 3:  # Only significant presence
                if ext in LANGUAGE_EXTENSIONS:
                    language = LANGUAGE_EXTENSIONS[ext]
                    if language not in indicators["languages"]:
                        indicators["languages"].append(language)

        # Framework detection from directory presence in git files
        directories = {
            file_path.parts[0] for file_path in git_files if len(file_path.parts) > 1
        }

        if "src" in directories:
            indicators["architecture"].append("src-based")
        if "app" in directories:
            indicators["architecture"].append("app-based")
        if "tests" in directories or "test" in directories:
            indicators["architecture"].append("tested")

        # Tool detection from git tracked files
        git_file_names = {file_path.name for file_path in git_files}
        git_file_paths = {str(file_path) for file_path in git_files}

        if "pyproject.toml" in git_file_names:
            indicators["tools"].append("modern-python")
            # Check for specific tools in pyproject.toml
            try:
                with open(self.project_path / "pyproject.toml", "rb") as f:
                    data = tomllib.load(f)
                    if "tool" in data:
                        tools = data["tool"]
                        if "ruff" in tools:
                            indicators["quality_tools"].append("ruff")
                        if "mypy" in tools:
                            indicators["quality_tools"].append("mypy")
                        if "pytest" in tools:
                            indicators["quality_tools"].append("pytest")
                        if "coverage" in tools or "cov" in tools:
                            indicators["quality_tools"].append("coverage")
            except (OSError, tomllib.TOMLDecodeError):
                # File doesn't exist or is not valid TOML
                pass

        if "package.json" in git_file_names:
            indicators["tools"].append("npm")
        if "Dockerfile" in git_file_names:
            indicators["tools"].append("containerized")
        if "Containerfile" in git_file_names:
            indicators["tools"].append("containerized")
        if "docker-compose.yml" in git_file_names:
            indicators["tools"].append("docker-compose")

        # CI/CD detection
        if ".gitlab-ci.yml" in git_file_names:
            indicators["ci_cd"].append("gitlab-ci")
        if any(path.startswith(".github/workflows/") for path in git_file_paths):
            indicators["ci_cd"].append("github-actions")
        if ".pre-commit-config.yaml" in git_file_names:
            indicators["quality_tools"].append("pre-commit")

        return indicators

    def _get_key_documentation(self) -> dict[str, str]:
        """Get documentation that helps understand project purpose and patterns."""
        docs = {}

        # README (most important for understanding)
        readme_files = ["README.md", "README.rst", "README.txt", "README"]
        for readme_name in readme_files:
            readme_path = self.project_path / readme_name
            if readme_path.exists():
                try:
                    content = readme_path.read_text(encoding="utf-8", errors="ignore")
                    # Take first 1500 chars - enough for purpose, not overwhelming
                    docs["README"] = content[:1500]
                    if len(content) > 1500:
                        docs["README"] += "..."
                    break
                except Exception as e:
                    logger.debug(f"Failed to read {readme_name}", error=str(e))

        # Architecture/design docs if present
        arch_files = ["ARCHITECTURE.md", "DESIGN.md", "docs/architecture.md"]
        for arch_file in arch_files:
            arch_path = self.project_path / arch_file
            if arch_path.exists():
                try:
                    content = arch_path.read_text(encoding="utf-8", errors="ignore")
                    docs["ARCHITECTURE"] = content[:1000]
                    if len(content) > 1000:
                        docs["ARCHITECTURE"] += "..."
                    break
                except Exception as e:
                    logger.debug(f"Failed to read {arch_file}", error=str(e))

        return docs
