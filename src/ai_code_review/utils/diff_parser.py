"""Unified diff parser with streaming and pre-filtering support."""

from __future__ import annotations

import re
from collections.abc import Callable, Generator

from ai_code_review.models.platform import PullRequestDiff

# Common binary file extensions to skip during parsing
# Binary file extensions for detection
_BINARY_EXTENSIONS_SET = {
    # Images
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".ico",
    ".svg",
    ".webp",
    ".tiff",
    ".tif",
    # Videos
    ".mp4",
    ".avi",
    ".mov",
    ".wmv",
    ".flv",
    ".webm",
    ".mkv",
    ".m4v",
    # Audio
    ".mp3",
    ".wav",
    ".ogg",
    ".flac",
    ".aac",
    ".m4a",
    ".wma",
    # Archives
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".7z",
    ".rar",
    ".tgz",
    ".tar.gz",
    ".tar.bz2",
    ".xz",
    # Executables and libraries
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bin",
    ".app",
    ".deb",
    ".rpm",
    # Documents
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".odt",
    ".ods",
    ".odp",
    # Fonts
    ".ttf",
    ".otf",
    ".woff",
    ".woff2",
    ".eot",
    # Compiled/bytecode
    ".pyc",
    ".pyo",
    ".class",
    ".o",
    ".a",
    ".obj",
    # Databases
    ".db",
    ".sqlite",
    ".sqlite3",
    ".dat",
    # Other
    ".jar",
    ".war",
    ".ear",
    ".iso",
    ".dmg",
}

# Convert to tuple for efficient endswith() checks
BINARY_EXTENSIONS = tuple(_BINARY_EXTENSIONS_SET)


