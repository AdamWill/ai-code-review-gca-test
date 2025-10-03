"""Code sample extraction for architectural pattern recognition."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

from context_generator.constants import (
    CONFIG_FILE_PATTERNS,
    ENTRY_POINT_PATTERNS,
    IMPORTANT_EXTENSIONS,
)
from context_generator.utils.git_utils import get_tracked_files, is_git_repository

logger = structlog.get_logger(__name__)


class CodeSampleExtractor:
    """Extract strategic code samples that reveal architectural patterns."""

    def __init__(self, project_path: Path, skip_git_validation: bool = False) -> None:
        """Initialize code sample extractor."""
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
            files = get_tracked_files(self.project_path)
            logger.debug(
                "Got git files", count=len(files), files=[str(f) for f in files]
            )
            return files

    def get_architecture_samples(self) -> dict[str, str]:
        """Get key code samples that show architectural patterns."""
        samples = {}

        # Entry points - show application structure and initialization
        entry_point = self._find_best_entry_point()
        if entry_point:
            samples["entry_point"] = self._get_code_sample(
                entry_point, max_lines=40, description="Main application entry point"
            )

        # Configuration - shows how the app is configured
        config_file = self._find_best_config_file()
        if config_file:
            samples["configuration"] = self._get_code_sample(
                config_file, max_lines=50, description="Configuration and settings"
            )

        # Core business logic - shows main patterns and architecture
        core_logic = self._find_core_logic_file()
        if core_logic:
            samples["core_logic"] = self._get_code_sample(
                core_logic, max_lines=60, description="Core business logic"
            )

        # Models/Data structures - shows data architecture
        models_file = self._find_models_file()
        if models_file:
            samples["models"] = self._get_code_sample(
                models_file, max_lines=45, description="Data models and structures"
            )

        logger.info("Extracted code samples", samples_count=len(samples))
        return samples

    def _find_best_entry_point(self) -> Path | None:
        """Find the most important entry point file."""
        candidates = ENTRY_POINT_PATTERNS

        # Get all git tracked files
        git_files = self._get_git_files()
        git_file_paths = {str(f) for f in git_files}

        for pattern in candidates:
            # Convert pattern to potential file paths and check if they exist in git
            if "*" in pattern:
                # Handle glob patterns by checking against all git files
                import fnmatch

                matches = [
                    self.project_path / f
                    for f in git_files
                    if fnmatch.fnmatch(str(f), pattern)
                ]
            else:
                # Direct file check
                potential_file = self.project_path / pattern
                matches = (
                    [potential_file] if str(Path(pattern)) in git_file_paths else []
                )

            # Filter to only code files
            valid_matches = [m for m in matches if self._is_likely_code_file(m)]

            if valid_matches:
                # Return the first match, preferring src/ over root
                return sorted(
                    valid_matches,
                    key=lambda p: (
                        0 if "src" in str(p) else 1,  # Prefer src/
                        len(str(p)),  # Prefer shorter paths
                    ),
                )[0]

        return None

    def _is_likely_code_file(self, path: Path) -> bool:
        """Check if a file is likely a code file based on extension or content."""
        if not path.is_file():
            return False

        # Check if it has a known code extension
        if path.suffix in IMPORTANT_EXTENSIONS:
            return True

        # For files without extensions (like shell scripts in bin/), check if they're executable
        # or have a shebang line
        if not path.suffix:
            try:
                # Check if file is executable (Unix-like systems)
                if path.stat().st_mode & 0o111:
                    return True

                # Check for shebang line
                with open(path, "rb") as f:
                    first_line = f.readline()
                    if first_line.startswith(b"#!"):
                        return True
            except (OSError, PermissionError):
                pass

        return False

    def _find_best_config_file(self) -> Path | None:
        """Find the most important configuration file."""
        candidates = CONFIG_FILE_PATTERNS

        for pattern in candidates:
            # Check if any git files match this pattern
            import fnmatch

            git_files = self._get_git_files()
            for file_path in git_files:
                full_path = self.project_path / file_path
                if fnmatch.fnmatch(str(file_path), pattern) or fnmatch.fnmatch(
                    str(full_path), pattern
                ):
                    return full_path

        return None

    def _find_core_logic_file(self) -> Path | None:
        """Find file containing core business logic."""
        candidates = [
            # Python core logic
            "**/engine.py",
            "**/service.py",
            "**/handler.py",
            "**/controller.py",
            "**/processor.py",
            "**/manager.py",
            "src/*/core/*.py",
            # JavaScript/TypeScript core logic
            "**/engine.js",
            "**/engine.ts",
            "**/service.js",
            "**/service.ts",
            "**/handler.js",
            "**/handler.ts",
            "**/controller.js",
            "**/controller.ts",
            # Go core logic
            "**/engine.go",
            "**/service.go",
            "**/handler.go",
            "**/controller.go",
            "pkg/*/*.go",
            "internal/*/*.go",
            # Rust core logic
            "**/engine.rs",
            "**/service.rs",
            "**/handler.rs",
            "src/lib.rs",
            "src/**/mod.rs",
            # Java core logic
            "**/Engine.java",
            "**/Service.java",
            "**/Handler.java",
            "**/Controller.java",
            "**/Manager.java",
            "src/main/java/**/service/*.java",
            "src/main/java/**/controller/*.java",
            # Ruby core logic
            "**/engine.rb",
            "**/service.rb",
            "**/handler.rb",
            "**/controller.rb",
            "lib/*/*.rb",
            # C/C++ core logic
            "**/engine.c",
            "**/engine.cpp",
            "**/service.c",
            "**/service.cpp",
            "src/*.c",
            "src/*.cpp",
            # Shell scripts
            "lib/*.sh",
        ]

        # Get all git tracked files
        git_files = self._get_git_files()

        for pattern in candidates:
            # Check if any git files match this pattern
            import fnmatch

            matching_files = []
            for file_path in git_files:
                full_path = self.project_path / file_path
                if fnmatch.fnmatch(str(file_path), pattern) or fnmatch.fnmatch(
                    str(full_path), pattern
                ):
                    matching_files.append(full_path)

            if matching_files:
                # Prefer files with more lines (likely more important)
                return max(matching_files, key=lambda p: self._get_file_line_count(p))

        return None

    def _find_models_file(self) -> Path | None:
        """Find file containing data models."""
        candidates = [
            # Python models
            "**/models.py",
            "**/model.py",
            "**/schema.py",
            "**/schemas.py",
            "src/*/models/*.py",
            # JavaScript/TypeScript models
            "**/models.js",
            "**/models.ts",
            "**/model.js",
            "**/model.ts",
            "**/schema.js",
            "**/schema.ts",
            "**/types.ts",
            "**/interfaces.ts",
            # Go models
            "**/models.go",
            "**/model.go",
            "**/types.go",
            "**/schema.go",
            "pkg/models/*.go",
            "internal/models/*.go",
            # Rust models
            "**/models.rs",
            "**/model.rs",
            "**/types.rs",
            "**/schema.rs",
            "src/models/mod.rs",
            # Java models
            "**/Models.java",
            "**/Model.java",
            "**/Entity.java",
            "**/DTO.java",
            "src/main/java/**/model/*.java",
            "src/main/java/**/entity/*.java",
            "src/main/java/**/dto/*.java",
            # Ruby models
            "**/models.rb",
            "**/model.rb",
            "app/models/*.rb",
            "lib/*/models/*.rb",
            # C/C++ models
            "**/models.h",
            "**/model.h",
            "**/types.h",
            "**/struct.h",
            "include/models.h",
            "include/types.h",
        ]

        for pattern in candidates:
            # Check if any git files match this pattern
            import fnmatch

            git_files = self._get_git_files()
            for file_path in git_files:
                full_path = self.project_path / file_path
                if fnmatch.fnmatch(str(file_path), pattern) or fnmatch.fnmatch(
                    str(full_path), pattern
                ):
                    return full_path

        return None

    def _get_code_sample(
        self, file_path: Path, max_lines: int = 50, description: str = ""
    ) -> str:
        """Extract meaningful code sample from file."""
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            if not lines:
                return f"# {description}\n# File is empty"

            # Take meaningful sample from the beginning
            sample_lines: list[str] = []
            current_lines = 0

            for line in lines:
                if current_lines >= max_lines:
                    break

                # Skip empty lines at the beginning
                if not sample_lines and not line.strip():
                    continue

                sample_lines.append(line.rstrip())
                current_lines += 1

            sample = "\n".join(sample_lines)

            # Add truncation indicator if needed
            if len(lines) > max_lines:
                sample += f"\n\n# ... ({len(lines) - max_lines} more lines)"

            # Add file context
            relative_path = file_path.relative_to(self.project_path)
            header = f"# {description}\n# File: {relative_path}\n\n"

            return header + sample

        except Exception as e:
            logger.debug(f"Failed to read code sample from {file_path}", error=str(e))
            return f"# {description}\n# Error reading file: {file_path}"

    def _get_file_line_count(self, file_path: Path) -> int:
        """Get number of lines in file."""
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                return sum(1 for _ in f)
        except Exception:
            return 0

    def get_sample_summary(self) -> dict[str, Any]:
        """Get summary of available samples for logging/debugging."""
        samples = self.get_architecture_samples()

        summary = {}
        for sample_type, content in samples.items():
            lines = content.count("\n")
            chars = len(content)
            summary[sample_type] = {"lines": lines, "chars": chars}

        return summary
