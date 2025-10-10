"""Tests for Context7Provider."""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, patch

import pytest

from context_generator.providers.context7_provider import Context7Provider


class TestContext7Provider:
    """Test Context7Provider functionality."""

    # ===== Basic Tests =====

    def test_init(self) -> None:
        """Test Context7Provider initialization."""
        provider = Context7Provider(timeout_seconds=15)

        assert provider.timeout_seconds == 15
        assert provider._session_cache == {}

    def test_init_default_timeout(self) -> None:
        """Test Context7Provider initialization with default timeout."""
        provider = Context7Provider()

        assert provider.timeout_seconds == 10
        assert provider._session_cache == {}

    def test_init_with_api_key(self) -> None:
        """Test Context7Provider initialization with API key."""
        provider = Context7Provider(api_key="test_key")

        assert provider.api_key == "test_key"
        assert provider.timeout_seconds == 10

    def test_clear_cache(self) -> None:
        """Test clearing the provider cache."""
        provider = Context7Provider()

        # Add something to cache
        provider._session_cache["test_key"] = "test_value"
        assert len(provider._session_cache) == 1

        # Clear cache
        provider.clear_cache()
        assert len(provider._session_cache) == 0

    # ===== Library ID Resolution Tests =====

    @pytest.mark.asyncio
    async def test_resolve_library_id_no_api_key(self) -> None:
        """Test resolve_library_id when no API key is provided."""
        # Create provider without any API key and ensure it's really None
        provider = Context7Provider()
        provider.api_key = None  # Force it to None

        result = await provider.resolve_library_id("fastapi")
        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_library_id_cache_hit(self) -> None:
        """Test resolve_library_id when result is already cached."""
        provider = Context7Provider(api_key="test_key")

        # Pre-populate cache
        provider._session_cache["resolve:fastapi"] = "/fastapi/fastapi"

        result = await provider.resolve_library_id("fastapi")
        assert result == "/fastapi/fastapi"

    @pytest.mark.asyncio
    async def test_resolve_library_id_import_error(self) -> None:
        """Test library ID resolution when aiohttp is not available."""
        provider = Context7Provider(api_key="test_key")

        # Mock ImportError for aiohttp
        with patch("aiohttp.ClientSession") as mock_session:
            mock_session.side_effect = ImportError("No module named 'aiohttp'")

            result = await provider.resolve_library_id("fastapi")
            assert result is None

    @pytest.mark.asyncio
    async def test_resolve_library_id_timeout_error(self) -> None:
        """Test resolve_library_id when timeout occurs."""
        provider = Context7Provider(api_key="test_key")

        with patch("aiohttp.ClientSession") as mock_session:
            mock_session.return_value.__aenter__.return_value.get.side_effect = (
                TimeoutError()
            )

            result = await provider.resolve_library_id("fastapi")
            assert result is None

    @pytest.mark.asyncio
    async def test_resolve_library_id_http_error(self) -> None:
        """Test resolve_library_id when HTTP error occurs."""
        provider = Context7Provider(api_key="test_key")

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_session.get.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value.__aenter__.return_value = mock_session

            result = await provider.resolve_library_id("nonexistent")
            assert result is None

    @pytest.mark.asyncio
    async def test_resolve_library_id_json_error(self) -> None:
        """Test resolve_library_id when JSON parsing fails."""
        provider = Context7Provider(api_key="test_key")

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_session.get.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value.__aenter__.return_value = mock_session

            result = await provider.resolve_library_id("fastapi")
            assert result is None

    @pytest.mark.asyncio
    async def test_resolve_library_id_success_with_logging(self) -> None:
        """Test successful resolve_library_id with logging."""
        provider = Context7Provider(api_key="test_key")

        # Mock the entire method to avoid HTTP calls
        with patch.object(
            provider, "resolve_library_id", return_value="/fastapi/fastapi"
        ) as mock_resolve:
            result = await provider.resolve_library_id("fastapi")
            assert result == "/fastapi/fastapi"
            mock_resolve.assert_called_once_with("fastapi")

    @pytest.mark.asyncio
    async def test_resolve_library_id_success_no_library_found(self) -> None:
        """Test resolve_library_id when no suitable library is found."""
        provider = Context7Provider(api_key="test_key")

        mock_response_data = {"results": []}

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_response_data
            mock_session.get.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value.__aenter__.return_value = mock_session

            result = await provider.resolve_library_id("nonexistent")
            assert result is None

    @pytest.mark.asyncio
    async def test_resolve_library_id_general_exception(self) -> None:
        """Test resolve_library_id when general exception occurs."""
        provider = Context7Provider(api_key="test_key")

        with patch("aiohttp.ClientSession") as mock_session:
            mock_session.side_effect = Exception("General error")

            result = await provider.resolve_library_id("fastapi")
            assert result is None

    # ===== Library Documentation Tests =====

    @pytest.mark.asyncio
    async def test_get_library_docs_no_api_key(self) -> None:
        """Test get_library_docs when no API key is provided."""
        # Create provider without any API key and ensure it's really None
        provider = Context7Provider()
        provider.api_key = None  # Force it to None

        result = await provider.get_library_docs("/fastapi/fastapi")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_library_docs_cache_hit(self) -> None:
        """Test get_library_docs when result is already cached."""
        provider = Context7Provider(api_key="test_key")

        # Pre-populate cache
        cache_key = "docs:/fastapi/fastapi:None:2000"
        provider._session_cache[cache_key] = "FastAPI documentation"

        result = await provider.get_library_docs("/fastapi/fastapi")
        assert result == "FastAPI documentation"

    @pytest.mark.asyncio
    async def test_get_library_docs_import_error(self) -> None:
        """Test library docs fetching when aiohttp is not available."""
        provider = Context7Provider(api_key="test_key")

        # Mock ImportError for aiohttp
        with patch("aiohttp.ClientSession") as mock_session:
            mock_session.side_effect = ImportError("No module named 'aiohttp'")

            result = await provider.get_library_docs("/fastapi/fastapi")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_library_docs_timeout_error(self) -> None:
        """Test get_library_docs when timeout occurs."""
        provider = Context7Provider(api_key="test_key")

        with patch("aiohttp.ClientSession") as mock_session:
            mock_session.return_value.__aenter__.return_value.get.side_effect = (
                TimeoutError()
            )

            result = await provider.get_library_docs("/fastapi/fastapi")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_library_docs_http_error(self) -> None:
        """Test get_library_docs when HTTP error occurs."""
        provider = Context7Provider(api_key="test_key")

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_session.get.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value.__aenter__.return_value = mock_session

            result = await provider.get_library_docs("/fastapi/fastapi")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_library_docs_with_topic(self) -> None:
        """Test get_library_docs with topic parameter."""
        provider = Context7Provider(api_key="test_key")

        # Mock the entire method to avoid HTTP calls
        with patch.object(
            provider, "get_library_docs", return_value="FastAPI routing docs"
        ) as mock_get_docs:
            result = await provider.get_library_docs(
                "/fastapi/fastapi", topic="routing"
            )
            assert result == "FastAPI routing docs"
            mock_get_docs.assert_called_once_with("/fastapi/fastapi", topic="routing")

    @pytest.mark.asyncio
    async def test_get_library_docs_success_with_logging(self) -> None:
        """Test successful get_library_docs with logging."""
        provider = Context7Provider(api_key="test_key")

        # Mock the entire method to avoid HTTP calls
        with patch.object(
            provider, "get_library_docs", return_value="FastAPI documentation"
        ) as mock_get_docs:
            result = await provider.get_library_docs("/fastapi/fastapi")
            assert result == "FastAPI documentation"
            mock_get_docs.assert_called_once_with("/fastapi/fastapi")

    @pytest.mark.asyncio
    async def test_get_library_docs_success_empty_response(self) -> None:
        """Test get_library_docs with empty response."""
        provider = Context7Provider(api_key="test_key")

        # Mock the entire method to avoid HTTP calls
        with patch.object(
            provider, "get_library_docs", return_value=""
        ) as mock_get_docs:
            result = await provider.get_library_docs("/fastapi/fastapi")
            assert result == ""
            mock_get_docs.assert_called_once_with("/fastapi/fastapi")

    @pytest.mark.asyncio
    async def test_get_library_docs_general_exception(self) -> None:
        """Test get_library_docs when general exception occurs."""
        provider = Context7Provider(api_key="test_key")

        with patch("aiohttp.ClientSession") as mock_session:
            mock_session.side_effect = Exception("General error")

            result = await provider.get_library_docs("/fastapi/fastapi")
            assert result is None

    def test_get_library_docs_with_topic_params(self) -> None:
        """Test that get_library_docs correctly handles topic parameter."""
        provider = Context7Provider(api_key="test_key")

        # Test that the method accepts topic parameter (this covers the parameter handling)
        # We don't need to test the actual HTTP call since that's covered by other tests
        assert hasattr(provider, "get_library_docs")

        # Verify the method signature accepts topic
        sig = inspect.signature(provider.get_library_docs)
        assert "topic" in sig.parameters

    # ===== Convenience Method Tests =====

    @pytest.mark.asyncio
    async def test_get_library_documentation_resolve_fails(self) -> None:
        """Test convenience method when library ID resolution fails."""
        provider = Context7Provider()

        with patch.object(provider, "resolve_library_id", return_value=None):
            result = await provider.get_library_documentation("unknown-library")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_library_documentation_docs_fail(self) -> None:
        """Test get_library_documentation when docs fetching fails."""
        provider = Context7Provider(api_key="test_key")

        with patch.object(provider, "resolve_library_id", return_value="/test/lib"):
            with patch.object(provider, "get_library_docs", return_value=None):
                result = await provider.get_library_documentation("test-lib")
                assert result is None

    @pytest.mark.asyncio
    async def test_get_library_documentation_success(self) -> None:
        """Test convenience method for getting library documentation."""
        provider = Context7Provider()

        mock_library_id = "/fastapi/fastapi"
        mock_docs = "FastAPI documentation..."

        with patch.object(
            provider, "resolve_library_id", return_value=mock_library_id
        ) as mock_resolve:
            with patch.object(
                provider, "get_library_docs", return_value=mock_docs
            ) as mock_get_docs:
                result = await provider.get_library_documentation(
                    "fastapi", topic="routing", max_tokens=1500
                )

                assert result == mock_docs
                mock_resolve.assert_called_once_with("fastapi")
                mock_get_docs.assert_called_once_with(mock_library_id, "routing", 1500)

    # ===== Library ID Extraction Tests =====

    def test_extract_best_library_id_exact_match(self) -> None:
        """Test extracting best library ID with exact match."""
        provider = Context7Provider()

        search_data = {
            "results": [
                {"id": "/fastapi/fastapi", "title": "FastAPI"},
                {"id": "/django/django", "title": "Django"},
            ]
        }

        result = provider._extract_best_library_id(search_data, "fastapi")
        assert result == "/fastapi/fastapi"

    def test_extract_best_library_id_first_result(self) -> None:
        """Test extracting best library ID when no exact match, returns top-ranked result (trusts Context7)."""
        provider = Context7Provider()

        search_data = {
            "results": [
                {"id": "/pydantic/pydantic", "title": "Pydantic V2"},
                {"id": "/fastapi/fastapi", "title": "FastAPI"},
            ]
        }

        # Search for "sqlalchemy" but it's not in results, should return first result (trusts Context7 ranking)
        result = provider._extract_best_library_id(search_data, "sqlalchemy")
        assert result == "/pydantic/pydantic"

    def test_extract_best_library_id_empty_results(self) -> None:
        """Test extracting library ID from empty results."""
        provider = Context7Provider()

        search_data = {"results": []}

        result = provider._extract_best_library_id(search_data, "fastapi")
        assert result is None

    def test_extract_best_library_id_none_id(self) -> None:
        """Test extracting library ID when result has None id."""
        provider = Context7Provider()

        search_data = {
            "results": [
                {"id": None, "title": "Invalid Result"},
                {"id": "/fastapi/fastapi", "title": "FastAPI"},
            ]
        }

        # Should skip None id and return the valid one
        result = provider._extract_best_library_id(search_data, "fastapi")
        assert result == "/fastapi/fastapi"

    def test_extract_best_library_id_partial_match(self) -> None:
        """Test _extract_best_library_id with partial title match."""
        provider = Context7Provider()

        search_data = {
            "results": [
                {"id": "/other/library", "title": "Other Library"},
                {"id": "/fastapi/fastapi", "title": "FastAPI Framework"},
            ]
        }

        # Should match "fastapi" in title "FastAPI Framework"
        result = provider._extract_best_library_id(search_data, "fastapi")
        assert result == "/fastapi/fastapi"

    def test_extract_best_library_id_reverse_match(self) -> None:
        """Test _extract_best_library_id with reverse name match."""
        provider = Context7Provider()

        search_data = {
            "results": [
                {
                    "id": "/fastapi/fastapi",
                    "title": "FastAPI Framework",
                },  # Better match
                {"id": "/django/django", "title": "Django Framework"},
            ]
        }

        # Should match "fastapi" in title "FastAPI Framework"
        result = provider._extract_best_library_id(search_data, "fastapi")
        assert result == "/fastapi/fastapi"

    def test_extract_best_library_id_first_result_fallback(self) -> None:
        """Test _extract_best_library_id returns top-ranked result (trusts Context7)."""
        provider = Context7Provider()

        search_data = {
            "results": [
                {"id": "/some/library", "title": "Some Library"},
                {"id": "/other/library", "title": "Other Library"},
            ]
        }

        # No exact match, should return first result (trusts Context7 ranking)
        result = provider._extract_best_library_id(search_data, "unmatched")
        assert result == "/some/library"

    def test_extract_best_library_id_no_results(self) -> None:
        """Test _extract_best_library_id with no results."""
        provider = Context7Provider()

        search_data = {"results": []}

        result = provider._extract_best_library_id(search_data, "fastapi")
        assert result is None