class FilteringStreamingDiffParser:
    """Parse unified diff format incrementally with file pre-filtering.

    This parser processes diffs in chunks, allowing filtering files BEFORE
    parsing their content. This significantly reduces memory usage and
    processing time for large diffs with many excluded files.

    Example:
        >>> parser = FilteringStreamingDiffParser(
        ...     should_exclude=lambda path: path.endswith('.lock')
        ... )
        >>> for chunk in download_diff_chunks():
        ...     for diff in parser.feed(chunk):
        ...         process_diff(diff)
        >>> for diff in parser.finalize():
        ...     process_diff(diff)
        >>> stats = parser.get_statistics()
    """

    def __init__(
        self,
        should_exclude: Callable[[str], bool] | None = None,
    ) -> None:
        """Initialize parser with optional exclusion filter.

        Args:
            should_exclude: Function that returns True if a file path should
                be excluded from parsing. If None, no user-defined filtering.
        """
        self.should_exclude = should_exclude or (lambda _: False)
        self.buffer = ""
        self.current_file_info: dict[str, str] | None = None
        self.current_file_content: list[str] = []
        self.skipping_current_file = False

        # Statistics tracking
        self.stats = {
            "total_files": 0,
            "filtered_files": 0,
            "binary_files": 0,
            "included_files": 0,
            "bytes_skipped": 0,
            "bytes_processed": 0,
        }

        # Regex pattern for file headers in unified diff format
        # Match diff headers with optional quotes for filenames with spaces
        # Handles: diff --git a/file.txt b/file.txt
        #      or: diff --git "a/my file.txt" "b/my file.txt"
        self.file_pattern = re.compile(r'^diff --git "?a/(.+?)"? "?b/(.+?)"?$')

    def _is_binary_file(self, file_path: str) -> bool:
        """Check if file is binary based on extension.

        Args:
            file_path: Path of the file to check

        Returns:
            True if file appears to be binary
        """
        file_path_lower = file_path.lower()
        # BINARY_EXTENSIONS is already a tuple for efficient checking
        return file_path_lower.endswith(BINARY_EXTENSIONS)

    def _should_skip_file(self, file_path: str) -> bool:
        """Determine if file should be skipped entirely.

        Args:
            file_path: Path of the file to check

        Returns:
            True if file should be skipped (not parsed)
        """
        # Check binary files first
        if self._is_binary_file(file_path):
            self.stats["binary_files"] += 1
            return True

        # Check user-defined exclusion patterns
        if self.should_exclude(file_path):
            self.stats["filtered_files"] += 1
            return True

        return False

    def feed(self, chunk: str) -> Generator[PullRequestDiff, None, None]:
        """Feed a chunk of data and yield complete file diffs for included files.

        Files matching exclusion patterns or binary extensions are skipped
        without parsing their content, saving memory and processing time.

        Args:
            chunk: Partial diff content to process

        Yields:
            PullRequestDiff objects only for files that pass the filter
        """
        self.buffer += chunk
        lines = self.buffer.split("\n")

        # Keep last incomplete line in buffer
        self.buffer = lines[-1]
        lines = lines[:-1]

        for line in lines:
            match = self.file_pattern.match(line)

            if match:
                # Found new file header
                self.stats["total_files"] += 1

                # Yield previous file if we were collecting it
                if self.current_file_info and not self.skipping_current_file:
                    diff_obj = self._build_diff()
                    if diff_obj:
                        self.stats["included_files"] += 1
                        self.stats["bytes_processed"] += len(diff_obj.diff)
                        yield diff_obj

                # Start tracking new file
                old_path = match.group(1)
                new_path = match.group(2)
                file_path = new_path if new_path != "/dev/null" else old_path

                # PRE-FILTER: Check if we should skip this file
                self.skipping_current_file = self._should_skip_file(file_path)

                if self.skipping_current_file:
                    # Don't store content, just skip
                    self.current_file_info = None
                    self.current_file_content = []
                else:
                    # Start collecting content for this file
                    self.current_file_info = {
                        "header": line,
                        "old_path": old_path,
                        "new_path": new_path,
                        "file_path": file_path,
                    }
                    self.current_file_content = [line]
            else:
                # Content line
                if self.skipping_current_file:
                    # Just skip this line - don't store it
                    self.stats["bytes_skipped"] += len(line) + 1  # +1 for newline
                    continue

                # Accumulate content for included files only
                if self.current_file_info:
                    self.current_file_content.append(line)

    def finalize(self) -> Generator[PullRequestDiff, None, None]:
        """Flush remaining content and yield final diff.

        Call this when all data has been fed to ensure the last file
        is processed.

        Yields:
            Final PullRequestDiff if any content remains and wasn't filtered
        """
        # Add any remaining buffer content
        if self.buffer and not self.skipping_current_file:
            self.current_file_content.append(self.buffer)

        # Yield the last file if it wasn't skipped
        if self.current_file_info and not self.skipping_current_file:
            diff_obj = self._build_diff()
            if diff_obj:
                self.stats["included_files"] += 1
                self.stats["bytes_processed"] += len(diff_obj.diff)
                yield diff_obj

        # Reset state
        self.buffer = ""
        self.current_file_info = None
        self.current_file_content = []
        self.skipping_current_file = False

    def _build_diff(self) -> PullRequestDiff | None:
        """Build PullRequestDiff from accumulated content.

        Returns:
            PullRequestDiff object or None if content is invalid
        """
        if not self.current_file_info or not self.current_file_content:
            return None

        # Join content
        file_diff = "\n".join(self.current_file_content)

        # Determine file status from diff content
        new_file = "new file mode" in file_diff
        deleted_file = "deleted file mode" in file_diff
        renamed_file = (
            self.current_file_info["old_path"] != self.current_file_info["new_path"]
        )

        return PullRequestDiff(
            file_path=self.current_file_info["file_path"],
            new_file=new_file,
            renamed_file=renamed_file,
            deleted_file=deleted_file,
            diff=file_diff,
        )

    def get_statistics(self) -> dict[str, int | float]:
        """Get filtering and processing statistics.

        Returns:
            Dictionary with statistics about filtering:
                - total_files: Total number of files encountered
                - included_files: Files that were parsed and included
                - filtered_files: Files excluded by user patterns
                - binary_files: Files excluded as binaries
                - bytes_skipped: Bytes skipped during filtering
                - bytes_processed: Bytes actually processed
                - filter_ratio: Ratio of filtered to total files
                - mb_skipped: Megabytes skipped
                - mb_processed: Megabytes processed
        """
        stats: dict[str, int | float] = {
            "total_files": self.stats["total_files"],
            "filtered_files": self.stats["filtered_files"],
            "binary_files": self.stats["binary_files"],
            "included_files": self.stats["included_files"],
            "bytes_skipped": self.stats["bytes_skipped"],
            "bytes_processed": self.stats["bytes_processed"],
        }
        if stats["total_files"] > 0:
            filtered_count = int(stats["filtered_files"]) + int(stats["binary_files"])
            stats["filter_ratio"] = filtered_count / int(stats["total_files"])
            stats["mb_skipped"] = int(stats["bytes_skipped"]) / 1024 / 1024
            stats["mb_processed"] = int(stats["bytes_processed"]) / 1024 / 1024
        else:
            stats["filter_ratio"] = 0.0
            stats["mb_skipped"] = 0.0
            stats["mb_processed"] = 0.0
        return stats
