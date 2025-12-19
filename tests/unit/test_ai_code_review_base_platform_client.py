"""Tests for base platform client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_code_review.core.base_platform_client import BasePlatformClient
from ai_code_review.models.config import AIProvider, Config, PlatformProvider


class DummyPlatformClient(BasePlatformClient):
    """Dummy implementation for testing."""

    async def get_authenticated_username(self) -> str:
        """Mock implementation."""
        return "test_user"

    async def get_pull_request_data(self, project_id: str, pr_number: int):
        """Mock implementation."""
        pass

    async def post_review(self, project_id: str, pr_number: int, review_content: str):
        """Mock implementation."""
        pass

    def get_platform_name(self) -> str:
        """Mock implementation."""
        return "test"

    def format_project_url(self, project_id: str) -> str:
        """Mock implementation."""
        return f"https://test.com/{project_id}"


@pytest.fixture
def test_config(monkeypatch) -> Config:
    """Test configuration isolated from environment variables."""
    # Set required environment variables for Anthropic
    monkeypatch.setenv("AI_API_KEY", "test_key")
    monkeypatch.setenv("GITLAB_TOKEN", "test_token")
    monkeypatch.setenv("GITLAB_URL", "https://gitlab.com")

    return Config(
        platform_provider=PlatformProvider.GITLAB,
        gitlab_url="https://gitlab.com",
        gitlab_token="test_token",
        ai_provider=AIProvider.ANTHROPIC,
        project_id="test/project",
        mr_iid=123,
        exclude_patterns=["*.lock", "*.min.js"],
        max_files=10,
    )


class TestBasePlatformClientConvertPatchset:
    """Test _convert_patchset_to_diffs method."""

    def test_convert_patchset_basic(self, test_config: Config) -> None:
        """Test basic patchset conversion."""
        client = DummyPlatformClient(test_config)

        # Create mock patched files
        mock_file1 = MagicMock()
        mock_file1.path = "file1.py"
        mock_file1.is_binary_file = False
        mock_file1.is_added_file = True
        mock_file1.is_rename = False
        mock_file1.is_removed_file = False
        mock_file1.__str__ = MagicMock(return_value="diff content 1")

        mock_file2 = MagicMock()
        mock_file2.path = "file2.py"
        mock_file2.is_binary_file = False
        mock_file2.is_added_file = False
        mock_file2.is_rename = False
        mock_file2.is_removed_file = False
        mock_file2.__str__ = MagicMock(return_value="diff content 2")

        mock_patch_set = [mock_file1, mock_file2]

        diffs = client._convert_patchset_to_diffs(mock_patch_set)

        assert len(diffs) == 2
        assert diffs[0].file_path == "file1.py"
        assert diffs[0].new_file is True
        assert diffs[0].diff == "diff content 1"
        assert diffs[1].file_path == "file2.py"
        assert diffs[1].new_file is False
        assert diffs[1].diff == "diff content 2"

    def test_convert_patchset_filters_binary(self, test_config: Config) -> None:
        """Test that binary files are filtered out."""
        client = DummyPlatformClient(test_config)

        # Create mock patched files
        mock_binary = MagicMock()
        mock_binary.path = "image.png"
        mock_binary.is_binary_file = True

        mock_text = MagicMock()
        mock_text.path = "file.py"
        mock_text.is_binary_file = False
        mock_text.is_added_file = False
        mock_text.is_rename = False
        mock_text.is_removed_file = False
        mock_text.__str__ = MagicMock(return_value="diff content")

        mock_patch_set = [mock_binary, mock_text]

        diffs = client._convert_patchset_to_diffs(mock_patch_set)

        assert len(diffs) == 1
        assert diffs[0].file_path == "file.py"

    def test_convert_patchset_filters_excluded_patterns(
        self, test_config: Config
    ) -> None:
        """Test that files matching exclude patterns are filtered out."""
        client = DummyPlatformClient(test_config)

        # Create mock patched files - using filenames that match test config patterns
        mock_lock = MagicMock()
        mock_lock.path = "yarn.lock"  # Matches *.lock pattern
        mock_lock.is_binary_file = False

        mock_minified = MagicMock()
        mock_minified.path = "app.min.js"  # Matches *.min.js pattern
        mock_minified.is_binary_file = False

        mock_normal = MagicMock()
        mock_normal.path = "app.py"
        mock_normal.is_binary_file = False
        mock_normal.is_added_file = False
        mock_normal.is_rename = False
        mock_normal.is_removed_file = False
        mock_normal.__str__ = MagicMock(return_value="diff content")

        mock_patch_set = [mock_lock, mock_minified, mock_normal]

        diffs = client._convert_patchset_to_diffs(mock_patch_set)

        assert len(diffs) == 1
        assert diffs[0].file_path == "app.py"

    def test_convert_patchset_respects_max_files(self, test_config: Config) -> None:
        """Test that max_files limit is respected."""
        test_config.max_files = 2
        client = DummyPlatformClient(test_config)

        # Create 3 mock files
        mock_files = []
        for i in range(3):
            mock_file = MagicMock()
            mock_file.path = f"file{i}.py"
            mock_file.is_binary_file = False
            mock_file.is_added_file = False
            mock_file.is_rename = False
            mock_file.is_removed_file = False
            mock_file.__str__ = MagicMock(return_value=f"diff {i}")
            mock_files.append(mock_file)

        mock_patch_set = mock_files

        diffs = client._convert_patchset_to_diffs(mock_patch_set)

        # Should only get 2 files due to max_files limit
        assert len(diffs) == 2
        assert diffs[0].file_path == "file0.py"
        assert diffs[1].file_path == "file1.py"

    def test_convert_patchset_handles_renamed_files(self, test_config: Config) -> None:
        """Test that renamed files are properly identified."""
        client = DummyPlatformClient(test_config)

        mock_renamed = MagicMock()
        mock_renamed.path = "new_name.py"
        mock_renamed.is_binary_file = False
        mock_renamed.is_added_file = False
        mock_renamed.is_rename = True
        mock_renamed.is_removed_file = False
        mock_renamed.__str__ = MagicMock(return_value="diff content")

        mock_patch_set = [mock_renamed]

        diffs = client._convert_patchset_to_diffs(mock_patch_set)

        assert len(diffs) == 1
        assert diffs[0].renamed_file is True

    def test_convert_patchset_handles_deleted_files(self, test_config: Config) -> None:
        """Test that deleted files are properly identified."""
        client = DummyPlatformClient(test_config)

        mock_deleted = MagicMock()
        mock_deleted.path = "deleted.py"
        mock_deleted.is_binary_file = False
        mock_deleted.is_added_file = False
        mock_deleted.is_rename = False
        mock_deleted.is_removed_file = True
        mock_deleted.__str__ = MagicMock(return_value="diff content")

        mock_patch_set = [mock_deleted]

        diffs = client._convert_patchset_to_diffs(mock_patch_set)

        assert len(diffs) == 1
        assert diffs[0].deleted_file is True

    def test_convert_patchset_empty(self, test_config: Config) -> None:
        """Test conversion of empty patchset."""
        client = DummyPlatformClient(test_config)

        mock_patch_set = []

        diffs = client._convert_patchset_to_diffs(mock_patch_set)

        assert len(diffs) == 0


class TestBasePlatformClientFetchDiffViaHttp:
    """Test _fetch_diff_via_http method."""

    @pytest.mark.asyncio
    async def test_fetch_diff_via_http_success(self, test_config: Config) -> None:
        """Test successful HTTP diff fetch."""
        client = DummyPlatformClient(test_config)

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "diff content"

        # Mock httpx.AsyncClient
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # Mock unidiff.PatchSet
        mock_patched_file = MagicMock()
        mock_patched_file.path = "file.py"
        mock_patched_file.is_binary_file = False
        mock_patched_file.is_added_file = False
        mock_patched_file.is_rename = False
        mock_patched_file.is_removed_file = False
        mock_patched_file.__str__ = MagicMock(return_value="diff content")

        mock_patch_set = [mock_patched_file]

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch("asyncio.to_thread", return_value=mock_patch_set),
        ):
            diffs = await client._fetch_diff_via_http(
                diff_url="https://example.com/diff",
                headers={"Authorization": "token test"},
            )

        assert diffs is not None
        assert len(diffs) == 1
        assert diffs[0].file_path == "file.py"

    @pytest.mark.asyncio
    async def test_fetch_diff_via_http_non_200_status(
        self, test_config: Config
    ) -> None:
        """Test HTTP diff fetch with non-200 status code."""
        client = DummyPlatformClient(test_config)

        # Mock HTTP response with non-200 status
        mock_response = MagicMock()
        mock_response.status_code = 404

        # Mock httpx.AsyncClient
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            diffs = await client._fetch_diff_via_http(
                diff_url="https://example.com/diff",
                headers={"Authorization": "token test"},
            )

        assert diffs is None

    @pytest.mark.asyncio
    async def test_fetch_diff_via_http_exception(self, test_config: Config) -> None:
        """Test HTTP diff fetch with exception."""
        client = DummyPlatformClient(test_config)

        # Mock httpx.AsyncClient to raise exception
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Network error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            diffs = await client._fetch_diff_via_http(
                diff_url="https://example.com/diff",
                headers={"Authorization": "token test"},
            )

        assert diffs is None

    @pytest.mark.asyncio
    async def test_fetch_diff_via_http_with_ssl_context(
        self, test_config: Config
    ) -> None:
        """Test HTTP diff fetch with custom SSL context."""
        client = DummyPlatformClient(test_config)

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "diff content"

        # Mock httpx.AsyncClient
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # Mock unidiff.PatchSet
        mock_patch_set = []

        with (
            patch("httpx.AsyncClient", return_value=mock_client) as mock_httpx,
            patch("asyncio.to_thread", return_value=mock_patch_set),
        ):
            ssl_context = MagicMock()
            await client._fetch_diff_via_http(
                diff_url="https://example.com/diff",
                headers={"Authorization": "token test"},
                ssl_context=ssl_context,
            )

        # Verify AsyncClient was called with ssl_context
        mock_httpx.assert_called_once()
        call_kwargs = mock_httpx.call_args[1]
        assert call_kwargs["verify"] == ssl_context

    @pytest.mark.asyncio
    async def test_fetch_diff_via_http_filters_binary_and_excluded(
        self, test_config: Config
    ) -> None:
        """Test that HTTP diff fetch applies filtering."""
        client = DummyPlatformClient(test_config)

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "diff content"

        # Mock httpx.AsyncClient
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # Mock unidiff.PatchSet with binary and excluded files
        mock_binary = MagicMock()
        mock_binary.path = "image.png"
        mock_binary.is_binary_file = True

        mock_excluded = MagicMock()
        mock_excluded.path = "package.lock"  # Matches *.lock pattern
        mock_excluded.is_binary_file = False

        mock_normal = MagicMock()
        mock_normal.path = "app.py"
        mock_normal.is_binary_file = False
        mock_normal.is_added_file = False
        mock_normal.is_rename = False
        mock_normal.is_removed_file = False
        mock_normal.__str__ = MagicMock(return_value="diff content")

        mock_patch_set = [mock_binary, mock_excluded, mock_normal]

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch("asyncio.to_thread", return_value=mock_patch_set),
        ):
            diffs = await client._fetch_diff_via_http(
                diff_url="https://example.com/diff",
                headers={"Authorization": "token test"},
            )

        assert diffs is not None
        assert len(diffs) == 1
        assert diffs[0].file_path == "app.py"
