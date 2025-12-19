"""Tests for diff_parser module."""

from __future__ import annotations

from ai_code_review.utils.diff_parser import (
    BINARY_EXTENSIONS,
    FilteringStreamingDiffParser,
)


class TestBinaryExtensions:
    """Test binary file extension detection."""

    def test_binary_extensions_include_common_types(self) -> None:
        """Test that BINARY_EXTENSIONS includes common binary types."""
        assert ".png" in BINARY_EXTENSIONS
        assert ".jpg" in BINARY_EXTENSIONS
        assert ".pdf" in BINARY_EXTENSIONS
        assert ".zip" in BINARY_EXTENSIONS
        assert ".exe" in BINARY_EXTENSIONS
        assert ".so" in BINARY_EXTENSIONS
        assert ".pyc" in BINARY_EXTENSIONS


class TestFilteringStreamingDiffParser:
    """Test FilteringStreamingDiffParser class."""

    def test_parse_basic_diff(self) -> None:
        """Test parsing a basic unified diff."""
        diff_content = """diff --git a/file.py b/file.py
index abc123..def456 100644
--- a/file.py
+++ b/file.py
@@ -1,3 +1,4 @@
 def hello():
-    print("old")
+    print("new")
+    return True
"""
        parser = FilteringStreamingDiffParser()
        diffs = list(parser.feed(diff_content))
        diffs.extend(parser.finalize())

        assert len(diffs) == 1
        assert diffs[0].file_path == "file.py"
        assert diffs[0].new_file is False
        assert diffs[0].renamed_file is False
        assert diffs[0].deleted_file is False
        assert "def hello():" in diffs[0].diff

    def test_parse_filename_with_spaces(self) -> None:
        """Test parsing diff with filenames containing spaces (quoted format)."""
        diff_content = """diff --git "a/my file.py" "b/my file.py"
index abc123..def456 100644
--- "a/my file.py"
+++ "b/my file.py"
@@ -1,1 +1,2 @@
 def test():
+    pass
"""
        parser = FilteringStreamingDiffParser()
        diffs = list(parser.feed(diff_content))
        diffs.extend(parser.finalize())

        assert len(diffs) == 1
        assert diffs[0].file_path == "my file.py"
        assert "def test():" in diffs[0].diff

    def test_parse_multiple_files(self) -> None:
        """Test parsing diff with multiple files."""
        diff_content = """diff --git a/file1.py b/file1.py
index abc123..def456 100644
--- a/file1.py
+++ b/file1.py
@@ -1,1 +1,1 @@
-old content
+new content
diff --git a/file2.py b/file2.py
index ghi789..jkl012 100644
--- a/file2.py
+++ b/file2.py
@@ -1,1 +1,1 @@
-another old
+another new
"""
        parser = FilteringStreamingDiffParser()
        diffs = list(parser.feed(diff_content))
        diffs.extend(parser.finalize())

        assert len(diffs) == 2
        assert diffs[0].file_path == "file1.py"
        assert diffs[1].file_path == "file2.py"

    def test_detect_new_file(self) -> None:
        """Test detection of new files."""
        diff_content = """diff --git a/new_file.py b/new_file.py
new file mode 100644
index 0000000..abc123
--- /dev/null
+++ b/new_file.py
@@ -0,0 +1,3 @@
+def new_function():
+    pass
"""
        parser = FilteringStreamingDiffParser()
        diffs = list(parser.feed(diff_content))
        diffs.extend(parser.finalize())

        assert len(diffs) == 1
        assert diffs[0].file_path == "new_file.py"
        assert diffs[0].new_file is True

    def test_detect_deleted_file(self) -> None:
        """Test detection of deleted files."""
        diff_content = """diff --git a/deleted_file.py b/deleted_file.py
deleted file mode 100644
index abc123..0000000
--- a/deleted_file.py
+++ /dev/null
@@ -1,3 +0,0 @@
-def old_function():
-    pass
"""
        parser = FilteringStreamingDiffParser()
        diffs = list(parser.feed(diff_content))
        diffs.extend(parser.finalize())

        assert len(diffs) == 1
        assert diffs[0].file_path == "deleted_file.py"
        assert diffs[0].deleted_file is True

    def test_detect_renamed_file(self) -> None:
        """Test detection of renamed files."""
        diff_content = """diff --git a/old_name.py b/new_name.py
similarity index 100%
rename from old_name.py
rename to new_name.py
"""
        parser = FilteringStreamingDiffParser()
        diffs = list(parser.feed(diff_content))
        diffs.extend(parser.finalize())

        assert len(diffs) == 1
        assert diffs[0].file_path == "new_name.py"
        assert diffs[0].renamed_file is True

    def test_prefilter_binary_files(self) -> None:
        """Test that binary files are pre-filtered."""
        diff_content = """diff --git a/image.png b/image.png
new file mode 100644
index 0000000..abc123
Binary files /dev/null and b/image.png differ
diff --git a/code.py b/code.py
index def456..ghi789 100644
--- a/code.py
+++ b/code.py
@@ -1,1 +1,1 @@
-old
+new
"""
        parser = FilteringStreamingDiffParser()
        diffs = list(parser.feed(diff_content))
        diffs.extend(parser.finalize())

        # Only code.py should be included
        assert len(diffs) == 1
        assert diffs[0].file_path == "code.py"

        # Check statistics
        stats = parser.get_statistics()
        assert stats["total_files"] == 2
        assert stats["binary_files"] == 1
        assert stats["included_files"] == 1

    def test_prefilter_excluded_patterns(self) -> None:
        """Test that excluded patterns are pre-filtered."""

        def should_exclude(path: str) -> bool:
            return (
                path.endswith(".lock")
                or path.endswith("package-lock.json")
                or "node_modules" in path
            )

        diff_content = """diff --git a/package-lock.json b/package-lock.json
index abc123..def456 100644
--- a/package-lock.json
+++ b/package-lock.json
@@ -1,1 +1,1 @@
-old lock content
+new lock content
diff --git a/src/code.py b/src/code.py
index ghi789..jkl012 100644
--- a/src/code.py
+++ b/src/code.py
@@ -1,1 +1,1 @@
-old code
+new code
"""
        parser = FilteringStreamingDiffParser(should_exclude=should_exclude)
        diffs = list(parser.feed(diff_content))
        diffs.extend(parser.finalize())

        # Only src/code.py should be included
        assert len(diffs) == 1
        assert diffs[0].file_path == "src/code.py"

        # Check statistics
        stats = parser.get_statistics()
        assert stats["total_files"] == 2
        assert stats["filtered_files"] == 1
        assert stats["included_files"] == 1

    def test_handle_incomplete_chunks(self) -> None:
        """Test buffer management with incomplete chunks."""
        # Split diff across multiple chunks
        chunk1 = """diff --git a/file.py b/file.py
index abc123..def456 100644
--- a/file.py
+++ b/file.py
@@ -1,3 +1,4 @@
 def hello():
"""
        chunk2 = """-    print("old")
+    print("new")
+    return True
"""
        parser = FilteringStreamingDiffParser()
        diffs1 = list(parser.feed(chunk1))
        diffs2 = list(parser.feed(chunk2))
        diffs3 = list(parser.finalize())

        # Combine all diffs
        all_diffs = diffs1 + diffs2 + diffs3

        assert len(all_diffs) == 1
        assert all_diffs[0].file_path == "file.py"
        assert "def hello():" in all_diffs[0].diff

    def test_statistics_tracking(self) -> None:
        """Test that statistics are tracked correctly."""

        def should_exclude(path: str) -> bool:
            return path.endswith(".lock")

        diff_content = """diff --git a/image.png b/image.png
new file mode 100644
Binary files /dev/null and b/image.png differ
diff --git a/package.lock b/package.lock
index abc123..def456 100644
--- a/package.lock
+++ b/package.lock
@@ -1,100 +1,100 @@
 lock content here
diff --git a/code.py b/code.py
index ghi789..jkl012 100644
--- a/code.py
+++ b/code.py
@@ -1,1 +1,1 @@
-old
+new
"""
        parser = FilteringStreamingDiffParser(should_exclude=should_exclude)
        diffs = list(parser.feed(diff_content))
        diffs.extend(parser.finalize())

        stats = parser.get_statistics()
        assert stats["total_files"] == 3
        assert stats["binary_files"] == 1
        assert stats["filtered_files"] == 1
        assert stats["included_files"] == 1
        assert "filter_ratio" in stats
        assert "mb_skipped" in stats
        assert "mb_processed" in stats

    def test_multiple_hunks_per_file(self) -> None:
        """Test handling files with multiple hunks."""
        diff_content = """diff --git a/file.py b/file.py
index abc123..def456 100644
--- a/file.py
+++ b/file.py
@@ -1,3 +1,3 @@
 def function1():
-    old1
+    new1
@@ -10,3 +10,3 @@
 def function2():
-    old2
+    new2
"""
        parser = FilteringStreamingDiffParser()
        diffs = list(parser.feed(diff_content))
        diffs.extend(parser.finalize())

        assert len(diffs) == 1
        assert diffs[0].file_path == "file.py"
        # Both hunks should be in the diff
        assert "function1" in diffs[0].diff
        assert "function2" in diffs[0].diff

    def test_empty_diff(self) -> None:
        """Test handling empty diff content."""
        parser = FilteringStreamingDiffParser()
        diffs = list(parser.feed(""))
        diffs.extend(parser.finalize())

        assert len(diffs) == 0

        stats = parser.get_statistics()
        assert stats["total_files"] == 0
        assert stats["included_files"] == 0

    def test_malformed_diff_header(self) -> None:
        """Test handling malformed diff headers gracefully."""
        diff_content = """not a valid diff header
some random content
diff --git a/valid.py b/valid.py
index abc123..def456 100644
--- a/valid.py
+++ b/valid.py
@@ -1,1 +1,1 @@
-old
+new
"""
        parser = FilteringStreamingDiffParser()
        diffs = list(parser.feed(diff_content))
        diffs.extend(parser.finalize())

        # Should still parse the valid file
        assert len(diffs) == 1
        assert diffs[0].file_path == "valid.py"

    def test_bytes_tracking(self) -> None:
        """Test that bytes skipped and processed are tracked."""

        def should_exclude(path: str) -> bool:
            return path.endswith(".lock")

        diff_content = (
            """diff --git a/large.lock b/large.lock
index abc123..def456 100644
--- a/large.lock
+++ b/large.lock
@@ -1,1000 +1,1000 @@
 """
            + "\n".join([f"line {i}" for i in range(1000)])
            + """
diff --git a/small.py b/small.py
index ghi789..jkl012 100644
--- a/small.py
+++ b/small.py
@@ -1,1 +1,1 @@
-old
+new
"""
        )
        parser = FilteringStreamingDiffParser(should_exclude=should_exclude)
        diffs = list(parser.feed(diff_content))
        diffs.extend(parser.finalize())

        stats = parser.get_statistics()
        # large.lock should be skipped
        assert stats["bytes_skipped"] > 0
        # small.py should be processed
        assert stats["bytes_processed"] > 0
        assert stats["included_files"] == 1

    def test_filter_ratio_calculation(self) -> None:
        """Test filter ratio is calculated correctly."""

        def should_exclude(path: str) -> bool:
            return "exclude" in path

        diff_content = """diff --git a/exclude1.py b/exclude1.py
index abc..def 100644
--- a/exclude1.py
+++ b/exclude1.py
@@ -1,1 +1,1 @@
-old
+new
diff --git a/exclude2.py b/exclude2.py
index ghi..jkl 100644
--- a/exclude2.py
+++ b/exclude2.py
@@ -1,1 +1,1 @@
-old
+new
diff --git a/include.py b/include.py
index mno..pqr 100644
--- a/include.py
+++ b/include.py
@@ -1,1 +1,1 @@
-old
+new
"""
        parser = FilteringStreamingDiffParser(should_exclude=should_exclude)
        diffs = list(parser.feed(diff_content))
        diffs.extend(parser.finalize())

        stats = parser.get_statistics()
        assert stats["total_files"] == 3
        assert stats["filtered_files"] == 2
        assert stats["included_files"] == 1
        # 2 out of 3 filtered = 0.666...
        assert abs(stats["filter_ratio"] - 0.666) < 0.01

    def test_case_insensitive_binary_detection(self) -> None:
        """Test that binary detection is case-insensitive."""
        diff_content = """diff --git a/IMAGE.PNG b/IMAGE.PNG
new file mode 100644
Binary files /dev/null and b/IMAGE.PNG differ
diff --git a/File.PDF b/File.PDF
new file mode 100644
Binary files /dev/null and b/File.PDF differ
"""
        parser = FilteringStreamingDiffParser()
        diffs = list(parser.feed(diff_content))
        diffs.extend(parser.finalize())

        # Both should be filtered as binary
        assert len(diffs) == 0

        stats = parser.get_statistics()
        assert stats["binary_files"] == 2
