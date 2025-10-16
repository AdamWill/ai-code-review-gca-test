"""Code structure section with architectural insights."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from context_generator.constants import (
    IMPORTANT_EXTENSIONS,
    IMPORTANT_FILES_NO_EXT,
    IMPORTANT_ROOT_FILES,
    PRIORITY_PYTHON_FILES,
)
from context_generator.sections.base_section import BaseSection
from context_generator.utils.git_utils import get_tracked_files, get_tracked_symlinks


class StructureSection(BaseSection):
    """Generate code structure analysis using code samples."""

    def __init__(self, llm_analyzer: Any) -> None:
        """Initialize structure section."""
        super().__init__("structure", required=True)
        self.llm_analyzer = llm_analyzer

    async def generate_content(
        self, facts: dict[str, Any], code_samples: dict[str, str]
    ) -> str:
        """Generate structure content with deterministic structure and LLM insights."""
        # Generate deterministic directory structure
        structure_tree = self._generate_directory_tree(facts)

        # Use LLM only for architectural insights
        prompt = self._create_structure_prompt(facts, code_samples, structure_tree)
        llm_insights = await self.llm_analyzer.call_llm(prompt, self.get_template_key())

        # Combine deterministic structure with LLM insights
        return f"""### Project Organization
```
{structure_tree}
```

