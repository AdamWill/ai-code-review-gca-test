"""Tests for secure Git utilities."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from context_generator.utils.git_utils import (
    SecureGitRunner,
    get_git_runner,
    get_tracked_files,
    is_git_repository,
)


class TestSecureGitRunner:
    """Test SecureGitRunner functionality."""

    def test_init_finds_git_executable(self) -> None:
        """Test that Git executable is found during initialization."""
        with patch("shutil.which", return_value="/usr/bin/git"):
            runner = SecureGitRunner()
            assert runner._git_path == "/usr/bin/git"

    def test_init_raises_when_git_not_found(self) -> None:
        """Test that RuntimeError is raised when Git is not found."""
        with patch("shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="Git executable not found"):
                SecureGitRunner()

    def test_validate_path_nonexistent(self) -> None:
        """Test path validation with non-existent path."""
        with patch("shutil.which", return_value="/usr/bin/git"):
            runner = SecureGitRunner()
            non_existent = Path("/non/existent/path")

            with pytest.raises(ValueError, match="Path does not exist"):
                runner._validate_path(non_existent)

    def test_validate_path_traversal_attack(self) -> None:
        """Test path validation prevents path traversal."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("shutil.which", return_value="/usr/bin/git"):
                runner = SecureGitRunner()
                # Create a path that exists and test the path traversal check
                tmp_path = Path(tmp_dir)

                # Mock the resolve method to return a path with .. in it
                with patch.object(Path, "resolve") as mock_resolve:
                    mock_resolve.return_value = Path("/some/path/../etc/passwd")

                    with pytest.raises(ValueError, match="Invalid path detected"):
                        runner._validate_path(tmp_path)

    @patch("subprocess.run")
    def test_is_git_repository_success(self, mock_run: Mock) -> None:
        """Test successful Git repository detection."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("shutil.which", return_value="/usr/bin/git"):
                runner = SecureGitRunner()
                mock_run.return_value.returncode = 0

                result = runner.is_git_repository(Path(tmp_dir))

                assert result is True
                mock_run.assert_called_once_with(
                    ["/usr/bin/git", "rev-parse", "--git-dir"],
                    cwd=Path(tmp_dir),
                    capture_output=True,
                    check=True,
                    timeout=10,
                )

    @patch("subprocess.run")
    def test_is_git_repository_failure(self, mock_run: Mock) -> None:
        """Test Git repository detection failure."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("shutil.which", return_value="/usr/bin/git"):
                runner = SecureGitRunner()
                mock_run.side_effect = Exception("Not a git repo")

                result = runner.is_git_repository(Path(tmp_dir))

                assert result is False

    @patch("subprocess.run")
    def test_get_tracked_files_success(self, mock_run: Mock) -> None:
        """Test successful tracked files retrieval."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("shutil.which", return_value="/usr/bin/git"):
                runner = SecureGitRunner()
                mock_result = Mock()
                mock_result.stdout = "file1.py\nfile2.py\ndir/file3.py"
                mock_run.return_value = mock_result

                files = runner.get_tracked_files(Path(tmp_dir))

                expected = [Path("file1.py"), Path("file2.py"), Path("dir/file3.py")]
                assert files == expected
                mock_run.assert_called_once_with(
                    ["/usr/bin/git", "ls-files"],
                    cwd=Path(tmp_dir),
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=30,
                )

    @patch("subprocess.run")
    def test_get_tracked_files_empty_output(self, mock_run: Mock) -> None:
        """Test tracked files with empty output."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("shutil.which", return_value="/usr/bin/git"):
                runner = SecureGitRunner()
                mock_result = Mock()
                mock_result.stdout = ""
                mock_run.return_value = mock_result

                files = runner.get_tracked_files(Path(tmp_dir))

                assert files == []

    @patch("subprocess.run")
    def test_get_tracked_files_filters_path_traversal(self, mock_run: Mock) -> None:
        """Test that path traversal attempts are filtered out."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("shutil.which", return_value="/usr/bin/git"):
                runner = SecureGitRunner()
                mock_result = Mock()
                mock_result.stdout = "file1.py\n../../../etc/passwd\nfile2.py"
                mock_run.return_value = mock_result

                files = runner.get_tracked_files(Path(tmp_dir))

                expected = [Path("file1.py"), Path("file2.py")]
                assert files == expected

    @patch("subprocess.run")
    def test_get_tracked_files_failure(self, mock_run: Mock) -> None:
        """Test tracked files retrieval failure."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("shutil.which", return_value="/usr/bin/git"):
                runner = SecureGitRunner()
                mock_run.side_effect = Exception("Git error")

                with pytest.raises(Exception, match="Git error"):
                    runner.get_tracked_files(Path(tmp_dir))

    @patch("subprocess.run")
    def test_get_tracked_files_not_git_repo(self, mock_run: Mock) -> None:
        """Test tracked files retrieval when not a git repository."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("shutil.which", return_value="/usr/bin/git"):
                runner = SecureGitRunner()
                # Mock git ls-files returning exit code 128 (not a git repository)
                mock_run.side_effect = subprocess.CalledProcessError(
                    128, "git", stderr=b"not a git repository"
                )

                with pytest.raises(RuntimeError, match="is not a Git repository"):
                    runner.get_tracked_files(Path(tmp_dir))

    @patch("subprocess.run")
    def test_get_tracked_files_timeout(self, mock_run: Mock) -> None:
        """Test tracked files retrieval timeout."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("shutil.which", return_value="/usr/bin/git"):
                runner = SecureGitRunner()
                mock_run.side_effect = subprocess.TimeoutExpired("git", 30)

                with pytest.raises(RuntimeError, match="Git command timed out"):
                    runner.get_tracked_files(Path(tmp_dir))


