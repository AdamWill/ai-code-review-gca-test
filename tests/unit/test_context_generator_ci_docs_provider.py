"""Tests for CI documentation provider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from context_generator.models import CIDocsConfig
from context_generator.providers.ci_docs_provider import CIDocsProvider


class TestCIDocsProvider:
    """Test CIDocsProvider functionality."""

    @pytest.fixture
    def config(self) -> CIDocsConfig:
        """Create test configuration."""
        return CIDocsConfig(
            enabled=True,
            timeout_seconds=30,
            max_content_length=100000,
        )

    @pytest.fixture
    def provider(self, config: CIDocsConfig) -> CIDocsProvider:
        """Create provider instance."""
        return CIDocsProvider(config)

    def test_init(self, provider: CIDocsProvider, config: CIDocsConfig) -> None:
        """Test provider initialization."""
        assert provider.config == config
        assert "gitlab-ci" in provider.CI_DOCS_URLS
        assert "github-actions" in provider.CI_DOCS_URLS

    def test_ci_docs_urls_structure(self, provider: CIDocsProvider) -> None:
        """Test that CI_DOCS_URLS has correct structure."""
        assert isinstance(provider.CI_DOCS_URLS, dict)

        # GitLab CI URLs
        gitlab_urls = provider.CI_DOCS_URLS["gitlab-ci"]
        assert "yaml" in gitlab_urls
        assert "variables" in gitlab_urls
        assert "jobs" in gitlab_urls
        assert "pipelines" in gitlab_urls

        # GitHub Actions URLs
        github_urls = provider.CI_DOCS_URLS["github-actions"]
        assert "workflow-syntax" in github_urls
        assert "variables" in github_urls
        assert "secrets" in github_urls

    @pytest.mark.asyncio
    async def test_fetch_ci_documentation_unknown_system(
        self, provider: CIDocsProvider
    ) -> None:
        """Test fetching docs for unknown CI system."""
        with pytest.raises(ValueError, match="Unsupported CI system"):
            await provider.fetch_ci_documentation("unknown-ci")

    @pytest.mark.asyncio
    async def test_fetch_ci_documentation_success(
        self, provider: CIDocsProvider
    ) -> None:
        """Test successful documentation fetch."""
        test_content = "# Test documentation content"

        # Create mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=test_content)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        # Create mock session
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await provider.fetch_ci_documentation("gitlab-ci")

            # Should have fetched some docs (at least one)
            assert len(result) > 0
            # Check that values are strings
            for value in result.values():
                assert isinstance(value, str)
                assert value == test_content

    @pytest.mark.asyncio
    async def test_fetch_ci_documentation_http_error(
        self, provider: CIDocsProvider
    ) -> None:
        """Test handling HTTP errors."""
        # Create mock response with 404
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        # Create mock session
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await provider.fetch_ci_documentation("gitlab-ci")

            # Should return empty dict when all requests fail
            assert result == {}

    @pytest.mark.asyncio
    async def test_fetch_ci_documentation_content_too_large(
        self, provider: CIDocsProvider
    ) -> None:
        """Test handling content that's too large (should truncate)."""
        # Create content larger than max_content_length
        large_content = "x" * (provider.config.max_content_length + 1000)

        # Create mock response with proper async context manager
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=large_content)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        # Create mock session
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await provider.fetch_ci_documentation("gitlab-ci")

            # Should return truncated content, not empty dict
            assert result != {}
            # Check that all doc types have truncated content
            for _doc_type, content in result.items():
                assert len(content) == provider.config.max_content_length
                assert content == large_content[: provider.config.max_content_length]

    @pytest.mark.asyncio
    async def test_fetch_ci_documentation_exception(
        self, provider: CIDocsProvider
    ) -> None:
        """Test handling exceptions during fetch."""
        # Create mock session that raises exception
        mock_session = AsyncMock()
        mock_session.get.side_effect = aiohttp.ClientError("Connection error")
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await provider.fetch_ci_documentation("gitlab-ci")

            # Should return empty dict when exceptions occur
            assert result == {}

    def test_get_supported_ci_systems(self, provider: CIDocsProvider) -> None:
        """Test getting list of supported CI systems."""
        systems = provider.get_supported_ci_systems()

        assert isinstance(systems, list)
        assert "gitlab-ci" in systems
        assert "github-actions" in systems

    def test_get_doc_types_for_ci_system_gitlab(self, provider: CIDocsProvider) -> None:
        """Test getting doc types for GitLab CI."""
        doc_types = provider.get_doc_types_for_ci_system("gitlab-ci")

        assert isinstance(doc_types, list)
        assert "yaml" in doc_types
        assert "variables" in doc_types
        assert "jobs" in doc_types
        assert "pipelines" in doc_types

    def test_get_doc_types_for_ci_system_github(self, provider: CIDocsProvider) -> None:
        """Test getting doc types for GitHub Actions."""
        doc_types = provider.get_doc_types_for_ci_system("github-actions")

        assert isinstance(doc_types, list)
        assert "workflow-syntax" in doc_types
        assert "variables" in doc_types
        assert "secrets" in doc_types

    def test_get_doc_types_for_ci_system_unknown(
        self, provider: CIDocsProvider
    ) -> None:
        """Test getting doc types for unknown CI system."""
        with pytest.raises(ValueError, match="Unsupported CI system"):
            provider.get_doc_types_for_ci_system("unknown-ci")
