"""Shared test fixtures for AI Code Review tests."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from ai_code_review.models.config import Config


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


@pytest.fixture(autouse=True)
def clean_environment(request):
    """Clean environment variables for consistent test runs.

    This fixture ensures tests are isolated from developer's local environment.
    It removes/patches environment variables that could affect test behavior.

    Tests can use the @pytest.mark.allow_env_file marker to allow .env file loading.
    """
    # Check if test allows .env file loading
    allow_env_file = request.node.get_closest_marker("allow_env_file") is not None

    # Environment variables that could interfere with tests
    env_vars_to_clean = [
        "SSL_CERT_PATH",
        "SSL_CERT_URL",
        "GITLAB_TOKEN",
        "GITHUB_TOKEN",
        "AI_API_KEY",
        "GITLAB_URL",
        "GITHUB_URL",
        "OLLAMA_BASE_URL",
        # Add more as needed
    ]

    # Store original values
    original_values = {}
    for var in env_vars_to_clean:
        original_values[var] = os.environ.get(var)
        # Remove from environment if it exists
        if var in os.environ:
            del os.environ[var]

    # Also patch the model_config to prevent .env file loading during tests (unless allowed)
    original_model_config = None
    if not allow_env_file:
        from ai_code_review.models.config import Config

        original_model_config = Config.model_config.copy()

        # Disable .env file loading for tests
        Config.model_config = {
            **original_model_config,
            "env_file": None,  # Disable .env file loading
        }

    try:
        yield
    finally:
        # Restore original environment
        for var, value in original_values.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]

        # Restore original model config if it was changed
        if original_model_config is not None:
            from ai_code_review.models.config import Config

            Config.model_config = original_model_config


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


# ===== Configuration Fixtures =====
# These fixtures provide common test configurations to reduce duplication


@pytest.fixture
def ollama_config() -> Config:
    """Create a test config for Ollama provider.

    Returns:
        Config: Configuration with Ollama provider and test values
    """
    return Config(
        gitlab_token="dummy",
        ai_provider="ollama",
        dry_run=True,
        ollama_base_url="http://localhost:11434",
    )


@pytest.fixture
def anthropic_config() -> Config:
    """Create a test config for Anthropic provider.

    Returns:
        Config: Configuration with Anthropic provider and test values
    """
    return Config(
        gitlab_token="dummy",
        ai_provider="anthropic",
        dry_run=True,
        ai_api_key="test_key",
    )


@pytest.fixture
def gemini_config() -> Config:
    """Create a test config for Gemini provider.

    Returns:
        Config: Configuration with Gemini provider and test values
    """
    return Config(
        gitlab_token="dummy",
        ai_provider="gemini",
        dry_run=True,
        ai_api_key="test_key",
    )


@pytest.fixture
def basic_config() -> Config:
    """Create a basic test config with minimal required fields.

    Returns:
        Config: Basic configuration for testing
    """
    return Config(
        gitlab_token="dummy",
        ai_provider="ollama",
        dry_run=True,
    )


@pytest.fixture
def github_config() -> Config:
    """Create a test config with GitHub tokens.

    Returns:
        Config: Configuration with both GitLab and GitHub tokens
    """
    return Config(
        gitlab_token="dummy",
        github_token="dummy",
        ai_provider="ollama",
        dry_run=True,
    )


# ===== HTTP Mocking Helpers =====


@contextmanager
def mock_httpx_client(diff_content: str, status: int = 200) -> Any:  # type: ignore[misc]
    """Create a mocked httpx client for testing HTTP diff fetching.

    This helper centralizes the complex mocking pattern needed for httpx's
    async context managers and streaming responses.

    Args:
        diff_content: The diff content to return from the mocked response
        status: HTTP status code to return (default: 200)

    Yields:
        The mocked client class (already patched via context manager)

    Example:
        with mock_httpx_client(diff_content="diff content"):
            diffs = await client._fetch_and_parse_diff_with_prefiltering(
                url, headers
            )
    """

    # Create async iterators for aiter_bytes and aiter_text
    async def async_chunks() -> Any:  # type: ignore[misc]
        yield diff_content.encode("utf-8")

    async def async_text_chunks() -> Any:  # type: ignore[misc]
        yield diff_content

    mock_response = MagicMock()
    mock_response.status_code = status
    mock_response.aiter_bytes = MagicMock(return_value=async_chunks())
    mock_response.aiter_text = MagicMock(return_value=async_text_chunks())
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_client = MagicMock()
    mock_client.stream = MagicMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value = mock_client
        yield mock_client_class
