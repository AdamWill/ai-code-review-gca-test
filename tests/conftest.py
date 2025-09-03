"""Shared test fixtures for AI Code Review tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


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
