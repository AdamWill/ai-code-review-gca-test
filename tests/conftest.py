"""Shared test fixtures for AI Code Review tests."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import Mock

import pytest


def create_gitpython_mock() -> Mock:
    """Create a complete GitPython mock for CI compatibility.

    This function creates a mock git module to prevent GitPython
    from trying to find the git binary during imports. This is
    essential for CI environments that don't have git installed.

    Returns:
        Mock: Configured git mock with necessary exceptions and classes
    """
    git_mock = Mock()
    git_mock.GitCommandError = type("GitCommandError", (Exception,), {})
    git_mock.InvalidGitRepositoryError = type(
        "InvalidGitRepositoryError", (Exception,), {}
    )
    git_mock.Repo = Mock
    return git_mock


@pytest.fixture
def chdir_tmp(tmp_path: Path):
    """Change to temporary directory and restore on cleanup.

    This fixture handles the common pattern of temporarily changing
    the working directory for tests that need to work with files
    relative to the current directory.

    Args:
        tmp_path: pytest temporary directory fixture

    Yields:
        Path: The temporary directory path
    """
    original_dir = os.getcwd()
    os.chdir(str(tmp_path))
    try:
        yield tmp_path
    finally:
        os.chdir(original_dir)