class TestGitUtilsFunctions:
    """Test module-level utility functions."""

    @patch("context_generator.utils.git_utils._git_runner", None)
    def test_get_git_runner_creates_instance(self) -> None:
        """Test that get_git_runner creates a new instance when needed."""
        with patch("shutil.which", return_value="/usr/bin/git"):
            runner = get_git_runner()
            assert isinstance(runner, SecureGitRunner)

    @patch("context_generator.utils.git_utils._git_runner")
    def test_get_git_runner_reuses_instance(self, mock_runner: Mock) -> None:
        """Test that get_git_runner reuses existing instance."""
        result = get_git_runner()
        assert result == mock_runner

    def test_is_git_repository_function(self) -> None:
        """Test is_git_repository function."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch(
                "context_generator.utils.git_utils.get_git_runner"
            ) as mock_get_runner:
                mock_runner = Mock()
                mock_runner.is_git_repository.return_value = True
                mock_get_runner.return_value = mock_runner

                result = is_git_repository(Path(tmp_dir))

                assert result is True
                mock_runner.is_git_repository.assert_called_once_with(Path(tmp_dir))

    def test_get_tracked_files_function(self) -> None:
        """Test get_tracked_files function."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch(
                "context_generator.utils.git_utils.get_git_runner"
            ) as mock_get_runner:
                mock_runner = Mock()
                expected_files = [Path("file1.py"), Path("file2.py")]
                mock_runner.get_tracked_files.return_value = expected_files
                mock_get_runner.return_value = mock_runner

                result = get_tracked_files(Path(tmp_dir))

                assert result == expected_files
                mock_runner.get_tracked_files.assert_called_once_with(Path(tmp_dir))

    def test_get_tracked_files_git_error_non_128(self) -> None:
        """Test get_tracked_files with git error (non-128 exit code)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("shutil.which", return_value="/usr/bin/git"):
                runner = SecureGitRunner()

                # Mock subprocess.run to raise CalledProcessError with exit code != 128
                mock_error = subprocess.CalledProcessError(
                    1, "git", stderr=b"Some error"
                )
                with patch("subprocess.run", side_effect=mock_error):
                    with pytest.raises(
                        RuntimeError, match="Git command failed with exit code 1"
                    ):
                        runner.get_tracked_files(Path(tmp_dir))

    def test_get_tracked_symlinks_git_error_non_128(self) -> None:
        """Test get_tracked_symlinks with git error (non-128 exit code)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("shutil.which", return_value="/usr/bin/git"):
                runner = SecureGitRunner()

                # Mock subprocess.run to raise CalledProcessError with exit code != 128
                mock_error = subprocess.CalledProcessError(1, "git")
                with patch("subprocess.run", side_effect=mock_error):
                    with pytest.raises(
                        RuntimeError, match="Git command failed with exit code 1"
                    ):
                        runner.get_tracked_symlinks(Path(tmp_dir))

    def test_get_tracked_symlinks_timeout(self) -> None:
        """Test get_tracked_symlinks with timeout."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("shutil.which", return_value="/usr/bin/git"):
                runner = SecureGitRunner()

                # Mock subprocess.run to raise TimeoutExpired
                mock_error = subprocess.TimeoutExpired("git", 30)
                with patch("subprocess.run", side_effect=mock_error):
                    with pytest.raises(RuntimeError, match="Git command timed out"):
                        runner.get_tracked_symlinks(Path(tmp_dir))