{llm_insights}"""

    def get_template_key(self) -> str:
        """Get template key for structure section."""
        return "code_structure"

    def get_dependencies(self) -> list[str]:
        """Required facts for structure."""
        return ["file_structure", "project_info"]

    def _get_git_files(self, project_path: Path) -> list[Path]:
        """Get all tracked files from git."""
        return get_tracked_files(project_path)

    def _get_git_files_in_dir(
        self, dir_path: Path
    ) -> tuple[list[Path], list[Path], dict[str, Path]]:
        """Get Git tracked files, directories, and symlinks within a specific directory.

        Returns:
            tuple: (files, directories, symlinks_dict) that are Git tracked within dir_path.
                   symlinks_dict maps symlink filenames (str) to their targets (Path).
        """
        if not hasattr(self, "_cached_git_files"):
            # Get project_path from dir_path if not set
            if not hasattr(self, "project_path"):
                # Find the project root by going up until we find a reasonable root
                current = dir_path
                while current.parent != current:
                    if (current / ".git").exists() or current.name in ["src", "tests"]:
                        self.project_path = (
                            current.parent
                            if current.name in ["src", "tests"]
                            else current
                        )
                        break
                    current = current.parent
                else:
                    # Fallback: use the directory itself as project root
                    self.project_path = dir_path

            # Get git files - keep them as relative paths (DON'T resolve - that would follow symlinks!)
            self._cached_git_files = self._get_git_files(self.project_path)

            # Get and cache symlinks - keep them as relative paths (DON'T resolve - that would follow symlinks!)
            self._cached_git_symlinks = get_tracked_symlinks(self.project_path)

        # Calculate relative directory path WITHOUT resolving (to preserve symlinks)
        # We cannot use .resolve() or .relative_to() on symlink-containing paths
        # because .resolve() follows symlinks to their targets
        try:
            if dir_path.is_absolute() and self.project_path.is_absolute():
                # Both absolute - create relative path by slicing path parts
                # Example: /home/user/project/src -> Path('src') when project is /home/user/project
                relative_dir = Path(*dir_path.parts[len(self.project_path.parts) :])
            elif not dir_path.is_absolute() and not self.project_path.is_absolute():
                # Both relative - use standard relative_to method
                relative_dir = dir_path.relative_to(self.project_path)
            elif not dir_path.is_absolute():
                # dir_path is relative, use as-is if it matches structure
                relative_dir = dir_path
            else:
                # Mixed: dir_path absolute, project_path relative - extract relative part
                # by slicing to avoid symlink resolution
                relative_dir = Path(*dir_path.parts[len(self.project_path.parts) :])
        except (ValueError, IndexError):
            # If dir_path is not within project_path, return empty results
            return [], [], {}

        files = []
        dirs = set()
        symlinks_in_dir = {}

        # First, collect symlinks to exclude them from files
        symlink_paths_set = set()  # Store as strings for reliable comparison
        for symlink_path, target in self._cached_git_symlinks.items():
            try:
                # symlink_path is already relative from get_tracked_symlinks
                symlink_relative = symlink_path

                # Check if the symlink is directly in this directory
                if len(symlink_relative.parts) == len(relative_dir.parts) + 1:
                    if (
                        symlink_relative.parts[: len(relative_dir.parts)]
                        == relative_dir.parts
                    ):
                        # Symlink is in this directory
                        # Store as string for reliable comparison (convert Path to string)
                        symlink_paths_set.add(str(symlink_relative))
                        # Get just the filename for display
                        symlink_name = symlink_relative.parts[-1]
                        symlinks_in_dir[symlink_name] = target

            except (ValueError, AttributeError):
                # symlink is not relative to project_path, skip
                continue

        # Now process regular files, excluding symlinks
        for git_file in self._cached_git_files:
            try:
                # git_file is already relative (from get_tracked_files)
                # DON'T resolve() - that would follow symlinks to their targets
                # Just use the path as-is
                git_file_relative = git_file

                # Skip if this file is actually a symlink (compare as strings)
                if str(git_file_relative) in symlink_paths_set:
                    continue

                # Check if the file is within the target directory
                if len(git_file_relative.parts) > len(relative_dir.parts):
                    # Check if the file path starts with our target directory
                    if (
                        git_file_relative.parts[: len(relative_dir.parts)]
                        == relative_dir.parts
                    ):
                        remaining_parts = git_file_relative.parts[
                            len(relative_dir.parts) :
                        ]

                        if len(remaining_parts) == 1:
                            # File is directly in this directory
                            files.append(git_file)
                        else:
                            # File is in a subdirectory, track the subdirectory
                            subdir_name = remaining_parts[0]
                            # Use the original dir_path for consistency
                            subdir_path = dir_path / subdir_name
                            dirs.add(subdir_path)

            except ValueError:
                # git_file is not relative to project_path, skip
                continue

        return files, sorted(dirs), symlinks_in_dir

    def _generate_directory_tree(self, facts: dict[str, Any]) -> str:
        """Generate deterministic directory tree from actual project structure."""
        from pathlib import Path

        structure = facts.get("file_structure", {})
        source_dirs = structure.get("source_dirs", [])
        root_files = structure.get("root_files", [])

        # Get project path from facts (added by ProjectFactsExtractor)
        project_info = facts.get("project_info", {})
        project_path_str = project_info.get("path", ".")
        self.project_path = Path(project_path_str)  # Store for use in other methods

        # Start with project root
        tree_lines = ["."]

        # Collect all items to display
        items = []

        # Add ALL source directories (not just Python-specific ones)
        # Sort them to have consistent order
        for source_dir in sorted(source_dirs):
            items.append(("dir", source_dir))

        # Add important root files
        for file in sorted(IMPORTANT_ROOT_FILES):
            if file in root_files:
                items.append(("file", file))

        # Generate tree with proper formatting
        for i, (item_type, item_name) in enumerate(items):
            is_last = i == len(items) - 1
            prefix = "└──" if is_last else "├──"

            if item_type == "dir":
                tree_lines.append(f"{prefix} {item_name}/")

                # Add subdirectories for any source directory (not just src/)
                if item_name in source_dirs:
                    subdir_lines = self._get_generic_dir_structure(
                        item_name, is_last, 0
                    )
                    tree_lines.extend(subdir_lines)
            else:
                tree_lines.append(f"{prefix} {item_name}")

        return "\n".join(tree_lines)

    def _get_generic_dir_structure(
        self, dir_name: str, is_parent_last: bool, current_depth: int = 0
    ) -> list[str]:
        """Get directory structure for any directory using recursive exploration."""
        # Use the project path as base
        project_path = self.project_path if hasattr(self, "project_path") else Path(".")
        dir_path = project_path / dir_name

        # Use our new recursive method for deep exploration
        # Start with empty prefix since this is called from _generate_directory_tree
        return self._get_recursive_dir_structure(
            dir_path, dir_name, is_parent_last, "", current_depth
        )

    def _get_recursive_dir_structure(
        self,
        subdir_path: Path,
        subdir_name: str,
        is_parent_last: bool,
        parent_prefix: str,
        current_depth: int,
    ) -> list[str]:
        """Get recursive directory structure with proper tree formatting."""
        lines: list[str] = []

        # Determine max items based on depth to avoid overwhelming output
        if current_depth <= 1:
            max_items = 25  # More items for shallow levels
        elif current_depth <= 3:
            max_items = 15  # Medium items for medium levels
        else:
            max_items = 8  # Fewer items for deep levels

        # Get items in this subdirectory
        try:
            git_files, git_dirs, git_symlinks = self._get_git_files_in_dir(subdir_path)

            # Collect all items (directories, files, and symlinks)
            items: list[tuple[str, bool, bool]] = []  # (name, is_dir, is_symlink)

            # Add directories first
            for git_dir in git_dirs:
                if not git_dir.name.startswith(".") and git_dir.name != "__pycache__":
                    items.append((f"{git_dir.name}/", True, False))

            # Add important files
            for git_file in git_files:
                if not git_file.name.startswith(".") and git_file.name != "__pycache__":
                    # Filter for important files
                    has_important_extension = git_file.suffix in IMPORTANT_EXTENSIONS
                    has_important_name = git_file.name in IMPORTANT_FILES_NO_EXT
                    is_priority_python = git_file.name in PRIORITY_PYTHON_FILES

                    if (
                        has_important_extension
                        or has_important_name
                        or is_priority_python
                    ):
                        items.append((git_file.name, False, False))

            # Add symlinks (git_symlinks is now {filename: target})
            for symlink_name, target in git_symlinks.items():
                if not symlink_name.startswith("."):
                    # Format: "link -> target"
                    symlink_display = f"{symlink_name} -> {target}"
                    items.append((symlink_display, False, True))

            # Sort items: directories first, then files, then symlinks
            # Key explanation: (not x[1], x[2], x[0]) where x = (name, is_dir, is_symlink)
            # - not x[1]: directories (True) come first (False < True, so not True < not False)
            # - x[2]: among non-dirs, non-symlinks (False) come before symlinks (True)
            # - x[0]: alphabetically by name as final tiebreaker
            items.sort(key=lambda x: (not x[1], x[2], x[0]))

            # Limit items but show more for important directories
            items = items[:max_items]

        except (ValueError, AttributeError):
            return lines

        # Calculate prefix for this level
        if is_parent_last:
            current_prefix = f"{parent_prefix}    "
        else:
            current_prefix = f"{parent_prefix}│   "

        # Generate tree lines for items in this directory
        for i, (item_name, is_dir, is_symlink) in enumerate(items):
            is_last_item = i == len(items) - 1
            connector = "└──" if is_last_item else "├──"
            lines.append(f"{current_prefix}{connector} {item_name}")

            # Recursive exploration for subdirectories (not for symlinks)
            if (
                is_dir
                and not is_symlink
                and current_depth < 6  # Allow deep recursion (up to 7 levels total)
                and self._should_explore_subdir(item_name.rstrip("/"))
            ):
                deeper_subdir_path = subdir_path / item_name.rstrip("/")
                deeper_subdir_name = item_name.rstrip("/")

                # Recursive call for deeper exploration
                deeper_lines = self._get_recursive_dir_structure(
                    deeper_subdir_path,
                    deeper_subdir_name,
                    is_last_item,
                    current_prefix,
                    current_depth + 1,
                )
                lines.extend(deeper_lines)

        return lines

    def _should_explore_subdir(self, dir_name: str) -> bool:
        """Determine if a subdirectory should be explored for better context."""
        # Always explore these important subdirectories
        important_subdirs = [
            "jobs",
            "modules",
            "utils",
            "models",
            "db",
            "api",
            "apidocs",
            "core",
            "services",
            "handlers",
            "controllers",
            "views",
            "components",
            "lib",
            "libs",
            "helpers",
            "parsers",
            "processors",
            "workflows",
            # Add more common directory patterns
            "config",
            "configs",
            "settings",
            "middleware",
            "auth",
            "authentication",
            "authorization",
            "tests",
            "test",
            "specs",
            "fixtures",
            "factories",
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

        # Also explore directories that look like main application modules
        # (contain multiple Python files or subdirectories)
        if dir_name.lower() in important_subdirs:
            return True

        # For src/ directories, explore if they seem to be main modules
        # (this catches project-specific directories like 'autometar_flow', 'package_test_flow')
        if self._looks_like_main_module(dir_name):
            return True

        return False

    def _looks_like_main_module(self, dir_name: str) -> bool:
        """Check if a directory looks like a main application module."""
        # Skip obviously non-module directories
        skip_dirs = [
            "__pycache__",
            ".git",
            "node_modules",
            "venv",
            ".venv",
            "dist",
            "build",
            "target",  # Rust/Java build dir
            "out",  # Common build dir
            ".next",  # Next.js build dir
            "coverage",  # Coverage reports
        ]
        if dir_name.lower() in skip_dirs:
            return False

        # More conservative heuristic: only explore directories that look like main modules
        # based on common naming patterns
        main_module_patterns = [
            # Contains underscores (common in Python packages)
            "_" in dir_name,
            # Looks like a package name (lowercase, no special chars except underscore/hyphen)
            dir_name.replace("_", "").replace("-", "").isalnum() and dir_name.islower(),
            # Common main module names
            dir_name.lower()
            in ["app", "main", "core", "src", "lib", "pkg", "internal"],
        ]

        return any(main_module_patterns)

    def _get_subdir_items(self, subdir_path: Path, max_items: int = 15) -> list[str]:
        """Get limited items from a subdirectory for context (Git tracked only)."""
        items: list[str] = []
        if not subdir_path.exists():
            return items

        try:
            # Use Git tracked files instead of filesystem
            git_files, git_dirs, git_symlinks = self._get_git_files_in_dir(subdir_path)

            # Add directories
            for git_dir in git_dirs:
                if not git_dir.name.startswith(".") and git_dir.name != "__pycache__":
                    items.append(f"{git_dir.name}/")

            # Add files with filtering
            for git_file in git_files:
                if not git_file.name.startswith(".") and git_file.name != "__pycache__":
                    # Same filtering logic as main method
                    has_important_extension = git_file.suffix in IMPORTANT_EXTENSIONS
                    has_important_name = git_file.name in IMPORTANT_FILES_NO_EXT

                    if has_important_extension or has_important_name:
                        items.append(git_file.name)

            # Add symlinks (git_symlinks is now {filename: target})
            for symlink_name, target in git_symlinks.items():
                if not symlink_name.startswith("."):
                    items.append(f"{symlink_name} -> {target}")

        except (PermissionError, ValueError):
            return items

        # Sort and limit (symlinks like files, not directories)
        items.sort(key=lambda x: (not x.endswith("/"), x))  # Directories first
        return items[:max_items]

    def _get_src_structure(self, is_parent_last: bool) -> list[str]:
        """Get src/ directory structure with proper tree formatting (Git tracked only)."""

        src_lines: list[str] = []
        src_path = self.project_path / "src"

        if not src_path.exists():
            return src_lines

        # Get Git tracked directories in src/
        try:
            _, git_dirs, _ = self._get_git_files_in_dir(src_path)
            subdirs = [d for d in git_dirs if not d.name.startswith(".")]
            subdirs.sort(key=lambda d: d.name)
        except (ValueError, AttributeError):
            return src_lines

        # Base prefix depends on whether src/ is the last item in parent
        base_prefix = "    " if is_parent_last else "│   "

        for i, subdir in enumerate(subdirs):
            is_last_subdir = i == len(subdirs) - 1
            connector = "└──" if is_last_subdir else "├──"
            src_lines.append(f"{base_prefix}{connector} {subdir.name}/")

            # Add key files in each subdirectory
            key_items = self._get_key_items_in_dir(subdir)
            for j, item_info in enumerate(key_items):
                is_last_item = j == len(key_items) - 1

                # Handle pre-indented subdir files
                if item_info.startswith("│   "):
                    # This is a file within a subdirectory - needs extra indentation
                    clean_item = item_info[4:]  # Remove the pre-indentation marker
                    item_connector = "└──" if is_last_item else "├──"

                    if is_last_subdir:
                        item_prefix = f"{base_prefix}    │   {item_connector}"
                    else:
                        item_prefix = f"{base_prefix}│   │   {item_connector}"

                    src_lines.append(f"{item_prefix} {clean_item}")
                else:
                    # Regular item (directory or file in current level)
                    item_connector = "└──" if is_last_item else "├──"

                    if is_last_subdir:
                        item_prefix = f"{base_prefix}    {item_connector}"
                    else:
                        item_prefix = f"{base_prefix}│   {item_connector}"

                    src_lines.append(f"{item_prefix} {item_info}")

        return src_lines

    def _get_key_items_in_dir(self, dir_path: Path) -> list[str]:
        """Get key files and subdirectories in a directory (Git tracked only)."""
        items: list[str] = []

        if not dir_path.exists():
            return items

        try:
            # Get Git tracked files and directories
            git_files, git_dirs, _ = self._get_git_files_in_dir(dir_path)

            # Add key subdirectories first (with their contents)
            subdirs = [
                d
                for d in git_dirs
                if not d.name.startswith(".") and d.name != "__pycache__"
            ]
            subdirs.sort(key=lambda d: d.name)
        except (ValueError, AttributeError):
            return items

        for subdir in subdirs:
            items.append(f"{subdir.name}/")
            # Add files within subdirectories
            subdir_files = self._get_files_in_subdir(subdir)
            items.extend(subdir_files)

        # Add key Python files in current directory (Git tracked only)
        py_files = [
            f.name for f in git_files if f.suffix == ".py" and f.name != "__init__.py"
        ]
        py_files.sort()

        # Prioritize important files
        for important in sorted(PRIORITY_PYTHON_FILES):
            if important in py_files:
                items.append(important)
                py_files.remove(important)

        # Add remaining files (show more for better context)
        items.extend(py_files[:12])  # Show up to 12 additional files

        return items

    def _get_files_in_subdir(self, subdir: Path) -> list[str]:
        """Get Python files in a subdirectory with proper indentation marker (Git tracked only)."""
        files: list[str] = []
        if not subdir.exists():
            return files

        try:
            # Get Git tracked files in this subdirectory
            git_files, _, _ = self._get_git_files_in_dir(subdir)
            py_files = [
                f.name
                for f in git_files
                if f.suffix == ".py" and f.name != "__init__.py"
            ]
            py_files.sort()
        except (ValueError, AttributeError):
            return files

        # Mark these as subdir files for proper indentation later
        for py_file in py_files:
            files.append(f"│   {py_file}")  # Pre-mark with indentation

        return files

    def _create_structure_prompt(
        self, facts: dict[str, Any], code_samples: dict[str, str], structure_tree: str
    ) -> str:
        """Create prompt for architectural insights (structure tree is deterministic)."""
        # Format code samples for LLM
        code_samples_text = ""
        for sample_type, content in code_samples.items():
            code_samples_text += f"\n=== {sample_type.upper()} ===\n{content}\n"

        return f"""Analyze the architectural patterns and development conventions from this code.

PROJECT STRUCTURE (already provided deterministically):
{structure_tree}

CODE SAMPLES:
{code_samples_text}

Generate EXACTLY this format (do NOT include Project Organization section):

### Architecture Patterns
**Code Organization:** [How code is structured - Clean Architecture, Layered, etc.]
**Key Components:** [Main modules and their responsibilities based on code samples]
**Entry Points:** [How the application starts and main flows]

### Important Files for Review Context
- **[filename from code samples]** - [Why reviewers should understand this file]
- **[filename from code samples]** - [Why reviewers should understand this file]
- **[filename from code samples]** - [Why reviewers should understand this file]

### Development Conventions
- **Naming:** [Naming patterns observed in the code samples]
- **Module Structure:** [How modules are organized based on actual structure]
- **Configuration:** [How configuration is handled based on code samples]
- **Testing:** [Testing structure and patterns if visible]

Requirements:
- Base analysis ONLY on the provided code samples and directory structure
- Focus on patterns that help understand code changes during reviews
- Identify 3-4 most critical files for reviewers to understand
- Mention conventions that affect code style expectations
- Do NOT repeat the directory structure - it's already provided above"""
