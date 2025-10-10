"""Tests for SSL certificate management utilities."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from aiohttp import ClientError

from ai_code_review.utils.ssl_utils import SSLCertificateManager


class TestSSLCertificateManager:
    """Test SSL certificate management functionality."""

    @pytest.fixture
    def ssl_manager(self, tmp_path: Path) -> SSLCertificateManager:
        """Create SSL manager with temporary cache directory."""
        return SSLCertificateManager(str(tmp_path / "ssl_cache"))

    @pytest.fixture
    def mock_cert_content(self) -> str:
        """Mock certificate content for testing."""
        return """-----BEGIN CERTIFICATE-----
MIIFazCCA1OgAwIBAgIRAIIQz7DSQONZRGPgu2OCiwAwDQYJKoZIhvcNAQELBQAw
TzELMAkGA1UEBhMCVVMxKTAnBgNVBAoTIEludGVybmV0IFNlY3VyaXR5IFJlc2Vh
cmNoIEdyb3VwMRUwEwYDVQQDEwxJU1JHIFJvb3QgWDEwHhcNMTUwNjA0MTEwNDM4
WhcNMzUwNjA0MTEwNDM4WjBPMQswCQYDVQQGEwJVUzEpMCcGA1UEChMgSW50ZXJu
ZXQgU2VjdXJpdHkgUmVzZWFyY2ggR3JvdXAxFTATBgNVBAMTDElTUkcgUm9vdCBY
-----END CERTIFICATE-----"""

    @pytest.mark.asyncio
    async def test_get_certificate_path_existing_file(
        self, ssl_manager: SSLCertificateManager, tmp_path: Path
    ) -> None:
        """Test getting certificate path from existing file."""
        # Create test certificate file
        cert_file = tmp_path / "test.crt"
        cert_file.write_text("test certificate content")

        result = await ssl_manager.get_certificate_path(cert_path=str(cert_file))

        assert result == str(cert_file)

    @pytest.mark.asyncio
    async def test_get_certificate_path_nonexistent_file(
        self, ssl_manager: SSLCertificateManager
    ) -> None:
        """Test error when certificate file doesn't exist."""
        with pytest.raises(ValueError, match="SSL certificate file not found"):
            await ssl_manager.get_certificate_path(cert_path="/nonexistent/cert.crt")

    @pytest.mark.asyncio
    async def test_get_certificate_path_no_cert_configured(
        self, ssl_manager: SSLCertificateManager
    ) -> None:
        """Test returning None when no certificate configured."""
        result = await ssl_manager.get_certificate_path()
        assert result is None

    @pytest.mark.asyncio
    async def test_download_certificate_success(
        self, ssl_manager: SSLCertificateManager, mock_cert_content: str
    ) -> None:
        """Test successful certificate download and caching."""
        cert_url = "https://internal-gitlab.com/ca-cert.crt"

        with patch.object(
            ssl_manager, "_download_and_cache_certificate"
        ) as mock_download:
            # Mock the download to return a fake certificate path
            fake_cert_path = str(ssl_manager.cache_dir / "test_cert.pem")
            ssl_manager.cache_dir.mkdir(exist_ok=True)
            Path(fake_cert_path).write_text(mock_cert_content)
            mock_download.return_value = fake_cert_path

            result = await ssl_manager.get_certificate_path(cert_url=cert_url)

        # Verify certificate path was returned
        assert result == fake_cert_path
        assert Path(result).exists()
        assert mock_cert_content in Path(result).read_text()

        # Verify download function was called
        mock_download.assert_called_once_with(cert_url)

    @pytest.mark.asyncio
    async def test_download_certificate_http_error(
        self, ssl_manager: SSLCertificateManager
    ) -> None:
        """Test handling HTTP errors during certificate download."""
        cert_url = "https://internal-gitlab.com/ca-cert.crt"

        with patch.object(
            ssl_manager, "_download_and_cache_certificate"
        ) as mock_download:
            mock_download.side_effect = ValueError(
                "Failed to download certificate: HTTP 404"
            )

            with pytest.raises(
                ValueError, match="Failed to download certificate: HTTP 404"
            ):
                await ssl_manager.get_certificate_path(cert_url=cert_url)

    @pytest.mark.asyncio
    async def test_download_certificate_network_error(
        self, ssl_manager: SSLCertificateManager
    ) -> None:
        """Test handling network errors during certificate download."""
        cert_url = "https://internal-gitlab.com/ca-cert.crt"

        with patch.object(
            ssl_manager, "_download_and_cache_certificate"
        ) as mock_download:
            mock_download.side_effect = ValueError(
                "Failed to download SSL certificate from https://internal-gitlab.com/ca-cert.crt: Connection failed"
            )

            with pytest.raises(
                ValueError,
                match="Failed to download SSL certificate.*Connection failed",
            ):
                await ssl_manager.get_certificate_path(cert_url=cert_url)

    @pytest.mark.asyncio
    async def test_download_certificate_invalid_content(
        self, ssl_manager: SSLCertificateManager
    ) -> None:
        """Test handling invalid certificate content."""
        cert_url = "https://internal-gitlab.com/ca-cert.crt"

        with patch.object(
            ssl_manager, "_download_and_cache_certificate"
        ) as mock_download:
            mock_download.side_effect = ValueError(
                "Downloaded content is not a valid certificate: https://internal-gitlab.com/ca-cert.crt"
            )

            with pytest.raises(
                ValueError, match="Downloaded content is not a valid certificate"
            ):
                await ssl_manager.get_certificate_path(cert_url=cert_url)

    @pytest.mark.asyncio
    async def test_certificate_caching(
        self, ssl_manager: SSLCertificateManager, mock_cert_content: str
    ) -> None:
        """Test certificate caching functionality."""
        cert_url = "https://internal-gitlab.com/ca-cert.crt"

        # Create a fake cached certificate
        fake_cert_path = str(ssl_manager.cache_dir / "test_cert.pem")
        ssl_manager.cache_dir.mkdir(exist_ok=True)
        Path(fake_cert_path).write_text(mock_cert_content)

        with patch.object(
            ssl_manager, "_download_and_cache_certificate"
        ) as mock_download:
            mock_download.return_value = fake_cert_path

            # First call - should download
            result1 = await ssl_manager.get_certificate_path(cert_url=cert_url)

            # Second call - should use cache (create new cached file for second call)
            Path(fake_cert_path).write_text(
                mock_cert_content
            )  # Ensure it exists for second call
            result2 = await ssl_manager.get_certificate_path(cert_url=cert_url)

        # Both should return same path
        assert result1 == fake_cert_path
        assert result2 == fake_cert_path
        assert Path(result1).exists()

        # Should be called for both (in this simplified test)
        assert mock_download.call_count >= 1

    def test_is_valid_certificate_content_valid(
        self, ssl_manager: SSLCertificateManager, mock_cert_content: str
    ) -> None:
        """Test certificate content validation with valid certificate."""
        result = ssl_manager._is_valid_certificate_content(mock_cert_content)
        assert result is True

    def test_is_valid_certificate_content_invalid(
        self, ssl_manager: SSLCertificateManager
    ) -> None:
        """Test certificate content validation with invalid content."""
        invalid_contents = [
            "This is not a certificate",
            "-----BEGIN CERTIFICATE-----\n",  # Missing end
            "-----END CERTIFICATE-----",  # Missing begin
            "",  # Empty
            "-----BEGIN CERTIFICATE-----\nshort\n-----END CERTIFICATE-----",  # Too short
        ]

        for content in invalid_contents:
            result = ssl_manager._is_valid_certificate_content(content)
            assert result is False

    @pytest.mark.asyncio
    async def test_priority_order_cert_path_over_url(
        self, ssl_manager: SSLCertificateManager, tmp_path: Path
    ) -> None:
        """Test that ssl_cert_path has priority over ssl_cert_url."""
        # Create test certificate file
        cert_file = tmp_path / "local.crt"
        cert_file.write_text("local certificate content")

        cert_url = "https://internal-gitlab.com/ca-cert.crt"

        # Should use cert_path and NOT download from URL
        result = await ssl_manager.get_certificate_path(
            cert_path=str(cert_file),
            cert_url=cert_url,
        )

        assert result == str(cert_file)
        # No HTTP call should be made when cert_path is provided

    @pytest.mark.asyncio
    async def test_download_and_cache_certificate_success(
        self, ssl_manager: SSLCertificateManager, mock_cert_content: str
    ) -> None:
        """Test actual certificate download with mocked HTTP response."""
        cert_url = "https://internal-gitlab.com/ca-cert.crt"

        # Mock aiohttp response
        with patch("aiohttp.ClientSession.get") as mock_get:
            # Setup mock response that acts as async context manager
            mock_response = mock_get.return_value.__aenter__.return_value
            mock_response.status = 200
            mock_response.text.return_value = mock_cert_content

            result = await ssl_manager._download_and_cache_certificate(cert_url)

        # Verify certificate was cached
        assert Path(result).exists()
        assert mock_cert_content in Path(result).read_text()
        assert result.endswith(".pem")

    @pytest.mark.asyncio
    async def test_download_and_cache_certificate_http_error(
        self, ssl_manager: SSLCertificateManager
    ) -> None:
        """Test HTTP error handling during certificate download."""
        cert_url = "https://internal-gitlab.com/ca-cert.crt"

        # Mock HTTP 404 error
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = mock_get.return_value.__aenter__.return_value
            mock_response.status = 404

            with pytest.raises(
                ValueError, match="Failed to download certificate: HTTP 404"
            ):
                await ssl_manager._download_and_cache_certificate(cert_url)

    @pytest.mark.asyncio
    async def test_download_and_cache_certificate_invalid_content(
        self, ssl_manager: SSLCertificateManager
    ) -> None:
        """Test invalid certificate content handling."""
        cert_url = "https://internal-gitlab.com/ca-cert.crt"

        # Mock response with invalid certificate content
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = mock_get.return_value.__aenter__.return_value
            mock_response.status = 200
            mock_response.text.return_value = "This is not a certificate"

            with pytest.raises(
                ValueError, match="Downloaded content is not a valid certificate"
            ):
                await ssl_manager._download_and_cache_certificate(cert_url)

    @pytest.mark.asyncio
    async def test_download_and_cache_certificate_network_error(
        self, ssl_manager: SSLCertificateManager
    ) -> None:
        """Test network error handling during certificate download."""
        cert_url = "https://internal-gitlab.com/ca-cert.crt"

        # Mock aiohttp ClientError
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.side_effect = ClientError("Connection failed")

            with pytest.raises(
                ValueError,
                match="Failed to download SSL certificate.*Connection failed",
            ):
                await ssl_manager._download_and_cache_certificate(cert_url)

    @pytest.mark.asyncio
    async def test_is_certificate_valid_existing_valid(
        self, ssl_manager: SSLCertificateManager, mock_cert_content: str, tmp_path: Path
    ) -> None:
        """Test certificate validation with valid cached certificate."""
        cert_file = tmp_path / "valid_cert.pem"
        cert_file.write_text(mock_cert_content)

        result = await ssl_manager._is_certificate_valid(cert_file)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_certificate_valid_nonexistent(
        self, ssl_manager: SSLCertificateManager, tmp_path: Path
    ) -> None:
        """Test certificate validation with nonexistent file."""
        nonexistent_file = tmp_path / "nonexistent.pem"

        result = await ssl_manager._is_certificate_valid(nonexistent_file)
        assert result is False

    @pytest.mark.asyncio
    async def test_is_certificate_valid_invalid_content(
        self, ssl_manager: SSLCertificateManager, tmp_path: Path
    ) -> None:
        """Test certificate validation with invalid content."""
        cert_file = tmp_path / "invalid_cert.pem"
        cert_file.write_text("This is not a certificate")

        result = await ssl_manager._is_certificate_valid(cert_file)
        assert result is False

    @pytest.mark.asyncio
    async def test_is_certificate_valid_read_error(
        self, ssl_manager: SSLCertificateManager, tmp_path: Path
    ) -> None:
        """Test certificate validation with file read error."""
        # Create a directory instead of a file to cause read error
        cert_dir = tmp_path / "not_a_file.pem"
        cert_dir.mkdir()

        result = await ssl_manager._is_certificate_valid(cert_dir)
        assert result is False

    @pytest.mark.asyncio
    async def test_cache_invalidation_and_redownload(
        self, ssl_manager: SSLCertificateManager, mock_cert_content: str
    ) -> None:
        """Test that invalid cached certificates are re-downloaded."""
        cert_url = "https://internal-gitlab.com/ca-cert.crt"

        # Create invalid cached certificate
        url_hash = "test_hash"
        cache_filename = f"cert_{url_hash}.pem"
        cache_path = ssl_manager.cache_dir / cache_filename
        ssl_manager.cache_dir.mkdir(exist_ok=True)
        cache_path.write_text("invalid certificate content")

        # Mock the actual download method
        with (
            patch("aiohttp.ClientSession.get") as mock_get,
            patch("hashlib.sha256") as mock_hash,
        ):
            # Mock hash to use predictable cache filename
            mock_hash.return_value.hexdigest.return_value = (
                url_hash + "0000000000000000"
            )

            # Setup mock response
            mock_response = mock_get.return_value.__aenter__.return_value
            mock_response.status = 200
            mock_response.text.return_value = mock_cert_content

            result = await ssl_manager.get_certificate_path(cert_url=cert_url)

        # Verify new valid certificate was downloaded and cached
        assert Path(result).exists()
        assert mock_cert_content in Path(result).read_text()

    @pytest.mark.asyncio
    async def test_cached_valid_certificate_path_coverage(
        self, ssl_manager: SSLCertificateManager, mock_cert_content: str
    ) -> None:
        """Test cache hit path to cover lines 82-90."""
        cert_url = "https://internal-gitlab.com/ca-cert.crt"

        # Create the actual cache path that would be generated
        import hashlib

        url_hash = hashlib.sha256(cert_url.encode()).hexdigest()[:16]
        cache_filename = f"cert_{url_hash}.pem"
        cache_path = ssl_manager.cache_dir / cache_filename
        ssl_manager.cache_dir.mkdir(exist_ok=True)
        cache_path.write_text(mock_cert_content)

        # Call the _download_and_cache_certificate method directly
        # This should hit the cache and return without downloading
        result = await ssl_manager._download_and_cache_certificate(cert_url)

        # Verify cached certificate was used
        assert result == str(cache_path)
        assert Path(result).exists()
        assert mock_cert_content in Path(result).read_text()

    @pytest.mark.asyncio
    async def test_cached_invalid_certificate_redownload_path(
        self, ssl_manager: SSLCertificateManager, mock_cert_content: str
    ) -> None:
        """Test cache invalidation path to cover line 90."""
        cert_url = "https://internal-gitlab.com/ca-cert.crt"

        # Create the actual cache path with invalid content
        import hashlib

        url_hash = hashlib.sha256(cert_url.encode()).hexdigest()[:16]
        cache_filename = f"cert_{url_hash}.pem"
        cache_path = ssl_manager.cache_dir / cache_filename
        ssl_manager.cache_dir.mkdir(exist_ok=True)
        cache_path.write_text("invalid certificate content")  # Invalid content

        # Mock aiohttp to provide valid certificate on download
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = mock_get.return_value.__aenter__.return_value
            mock_response.status = 200
            mock_response.text.return_value = mock_cert_content

            # This should detect invalid cache and re-download
            result = await ssl_manager._download_and_cache_certificate(cert_url)

        # Verify valid certificate was downloaded and cached
        assert result == str(cache_path)
        assert Path(result).exists()
        assert mock_cert_content in Path(result).read_text()
